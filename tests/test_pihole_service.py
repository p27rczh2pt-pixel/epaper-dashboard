import time
from unittest.mock import MagicMock, patch

from app import create_app
from app.services.pihole_service import get_device_list


def _make_app(active_days=30):
    app = create_app()
    app.config["DEVICE_LIST_ACTIVE_DAYS"] = active_days
    return app


@patch("app.services.pihole_service.get_client")
def test_get_device_list_filters_stale_and_missing_last_query(mock_get_client):
    now = time.time()
    mock_client = MagicMock()
    mock_client.get_devices.return_value = {
        "devices": [
            {"hwaddr": "recent", "ips": [{"ip": "1.1.1.1"}], "lastQuery": now - 3600},
            {"hwaddr": "stale", "ips": [{"ip": "1.1.1.2"}], "lastQuery": now - 40 * 86400},
            {"hwaddr": "never-queried", "ips": [{"ip": "1.1.1.3"}]},
        ]
    }
    mock_get_client.return_value = mock_client

    with _make_app().app_context():
        result = get_device_list()

    assert [d["mac"] for d in result["devices"]] == ["recent"]
    assert result["count"] == 1


@patch("app.services.pihole_service.get_client")
def test_get_device_list_sorts_most_recent_first(mock_get_client):
    now = time.time()
    mock_client = MagicMock()
    mock_client.get_devices.return_value = {
        "devices": [
            {"hwaddr": "older", "ips": [{"ip": "1.1.1.1"}], "lastQuery": now - 1000},
            {"hwaddr": "newer", "ips": [{"ip": "1.1.1.2"}], "lastQuery": now - 10},
        ]
    }
    mock_get_client.return_value = mock_client

    with _make_app().app_context():
        result = get_device_list()

    assert [d["mac"] for d in result["devices"]] == ["newer", "older"]
