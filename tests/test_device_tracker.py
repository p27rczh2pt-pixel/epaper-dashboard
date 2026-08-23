import json

from app.services.device_tracker import check_devices

DEVICE_A = {"mac": "aa:aa:aa:aa:aa:aa", "vendor": "Roku, Inc", "ips": ["192.168.1.10"], "hostname": None}
DEVICE_B = {"mac": "bb:bb:bb:bb:bb:bb", "vendor": "Amazon Technologies Inc.", "ips": ["192.168.1.11"], "hostname": None}


def test_first_run_seeds_baseline_without_flagging(tmp_path):
    known_file = tmp_path / "known_devices.json"

    result = check_devices([DEVICE_A, DEVICE_B], str(known_file))

    assert result["baseline_seeded"] is True
    assert result["new_count"] == 0
    assert result["new_devices"] == []
    assert result["known_count"] == 2
    assert known_file.exists()

    saved = json.loads(known_file.read_text())
    assert set(saved.keys()) == {DEVICE_A["mac"], DEVICE_B["mac"]}


def test_previously_unseen_device_is_flagged_once_then_not_again(tmp_path):
    known_file = tmp_path / "known_devices.json"
    check_devices([DEVICE_A], str(known_file))  # seed baseline with only A

    result = check_devices([DEVICE_A, DEVICE_B], str(known_file))  # B shows up
    assert result["baseline_seeded"] is False
    assert result["new_count"] == 1
    assert result["new_devices"] == [DEVICE_B]
    assert result["known_count"] == 2

    result2 = check_devices([DEVICE_A, DEVICE_B], str(known_file))  # B seen again
    assert result2["new_count"] == 0
    assert result2["new_devices"] == []


def test_device_missing_from_current_poll_is_not_forgotten(tmp_path):
    known_file = tmp_path / "known_devices.json"
    check_devices([DEVICE_A, DEVICE_B], str(known_file))  # baseline with both

    result = check_devices([DEVICE_A], str(known_file))  # B temporarily offline
    assert result["new_count"] == 0
    assert result["known_count"] == 2  # B still remembered, not purged

    result2 = check_devices([DEVICE_A, DEVICE_B], str(known_file))  # B comes back
    assert result2["new_count"] == 0  # not re-flagged just for reappearing


def test_devices_without_mac_are_ignored(tmp_path):
    known_file = tmp_path / "known_devices.json"
    no_mac = {"mac": None, "vendor": None, "ips": ["192.168.1.99"], "hostname": None}

    result = check_devices([no_mac], str(known_file))

    assert result["known_count"] == 0
    assert result["new_count"] == 0


def test_corrupt_known_file_is_treated_as_empty(tmp_path):
    known_file = tmp_path / "known_devices.json"
    known_file.write_text("{not valid json")

    result = check_devices([DEVICE_A], str(known_file))

    # File existed but was unreadable — not treated as a fresh "first run",
    # so this recovers by treating it as an empty known-list (which means
    # DEVICE_A gets (re-)flagged as new) rather than crashing.
    assert result["baseline_seeded"] is False
    assert result["new_count"] == 1
    assert result["known_count"] == 1
    assert json.loads(known_file.read_text())  # overwritten with valid JSON now
