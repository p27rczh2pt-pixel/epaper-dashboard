import re
import subprocess
import time

import requests

from app.services import ping_history

_STATS_RE = re.compile(
    r"(?P<transmitted>\d+) packets transmitted, (?P<received>\d+) (?:packets )?received,.*?"
    r"(?P<loss>[\d.]+)% packet loss"
)
_RTT_RE = re.compile(r"rtt min/avg/max/mdev = (?P<min>[\d.]+)/(?P<avg>[\d.]+)/(?P<max>[\d.]+)/(?P<mdev>[\d.]+)")
_TIME_OFFSET_RE = re.compile(r"Offset:\s*(?P<value>[+-]?[\d.]+)(?P<unit>us|ms|s)\b")
_TIME_OFFSET_MS_PER_UNIT = {"us": 0.001, "ms": 1.0, "s": 1000.0}

# IP/ISP barely change; module-level cache so we don't hit the free API on
# every poll (and don't get rate-limited).
_external_ip_cache = {"data": None, "fetched_at": 0.0}


class NetworkError(Exception):
    """Raised when the ping subprocess fails to run or its output can't be parsed."""


def ping_host(host, count=5, timeout=5):
    try:
        result = subprocess.run(
            ["ping", "-c", str(count), "-W", str(max(int(timeout), 1)), host],
            capture_output=True,
            text=True,
            timeout=count * timeout + 10,
        )
    except FileNotFoundError as exc:
        raise NetworkError("ping binary not found on this system") from exc
    except subprocess.TimeoutExpired as exc:
        raise NetworkError(f"ping to {host} timed out") from exc

    stats_match = _STATS_RE.search(result.stdout)
    if not stats_match:
        raise NetworkError(f"could not parse ping output for {host}: {result.stderr.strip() or result.stdout.strip()}")

    rtt_match = _RTT_RE.search(result.stdout)

    return {
        "host": host,
        "packets_transmitted": int(stats_match.group("transmitted")),
        "packets_received": int(stats_match.group("received")),
        "packet_loss_percent": float(stats_match.group("loss")),
        "rtt_min_ms": float(rtt_match.group("min")) if rtt_match else None,
        "rtt_avg_ms": float(rtt_match.group("avg")) if rtt_match else None,
        "rtt_max_ms": float(rtt_match.group("max")) if rtt_match else None,
    }


def get_time_sync_status(timeout=5):
    """
    Uses timedatectl rather than talking to chrony/systemd-timesyncd
    directly, since timedatectl reports whichever of the two is actually
    active (the Pi runs systemd-timesyncd; chrony isn't installed) via one
    consistent interface.
    """
    try:
        synced_result = subprocess.run(
            ["timedatectl", "show", "--property=NTPSynchronized", "--value"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise NetworkError("timedatectl not found on this system") from exc
    except subprocess.TimeoutExpired as exc:
        raise NetworkError("timedatectl status check timed out") from exc

    if synced_result.returncode != 0:
        raise NetworkError(
            f"timedatectl exited {synced_result.returncode}: "
            f"{synced_result.stderr.strip() or synced_result.stdout.strip()}"
        )

    offset_ms = None
    try:
        status_result = subprocess.run(
            ["timedatectl", "timesync-status"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        match = _TIME_OFFSET_RE.search(status_result.stdout)
        if match:
            offset_ms = round(float(match.group("value")) * _TIME_OFFSET_MS_PER_UNIT[match.group("unit")], 3)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass  # offset is a nice-to-have; sync status above is the source of truth

    return {"synced": synced_result.stdout.strip() == "yes", "offset_ms": offset_ms}


def get_external_ip_info(api_url, timeout=5, cache_ttl=3600, force_refresh=False):
    """
    Expects ip-api.com's response shape ({"status": "success"|"fail", "query": ip,
    "isp", "city", "regionName", "country", ...}) — swapped from ipapi.co, whose
    free tier has a much lower daily quota and started 429ing under normal use.
    """
    now = time.monotonic()
    cached = _external_ip_cache["data"]
    if not force_refresh and cached and (now - _external_ip_cache["fetched_at"]) < cache_ttl:
        return cached

    resp = requests.get(api_url, timeout=timeout)
    resp.raise_for_status()
    payload = resp.json()

    if payload.get("status") == "fail":
        raise requests.RequestException(payload.get("message") or "external IP lookup failed")

    data = {
        "ip": payload.get("query"),
        "isp": payload.get("isp"),
        "city": payload.get("city"),
        "region": payload.get("regionName"),
        "country": payload.get("country"),
    }
    _external_ip_cache["data"] = data
    _external_ip_cache["fetched_at"] = now
    return data


def get_network_health(app_config):
    """
    Returns ping and external-IP results independently, each with its own
    `error` field on failure, so a flaky external IP API doesn't blank out
    otherwise-good ping stats (and vice versa).
    """
    result = {"ping": None, "external_ip": None, "time_sync": None}

    try:
        result["ping"] = ping_host(
            app_config["NETWORK_PING_HOST"],
            count=app_config["NETWORK_PING_COUNT"],
            timeout=app_config["NETWORK_PING_TIMEOUT"],
        )
    except NetworkError as exc:
        result["ping"] = {"error": str(exc)}

    result["ping_history"] = ping_history.get_tracker().record(
        result["ping"].get("rtt_avg_ms"),
        result["ping"].get("packet_loss_percent"),
    )

    try:
        result["time_sync"] = get_time_sync_status(timeout=app_config["TIME_SYNC_TIMEOUT"])
    except NetworkError as exc:
        result["time_sync"] = {"error": str(exc)}

    try:
        result["external_ip"] = get_external_ip_info(
            app_config["EXTERNAL_IP_API_URL"],
            timeout=app_config["EXTERNAL_IP_TIMEOUT"],
            cache_ttl=app_config["EXTERNAL_IP_CACHE_TTL"],
        )
    except requests.RequestException as exc:
        result["external_ip"] = {"error": str(exc)}

    return result
