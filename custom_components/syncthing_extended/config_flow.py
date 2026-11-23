"""Config flow for Syncthing."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    SyncthingApi,
    SyncthingApiError,
    SyncthingAuthError,
    SyncthingConnectionError,
    SyncthingSslError,
    normalize_base_path,
    parse_host_input,
)
from .const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_PATH,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_USE_SSL,
    CONF_VERIFY_SSL,
    DEFAULT_PATH,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USE_SSL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_PATH, default=DEFAULT_PATH): str,
        vol.Required(CONF_API_KEY): str,
        vol.Optional(CONF_USE_SSL, default=DEFAULT_USE_SSL): bool,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            int, vol.Range(min=10, max=300)
        ),
    }
)


# Reconfigure only covers the connection. The update interval lives in the
# options flow, and options take precedence over entry data, so offering it
# here would silently have no effect once it was set there.
STEP_RECONFIGURE_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_PATH, default=DEFAULT_PATH): str,
        vol.Required(CONF_API_KEY): str,
        vol.Optional(CONF_USE_SSL, default=DEFAULT_USE_SSL): bool,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
    }
)


def _resolve_connection(user_input: dict[str, Any]) -> dict[str, Any]:
    """Return user input with host, port, path and SSL resolved.

    The host field may carry a full URL (``https://xyz/syncthing``). Anything
    it specifies wins over the matching form field, except for an explicit
    entry in the location field, which always takes precedence over a path
    detected in the host field.

    Raises ValueError if the host entry cannot be interpreted.
    """
    host, port, path_from_host, use_ssl = parse_host_input(user_input[CONF_HOST])

    resolved = dict(user_input)
    resolved[CONF_HOST] = host
    if port is not None:
        resolved[CONF_PORT] = port
    if use_ssl is not None:
        resolved[CONF_USE_SSL] = use_ssl
    resolved[CONF_PATH] = (
        normalize_base_path(user_input.get(CONF_PATH)) or path_from_host
    )
    return resolved


class SyncthingConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle config flow for Syncthing."""

    VERSION = 1

    def _update_entry_and_abort(
        self, entry: ConfigEntry, data_updates: dict[str, Any]
    ) -> FlowResult:
        """Store new entry data, make sure the entry reloads, and end the flow.

        The entry's update listener already reloads it whenever its data
        changes. Newer cores therefore reject `async_update_reload_and_abort`
        for entries with an update listener and offer `async_update_and_abort`.
        """
        update_and_abort = getattr(self, "async_update_and_abort", None)
        if update_and_abort is None:  # cores without async_update_and_abort
            return self.async_update_reload_and_abort(entry, data_updates=data_updates)
        if all(entry.data.get(key) == value for key, value in data_updates.items()):
            # Nothing changes, so the listener will not fire. Reload anyway: the
            # user just confirmed the settings, e.g. to retry a failed setup.
            self.hass.config_entries.async_schedule_reload(entry.entry_id)
        return update_and_abort(entry, data_updates=data_updates)

    def _api_for(self, resolved: dict[str, Any]) -> SyncthingApi:
        """Build an API client for resolved connection settings."""
        verify_ssl = resolved.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
        return SyncthingApi(
            host=resolved[CONF_HOST],
            port=resolved[CONF_PORT],
            api_key=resolved[CONF_API_KEY],
            use_ssl=resolved.get(CONF_USE_SSL, DEFAULT_USE_SSL),
            verify_ssl=verify_ssl,
            session=async_get_clientsession(self.hass, verify_ssl=verify_ssl),
            path=resolved[CONF_PATH],
        )

    async def _async_probe(
        self, api: SyncthingApi, *, check_health: bool
    ) -> tuple[str | None, str | None]:
        """Contact Syncthing and return (device id, error key); one of them is None."""
        try:
            if check_health and not await api.check_health():
                return None, "cannot_connect"
            # An authenticated call, so it also validates the API key
            status = await api.get_system_status()
        except SyncthingAuthError:
            return None, "invalid_auth"
        except SyncthingSslError:
            return None, "ssl_error"
        except SyncthingConnectionError:
            return None, "cannot_connect"
        except SyncthingApiError as err:
            # Typically an HTTP error: something answers at that address, but
            # not the Syncthing API, e.g. a wrong location prefix.
            _LOGGER.debug("Syncthing API not reachable: %s", err)
            return None, "cannot_connect"
        except Exception:
            _LOGGER.exception("Unexpected error while contacting Syncthing")
            return None, "unknown"

        unique_id = status.get("myID", "")
        return (unique_id, None) if unique_id else (None, "cannot_connect")

    async def _async_entry_title(
        self, api: SyncthingApi, resolved: dict[str, Any], unique_id: str
    ) -> str:
        """Return a title for the entry, preferring the Syncthing device name."""
        try:
            devices = await api.get_config_devices()
            own = next((d for d in devices if d.get("deviceID") == unique_id), None)
            if own and own.get("name"):
                return f"Syncthing @ {own['name']}"
        except Exception:
            # The name is cosmetic; fall back to the address.
            _LOGGER.debug("Could not look up the Syncthing device name", exc_info=True)
        return (
            f"Syncthing ({resolved[CONF_HOST]}:"
            f"{resolved[CONF_PORT]}{resolved[CONF_PATH]})"
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                resolved = _resolve_connection(user_input)
            except ValueError as err:
                _LOGGER.debug("Invalid host entry %r: %s", user_input[CONF_HOST], err)
                errors[CONF_HOST] = "invalid_host"
            else:
                api = self._api_for(resolved)
                unique_id, error = await self._async_probe(api, check_health=True)
                if unique_id is not None:
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=await self._async_entry_title(api, resolved, unique_id),
                        data=resolved,
                    )
                errors["base"] = error

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA, user_input or {}
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfiguration of an existing entry.

        Lets an existing installation add or change host, port, location and
        SSL settings without having to be removed and set up again.
        """
        reconfigure_entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                resolved = _resolve_connection(user_input)
            except ValueError as err:
                _LOGGER.debug("Invalid host entry %r: %s", user_input[CONF_HOST], err)
                errors[CONF_HOST] = "invalid_host"
            else:
                unique_id, error = await self._async_probe(
                    self._api_for(resolved), check_health=False
                )
                if unique_id is not None:
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_mismatch(reason="wrong_instance")
                    return self._update_entry_and_abort(reconfigure_entry, resolved)
                errors["base"] = error

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                STEP_RECONFIGURE_DATA_SCHEMA,
                user_input or dict(reconfigure_entry.data),
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Handle re-authentication when credentials become invalid."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle re-auth confirmation step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            reauth_entry = self._get_reauth_entry()
            session = async_get_clientsession(
                self.hass,
                verify_ssl=reauth_entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
            )
            api = SyncthingApi(
                host=reauth_entry.data[CONF_HOST],
                port=reauth_entry.data[CONF_PORT],
                api_key=user_input[CONF_API_KEY],
                verify_ssl=reauth_entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
                session=session,
                path=reauth_entry.data.get(CONF_PATH, DEFAULT_PATH),
            )
            try:
                await api.get_system_status()
                return self._update_entry_and_abort(
                    reauth_entry, {CONF_API_KEY: user_input[CONF_API_KEY]}
                )
            except SyncthingAuthError:
                errors["base"] = "invalid_auth"
            except SyncthingSslError:
                errors["base"] = "ssl_error"
            except SyncthingConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during re-auth")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SyncthingOptionsFlow:
        """Get the options flow handler."""
        return SyncthingOptionsFlow()


class SyncthingOptionsFlow(OptionsFlow):
    """Handle options flow for Syncthing."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle options step."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )

        options_schema = vol.Schema(
            {
                vol.Optional(CONF_SCAN_INTERVAL, default=current_interval): vol.All(
                    int, vol.Range(min=10, max=300)
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
        )
