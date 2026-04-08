"""Diagnostics support for Syncthing integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_API_KEY
from .coordinator import SyncthingCoordinator

TO_REDACT = {CONF_API_KEY, "myID", "deviceID", "address", "full_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: SyncthingCoordinator = entry.runtime_data
    data = coordinator.data

    diag: dict[str, Any] = {
        "config_entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "system": {
            "version": data.version,
            "status": async_redact_data(data.system_status, TO_REDACT),
        },
        "connections": async_redact_data(data.connections, TO_REDACT),
        "folders": [
            {
                "id": folder["id"],
                "label": folder.get("label"),
                "paused": folder.get("paused"),
                "status": data.folder_status.get(folder["id"], {}),
                "completion": data.folder_completion.get(folder["id"], {}),
                "stats": data.folder_stats.get(folder["id"], {}),
            }
            for folder in data.config_folders
        ],
        "devices": [
            {
                "name": device.get("name"),
                "deviceID": "**REDACTED**",
                "paused": device.get("paused"),
                "connection": async_redact_data(
                    data.connections.get("connections", {}).get(
                        device["deviceID"], {}
                    ),
                    TO_REDACT,
                ),
                "stats": data.device_stats.get(device["deviceID"], {}),
            }
            for device in data.config_devices
        ],
    }

    return diag
