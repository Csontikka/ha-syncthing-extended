"""Constants for Syncthing integration."""

DOMAIN = "syncthing"
DEFAULT_PORT = 8384
DEFAULT_USE_SSL = True
DEFAULT_VERIFY_SSL = False
DEFAULT_SCAN_INTERVAL = 30  # seconds

# Config entry keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_API_KEY = "api_key"
CONF_USE_SSL = "use_ssl"
CONF_VERIFY_SSL = "verify_ssl"
CONF_SCAN_INTERVAL = "scan_interval"

# API endpoints
API_HEALTH = "/rest/noauth/health"
API_VERSION = "/rest/system/version"
API_STATUS = "/rest/system/status"
API_CONNECTIONS = "/rest/system/connections"
API_CONFIG_DEVICES = "/rest/config/devices"
API_CONFIG_FOLDERS = "/rest/config/folders"
API_DB_STATUS = "/rest/db/status"
API_DB_COMPLETION = "/rest/db/completion"
API_STATS_DEVICE = "/rest/stats/device"
API_STATS_FOLDER = "/rest/stats/folder"
API_DB_SCAN = "/rest/db/scan"
API_FOLDER_ERRORS = "/rest/folder/errors"
API_SYSTEM_PAUSE = "/rest/system/pause"
API_SYSTEM_RESUME = "/rest/system/resume"
API_CONFIG_FOLDERS_SET = "/rest/config/folders"

# Folder states
STATE_IDLE = "idle"
STATE_SCANNING = "scanning"
STATE_SYNCING = "syncing"
STATE_ERROR = "error"
STATE_UNKNOWN = "unknown"

# Platforms
PLATFORMS: list[str] = ["sensor", "binary_sensor", "button"]
