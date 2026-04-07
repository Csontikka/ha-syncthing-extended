"""Tests for Syncthing sensor entity classes and value functions."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from custom_components.syncthing.sensor import (
    DEVICE_SENSORS,
    FOLDER_SENSORS,
    SYSTEM_SENSORS,
    SyncthingDeviceSensor,
    SyncthingFolderSensor,
    SyncthingSystemSensor,
)
from tests.conftest import build_mock_coordinator_data

ENTRY_ID = "test_entry_id"
DEVICE_ID = "DEVICE2ID-MZJNU2Y-IQGDREY-DM2MGTI-MNT4YXL-CLFRA3N-SMUX2ZC-ABCDEFG"


def make_coordinator():
    coordinator = MagicMock()
    coordinator.data = build_mock_coordinator_data()
    return coordinator


# --- SyncthingSystemSensor ---

def test_system_sensor_version_value():
    coordinator = make_coordinator()
    desc = next(d for d in SYSTEM_SENSORS if d.key == "version")
    entity = SyncthingSystemSensor(coordinator, desc, ENTRY_ID)
    assert entity.native_value == "v1.29.0"


def test_system_sensor_version_attrs():
    coordinator = make_coordinator()
    desc = next(d for d in SYSTEM_SENSORS if d.key == "version")
    entity = SyncthingSystemSensor(coordinator, desc, ENTRY_ID)
    attrs = entity.extra_state_attributes
    assert attrs["os"] == "linux"
    assert attrs["arch"] == "amd64"


def test_system_sensor_uptime_value():
    coordinator = make_coordinator()
    desc = next(d for d in SYSTEM_SENSORS if d.key == "uptime")
    entity = SyncthingSystemSensor(coordinator, desc, ENTRY_ID)
    assert entity.native_value == 2635


def test_system_sensor_uptime_no_attrs():
    coordinator = make_coordinator()
    desc = next(d for d in SYSTEM_SENSORS if d.key == "uptime")
    entity = SyncthingSystemSensor(coordinator, desc, ENTRY_ID)
    assert entity.extra_state_attributes is None


def test_system_sensor_my_id_value():
    coordinator = make_coordinator()
    desc = next(d for d in SYSTEM_SENSORS if d.key == "my_id")
    entity = SyncthingSystemSensor(coordinator, desc, ENTRY_ID)
    val = entity.native_value
    assert val.endswith("...")
    assert len(val) == 10  # 7 chars + "..."


def test_system_sensor_my_id_attrs():
    coordinator = make_coordinator()
    desc = next(d for d in SYSTEM_SENSORS if d.key == "my_id")
    entity = SyncthingSystemSensor(coordinator, desc, ENTRY_ID)
    attrs = entity.extra_state_attributes
    assert "full_id" in attrs
    assert len(attrs["full_id"]) > 7


def test_system_sensor_total_in_bytes():
    coordinator = make_coordinator()
    desc = next(d for d in SYSTEM_SENSORS if d.key == "total_in_bytes")
    entity = SyncthingSystemSensor(coordinator, desc, ENTRY_ID)
    assert entity.native_value == 2048000


def test_system_sensor_total_out_bytes():
    coordinator = make_coordinator()
    desc = next(d for d in SYSTEM_SENSORS if d.key == "total_out_bytes")
    entity = SyncthingSystemSensor(coordinator, desc, ENTRY_ID)
    assert entity.native_value == 1024000


def test_system_sensor_unique_id():
    coordinator = make_coordinator()
    desc = next(d for d in SYSTEM_SENSORS if d.key == "version")
    entity = SyncthingSystemSensor(coordinator, desc, ENTRY_ID)
    assert entity.unique_id == f"{ENTRY_ID}_version"


# --- SyncthingFolderSensor ---

def test_folder_sensor_state_value():
    coordinator = make_coordinator()
    desc = next(d for d in FOLDER_SENSORS if d.key == "state")
    entity = SyncthingFolderSensor(coordinator, desc, ENTRY_ID, "abcd-1234", "Documents")
    assert entity.native_value == "idle"


def test_folder_sensor_state_attrs():
    coordinator = make_coordinator()
    desc = next(d for d in FOLDER_SENSORS if d.key == "state")
    entity = SyncthingFolderSensor(coordinator, desc, ENTRY_ID, "abcd-1234", "Documents")
    attrs = entity.extra_state_attributes
    assert "state_changed" in attrs
    assert "sequence" in attrs


def test_folder_sensor_completion_value():
    coordinator = make_coordinator()
    desc = next(d for d in FOLDER_SENSORS if d.key == "completion")
    entity = SyncthingFolderSensor(coordinator, desc, ENTRY_ID, "abcd-1234", "Documents")
    assert entity.native_value == pytest.approx(99.99)  # round(99.9937, 2)


def test_folder_sensor_need_bytes_value():
    coordinator = make_coordinator()
    desc = next(d for d in FOLDER_SENSORS if d.key == "need_bytes")
    entity = SyncthingFolderSensor(coordinator, desc, ENTRY_ID, "abcd-1234", "Documents")
    assert entity.native_value == 9789241


def test_folder_sensor_need_files_value():
    coordinator = make_coordinator()
    desc = next(d for d in FOLDER_SENSORS if d.key == "need_files")
    entity = SyncthingFolderSensor(coordinator, desc, ENTRY_ID, "abcd-1234", "Documents")
    assert entity.native_value == 12


def test_folder_sensor_global_bytes():
    coordinator = make_coordinator()
    desc = next(d for d in FOLDER_SENSORS if d.key == "global_bytes")
    entity = SyncthingFolderSensor(coordinator, desc, ENTRY_ID, "abcd-1234", "Documents")
    assert entity.native_value == 156793013575


def test_folder_sensor_in_sync_bytes():
    coordinator = make_coordinator()
    desc = next(d for d in FOLDER_SENSORS if d.key == "in_sync_bytes")
    entity = SyncthingFolderSensor(coordinator, desc, ENTRY_ID, "abcd-1234", "Documents")
    assert entity.native_value == 156783224334


def test_folder_sensor_local_files():
    coordinator = make_coordinator()
    desc = next(d for d in FOLDER_SENSORS if d.key == "local_files")
    entity = SyncthingFolderSensor(coordinator, desc, ENTRY_ID, "abcd-1234", "Documents")
    assert entity.native_value == 7811


def test_folder_sensor_pull_errors_zero():
    coordinator = make_coordinator()
    desc = next(d for d in FOLDER_SENSORS if d.key == "pull_errors")
    entity = SyncthingFolderSensor(coordinator, desc, ENTRY_ID, "abcd-1234", "Documents")
    assert entity.native_value == 0


def test_folder_sensor_last_scan():
    coordinator = make_coordinator()
    desc = next(d for d in FOLDER_SENSORS if d.key == "last_scan")
    entity = SyncthingFolderSensor(coordinator, desc, ENTRY_ID, "abcd-1234", "Documents")
    from datetime import datetime, timezone
    assert entity.native_value == datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def test_folder_sensor_last_file():
    coordinator = make_coordinator()
    desc = next(d for d in FOLDER_SENSORS if d.key == "last_file")
    entity = SyncthingFolderSensor(coordinator, desc, ENTRY_ID, "abcd-1234", "Documents")
    assert entity.native_value == "documents/report.pdf"


def test_folder_sensor_last_file_none():
    coordinator = make_coordinator()
    desc = next(d for d in FOLDER_SENSORS if d.key == "last_file")
    entity = SyncthingFolderSensor(coordinator, desc, ENTRY_ID, "efgh-5678", "Photos")
    assert entity.native_value is None


def test_folder_sensor_last_file_attrs():
    coordinator = make_coordinator()
    desc = next(d for d in FOLDER_SENSORS if d.key == "last_file")
    entity = SyncthingFolderSensor(coordinator, desc, ENTRY_ID, "abcd-1234", "Documents")
    attrs = entity.extra_state_attributes
    assert "at" in attrs


def test_folder_sensor_no_attr_fn():
    coordinator = make_coordinator()
    desc = next(d for d in FOLDER_SENSORS if d.key == "completion")
    entity = SyncthingFolderSensor(coordinator, desc, ENTRY_ID, "abcd-1234", "Documents")
    assert entity.extra_state_attributes is None


def test_folder_sensor_unique_id():
    coordinator = make_coordinator()
    desc = next(d for d in FOLDER_SENSORS if d.key == "state")
    entity = SyncthingFolderSensor(coordinator, desc, ENTRY_ID, "abcd-1234", "Documents")
    assert entity.unique_id == f"{ENTRY_ID}_folder_abcd-1234_state"


# --- SyncthingDeviceSensor ---

def test_device_sensor_connection_type():
    coordinator = make_coordinator()
    desc = next(d for d in DEVICE_SENSORS if d.key == "connection_type")
    entity = SyncthingDeviceSensor(coordinator, desc, ENTRY_ID, DEVICE_ID, "Laptop")
    assert entity.native_value == "tcp-client"


def test_device_sensor_address():
    coordinator = make_coordinator()
    desc = next(d for d in DEVICE_SENSORS if d.key == "address")
    entity = SyncthingDeviceSensor(coordinator, desc, ENTRY_ID, DEVICE_ID, "Laptop")
    assert entity.native_value == "192.168.1.10:22000"


def test_device_sensor_client_version():
    coordinator = make_coordinator()
    desc = next(d for d in DEVICE_SENSORS if d.key == "client_version")
    entity = SyncthingDeviceSensor(coordinator, desc, ENTRY_ID, DEVICE_ID, "Laptop")
    assert entity.native_value == "v1.28.0"


def test_device_sensor_last_seen():
    coordinator = make_coordinator()
    desc = next(d for d in DEVICE_SENSORS if d.key == "last_seen")
    entity = SyncthingDeviceSensor(coordinator, desc, ENTRY_ID, DEVICE_ID, "Laptop")
    from datetime import datetime, timezone
    assert entity.native_value == datetime(2024, 1, 1, 11, 59, 0, tzinfo=timezone.utc)


def test_device_sensor_in_bytes():
    coordinator = make_coordinator()
    desc = next(d for d in DEVICE_SENSORS if d.key == "in_bytes")
    entity = SyncthingDeviceSensor(coordinator, desc, ENTRY_ID, DEVICE_ID, "Laptop")
    assert entity.native_value == 1024000


def test_device_sensor_out_bytes():
    coordinator = make_coordinator()
    desc = next(d for d in DEVICE_SENSORS if d.key == "out_bytes")
    entity = SyncthingDeviceSensor(coordinator, desc, ENTRY_ID, DEVICE_ID, "Laptop")
    assert entity.native_value == 512000


def test_device_sensor_unknown_device_returns_none():
    coordinator = make_coordinator()
    desc = next(d for d in DEVICE_SENSORS if d.key == "in_bytes")
    entity = SyncthingDeviceSensor(coordinator, desc, ENTRY_ID, "UNKNOWN", "Unknown")
    assert entity.native_value is None


def test_device_sensor_no_attr_fn():
    coordinator = make_coordinator()
    desc = next(d for d in DEVICE_SENSORS if d.key == "in_bytes")
    entity = SyncthingDeviceSensor(coordinator, desc, ENTRY_ID, DEVICE_ID, "Laptop")
    assert entity.extra_state_attributes is None


def test_device_sensor_unique_id():
    coordinator = make_coordinator()
    desc = next(d for d in DEVICE_SENSORS if d.key == "in_bytes")
    entity = SyncthingDeviceSensor(coordinator, desc, ENTRY_ID, DEVICE_ID, "Laptop")
    assert entity.unique_id == f"{ENTRY_ID}_device_{DEVICE_ID}_in_bytes"


# --- async_setup_entry for sensor platform ---

def test_sensor_async_setup_entry_creates_entities():
    import asyncio
    from unittest.mock import MagicMock
    from custom_components.syncthing.sensor import async_setup_entry

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
    # 5 system + 2 folders * 13 + 1 remote device * 6 = 5 + 26 + 6 = 37
    assert len(entities) == 37
    types = {type(e).__name__ for e in entities}
    assert "SyncthingSystemSensor" in types
    assert "SyncthingFolderSensor" in types
    assert "SyncthingDeviceSensor" in types
