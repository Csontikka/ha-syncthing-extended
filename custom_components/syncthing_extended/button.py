"""Button platform for Syncthing."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SyncthingConfigEntry
from .coordinator import SyncthingCoordinator
from .entity import SyncthingDeviceEntity, SyncthingFolderEntity, SyncthingSystemEntity

PARALLEL_UPDATES = 1

_LOGGER = logging.getLogger(__name__)


async def _send(
    coordinator: SyncthingCoordinator, command: Awaitable[bool], action: str
) -> None:
    """Run a Syncthing command for a button press, then refresh the data.

    A rejected command raises, so the failure shows up in the UI instead of the
    button appearing to do nothing.
    """
    if not await command:
        raise HomeAssistantError(f"Failed to {action}")
    await asyncio.sleep(1)
    await coordinator.async_refresh()


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
        entities.extend(
            button(coordinator, entry.entry_id, folder_id, folder_label)
            for button in (
                SyncthingFolderScanButton,
                SyncthingFolderPauseButton,
                SyncthingFolderResumeButton,
            )
        )

    my_id = coordinator.data.system_status.get("myID", "")
    for device in coordinator.data.config_devices:
        device_id = device["deviceID"]
        if device_id == my_id:
            continue
        device_label = device.get("name") or device_id[:8]
        entities.extend(
            button(coordinator, entry.entry_id, device_id, device_label)
            for button in (SyncthingDevicePauseButton, SyncthingDeviceResumeButton)
        )

    async_add_entities(entities)


class SyncthingScanAllButton(SyncthingSystemEntity, ButtonEntity):
    """Button to trigger scan of all folders."""

    _attr_translation_key = "scan_all"
    _attr_icon = "mdi:folder-refresh"

    def __init__(
        self,
        coordinator: SyncthingCoordinator,
        entry_id: str,
    ) -> None:
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_scan_all"

    async def async_press(self) -> None:
        """Trigger scan of all folders."""
        _LOGGER.debug("Button pressed: scan_all")
        await _send(
            self.coordinator,
            self.coordinator.api.scan_all_folders(),
            "scan all folders",
        )


class SyncthingFolderScanButton(SyncthingFolderEntity, ButtonEntity):
    """Button to trigger scan of a specific folder."""

    _attr_translation_key = "folder_scan"
    _attr_icon = "mdi:folder-sync"

    def __init__(
        self,
        coordinator: SyncthingCoordinator,
        entry_id: str,
        folder_id: str,
        folder_label: str,
    ) -> None:
        super().__init__(coordinator, entry_id, folder_id, folder_label)
        self._attr_unique_id = f"{entry_id}_folder_{folder_id}_scan"

    async def async_press(self) -> None:
        """Trigger scan of this folder."""
        _LOGGER.debug("Button pressed: scan_folder %s", self._folder_id)
        await _send(
            self.coordinator,
            self.coordinator.api.scan_folder(self._folder_id),
            f"scan folder {self._folder_id}",
        )


class SyncthingFolderPauseButton(SyncthingFolderEntity, ButtonEntity):
    """Button to pause a specific folder."""

    _attr_translation_key = "folder_pause"
    _attr_icon = "mdi:folder-lock"

    def __init__(
        self,
        coordinator: SyncthingCoordinator,
        entry_id: str,
        folder_id: str,
        folder_label: str,
    ) -> None:
        super().__init__(coordinator, entry_id, folder_id, folder_label)
        self._attr_unique_id = f"{entry_id}_folder_{folder_id}_pause"

    async def async_press(self) -> None:
        """Pause this folder."""
        _LOGGER.debug("Button pressed: pause_folder %s", self._folder_id)
        await _send(
            self.coordinator,
            self.coordinator.api.pause_folder(self._folder_id),
            f"pause folder {self._folder_id}",
        )


class SyncthingFolderResumeButton(SyncthingFolderEntity, ButtonEntity):
    """Button to resume a specific folder."""

    _attr_translation_key = "folder_resume"
    _attr_icon = "mdi:folder-play"

    def __init__(
        self,
        coordinator: SyncthingCoordinator,
        entry_id: str,
        folder_id: str,
        folder_label: str,
    ) -> None:
        super().__init__(coordinator, entry_id, folder_id, folder_label)
        self._attr_unique_id = f"{entry_id}_folder_{folder_id}_resume"

    async def async_press(self) -> None:
        """Resume this folder."""
        _LOGGER.debug("Button pressed: resume_folder %s", self._folder_id)
        await _send(
            self.coordinator,
            self.coordinator.api.resume_folder(self._folder_id),
            f"resume folder {self._folder_id}",
        )


class SyncthingDevicePauseButton(SyncthingDeviceEntity, ButtonEntity):
    """Button to pause a specific device."""

    _attr_translation_key = "device_pause"
    _attr_icon = "mdi:pause-circle"

    def __init__(
        self,
        coordinator: SyncthingCoordinator,
        entry_id: str,
        device_id: str,
        device_label: str,
    ) -> None:
        super().__init__(coordinator, entry_id, device_id, device_label)
        self._attr_unique_id = f"{entry_id}_device_{device_id}_pause"

    async def async_press(self) -> None:
        """Pause this device."""
        _LOGGER.debug("Button pressed: pause_device %s", self._device_id)
        await _send(
            self.coordinator,
            self.coordinator.api.pause_device(self._device_id),
            f"pause device {self._device_id}",
        )


class SyncthingDeviceResumeButton(SyncthingDeviceEntity, ButtonEntity):
    """Button to resume a specific device."""

    _attr_translation_key = "device_resume"
    _attr_icon = "mdi:play-circle"

    def __init__(
        self,
        coordinator: SyncthingCoordinator,
        entry_id: str,
        device_id: str,
        device_label: str,
    ) -> None:
        super().__init__(coordinator, entry_id, device_id, device_label)
        self._attr_unique_id = f"{entry_id}_device_{device_id}_resume"

    async def async_press(self) -> None:
        """Resume this device."""
        _LOGGER.debug("Button pressed: resume_device %s", self._device_id)
        await _send(
            self.coordinator,
            self.coordinator.api.resume_device(self._device_id),
            f"resume device {self._device_id}",
        )
