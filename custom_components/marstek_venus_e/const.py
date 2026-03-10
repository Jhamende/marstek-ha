"""Constants for the Marstek Venus E integration."""

DOMAIN = "marstek_venus_e"
DEFAULT_PORT = 30000
DEFAULT_SCAN_INTERVAL = 60  # seconds — do not go below 30s or device may become unstable
DISCOVERY_TIMEOUT = 3.0     # seconds to collect broadcast responses
UDP_COMMAND_TIMEOUT = 12.0  # seconds per individual command
UDP_RETRIES = 2             # retry attempts on timeout

CONF_HOST = "host"
CONF_PORT = "port"
CONF_MAC = "mac"
CONF_DEVICE_LABEL = "device_label"
CONF_SCAN_INTERVAL = "scan_interval"

# ── API method names ──────────────────────────────────────────────────────────
METHOD_GET_DEVICE  = "Marstek.GetDevice"
METHOD_BAT_STATUS  = "Bat.GetStatus"
METHOD_PV_STATUS   = "PV.GetStatus"
METHOD_ES_STATUS   = "ES.GetStatus"
METHOD_ES_GET_MODE = "ES.GetMode"
METHOD_ES_SET_MODE = "ES.SetMode"
METHOD_EM_STATUS   = "EM.GetStatus"
METHOD_WIFI_STATUS = "Wifi.GetStatus"

# ── Operating modes ───────────────────────────────────────────────────────────
MODE_AUTO    = "Auto"
MODE_AI      = "AI"
MODE_MANUAL  = "Manual"
MODE_PASSIVE = "Passive"
OPERATING_MODES = [MODE_AUTO, MODE_AI, MODE_MANUAL, MODE_PASSIVE]

# ── HA service names ──────────────────────────────────────────────────────────
SERVICE_SET_PASSIVE_MODE    = "set_passive_mode"
SERVICE_SET_MANUAL_SCHEDULE = "set_manual_schedule"
SERVICE_CLEAR_SCHEDULES     = "clear_schedules"
SERVICE_FORCE_REFRESH       = "force_refresh"

# ── Service / attribute names ─────────────────────────────────────────────────
ATTR_POWER      = "power"
ATTR_CD_TIME    = "cd_time"
ATTR_TIME_NUM   = "time_num"
ATTR_START_TIME = "start_time"
ATTR_END_TIME   = "end_time"
ATTR_WEEK_SET   = "week_set"
ATTR_ENABLE     = "enable"
ATTR_DEVICE_ID  = "device_id"

# week_set bitmask (bit 0 = Monday … bit 6 = Sunday)
WEEK_ALL_DAYS = 127
