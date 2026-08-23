"""
Persisted "have we seen this device before" tracking, keyed by MAC address
(Pi-hole's `hwaddr`, from /api/network/devices — stable across DHCP IP
changes, unlike IP). Unlike anomaly_service's in-memory tracker, this is
written to disk so it survives Flask restarts and reboots.

On the very first-ever run (no known-devices file yet), every device Pi-hole
currently knows about is seeded into the known list WITHOUT being flagged —
otherwise a brand-new install would immediately report N "new" devices for
what's actually just the existing household network.
"""

import json
import os
import tempfile
from datetime import datetime, timezone


def _load_known(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_known(path, known):
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".known_devices_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(known, f, indent=2, sort_keys=True)
        os.replace(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def check_devices(devices, known_file_path):
    """
    devices: list of {"mac": str, "vendor": str|None, "ips": [str], "hostname": str|None}
    Returns {"new_count", "new_devices", "known_count", "baseline_seeded"}.
    """
    is_first_run = not os.path.exists(known_file_path)
    known = _load_known(known_file_path)
    new_devices = []

    for device in devices:
        mac = device.get("mac")
        if not mac or mac in known:
            continue
        known[mac] = {
            "first_seen_detected_at": datetime.now(timezone.utc).isoformat(),
            "vendor": device.get("vendor"),
            "ips": device.get("ips", []),
            "hostname": device.get("hostname"),
        }
        if not is_first_run:
            new_devices.append(device)

    if is_first_run or new_devices:
        _save_known(known_file_path, known)

    return {
        "new_count": len(new_devices),
        "new_devices": new_devices,
        "known_count": len(known),
        "baseline_seeded": is_first_run,
    }
