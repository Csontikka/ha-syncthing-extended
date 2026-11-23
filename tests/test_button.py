"""Tests for Syncthing button platform."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.syncthing_extended.button import (
    SyncthingDevicePauseButton,
    SyncthingDeviceResumeButton,
    SyncthingFolderPauseButton,
    SyncthingFolderResumeButton,
    SyncthingFolderScanButton,
    SyncthingScanAllButton,
    async_setup_entry,
)
from tests.conftest import build_mock_api, build_mock_coordinator_data

ENTRY_ID = "test_entry_id"


def make_coordinator():
    coordinator = MagicMock()
    coordinator.data = build_mock_coordinator_data()
    coordinator.api = build_mock_api()
    coordinator.async_refresh = AsyncMock()
    return coordinator


# --- SyncthingScanAllButton ---

def test_scan_all_button_unique_id():
    coordinator = make_coordinator()
    button = SyncthingScanAllButton(coordinator, ENTRY_ID)
    assert button.unique_id == f"{ENTRY_ID}_scan_all"


def test_scan_all_button_press():
    async def _run():
        coordinator = make_coordinator()
        button = SyncthingScanAllButton(coordinator, ENTRY_ID)
        await button.async_press()
        return coordinator

    coordinator = asyncio.run(_run())
    coordinator.api.scan_all_folders.assert_called_once()
    coordinator.async_refresh.assert_called_once()


# --- SyncthingFolderScanButton ---

def test_folder_scan_button_unique_id():
    coordinator = make_coordinator()
    button = SyncthingFolderScanButton(coordinator, ENTRY_ID, "abcd-1234", "Documents")
    assert button.unique_id == f"{ENTRY_ID}_folder_abcd-1234_scan"


def test_folder_scan_button_press():
    async def _run():
        coordinator = make_coordinator()
        button = SyncthingFolderScanButton(coordinator, ENTRY_ID, "abcd-1234", "Documents")
        await button.async_press()
        return coordinator

    coordinator = asyncio.run(_run())
    coordinator.api.scan_folder.assert_called_once_with("abcd-1234")
    coordinator.async_refresh.assert_called_once()


# --- async_setup_entry ---

def test_async_setup_entry_creates_buttons():
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
    # 1 scan_all + 2 folders × 3 (scan/pause/resume) + 1 device × 2 (pause/resume) = 9
    assert len(entities) == 9
    types = [type(e).__name__ for e in entities]
    assert "SyncthingScanAllButton" in types
    assert types.count("SyncthingFolderScanButton") == 2
    assert types.count("SyncthingFolderPauseButton") == 2
    assert types.count("SyncthingFolderResumeButton") == 2
    assert types.count("SyncthingDevicePauseButton") == 1
    assert types.count("SyncthingDeviceResumeButton") == 1


# --- SyncthingFolderPauseButton / ResumeButton press ---

def test_folder_pause_button_press():
    async def _run():
        coordinator = make_coordinator()
        coordinator.api.pause_folder = AsyncMock(return_value=True)
        button = SyncthingFolderPauseButton(coordinator, ENTRY_ID, "abcd-1234", "Documents")
        await button.async_press()
        return coordinator

    coordinator = asyncio.run(_run())
    coordinator.api.pause_folder.assert_called_once_with("abcd-1234")
    coordinator.async_refresh.assert_called_once()


def test_folder_resume_button_press():
    async def _run():
        coordinator = make_coordinator()
        coordinator.api.resume_folder = AsyncMock(return_value=True)
        button = SyncthingFolderResumeButton(coordinator, ENTRY_ID, "abcd-1234", "Documents")
        await button.async_press()
        return coordinator

    coordinator = asyncio.run(_run())
    coordinator.api.resume_folder.assert_called_once_with("abcd-1234")
    coordinator.async_refresh.assert_called_once()


# --- SyncthingDevicePauseButton / ResumeButton press ---

def test_device_pause_button_press():
    async def _run():
        coordinator = make_coordinator()
        button = SyncthingDevicePauseButton(coordinator, ENTRY_ID, "DEV123", "Laptop")
        await button.async_press()
        return coordinator

    coordinator = asyncio.run(_run())
    coordinator.api.pause_device.assert_called_once_with("DEV123")
    coordinator.async_refresh.assert_called_once()


def test_device_resume_button_press():
    async def _run():
        coordinator = make_coordinator()
        button = SyncthingDeviceResumeButton(coordinator, ENTRY_ID, "DEV123", "Laptop")
        await button.async_press()
        return coordinator

    coordinator = asyncio.run(_run())
    coordinator.api.resume_device.assert_called_once_with("DEV123")
    coordinator.async_refresh.assert_called_once()


def test_folder_pause_button_unique_id():
    coordinator = make_coordinator()
    button = SyncthingFolderPauseButton(coordinator, ENTRY_ID, "abcd-1234", "Documents")
    assert button.unique_id == f"{ENTRY_ID}_folder_abcd-1234_pause"


def test_device_pause_button_unique_id():
    coordinator = make_coordinator()
    button = SyncthingDevicePauseButton(coordinator, ENTRY_ID, "DEV123", "Laptop")
    assert button.unique_id == f"{ENTRY_ID}_device_DEV123_pause"


# --- a rejected command must be visible to the user ---

@pytest.mark.parametrize(
    ("make_button", "method", "message"),
    [
        (lambda c: SyncthingScanAllButton(c, ENTRY_ID), "scan_all_folders", "Failed to scan all folders"),
        (lambda c: SyncthingFolderScanButton(c, ENTRY_ID, "abcd", "Docs"), "scan_folder", "Failed to scan folder abcd"),
        (lambda c: SyncthingFolderPauseButton(c, ENTRY_ID, "abcd", "Docs"), "pause_folder", "Failed to pause folder abcd"),
        (lambda c: SyncthingFolderResumeButton(c, ENTRY_ID, "abcd", "Docs"), "resume_folder", "Failed to resume folder abcd"),
        (lambda c: SyncthingDevicePauseButton(c, ENTRY_ID, "DEV1", "Laptop"), "pause_device", "Failed to pause device DEV1"),
        (lambda c: SyncthingDeviceResumeButton(c, ENTRY_ID, "DEV1", "Laptop"), "resume_device", "Failed to resume device DEV1"),
    ],
)
def test_button_press_raises_when_syncthing_rejects_the_command(make_button, method, message):
    coordinator = make_coordinator()
    setattr(coordinator.api, method, AsyncMock(return_value=False))
    press = make_button(coordinator).async_press()

    with pytest.raises(HomeAssistantError, match=message):
        asyncio.run(press)

    coordinator.async_refresh.assert_not_called()
