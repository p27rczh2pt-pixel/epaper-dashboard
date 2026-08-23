import re
import subprocess
import time

import requests

_STATS_RE = re.compile(
    r"(?P<transmitted>\d+) packets transmitted, (?P<received>\d+) (?:packets )?received,.*?"
    r"(?P<loss>[\d.]+)% packet loss"
)
_RTT_RE = re.compile(r"rtt min/avg/max/mdev = (?P<min>[\d.]+)/(?P<avg>[\d.]+)/(?P<max>[\d.]+)/(?P<mdev>[\d.]+)")

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


def get_external_ip_info(api_url, timeout=5, cache_ttl=3600, force_refresh=False):
    now = time.monotonic()
    cached = _external_ip_cache["data"]
    if not force_refresh and cached and (now - _external_ip_cache["fetched_at"]) < cache_ttl:
        return cached

    resp = requests.get(api_url, timeout=timeout)
    resp.raise_for_status()
    payload = resp.json()

    data = {
        "ip": payload.get("ip"),
        "isp": payload.get("org"),
        "city": payload.get("city"),
        "region": payload.get("region"),
        "country": payload.get("country_name"),
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
    result = {"ping": None, "external_ip": None}

    try:
        result["ping"] = ping_host(
            app_config["NETWORK_PING_HOST"],
            count=app_config["NETWORK_PING_COUNT"],
            timeout=app_config["NETWORK_PING_TIMEOUT"],
        )
    except NetworkError as exc:
        result["ping"] = {"error": str(exc)}

    try:
        result["external_ip"] = get_external_ip_info(
            app_config["EXTERNAL_IP_API_URL"],
            timeout=app_config["EXTERNAL_IP_TIMEOUT"],
            cache_ttl=app_config["EXTERNAL_IP_CACHE_TTL"],
        )
    except requests.RequestException as exc:
        result["external_ip"] = {"error": str(exc)}

    return result
