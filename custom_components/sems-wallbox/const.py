"""Constants for the sems integration."""

DOMAIN = "sems-wallbox"

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, CONF_SCAN_INTERVAL
from datetime import timedelta

CONF_STATION_ID = "wallbox_serial_No"

DEFAULT_SCAN_INTERVAL = 20  # timedelta(seconds=20)

# Validation of the user's configuration
SEMS_CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_STATION_ID): str,
        vol.Optional(
            CONF_SCAN_INTERVAL, description={"suggested_value": 60}
        ): int,  # , default=DEFAULT_SCAN_INTERVAL
    }
)
