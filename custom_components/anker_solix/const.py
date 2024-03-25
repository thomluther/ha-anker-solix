"""Constants for Anker Solix."""
from datetime import datetime
from enum import IntFlag
from logging import Logger, getLogger

import voluptuous as vol

from homeassistant.const import CONF_ENTITY_ID
import homeassistant.helpers.config_validation as cv

from .solixapi import api

LOGGER: Logger = getLogger(__package__)

NAME: str = "Anker Solix"
DOMAIN: str = "anker_solix"
VERSION: str = "1.0.0"
MANUFACTURER: str = "Anker"
ATTRIBUTION: str = "Data provided by Anker Solix Api"
ACCEPT_TERMS: str = "accept_terms"
TERMS_LINK: str = "terms_link"
TC_LINK: str = "https://github.com/thomluther/hacs-anker-solix/blob/main/README.md"
TESTMODE: str = "testmode"
TESTFOLDER: str = "testfolder"
INTERVALMULT: str = "dev_interval_mult"
UPDT_INTV_MIN: str = "updt_interval_min"
UPDT_INTV_MAX: str = "updt_interval_max"
EXAMPLESFOLDER: str = "examples"
ERROR_DETAIL: str = "error_detail"
LAST_PERIOD: str = "last_period"
LAST_RESET: str = "last_reset"
SHARED_ACCOUNT: str = "shared_account"
IMAGEFOLDER: str = "images"
ALLOW_TESTMODE: bool = (
    True  # True will enable configuration options for testmode and testfolder
)
TEST_NUMBERVARIANCE: bool = False  # True will enable variance for some measurement numbers when running in testmode from static files (numbers have no logical meaning)
CREATE_ALL_ENTITIES: bool = False  # True will create all entities per device type for testing even if no values available


class AnkerSolixEntityFeature(IntFlag):
    """Supported features of the Anker Solix Entities."""

    SOLARBANK_SCHEDULE = 1


SERVICE_GET_SOLARBANK_SCHEDULE = "get_solarbank_schedule"
SERVICE_SET_SOLARBANK_SCHEDULE = "set_solarbank_schedule"
SERVICE_UPDATE_SOLARBANK_SCHEDULE = "update_solarbank_schedule"

START_TIME = "start_time"
END_TIME = "end_time"
APPLIANCE_LOAD = "appliance_load"
CHARGE_PRIORITY_LIMIT = "charge_priority_limit"
ALLOW_DISCHARGE = "allow_discharge"


VALID_DAYTIME = vol.All(
    lambda v: datetime.strptime(":".join(str(v).split(":")[:2]), "%H:%M"),
)
VALID_APPLIANCE_LOAD = vol.Any(
    None,
    vol.All(
        vol.Coerce(int),
        vol.Range(
            min=api.SolixDefaults.PRESET_MIN,
            max=api.SolixDefaults.PRESET_MAX,
        ),
    ),
)
VALID_CHARGE_PRIORITY = vol.Any(
    None,
    vol.All(
        vol.Coerce(int),
        vol.Range(
            min=api.SolixDefaults.CHARGE_PRIORITY_MIN,
            max=api.SolixDefaults.CHARGE_PRIORITY_MAX,
        ),
    ),
)
VALID_ALLOW_DISCHARGE = vol.Any(None, vol.Coerce(bool))
VALID_ENTITY_ID = vol.All(
    vol.Coerce(str),
    vol.Length(min=1),
    cv.entity_id,
    cv.entity_domain(DOMAIN),
)

SOLARBANK_TIMESLOT_DICT: dict = {
    vol.Required(START_TIME): VALID_DAYTIME,
    vol.Required(END_TIME): VALID_DAYTIME,
    vol.Optional(
        APPLIANCE_LOAD,
    ): VALID_APPLIANCE_LOAD,
    vol.Optional(
        CHARGE_PRIORITY_LIMIT,
    ): VALID_CHARGE_PRIORITY,
    vol.Optional(
        ALLOW_DISCHARGE,
    ): VALID_ALLOW_DISCHARGE,
}

SOLARBANK_TIMESLOT_SCHEMA: vol.Schema = vol.All(
    cv.make_entity_service_schema(
        {vol.Required(CONF_ENTITY_ID): VALID_ENTITY_ID, **SOLARBANK_TIMESLOT_DICT}
    ),
    cv.has_at_least_one_key(APPLIANCE_LOAD, CHARGE_PRIORITY_LIMIT, ALLOW_DISCHARGE),
)

SOLARBANK_ENTITY_SCHEMA: vol.Schema = vol.All(
    cv.make_entity_service_schema(
        {vol.Required(CONF_ENTITY_ID): VALID_ENTITY_ID}
    ),
)

