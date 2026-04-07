"""Tests for Syncthing sensor entities."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.syncthing.sensor import (
    SYSTEM_SENSORS,
    FOLDER_SENSORS,
    DEVICE_SENSORS,
    SyncthingSystemSensor,
    SyncthingFolderSensor,
    SyncthingDeviceSensor,
)
from tests.conftest import build_mock_coordinator_data, build_mock_api


def make_coordinator(data=None):
    coordinator = MagicMock()
    coordinator.data = data or build_mock_coordinator_data()
    coordinator.api = build_mock_api()
    return coordinator


# --- System sensors ---

def test_system_sensor_version():
    coord = make_coordinator()
    desc = next(d for d in SYSTEM_SENSORS if d.key == "version")
    entity = SyncthingSystemSensor(coord, desc, "test_entry")
    assert entity.native_value == "v1.29.0"
    assert entity.extra_state_attributes["os"] == "linux"


def test_system_sensor_uptime():
    coord = make_coordinator()
    desc = next(d for d in SYSTEM_SENSORS if d.key == "uptime")
    entity = SyncthingSystemSensor(coord, desc, "test_entry")
    assert entity.native_value == 2635


def test_system_sensor_my_id_truncated():
    coord = make_coordinator()
    desc = next(d for d in SYSTEM_SENSORS if d.key == "my_id")
    entity = SyncthingSystemSensor(coord, desc, "test_entry")
    value = entity.native_value
    assert value.endswith("...")
    assert len(value) == 10  # 7 chars + "..."
    assert entity.extra_state_attributes["full_id"].startswith("P56IOI7")


def test_system_sensor_total_in_bytes():
    coord = make_coordinator()
    desc = next(d for d in SYSTEM_SENSORS if d.key == "total_in_bytes")
    entity = SyncthingSystemSensor(coord, desc, "test_entry")
    assert entity.native_value == 2048000


def test_system_sensor_total_out_bytes():
    coord = make_coordinator()
    desc = next(d for d in SYSTEM_SENSORS if d.key == "total_out_bytes")
    entity = SyncthingSystemSensor(coord, desc, "test_entry")
    assert entity.native_value == 1024000


# --- Folder sensors ---

def test_folder_sensor_state_idle():
    coord = make_coordinator()
    desc = next(d for d in FOLDER_SENSORS if d.key == "state")
    entity = SyncthingFolderSensor(coord, desc, "test_entry", "abcd-1234", "Documents")
    assert entity.native_value == "idle"


def test_folder_sensor_state_syncing():
    coord = make_coordinator()
    desc = next(d for d in FOLDER_SENSORS if d.key == "state")
    entity = SyncthingFolderSensor(coord, desc, "test_entry", "efgh-5678", "Photos")
    assert entity.native_value == "syncing"


def test_folder_sensor_completion():
    coord = make_coordinator()
    desc = next(d for d in FOLDER_SENSORS if d.key == "completion")
    entity = SyncthingFolderSensor(coord, desc, "test_entry", "abcd-1234", "Documents")
    assert entity.native_value == pytest.approx(99.99)


def test_folder_sensor_completion_partial():
    coord = make_coordinator()
    desc = next(d for d in FOLDER_SENSORS if d.key == "completion")
    entity = SyncthingFolderSensor(coord, desc, "test_entry", "efgh-5678", "Photos")
    assert entity.native_value == pytest.approx(80.0)


def test_folder_sensor_need_bytes():
    coord = make_coordinator()
    desc = next(d for d in FOLDER_SENSORS if d.key == "need_bytes")
    entity = SyncthingFolderSensor(coord, desc, "test_entry", "abcd-1234", "Documents")
    assert entity.native_value == 9789241


def test_folder_sensor_need_files():
    coord = make_coordinator()
    desc = next(d for d in FOLDER_SENSORS if d.key == "need_files")
    entity = SyncthingFolderSensor(coord, desc, "test_entry", "abcd-1234", "Documents")
    assert entity.native_value == 12


def test_folder_sensor_pull_errors_zero():
    coord = make_coordinator()
    desc = next(d for d in FOLDER_SENSORS if d.key == "pull_errors")
    entity = SyncthingFolderSensor(coord, desc, "test_entry", "abcd-1234", "Documents")
    assert entity.native_value == 0


def test_folder_sensor_pull_errors_nonzero():
    coord = make_coordinator()
    desc = next(d for d in FOLDER_SENSORS if d.key == "pull_errors")
    entity = SyncthingFolderSensor(coord, desc, "test_entry", "efgh-5678", "Photos")
    assert entity.native_value == 2


def test_folder_sensor_last_file():
    coord = make_coordinator()
    desc = next(d for d in FOLDER_SENSORS if d.key == "last_file")
    entity = SyncthingFolderSensor(coord, desc, "test_entry", "abcd-1234", "Documents")
    assert entity.native_value == "documents/report.pdf"


def test_folder_sensor_last_file_none():
    coord = make_coordinator()
    desc = next(d for d in FOLDER_SENSORS if d.key == "last_file")
    entity = SyncthingFolderSensor(coord, desc, "test_entry", "efgh-5678", "Photos")
    assert entity.native_value is None


def test_folder_sensor_unique_id():
    coord = make_coordinator()
    desc = next(d for d in FOLDER_SENSORS if d.key == "state")
    entity = SyncthingFolderSensor(coord, desc, "entry1", "abcd-1234", "Documents")
    assert entity.unique_id == "entry1_folder_abcd-1234_state"


# --- Device sensors ---

DEVICE_ID = "DEVICE2ID-MZJNU2Y-IQGDREY-DM2MGTI-MNT4YXL-CLFRA3N-SMUX2ZC-ABCDEFG"


def test_device_sensor_connection_type():
    coord = make_coordinator()
    desc = next(d for d in DEVICE_SENSORS if d.key == "connection_type")
    entity = SyncthingDeviceSensor(coord, desc, "test_entry", DEVICE_ID, "Laptop")
    assert entity.native_value == "tcp-client"


def test_device_sensor_address():
    coord = make_coordinator()
    desc = next(d for d in DEVICE_SENSORS if d.key == "address")
    entity = SyncthingDeviceSensor(coord, desc, "test_entry", DEVICE_ID, "Laptop")
    assert entity.native_value == "192.168.1.10:22000"


def test_device_sensor_client_version():
    coord = make_coordinator()
    desc = next(d for d in DEVICE_SENSORS if d.key == "client_version")
    entity = SyncthingDeviceSensor(coord, desc, "test_entry", DEVICE_ID, "Laptop")
    assert entity.native_value == "v1.28.0"


def test_device_sensor_in_bytes():
    coord = make_coordinator()
    desc = next(d for d in DEVICE_SENSORS if d.key == "in_bytes")
    entity = SyncthingDeviceSensor(coord, desc, "test_entry", DEVICE_ID, "Laptop")
    assert entity.native_value == 1024000


def test_device_sensor_last_seen():
    coord = make_coordinator()
    desc = next(d for d in DEVICE_SENSORS if d.key == "last_seen")
    entity = SyncthingDeviceSensor(coord, desc, "test_entry", DEVICE_ID, "Laptop")
    from datetime import datetime, timezone
    assert entity.native_value == datetime(2024, 1, 1, 11, 59, 0, tzinfo=timezone.utc)


def test_device_sensor_unique_id():
    coord = make_coordinator()
    desc = next(d for d in DEVICE_SENSORS if d.key == "connection_type")
    entity = SyncthingDeviceSensor(coord, desc, "entry1", DEVICE_ID, "Laptop")
    assert entity.unique_id == f"entry1_device_{DEVICE_ID}_connection_type"


def test_device_sensor_missing_device_returns_none():
    """Device not in connections → sensor returns None gracefully."""
    coord = make_coordinator()
    desc = next(d for d in DEVICE_SENSORS if d.key == "connection_type")
    entity = SyncthingDeviceSensor(coord, desc, "entry1", "NONEXISTENT-DEVICE-ID", "Ghost")
    assert entity.native_value is None
