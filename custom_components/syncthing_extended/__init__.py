"""Syncthing integration for Home Assistant."""

from __future__ import annotations

import asyncio
import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SyncthingApi
from .const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_PATH,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_USE_SSL,
    CONF_VERIFY_SSL,
    DEFAULT_PATH,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USE_SSL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import SyncthingCoordinator
from .entity import HUB_MANUFACTURER, HUB_NAME

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type SyncthingConfigEntry = ConfigEntry[SyncthingCoordinator]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Syncthing integration (registers services)."""
    _async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: SyncthingConfigEntry) -> bool:
    """Set up Syncthing from a config entry."""
    if hass.config_entries.async_entries("syncthing"):
        _LOGGER.warning(
            "The built-in Syncthing integration is also active. "
            "We recommend disabling it to avoid duplicate entities and "
            "potential conflicts. Go to Settings → Integrations → Syncthing → Delete"
        )

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
        path=entry.data.get(CONF_PATH, DEFAULT_PATH),
    )

    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )

    coordinator = SyncthingCoordinator(hass, api, scan_interval)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    # Folder and remote-device entries link to the hub by its registry id, so the
    # hub has to exist before the platforms create them.
    hub = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=HUB_NAME,
        manufacturer=HUB_MANUFACTURER,
        sw_version=coordinator.data.version.get("version"),
    )
    coordinator.hub_device_id = hub.id

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
    raise ValueError("No Syncthing config entry found")


# Service name -> (API method, call data field naming the target, what it does).
# Services without a field act on the whole instance.
_SERVICES: dict[str, tuple[str, str | None, str]] = {
    "scan_folder": ("scan_folder", "folder_id", "scan folder"),
    "scan_all": ("scan_all_folders", None, "scan all folders"),
    "pause_folder": ("pause_folder", "folder_id", "pause folder"),
    "resume_folder": ("resume_folder", "folder_id", "resume folder"),
    "pause_device": ("pause_device", "device_id", "pause device"),
    "resume_device": ("resume_device", "device_id", "resume device"),
    "pause_all": ("pause_all", None, "pause all devices"),
    "resume_all": ("resume_all", None, "resume all devices"),
}


def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services (idempotent)."""
    if hass.services.has_service(DOMAIN, "scan_folder"):
        return

    for service, (method, field, action) in _SERVICES.items():
        hass.services.async_register(
            DOMAIN,
            service,
            _service_handler(hass, service, method, field, action),
            schema=vol.Schema({vol.Required(field): str}) if field else None,
        )


def _service_handler(
    hass: HomeAssistant, service: str, method: str, field: str | None, action: str
):
    """Build the handler that forwards one service to the Syncthing API."""

    async def handle(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass)
        command = getattr(coordinator.api, method)
        target = call.data[field] if field else None
        description = f"{action} {target}" if field else action
        _LOGGER.debug("Service: %s (%s)", service, description)
        if not await (command(target) if field else command()):
            raise HomeAssistantError(f"Failed to {description}")
        await asyncio.sleep(1)
        await coordinator.async_refresh()

    return handle
