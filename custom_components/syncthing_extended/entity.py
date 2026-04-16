"""Common entity base classes for Syncthing."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SyncthingCoordinator


class SyncthingSystemEntity(CoordinatorEntity[SyncthingCoordinator]):
    """Base class for system-level Syncthing entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SyncthingCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        version = coordinator.data.version.get("version") if coordinator.data else None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="Syncthing",
            manufacturer="Syncthing Foundation",
            sw_version=version,
        )


class SyncthingFolderEntity(CoordinatorEntity[SyncthingCoordinator]):
    """Base class for per-folder Syncthing entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SyncthingCoordinator,
        entry_id: str,
        folder_id: str,
        folder_label: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._folder_id = folder_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_folder_{folder_id}")},
            name=f"Syncthing Folder: {folder_label}",
            manufacturer="Syncthing Foundation",
            via_device=(DOMAIN, entry_id),
        )


class SyncthingDeviceEntity(CoordinatorEntity[SyncthingCoordinator]):
    """Base class for per-device Syncthing entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SyncthingCoordinator,
        entry_id: str,
        device_id: str,
        device_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._device_id = device_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_device_{device_id}")},
            name=f"Syncthing Device: {device_name}",
            manufacturer="Syncthing Foundation",
            via_device=(DOMAIN, entry_id),
        )
