"""Syncthing Extended integration for Home Assistant."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SyncthingApi
from .const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_USE_SSL,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USE_SSL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import SyncthingCoordinator

_LOGGER = logging.getLogger(__name__)

type SyncthingConfigEntry = ConfigEntry[SyncthingCoordinator]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Syncthing Extended integration (registers services)."""
    _async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: SyncthingConfigEntry) -> bool:
    """Set up Syncthing Extended from a config entry."""
    use_ssl = entry.data.get(CONF_USE_SSL, DEFAULT_USE_SSL)
    verify_ssl = entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
    session = async_get_clientsession(hass, verify_ssl=verify_ssl)

    api = SyncthingApi(
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        api_key=entry.data[CONF_API_KEY],
        use_ssl=use_ssl,
        verify_ssl=verify_ssl,
        session=session,
    )

    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )

    coordinator = SyncthingCoordinator(hass, api, scan_interval)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: SyncthingConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(
    hass: HomeAssistant, entry: SyncthingConfigEntry
) -> None:
    """Handle options update — reload the entry."""
    await hass.config_entries.async_reload(entry.entry_id)


def _get_coordinator(hass: HomeAssistant) -> SyncthingCoordinator:
    """Get the first available coordinator."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        if hasattr(entry, "runtime_data") and entry.runtime_data:
            return entry.runtime_data
    raise ValueError("No Syncthing Extended config entry found")


def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services (idempotent)."""
    if hass.services.has_service(DOMAIN, "scan_folder"):
        return

    async def handle_scan_folder(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass)
        folder_id = call.data["folder_id"]
        if not await coordinator.api.scan_folder(folder_id):
            raise HomeAssistantError(f"Failed to scan folder {folder_id}")
        await coordinator.async_request_refresh()

    async def handle_scan_all(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass)
        if not await coordinator.api.scan_all_folders():
            raise HomeAssistantError("Failed to scan all folders")
        await coordinator.async_request_refresh()

    async def handle_pause_device(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass)
        if not await coordinator.api.pause_device(call.data["device_id"]):
            raise HomeAssistantError(f"Failed to pause device {call.data['device_id']}")
        await coordinator.async_request_refresh()

    async def handle_resume_device(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass)
        if not await coordinator.api.resume_device(call.data["device_id"]):
            raise HomeAssistantError(f"Failed to resume device {call.data['device_id']}")
        await coordinator.async_request_refresh()

    async def handle_pause_folder(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass)
        folder_id = call.data["folder_id"]
        if not await coordinator.api.pause_folder(folder_id):
            raise HomeAssistantError(f"Failed to pause folder {folder_id}")
        await coordinator.async_request_refresh()

    async def handle_resume_folder(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass)
        folder_id = call.data["folder_id"]
        if not await coordinator.api.resume_folder(folder_id):
            raise HomeAssistantError(f"Failed to resume folder {folder_id}")
        await coordinator.async_request_refresh()

    async def handle_pause_all(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass)
        if not await coordinator.api.pause_all():
            raise HomeAssistantError("Failed to pause all devices")
        await coordinator.async_request_refresh()

    async def handle_resume_all(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass)
        if not await coordinator.api.resume_all():
            raise HomeAssistantError("Failed to resume all devices")
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN, "scan_folder", handle_scan_folder,
        schema=vol.Schema({vol.Required("folder_id"): str}),
    )
    hass.services.async_register(DOMAIN, "scan_all", handle_scan_all)
    hass.services.async_register(
        DOMAIN, "pause_folder", handle_pause_folder,
        schema=vol.Schema({vol.Required("folder_id"): str}),
    )
    hass.services.async_register(
        DOMAIN, "resume_folder", handle_resume_folder,
        schema=vol.Schema({vol.Required("folder_id"): str}),
    )
    hass.services.async_register(
        DOMAIN, "pause_device", handle_pause_device,
        schema=vol.Schema({vol.Required("device_id"): str}),
    )
    hass.services.async_register(
        DOMAIN, "resume_device", handle_resume_device,
        schema=vol.Schema({vol.Required("device_id"): str}),
    )
    hass.services.async_register(DOMAIN, "pause_all", handle_pause_all)
    hass.services.async_register(DOMAIN, "resume_all", handle_resume_all)
