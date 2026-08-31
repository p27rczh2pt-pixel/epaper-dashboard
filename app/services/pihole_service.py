import time

from flask import current_app

from app.services import anomaly_service, device_tracker, memory_history
from app.services.pihole_client import PiholeClient
from app.utils.data import dig


def get_client():
    """
    One PiholeClient for the lifetime of the Flask app process (scoped to
    current_app, same pattern as the *_history trackers) — NOT per-request.

    Logging in and back out of Pi-hole on every single API call (the
    previous per-request `g`-scoped behavior) burns through Pi-hole's
    concurrent-session limit under normal dashboard polling — three
    routes (stats/health/devices) hitting Pi-hole every 60s each opened
    and closed their own session, and enough churn eventually got a
    request rejected with a 429. Reusing one client lets PiholeClient's
    own _ensure_authenticated()/401-retry logic re-authenticate only when
    the session actually needs it.
    """
    if not hasattr(current_app, "_pihole_client"):
        current_app._pihole_client = PiholeClient(
            host=current_app.config["PIHOLE_HOST"],
            app_password=current_app.config["PIHOLE_APP_PASSWORD"],
            verify_tls=current_app.config["PIHOLE_VERIFY_TLS"],
            timeout=current_app.config["PIHOLE_TIMEOUT"],
        )
    return current_app._pihole_client


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


def _normalize_devices(raw):
    devices = []
    for d in dig(raw, "devices", default=[]) or []:
        mac = d.get("hwaddr")
        if not mac:
            continue
        ips = [ip.get("ip") for ip in (d.get("ips") or []) if ip.get("ip")]
        hostname = next((ip.get("name") for ip in (d.get("ips") or []) if ip.get("name")), None)
        devices.append(
            {
                "mac": mac,
                "vendor": d.get("macVendor") or None,
                "ips": ips,
                "hostname": hostname,
                # Defensive: only trust these if Pi-hole actually sent numbers,
                # so a schema drift degrades to "—" on the dashboard instead
                # of a crash (same tradeoff as get_dns_stats' dig() lookups).
                "last_query_at": d.get("lastQuery") if isinstance(d.get("lastQuery"), (int, float)) else None,
                "query_count": d.get("numQueries") if isinstance(d.get("numQueries"), (int, float)) else None,
            }
        )
    return devices


def get_new_devices():
    """
    Device inventory from /api/network/devices, diffed against the
    persisted known-devices file. Reuses the same app-lifetime PiholeClient
    (and its session) as the other functions here — no extra Pi-hole login.
    """
    client = get_client()
    devices = _normalize_devices(client.get_devices())
    return device_tracker.check_devices(devices, current_app.config["DEVICE_KNOWN_FILE"])


def get_device_list():
    """
    Device roster from /api/network/devices, filtered to devices with a
    lastQuery within DEVICE_LIST_ACTIVE_DAYS — Pi-hole's network table
    otherwise holds every device it's ever seen (via DHCP/ARP), including
    long-gone ones, which isn't what "what's on my network" should show.
    A device with no lastQuery at all is treated as stale and excluded too.
    Sorted most-recently-active first.
    """
    client = get_client()
    devices = _normalize_devices(client.get_devices())

    cutoff = time.time() - current_app.config["DEVICE_LIST_ACTIVE_DAYS"] * 86400
    devices = [d for d in devices if d["last_query_at"] and d["last_query_at"] >= cutoff]

    devices.sort(key=lambda d: d["last_query_at"], reverse=True)
    return {"devices": devices, "count": len(devices)}


def get_pihole_system_health():
    """Memory/load/uptime of the Pi-hole host itself, via /api/info/system."""
    client = get_client()
    info = client.get_system_info()
    memory_percent_used = dig(info, "system", "memory", "ram", "%used")

    return {
        "cpu_load_percent": dig(info, "system", "cpu", "load", "percent"),
        "memory_percent_used": memory_percent_used,
        "uptime_seconds": dig(info, "system", "uptime"),
        "memory_history": memory_history.get_tracker().record(memory_percent_used),
    }
