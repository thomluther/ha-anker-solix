"""Constants for Anker Solix."""

from dataclasses import fields
from datetime import datetime
from logging import Logger, getLogger
from typing import Any, Final
import urllib.parse

import voluptuous as vol

from homeassistant.const import CONF_METHOD, CONF_PAYLOAD, Platform
import homeassistant.helpers.config_validation as cv

from .solixapi.apitypes import (
    SolarbankRatePlan,
    SolixDayTypes,
    SolixDefaults,
    SolixTariffTypes,
)

LOGGER: Logger = getLogger(__package__)

NAME: Final[str] = "Anker Solix"
DOMAIN: Final[str] = "anker_solix"
MANUFACTURER: Final[str] = "Anker"
ATTRIBUTION: Final[str] = "Data provided by Anker Solix Api"
ACCEPT_TERMS: Final[str] = "accept_terms"
TERMS_LINK: Final[str] = "terms_link"
MQTT_LINK: Final[str] = "mqtt_link"
TC_LINK: Final[str] = "https://github.com/thomluther/ha-anker-solix/blob/main/README.md"
MQ_LINK: Final[str] = (
    "https://github.com/thomluther/ha-anker-solix#mqtt-managed-devices"
)
REQUEST_LINK: Final[str] = (
    "https://github.com/thomluther/ha-anker-solix/blob/main/custom_components/anker_solix/solixapi/apitypes.py#L98"
)
PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.DATETIME,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]
TESTMODE: Final[str] = "testmode"
TESTFOLDER: Final[str] = "testfolder"
CONF_MQTT_TEST_SPEED: Final[str] = "mqtt_test_speed"
INTERVALMULT: Final[str] = "dev_interval_mult"
UPDT_INTV_MIN: Final[str] = "updt_interval_min"
UPDT_INTV_MAX: Final[str] = "updt_interval_max"
CONF_SKIP_INVALID: Final[str] = "skip_invalid"
CONF_ENDPOINT_LIMIT: Final[str] = "endpoint_limit"
CONF_API_OPTIONS: Final[str] = "api_options"
CONF_MQTT_OPTIONS: Final[str] = "mqtt_options"
CONF_TEST_OPTIONS: Final[str] = "test_options"
CONF_MQTT_USAGE: Final[str] = "mqtt_usage"
CONF_TRIGGER_TIMEOUT: Final[str] = "trigger_timeout"
EXAMPLESFOLDER: Final[str] = "examples"
REGISTERED_EXCLUDES: Final[str] = "registered_excludes"
ERROR_DETAIL: Final[str] = "error_detail"
LAST_PERIOD: Final[str] = "last_period"
LAST_RESET: Final[str] = "last_reset"
SHARED_ACCOUNT: Final[str] = "shared_account"
IMAGEFOLDER: Final[str] = "images"
EXPORTFOLDER: Final[str] = "exports"
MQTT_OVERLAY: Final[str] = "mqtt_overlay"

# True will enable configuration options for testmode and testfolder
ALLOW_TESTMODE: Final[bool] = False
# True will enable variance for some measurement numbers when running in testmode from static files (numbers have no logical meaning)
TEST_NUMBERVARIANCE: Final[bool] = False
# True will create all entities per device type for testing even if no values available
CREATE_ALL_ENTITIES: Final[bool] = False
# True will enable MQTT usage per default
DEFAULT_MQTT_USAGE: Final[bool] = False

SERVICE_GET_SYSTEM_INFO: Final[str] = "get_system_info"
SERVICE_GET_DEVICE_INFO: Final[str] = "get_device_info"
SERVICE_EXPORT_SYSTEMS: Final[str] = "export_systems"
SERVICE_GET_SOLARBANK_SCHEDULE: Final[str] = "get_solarbank_schedule"
SERVICE_CLEAR_SOLARBANK_SCHEDULE: Final[str] = "clear_solarbank_schedule"
SERVICE_SET_SOLARBANK_SCHEDULE: Final[str] = "set_solarbank_schedule"
SERVICE_UPDATE_SOLARBANK_SCHEDULE: Final[str] = "update_solarbank_schedule"
SERVICE_MODIFY_SOLIX_BACKUP_CHARGE: Final[str] = "modify_solix_backup_charge"
SERVICE_MODIFY_SOLIX_USE_TIME: Final[str] = "modify_solix_use_time"
SERVICE_API_REQUEST: Final[str] = "api_request"


START_TIME: Final[str] = "start_time"
END_TIME: Final[str] = "end_time"
PLAN: Final[str] = "plan"
WEEK_DAYS: Final[str] = "week_days"
APPLIANCE_LOAD: Final[str] = "appliance_load"
DEVICE_LOAD: Final[str] = "device_load"
CHARGE_PRIORITY_LIMIT: Final[str] = "charge_priority_limit"
ALLOW_EXPORT: Final[str] = "allow_export"
DISCHARGE_PRIORITY: Final[str] = "discharge_priority"
INCLUDE_CACHE: Final[str] = "include_cache"
INCLUDE_MQTT_CACHE: Final[str] = "include_mqtt_cache"
INCLUDE_MQTT: Final[str] = "include_mqtt"
BACKUP_START: Final[str] = "backup_start"
BACKUP_END: Final[str] = "backup_end"
BACKUP_DURATION: Final[str] = "backup_duration"
ENABLE_BACKUP: Final[str] = "enable_backup"
START_MONTH: Final[str] = "start_month"
END_MONTH: Final[str] = "end_month"
DAY_TYPE: Final[str] = "day_type"
START_HOUR: Final[str] = "start_hour"
END_HOUR: Final[str] = "end_hour"
TARIFF: Final[str] = "tariff"
TARIFF_PRICE: Final[str] = "tariff_price"
DELETE: Final[str] = "delete"
ENDPOINT: Final[str] = "endpoint"


def extractNone(value: Any) -> None:
    """Validate if value to be considered as None."""
    if value is None or (
        isinstance(value, str)
        and (value == "" or value.isspace() or value.lower() == "none")
    ):
        return None
    return value


VALID_DAYTIME = vol.All(
    lambda v: datetime.strptime(":".join(str(v).split(":")[:2]), "%H:%M"),
)
VALID_APPLIANCE_LOAD = vol.All(
    extractNone,
    vol.Any(
        None,
        vol.All(
            vol.Coerce(int),
            vol.Range(
                # min=SolixDefaults.PRESET_MIN,  # Min for SB1 usable only
                min=0,
                # max=SolixDefaults.PRESET_MAX * 2, # Max. device defaults not usable anymore since multisystem capability
                max=SolixDefaults.PRESET_MAX_MULTISYSTEM,
            ),
        ),
    ),
)
# Device load settings only supported for SB1, Multisystems do not support individual device settings
VALID_DEVICE_LOAD = vol.All(
    extractNone,
    vol.Any(
        None,
        vol.All(
            vol.Coerce(int),
            vol.Range(
                min=int(SolixDefaults.PRESET_MIN / 2),
                max=SolixDefaults.PRESET_MAX,
            ),
        ),
    ),
)
VALID_CHARGE_PRIORITY = vol.All(
    extractNone,
    vol.Any(
        None,
        vol.All(
            vol.Coerce(int),
            vol.Range(
                min=SolixDefaults.CHARGE_PRIORITY_MIN,
                max=SolixDefaults.CHARGE_PRIORITY_MAX,
            ),
        ),
    ),
)
VALID_SWITCH = vol.All(extractNone, vol.Any(None, vol.Coerce(bool)))
VALID_WEEK_DAYS = vol.All(extractNone, vol.Any(None, cv.weekdays))
VALID_PLAN = vol.All(
    extractNone,
    vol.Any(
        None,
        vol.In([SolarbankRatePlan.manual, SolarbankRatePlan.smartplugs]),
    ),
)
EXTRA_PLAN_AC = vol.In([SolarbankRatePlan.backup, SolarbankRatePlan.use_time])
EXTRA_PLAN_SB3 = vol.In([SolarbankRatePlan.time_slot])
MONTHS: Final[list] = [
    "jan",
    "feb",
    "mar",
    "apr",
    "may",
    "jun",
    "jul",
    "aug",
    "sep",
    "oct",
    "nov",
    "dec",
]
VALID_MONTH = vol.All(
    extractNone,
    vol.Any(
        None,
        vol.All(
            vol.Lower,
            vol.In(MONTHS),
        ),
        vol.All(vol.Coerce(int), vol.Range(min=1, max=12)),
        msg=f"not in {MONTHS + list(range(1, 13))}",
    ),
)


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
            ): vol.Any(
                VALID_PLAN,
                EXTRA_PLAN_AC,
                EXTRA_PLAN_SB3,
                msg=f"not in {
                    [
                        field.default
                        for field in fields(SolarbankRatePlan)
                        if field.default
                    ]
                }",
            ),
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
            vol.Optional(
                INCLUDE_MQTT_CACHE,
            ): VALID_SWITCH,
        }
    ),
)

SOLIX_EXPORT_SCHEMA: vol.Schema = vol.All(
    cv.make_entity_service_schema(
        {
            **cv.TARGET_SERVICE_FIELDS,
            vol.Optional(
                INCLUDE_MQTT,
            ): VALID_SWITCH,
        }
    ),
)

SOLIX_BACKUP_CHARGE_SCHEMA: vol.Schema = vol.All(
    cv.make_entity_service_schema(
        {
            **cv.TARGET_SERVICE_FIELDS,
            vol.Optional(BACKUP_START): vol.All(
                extractNone, vol.Any(None, cv.datetime)
            ),
            vol.Optional(BACKUP_END): vol.All(extractNone, vol.Any(None, cv.datetime)),
            vol.Optional(BACKUP_DURATION): vol.All(
                extractNone,
                vol.Any(
                    None,
                    vol.All(
                        vol.Any(
                            cv.time_period_dict,
                            cv.time_period_str,
                            msg="no time period object or string",
                        ),
                        cv.positive_timedelta,
                    ),
                ),
            ),
            vol.Optional(ENABLE_BACKUP): VALID_SWITCH,
        }
    ),
)

SOLIX_USE_TIME_SCHEMA: vol.Schema = vol.All(
    cv.make_entity_service_schema(
        {
            **cv.TARGET_SERVICE_FIELDS,
            vol.Optional(START_MONTH): VALID_MONTH,
            vol.Optional(END_MONTH): VALID_MONTH,
            vol.Optional(START_HOUR): vol.All(
                extractNone,
                vol.Any(
                    None,
                    cv.time,
                    vol.Range(min=0, max=23, msg="no time and not in range 0-23"),
                ),
            ),
            vol.Optional(END_HOUR): vol.All(
                extractNone,
                vol.Any(
                    None,
                    cv.time,
                    vol.Range(min=1, max=24),
                    msg="no time and not in range 1-24",
                ),
            ),
            vol.Optional(DAY_TYPE): vol.All(
                extractNone,
                vol.Any(
                    None,
                    vol.All(
                        vol.Lower,
                        vol.In(
                            [item.value for item in SolixDayTypes],
                        ),
                    ),
                    msg=f"not in {[item.value for item in SolixDayTypes]}",
                ),
            ),
            vol.Optional(TARIFF): vol.All(
                extractNone,
                vol.Any(
                    None,
                    vol.In(
                        [item.value for item in SolixTariffTypes],
                    ),
                    vol.All(
                        vol.Lower,
                        vol.In(
                            [item.name.lower() for item in SolixTariffTypes],
                        ),
                    ),
                    msg=f"not in {[item.value for item in SolixTariffTypes] + [item.name.lower() for item in SolixTariffTypes]}",
                ),
            ),
            vol.Optional(TARIFF_PRICE): vol.All(
                extractNone, vol.Any(None, cv.positive_float)
            ),
            vol.Optional(DELETE): VALID_SWITCH,
        }
    ),
)

SOLIX_REQUEST_SCHEMA: vol.Schema = vol.All(
    cv.make_entity_service_schema(
        {
            **cv.TARGET_SERVICE_FIELDS,
            vol.Required(CONF_METHOD): vol.All(vol.Lower, vol.In(["post", "get"])),
            vol.Required(ENDPOINT): vol.All(
                extractNone,
                vol.NotIn([None]),
                cv.string,
                vol.Strip,
                urllib.parse.quote,
            ),
            vol.Optional(
                CONF_PAYLOAD,
            ): vol.All(extractNone, vol.Any(None, vol.Coerce(dict))),
        }
    ),
)
