"""Tests for Syncthing button platform."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from custom_components.syncthing.button import (
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
    coordinator.async_request_refresh = AsyncMock()
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
    coordinator.async_request_refresh.assert_called_once()


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
    coordinator.async_request_refresh.assert_called_once()


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
