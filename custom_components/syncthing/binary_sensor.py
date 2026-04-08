"""Binary sensor platform for Syncthing."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SyncthingConfigEntry
from .const import DOMAIN
from .coordinator import SyncthingCoordinator, SyncthingData

PARALLEL_UPDATES = 1


# --- Descriptions ---


@dataclass(frozen=True, kw_only=True)
class SyncthingBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a Syncthing binary sensor entity."""

    value_fn: Callable[[SyncthingData], bool | None]
    attr_fn: Callable[[SyncthingData], dict[str, Any]] | None = None


@dataclass(frozen=True, kw_only=True)
class SyncthingFolderBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a per-folder Syncthing binary sensor entity."""

    value_fn: Callable[[SyncthingData, str], bool | None]
    attr_fn: Callable[[SyncthingData, str], dict[str, Any]] | None = None


# --- System binary sensor definitions ---


SYSTEM_BINARY_SENSORS: tuple[SyncthingBinarySensorEntityDescription, ...] = (
    SyncthingBinarySensorEntityDescription(
        key="running",
        translation_key="running",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: bool(data.system_status.get("myID")),
        attr_fn=lambda data: {
            "goroutines": data.system_status.get("goroutines"),
            "alloc_bytes": data.system_status.get("alloc"),
            "start_time": data.system_status.get("startTime"),
        },
    ),
)


# --- Folder binary sensor definitions ---


@dataclass(frozen=True, kw_only=True)
class SyncthingDeviceBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a per-device Syncthing binary sensor entity."""

    value_fn: Callable[[SyncthingData, str], bool | None]
    attr_fn: Callable[[SyncthingData, str], dict[str, Any]] | None = None


def _folder_status(data: SyncthingData, fid: str) -> dict[str, Any]:
    """Get folder status dict."""
    return data.folder_status.get(fid, {})


def _folder_config(data: SyncthingData, fid: str) -> dict[str, Any]:
    """Get folder config dict."""
    for folder in data.config_folders:
        if folder["id"] == fid:
            return folder
    return {}


FOLDER_BINARY_SENSORS: tuple[SyncthingFolderBinarySensorEntityDescription, ...] = (
    SyncthingFolderBinarySensorEntityDescription(
        key="error",
        translation_key="folder_error",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data, fid: _folder_status(data, fid).get("pullErrors", 0) > 0,
        attr_fn=lambda data, fid: {
            "pull_errors": _folder_status(data, fid).get("pullErrors"),
            "state": _folder_status(data, fid).get("state"),
        },
    ),
    SyncthingFolderBinarySensorEntityDescription(
        key="syncing",
        translation_key="folder_syncing",
        device_class=BinarySensorDeviceClass.MOVING,
        value_fn=lambda data, fid: _folder_status(data, fid).get("state") == "syncing",
    ),
    SyncthingFolderBinarySensorEntityDescription(
        key="paused",
        translation_key="folder_paused",
        icon="mdi:pause-circle-outline",
        value_fn=lambda data, fid: _folder_config(data, fid).get("paused", False),
    ),
)


# --- Device binary sensor definitions ---


def _device_connection(data: SyncthingData, did: str) -> dict[str, Any]:
    """Get device connection dict."""
    return data.connections.get("connections", {}).get(did, {})


DEVICE_BINARY_SENSORS: tuple[SyncthingDeviceBinarySensorEntityDescription, ...] = (
    SyncthingDeviceBinarySensorEntityDescription(
        key="connected",
        translation_key="device_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda data, did: _device_connection(data, did).get(
            "connected", False
        ),
    ),
    SyncthingDeviceBinarySensorEntityDescription(
        key="paused",
        translation_key="device_paused",
        icon="mdi:pause-circle-outline",
        value_fn=lambda data, did: _device_connection(data, did).get("paused", False),
    ),
)


# --- Setup ---


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SyncthingConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Syncthing binary sensors."""
    coordinator = entry.runtime_data

    entities: list[BinarySensorEntity] = [
        SyncthingSystemBinarySensor(coordinator, description, entry.entry_id)
        for description in SYSTEM_BINARY_SENSORS
    ]

    for folder in coordinator.data.config_folders:
        folder_id = folder["id"]
        folder_label = folder.get("label") or folder_id
        for description in FOLDER_BINARY_SENSORS:
            entities.append(
                SyncthingFolderBinarySensor(
                    coordinator, description, entry.entry_id, folder_id, folder_label
                )
            )

    my_id = coordinator.data.system_status.get("myID", "")
    for device in coordinator.data.config_devices:
        device_id = device["deviceID"]
        if device_id == my_id:
            continue
        device_name = device.get("name") or device_id[:7]
        for description in DEVICE_BINARY_SENSORS:
            entities.append(
                SyncthingDeviceBinarySensor(
                    coordinator, description, entry.entry_id, device_id, device_name
                )
            )

    async_add_entities(entities)


# --- Entity classes ---


class SyncthingSystemBinarySensor(
    CoordinatorEntity[SyncthingCoordinator], BinarySensorEntity
):
    """Binary sensor for system-level Syncthing status."""

    entity_description: SyncthingBinarySensorEntityDescription
    _attr_has_entity_name = True
    _unrecorded_attributes = frozenset({"goroutines", "alloc_bytes"})

    def __init__(
        self,
        coordinator: SyncthingCoordinator,
        description: SyncthingBinarySensorEntityDescription,
        entry_id: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": "Syncthing",
            "manufacturer": "Syncthing Foundation",
            "sw_version": coordinator.data.version.get("version")
            if coordinator.data
            else None,
        }

    @property
    def is_on(self) -> bool | None:
        """Return true if sensor is on."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if self.entity_description.attr_fn:
            return self.entity_description.attr_fn(self.coordinator.data)
        return None


class SyncthingFolderBinarySensor(
    CoordinatorEntity[SyncthingCoordinator], BinarySensorEntity
):
    """Binary sensor for per-folder Syncthing status."""

    entity_description: SyncthingFolderBinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SyncthingCoordinator,
        description: SyncthingFolderBinarySensorEntityDescription,
        entry_id: str,
        folder_id: str,
        folder_label: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._folder_id = folder_id
        self._attr_unique_id = f"{entry_id}_folder_{folder_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry_id}_folder_{folder_id}")},
            "name": f"Syncthing Folder: {folder_label}",
            "manufacturer": "Syncthing Foundation",
            "via_device": (DOMAIN, entry_id),
        }

    @property
    def is_on(self) -> bool | None:
        """Return true if sensor is on."""
        return self.entity_description.value_fn(self.coordinator.data, self._folder_id)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if self.entity_description.attr_fn:
            return self.entity_description.attr_fn(
                self.coordinator.data, self._folder_id
            )
        return None


class SyncthingDeviceBinarySensor(
    CoordinatorEntity[SyncthingCoordinator], BinarySensorEntity
):
    """Binary sensor for per-device Syncthing status."""

    entity_description: SyncthingDeviceBinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SyncthingCoordinator,
        description: SyncthingDeviceBinarySensorEntityDescription,
        entry_id: str,
        device_id: str,
        device_name: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._device_id = device_id
        self._attr_unique_id = f"{entry_id}_device_{device_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry_id}_device_{device_id}")},
            "name": f"Syncthing Device: {device_name}",
            "manufacturer": "Syncthing Foundation",
            "via_device": (DOMAIN, entry_id),
        }

    @property
    def is_on(self) -> bool | None:
        """Return true if sensor is on."""
        return self.entity_description.value_fn(self.coordinator.data, self._device_id)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if self.entity_description.attr_fn:
            return self.entity_description.attr_fn(
                self.coordinator.data, self._device_id
            )
        return None
