"""Syncthing data coordinator."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SyncthingApi, SyncthingApiError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class SyncthingData:
    """Container for all Syncthing data."""

    version: dict[str, Any] = field(default_factory=dict)
    system_status: dict[str, Any] = field(default_factory=dict)
    connections: dict[str, Any] = field(default_factory=dict)
    config_devices: list[dict[str, Any]] = field(default_factory=list)
    config_folders: list[dict[str, Any]] = field(default_factory=list)
    folder_status: dict[str, dict[str, Any]] = field(default_factory=dict)
    folder_completion: dict[str, dict[str, Any]] = field(default_factory=dict)
    folder_stats: dict[str, Any] = field(default_factory=dict)
    device_stats: dict[str, Any] = field(default_factory=dict)


class SyncthingCoordinator(DataUpdateCoordinator[SyncthingData]):
    """Manages polling data from the Syncthing API."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: SyncthingApi,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api

    async def _async_update_data(self) -> SyncthingData:
        """Fetch all data from Syncthing API."""
        _LOGGER.debug("Fetching Syncthing data from %s", self.api.base_url)
        try:
            version = await self.api.get_version()
            system_status = await self.api.get_system_status()
            connections = await self.api.get_connections()
            config_devices = await self.api.get_config_devices()
            config_folders = await self.api.get_config_folders()
            device_stats = await self.api.get_device_stats()
            folder_stats = await self.api.get_folder_stats()

            folder_status: dict[str, dict[str, Any]] = {}
            folder_completion: dict[str, dict[str, Any]] = {}

            for folder in config_folders:
                fid = folder["id"]
                try:
                    folder_status[fid] = await self.api.get_folder_status(fid)
                except SyncthingApiError as err:
                    _LOGGER.warning("Failed to get status for folder %s: %s", fid, err)
                    folder_status[fid] = {}
                try:
                    folder_completion[fid] = await self.api.get_folder_completion(fid)
                except SyncthingApiError as err:
                    # Paused folders return 404 for completion — this is expected
                    _LOGGER.debug("Skipping completion for folder %s: %s", fid, err)
                    folder_completion[fid] = {}

            remote_devices = [
                d
                for d in config_devices
                if d.get("deviceID") != system_status.get("myID")
            ]
            _LOGGER.debug(
                "Update complete: %d folder(s), %d remote device(s)",
                len(config_folders),
                len(remote_devices),
            )
            return SyncthingData(
                version=version,
                system_status=system_status,
                connections=connections,
                config_devices=config_devices,
                config_folders=config_folders,
                folder_status=folder_status,
                folder_completion=folder_completion,
                folder_stats=folder_stats,
                device_stats=device_stats,
            )

        except SyncthingApiError as err:
            raise UpdateFailed(f"Error communicating with Syncthing: {err}") from err
