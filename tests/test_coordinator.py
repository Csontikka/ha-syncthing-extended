"""Tests for Syncthing coordinator."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.syncthing.api import SyncthingApiError
from custom_components.syncthing.coordinator import (
    SyncthingCoordinator,
    SyncthingData,
)
from tests.conftest import (
    MOCK_FOLDER_COMPLETION,
    MOCK_FOLDER_STATUS,
    MOCK_SYSTEM_STATUS,
    build_mock_api,
)


def make_hass():
    hass = MagicMock()
    hass.loop = asyncio.get_event_loop()
    return hass


def test_coordinator_fetch_all_data():
    async def _run():
        api = build_mock_api()
        coordinator = SyncthingCoordinator(make_hass(), api, scan_interval=30)
        return await coordinator._async_update_data()

    data = asyncio.run(_run())

    assert isinstance(data, SyncthingData)
    assert data.version["version"] == "v1.29.0"
    assert data.system_status["myID"] == MOCK_SYSTEM_STATUS["myID"]
    assert data.connections["total"]["inBytesTotal"] == 2048000
    assert len(data.config_folders) == 2
    assert len(data.config_devices) == 2
    assert "abcd-1234" in data.folder_status
    assert "efgh-5678" in data.folder_status
    assert data.folder_status["abcd-1234"]["state"] == "idle"
    assert data.folder_completion["abcd-1234"]["completion"] == pytest.approx(99.9937)


def test_coordinator_raises_update_failed_on_api_error():
    from homeassistant.helpers.update_coordinator import UpdateFailed

    async def _run():
        api = build_mock_api()
        api.get_version = AsyncMock(side_effect=SyncthingApiError("connection failed"))
        coordinator = SyncthingCoordinator(make_hass(), api)
        await coordinator._async_update_data()

    try:
        asyncio.run(_run())
        assert False, "Expected UpdateFailed"
    except Exception as e:
        assert "Error communicating" in str(e)


def test_coordinator_partial_folder_failure():
    async def _run():
        api = build_mock_api()

        async def folder_status_side_effect(fid):
            if fid == "efgh-5678":
                raise SyncthingApiError("timeout")
            return MOCK_FOLDER_STATUS.get(fid, {})

        api.get_folder_status = AsyncMock(side_effect=folder_status_side_effect)
        coordinator = SyncthingCoordinator(make_hass(), api)
        return await coordinator._async_update_data()

    data = asyncio.run(_run())
    assert data.folder_status["abcd-1234"]["state"] == "idle"
    assert data.folder_status["efgh-5678"] == {}


def test_coordinator_my_id_in_devices():
    async def _run():
        api = build_mock_api()
        coordinator = SyncthingCoordinator(make_hass(), api)
        return await coordinator._async_update_data()

    data = asyncio.run(_run())
    my_id = data.system_status["myID"]
    device_ids = [d["deviceID"] for d in data.config_devices]
    assert my_id in device_ids
