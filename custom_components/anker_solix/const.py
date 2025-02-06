"""Constants for Anker Solix."""

from datetime import datetime
from logging import Logger, getLogger

import voluptuous as vol

from homeassistant.const import Platform
import homeassistant.helpers.config_validation as cv

from .solixapi import api

LOGGER: Logger = getLogger(__package__)

NAME: str = "Anker Solix"
DOMAIN: str = "anker_solix"
MANUFACTURER: str = "Anker"
ATTRIBUTION: str = "Data provided by Anker Solix Api"
ACCEPT_TERMS: str = "accept_terms"
TERMS_LINK: str = "terms_link"
TC_LINK: str = "https://github.com/thomluther/ha-anker-solix/blob/main/README.md"
PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.DATETIME,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]
TESTMODE: str = "testmode"
TESTFOLDER: str = "testfolder"
INTERVALMULT: str = "dev_interval_mult"
UPDT_INTV_MIN: str = "updt_interval_min"
UPDT_INTV_MAX: str = "updt_interval_max"
CONF_SKIP_INVALID: str = "skip_invalid"
EXAMPLESFOLDER: str = "examples"
REGISTERED_EXCLUDES: str = "registered_excludes"
ERROR_DETAIL: str = "error_detail"
LAST_PERIOD: str = "last_period"
LAST_RESET: str = "last_reset"
SHARED_ACCOUNT: str = "shared_account"
IMAGEFOLDER: str = "images"
EXPORTFOLDER: str = "exports"

ALLOW_TESTMODE: bool = (
    True  # True will enable configuration options for testmode and testfolder
)
TEST_NUMBERVARIANCE: bool = False  # True will enable variance for some measurement numbers when running in testmode from static files (numbers have no logical meaning)
CREATE_ALL_ENTITIES: bool = False  # True will create all entities per device type for testing even if no values available

SERVICE_GET_SYSTEM_INFO = "get_system_info"
SERVICE_EXPORT_SYSTEMS = "export_systems"
SERVICE_GET_SOLARBANK_SCHEDULE = "get_solarbank_schedule"
SERVICE_CLEAR_SOLARBANK_SCHEDULE = "clear_solarbank_schedule"
SERVICE_SET_SOLARBANK_SCHEDULE = "set_solarbank_schedule"
SERVICE_UPDATE_SOLARBANK_SCHEDULE = "update_solarbank_schedule"

START_TIME = "start_time"
END_TIME = "end_time"
PLAN = "plan"
WEEK_DAYS = "week_days"
APPLIANCE_LOAD = "appliance_load"
DEVICE_LOAD = "device_load"
CHARGE_PRIORITY_LIMIT = "charge_priority_limit"
ALLOW_EXPORT = "allow_export"
DISCHARGE_PRIORITY = "discharge_priority"
INCLUDE_CACHE = "include_cache"


VALID_DAYTIME = vol.All(
    lambda v: datetime.strptime(":".join(str(v).split(":")[:2]), "%H:%M"),
)
VALID_APPLIANCE_LOAD = vol.Any(
    None,
    cv.ENTITY_MATCH_NONE,
    vol.All(
        vol.Coerce(int),
        vol.Range(
            # min=api.SolixDefaults.PRESET_MIN,  # Min for SB1 usable only
            min=0,
            max=api.SolixDefaults.PRESET_MAX * 2,
        ),
    ),
)
VALID_DEVICE_LOAD = vol.Any(
    None,
    cv.ENTITY_MATCH_NONE,
    vol.All(
        vol.Coerce(int),
        vol.Range(
            min=int(api.SolixDefaults.PRESET_MIN / 2),
            max=api.SolixDefaults.PRESET_MAX,
        ),
    ),
)
VALID_CHARGE_PRIORITY = vol.Any(
    None,
    cv.ENTITY_MATCH_NONE,
    vol.All(
        vol.Coerce(int),
        vol.Range(
            min=api.SolixDefaults.CHARGE_PRIORITY_MIN,
            max=api.SolixDefaults.CHARGE_PRIORITY_MAX,
        ),
    ),
)
VALID_SWITCH = vol.Any(None, cv.ENTITY_MATCH_NONE, vol.Coerce(bool))
VALID_WEEK_DAYS = vol.Any(None, cv.ENTITY_MATCH_NONE, cv.weekdays)
VALID_PLAN = vol.Any(
    None,
    cv.ENTITY_MATCH_NONE,
    vol.Any(api.SolarbankRatePlan.manual, api.SolarbankRatePlan.smartplugs),
)
EXTRA_PLAN_AC = vol.Any(api.SolarbankRatePlan.backup, api.SolarbankRatePlan.use_time)

SOLARBANK_TIMESLOT_DICT: dict = {
    vol.Required(START_TIME): VALID_DAYTIME,
    vol.Required(END_TIME): VALID_DAYTIME,
    vol.Optional(
        PLAN,
    ): VALID_PLAN,
    vol.Optional(
        WEEK_DAYS,
    ): VALID_WEEK_DAYS,
    vol.Optional(
        APPLIANCE_LOAD,
    ): VALID_APPLIANCE_LOAD,
    vol.Optional(
        DEVICE_LOAD,
    ): VALID_DEVICE_LOAD,
    vol.Optional(
        CHARGE_PRIORITY_LIMIT,
    ): VALID_CHARGE_PRIORITY,
    vol.Optional(
        ALLOW_EXPORT,
    ): VALID_SWITCH,
    vol.Optional(
        DISCHARGE_PRIORITY,
    ): VALID_SWITCH,
}

SOLARBANK_TIMESLOT_SCHEMA: vol.Schema = vol.All(
    cv.make_entity_service_schema(
        {**cv.TARGET_SERVICE_FIELDS, **SOLARBANK_TIMESLOT_DICT}
    ),
)

SOLIX_WEEKDAY_SCHEMA: vol.Schema = vol.All(
    cv.make_entity_service_schema(
        {
            **cv.TARGET_SERVICE_FIELDS,
            vol.Optional(
                PLAN,
            ): vol.Any(VALID_PLAN,EXTRA_PLAN_AC),
            vol.Optional(
                WEEK_DAYS,
            ): VALID_WEEK_DAYS,
        }
    ),
)

SOLIX_ENTITY_SCHEMA: vol.Schema = vol.All(
    cv.make_entity_service_schema(
        {
            **cv.TARGET_SERVICE_FIELDS,
            vol.Optional(
                INCLUDE_CACHE,
            ): VALID_SWITCH,
        }
    ),
)
