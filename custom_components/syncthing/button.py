"""Button platform for Syncthing."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SyncthingConfigEntry

PARALLEL_UPDATES = 1
from .const import DOMAIN
from .coordinator import SyncthingCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SyncthingConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Syncthing buttons."""
    coordinator = entry.runtime_data

    entities: list[ButtonEntity] = [
        SyncthingScanAllButton(coordinator, entry.entry_id),
    ]

    for folder in coordinator.data.config_folders:
        folder_id = folder["id"]
        folder_label = folder.get("label") or folder_id
        entities.append(
            SyncthingFolderScanButton(
                coordinator, entry.entry_id, folder_id, folder_label
            )
        )
        entities.append(
            SyncthingFolderPauseButton(
                coordinator, entry.entry_id, folder_id, folder_label
            )
        )
        entities.append(
            SyncthingFolderResumeButton(
                coordinator, entry.entry_id, folder_id, folder_label
            )
        )

    my_id = coordinator.data.system_status.get("myID", "")
    for device in coordinator.data.config_devices:
        device_id = device["deviceID"]
        if device_id == my_id:
            continue
        device_label = device.get("name") or device_id[:8]
        entities.append(
            SyncthingDevicePauseButton(
                coordinator, entry.entry_id, device_id, device_label
            )
        )
        entities.append(
            SyncthingDeviceResumeButton(
                coordinator, entry.entry_id, device_id, device_label
            )
        )

    async_add_entities(entities)


class SyncthingScanAllButton(CoordinatorEntity[SyncthingCoordinator], ButtonEntity):
    """Button to trigger scan of all folders."""

    _attr_has_entity_name = True
    _attr_translation_key = "scan_all"
    _attr_icon = "mdi:folder-refresh"

    def __init__(
        self,
        coordinator: SyncthingCoordinator,
        entry_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_scan_all"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": "Syncthing",
            "manufacturer": "Syncthing Foundation",
        }

    async def async_press(self) -> None:
        """Trigger scan of all folders."""
        _LOGGER.debug("Button pressed: scan_all")
        await self.coordinator.api.scan_all_folders()
        await self.coordinator.async_request_refresh()


class SyncthingFolderScanButton(CoordinatorEntity[SyncthingCoordinator], ButtonEntity):
    """Button to trigger scan of a specific folder."""

    _attr_has_entity_name = True
    _attr_translation_key = "folder_scan"
    _attr_icon = "mdi:folder-sync"

    def __init__(
        self,
        coordinator: SyncthingCoordinator,
        entry_id: str,
        folder_id: str,
        folder_label: str,
    ) -> None:
        super().__init__(coordinator)
        self._folder_id = folder_id
        self._attr_unique_id = f"{entry_id}_folder_{folder_id}_scan"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry_id}_folder_{folder_id}")},
            "name": f"Syncthing Folder: {folder_label}",
            "manufacturer": "Syncthing Foundation",
            "via_device": (DOMAIN, entry_id),
        }

    async def async_press(self) -> None:
        """Trigger scan of this folder."""
        _LOGGER.debug("Button pressed: scan_folder %s", self._folder_id)
        await self.coordinator.api.scan_folder(self._folder_id)
        await self.coordinator.async_request_refresh()


class SyncthingFolderPauseButton(CoordinatorEntity[SyncthingCoordinator], ButtonEntity):
    """Button to pause a specific folder."""

    _attr_has_entity_name = True
    _attr_translation_key = "folder_pause"
    _attr_icon = "mdi:folder-pause"

    def __init__(
        self,
        coordinator: SyncthingCoordinator,
        entry_id: str,
        folder_id: str,
        folder_label: str,
    ) -> None:
        super().__init__(coordinator)
        self._folder_id = folder_id
        self._attr_unique_id = f"{entry_id}_folder_{folder_id}_pause"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry_id}_folder_{folder_id}")},
            "name": f"Syncthing Folder: {folder_label}",
            "manufacturer": "Syncthing Foundation",
            "via_device": (DOMAIN, entry_id),
        }

    async def async_press(self) -> None:
        """Pause this folder."""
        _LOGGER.debug("Button pressed: pause_folder %s", self._folder_id)
        await self.coordinator.api.pause_folder(self._folder_id)
        await self.coordinator.async_request_refresh()


class SyncthingFolderResumeButton(CoordinatorEntity[SyncthingCoordinator], ButtonEntity):
    """Button to resume a specific folder."""

    _attr_has_entity_name = True
    _attr_translation_key = "folder_resume"
    _attr_icon = "mdi:folder-play"

    def __init__(
        self,
        coordinator: SyncthingCoordinator,
        entry_id: str,
        folder_id: str,
        folder_label: str,
    ) -> None:
        super().__init__(coordinator)
        self._folder_id = folder_id
        self._attr_unique_id = f"{entry_id}_folder_{folder_id}_resume"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry_id}_folder_{folder_id}")},
            "name": f"Syncthing Folder: {folder_label}",
            "manufacturer": "Syncthing Foundation",
            "via_device": (DOMAIN, entry_id),
        }

    async def async_press(self) -> None:
        """Resume this folder."""
        _LOGGER.debug("Button pressed: resume_folder %s", self._folder_id)
        await self.coordinator.api.resume_folder(self._folder_id)
        await self.coordinator.async_request_refresh()


class SyncthingDevicePauseButton(CoordinatorEntity[SyncthingCoordinator], ButtonEntity):
    """Button to pause a specific device."""

    _attr_has_entity_name = True
    _attr_translation_key = "device_pause"
    _attr_icon = "mdi:pause-circle"

    def __init__(
        self,
        coordinator: SyncthingCoordinator,
        entry_id: str,
        device_id: str,
        device_label: str,
    ) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{entry_id}_device_{device_id}_pause"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry_id}_device_{device_id}")},
            "name": f"Syncthing Device: {device_label}",
            "manufacturer": "Syncthing Foundation",
            "via_device": (DOMAIN, entry_id),
        }

    async def async_press(self) -> None:
        """Pause this device."""
        _LOGGER.debug("Button pressed: pause_device %s", self._device_id)
        await self.coordinator.api.pause_device(self._device_id)
        await self.coordinator.async_request_refresh()


class SyncthingDeviceResumeButton(CoordinatorEntity[SyncthingCoordinator], ButtonEntity):
    """Button to resume a specific device."""

    _attr_has_entity_name = True
    _attr_translation_key = "device_resume"
    _attr_icon = "mdi:play-circle"

    def __init__(
        self,
        coordinator: SyncthingCoordinator,
        entry_id: str,
        device_id: str,
        device_label: str,
    ) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{entry_id}_device_{device_id}_resume"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry_id}_device_{device_id}")},
            "name": f"Syncthing Device: {device_label}",
            "manufacturer": "Syncthing Foundation",
            "via_device": (DOMAIN, entry_id),
        }

    async def async_press(self) -> None:
        """Resume this device."""
        _LOGGER.debug("Button pressed: resume_device %s", self._device_id)
        await self.coordinator.api.resume_device(self._device_id)
        await self.coordinator.async_request_refresh()
