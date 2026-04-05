"""Config flow for Syncthing Extended."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SyncthingApi, SyncthingAuthError, SyncthingConnectionError, SyncthingSslError
from .const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_USE_SSL,
    CONF_VERIFY_SSL,
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
        vol.Required(CONF_API_KEY): str,
        vol.Optional(CONF_USE_SSL, default=DEFAULT_USE_SSL): bool,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            int, vol.Range(min=10, max=300)
        ),
    }
)


class SyncthingConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle config flow for Syncthing Extended."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            use_ssl = user_input.get(CONF_USE_SSL, DEFAULT_USE_SSL)
            verify_ssl = user_input.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
            session = async_get_clientsession(self.hass, verify_ssl=verify_ssl)
            api = SyncthingApi(
                host=user_input[CONF_HOST],
                port=user_input[CONF_PORT],
                api_key=user_input[CONF_API_KEY],
                use_ssl=use_ssl,
                verify_ssl=verify_ssl,
                session=session,
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
                        title = f"Syncthing ({user_input[CONF_HOST]}:{user_input[CONF_PORT]})"
                        try:
                            devices = await api.get_config_devices()
                            own = next((d for d in devices if d.get("deviceID") == unique_id), None)
                            if own and own.get("name"):
                                title = f"Syncthing @ {own['name']}"
                        except Exception:
                            pass

                        return self.async_create_entry(
                            title=title,
                            data=user_input,
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

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> FlowResult:
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
                self.hass, verify_ssl=reauth_entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
            )
            api = SyncthingApi(
                host=reauth_entry.data[CONF_HOST],
                port=reauth_entry.data[CONF_PORT],
                api_key=user_input[CONF_API_KEY],
                verify_ssl=reauth_entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
                session=session,
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
    """Handle options flow for Syncthing Extended."""

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
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=current_interval
                ): vol.All(int, vol.Range(min=10, max=300)),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
        )
