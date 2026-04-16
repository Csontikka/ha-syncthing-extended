"""Tests for Syncthing Extended __init__.py — services and setup."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.exceptions import HomeAssistantError

from custom_components.syncthing_extended import _async_register_services, _get_coordinator
from custom_components.syncthing_extended.const import DOMAIN, PLATFORMS
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
    coordinator.async_refresh = AsyncMock()
    entry = MagicMock()
    entry.runtime_data = coordinator
    return entry, coordinator


# --- _async_register_services ---

EXPECTED_SERVICES = {
    "scan_folder",
    "scan_all",
    "pause_folder",
    "resume_folder",
    "pause_device",
    "resume_device",
    "pause_all",
    "resume_all",
}


def test_register_services_registers_all_with_correct_domain():
    hass = make_hass(has_service=False)
    _async_register_services(hass)

    assert hass.services.async_register.call_count == 8
    registered = set()
    for call in hass.services.async_register.call_args_list:
        domain, name = call.args[0], call.args[1]
        assert domain == DOMAIN, f"Wrong domain: {domain}"
        registered.add(name)
    assert registered == EXPECTED_SERVICES


def test_register_services_folder_schemas_require_folder_id():
    """Verify schema validation: folder services reject calls without folder_id."""
    import voluptuous as vol
    hass = make_hass(has_service=False)
    _async_register_services(hass)

    schemas = {}
    for call in hass.services.async_register.call_args_list:
        name = call.args[1]
        schema = call.kwargs.get("schema")
        schemas[name] = schema

    # folder_id-requiring services should have a schema
    for svc in ("scan_folder", "pause_folder", "resume_folder"):
        assert schemas[svc] is not None, f"{svc} missing schema"
        with pytest.raises(vol.Invalid):
            schemas[svc]({})  # missing folder_id

    # device_id-requiring services
    for svc in ("pause_device", "resume_device"):
        assert schemas[svc] is not None, f"{svc} missing schema"
        with pytest.raises(vol.Invalid):
            schemas[svc]({})


def test_register_services_idempotent_when_already_registered():
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
    hass.config_entries.async_entries.assert_called_once_with(DOMAIN)


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
    handlers = {call.args[1]: call.args[2] for call in hass.services.async_register.call_args_list}
    return hass, coordinator, handlers


# Patch asyncio.sleep in the init module so the 1-second delay in handlers is skipped.
def _run_handler(handler, call):
    async def _inner():
        with patch(
            "custom_components.syncthing_extended.asyncio.sleep", new=AsyncMock()
        ):
            await handler(call)
    asyncio.run(_inner())


# scan_folder

def test_handle_scan_folder_calls_api_and_refreshes():
    hass, coordinator, handlers = _make_hass_with_coordinator()
    call = MagicMock()
    call.data = {"folder_id": "abcd-1234"}

    _run_handler(handlers["scan_folder"], call)

    coordinator.api.scan_folder.assert_awaited_once_with("abcd-1234")
    coordinator.async_refresh.assert_awaited_once()


def test_handle_scan_folder_raises_on_api_false():
    hass, coordinator, handlers = _make_hass_with_coordinator()
    coordinator.api.scan_folder = AsyncMock(return_value=False)
    call = MagicMock()
    call.data = {"folder_id": "bad-folder"}

    with pytest.raises(HomeAssistantError, match=r"Failed to scan folder bad-folder"):
        _run_handler(handlers["scan_folder"], call)
    coordinator.async_refresh.assert_not_awaited()


# scan_all

def test_handle_scan_all_calls_api_and_refreshes():
    hass, coordinator, handlers = _make_hass_with_coordinator()
    call = MagicMock()

    _run_handler(handlers["scan_all"], call)

    coordinator.api.scan_all_folders.assert_awaited_once()
    coordinator.async_refresh.assert_awaited_once()


def test_handle_scan_all_raises_on_api_false():
    hass, coordinator, handlers = _make_hass_with_coordinator()
    coordinator.api.scan_all_folders = AsyncMock(return_value=False)
    call = MagicMock()

    with pytest.raises(HomeAssistantError, match=r"Failed to scan all folders"):
        _run_handler(handlers["scan_all"], call)
    coordinator.async_refresh.assert_not_awaited()


# pause_device / resume_device

def test_handle_pause_device_calls_api_and_refreshes():
    hass, coordinator, handlers = _make_hass_with_coordinator()
    call = MagicMock()
    call.data = {"device_id": "DEV123"}

    _run_handler(handlers["pause_device"], call)

    coordinator.api.pause_device.assert_awaited_once_with("DEV123")
    coordinator.async_refresh.assert_awaited_once()


def test_handle_pause_device_raises_on_api_false():
    hass, coordinator, handlers = _make_hass_with_coordinator()
    coordinator.api.pause_device = AsyncMock(return_value=False)
    call = MagicMock()
    call.data = {"device_id": "DEV123"}

    with pytest.raises(HomeAssistantError, match=r"Failed to pause device DEV123"):
        _run_handler(handlers["pause_device"], call)


def test_handle_resume_device_calls_api_and_refreshes():
    hass, coordinator, handlers = _make_hass_with_coordinator()
    call = MagicMock()
    call.data = {"device_id": "DEV123"}

    _run_handler(handlers["resume_device"], call)

    coordinator.api.resume_device.assert_awaited_once_with("DEV123")
    coordinator.async_refresh.assert_awaited_once()


def test_handle_resume_device_raises_on_api_false():
    hass, coordinator, handlers = _make_hass_with_coordinator()
    coordinator.api.resume_device = AsyncMock(return_value=False)
    call = MagicMock()
    call.data = {"device_id": "DEV123"}

    with pytest.raises(HomeAssistantError, match=r"Failed to resume device DEV123"):
        _run_handler(handlers["resume_device"], call)


# pause_folder / resume_folder

def test_handle_pause_folder_calls_api_and_refreshes():
    hass, coordinator, handlers = _make_hass_with_coordinator()
    coordinator.api.pause_folder = AsyncMock(return_value=True)
    call = MagicMock()
    call.data = {"folder_id": "abcd-1234"}

    _run_handler(handlers["pause_folder"], call)

    coordinator.api.pause_folder.assert_awaited_once_with("abcd-1234")
    coordinator.async_refresh.assert_awaited_once()


def test_handle_pause_folder_raises_on_api_false():
    hass, coordinator, handlers = _make_hass_with_coordinator()
    coordinator.api.pause_folder = AsyncMock(return_value=False)
    call = MagicMock()
    call.data = {"folder_id": "abcd-1234"}

    with pytest.raises(HomeAssistantError, match=r"Failed to pause folder abcd-1234"):
        _run_handler(handlers["pause_folder"], call)


def test_handle_resume_folder_calls_api_and_refreshes():
    hass, coordinator, handlers = _make_hass_with_coordinator()
    coordinator.api.resume_folder = AsyncMock(return_value=True)
    call = MagicMock()
    call.data = {"folder_id": "abcd-1234"}

    _run_handler(handlers["resume_folder"], call)

    coordinator.api.resume_folder.assert_awaited_once_with("abcd-1234")
    coordinator.async_refresh.assert_awaited_once()


def test_handle_resume_folder_raises_on_api_false():
    hass, coordinator, handlers = _make_hass_with_coordinator()
    coordinator.api.resume_folder = AsyncMock(return_value=False)
    call = MagicMock()
    call.data = {"folder_id": "abcd-1234"}

    with pytest.raises(HomeAssistantError, match=r"Failed to resume folder abcd-1234"):
        _run_handler(handlers["resume_folder"], call)


# pause_all / resume_all

def test_handle_pause_all_calls_api_and_refreshes():
    hass, coordinator, handlers = _make_hass_with_coordinator()
    call = MagicMock()

    _run_handler(handlers["pause_all"], call)

    coordinator.api.pause_all.assert_awaited_once()
    coordinator.async_refresh.assert_awaited_once()


def test_handle_pause_all_raises_on_api_false():
    hass, coordinator, handlers = _make_hass_with_coordinator()
    coordinator.api.pause_all = AsyncMock(return_value=False)
    call = MagicMock()

    with pytest.raises(HomeAssistantError, match=r"Failed to pause all devices"):
        _run_handler(handlers["pause_all"], call)


def test_handle_resume_all_calls_api_and_refreshes():
    hass, coordinator, handlers = _make_hass_with_coordinator()
    call = MagicMock()

    _run_handler(handlers["resume_all"], call)

    coordinator.api.resume_all.assert_awaited_once()
    coordinator.async_refresh.assert_awaited_once()


def test_handle_resume_all_raises_on_api_false():
    hass, coordinator, handlers = _make_hass_with_coordinator()
    coordinator.api.resume_all = AsyncMock(return_value=False)
    call = MagicMock()

    with pytest.raises(HomeAssistantError, match=r"Failed to resume all devices"):
        _run_handler(handlers["resume_all"], call)


# --- async_setup ---

def test_async_setup_registers_all_services():
    async def _run():
        from custom_components.syncthing_extended import async_setup
        hass = make_hass(has_service=False)
        result = await async_setup(hass, {})
        return hass, result

    hass, result = asyncio.run(_run())
    assert result is True
    assert hass.services.async_register.call_count == 8
    registered = {call.args[1] for call in hass.services.async_register.call_args_list}
    assert registered == EXPECTED_SERVICES


# --- async_setup_entry / async_unload_entry ---

def test_async_setup_entry_stores_coordinator_and_forwards_platforms():
    from custom_components.syncthing_extended import async_setup_entry
    from custom_components.syncthing_extended.coordinator import SyncthingCoordinator

    async def _run():
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
        hass.config_entries.async_entries = MagicMock(return_value=[])
        hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

        mock_coordinator = MagicMock(spec=SyncthingCoordinator)
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator.data = build_mock_coordinator_data()

        with patch(
            "custom_components.syncthing_extended.SyncthingApi",
        ) as mock_api_cls, patch(
            "custom_components.syncthing_extended.async_get_clientsession",
            return_value=MagicMock(),
        ), patch(
            "custom_components.syncthing_extended.SyncthingCoordinator",
            return_value=mock_coordinator,
        ):
            result = await async_setup_entry(hass, entry)

        return result, entry, hass, mock_coordinator, mock_api_cls

    result, entry, hass, mock_coordinator, mock_api_cls = asyncio.run(_run())

    assert result is True
    # Coordinator stored on entry
    assert entry.runtime_data is mock_coordinator
    # First refresh awaited
    mock_coordinator.async_config_entry_first_refresh.assert_awaited_once()
    # Platforms forwarded
    hass.config_entries.async_forward_entry_setups.assert_awaited_once_with(
        entry, PLATFORMS
    )
    # API constructed with entry config
    mock_api_cls.assert_called_once()
    api_kwargs = mock_api_cls.call_args.kwargs
    assert api_kwargs["host"] == "192.168.1.1"
    assert api_kwargs["port"] == 8384
    assert api_kwargs["api_key"] == "test-key"
    # update listener registered (entry.async_on_unload called with listener)
    assert entry.async_on_unload.called


def test_async_setup_entry_warns_when_builtin_syncthing_active(caplog):
    """Cover the built-in integration warning branch."""
    from custom_components.syncthing_extended import async_setup_entry
    from custom_components.syncthing_extended.coordinator import SyncthingCoordinator

    async def _run():
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

        def entries_side_effect(domain):
            if domain == "syncthing":
                return [MagicMock()]
            return []

        hass.config_entries.async_entries = MagicMock(side_effect=entries_side_effect)
        hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

        mock_coordinator = MagicMock(spec=SyncthingCoordinator)
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()

        with patch("custom_components.syncthing_extended.SyncthingApi"), patch(
            "custom_components.syncthing_extended.async_get_clientsession",
            return_value=MagicMock(),
        ), patch(
            "custom_components.syncthing_extended.SyncthingCoordinator",
            return_value=mock_coordinator,
        ):
            return await async_setup_entry(hass, entry)

    import logging
    caplog.set_level(logging.WARNING, logger="custom_components.syncthing_extended")
    assert asyncio.run(_run()) is True
    assert any("built-in Syncthing" in rec.message for rec in caplog.records)


def test_async_unload_entry_calls_unload_platforms():
    from custom_components.syncthing_extended import async_unload_entry

    async def _run():
        entry = MagicMock()
        hass = MagicMock()
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

        result = await async_unload_entry(hass, entry)
        return result, hass, entry

    result, hass, entry = asyncio.run(_run())
    assert result is True
    hass.config_entries.async_unload_platforms.assert_awaited_once_with(entry, PLATFORMS)


def test_async_update_listener_reloads_entry():
    async def _run():
        from custom_components.syncthing_extended import _async_update_listener

        entry = MagicMock()
        entry.entry_id = "test_entry"
        hass = MagicMock()
        hass.config_entries.async_reload = AsyncMock()

        await _async_update_listener(hass, entry)
        hass.config_entries.async_reload.assert_awaited_once_with("test_entry")

    asyncio.run(_run())
