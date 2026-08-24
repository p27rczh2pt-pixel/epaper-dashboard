"""
Renders the dashboard layout to a PIL Image, given the aggregated data
dict produced by poller.py's fetch_all() — keys "pihole_stats",
"pihole_health", "network_health", "system_health", each either the
route's JSON body or {"error": "..."} if that route couldn't be reached.

Kept separate from poller.py so preview.py (or any script) can import
`render_dashboard` without pulling in the Waveshare/SPI dependencies.
"""

import os
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

WIDTH = 800
HEIGHT = 480

# Dark mode: white ink on a black page (including the panel/title bars,
# which stay the inverse of the page either way). Flip to False for the
# original black-on-white look.
INVERTED = False
INK = 255 if INVERTED else 0
PAPER = 0 if INVERTED else 255

MARGIN = 10
HEADER_HEIGHT = 40
PANEL_GAP = 8
PANEL_PAD = 10
TITLE_BAR_HEIGHT = 26
CORNER_RADIUS = 10

_FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
_FONT_REGULAR = os.path.join(_FONT_DIR, "DejaVuSans.ttf")
_FONT_BOLD = os.path.join(_FONT_DIR, "DejaVuSans-Bold.ttf")

_ICON_DIR = os.path.join(os.path.dirname(__file__), "icons")
ICON_SIZE = 18  # fits inside TITLE_BAR_HEIGHT with a few px of padding
_icon_mask_cache = {}


class Fonts:
    def __init__(self):
        self.title = ImageFont.truetype(_FONT_BOLD, 24)
        self.panel_title = ImageFont.truetype(_FONT_BOLD, 16)
        self.headline = ImageFont.truetype(_FONT_BOLD, 20)
        self.body = ImageFont.truetype(_FONT_REGULAR, 16)
        self.small = ImageFont.truetype(_FONT_REGULAR, 14)


# --- formatting helpers ---------------------------------------------------

def _fmt_int(n):
    return f"{n:,}" if isinstance(n, (int, float)) else "—"


def _fmt_pct(p):
    return f"{p:.1f}%" if isinstance(p, (int, float)) else "—"


def _fmt_ms(v):
    return f"{v:.1f} ms" if isinstance(v, (int, float)) else "—"


def _fmt_temp(v):
    return f"{v:.1f}°C" if isinstance(v, (int, float)) else "—"


def _fmt_bytes(n):
    if not isinstance(n, (int, float)):
        return "—"
    value = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(value) < 1024 or unit == "TB":
            return f"{value:.0f}{unit}" if unit == "B" else f"{value:.1f}{unit}"
        value /= 1024
    return f"{value:.1f}TB"


def _fmt_duration(seconds):
    if not isinstance(seconds, (int, float)):
        return "—"
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def _device_label(device):
    label = device.get("hostname") or device.get("vendor") or device.get("mac", "unknown")
    ip = (device.get("ips") or [None])[0]
    return f"{label} ({ip})" if ip else label


def _truncate(draw, text, font, max_width):
    if draw.textlength(text, font=font) <= max_width:
        return text
    ellipsis = "…"
    while text and draw.textlength(text + ellipsis, font=font) > max_width:
        text = text[:-1]
    return (text + ellipsis) if text else ellipsis


# --- layout primitives -----------------------------------------------------

def _draw_header(draw, fonts):
    # Top corners stay square (flush against the physical screen edge);
    # only the bottom corners round, same as a card meeting an edge.
    draw.rounded_rectangle(
        [0, 0, WIDTH, HEADER_HEIGHT],
        radius=CORNER_RADIUS,
        corners=(False, False, True, True),
        fill=INK,
    )
    title = "LookingGlass"
    tw = draw.textlength(title, font=fonts.title)
    draw.text(((WIDTH - tw) / 2, 7), title, font=fonts.title, fill=PAPER)

    timestamp = datetime.now().strftime("%a %b %d  %H:%M")
    tw = draw.textlength(timestamp, font=fonts.body)
    draw.text((WIDTH - MARGIN - tw, 12), timestamp, font=fonts.body, fill=PAPER)


def _get_icon_mask(name, size):
    """
    Icon PNGs are black-on-transparent; the alpha channel doubles as a paste
    mask. Hard-thresholded to pure 0/255 — the base image is mode "1", and
    pasting a mask with antialiased (intermediate-gray) values onto a 1-bit
    image doesn't cleanly binarize; it leaves genuinely invalid in-between
    byte values baked into the buffer, which render as visual noise on real
    e-paper hardware instead of a solid icon.
    """
    key = (name, size)
    if key not in _icon_mask_cache:
        icon = Image.open(os.path.join(_ICON_DIR, f"{name}.png")).convert("RGBA")
        icon = icon.resize((size, size), Image.LANCZOS)
        alpha = icon.split()[-1]
        _icon_mask_cache[key] = alpha.point(lambda p: 255 if p > 127 else 0)
    return _icon_mask_cache[key]


def _paste_icon(image, name, x, y, size, tint):
    mask = _get_icon_mask(name, size)
    image.paste(Image.new("L", (size, size), tint), (x, y), mask)


ICON_PAD = 4


def _draw_corner_icon(image, box, name):
    """Bottom-right corner of the panel body. Tinted INK (not PAPER) since
    it sits on the page background, not on an INK-filled title bar."""
    _, _, x1, y1 = box
    x = x1 - ICON_PAD - ICON_SIZE
    y = y1 - ICON_PAD - ICON_SIZE
    _paste_icon(image, name, x, y, ICON_SIZE, INK)


def _draw_panel_frame(draw, box, title, fonts):
    x0, y0, x1, y1 = box
    draw.rounded_rectangle([x0, y0, x1, y1], radius=CORNER_RADIUS, outline=INK, width=2)
    draw.rounded_rectangle(
        [x0, y0, x1, y0 + TITLE_BAR_HEIGHT],
        radius=CORNER_RADIUS,
        corners=(True, True, False, False),
        fill=INK,
    )
    draw.text((x0 + PANEL_PAD, y0 + 4), title, font=fonts.panel_title, fill=PAPER)
    return x0 + PANEL_PAD, y0 + TITLE_BAR_HEIGHT + 8, x1 - PANEL_PAD


def _draw_bar(draw, x, y, width, height, fraction):
    fraction = 0.0 if not isinstance(fraction, (int, float)) else max(0.0, min(1.0, fraction))
    radius = height // 2
    draw.rounded_rectangle([x, y, x + width, y + height], radius=radius, outline=INK, width=1)
    filled = int(width * fraction)
    if filled > 0:
        # Radius can't exceed half the filled width, or PIL's rounded_rectangle
        # errors out on a box too small to fit the requested corner radius.
        fill_radius = min(radius, filled // 2)
        draw.rounded_rectangle([x, y, x + filled, y + height], radius=fill_radius, fill=INK)


def _draw_line_chart(draw, x, y, width, height, values, fonts, pad=4, floor_range=5.0):
    """Small bordered sparkline for a rolling history of percentages, most
    recent point on the right. Y-axis auto-scales to the data (floored to a
    minimum span so a near-flat history doesn't look like noisy jitter)."""
    draw.rounded_rectangle([x, y, x + width, y + height], radius=4, outline=INK, width=1)

    numeric = [v for v in (values or []) if isinstance(v, (int, float))]
    if len(numeric) < 2:
        msg = "collecting history…"
        tw = draw.textlength(msg, font=fonts.small)
        draw.text((x + (width - tw) / 2, y + (height - fonts.small.size) / 2), msg, font=fonts.small, fill=INK)
        return

    inner_x0, inner_y0 = x + pad, y + pad
    inner_x1, inner_y1 = x + width - pad, y + height - pad

    lo, hi = min(numeric), max(numeric)
    if hi - lo < floor_range:
        mid = (hi + lo) / 2
        lo, hi = mid - floor_range / 2, mid + floor_range / 2
    lo = max(0.0, lo)

    def scaled(v):
        frac = 0.5 if hi == lo else (v - lo) / (hi - lo)
        return inner_y1 - frac * (inner_y1 - inner_y0)

    step = (inner_x1 - inner_x0) / (len(numeric) - 1)
    points = [(inner_x0 + i * step, scaled(v)) for i, v in enumerate(numeric)]
    draw.line(points, fill=INK, width=2, joint="curve")


def _draw_banner(draw, x, y, right, text, font, pad=3):
    """Inverted call-out (INK fill, PAPER text) — same visual language as the panel title bars."""
    height = font.size + pad * 2
    draw.rounded_rectangle([x - pad, y - pad, right, y + height - pad], radius=CORNER_RADIUS // 2, fill=INK)
    draw.text((x, y), text, font=font, fill=PAPER)
    return y + height + 4


def _unavailable(draw, x, y, right, fonts, payload):
    message = payload.get("message") or payload.get("error", "unavailable")
    draw.text((x, y), _truncate(draw, f"Unavailable: {message}", fonts.small, right - x), font=fonts.small, fill=INK)


# --- panels ------------------------------------------------------------

def _draw_pihole_panel(image, draw, box, fonts, stats):
    x, y, right = _draw_panel_frame(draw, box, "DNS", fonts)
    _draw_corner_icon(image, box, "pihole")

    if "error" in stats:
        _unavailable(draw, x, y, right, fonts, stats)
        return

    draw.text((x, y), f"{_fmt_int(stats.get('queries_total'))} queries", font=fonts.headline, fill=INK)
    y += 26
    draw.text(
        (x, y),
        f"{_fmt_int(stats.get('queries_blocked'))} blocked ({_fmt_pct(stats.get('percent_blocked'))})",
        font=fonts.body,
        fill=INK,
    )
    y += 21
    draw.text((x, y), f"{_fmt_int(stats.get('unique_clients'))} active clients", font=fonts.body, fill=INK)
    y += 25

    anomaly = stats.get("traffic_anomaly") or {}
    is_anomaly = bool(anomaly.get("is_anomaly"))
    if is_anomaly:
        qpm = anomaly.get("queries_per_min")
        baseline = anomaly.get("baseline_qpm")
        alert = f"! Traffic spike: {qpm:.0f} vs {baseline:.0f} qpm" if qpm and baseline else "! Unusual traffic"
        y = _draw_banner(draw, x, y, right, _truncate(draw, alert, fonts.panel_title, right - x - 8), fonts.panel_title)

    draw.text((x, y), "Top blocked domains:", font=fonts.body, fill=INK)
    y += 20
    # 3 normally (leaves room for the corner icon); fewer during an active
    # alert, which also needs room for the banner above.
    domain_limit = 1 if is_anomaly else 3
    for item in (stats.get("top_blocked_domains") or [])[:domain_limit]:
        line = f"{item.get('domain', '?')} ({_fmt_int(item.get('count'))})"
        draw.text((x + 6, y), _truncate(draw, line, fonts.small, right - x - 6), font=fonts.small, fill=INK)
        y += 18


def _draw_network_panel(image, draw, box, fonts, health, new_devices):
    x, y, right = _draw_panel_frame(draw, box, "Network", fonts)
    _draw_corner_icon(image, box, "globe")

    if "error" in health:
        _unavailable(draw, x, y, right, fonts, health)
        y += 21
    else:
        ping = health.get("ping") or {}
        if "error" in ping:
            draw.text((x, y), "Ping: unavailable", font=fonts.headline, fill=INK)
            y += 26
            draw.text((x, y), _truncate(draw, ping["error"], fonts.small, right - x), font=fonts.small, fill=INK)
            y += 21
        else:
            draw.text(
                (x, y),
                f"{_fmt_ms(ping.get('rtt_avg_ms'))} avg · {_fmt_pct(ping.get('packet_loss_percent'))} loss",
                font=fonts.headline,
                fill=INK,
            )
            y += 26
            draw.text(
                (x, y),
                f"to {ping.get('host', '?')} ({_fmt_int(ping.get('packets_received'))}/"
                f"{_fmt_int(ping.get('packets_transmitted'))} received)",
                font=fonts.small,
                fill=INK,
            )
            y += 25

        external = health.get("external_ip") or {}
        if "error" in external:
            draw.text((x, y), "External IP: unavailable", font=fonts.body, fill=INK)
            y += 21
        else:
            draw.text((x, y), f"IP: {external.get('ip', '—')}", font=fonts.body, fill=INK)
            y += 21
            draw.text(
                (x, y), _truncate(draw, f"ISP: {external.get('isp', '—')}", fonts.body, right - x), font=fonts.body, fill=INK
            )
            y += 21
            location = ", ".join(filter(None, [external.get("city"), external.get("region"), external.get("country")]))
            if location:
                draw.text((x, y), _truncate(draw, location, fonts.small, right - x), font=fonts.small, fill=INK)
            y += 21

        time_sync = health.get("time_sync") or {}
        if "error" in time_sync:
            draw.text((x, y), "Time Sync: unavailable", font=fonts.small, fill=INK)
            y += 19
        elif time_sync.get("synced") is False:
            y = _draw_banner(draw, x, y, right, "! Time NOT synced", fonts.panel_title)
        elif "synced" in time_sync:
            offset = time_sync.get("offset_ms")
            label = f"Time Sync: OK ({offset:+.1f}ms)" if isinstance(offset, (int, float)) else "Time Sync: OK"
            draw.text((x, y), label, font=fonts.small, fill=INK)
            y += 19
        else:
            draw.text((x, y), "Time Sync: —", font=fonts.small, fill=INK)
            y += 19

    if new_devices is None:
        draw.text((x, y), "New devices: —", font=fonts.small, fill=INK)
    elif new_devices.get("new_count"):
        count = new_devices["new_count"]
        seen = new_devices.get("new_devices") or []
        if count == 1 and seen:
            alert = f"! New device: {_device_label(seen[0])}"
        else:
            alert = f"! New devices: {count}"
        _draw_banner(draw, x, y, right, _truncate(draw, alert, fonts.panel_title, right - x - 8), fonts.panel_title)
    else:
        draw.text((x, y), "New devices: 0", font=fonts.small, fill=INK)


def _draw_pihole_health_panel(image, draw, box, fonts, health):
    x, y, right = _draw_panel_frame(draw, box, "Pi-hole", fonts)
    _draw_corner_icon(image, box, "raspberrypi")

    if "error" in health:
        _unavailable(draw, x, y, right, fonts, health)
        return

    draw.text((x, y), f"Mem {_fmt_pct(health.get('memory_percent_used'))}", font=fonts.headline, fill=INK)
    y += 26

    load = health.get("cpu_load_percent") or []
    load_str = ", ".join(f"{v:.2f}" for v in load if isinstance(v, (int, float))) or "—"
    draw.text((x, y), f"Load (1/5/15m): {load_str}", font=fonts.body, fill=INK)
    y += 23
    draw.text((x, y), f"Uptime: {_fmt_duration(health.get('uptime_seconds'))}", font=fonts.body, fill=INK)
    y += 25

    draw.text((x, y), "Mem history:", font=fonts.small, fill=INK)
    y += 18

    _, _, _, y1 = box
    chart_bottom = y1 - ICON_PAD - ICON_SIZE - 6
    _draw_line_chart(draw, x, y, right - x, chart_bottom - y, health.get("memory_history"), fonts)


def _draw_system_panel(image, draw, box, fonts, health):
    x, y, right = _draw_panel_frame(draw, box, "Dock Zero", fonts)
    _draw_corner_icon(image, box, "cpu")

    if "error" in health:
        _unavailable(draw, x, y, right, fonts, health)
        return

    draw.text((x, y), f"CPU {_fmt_temp(health.get('cpu_temp_celsius'))}", font=fonts.headline, fill=INK)
    y += 26
    draw.text((x, y), f"Mem {_fmt_pct(health.get('memory_percent_used'))}", font=fonts.body, fill=INK)
    y += 21
    draw.text((x, y), f"Uptime: {_fmt_duration(health.get('uptime_seconds'))}", font=fonts.body, fill=INK)
    y += 25

    disk = health.get("disk") or {}
    percent_used = disk.get("percent_used")
    draw.text(
        (x, y),
        f"Disk: {_fmt_pct(percent_used)} used ({_fmt_bytes(disk.get('free_bytes'))} free)",
        font=fonts.body,
        fill=INK,
    )
    y += 21
    bar_fraction = (percent_used / 100.0) if isinstance(percent_used, (int, float)) else None
    _draw_bar(draw, x, y, right - x, 14, bar_fraction)


# --- entry point ------------------------------------------------------------

def render_dashboard(data: dict) -> Image.Image:
    image = Image.new("1", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)
    fonts = Fonts()

    _draw_header(draw, fonts)

    panel_top = HEADER_HEIGHT + PANEL_GAP
    panel_width = (WIDTH - MARGIN * 2 - PANEL_GAP) // 2
    panel_height = (HEIGHT - panel_top - MARGIN - PANEL_GAP) // 2

    left_x0 = MARGIN
    right_x0 = MARGIN + panel_width + PANEL_GAP
    right_x1 = WIDTH - MARGIN
    top_y0 = panel_top
    top_y1 = panel_top + panel_height
    bottom_y0 = top_y1 + PANEL_GAP
    bottom_y1 = bottom_y0 + panel_height

    pihole_stats = data.get("pihole_stats", {})

    _draw_pihole_panel(image, draw, (left_x0, bottom_y0, left_x0 + panel_width, bottom_y1), fonts, pihole_stats)
    _draw_network_panel(
        image,
        draw,
        (left_x0, top_y0, left_x0 + panel_width, top_y1),
        fonts,
        data.get("network_health", {}),
        pihole_stats.get("new_devices"),
    )
    _draw_pihole_health_panel(
        image, draw, (right_x0, top_y0, right_x1, top_y1), fonts, data.get("pihole_health", {})
    )
    _draw_system_panel(
        image, draw, (right_x0, bottom_y0, right_x1, bottom_y1), fonts, data.get("system_health", {})
    )

    return image
