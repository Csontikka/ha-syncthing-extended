"""Sensor platform for Syncthing."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfInformation, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SyncthingConfigEntry
from .const import DOMAIN
from .coordinator import SyncthingCoordinator, SyncthingData

PARALLEL_UPDATES = 1


# --- Descriptions ---


@dataclass(frozen=True, kw_only=True)
class SyncthingSensorEntityDescription(SensorEntityDescription):
    """Describes a Syncthing sensor entity."""

    value_fn: Callable[[SyncthingData], Any]
    attr_fn: Callable[[SyncthingData], dict[str, Any]] | None = None


@dataclass(frozen=True, kw_only=True)
class SyncthingFolderSensorEntityDescription(SensorEntityDescription):
    """Describes a per-folder Syncthing sensor entity."""

    value_fn: Callable[[SyncthingData, str], Any]
    attr_fn: Callable[[SyncthingData, str], dict[str, Any]] | None = None


# --- System sensor definitions ---


SYSTEM_SENSORS: tuple[SyncthingSensorEntityDescription, ...] = (
    SyncthingSensorEntityDescription(
        key="version",
        translation_key="version",
        icon="mdi:tag",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.version.get("version"),
        attr_fn=lambda data: {
            "long_version": data.version.get("longVersion"),
            "os": data.version.get("os"),
            "arch": data.version.get("arch"),
        },
    ),
    SyncthingSensorEntityDescription(
        key="uptime",
        translation_key="uptime",
        icon="mdi:clock-outline",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.system_status.get("uptime"),
    ),
    SyncthingSensorEntityDescription(
        key="my_id",
        translation_key="my_id",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.system_status.get("myID", "")[:7] + "...",
        attr_fn=lambda data: {
            "full_id": data.system_status.get("myID"),
        },
    ),
    SyncthingSensorEntityDescription(
        key="total_in_bytes",
        translation_key="total_in_bytes",
        icon="mdi:download",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
        value_fn=lambda data: data.connections.get("total", {}).get("inBytesTotal"),
    ),
    SyncthingSensorEntityDescription(
        key="total_out_bytes",
        translation_key="total_out_bytes",
        icon="mdi:upload",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
        value_fn=lambda data: data.connections.get("total", {}).get("outBytesTotal"),
    ),
)


# --- Folder sensor definitions ---


@dataclass(frozen=True, kw_only=True)
class SyncthingDeviceSensorEntityDescription(SensorEntityDescription):
    """Describes a per-device Syncthing sensor entity."""

    value_fn: Callable[[SyncthingData, str], Any]
    attr_fn: Callable[[SyncthingData, str], dict[str, Any]] | None = None


def _folder_status(data: SyncthingData, fid: str) -> dict[str, Any]:
    """Get folder status dict."""
    return data.folder_status.get(fid, {})


def _folder_completion(data: SyncthingData, fid: str) -> dict[str, Any]:
    """Get folder completion dict."""
    return data.folder_completion.get(fid, {})


def _folder_stats(data: SyncthingData, fid: str) -> dict[str, Any]:
    """Get folder stats dict."""
    return data.folder_stats.get(fid, {})


FOLDER_SENSORS: tuple[SyncthingFolderSensorEntityDescription, ...] = (
    SyncthingFolderSensorEntityDescription(
        key="state",
        translation_key="folder_state",
        icon="mdi:folder-sync",
        value_fn=lambda data, fid: _folder_status(data, fid).get("state"),
        attr_fn=lambda data, fid: {
            "state_changed": _folder_status(data, fid).get("stateChanged"),
            "sequence": _folder_status(data, fid).get("sequence"),
        },
    ),
    SyncthingFolderSensorEntityDescription(
        key="completion",
        translation_key="folder_completion",
        icon="mdi:percent",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        value_fn=lambda data, fid: round(
            _folder_completion(data, fid).get("completion", 0), 2
        ),
    ),
    SyncthingFolderSensorEntityDescription(
        key="need_bytes",
        translation_key="folder_need_bytes",
        icon="mdi:download-outline",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
        value_fn=lambda data, fid: _folder_status(data, fid).get("needBytes"),
    ),
    SyncthingFolderSensorEntityDescription(
        key="need_files",
        translation_key="folder_need_files",
        icon="mdi:file-alert-outline",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, fid: _folder_status(data, fid).get("needFiles"),
    ),
    SyncthingFolderSensorEntityDescription(
        key="global_bytes",
        translation_key="folder_global_bytes",
        icon="mdi:database",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
        entity_category=EntityCategory.DIAGNOSTIC,

        value_fn=lambda data, fid: _folder_status(data, fid).get("globalBytes"),
    ),
    SyncthingFolderSensorEntityDescription(
        key="global_files",
        translation_key="folder_global_files",
        icon="mdi:file-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,

        value_fn=lambda data, fid: _folder_status(data, fid).get("globalFiles"),
    ),
    SyncthingFolderSensorEntityDescription(
        key="in_sync_bytes",
        translation_key="folder_in_sync_bytes",
        icon="mdi:database-check",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
        entity_category=EntityCategory.DIAGNOSTIC,

        value_fn=lambda data, fid: _folder_status(data, fid).get("inSyncBytes"),
    ),
    SyncthingFolderSensorEntityDescription(
        key="in_sync_files",
        translation_key="folder_in_sync_files",
        icon="mdi:file-check",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,

        value_fn=lambda data, fid: _folder_status(data, fid).get("inSyncFiles"),
    ),
    SyncthingFolderSensorEntityDescription(
        key="local_bytes",
        translation_key="folder_local_bytes",
        icon="mdi:database-outline",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
        entity_category=EntityCategory.DIAGNOSTIC,

        value_fn=lambda data, fid: _folder_status(data, fid).get("localBytes"),
    ),
    SyncthingFolderSensorEntityDescription(
        key="local_files",
        translation_key="folder_local_files",
        icon="mdi:file-multiple-outline",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,

        value_fn=lambda data, fid: _folder_status(data, fid).get("localFiles"),
    ),
    SyncthingFolderSensorEntityDescription(
        key="pull_errors",
        translation_key="folder_pull_errors",
        icon="mdi:alert-circle-outline",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, fid: _folder_status(data, fid).get("pullErrors"),
    ),
    SyncthingFolderSensorEntityDescription(
        key="last_scan",
        translation_key="folder_last_scan",
        icon="mdi:calendar-clock",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data, fid: datetime.fromisoformat(v) if (v := _folder_stats(data, fid).get("lastScan")) else None,
    ),
    SyncthingFolderSensorEntityDescription(
        key="last_file",
        translation_key="folder_last_file",
        icon="mdi:file-check-outline",
        value_fn=lambda data, fid: (
            (_folder_stats(data, fid).get("lastFile") or {}).get("filename")
        ),
        attr_fn=lambda data, fid: {
            "at": (_folder_stats(data, fid).get("lastFile") or {}).get("at"),
        },
    ),
)


# --- Device sensor definitions ---


def _device_connection(data: SyncthingData, did: str) -> dict[str, Any]:
    """Get device connection dict."""
    return data.connections.get("connections", {}).get(did, {})


def _device_stats_entry(data: SyncthingData, did: str) -> dict[str, Any]:
    """Get device stats dict."""
    return data.device_stats.get(did, {})


DEVICE_SENSORS: tuple[SyncthingDeviceSensorEntityDescription, ...] = (
    SyncthingDeviceSensorEntityDescription(
        key="connection_type",
        translation_key="device_connection_type",
        icon="mdi:network-outline",
        entity_category=EntityCategory.DIAGNOSTIC,

        value_fn=lambda data, did: _device_connection(data, did).get("type"),
    ),
    SyncthingDeviceSensorEntityDescription(
        key="address",
        translation_key="device_address",
        icon="mdi:ip-network",
        entity_category=EntityCategory.DIAGNOSTIC,

        value_fn=lambda data, did: _device_connection(data, did).get("address"),
    ),
    SyncthingDeviceSensorEntityDescription(
        key="client_version",
        translation_key="device_client_version",
        icon="mdi:tag",
        entity_category=EntityCategory.DIAGNOSTIC,

        value_fn=lambda data, did: _device_connection(data, did).get("clientVersion"),
    ),
    SyncthingDeviceSensorEntityDescription(
        key="last_seen",
        translation_key="device_last_seen",
        icon="mdi:clock-check-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data, did: datetime.fromisoformat(v) if (v := _device_stats_entry(data, did).get("lastSeen")) else None,
    ),
    SyncthingDeviceSensorEntityDescription(
        key="in_bytes",
        translation_key="device_in_bytes",
        icon="mdi:download",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
        value_fn=lambda data, did: _device_connection(data, did).get("inBytesTotal"),
    ),
    SyncthingDeviceSensorEntityDescription(
        key="out_bytes",
        translation_key="device_out_bytes",
        icon="mdi:upload",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
        value_fn=lambda data, did: _device_connection(data, did).get("outBytesTotal"),
    ),
)


# --- Setup ---


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SyncthingConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Syncthing sensors."""
    coordinator = entry.runtime_data

    entities: list[SensorEntity] = [
        SyncthingSystemSensor(coordinator, description, entry.entry_id)
        for description in SYSTEM_SENSORS
    ]

    for folder in coordinator.data.config_folders:
        folder_id = folder["id"]
        folder_label = folder.get("label") or folder_id
        for description in FOLDER_SENSORS:
            entities.append(
                SyncthingFolderSensor(
                    coordinator, description, entry.entry_id, folder_id, folder_label
                )
            )

    my_id = coordinator.data.system_status.get("myID", "")
    for device in coordinator.data.config_devices:
        device_id = device["deviceID"]
        if device_id == my_id:
            continue
        device_name = device.get("name") or device_id[:7]
        for description in DEVICE_SENSORS:
            entities.append(
                SyncthingDeviceSensor(
                    coordinator, description, entry.entry_id, device_id, device_name
                )
            )

    async_add_entities(entities)


# --- Entity classes ---


class SyncthingSystemSensor(CoordinatorEntity[SyncthingCoordinator], SensorEntity):
    """Sensor for system-level Syncthing data."""

    entity_description: SyncthingSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SyncthingCoordinator,
        description: SyncthingSensorEntityDescription,
        entry_id: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": "Syncthing",
            "manufacturer": "Syncthing Foundation",
            "sw_version": coordinator.data.version.get("version") if coordinator.data else None,
        }

    @property
    def native_value(self) -> Any:
        """Return sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if self.entity_description.attr_fn:
            return self.entity_description.attr_fn(self.coordinator.data)
        return None


class SyncthingFolderSensor(CoordinatorEntity[SyncthingCoordinator], SensorEntity):
    """Sensor for per-folder Syncthing data."""

    entity_description: SyncthingFolderSensorEntityDescription
    _attr_has_entity_name = True
    _unrecorded_attributes = frozenset({"sequence"})

    def __init__(
        self,
        coordinator: SyncthingCoordinator,
        description: SyncthingFolderSensorEntityDescription,
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
    def native_value(self) -> Any:
        """Return sensor value."""
        return self.entity_description.value_fn(self.coordinator.data, self._folder_id)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if self.entity_description.attr_fn:
            return self.entity_description.attr_fn(self.coordinator.data, self._folder_id)
        return None


class SyncthingDeviceSensor(CoordinatorEntity[SyncthingCoordinator], SensorEntity):
    """Sensor for per-device Syncthing data."""

    entity_description: SyncthingDeviceSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SyncthingCoordinator,
        description: SyncthingDeviceSensorEntityDescription,
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
    def native_value(self) -> Any:
        """Return sensor value."""
        return self.entity_description.value_fn(self.coordinator.data, self._device_id)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        if self.entity_description.attr_fn:
            return self.entity_description.attr_fn(self.coordinator.data, self._device_id)
        return None
