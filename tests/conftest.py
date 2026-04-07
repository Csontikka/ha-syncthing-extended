"""Test fixtures for Syncthing Extended."""
from __future__ import annotations

import asyncio
import copy
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.syncthing.coordinator import SyncthingData


# Reset event loop policy — HA overrides it with a custom one that breaks on Windows
# under pytest-socket's socket blocking.
@pytest.fixture(scope="session", autouse=True)
def reset_event_loop_policy():
    """Use default asyncio event loop policy instead of HA's custom one."""
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
    yield
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

# --- Mock API responses ---

MOCK_VERSION = {
    "arch": "amd64",
    "longVersion": "syncthing v1.29.0 'Fluorine Phosphate' (go1.22.0 linux-amd64) ld@build",
    "os": "linux",
    "version": "v1.29.0",
}

MOCK_SYSTEM_STATUS = {
    "alloc": 30618136,
    "sys": 42092792,
    "goroutines": 49,
    "myID": "P56IOI7-MZJNU2Y-IQGDREY-DM2MGTI-MNT4YXL-CLFRA3N-SMUX2ZC-2HXNUQQ",
    "startTime": "2024-01-01T00:00:00Z",
    "uptime": 2635,
    "cpuPercent": 0,
    "discoveryEnabled": True,
}

MOCK_CONNECTIONS = {
    "connections": {
        "DEVICE2ID-MZJNU2Y-IQGDREY-DM2MGTI-MNT4YXL-CLFRA3N-SMUX2ZC-ABCDEFG": {
            "address": "192.168.1.10:22000",
            "at": "2024-01-01T12:00:00Z",
            "clientVersion": "v1.28.0",
            "connected": True,
            "inBytesTotal": 1024000,
            "outBytesTotal": 512000,
            "isLocal": True,
            "paused": False,
            "startedAt": "2024-01-01T10:00:00Z",
            "type": "tcp-client",
        }
    },
    "total": {
        "at": "2024-01-01T12:00:00Z",
        "inBytesTotal": 2048000,
        "outBytesTotal": 1024000,
    },
}

MOCK_CONFIG_DEVICES = [
    {
        "deviceID": "P56IOI7-MZJNU2Y-IQGDREY-DM2MGTI-MNT4YXL-CLFRA3N-SMUX2ZC-2HXNUQQ",
        "name": "This Device",
        "addresses": ["dynamic"],
        "paused": False,
    },
    {
        "deviceID": "DEVICE2ID-MZJNU2Y-IQGDREY-DM2MGTI-MNT4YXL-CLFRA3N-SMUX2ZC-ABCDEFG",
        "name": "Laptop",
        "addresses": ["dynamic", "tcp://192.168.1.10:22000"],
        "paused": False,
    },
]

MOCK_CONFIG_FOLDERS = [
    {
        "id": "abcd-1234",
        "label": "Documents",
        "path": "/home/user/Documents",
        "type": "sendreceive",
        "paused": False,
        "devices": [
            {"deviceID": "DEVICE2ID-MZJNU2Y-IQGDREY-DM2MGTI-MNT4YXL-CLFRA3N-SMUX2ZC-ABCDEFG"}
        ],
    },
    {
        "id": "efgh-5678",
        "label": "Photos",
        "path": "/home/user/Photos",
        "type": "sendreceive",
        "paused": True,
        "devices": [],
    },
]

MOCK_FOLDER_STATUS = {
    "abcd-1234": {
        "globalBytes": 156793013575,
        "globalFiles": 7823,
        "globalDeleted": 12,
        "inSyncBytes": 156783224334,
        "inSyncFiles": 7811,
        "localBytes": 156783224334,
        "localFiles": 7811,
        "needBytes": 9789241,
        "needFiles": 12,
        "needDeletes": 0,
        "pullErrors": 0,
        "state": "idle",
        "stateChanged": "2024-01-01T12:00:00Z",
        "sequence": 1234,
    },
    "efgh-5678": {
        "globalBytes": 50000000,
        "globalFiles": 500,
        "globalDeleted": 0,
        "inSyncBytes": 40000000,
        "inSyncFiles": 400,
        "needBytes": 10000000,
        "needFiles": 100,
        "pullErrors": 2,
        "state": "syncing",
        "stateChanged": "2024-01-01T11:00:00Z",
        "sequence": 500,
    },
}

MOCK_FOLDER_COMPLETION = {
    "abcd-1234": {
        "completion": 99.9937,
        "globalBytes": 156793013575,
        "needBytes": 9789241,
        "globalItems": 7823,
        "needItems": 12,
        "needDeletes": 0,
        "remoteState": "valid",
        "sequence": 1234,
    },
    "efgh-5678": {
        "completion": 80.0,
        "globalBytes": 50000000,
        "needBytes": 10000000,
        "globalItems": 500,
        "needItems": 100,
        "needDeletes": 0,
        "remoteState": "valid",
        "sequence": 500,
    },
}

MOCK_FOLDER_STATS = {
    "abcd-1234": {
        "lastScan": "2024-01-01T12:00:00Z",
        "lastFile": {
            "filename": "documents/report.pdf",
            "at": "2024-01-01T11:55:00Z",
        },
    },
    "efgh-5678": {
        "lastScan": "2024-01-01T10:00:00Z",
        "lastFile": None,
    },
}

MOCK_DEVICE_STATS = {
    "DEVICE2ID-MZJNU2Y-IQGDREY-DM2MGTI-MNT4YXL-CLFRA3N-SMUX2ZC-ABCDEFG": {
        "lastSeen": "2024-01-01T11:59:00Z",
        "lastConnectionDurationS": 3600.5,
    }
}


def build_mock_coordinator_data() -> SyncthingData:
    """Build a SyncthingData instance with deep-copied mock data."""
    return SyncthingData(
        version=copy.deepcopy(MOCK_VERSION),
        system_status=copy.deepcopy(MOCK_SYSTEM_STATUS),
        connections=copy.deepcopy(MOCK_CONNECTIONS),
        config_devices=copy.deepcopy(MOCK_CONFIG_DEVICES),
        config_folders=copy.deepcopy(MOCK_CONFIG_FOLDERS),
        folder_status=copy.deepcopy(MOCK_FOLDER_STATUS),
        folder_completion=copy.deepcopy(MOCK_FOLDER_COMPLETION),
        folder_stats=copy.deepcopy(MOCK_FOLDER_STATS),
        device_stats=copy.deepcopy(MOCK_DEVICE_STATS),
    )


def build_mock_api(healthy: bool = True, auth_error: bool = False) -> MagicMock:
    """Build a mock SyncthingApi."""
    from custom_components.syncthing.api import (
        SyncthingAuthError,
        SyncthingConnectionError,
    )

    api = MagicMock()
    api.check_health = AsyncMock(return_value=healthy)

    if auth_error:
        api.get_system_status = AsyncMock(side_effect=SyncthingAuthError("Invalid API key"))
    elif not healthy:
        api.get_system_status = AsyncMock(
            side_effect=SyncthingConnectionError("Cannot connect")
        )
    else:
        api.get_system_status = AsyncMock(return_value=MOCK_SYSTEM_STATUS)

    api.get_version = AsyncMock(return_value=MOCK_VERSION)
    api.get_connections = AsyncMock(return_value=MOCK_CONNECTIONS)
    api.get_config_devices = AsyncMock(return_value=MOCK_CONFIG_DEVICES)
    api.get_config_folders = AsyncMock(return_value=MOCK_CONFIG_FOLDERS)
    api.get_device_stats = AsyncMock(return_value=MOCK_DEVICE_STATS)
    api.get_folder_stats = AsyncMock(return_value=MOCK_FOLDER_STATS)
    api.get_folder_status = AsyncMock(
        side_effect=lambda fid: MOCK_FOLDER_STATUS.get(fid, {})
    )
    api.get_folder_completion = AsyncMock(
        side_effect=lambda fid: MOCK_FOLDER_COMPLETION.get(fid, {})
    )
    api.scan_folder = AsyncMock(return_value=True)
    api.scan_all_folders = AsyncMock(return_value=True)
    api.pause_device = AsyncMock(return_value=True)
    api.resume_device = AsyncMock(return_value=True)
    api.pause_all = AsyncMock(return_value=True)
    api.resume_all = AsyncMock(return_value=True)

    return api
