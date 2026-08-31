import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Config:
    # Pi-hole (v6 API)
    PIHOLE_HOST = os.environ.get("PIHOLE_HOST", "http://pi.hole")
    PIHOLE_APP_PASSWORD = os.environ.get("PIHOLE_APP_PASSWORD", "")
    PIHOLE_VERIFY_TLS = os.environ.get("PIHOLE_VERIFY_TLS", "true").lower() == "true"
    PIHOLE_TIMEOUT = float(os.environ.get("PIHOLE_TIMEOUT", "5"))

    # Network health
    NETWORK_PING_HOST = os.environ.get("NETWORK_PING_HOST", "1.1.1.1")
    NETWORK_PING_COUNT = int(os.environ.get("NETWORK_PING_COUNT", "5"))
    NETWORK_PING_TIMEOUT = float(os.environ.get("NETWORK_PING_TIMEOUT", "5"))
    TIME_SYNC_TIMEOUT = float(os.environ.get("TIME_SYNC_TIMEOUT", "5"))

    # Ping latency/loss history, for the Network page's rolling chart (see
    # app/services/ping_history.py). Sampled once per dashboard background
    # refresh (60s, see dashboard.html) rather than on a fixed schedule —
    # there's no separate poller process anymore, so 60 samples covers
    # roughly the past hour AS LONG AS the dashboard page stays open and
    # polling; history stalls (doesn't backfill) while nothing is viewing it.
    NETWORK_PING_HISTORY_SIZE = int(os.environ.get("NETWORK_PING_HISTORY_SIZE", "60"))

    # ip-api.com's free tier (~45 req/min, no key) — swapped from ipapi.co,
    # whose free daily quota was getting exhausted and 429ing. No HTTPS on
    # the free tier; the payload is just public IP geolocation, not sensitive.
    EXTERNAL_IP_API_URL = os.environ.get("EXTERNAL_IP_API_URL", "http://ip-api.com/json/")
    EXTERNAL_IP_TIMEOUT = float(os.environ.get("EXTERNAL_IP_TIMEOUT", "5"))
    # IP/ISP rarely change; cache well beyond the poll interval since the free
    # API (ipapi.co) has a low daily quota and returns 429s once it's hit.
    EXTERNAL_IP_CACHE_TTL = float(os.environ.get("EXTERNAL_IP_CACHE_TTL", "86400"))

    # Pi Zero's own system health
    SYSTEM_DISK_PATH = os.environ.get("SYSTEM_DISK_PATH", "/")

    # Query rate anomaly detection (see app/services/anomaly_service.py)
    ANOMALY_HISTORY_SIZE = int(os.environ.get("ANOMALY_HISTORY_SIZE", "12"))
    ANOMALY_MULTIPLIER = float(os.environ.get("ANOMALY_MULTIPLIER", "3.0"))
    ANOMALY_MIN_QPM = float(os.environ.get("ANOMALY_MIN_QPM", "5.0"))
    ANOMALY_MIN_SAMPLES = int(os.environ.get("ANOMALY_MIN_SAMPLES", "3"))

    # New device detection (see app/services/device_tracker.py) — persisted
    # to disk (not in-memory) so it survives Flask restarts/reboots.
    DEVICE_KNOWN_FILE = os.environ.get("DEVICE_KNOWN_FILE", os.path.join(BASE_DIR, "data", "known_devices.json"))

    # Devices page (see pihole_service.get_device_list): only show devices
    # with query activity within this many days, so the list reflects
    # what's actually still on the network instead of everything Pi-hole's
    # network table has ever recorded.
    DEVICE_LIST_ACTIVE_DAYS = int(os.environ.get("DEVICE_LIST_ACTIVE_DAYS", "30"))

    # Pi-hole memory usage history, for the dashboard's sparkline (see
    # app/services/memory_history.py). Sampled once per dashboard background
    # refresh (60s) — there's no separate poller process anymore — so 540
    # samples covers roughly the past 9 hours, matching the window this
    # sparkline was originally designed around.
    PIHOLE_MEM_HISTORY_SIZE = int(os.environ.get("PIHOLE_MEM_HISTORY_SIZE", "540"))

    # Pi Zero disk usage history, for the dashboard's sparkline (see
    # app/services/disk_history.py). Same window as PIHOLE_MEM_HISTORY_SIZE.
    DISK_HISTORY_SIZE = int(os.environ.get("DISK_HISTORY_SIZE", "540"))
