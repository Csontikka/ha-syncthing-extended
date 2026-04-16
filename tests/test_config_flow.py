"""Tests for Syncthing config flow."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.syncthing_extended.api import (
    SyncthingAuthError,
    SyncthingConnectionError,
    SyncthingSslError,
)
from custom_components.syncthing_extended.const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_USE_SSL,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from tests.conftest import MOCK_SYSTEM_STATUS, MOCK_VERSION

VALID_INPUT = {
    CONF_HOST: "192.168.1.100",
    CONF_PORT: 8384,
    CONF_API_KEY: "test-api-key-12345",
    CONF_USE_SSL: True,
    CONF_VERIFY_SSL: False,
    CONF_SCAN_INTERVAL: 30,
}


def _mock_api(healthy=True, auth_error=False, connect_error=False):
    api = MagicMock()
    api.check_health = AsyncMock(return_value=not connect_error and healthy)
    if auth_error:
        api.get_system_status = AsyncMock(side_effect=SyncthingAuthError("bad key"))
    elif connect_error:
        api.get_system_status = AsyncMock(
            side_effect=SyncthingConnectionError("no route")
        )
    else:
        api.get_system_status = AsyncMock(return_value=MOCK_SYSTEM_STATUS)
    api.get_config_devices = AsyncMock(return_value=[])
    api.get_version = AsyncMock(return_value=MOCK_VERSION)
    return api


def _make_flow():
    from custom_components.syncthing_extended.config_flow import SyncthingConfigFlow

    flow = SyncthingConfigFlow()
    flow.hass = MagicMock()
    flow.hass.config_entries = MagicMock()
    flow.hass.config_entries.async_entries = MagicMock(return_value=[])
    return flow


class _Recorder:
    """Captures call kwargs for async_show_form / async_create_entry so we can assert
    the flow actually computed them — instead of testing our own return_value echo."""

    def __init__(self, kind: str = "form"):
        self.kind = kind
        self.calls: list[dict] = []

    def show_form(self, **kwargs):
        self.calls.append(kwargs)
        return {"type": "form", **{k: v for k, v in kwargs.items() if k in ("step_id", "errors")}}

    def create_entry(self, **kwargs):
        self.calls.append(kwargs)
        return {"type": "create_entry", **kwargs}

    @property
    def last(self) -> dict:
        assert self.calls, "No recorded call"
        return self.calls[-1]


def _patch_common(flow, mock_api):
    """Patch SyncthingApi + clientsession common to every flow test."""
    return [
        patch(
            "custom_components.syncthing_extended.config_flow.SyncthingApi",
            return_value=mock_api,
        ),
        patch(
            "custom_components.syncthing_extended.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
    ]


def _run_step(flow, step_coro_factory):
    return asyncio.run(step_coro_factory(flow))


# --- user step ---

def test_config_flow_shows_form_on_empty_with_empty_errors():
    flow = _make_flow()
    rec = _Recorder()
    with patch.object(flow, "async_show_form", side_effect=rec.show_form):
        result = _run_step(flow, lambda f: f.async_step_user(None))

    assert result["type"] == "form"
    assert rec.last["step_id"] == "user"
    assert rec.last["errors"] == {}


def test_config_flow_success_creates_entry_with_correct_data_and_unique_id():
    flow = _make_flow()
    mock_api = _mock_api()
    rec = _Recorder()
    set_uid = AsyncMock()

    with patch(
        "custom_components.syncthing_extended.config_flow.SyncthingApi",
        return_value=mock_api,
    ), patch(
        "custom_components.syncthing_extended.config_flow.async_get_clientsession",
        return_value=MagicMock(),
    ), patch.object(flow, "async_set_unique_id", set_uid), patch.object(
        flow, "_abort_if_unique_id_configured", MagicMock()
    ), patch.object(flow, "async_create_entry", side_effect=rec.create_entry):
        result = _run_step(flow, lambda f: f.async_step_user(VALID_INPUT))

    assert result["type"] == "create_entry"
    # The flow must forward the user input verbatim
    assert rec.last["data"] == VALID_INPUT
    # Title falls back to host:port (no friendly device name in this test)
    assert rec.last["title"] == f"Syncthing ({VALID_INPUT[CONF_HOST]}:{VALID_INPUT[CONF_PORT]})"
    # Unique ID must be myID from the health check
    set_uid.assert_awaited_once_with(MOCK_SYSTEM_STATUS["myID"])


def test_config_flow_success_with_device_name_uses_friendly_title():
    flow = _make_flow()
    mock_api = _mock_api()
    mock_api.get_config_devices = AsyncMock(
        return_value=[
            {"deviceID": MOCK_SYSTEM_STATUS["myID"], "name": "MyNAS"},
            {"deviceID": "OTHER", "name": "OtherDevice"},
        ]
    )
    rec = _Recorder()

    with patch(
        "custom_components.syncthing_extended.config_flow.SyncthingApi",
        return_value=mock_api,
    ), patch(
        "custom_components.syncthing_extended.config_flow.async_get_clientsession",
        return_value=MagicMock(),
    ), patch.object(flow, "async_set_unique_id", AsyncMock()), patch.object(
        flow, "_abort_if_unique_id_configured", MagicMock()
    ), patch.object(flow, "async_create_entry", side_effect=rec.create_entry):
        result = _run_step(flow, lambda f: f.async_step_user(VALID_INPUT))

    assert result["type"] == "create_entry"
    assert rec.last["title"] == "Syncthing @ MyNAS"


def test_config_flow_success_friendly_name_lookup_failure_falls_back():
    """get_config_devices raises → title stays as host:port fallback."""
    flow = _make_flow()
    mock_api = _mock_api()
    mock_api.get_config_devices = AsyncMock(side_effect=Exception("network error"))
    rec = _Recorder()

    with patch(
        "custom_components.syncthing_extended.config_flow.SyncthingApi",
        return_value=mock_api,
    ), patch(
        "custom_components.syncthing_extended.config_flow.async_get_clientsession",
        return_value=MagicMock(),
    ), patch.object(flow, "async_set_unique_id", AsyncMock()), patch.object(
        flow, "_abort_if_unique_id_configured", MagicMock()
    ), patch.object(flow, "async_create_entry", side_effect=rec.create_entry):
        result = _run_step(flow, lambda f: f.async_step_user(VALID_INPUT))

    assert result["type"] == "create_entry"
    assert rec.last["title"] == f"Syncthing ({VALID_INPUT[CONF_HOST]}:{VALID_INPUT[CONF_PORT]})"


@pytest.mark.parametrize(
    ("api_fixture", "expected_error"),
    [
        (lambda: _mock_api(healthy=False), "cannot_connect"),
        (lambda: _mock_api(auth_error=True), "invalid_auth"),
    ],
)
def test_config_flow_check_health_paths_set_correct_error(api_fixture, expected_error):
    flow = _make_flow()
    rec = _Recorder()
    with patch(
        "custom_components.syncthing_extended.config_flow.SyncthingApi",
        return_value=api_fixture(),
    ), patch(
        "custom_components.syncthing_extended.config_flow.async_get_clientsession",
        return_value=MagicMock(),
    ), patch.object(flow, "async_show_form", side_effect=rec.show_form):
        result = _run_step(flow, lambda f: f.async_step_user(VALID_INPUT))

    assert result["type"] == "form"
    # Critical: the flow produced this error, not our test harness
    assert rec.last["errors"] == {"base": expected_error}


@pytest.mark.parametrize(
    ("side_effect", "expected_error"),
    [
        (SyncthingSslError("bad cert"), "ssl_error"),
        (SyncthingConnectionError("no route"), "cannot_connect"),
        (SyncthingAuthError("bad key"), "invalid_auth"),
        (RuntimeError("unexpected"), "unknown"),
    ],
)
def test_config_flow_check_health_exception_maps_to_error(side_effect, expected_error):
    flow = _make_flow()
    mock_api = MagicMock()
    mock_api.check_health = AsyncMock(side_effect=side_effect)
    rec = _Recorder()

    with patch(
        "custom_components.syncthing_extended.config_flow.SyncthingApi",
        return_value=mock_api,
    ), patch(
        "custom_components.syncthing_extended.config_flow.async_get_clientsession",
        return_value=MagicMock(),
    ), patch.object(flow, "async_show_form", side_effect=rec.show_form):
        result = _run_step(flow, lambda f: f.async_step_user(VALID_INPUT))

    assert result["type"] == "form"
    assert rec.last["errors"] == {"base": expected_error}


def test_config_flow_empty_unique_id_reports_cannot_connect():
    flow = _make_flow()
    mock_api = MagicMock()
    mock_api.check_health = AsyncMock(return_value=True)
    mock_api.get_system_status = AsyncMock(return_value={"myID": ""})
    rec = _Recorder()

    with patch(
        "custom_components.syncthing_extended.config_flow.SyncthingApi",
        return_value=mock_api,
    ), patch(
        "custom_components.syncthing_extended.config_flow.async_get_clientsession",
        return_value=MagicMock(),
    ), patch.object(flow, "async_show_form", side_effect=rec.show_form):
        result = _run_step(flow, lambda f: f.async_step_user(VALID_INPUT))

    assert result["type"] == "form"
    assert rec.last["errors"] == {"base": "cannot_connect"}


# --- reauth step ---

def _reauth_entry():
    entry = MagicMock()
    entry.data = {
        CONF_HOST: "192.168.1.100",
        CONF_PORT: 8384,
        CONF_API_KEY: "old-key",
        CONF_VERIFY_SSL: False,
    }
    return entry


def test_reauth_confirm_success_updates_entry_with_new_key():
    flow = _make_flow()
    mock_api = _mock_api()
    reauth_entry = _reauth_entry()
    captured = {}

    def _abort_and_reload(entry, *, data_updates):
        captured["entry"] = entry
        captured["data_updates"] = data_updates
        return {"type": "abort", "reason": "reauth_successful"}

    with patch(
        "custom_components.syncthing_extended.config_flow.SyncthingApi",
        return_value=mock_api,
    ), patch(
        "custom_components.syncthing_extended.config_flow.async_get_clientsession",
        return_value=MagicMock(),
    ), patch.object(
        flow, "_get_reauth_entry", return_value=reauth_entry
    ), patch.object(
        flow, "async_update_reload_and_abort", side_effect=_abort_and_reload
    ):
        result = _run_step(
            flow,
            lambda f: f.async_step_reauth_confirm({CONF_API_KEY: "new-api-key"}),
        )

    assert result["type"] == "abort"
    assert result["reason"] == "reauth_successful"
    assert captured["entry"] is reauth_entry
    # The new key must be forwarded — otherwise the reauth was a no-op
    assert captured["data_updates"] == {CONF_API_KEY: "new-api-key"}


@pytest.mark.parametrize(
    ("side_effect", "expected_error"),
    [
        (SyncthingAuthError("bad key"), "invalid_auth"),
        (SyncthingSslError("bad cert"), "ssl_error"),
        (SyncthingConnectionError("no route"), "cannot_connect"),
        (RuntimeError("boom"), "unknown"),
    ],
)
def test_reauth_confirm_exception_maps_to_error(side_effect, expected_error):
    flow = _make_flow()
    mock_api = MagicMock()
    mock_api.get_system_status = AsyncMock(side_effect=side_effect)
    rec = _Recorder()

    with patch(
        "custom_components.syncthing_extended.config_flow.SyncthingApi",
        return_value=mock_api,
    ), patch(
        "custom_components.syncthing_extended.config_flow.async_get_clientsession",
        return_value=MagicMock(),
    ), patch.object(
        flow, "_get_reauth_entry", return_value=_reauth_entry()
    ), patch.object(flow, "async_show_form", side_effect=rec.show_form):
        result = _run_step(
            flow, lambda f: f.async_step_reauth_confirm({CONF_API_KEY: "new-key"})
        )

    assert result["type"] == "form"
    assert rec.last["errors"] == {"base": expected_error}
    assert rec.last["step_id"] == "reauth_confirm"


def test_reauth_step_delegates_to_confirm():
    flow = _make_flow()
    rec = _Recorder()
    with patch.object(flow, "async_show_form", side_effect=rec.show_form):
        result = _run_step(flow, lambda f: f.async_step_reauth({}))
    assert result["type"] == "form"
    assert rec.last["step_id"] == "reauth_confirm"
    # entering reauth with no input → empty errors
    assert rec.last["errors"] == {}


def test_reauth_confirm_shows_form_on_empty_input():
    flow = _make_flow()
    rec = _Recorder()
    with patch.object(flow, "async_show_form", side_effect=rec.show_form):
        result = _run_step(flow, lambda f: f.async_step_reauth_confirm(None))
    assert result["type"] == "form"
    assert rec.last["step_id"] == "reauth_confirm"
    assert rec.last["errors"] == {}


# --- options flow ---

def _make_options_flow(current_interval=30):
    from custom_components.syncthing_extended.config_flow import SyncthingOptionsFlow

    config_entry = MagicMock()
    config_entry.options = {}
    config_entry.data = {CONF_SCAN_INTERVAL: current_interval}
    flow = SyncthingOptionsFlow()
    flow._config_entry = config_entry
    return flow


def test_options_flow_success_saves_scan_interval():
    flow = _make_options_flow()
    rec = _Recorder()
    with patch.object(flow, "async_create_entry", side_effect=rec.create_entry):
        result = _run_step(
            flow, lambda f: f.async_step_init({CONF_SCAN_INTERVAL: 60})
        )
    assert result["type"] == "create_entry"
    assert rec.last["data"] == {CONF_SCAN_INTERVAL: 60}


def test_options_flow_shows_form_on_empty_with_schema():
    """Show-form path must include a schema with current scan_interval default."""
    flow = _make_options_flow(current_interval=45)
    rec = _Recorder()
    with patch.object(flow, "async_show_form", side_effect=rec.show_form):
        result = _run_step(flow, lambda f: f.async_step_init(None))
    assert result["type"] == "form"
    assert rec.last["step_id"] == "init"
    # Verify the schema is present (the shape; value default lives in voluptuous)
    assert rec.last.get("data_schema") is not None


def test_async_get_options_flow_returns_options_flow_instance():
    from custom_components.syncthing_extended.config_flow import (
        SyncthingConfigFlow,
        SyncthingOptionsFlow,
    )

    result = SyncthingConfigFlow.async_get_options_flow(MagicMock())
    assert isinstance(result, SyncthingOptionsFlow)


# --- config flow class metadata ---

def test_config_flow_is_registered_under_our_domain():
    """The flow must be registered under our DOMAIN — not a typo."""
    from homeassistant.config_entries import HANDLERS
    from custom_components.syncthing_extended.config_flow import SyncthingConfigFlow

    assert HANDLERS.get(DOMAIN) is SyncthingConfigFlow
