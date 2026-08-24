from unittest.mock import MagicMock, patch

import pytest
import requests

from app.services import network_service
from app.services.network_service import NetworkError, get_network_health, ping_host

PING_OUTPUT_OK = """PING 1.1.1.1 (1.1.1.1) 56(84) bytes of data.
64 bytes from 1.1.1.1: icmp_seq=1 ttl=59 time=12.3 ms
64 bytes from 1.1.1.1: icmp_seq=2 ttl=59 time=11.9 ms

--- 1.1.1.1 ping statistics ---
2 packets transmitted, 2 received, 0% packet loss, time 1001ms
rtt min/avg/max/mdev = 11.900/12.100/12.300/0.200 ms
"""

PING_OUTPUT_LOSS = """PING 1.1.1.1 (1.1.1.1) 56(84) bytes of data.

--- 1.1.1.1 ping statistics ---
5 packets transmitted, 0 received, 100% packet loss, time 4089ms
"""

TIMESYNC_STATUS_OUTPUT = """       Server: 74.208.90.90 (2.debian.pool.ntp.org)
Poll interval: 34min 8s (min: 32s; max 34min 8s)
         Leap: normal
      Version: 4
      Stratum: 3
    Reference: D8E50445
    Precision: 1us (-21)
Root distance: 36.796ms (max: 5s)
       Offset: +1.329ms
        Delay: 26.688ms
       Jitter: 17.275ms
 Packet count: 19
    Frequency: -2.245ppm
"""


@pytest.fixture(autouse=True)
def _reset_ip_cache():
    network_service._external_ip_cache.update({"data": None, "fetched_at": 0.0})
    yield
    network_service._external_ip_cache.update({"data": None, "fetched_at": 0.0})


@patch("app.services.network_service.subprocess.run")
def test_ping_host_parses_success(mock_run):
    mock_run.return_value = MagicMock(stdout=PING_OUTPUT_OK, stderr="", returncode=0)

    result = ping_host("1.1.1.1", count=2, timeout=5)

    assert result["packets_transmitted"] == 2
    assert result["packets_received"] == 2
    assert result["packet_loss_percent"] == 0.0
    assert result["rtt_avg_ms"] == 12.1


@patch("app.services.network_service.subprocess.run")
def test_ping_host_parses_full_loss_without_rtt_line(mock_run):
    mock_run.return_value = MagicMock(stdout=PING_OUTPUT_LOSS, stderr="", returncode=1)

    result = ping_host("1.1.1.1", count=5, timeout=5)

    assert result["packet_loss_percent"] == 100.0
    assert result["rtt_avg_ms"] is None


@patch("app.services.network_service.subprocess.run", side_effect=FileNotFoundError)
def test_ping_host_missing_binary_raises(mock_run):
    with pytest.raises(NetworkError):
        ping_host("1.1.1.1")


@patch("app.services.network_service.subprocess.run")
def test_get_time_sync_status_synced_with_offset(mock_run):
    mock_run.side_effect = [
        MagicMock(stdout="yes\n", stderr="", returncode=0),
        MagicMock(stdout=TIMESYNC_STATUS_OUTPUT, stderr="", returncode=0),
    ]

    result = network_service.get_time_sync_status()

    assert result == {"synced": True, "offset_ms": 1.329}


@patch("app.services.network_service.subprocess.run")
def test_get_time_sync_status_not_synced(mock_run):
    mock_run.side_effect = [
        MagicMock(stdout="no\n", stderr="", returncode=0),
        MagicMock(stdout="", stderr="", returncode=1),
    ]

    result = network_service.get_time_sync_status()

    assert result["synced"] is False


@patch("app.services.network_service.subprocess.run", side_effect=FileNotFoundError)
def test_get_time_sync_status_missing_binary_raises(mock_run):
    with pytest.raises(NetworkError):
        network_service.get_time_sync_status()


@patch("app.services.network_service.requests.get")
def test_external_ip_info_is_cached(mock_get):
    mock_get.return_value = MagicMock(
        json=lambda: {
            "status": "success",
            "query": "1.2.3.4",
            "isp": "Example ISP",
            "city": "Nowhere",
            "regionName": "Nowhereland",
            "country": "US",
        }
    )
    mock_get.return_value.raise_for_status = MagicMock()

    first = network_service.get_external_ip_info("http://fake", timeout=5, cache_ttl=3600)
    second = network_service.get_external_ip_info("http://fake", timeout=5, cache_ttl=3600)

    assert first == second
    assert first["ip"] == "1.2.3.4"
    assert first["isp"] == "Example ISP"
    mock_get.assert_called_once()


@patch("app.services.network_service.requests.get")
def test_external_ip_info_status_fail_raises(mock_get):
    mock_get.return_value = MagicMock(json=lambda: {"status": "fail", "message": "private range"})
    mock_get.return_value.raise_for_status = MagicMock()

    with pytest.raises(requests.RequestException):
        network_service.get_external_ip_info("http://fake", timeout=5, cache_ttl=3600)


@patch("app.services.network_service.requests.get", side_effect=requests.RequestException("boom"))
@patch("app.services.network_service.subprocess.run")
def test_get_network_health_reports_partial_failure(mock_run, mock_get):
    mock_run.return_value = MagicMock(stdout=PING_OUTPUT_OK, stderr="", returncode=0)

    config = {
        "NETWORK_PING_HOST": "1.1.1.1",
        "NETWORK_PING_COUNT": 2,
        "NETWORK_PING_TIMEOUT": 5,
        "TIME_SYNC_TIMEOUT": 5,
        "EXTERNAL_IP_API_URL": "http://fake",
        "EXTERNAL_IP_TIMEOUT": 5,
        "EXTERNAL_IP_CACHE_TTL": 3600,
    }

    result = get_network_health(config)

    assert result["ping"]["packet_loss_percent"] == 0.0
    assert "error" in result["external_ip"]
