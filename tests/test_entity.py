"""Tests for the hub link of folder and remote-device entries."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from custom_components.syncthing_extended import entity
from custom_components.syncthing_extended.const import DOMAIN
from custom_components.syncthing_extended.entity import (
    SyncthingDeviceEntity,
    SyncthingFolderEntity,
    hub_link,
)
from tests.conftest import build_mock_coordinator_data

ENTRY_ID = "test_entry_id"


def make_coordinator(hub_device_id="hub-registry-id"):
    coordinator = MagicMock()
    coordinator.data = build_mock_coordinator_data()
    coordinator.hub_device_id = hub_device_id
    return coordinator


def test_hub_link_uses_identifier_on_cores_without_via_device_id():
    with patch.object(entity, "SUPPORTS_VIA_DEVICE_ID", False):
        assert hub_link(make_coordinator(), ENTRY_ID) == {
            "via_device": (DOMAIN, ENTRY_ID)
        }


def test_hub_link_uses_registry_id_of_the_hub_when_supported():
    with patch.object(entity, "SUPPORTS_VIA_DEVICE_ID", True):
        assert hub_link(make_coordinator(), ENTRY_ID) == {
            "via_device_id": "hub-registry-id"
        }


def test_hub_link_is_omitted_when_the_hub_is_not_registered():
    with patch.object(entity, "SUPPORTS_VIA_DEVICE_ID", True):
        assert hub_link(make_coordinator(hub_device_id=None), ENTRY_ID) == {}


def test_folder_and_device_entities_never_pass_deprecated_via_device_when_supported():
    with patch.object(entity, "SUPPORTS_VIA_DEVICE_ID", True):
        folder = SyncthingFolderEntity(make_coordinator(), ENTRY_ID, "abcd", "Docs")
        device = SyncthingDeviceEntity(make_coordinator(), ENTRY_ID, "DEV", "Laptop")

    for info in (folder.device_info, device.device_info):
        assert info["via_device_id"] == "hub-registry-id"
        assert "via_device" not in info
