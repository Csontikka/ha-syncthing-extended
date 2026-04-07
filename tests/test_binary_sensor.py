"""Tests for Syncthing binary sensor platform."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from custom_components.syncthing.binary_sensor import (
    DEVICE_BINARY_SENSORS,
    FOLDER_BINARY_SENSORS,
    SYSTEM_BINARY_SENSORS,
    SyncthingDeviceBinarySensor,
    SyncthingFolderBinarySensor,
    SyncthingSystemBinarySensor,
    async_setup_entry,
)
from tests.conftest import (
    MOCK_SYSTEM_STATUS,
    build_mock_coordinator_data,
)

ENTRY_ID = "test_entry_id"
DEVICE_ID = "DEVICE2ID-MZJNU2Y-IQGDREY-DM2MGTI-MNT4YXL-CLFRA3N-SMUX2ZC-ABCDEFG"


def make_coordinator():
    coordinator = MagicMock()
    coordinator.data = build_mock_coordinator_data()
    return coordinator


# --- System binary sensor value_fn ---

def test_running_value_fn_true():
    data = build_mock_coordinator_data()
    desc = SYSTEM_BINARY_SENSORS[0]
    assert desc.value_fn(data) is True


def test_running_value_fn_false():
    data = build_mock_coordinator_data()
    data.system_status["myID"] = ""
    desc = SYSTEM_BINARY_SENSORS[0]
    assert desc.value_fn(data) is False


def test_running_attr_fn():
    data = build_mock_coordinator_data()
    desc = SYSTEM_BINARY_SENSORS[0]
    attrs = desc.attr_fn(data)
    assert "goroutines" in attrs
    assert attrs["goroutines"] == MOCK_SYSTEM_STATUS["goroutines"]
    assert "alloc_bytes" in attrs
    assert "start_time" in attrs


# --- Folder binary sensor value_fn ---

def test_folder_error_false_when_no_errors():
    data = build_mock_coordinator_data()
    error_desc = next(d for d in FOLDER_BINARY_SENSORS if d.key == "error")
    assert error_desc.value_fn(data, "abcd-1234") is False


def test_folder_error_true_when_pull_errors():
    data = build_mock_coordinator_data()
    error_desc = next(d for d in FOLDER_BINARY_SENSORS if d.key == "error")
    assert error_desc.value_fn(data, "efgh-5678") is True


def test_folder_error_attr_fn():
    data = build_mock_coordinator_data()
    error_desc = next(d for d in FOLDER_BINARY_SENSORS if d.key == "error")
    attrs = error_desc.attr_fn(data, "efgh-5678")
    assert attrs["pull_errors"] == 2
    assert attrs["state"] == "syncing"


def test_folder_syncing_true():
    data = build_mock_coordinator_data()
    syncing_desc = next(d for d in FOLDER_BINARY_SENSORS if d.key == "syncing")
    assert syncing_desc.value_fn(data, "efgh-5678") is True


def test_folder_syncing_false():
    data = build_mock_coordinator_data()
    syncing_desc = next(d for d in FOLDER_BINARY_SENSORS if d.key == "syncing")
    assert syncing_desc.value_fn(data, "abcd-1234") is False


def test_folder_paused_true():
    data = build_mock_coordinator_data()
    paused_desc = next(d for d in FOLDER_BINARY_SENSORS if d.key == "paused")
    assert paused_desc.value_fn(data, "efgh-5678") is True


def test_folder_paused_false():
    data = build_mock_coordinator_data()
    paused_desc = next(d for d in FOLDER_BINARY_SENSORS if d.key == "paused")
    assert paused_desc.value_fn(data, "abcd-1234") is False


def test_folder_paused_missing_folder():
    data = build_mock_coordinator_data()
    paused_desc = next(d for d in FOLDER_BINARY_SENSORS if d.key == "paused")
    assert paused_desc.value_fn(data, "nonexistent") is False


# --- Device binary sensor value_fn ---

def test_device_connected_true():
    data = build_mock_coordinator_data()
    connected_desc = next(d for d in DEVICE_BINARY_SENSORS if d.key == "connected")
    assert connected_desc.value_fn(data, DEVICE_ID) is True


def test_device_connected_false_missing():
    data = build_mock_coordinator_data()
    connected_desc = next(d for d in DEVICE_BINARY_SENSORS if d.key == "connected")
    assert connected_desc.value_fn(data, "UNKNOWN-DEVICE") is False


def test_device_paused_false():
    data = build_mock_coordinator_data()
    paused_desc = next(d for d in DEVICE_BINARY_SENSORS if d.key == "paused")
    assert paused_desc.value_fn(data, DEVICE_ID) is False


# --- Entity class: SyncthingSystemBinarySensor ---

def test_system_binary_sensor_is_on():
    coordinator = make_coordinator()
    desc = SYSTEM_BINARY_SENSORS[0]
    entity = SyncthingSystemBinarySensor(coordinator, desc, ENTRY_ID)
    assert entity.is_on is True


def test_system_binary_sensor_unique_id():
    coordinator = make_coordinator()
    desc = SYSTEM_BINARY_SENSORS[0]
    entity = SyncthingSystemBinarySensor(coordinator, desc, ENTRY_ID)
    assert entity.unique_id == f"{ENTRY_ID}_running"


def test_system_binary_sensor_extra_attrs():
    coordinator = make_coordinator()
    desc = SYSTEM_BINARY_SENSORS[0]
    entity = SyncthingSystemBinarySensor(coordinator, desc, ENTRY_ID)
    attrs = entity.extra_state_attributes
    assert attrs is not None
    assert "goroutines" in attrs


# --- Entity class: SyncthingFolderBinarySensor ---

def test_folder_binary_sensor_is_on_error():
    coordinator = make_coordinator()
    desc = next(d for d in FOLDER_BINARY_SENSORS if d.key == "error")
    entity = SyncthingFolderBinarySensor(coordinator, desc, ENTRY_ID, "efgh-5678", "Photos")
    assert entity.is_on is True


def test_folder_binary_sensor_unique_id():
    coordinator = make_coordinator()
    desc = next(d for d in FOLDER_BINARY_SENSORS if d.key == "syncing")
    entity = SyncthingFolderBinarySensor(coordinator, desc, ENTRY_ID, "abcd-1234", "Documents")
    assert entity.unique_id == f"{ENTRY_ID}_folder_abcd-1234_syncing"


def test_folder_binary_sensor_extra_attrs():
    coordinator = make_coordinator()
    desc = next(d for d in FOLDER_BINARY_SENSORS if d.key == "error")
    entity = SyncthingFolderBinarySensor(coordinator, desc, ENTRY_ID, "efgh-5678", "Photos")
    attrs = entity.extra_state_attributes
    assert attrs is not None
    assert attrs["pull_errors"] == 2


def test_folder_binary_sensor_no_attr_fn():
    coordinator = make_coordinator()
    desc = next(d for d in FOLDER_BINARY_SENSORS if d.key == "paused")
    entity = SyncthingFolderBinarySensor(coordinator, desc, ENTRY_ID, "abcd-1234", "Documents")
    assert entity.extra_state_attributes is None


# --- Entity class: SyncthingDeviceBinarySensor ---

def test_device_binary_sensor_is_on():
    coordinator = make_coordinator()
    desc = next(d for d in DEVICE_BINARY_SENSORS if d.key == "connected")
    entity = SyncthingDeviceBinarySensor(coordinator, desc, ENTRY_ID, DEVICE_ID, "Laptop")
    assert entity.is_on is True


def test_device_binary_sensor_unique_id():
    coordinator = make_coordinator()
    desc = next(d for d in DEVICE_BINARY_SENSORS if d.key == "connected")
    entity = SyncthingDeviceBinarySensor(coordinator, desc, ENTRY_ID, DEVICE_ID, "Laptop")
    assert entity.unique_id == f"{ENTRY_ID}_device_{DEVICE_ID}_connected"


def test_device_binary_sensor_no_attr_fn():
    coordinator = make_coordinator()
    desc = next(d for d in DEVICE_BINARY_SENSORS if d.key == "connected")
    entity = SyncthingDeviceBinarySensor(coordinator, desc, ENTRY_ID, DEVICE_ID, "Laptop")
    assert entity.extra_state_attributes is None


def test_system_binary_sensor_no_attr_fn_returns_none():
    """Cover the extra_state_attributes None branch when attr_fn is absent."""
    from custom_components.syncthing.binary_sensor import (
        SyncthingBinarySensorEntityDescription,
    )
    from homeassistant.components.binary_sensor import BinarySensorDeviceClass

    coordinator = make_coordinator()
    desc = SyncthingBinarySensorEntityDescription(
        key="test_no_attr",
        translation_key="running",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda data: True,
        attr_fn=None,
    )
    entity = SyncthingSystemBinarySensor(coordinator, desc, ENTRY_ID)
    assert entity.extra_state_attributes is None


# --- async_setup_entry ---

def test_async_setup_entry_creates_entities():
    async def _run():
        coordinator = make_coordinator()
        entry = MagicMock()
        entry.runtime_data = coordinator
        entry.entry_id = ENTRY_ID

        added = []
        async_add_entities = MagicMock(side_effect=lambda entities: added.extend(entities))

        await async_setup_entry(MagicMock(), entry, async_add_entities)
        return added

    entities = asyncio.run(_run())
    # 1 system + 2 folders * 3 + 1 remote device * 2 = 1 + 6 + 2 = 9
    assert len(entities) == 9
    types = {type(e).__name__ for e in entities}
    assert "SyncthingSystemBinarySensor" in types
    assert "SyncthingFolderBinarySensor" in types
    assert "SyncthingDeviceBinarySensor" in types
