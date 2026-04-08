# Syncthing — Home Assistant Integration

![Syncthing](https://raw.githubusercontent.com/Csontikka/ha-syncthing/master/images/banner.svg)

![GitHub release (latest by date)](https://img.shields.io/github/v/release/Csontikka/ha-syncthing?style=plastic)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=plastic)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=plastic)](LICENSE)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=Csontikka_ha-syncthing&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=Csontikka_ha-syncthing)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=Csontikka_ha-syncthing&metric=reliability_rating)](https://sonarcloud.io/summary/new_code?id=Csontikka_ha-syncthing)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=Csontikka_ha-syncthing&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=Csontikka_ha-syncthing)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-donate-yellow.svg?style=plastic)](https://buymeacoffee.com/Csontikka)

Full-featured Home Assistant integration for [Syncthing](https://syncthing.net). Monitor folder sync status, device connectivity and traffic, trigger rescans, and pause/resume folders and devices — all from your HA dashboard. Supports multiple Syncthing instances simultaneously.

## Why this instead of the built-in integration?

The core Syncthing integration creates only one sensor per folder showing its state. That's it.

This integration adds:

| Feature | Built-in | This |
|---------|----------|------|
| Folder state sensor | ✅ | ✅ |
| Folder completion % | ⚠️ attr only | ✅ dedicated sensor |
| Bytes / files needed | ⚠️ attr only | ✅ dedicated sensor |
| Folder size & file count | ⚠️ attr only | ✅ dedicated sensor |
| Pull error detection | ⚠️ attr only | ✅ dedicated sensor |
| Last scan / last file | ❌ | ✅ |
| Device online/offline | ❌ | ✅ |
| Device connection type | ❌ | ✅ |
| Per-device traffic stats | ❌ | ✅ |
| Total traffic sensors | ❌ | ✅ |
| Scan trigger (button + service) | ❌ | ✅ |
| Pause / resume folder | ❌ | ✅ |
| Pause / resume device | ❌ | ✅ |
| Multi-instance support | ❌ | ✅ |
| UI config (no YAML) | ✅ | ✅ |

## Screenshots

**System device** — version, uptime, running state, total traffic and scan button:

![Syncthing system device](https://raw.githubusercontent.com/Csontikka/ha-syncthing/master/images/device_main.png)

**Folder** — sync state, completion, controls and all folder sensors:

![Syncthing folder](https://raw.githubusercontent.com/Csontikka/ha-syncthing/master/images/folder_syncthing_photos.png)

**Remote device** — connectivity, traffic, pause/resume controls and diagnostic sensors:

![Syncthing remote device](https://raw.githubusercontent.com/Csontikka/ha-syncthing/master/images/device_virtualwin10.png)

## Installation

### HACS (recommended)

1. Open HACS → Integrations
2. Click the three-dot menu → **Custom repositories**
3. Add `https://github.com/Csontikka/ha-syncthing` with category **Integration**
4. Click **Download**
5. Restart Home Assistant

After setup, the integration appears in Settings → Integrations:

![Integration card](https://raw.githubusercontent.com/Csontikka/ha-syncthing/master/images/integration_card.png)

### Manual

1. Copy `custom_components/syncthing/` to your HA `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings → Integrations → Add Integration**
2. Search for **Syncthing**
3. Enter your connection details:

![Config flow](https://raw.githubusercontent.com/Csontikka/ha-syncthing/master/images/config_flow.png)

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| Host | Yes | — | IP address or hostname of the Syncthing instance |
| Port | Yes | `8384` | Syncthing GUI/API port |
| API Key | Yes | — | Found in Syncthing UI: Actions → Settings → API Key |
| Use HTTPS | No | `false` | Connect using HTTPS instead of HTTP |
| Verify SSL | No | `false` | Validate the HTTPS certificate (requires Use HTTPS) |
| Update interval | No | `30` | How often to poll for updates, in seconds (10–300) |

### Finding your API key

![Syncthing API key location](https://raw.githubusercontent.com/Csontikka/ha-syncthing/master/images/syncthing_settings_apikey.png)

- **Syncthing UI**: Actions → Settings → right panel → API Key
- **Linux**: `~/.local/state/syncthing/config.xml` → `<gui><apikey>…</apikey></gui>`
- **Proxmox LXC**: `/root/.local/state/syncthing/config.xml`

### Remote access requirement

Syncthing must listen on a non-localhost address. If bound to `127.0.0.1:8384`, change it to `0.0.0.0:8384` in Syncthing GUI (Settings → GUI Listen Addresses) and restart Syncthing.

### Options

After setup you can change the **Update interval** via **Settings → Integrations → Syncthing → Configure**.

### Re-authentication

If your API key changes, Home Assistant will show a re-authentication prompt. Click **Re-authenticate** and enter the new API key — no need to delete and re-add the integration.

## Entities

### System (one per Syncthing instance)

| Entity | Type | Description |
|--------|------|-------------|
| Running | Binary sensor | `on` when Syncthing is reachable |
| Version | Sensor | Syncthing version string |
| Uptime | Sensor | Uptime in seconds |
| Device ID | Sensor | This instance's Syncthing device ID |
| Total downloaded | Sensor | Total bytes received (all devices) |
| Total uploaded | Sensor | Total bytes sent (all devices) |

### Per folder

| Entity | Type | Description |
|--------|------|-------------|
| State | Sensor | `idle` / `syncing` / `scanning` / `error` |
| Completion | Sensor | Sync completion percentage |
| Bytes needed | Sensor | Bytes remaining to sync |
| Files needed | Sensor | File count remaining to sync |
| Error | Binary sensor | `on` when pull errors > 0 |
| Syncing | Binary sensor | `on` when state is `syncing` |
| Paused | Binary sensor | `on` when folder is paused |
| Scan | Button | Trigger immediate rescan |
| Pause | Button | Pause this folder |
| Resume | Button | Resume this folder |
| Total size | Sensor | Total folder size |
| Total files | Sensor | Total file count |
| Pull errors | Sensor | Number of pull errors |
| Last scan | Sensor | Timestamp of last folder scan |
| Last synced file | Sensor | Filename of last synced file |

### Per device (sync partners)

| Entity | Type | Description |
|--------|------|-------------|
| Connected | Binary sensor | `on` when device is online |
| Paused | Binary sensor | `on` when device is paused |
| Downloaded | Sensor | Bytes received from this device |
| Uploaded | Sensor | Bytes sent to this device |
| Pause | Button | Pause sync with this device |
| Resume | Button | Resume sync with this device |
| Connection type | Sensor | `tcp-client`, `relay-server`, `quic-client`, etc. |
| Address | Sensor | Remote IP:port |
| Client version | Sensor | Syncthing version on remote device |
| Last seen | Sensor | Timestamp of last connection |

## Services

| Service | Parameters | Description |
|---------|-----------|-------------|
| `syncthing.scan_folder` | `folder_id` | Trigger rescan of one folder |
| `syncthing.scan_all` | — | Trigger rescan of all folders |
| `syncthing.pause_folder` | `folder_id` | Pause a specific folder |
| `syncthing.resume_folder` | `folder_id` | Resume a specific folder |
| `syncthing.pause_device` | `device_id` | Pause sync with a device |
| `syncthing.resume_device` | `device_id` | Resume sync with a device |
| `syncthing.pause_all` | — | Pause all devices |
| `syncthing.resume_all` | — | Resume all devices |

### Example automation

```yaml
automation:
  - alias: "Alert when Syncthing folder has errors"
    trigger:
      - platform: state
        entity_id: binary_sensor.syncthing_folder_documents_error
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          message: "Syncthing: Documents folder has sync errors!"

  - alias: "Scan after backup completes"
    trigger:
      - platform: state
        entity_id: sensor.backup_status
        to: "completed"
    action:
      - service: syncthing.scan_all
```

## Removal

1. Go to **Settings → Devices & Services → Syncthing**
2. Click the three-dot menu → **Delete**
3. Optionally remove `custom_components/syncthing/` and restart HA

## Supported versions

- Home Assistant 2024.1.0+
- Syncthing v1.20.0+

## Support

Found a bug or have an idea? [Open an issue](https://github.com/Csontikka/ha-syncthing/issues) — feedback and feature requests are welcome!

If you find this integration useful, consider [buying me a coffee](https://buymeacoffee.com/Csontikka).
