"""Tests for Syncthing coordinator."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.syncthing_extended.api import SyncthingApiError, SyncthingAuthError
from custom_components.syncthing_extended.coordinator import (
    SyncthingCoordinator,
    SyncthingData,
)
from tests.conftest import (
    MOCK_CONFIG_FOLDERS,
    MOCK_FOLDER_COMPLETION,
    MOCK_FOLDER_STATUS,
    MOCK_SYSTEM_STATUS,
    build_mock_api,
)


def _make_hass_in_loop():
    """Build a MagicMock hass with an event loop attached. MUST be called inside
    an `async def` — asyncio.get_event_loop() needs a running loop context in py3.12+."""
    hass = MagicMock()
    hass.loop = asyncio.get_event_loop()
    return hass


def test_coordinator_fetches_and_merges_all_data():
    """Happy path: every configured folder gets a status + completion entry."""
    async def _run():
        api = build_mock_api()
        coordinator = SyncthingCoordinator(_make_hass_in_loop(), api, scan_interval=30)
        return api, await coordinator._async_update_data()

    api, data = asyncio.run(_run())

    assert isinstance(data, SyncthingData)
    # Every config folder ID appears in both status and completion dicts
    expected_ids = {f["id"] for f in MOCK_CONFIG_FOLDERS}
    assert set(data.folder_status.keys()) == expected_ids
    assert set(data.folder_completion.keys()) == expected_ids
    # The loop invoked the per-folder APIs once per folder (not skipped, not duplicated)
    assert api.get_folder_status.await_count == len(MOCK_CONFIG_FOLDERS)
    assert api.get_folder_completion.await_count == len(MOCK_CONFIG_FOLDERS)
    for fid in expected_ids:
        api.get_folder_status.assert_any_await(fid)
        api.get_folder_completion.assert_any_await(fid)
    # Top-level fields propagated verbatim
    assert data.version["version"] == "v1.29.0"
    assert data.system_status["myID"] == MOCK_SYSTEM_STATUS["myID"]
    assert data.connections["total"]["inBytesTotal"] == 2048000
    # Config arrays preserved (coordinator doesn't filter config_devices — that's
    # a display-time concern in entity code).
    assert len(data.config_folders) == len(MOCK_CONFIG_FOLDERS)
    assert len(data.config_devices) == 2


def test_coordinator_raises_update_failed_on_generic_api_error():
    async def _run():
        api = build_mock_api()
        api.get_version = AsyncMock(side_effect=SyncthingApiError("connection failed"))
        coordinator = SyncthingCoordinator(_make_hass_in_loop(), api)
        await coordinator._async_update_data()

    with pytest.raises(UpdateFailed, match=r"Error communicating with Syncthing"):
        asyncio.run(_run())


def test_coordinator_raises_config_entry_auth_failed_on_auth_error():
    async def _run():
        api = build_mock_api()
        api.get_version = AsyncMock(side_effect=SyncthingAuthError("Invalid API key"))
        coordinator = SyncthingCoordinator(_make_hass_in_loop(), api)
        await coordinator._async_update_data()

    with pytest.raises(ConfigEntryAuthFailed, match=r"re-authenticate"):
        asyncio.run(_run())


def test_coordinator_per_folder_status_failure_falls_back_to_empty_dict():
    """One folder fails on status → that entry becomes {} and the other folder
    still has full data. No UpdateFailed bubbles up."""
    async def _run():
        api = build_mock_api()

        async def folder_status_side_effect(fid):
            if fid == "efgh-5678":
                raise SyncthingApiError("timeout")
            return MOCK_FOLDER_STATUS[fid]

        api.get_folder_status = AsyncMock(side_effect=folder_status_side_effect)
        coordinator = SyncthingCoordinator(_make_hass_in_loop(), api)
        return await coordinator._async_update_data()

    data = asyncio.run(_run())

    assert data.folder_status["efgh-5678"] == {}
    assert data.folder_status["abcd-1234"]["state"] == "idle"
    assert data.folder_status["abcd-1234"]["pullErrors"] == 0
    assert len(data.folder_status) == 2


def test_coordinator_per_folder_completion_failure_falls_back_to_empty_dict():
    """Paused folder 404 on completion → {} fallback, other folder intact."""
    async def _run():
        api = build_mock_api()

        async def completion_side_effect(fid):
            if fid == "efgh-5678":
                raise SyncthingApiError("404 Not Found (paused)")
            return MOCK_FOLDER_COMPLETION[fid]

        api.get_folder_completion = AsyncMock(side_effect=completion_side_effect)
        coordinator = SyncthingCoordinator(_make_hass_in_loop(), api)
        return await coordinator._async_update_data()

    data = asyncio.run(_run())

    assert data.folder_completion["efgh-5678"] == {}
    assert data.folder_completion["abcd-1234"]["completion"] == pytest.approx(99.9937)
    assert len(data.folder_completion) == 2


def test_coordinator_uses_configured_scan_interval():
    async def _run():
        api = build_mock_api()
        return SyncthingCoordinator(_make_hass_in_loop(), api, scan_interval=120)

    coordinator = asyncio.run(_run())
    assert coordinator.update_interval.total_seconds() == 120
