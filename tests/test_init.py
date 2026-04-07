"""Tests for Syncthing Extended __init__.py — services and setup."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.syncthing import _async_register_services, _get_coordinator
from custom_components.syncthing.const import DOMAIN
from tests.conftest import build_mock_api, build_mock_coordinator_data


def make_hass(has_service=False):
    hass = MagicMock()
    hass.services.has_service = MagicMock(return_value=has_service)
    hass.services.async_register = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])
    return hass


def make_entry_with_coordinator():
    coordinator = MagicMock()
    coordinator.data = build_mock_coordinator_data()
    coordinator.api = build_mock_api()
    coordinator.async_request_refresh = AsyncMock()
    entry = MagicMock()
    entry.runtime_data = coordinator
    return entry, coordinator


# --- _async_register_services ---

def test_register_services_registers_all():
    hass = make_hass(has_service=False)
    _async_register_services(hass)
    assert hass.services.async_register.call_count == 8
    registered = {call.args[1] for call in hass.services.async_register.call_args_list}
    assert registered == {"scan_folder", "scan_all", "pause_folder", "resume_folder", "pause_device", "resume_device", "pause_all", "resume_all"}


def test_register_services_idempotent():
    hass = make_hass(has_service=True)
    _async_register_services(hass)
    hass.services.async_register.assert_not_called()


# --- _get_coordinator ---

def test_get_coordinator_returns_runtime_data():
    entry, coordinator = make_entry_with_coordinator()
    hass = make_hass()
    hass.config_entries.async_entries = MagicMock(return_value=[entry])
    result = _get_coordinator(hass)
    assert result is coordinator


def test_get_coordinator_raises_when_no_entries():
    hass = make_hass()
    with pytest.raises(ValueError, match="No Syncthing"):
        _get_coordinator(hass)


# --- Service handlers ---

def _make_hass_with_coordinator():
    entry, coordinator = make_entry_with_coordinator()
    hass = make_hass(has_service=False)
    hass.config_entries.async_entries = MagicMock(return_value=[entry])
    hass.services.async_register = MagicMock()
    _async_register_services(hass)
    # Extract the registered handlers
    handlers = {call.args[1]: call.args[2] for call in hass.services.async_register.call_args_list}
    return hass, coordinator, handlers


def test_handle_scan_folder_success():
    async def _run():
        hass, coordinator, handlers = _make_hass_with_coordinator()
        call = MagicMock()
        call.data = {"folder_id": "abcd-1234"}
        await handlers["scan_folder"](call)
        coordinator.api.scan_folder.assert_called_once_with("abcd-1234")
        coordinator.async_request_refresh.assert_called_once()

    asyncio.run(_run())


def test_handle_scan_folder_failure_raises():
    async def _run():
        hass, coordinator, handlers = _make_hass_with_coordinator()
        coordinator.api.scan_folder = AsyncMock(return_value=False)
        call = MagicMock()
        call.data = {"folder_id": "bad-folder"}
        await handlers["scan_folder"](call)

    from homeassistant.exceptions import HomeAssistantError
    try:
        asyncio.run(_run())
        assert False, "Expected HomeAssistantError"
    except HomeAssistantError:
        pass


def test_handle_scan_all_success():
    async def _run():
        hass, coordinator, handlers = _make_hass_with_coordinator()
        call = MagicMock()
        await handlers["scan_all"](call)
        coordinator.api.scan_all_folders.assert_called_once()

    asyncio.run(_run())


def test_handle_scan_all_failure_raises():
    async def _run():
        hass, coordinator, handlers = _make_hass_with_coordinator()
        coordinator.api.scan_all_folders = AsyncMock(return_value=False)
        call = MagicMock()
        await handlers["scan_all"](call)

    from homeassistant.exceptions import HomeAssistantError
    try:
        asyncio.run(_run())
        assert False, "Expected HomeAssistantError"
    except HomeAssistantError:
        pass


def test_handle_pause_device_success():
    async def _run():
        hass, coordinator, handlers = _make_hass_with_coordinator()
        call = MagicMock()
        call.data = {"device_id": "DEV123"}
        await handlers["pause_device"](call)
        coordinator.api.pause_device.assert_called_once_with("DEV123")

    asyncio.run(_run())


def test_handle_pause_device_failure_raises():
    async def _run():
        hass, coordinator, handlers = _make_hass_with_coordinator()
        coordinator.api.pause_device = AsyncMock(return_value=False)
        call = MagicMock()
        call.data = {"device_id": "DEV123"}
        await handlers["pause_device"](call)

    from homeassistant.exceptions import HomeAssistantError
    try:
        asyncio.run(_run())
        assert False, "Expected HomeAssistantError"
    except HomeAssistantError:
        pass


def test_handle_resume_device_success():
    async def _run():
        hass, coordinator, handlers = _make_hass_with_coordinator()
        call = MagicMock()
        call.data = {"device_id": "DEV123"}
        await handlers["resume_device"](call)
        coordinator.api.resume_device.assert_called_once_with("DEV123")

    asyncio.run(_run())


def test_handle_pause_all_success():
    async def _run():
        hass, coordinator, handlers = _make_hass_with_coordinator()
        call = MagicMock()
        await handlers["pause_all"](call)
        coordinator.api.pause_all.assert_called_once()

    asyncio.run(_run())


def test_handle_resume_all_success():
    async def _run():
        hass, coordinator, handlers = _make_hass_with_coordinator()
        call = MagicMock()
        await handlers["resume_all"](call)
        coordinator.api.resume_all.assert_called_once()

    asyncio.run(_run())


def test_handle_resume_all_failure_raises():
    async def _run():
        hass, coordinator, handlers = _make_hass_with_coordinator()
        coordinator.api.resume_all = AsyncMock(return_value=False)
        call = MagicMock()
        await handlers["resume_all"](call)

    from homeassistant.exceptions import HomeAssistantError
    try:
        asyncio.run(_run())
        assert False, "Expected HomeAssistantError"
    except HomeAssistantError:
        pass


# --- async_setup ---

def test_async_setup_registers_services():
    async def _run():
        from custom_components.syncthing import async_setup
        hass = make_hass(has_service=False)
        result = await async_setup(hass, {})
        return hass, result

    hass, result = asyncio.run(_run())
    assert result is True
    assert hass.services.async_register.call_count == 8


# --- api pause/resume bool returns ---

def test_api_pause_returns_true():
    async def _run():
        api = build_mock_api()
        return await api.pause_device("DEV")

    assert asyncio.run(_run()) is True


def test_api_resume_returns_true():
    async def _run():
        api = build_mock_api()
        return await api.resume_device("DEV")

    assert asyncio.run(_run()) is True


def test_api_pause_all_returns_true():
    async def _run():
        api = build_mock_api()
        return await api.pause_all()

    assert asyncio.run(_run()) is True


def test_api_resume_all_returns_true():
    async def _run():
        api = build_mock_api()
        return await api.resume_all()

    assert asyncio.run(_run()) is True


# --- async_setup_entry / async_unload_entry ---

def test_async_setup_entry_stores_coordinator():
    async def _run():
        from custom_components.syncthing import async_setup_entry
        from custom_components.syncthing.coordinator import SyncthingCoordinator

        entry = MagicMock()
        entry.data = {
            "host": "192.168.1.1",
            "port": 8384,
            "api_key": "test-key",
            "verify_ssl": False,
            "scan_interval": 30,
        }
        entry.options = {}
        entry.entry_id = "test_entry"

        hass = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

        mock_coordinator = MagicMock(spec=SyncthingCoordinator)
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator.data = build_mock_coordinator_data()

        with patch(
            "custom_components.syncthing.SyncthingApi",
        ), patch(
            "custom_components.syncthing.async_get_clientsession",
            return_value=MagicMock(),
        ), patch(
            "custom_components.syncthing.SyncthingCoordinator",
            return_value=mock_coordinator,
        ):
            result = await async_setup_entry(hass, entry)

        return result, entry

    result, entry = asyncio.run(_run())
    assert result is True
    assert entry.runtime_data is not None


def test_async_unload_entry():
    async def _run():
        from custom_components.syncthing import async_unload_entry

        entry = MagicMock()
        hass = MagicMock()
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

        return await async_unload_entry(hass, entry)

    assert asyncio.run(_run()) is True


def test_async_update_listener_reloads():
    async def _run():
        from custom_components.syncthing import _async_update_listener

        entry = MagicMock()
        entry.entry_id = "test_entry"
        hass = MagicMock()
        hass.config_entries.async_reload = AsyncMock()

        await _async_update_listener(hass, entry)
        hass.config_entries.async_reload.assert_called_once_with("test_entry")

    asyncio.run(_run())


def test_handle_resume_device_failure_raises():
    async def _run():
        hass, coordinator, handlers = _make_hass_with_coordinator()
        coordinator.api.resume_device = AsyncMock(return_value=False)
        call = MagicMock()
        call.data = {"device_id": "DEV123"}
        await handlers["resume_device"](call)

    from homeassistant.exceptions import HomeAssistantError
    try:
        asyncio.run(_run())
        assert False, "Expected HomeAssistantError"
    except HomeAssistantError:
        pass


def test_handle_pause_all_failure_raises():
    async def _run():
        hass, coordinator, handlers = _make_hass_with_coordinator()
        coordinator.api.pause_all = AsyncMock(return_value=False)
        call = MagicMock()
        await handlers["pause_all"](call)

    from homeassistant.exceptions import HomeAssistantError
    try:
        asyncio.run(_run())
        assert False, "Expected HomeAssistantError"
    except HomeAssistantError:
        pass
