from flask import current_app, g

from app.services import anomaly_service, device_tracker
from app.services.pihole_client import PiholeClient
from app.utils.data import dig


def get_client():
    """
    One PiholeClient per app-context (Flask `g`), so the same session/sid
    gets reused across the handful of calls a single request makes.
    """
    if "pihole_client" not in g:
        g.pihole_client = PiholeClient(
            host=current_app.config["PIHOLE_HOST"],
            app_password=current_app.config["PIHOLE_APP_PASSWORD"],
            verify_tls=current_app.config["PIHOLE_VERIFY_TLS"],
            timeout=current_app.config["PIHOLE_TIMEOUT"],
        )
    return g.pihole_client


def get_dns_stats(top_n=5):
    """
    Normalized DNS stats: totals, block rate, top blocked domains, top clients.

    NOTE: field names below match the Pi-hole v6 API as documented at
    <your-pihole-host>/api/docs at time of writing. If your Pi-hole version
    drifts, check that page and adjust the `dig(...)` paths here — the
    defensive lookups mean a schema change degrades to `None` fields
    instead of a crash.
    """
    client = get_client()
    summary = client.get_summary()
    top_domains = client.get_top_domains(blocked=True, count=top_n)
    top_clients = client.get_top_clients(count=top_n)

    queries_total = dig(summary, "queries", "total")

    return {
        "queries_total": queries_total,
        "queries_blocked": dig(summary, "queries", "blocked"),
        "percent_blocked": dig(summary, "queries", "percent_blocked"),
        "unique_clients": dig(summary, "clients", "active"),
        "top_blocked_domains": [
            {"domain": d.get("domain"), "count": d.get("count")}
            for d in (dig(top_domains, "domains", default=[]) or [])[:top_n]
        ],
        "top_clients": [
            {"client": c.get("name") or c.get("ip"), "count": c.get("count")}
            for c in (dig(top_clients, "clients", default=[]) or [])[:top_n]
        ],
        "traffic_anomaly": anomaly_service.get_tracker().evaluate(queries_total),
    }


def get_new_devices():
    """
    Device inventory from /api/network/devices, diffed against the
    persisted known-devices file. Reuses the same per-request PiholeClient
    (and its session) as get_dns_stats() when called within the same
    request — no extra Pi-hole login.
    """
    client = get_client()
    raw = client.get_devices()

    devices = []
    for d in dig(raw, "devices", default=[]) or []:
        mac = d.get("hwaddr")
        if not mac:
            continue
        ips = [ip.get("ip") for ip in (d.get("ips") or []) if ip.get("ip")]
        hostname = next((ip.get("name") for ip in (d.get("ips") or []) if ip.get("name")), None)
        devices.append({"mac": mac, "vendor": d.get("macVendor") or None, "ips": ips, "hostname": hostname})

    return device_tracker.check_devices(devices, current_app.config["DEVICE_KNOWN_FILE"])


def get_pihole_system_health():
    """Memory/load/uptime of the Pi-hole host itself, via /api/info/system."""
    client = get_client()
    info = client.get_system_info()

    return {
        "cpu_load_percent": dig(info, "system", "cpu", "load", "percent"),
        "memory_percent_used": dig(info, "system", "memory", "ram", "%used"),
        "uptime_seconds": dig(info, "system", "uptime"),
    }


def close_client(exception=None):
    client = g.pop("pihole_client", None)
    if client is not None:
        client.close()
