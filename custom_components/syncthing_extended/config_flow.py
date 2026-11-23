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
                return self.async_show_form(
                    step_id="user",
                    data_schema=self.add_suggested_values_to_schema(
                        STEP_USER_DATA_SCHEMA, user_input
                    ),
                    errors={CONF_HOST: "invalid_host"},
                )

            use_ssl = resolved.get(CONF_USE_SSL, DEFAULT_USE_SSL)
            verify_ssl = resolved.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
            session = async_get_clientsession(self.hass, verify_ssl=verify_ssl)
            api = SyncthingApi(
                host=resolved[CONF_HOST],
                port=resolved[CONF_PORT],
                api_key=resolved[CONF_API_KEY],
                use_ssl=use_ssl,
                verify_ssl=verify_ssl,
                session=session,
                path=resolved[CONF_PATH],
            )

            try:
                healthy = await api.check_health()
                if not healthy:
                    errors["base"] = "cannot_connect"
                else:
                    # Validate API key by making an authenticated call
                    status = await api.get_system_status()
                    unique_id = status.get("myID", "")

                    if not unique_id:
                        errors["base"] = "cannot_connect"
                    else:
                        await self.async_set_unique_id(unique_id)
                        self._abort_if_unique_id_configured()

                        # Try to get a friendly device name
                        title = (
                            f"Syncthing ({resolved[CONF_HOST]}:"
                            f"{resolved[CONF_PORT]}{resolved[CONF_PATH]})"
                        )
                        try:
                            devices = await api.get_config_devices()
                            own = next(
                                (d for d in devices if d.get("deviceID") == unique_id),
                                None,
                            )
                            if own and own.get("name"):
                                title = f"Syncthing @ {own['name']}"
                        except Exception:
                            pass

                        return self.async_create_entry(
                            title=title,
                            data=resolved,
                        )
            except SyncthingAuthError:
                errors["base"] = "invalid_auth"
            except SyncthingSslError:
                errors["base"] = "ssl_error"
            except SyncthingConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during config flow")
                errors["base"] = "unknown"

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
                verify_ssl = resolved.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
                api = SyncthingApi(
                    host=resolved[CONF_HOST],
                    port=resolved[CONF_PORT],
                    api_key=resolved[CONF_API_KEY],
                    use_ssl=resolved.get(CONF_USE_SSL, DEFAULT_USE_SSL),
                    verify_ssl=verify_ssl,
                    session=async_get_clientsession(self.hass, verify_ssl=verify_ssl),
                    path=resolved[CONF_PATH],
                )
                try:
                    status = await api.get_system_status()
                    unique_id = status.get("myID", "")
                    if not unique_id:
                        errors["base"] = "cannot_connect"
                    else:
                        await self.async_set_unique_id(unique_id)
                        self._abort_if_unique_id_mismatch(reason="wrong_instance")
                        return self.async_update_reload_and_abort(
                            reconfigure_entry,
                            data_updates=resolved,
                        )
                except SyncthingAuthError:
                    errors["base"] = "invalid_auth"
                except SyncthingSslError:
                    errors["base"] = "ssl_error"
                except SyncthingConnectionError:
                    errors["base"] = "cannot_connect"
                except Exception:
                    _LOGGER.exception("Unexpected error during reconfiguration")
                    errors["base"] = "unknown"

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA,
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
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={CONF_API_KEY: user_input[CONF_API_KEY]},
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
