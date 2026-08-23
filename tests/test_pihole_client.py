from unittest.mock import MagicMock, patch

import pytest

from app.services.pihole_client import PiholeAuthError, PiholeClient


def _auth_response(sid="test-sid", validity=300, valid=True):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"session": {"valid": valid, "sid": sid, "csrf": "test-csrf", "validity": validity}}
    resp.raise_for_status = MagicMock()
    return resp


def _data_response(payload, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload
    resp.raise_for_status = MagicMock()
    return resp


@patch("app.services.pihole_client.requests.Session")
def test_authenticates_before_first_request(mock_session_cls):
    session = mock_session_cls.return_value
    session.post.return_value = _auth_response()
    session.get.return_value = _data_response({"queries": {"total": 100, "blocked": 10, "percent_blocked": 10.0}})

    client = PiholeClient(host="http://pi.hole", app_password="secret")
    result = client.get_summary()

    session.post.assert_called_once()
    assert session.get.call_args.kwargs["headers"]["sid"] == "test-sid"
    assert result["queries"]["total"] == 100


@patch("app.services.pihole_client.requests.Session")
def test_bad_app_password_raises(mock_session_cls):
    session = mock_session_cls.return_value
    session.post.return_value = _auth_response(valid=False)

    client = PiholeClient(host="http://pi.hole", app_password="wrong")
    with pytest.raises(PiholeAuthError):
        client.get_summary()


@patch("app.services.pihole_client.requests.Session")
def test_reauthenticates_on_401(mock_session_cls):
    session = mock_session_cls.return_value
    session.post.side_effect = [_auth_response(sid="sid-1"), _auth_response(sid="sid-2")]

    expired_resp = MagicMock()
    expired_resp.status_code = 401
    ok_resp = _data_response({"queries": {"total": 5}})
    session.get.side_effect = [expired_resp, ok_resp]

    client = PiholeClient(host="http://pi.hole", app_password="secret")
    result = client.get_summary()

    assert session.post.call_count == 2
    assert result["queries"]["total"] == 5
