"""Tests for Syncthing API client."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

import aiohttp

from custom_components.syncthing_extended.api import (
    SyncthingApi,
    SyncthingApiError,
    SyncthingAuthError,
    SyncthingConnectionError,
    SyncthingSslError,
)

BASE_URL = "https://192.168.1.1:8384"


def make_api(session: MagicMock) -> SyncthingApi:
    return SyncthingApi(
        host="192.168.1.1",
        port=8384,
        api_key="test-api-key",
        verify_ssl=False,
        session=session,
    )


def make_mock_response(
    status: int, json_data: dict | None = None, text: str = ""
) -> MagicMock:
    resp = MagicMock()
    resp.status = status
    resp.content_type = "application/json" if json_data is not None else "text/plain"
    resp.json = AsyncMock(return_value=json_data or {})
    resp.text = AsyncMock(return_value=text)
    resp.raise_for_status = MagicMock()
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    return resp


def _text_response() -> MagicMock:
    resp = make_mock_response(200, None, text="")
    resp.content_type = "text/plain"
    return resp


def _run_with_session(resp_or_side_effect, coro_factory):
    session = MagicMock()
    if isinstance(resp_or_side_effect, Exception):
        session.request = MagicMock(side_effect=resp_or_side_effect)
    elif callable(resp_or_side_effect) and not isinstance(resp_or_side_effect, MagicMock):
        session.request = MagicMock(side_effect=resp_or_side_effect)
    else:
        session.request = MagicMock(return_value=resp_or_side_effect)
    api = make_api(session)
    result = asyncio.run(coro_factory(api))
    return session, result


def _assert_request(session: MagicMock, method: str, endpoint: str, **extra) -> None:
    """Assert session.request was called once with the expected method + URL + kwargs."""
    assert session.request.call_count == 1, (
        f"Expected 1 request, got {session.request.call_count}"
    )
    call = session.request.call_args
    # positional: (method, url)
    assert call.args[0] == method, f"Method: expected {method}, got {call.args[0]}"
    assert call.args[1] == f"{BASE_URL}{endpoint}", (
        f"URL: expected {BASE_URL}{endpoint}, got {call.args[1]}"
    )
    # Auth header always present on authenticated requests
    headers = call.kwargs.get("headers", {})
    if extra.pop("authenticated", True):
        assert headers.get("X-API-Key") == "test-api-key", (
            f"Missing/wrong X-API-Key header: {headers}"
        )
    for key, expected in extra.items():
        assert call.kwargs.get(key) == expected, (
            f"kwargs[{key}]: expected {expected}, got {call.kwargs.get(key)}"
        )


# --- check_health ---

def test_check_health_ok_returns_true_and_no_auth_header():
    session, result = _run_with_session(
        make_mock_response(200, {"status": "OK"}),
        lambda api: api.check_health(),
    )
    assert result is True
    # check_health is unauthenticated → no X-API-Key header
    call = session.request.call_args
    assert call.args[0] == "GET"
    assert call.args[1] == f"{BASE_URL}/rest/noauth/health"
    assert call.kwargs["headers"] == {}


def test_check_health_connection_error_returns_false():
    _, result = _run_with_session(
        aiohttp.ClientConnectorError(MagicMock(), MagicMock()),
        lambda api: api.check_health(),
    )
    assert result is False


def test_check_health_bad_status_returns_false():
    _, result = _run_with_session(
        make_mock_response(200, {"status": "NOT_OK"}),
        lambda api: api.check_health(),
    )
    assert result is False


def test_check_health_missing_status_key_returns_false():
    _, result = _run_with_session(
        make_mock_response(200, {"something_else": "value"}),
        lambda api: api.check_health(),
    )
    assert result is False


def test_check_health_non_dict_body_returns_false():
    _, result = _run_with_session(
        make_mock_response(200, None, text="plaintext"),
        lambda api: api.check_health(),
    )
    assert result is False


def test_check_health_ssl_error_propagates():
    with pytest.raises(SyncthingSslError, match="SSL certificate verification failed"):
        _run_with_session(
            aiohttp.ClientSSLError(MagicMock(), MagicMock()),
            lambda api: api.check_health(),
        )


# --- Auth / error classification ---

def test_auth_error_403_raises_with_status_in_message():
    with pytest.raises(SyncthingAuthError, match=r"HTTP 403"):
        _run_with_session(
            make_mock_response(403),
            lambda api: api.get_version(),
        )


def test_auth_error_401_raises_with_status_in_message():
    with pytest.raises(SyncthingAuthError, match=r"HTTP 401"):
        _run_with_session(
            make_mock_response(401),
            lambda api: api.get_system_status(),
        )


def test_connection_error_wraps_with_host_port():
    with pytest.raises(SyncthingConnectionError, match=r"192\.168\.1\.1:8384"):
        _run_with_session(
            aiohttp.ClientConnectorError(MagicMock(), MagicMock()),
            lambda api: api.get_version(),
        )


def test_ssl_error_wraps_with_host_port():
    with pytest.raises(SyncthingSslError, match=r"192\.168\.1\.1:8384"):
        _run_with_session(
            aiohttp.ClientSSLError(MagicMock(), MagicMock()),
            lambda api: api.get_version(),
        )


def test_generic_client_error_wraps_as_api_error():
    with pytest.raises(SyncthingApiError, match=r"Request failed"):
        _run_with_session(
            aiohttp.ClientError("boom"),
            lambda api: api.get_version(),
        )


# --- GET endpoints: verify URL + returned body ---

def test_get_version_returns_data_and_calls_correct_endpoint():
    from tests.conftest import MOCK_VERSION

    session, result = _run_with_session(
        make_mock_response(200, MOCK_VERSION),
        lambda api: api.get_version(),
    )
    assert result["version"] == "v1.29.0"
    assert result["os"] == "linux"
    _assert_request(session, "GET", "/rest/system/version", params=None, json=None)


def test_get_system_status_hits_correct_endpoint():
    from tests.conftest import MOCK_SYSTEM_STATUS

    session, result = _run_with_session(
        make_mock_response(200, MOCK_SYSTEM_STATUS),
        lambda api: api.get_system_status(),
    )
    assert result["myID"] == MOCK_SYSTEM_STATUS["myID"]
    _assert_request(session, "GET", "/rest/system/status")


def test_get_connections_returns_data_and_hits_endpoint():
    from tests.conftest import MOCK_CONNECTIONS

    session, result = _run_with_session(
        make_mock_response(200, MOCK_CONNECTIONS),
        lambda api: api.get_connections(),
    )
    assert result["total"]["inBytesTotal"] == 2048000
    _assert_request(session, "GET", "/rest/system/connections")


def test_get_config_devices_returns_list_with_expected_device():
    from tests.conftest import MOCK_CONFIG_DEVICES

    session, result = _run_with_session(
        make_mock_response(200, MOCK_CONFIG_DEVICES),
        lambda api: api.get_config_devices(),
    )
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["deviceID"] == MOCK_CONFIG_DEVICES[0]["deviceID"]
    _assert_request(session, "GET", "/rest/config/devices")


def test_get_config_folders_returns_list_with_expected_ids():
    from tests.conftest import MOCK_CONFIG_FOLDERS

    session, result = _run_with_session(
        make_mock_response(200, MOCK_CONFIG_FOLDERS),
        lambda api: api.get_config_folders(),
    )
    assert [f["id"] for f in result] == ["abcd-1234", "efgh-5678"]
    _assert_request(session, "GET", "/rest/config/folders")


def test_get_folder_status_passes_folder_id_as_param():
    session, _ = _run_with_session(
        make_mock_response(200, {"state": "idle"}),
        lambda api: api.get_folder_status("abcd-1234"),
    )
    _assert_request(
        session, "GET", "/rest/db/status", params={"folder": "abcd-1234"}, json=None
    )


def test_get_folder_completion_returns_data_and_uses_folder_param():
    session, result = _run_with_session(
        make_mock_response(200, {"completion": 99.9}),
        lambda api: api.get_folder_completion("abcd-1234"),
    )
    assert result["completion"] == pytest.approx(99.9)
    _assert_request(
        session, "GET", "/rest/db/completion", params={"folder": "abcd-1234"}
    )


def test_get_folder_completion_with_device_id_includes_device_param():
    session, result = _run_with_session(
        make_mock_response(200, {"completion": 80.0}),
        lambda api: api.get_folder_completion("abcd-1234", device_id="DEV123"),
    )
    assert result["completion"] == pytest.approx(80.0)
    _assert_request(
        session,
        "GET",
        "/rest/db/completion",
        params={"folder": "abcd-1234", "device": "DEV123"},
    )


def test_get_folder_errors_returns_data_and_passes_folder_id():
    session, result = _run_with_session(
        make_mock_response(200, {"errors": [{"path": "foo", "error": "bar"}]}),
        lambda api: api.get_folder_errors("abcd-1234"),
    )
    assert result["errors"][0]["path"] == "foo"
    _assert_request(
        session, "GET", "/rest/folder/errors", params={"folder": "abcd-1234"}
    )


def test_get_device_stats_returns_data_with_expected_device():
    from tests.conftest import MOCK_DEVICE_STATS

    session, result = _run_with_session(
        make_mock_response(200, MOCK_DEVICE_STATS),
        lambda api: api.get_device_stats(),
    )
    dev_id = next(iter(MOCK_DEVICE_STATS))
    assert result[dev_id]["lastSeen"] == "2024-01-01T11:59:00Z"
    _assert_request(session, "GET", "/rest/stats/device")


def test_get_folder_stats_returns_data_with_expected_folder():
    from tests.conftest import MOCK_FOLDER_STATS

    session, result = _run_with_session(
        make_mock_response(200, MOCK_FOLDER_STATS),
        lambda api: api.get_folder_stats(),
    )
    assert result["abcd-1234"]["lastFile"]["filename"] == "documents/report.pdf"
    _assert_request(session, "GET", "/rest/stats/folder")


# --- POST action endpoints: verify method + URL + params ---

def test_scan_folder_success_posts_with_folder_param():
    session, result = _run_with_session(
        _text_response(), lambda api: api.scan_folder("abcd-1234")
    )
    assert result is True
    _assert_request(
        session, "POST", "/rest/db/scan", params={"folder": "abcd-1234"}, json=None
    )


def test_scan_folder_returns_false_on_error():
    _, result = _run_with_session(
        aiohttp.ClientError("error"), lambda api: api.scan_folder("abcd-1234")
    )
    assert result is False


def test_scan_all_folders_success_posts_without_params():
    session, result = _run_with_session(
        _text_response(), lambda api: api.scan_all_folders()
    )
    assert result is True
    _assert_request(session, "POST", "/rest/db/scan", params=None, json=None)


def test_scan_all_folders_returns_false_on_error():
    _, result = _run_with_session(
        aiohttp.ClientError("error"), lambda api: api.scan_all_folders()
    )
    assert result is False


def test_pause_device_success_posts_with_device_param():
    session, result = _run_with_session(
        _text_response(), lambda api: api.pause_device("DEV123")
    )
    assert result is True
    _assert_request(
        session, "POST", "/rest/system/pause", params={"device": "DEV123"}, json=None
    )


def test_pause_device_returns_false_on_error():
    _, result = _run_with_session(
        aiohttp.ClientError("error"), lambda api: api.pause_device("DEV123")
    )
    assert result is False


def test_resume_device_success_posts_with_device_param():
    session, result = _run_with_session(
        _text_response(), lambda api: api.resume_device("DEV123")
    )
    assert result is True
    _assert_request(
        session, "POST", "/rest/system/resume", params={"device": "DEV123"}, json=None
    )


def test_resume_device_returns_false_on_error():
    _, result = _run_with_session(
        aiohttp.ClientError("error"), lambda api: api.resume_device("DEV123")
    )
    assert result is False


def test_pause_all_success_posts_without_params():
    session, result = _run_with_session(
        _text_response(), lambda api: api.pause_all()
    )
    assert result is True
    _assert_request(session, "POST", "/rest/system/pause", params=None, json=None)


def test_pause_all_returns_false_on_error():
    _, result = _run_with_session(
        aiohttp.ClientError("error"), lambda api: api.pause_all()
    )
    assert result is False


def test_resume_all_success_posts_without_params():
    session, result = _run_with_session(
        _text_response(), lambda api: api.resume_all()
    )
    assert result is True
    _assert_request(session, "POST", "/rest/system/resume", params=None, json=None)


def test_resume_all_returns_false_on_error():
    _, result = _run_with_session(
        aiohttp.ClientError("error"), lambda api: api.resume_all()
    )
    assert result is False


def test_pause_folder_success_patches_with_body_true():
    session, result = _run_with_session(
        _text_response(), lambda api: api.pause_folder("abcd-1234")
    )
    assert result is True
    _assert_request(
        session,
        "PATCH",
        "/rest/config/folders/abcd-1234",
        params=None,
        json={"paused": True},
    )


def test_pause_folder_returns_false_on_error():
    _, result = _run_with_session(
        aiohttp.ClientError("Connection failed"),
        lambda api: api.pause_folder("abcd-1234"),
    )
    assert result is False


def test_resume_folder_success_patches_with_body_false():
    session, result = _run_with_session(
        _text_response(), lambda api: api.resume_folder("abcd-1234")
    )
    assert result is True
    _assert_request(
        session,
        "PATCH",
        "/rest/config/folders/abcd-1234",
        params=None,
        json={"paused": False},
    )


def test_resume_folder_returns_false_on_error():
    _, result = _run_with_session(
        aiohttp.ClientError("Connection failed"),
        lambda api: api.resume_folder("abcd-1234"),
    )
    assert result is False


# --- base_url construction ---

def test_base_url_http_when_ssl_disabled():
    api = SyncthingApi("myhost", 8384, "key", use_ssl=False)
    assert api.base_url == "http://myhost:8384"


def test_base_url_https_when_ssl_enabled():
    api = SyncthingApi("myhost", 8384, "key", use_ssl=True)
    assert api.base_url == "https://myhost:8384"
