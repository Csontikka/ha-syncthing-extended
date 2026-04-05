"""Syncthing REST API client."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import (
    API_HEALTH,
    API_VERSION,
    API_STATUS,
    API_CONNECTIONS,
    API_CONFIG_DEVICES,
    API_CONFIG_FOLDERS,
    API_DB_STATUS,
    API_DB_COMPLETION,
    API_STATS_DEVICE,
    API_STATS_FOLDER,
    API_DB_SCAN,
    API_FOLDER_ERRORS,
    API_SYSTEM_PAUSE,
    API_SYSTEM_RESUME,
)

_LOGGER = logging.getLogger(__name__)


class SyncthingApiError(Exception):
    """Base API error."""


class SyncthingConnectionError(SyncthingApiError):
    """Connection error."""


class SyncthingAuthError(SyncthingApiError):
    """Authentication error."""


class SyncthingApi:
    """Async Syncthing REST API client."""

    def __init__(
        self,
        host: str,
        port: int,
        api_key: str,
        use_ssl: bool = True,
        verify_ssl: bool = False,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._api_key = api_key
        self._use_ssl = use_ssl
        self._verify_ssl = verify_ssl
        self._session = session
        scheme = "https" if use_ssl else "http"
        self._base_url = f"{scheme}://{host}:{port}"

    @property
    def base_url(self) -> str:
        """Return base URL."""
        return self._base_url

    def _get_headers(self) -> dict[str, str]:
        """Return auth headers."""
        return {"X-API-Key": self._api_key}

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, str] | None = None,
        json_data: dict | None = None,
        authenticated: bool = True,
    ) -> Any:
        """Make an async HTTP request to the Syncthing API."""
        url = f"{self._base_url}{endpoint}"
        headers = self._get_headers() if authenticated else {}
        ssl_context: bool | None = None if self._verify_ssl else False

        try:
            async with self._session.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json_data,
                ssl=ssl_context,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status in (401, 403):
                    raise SyncthingAuthError(
                        f"Authentication failed (HTTP {response.status})"
                    )
                response.raise_for_status()
                if response.content_type == "application/json":
                    return await response.json()
                return await response.text()
        except SyncthingApiError:
            raise
        except aiohttp.ClientConnectorError as err:
            raise SyncthingConnectionError(
                f"Cannot connect to {self._host}:{self._port}: {err}"
            ) from err
        except aiohttp.ClientError as err:
            raise SyncthingApiError(f"Request failed: {err}") from err

    # --- System endpoints ---

    async def check_health(self) -> bool:
        """Check if Syncthing is reachable (no auth needed)."""
        try:
            result = await self._request("GET", API_HEALTH, authenticated=False)
            return isinstance(result, dict) and result.get("status") == "OK"
        except SyncthingApiError:
            return False

    async def get_version(self) -> dict[str, Any]:
        """Get Syncthing version info."""
        return await self._request("GET", API_VERSION)

    async def get_system_status(self) -> dict[str, Any]:
        """Get system status (myID, uptime, etc.)."""
        return await self._request("GET", API_STATUS)

    async def get_connections(self) -> dict[str, Any]:
        """Get all device connections and total traffic."""
        return await self._request("GET", API_CONNECTIONS)

    # --- Config endpoints ---

    async def get_config_devices(self) -> list[dict[str, Any]]:
        """Get configured devices list."""
        return await self._request("GET", API_CONFIG_DEVICES)

    async def get_config_folders(self) -> list[dict[str, Any]]:
        """Get configured folders list."""
        return await self._request("GET", API_CONFIG_FOLDERS)

    # --- Database / status endpoints ---

    async def get_folder_status(self, folder_id: str) -> dict[str, Any]:
        """Get folder sync status (expensive call)."""
        return await self._request(
            "GET", API_DB_STATUS, params={"folder": folder_id}
        )

    async def get_folder_completion(
        self, folder_id: str, device_id: str | None = None
    ) -> dict[str, Any]:
        """Get folder completion percentage."""
        params: dict[str, str] = {"folder": folder_id}
        if device_id:
            params["device"] = device_id
        return await self._request("GET", API_DB_COMPLETION, params=params)

    async def get_folder_errors(self, folder_id: str) -> dict[str, Any]:
        """Get folder pull errors."""
        return await self._request(
            "GET", API_FOLDER_ERRORS, params={"folder": folder_id}
        )

    # --- Stats endpoints ---

    async def get_device_stats(self) -> dict[str, Any]:
        """Get device statistics (lastSeen, etc.)."""
        return await self._request("GET", API_STATS_DEVICE)

    async def get_folder_stats(self) -> dict[str, Any]:
        """Get folder statistics (lastScan, lastFile, etc.)."""
        return await self._request("GET", API_STATS_FOLDER)

    # --- Action endpoints ---

    async def scan_folder(self, folder_id: str) -> bool:
        """Trigger a folder rescan."""
        try:
            await self._request(
                "POST", API_DB_SCAN, params={"folder": folder_id}
            )
            return True
        except SyncthingApiError as err:
            _LOGGER.error("Failed to scan folder %s: %s", folder_id, err)
            return False

    async def scan_all_folders(self) -> bool:
        """Trigger rescan of all folders."""
        try:
            await self._request("POST", API_DB_SCAN)
            return True
        except SyncthingApiError as err:
            _LOGGER.error("Failed to scan all folders: %s", err)
            return False

    async def pause_device(self, device_id: str) -> bool:
        """Pause a device."""
        try:
            await self._request("POST", API_SYSTEM_PAUSE, params={"device": device_id})
            return True
        except SyncthingApiError as err:
            _LOGGER.error("Failed to pause device %s: %s", device_id, err)
            return False

    async def resume_device(self, device_id: str) -> bool:
        """Resume a device."""
        try:
            await self._request("POST", API_SYSTEM_RESUME, params={"device": device_id})
            return True
        except SyncthingApiError as err:
            _LOGGER.error("Failed to resume device %s: %s", device_id, err)
            return False

    async def pause_folder(self, folder_id: str) -> bool:
        """Pause a folder."""
        try:
            await self._request(
                "PATCH", f"/rest/config/folders/{folder_id}",
                json_data={"paused": True},
            )
            return True
        except SyncthingApiError as err:
            _LOGGER.error("Failed to pause folder %s: %s", folder_id, err)
            return False

    async def resume_folder(self, folder_id: str) -> bool:
        """Resume a folder."""
        try:
            await self._request(
                "PATCH", f"/rest/config/folders/{folder_id}",
                json_data={"paused": False},
            )
            return True
        except SyncthingApiError as err:
            _LOGGER.error("Failed to resume folder %s: %s", folder_id, err)
            return False

    async def pause_all(self) -> bool:
        """Pause all devices."""
        try:
            await self._request("POST", API_SYSTEM_PAUSE)
            return True
        except SyncthingApiError as err:
            _LOGGER.error("Failed to pause all devices: %s", err)
            return False

    async def resume_all(self) -> bool:
        """Resume all devices."""
        try:
            await self._request("POST", API_SYSTEM_RESUME)
            return True
        except SyncthingApiError as err:
            _LOGGER.error("Failed to resume all devices: %s", err)
            return False
