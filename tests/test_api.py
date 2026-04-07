"""Tests for Syncthing API client."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

import aiohttp

from custom_components.syncthing.api import (
    SyncthingApi,
    SyncthingApiError,
    SyncthingAuthError,
    SyncthingConnectionError,
    SyncthingSslError,
)


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


# --- Tests ---

def test_check_health_ok():
    async def _run():
        session = MagicMock()
        resp = make_mock_response(200, {"status": "OK"})
        session.request = MagicMock(return_value=resp)
        api = make_api(session)
        return await api.check_health()

    assert asyncio.run(_run()) is True


def test_check_health_connection_error():
    async def _run():
        session = MagicMock()
        session.request = MagicMock(
            side_effect=aiohttp.ClientConnectorError(MagicMock(), MagicMock())
        )
        api = make_api(session)
        return await api.check_health()

    assert asyncio.run(_run()) is False


def test_check_health_bad_status():
    async def _run():
        session = MagicMock()
        resp = make_mock_response(200, {"status": "NOT_OK"})
        session.request = MagicMock(return_value=resp)
        api = make_api(session)
        return await api.check_health()

    assert asyncio.run(_run()) is False


def test_auth_error_403():
    async def _run():
        session = MagicMock()
        resp = make_mock_response(403)
        session.request = MagicMock(return_value=resp)
        api = make_api(session)
        await api.get_version()

    try:
        asyncio.run(_run())
        assert False, "Expected SyncthingAuthError"
    except SyncthingAuthError:
        pass


def test_auth_error_401():
    async def _run():
        session = MagicMock()
        resp = make_mock_response(401)
        session.request = MagicMock(return_value=resp)
        api = make_api(session)
        await api.get_system_status()

    try:
        asyncio.run(_run())
        assert False, "Expected SyncthingAuthError"
    except SyncthingAuthError:
        pass


def test_connection_error_propagates():
    async def _run():
        session = MagicMock()
        session.request = MagicMock(
            side_effect=aiohttp.ClientConnectorError(MagicMock(), MagicMock())
        )
        api = make_api(session)
        await api.get_version()

    try:
        asyncio.run(_run())
        assert False, "Expected SyncthingConnectionError"
    except SyncthingConnectionError:
        pass


def test_get_version_returns_data():
    from tests.conftest import MOCK_VERSION

    async def _run():
        session = MagicMock()
        resp = make_mock_response(200, MOCK_VERSION)
        session.request = MagicMock(return_value=resp)
        api = make_api(session)
        return await api.get_version()

    result = asyncio.run(_run())
    assert result["version"] == "v1.29.0"
    assert result["os"] == "linux"


def test_get_folder_status_passes_folder_id():
    async def _run():
        session = MagicMock()
        resp = make_mock_response(200, {"state": "idle"})
        session.request = MagicMock(return_value=resp)
        api = make_api(session)
        await api.get_folder_status("abcd-1234")
        return session.request.call_args

    call_kwargs = asyncio.run(_run())
    assert call_kwargs.kwargs["params"] == {"folder": "abcd-1234"}


def test_scan_folder_returns_true_on_success():
    async def _run():
        session = MagicMock()
        resp = make_mock_response(200, None, text="")
        resp.content_type = "text/plain"
        session.request = MagicMock(return_value=resp)
        api = make_api(session)
        return await api.scan_folder("abcd-1234")

    assert asyncio.run(_run()) is True


def test_scan_folder_returns_false_on_error():
    async def _run():
        session = MagicMock()
        session.request = MagicMock(side_effect=aiohttp.ClientError("error"))
        api = make_api(session)
        return await api.scan_folder("abcd-1234")

    assert asyncio.run(_run()) is False


def test_base_url_http():
    api = SyncthingApi("myhost", 8384, "key", use_ssl=False)
    assert api.base_url == "http://myhost:8384"


def test_base_url_https():
    api = SyncthingApi("myhost", 8384, "key", use_ssl=True)
    assert api.base_url == "https://myhost:8384"


def test_get_connections_returns_data():
    from tests.conftest import MOCK_CONNECTIONS

    async def _run():
        session = MagicMock()
        resp = make_mock_response(200, MOCK_CONNECTIONS)
        session.request = MagicMock(return_value=resp)
        api = make_api(session)
        return await api.get_connections()

    result = asyncio.run(_run())
    assert result["total"]["inBytesTotal"] == 2048000


def test_get_config_devices_returns_list():
    from tests.conftest import MOCK_CONFIG_DEVICES

    async def _run():
        session = MagicMock()
        resp = make_mock_response(200, MOCK_CONFIG_DEVICES)
        session.request = MagicMock(return_value=resp)
        api = make_api(session)
        return await api.get_config_devices()

    result = asyncio.run(_run())
    assert isinstance(result, list)


def test_get_config_folders_returns_list():
    from tests.conftest import MOCK_CONFIG_FOLDERS

    async def _run():
        session = MagicMock()
        resp = make_mock_response(200, MOCK_CONFIG_FOLDERS)
        session.request = MagicMock(return_value=resp)
        api = make_api(session)
        return await api.get_config_folders()

    result = asyncio.run(_run())
    assert isinstance(result, list)


def test_get_folder_completion_returns_data():
    async def _run():
        session = MagicMock()
        resp = make_mock_response(200, {"completion": 99.9})
        session.request = MagicMock(return_value=resp)
        api = make_api(session)
        return await api.get_folder_completion("abcd-1234")

    result = asyncio.run(_run())
    assert result["completion"] == pytest.approx(99.9)


def test_get_folder_completion_with_device_id():
    async def _run():
        session = MagicMock()
        resp = make_mock_response(200, {"completion": 80.0})
        session.request = MagicMock(return_value=resp)
        api = make_api(session)
        return await api.get_folder_completion("abcd-1234", device_id="DEV123")

    result = asyncio.run(_run())
    assert result["completion"] == pytest.approx(80.0)


def test_get_folder_errors_returns_data():
    async def _run():
        session = MagicMock()
        resp = make_mock_response(200, {"errors": []})
        session.request = MagicMock(return_value=resp)
        api = make_api(session)
        return await api.get_folder_errors("abcd-1234")

    result = asyncio.run(_run())
    assert "errors" in result


def test_scan_all_folders_returns_true_on_success():
    async def _run():
        session = MagicMock()
        resp = make_mock_response(200, None, text="")
        resp.content_type = "text/plain"
        session.request = MagicMock(return_value=resp)
        api = make_api(session)
        return await api.scan_all_folders()

    assert asyncio.run(_run()) is True


def test_pause_device_returns_true_on_success():
    async def _run():
        session = MagicMock()
        resp = make_mock_response(200, None, text="")
        resp.content_type = "text/plain"
        session.request = MagicMock(return_value=resp)
        api = make_api(session)
        return await api.pause_device("DEV123")

    assert asyncio.run(_run()) is True


def test_resume_device_returns_true_on_success():
    async def _run():
        session = MagicMock()
        resp = make_mock_response(200, None, text="")
        resp.content_type = "text/plain"
        session.request = MagicMock(return_value=resp)
        api = make_api(session)
        return await api.resume_device("DEV123")

    assert asyncio.run(_run()) is True


def test_pause_all_returns_true_on_success():
    async def _run():
        session = MagicMock()
        resp = make_mock_response(200, None, text="")
        resp.content_type = "text/plain"
        session.request = MagicMock(return_value=resp)
        api = make_api(session)
        return await api.pause_all()

    assert asyncio.run(_run()) is True


def test_resume_all_returns_true_on_success():
    async def _run():
        session = MagicMock()
        resp = make_mock_response(200, None, text="")
        resp.content_type = "text/plain"
        session.request = MagicMock(return_value=resp)
        api = make_api(session)
        return await api.resume_all()

    assert asyncio.run(_run()) is True


def test_get_device_stats_returns_data():
    from tests.conftest import MOCK_DEVICE_STATS

    async def _run():
        session = MagicMock()
        resp = make_mock_response(200, MOCK_DEVICE_STATS)
        session.request = MagicMock(return_value=resp)
        api = make_api(session)
        return await api.get_device_stats()

    result = asyncio.run(_run())
    assert isinstance(result, dict)


def test_get_folder_stats_returns_data():
    from tests.conftest import MOCK_FOLDER_STATS

    async def _run():
        session = MagicMock()
        resp = make_mock_response(200, MOCK_FOLDER_STATS)
        session.request = MagicMock(return_value=resp)
        api = make_api(session)
        return await api.get_folder_stats()

    result = asyncio.run(_run())
    assert isinstance(result, dict)


def test_scan_all_folders_returns_false_on_error():
    async def _run():
        session = MagicMock()
        session.request = MagicMock(side_effect=aiohttp.ClientError("error"))
        api = make_api(session)
        return await api.scan_all_folders()

    assert asyncio.run(_run()) is False


def test_pause_device_returns_false_on_error():
    async def _run():
        session = MagicMock()
        session.request = MagicMock(side_effect=aiohttp.ClientError("error"))
        api = make_api(session)
        return await api.pause_device("DEV123")

    assert asyncio.run(_run()) is False


def test_resume_device_returns_false_on_error():
    async def _run():
        session = MagicMock()
        session.request = MagicMock(side_effect=aiohttp.ClientError("error"))
        api = make_api(session)
        return await api.resume_device("DEV123")

    assert asyncio.run(_run()) is False


def test_pause_all_returns_false_on_error():
    async def _run():
        session = MagicMock()
        session.request = MagicMock(side_effect=aiohttp.ClientError("error"))
        api = make_api(session)
        return await api.pause_all()

    assert asyncio.run(_run()) is False


def test_resume_all_returns_false_on_error():
    async def _run():
        session = MagicMock()
        session.request = MagicMock(side_effect=aiohttp.ClientError("error"))
        api = make_api(session)
        return await api.resume_all()

    assert asyncio.run(_run()) is False


def test_ssl_error_raises_syncthing_ssl_error():
    async def _run():
        session = MagicMock()
        session.request = MagicMock(
            side_effect=aiohttp.ClientSSLError(MagicMock(), MagicMock())
        )
        api = make_api(session)
        await api.get_version()

    try:
        asyncio.run(_run())
        assert False, "Expected SyncthingSslError"
    except SyncthingSslError:
        pass


def test_check_health_ssl_error_propagates():
    async def _run():
        session = MagicMock()
        session.request = MagicMock(
            side_effect=aiohttp.ClientSSLError(MagicMock(), MagicMock())
        )
        api = make_api(session)
        return await api.check_health()

    try:
        asyncio.run(_run())
        assert False, "Expected SyncthingSslError"
    except SyncthingSslError:
        pass
