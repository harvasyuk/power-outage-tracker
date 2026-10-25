"""Constants for Power Outage Tracker."""

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "power_outage_tracker"

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]

CONF_SOURCE_ENTITY_1 = "source_entity_1"
CONF_SOURCE_ENTITY_2 = "source_entity_2"
CONF_STARTUP_GRACE = "startup_grace"
CONF_OUTAGE_DELAY = "outage_delay"
CONF_RESTORE_DELAY = "restore_delay"

DEFAULT_STARTUP_GRACE = 120
DEFAULT_OUTAGE_DELAY = 60
DEFAULT_RESTORE_DELAY = 15

MIN_DELAY = 0
MAX_DELAY = 3600

STORAGE_VERSION = 1
STORAGE_KEY_PREFIX = DOMAIN

UPDATE_INTERVAL = timedelta(minutes=1)

EVENT_OUTAGE_STARTED = f"{DOMAIN}_outage_started"
EVENT_POWER_RESTORED = f"{DOMAIN}_power_restored"

STATE_POWER_PRESENT = "power_present"
STATE_POWER_OUTAGE = "power_outage"

STATUS_STARTING = "starting"
STATUS_TRACKING = "tracking"
STATUS_POSSIBLE_OUTAGE = "possible_outage"
STATUS_POSSIBLE_RESTORE = "possible_restore"
STATUS_WAITING_FOR_SOURCE = "waiting_for_source"

MONITORING_STATUSES = [
    STATUS_STARTING,
    STATUS_TRACKING,
    STATUS_POSSIBLE_OUTAGE,
    STATUS_POSSIBLE_RESTORE,
    STATUS_WAITING_FOR_SOURCE,
]
