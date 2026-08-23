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

    EXTERNAL_IP_API_URL = os.environ.get("EXTERNAL_IP_API_URL", "https://ipapi.co/json/")
    EXTERNAL_IP_TIMEOUT = float(os.environ.get("EXTERNAL_IP_TIMEOUT", "5"))
    # IP/ISP rarely change; cache to avoid hammering the free API on every poll.
    EXTERNAL_IP_CACHE_TTL = float(os.environ.get("EXTERNAL_IP_CACHE_TTL", "3600"))

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
