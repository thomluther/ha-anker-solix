"""Sensor platform for anker_solix."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from pathlib import Path
from random import choice, randrange
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_EXCLUDE,
    PERCENTAGE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    EntityCategory,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, SupportsResponse, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr, entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .config_flow import _SCAN_INTERVAL_MIN
from .const import (
    ALLOW_EXPORT,
    ALLOW_TESTMODE,
    APPLIANCE_LOAD,
    ATTRIBUTION,
    CHARGE_PRIORITY_LIMIT,
    CONF_SKIP_INVALID,
    CREATE_ALL_ENTITIES,
    DEVICE_LOAD,
    DISCHARGE_PRIORITY,
    DOMAIN,
    END_TIME,
    INCLUDE_CACHE,
    LOGGER,
    MQTT_OVERLAY,
    PLAN,
    SERVICE_CLEAR_SOLARBANK_SCHEDULE,
    SERVICE_GET_SOLARBANK_SCHEDULE,
    SERVICE_GET_SYSTEM_INFO,
    SERVICE_SET_SOLARBANK_SCHEDULE,
    SERVICE_UPDATE_SOLARBANK_SCHEDULE,
    SOLARBANK_TIMESLOT_SCHEMA,
    SOLIX_ENTITY_SCHEMA,
    SOLIX_WEEKDAY_SCHEMA,
    START_TIME,
    TEST_NUMBERVARIANCE,
    WEEK_DAYS,
)
from .coordinator import AnkerSolixDataUpdateCoordinator
from .entity import (
    AnkerSolixEntityFeature,
    AnkerSolixEntityRequiredKeyMixin,
    AnkerSolixEntityType,
    AnkerSolixPicturePath,
    get_AnkerSolixAccountInfo,
    get_AnkerSolixDeviceInfo,
    get_AnkerSolixSubdeviceInfo,
    get_AnkerSolixSystemInfo,
    get_AnkerSolixVehicleInfo,
)
from .solixapi.apitypes import (
    ApiCategories,
    SmartmeterStatus,
    Solarbank2Timeslot,
    SolarbankAiemsRuntimeStatus,
    SolarbankPowerMode,
    SolarbankRatePlan,
    SolarbankStatus,
    SolarbankTimeslot,
    SolarbankUsageMode,
    SolixDeviceStatus,
    SolixDeviceType,
    SolixGridStatus,
    SolixParmType,
    SolixPpsPortStatus,
    SolixRoleStatus,
)
from .solixapi.helpers import get_enum_name


@dataclass(frozen=True)
class AnkerSolixSensorDescription(
    SensorEntityDescription, AnkerSolixEntityRequiredKeyMixin
):
    """Sensor entity description with optional keys."""

    picture_path: str = None
    feature: AnkerSolixEntityFeature | None = None
    check_invalid: bool = False
    restore: bool = False
    mqtt: bool = False
    # Use optionally to provide function for value calculation or lookup of nested values
    value_fn: Callable[[dict, str, str], StateType] = lambda d, jk, ctx: d.get(jk)
    attrib_fn: Callable[[dict, str], dict | None] = lambda d, ctx: None
    unit_fn: Callable[[dict, str], dict | None] = lambda d, ctx: None
    force_creation_fn: Callable[[dict], bool] = lambda d: False
    exclude_fn: Callable[[set, dict], bool] = lambda s, d: False
    nested_sensor: bool = False


DEVICE_SENSORS = [
    AnkerSolixSensorDescription(
        # Balcony power device status
        key="status_desc",
        translation_key="status_desc",
        json_key="status_desc",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.ENUM,
        options=[status.name for status in SolixDeviceStatus],
        attrib_fn=lambda d, _: {
            "status": d.get("status"),
        },
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        # HES device status
        key="status_desc",
        translation_key="status_desc",
        json_key="status_desc",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        options=[status.name for status in SolixDeviceStatus],
        value_fn=lambda d, jk, _: (d.get("hes_data") or {}).get(jk),
        attrib_fn=lambda d, _: {
            "status": (d.get("hes_data") or {}).get("online_status"),
            "network": (d.get("hes_data") or {}).get("network_status_desc"),
            "network_code": (d.get("hes_data") or {}).get("network_status"),
        },
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
    ),
    AnkerSolixSensorDescription(
        # Balcony device charging status
        key="charging_status_desc",
        translation_key="charging_status_desc",
        json_key="charging_status_desc",
        device_class=SensorDeviceClass.ENUM,
        options=[status.name for status in SolarbankStatus],
        attrib_fn=lambda d, _: {"charging_status": d.get("charging_status")},
        exclude_fn=lambda s, _: not ({SolixDeviceType.SOLARBANK.value} - s),
        check_invalid=True,
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        # HES station status
        key="hes_station_role",
        translation_key="hes_station_role",
        json_key="role_status_desc",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        options=[status.name for status in SolixRoleStatus],
        value_fn=lambda d, jk, _: (d.get("hes_data") or {}).get(jk),
        attrib_fn=lambda d, _: {
            "role_status": (d.get("hes_data") or {}).get("master_slave_status"),
            "station_id": (d.get("hes_data") or {}).get("station_id"),
            "station_type": (d.get("hes_data") or {}).get("type"),
        },
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
    ),
    AnkerSolixSensorDescription(
        # Photovoltaik power of device
        key="input_power",
        translation_key="input_power",
        json_key="input_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        # use different MQTT value name if overlay
        value_fn=lambda d, jk, _: (d.get("photovoltaic_power") or d.get(jk))
        if d.get(MQTT_OVERLAY)
        else (d.get(jk) or d.get("photovoltaic_power")),
        # track MPPT voltage here if no PV channel breakdown in data
        attrib_fn=lambda d, _: {}
        if d.get("solar_power_1") or d.get("pv_1_power")
        else (
            ({"pv_1_voltage": v} if (v := d.get("pv_1_voltage")) else {})
            | ({"pv_2_voltage": v} if (v := d.get("pv_2_voltage")) else {})
        ),
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        check_invalid=True,
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="solar_power_1",
        translation_key="solar_power_1",
        json_key="solar_power_1",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda d, jk, _: (d.get("pv_1_power") or d.get(jk))
        if d.get(MQTT_OVERLAY)
        else (d.get(jk) or d.get("pv_1_power")),
        attrib_fn=lambda d, _: {
            "name": (d.get("pv_name") or {}).get("pv1_name") or "",
        }
        | ({"voltage": v} if (v := d.get("pv_1_voltage")) else {}),
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        check_invalid=True,
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="solar_power_2",
        translation_key="solar_power_2",
        json_key="solar_power_2",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda d, jk, _: (d.get("pv_2_power") or d.get(jk))
        if d.get(MQTT_OVERLAY)
        else (d.get(jk) or d.get("pv_2_power")),
        attrib_fn=lambda d, _: {
            "name": (d.get("pv_name") or {}).get("pv2_name") or "",
        }
        | ({"voltage": v} if (v := d.get("pv_2_voltage")) else {}),
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        check_invalid=True,
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="solar_power_3",
        translation_key="solar_power_3",
        json_key="solar_power_3",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda d, jk, _: (d.get("pv_3_power") or d.get(jk))
        if d.get(MQTT_OVERLAY)
        else (d.get(jk) or d.get("pv_3_power")),
        attrib_fn=lambda d, _: {
            "name": (d.get("pv_name") or {}).get("pv3_name") or "",
        }
        | ({"voltage": v} if (v := d.get("pv_3_voltage")) else {}),
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        check_invalid=True,
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="solar_power_4",
        translation_key="solar_power_4",
        json_key="solar_power_4",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda d, jk, _: (d.get("pv_4_power") or d.get(jk))
        if d.get(MQTT_OVERLAY)
        else (d.get(jk) or d.get("pv_4_power")),
        attrib_fn=lambda d, _: {
            "name": (d.get("pv_name") or {}).get("pv4_name") or "",
        }
        | ({"voltage": v} if (v := d.get("pv_4_voltage")) else {}),
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        check_invalid=True,
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="dc_input_power",
        translation_key="dc_input_power",
        json_key="dc_input_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="dc_input_power_total",
        translation_key="dc_input_power_total",
        json_key="dc_input_power_total",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="ac_input_power",
        translation_key="ac_input_power",
        json_key="ac_input_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="ac_input_power_total",
        translation_key="ac_input_power_total",
        json_key="ac_input_power_total",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="ac_socket",
        translation_key="ac_socket",
        json_key="ac_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        check_invalid=True,
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="dc_output_power",
        translation_key="dc_output_power",
        json_key="output_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        check_invalid=True,
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="dc_output_power_total",
        translation_key="dc_output_power_total",
        json_key="dc_output_power_total",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        check_invalid=True,
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        # can be combined AC/DC output power
        key="output_power_total",
        translation_key="output_power_total",
        json_key="output_power_total",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        check_invalid=True,
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="ac_output_power",
        translation_key="ac_output_power",
        json_key="ac_output_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="ac_output_power_total",
        translation_key="ac_output_power_total",
        json_key="ac_output_power_total",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="battery_power_signed",
        translation_key="battery_power_signed",
        json_key="charging_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        # use different MQTT value name if overlay
        value_fn=lambda d, jk, _: (d.get("battery_power_signed") or d.get(jk))
        if d.get(MQTT_OVERLAY)
        else (d.get(jk) or d.get("battery_power_signed")),
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="bat_discharge_power",
        translation_key="bat_discharge_power",
        json_key="bat_discharge_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="bat_charge_power",
        translation_key="bat_charge_power",
        json_key="bat_charge_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="ac_to_home_load",
        translation_key="ac_to_home_load",
        json_key="to_home_load",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        check_invalid=True,
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="ac_generate_power",
        translation_key="ac_generate_power",
        json_key="generate_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, _: not ({SolixDeviceType.INVERTER.value} - s),
    ),
    AnkerSolixSensorDescription(
        key="current_power",
        translation_key="current_power",
        json_key="current_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
    ),
    AnkerSolixSensorDescription(
        key="heating_power",
        translation_key="heating_power",
        json_key="pei_heating_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="grid_to_battery_power",
        translation_key="grid_to_battery_power",
        json_key="grid_to_battery_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="all_power_limit",
        translation_key="all_power_limit",
        json_key="all_power_limit",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
    ),
    AnkerSolixSensorDescription(
        key="all_ac_input_limit",
        translation_key="all_ac_input_limit",
        json_key="all_ac_input_limit",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
    ),
    AnkerSolixSensorDescription(
        key="power_limit_option",
        translation_key="power_limit_option",
        json_key="power_limit_option",
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
    ),
    AnkerSolixSensorDescription(
        key="micro_inverter_power",
        translation_key="micro_inverter_power",
        json_key="micro_inverter_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        attrib_fn=lambda d, _: {
            "name": (d.get("pv_name") or {}).get("micro_inverter_name") or "",
        },
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
    ),
    AnkerSolixSensorDescription(
        key="micro_inverter_power_limit",
        translation_key="micro_inverter_power_limit",
        json_key="micro_inverter_power_limit",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
    ),
    AnkerSolixSensorDescription(
        key="energy_today",
        translation_key="energy_today",
        json_key="energy_today",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: d.get(jk),
        attrib_fn=lambda d, _: {"last_period": d.get("energy_last_period")},
        exclude_fn=lambda s, d: not (
            {d.get("type")} - s and {ApiCategories.smartplug_energy} - s
        ),
    ),
    AnkerSolixSensorDescription(
        # Resulting Output preset per device
        # This may also present 0 W if the allow discharge switch is disabled, even if the W preset value remains and the minimum bypass per defined inverter will be used
        # This is confusing in the App and the Api, since there may be the minimum bypass W applied even if 0 W is shown.
        # 0 W is only applied truly if the 0 W Switch is installed for non Anker inverters, or if MI80 is used which supports the 0 W setting natively
        # NOTE: The Api does not reflect active blend plan output power in this field, only the custom plan preset or the default setting without customer plan
        key="set_output_power",
        translation_key="set_output_power",
        json_key="set_output_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        attrib_fn=lambda d, _: {"schedule": d.get("schedule")},
        feature=AnkerSolixEntityFeature.SOLARBANK_SCHEDULE,
        # This entry has the unit with the number and needs to be removed
        value_fn=lambda d, jk, _: str(d.get(jk) or "").replace("W", "") or None,
        # Force the creation for solarbanks since data could be empty if disconnected?
        force_creation_fn=lambda d: bool(
            d.get("type") == SolixDeviceType.SOLARBANK.value and "set_output_power" in d
        ),
        exclude_fn=lambda s, _: not ({SolixDeviceType.SOLARBANK.value} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="set_power_mode",
        translation_key="set_power_mode",
        json_key="preset_power_mode",
        device_class=SensorDeviceClass.ENUM,
        options=[mode.name for mode in SolarbankPowerMode],
        value_fn=lambda d, jk, _: get_enum_name(SolarbankPowerMode, d.get(jk)),
        attrib_fn=lambda d, _: {
            "mode": d.get("preset_power_mode"),
        },
        exclude_fn=lambda s, _: not ({SolixDeviceType.SOLARBANK.value} - s),
        force_creation_fn=lambda d: "preset_power_mode" in d
        and d.get("cascaded")
        and int(d.get("solarbank_count") or 0) > 1,
    ),
    AnkerSolixSensorDescription(
        # general device overall state of charge
        key="state_of_charge",
        translation_key="state_of_charge",
        json_key="battery_soc",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        # show some attributes only if no main battery data available, to avoid duplicate attributes
        attrib_fn=lambda d, _: (
            {
                "state_of_health": v,
            }
            if (v := d.get("battery_soh")) and "main_battery_soc" not in d
            else {}
        )
        | (
            {
                "voltage": v,
            }
            if (v := d.get("battery_voltage"))
            else {}
        ),
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        check_invalid=True,
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="remaining_time_hours",
        translation_key="remaining_time_hours",
        json_key="remaining_time_hours",
        value_fn=lambda d, jk, _: None
        if (val := d.get(jk)) is None
        else timedelta(hours=val),
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        # calculated or customized entity
        key="battery_energy",
        translation_key="battery_energy",
        json_key="battery_energy",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        suggested_display_precision=0,
        # Capacity moved to number entities to allow customization
        # attrib_fn=lambda d, _: {
        #     "capacity": " ".join(
        #         [str(d.get("battery_capacity") or "----"), UnitOfEnergy.WATT_HOUR]
        #     )
        # },
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
    ),
    AnkerSolixSensorDescription(
        key="discharged_energy",
        translation_key="discharged_energy",
        json_key="discharged_energy",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=3,
        exclude_fn=lambda s, d: not (
            ({d.get("type")} - s) and ({f"{d.get('type', '')!s}_energy"} - s)
        ),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="charged_energy",
        translation_key="charged_energy",
        json_key="charged_energy",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=3,
        exclude_fn=lambda s, d: not (
            ({d.get("type")} - s) and ({f"{d.get('type', '')!s}_energy"} - s)
        ),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="output_energy",
        translation_key="output_energy",
        json_key="output_energy",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=3,
        exclude_fn=lambda s, d: not (
            ({d.get("type")} - s) and ({f"{d.get('type', '')!s}_energy"} - s)
        ),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="solar_energy",
        translation_key="solar_energy",
        json_key="pv_yield",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=3,
        exclude_fn=lambda s, d: not (
            ({d.get("type")} - s) and ({f"{d.get('type', '')!s}_energy"} - s)
        ),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        # calculated entity
        key="device_efficiency",
        translation_key="device_efficiency",
        json_key="device_efficiency",
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=2,
        exclude_fn=lambda s, d: not (
            ({d.get("type")} - s) and ({f"{d.get('type', '')!s}_energy"} - s)
        ),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        # calculated entity
        key="battery_efficiency",
        translation_key="battery_efficiency",
        json_key="battery_efficiency",
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=2,
        exclude_fn=lambda s, d: not (
            ({d.get("type")} - s) and ({f"{d.get('type', '')!s}_energy"} - s)
        ),
        mqtt=True,
    ),
    # This value does not seem to be used by any device
    # AnkerSolixSensorDescription(
    #     key="bws_surplus",
    #     translation_key="bws_surplus",
    #     json_key="bws_surplus",
    #     entity_registry_enabled_default=False,
    #     native_unit_of_measurement=UnitOfPower.WATT,
    #     device_class=SensorDeviceClass.POWER,
    #     state_class=SensorStateClass.MEASUREMENT,
    #     exclude_fn=lambda s, d: not ({d.get("type")} - s),
    #     check_invalid=True,
    # ),
    AnkerSolixSensorDescription(
        key="temperature",
        translation_key="temperature",
        json_key="temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="exp_1_temperature",
        translation_key="exp_1_temperature",
        json_key="exp_1_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="exp_2_temperature",
        translation_key="exp_2_temperature",
        json_key="exp_2_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="exp_3_temperature",
        translation_key="exp_3_temperature",
        json_key="exp_3_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="exp_4_temperature",
        translation_key="exp_4_temperature",
        json_key="exp_4_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="exp_5_temperature",
        translation_key="exp_5_temperature",
        json_key="exp_5_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="sw_version",
        translation_key="sw_version",
        json_key="sw_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
    ),
    AnkerSolixSensorDescription(
        key="sub_package_num",
        translation_key="sub_package_num",
        json_key="sub_package_num",
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        # use different MQTT value name if overlay, show only if exp pack installed
        value_fn=lambda d, jk, _: (
            (d.get("expansion_packs") or d.get(jk))
            if d.get(MQTT_OVERLAY)
            else (d.get(jk) or d.get("expansion_packs"))
        )
        or None,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        check_invalid=True,
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="inverter_info",
        translation_key="inverter_info",
        json_key="solar_model_name",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d, jk, _: (d.get("solar_info") or {}).get(jk),
        attrib_fn=lambda d, _: {
            "solar_brand": (d.get("solar_info") or {}).get("solar_brand"),
            "solar_model": (d.get("solar_info") or {}).get("solar_model"),
            "solar_sn": (d.get("solar_info") or {}).get("solar_sn"),
        },
        exclude_fn=lambda s, _: not (
            {SolixDeviceType.SOLARBANK.value} - s
            and {ApiCategories.solarbank_solar_info} - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="fittings",
        translation_key="fittings",
        json_key="fittings",
        nested_sensor=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d, jk, c: ((d.get(jk) or {}).get(c.split("_")[1]) or {}).get(
            "alias_name"
        ),
        attrib_fn=lambda d, c: {
            "device_sn": ((d.get("fittings") or {}).get(c.split("_")[1]) or {}).get(
                "device_sn"
            ),
            "device_name": ((d.get("fittings") or {}).get(c.split("_")[1]) or {}).get(
                "device_name"
            ),
            "device_pn": ((d.get("fittings") or {}).get(c.split("_")[1]) or {}).get(
                "product_code"
            ),
            "bt_mac": ((d.get("fittings") or {}).get(c.split("_")[1]) or {}).get(
                "bt_ble_mac"
            ),
        },
        exclude_fn=lambda s, _: not (
            {SolixDeviceType.SOLARBANK.value} - s
            and {ApiCategories.solarbank_fittings} - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="grid_power_signed",
        translation_key="grid_power_signed",
        json_key="grid_power_signed",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="photovoltaic_to_grid_power",
        translation_key="photovoltaic_to_grid_power",
        json_key="photovoltaic_to_grid_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        # use different MQTT value name if overlay
        value_fn=lambda d, jk, _: (
            (d.get("pv_to_grid_power") or d.get(jk))
            if d.get(MQTT_OVERLAY)
            else (d.get(jk) or d.get("pv_to_grid_power"))
        )
        or None,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        check_invalid=True,
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="grid_to_home_power",
        translation_key="grid_to_home_power",
        json_key="grid_to_home_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, _: not ({SolixDeviceType.SMARTMETER.value} - s),
        check_invalid=True,
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        # balcony systems grid status
        key="grid_status_desc",
        translation_key="grid_status_desc",
        json_key="grid_status_desc",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        options=[status.name for status in SmartmeterStatus],
        attrib_fn=lambda d, _: {"grid_status": d.get("grid_status")},
        exclude_fn=lambda s, _: not ({SolixDeviceType.SMARTMETER.value} - s),
        check_invalid=True,
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        # HES systems grid status
        key="grid_status_desc",
        translation_key="grid_status_desc",
        json_key="grid_status_desc",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        options=[status.name for status in SolixGridStatus],
        value_fn=lambda d, jk, _: (d.get("hes_data") or {}).get(jk),
        attrib_fn=lambda d, _: {
            "grid_status": (d.get("hes_data") or {}).get("grid_status")
        },
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
    ),
    AnkerSolixSensorDescription(
        key="tag",
        translation_key="tag",
        json_key="tag",
        # This value my be empty for devices not supporting tags
        value_fn=lambda d, jk, _: d.get(jk) or None,
        exclude_fn=lambda s, d: not (
            {d.get("type")} - s and {ApiCategories.device_tag} - s
        ),
        check_invalid=True,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    AnkerSolixSensorDescription(
        key="err_code",
        translation_key="err_code",
        json_key="err_code",
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        check_invalid=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="discharge_power_avg",
        translation_key="discharge_power",
        json_key="discharge_power_avg",
        unit_fn=lambda d, _: str((d.get("average_power") or {}).get("power_unit") or "")
        .lower()
        .replace("w", "W"),
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: None
        if not (avg := d.get("average_power"))
        else avg.get(jk),
        exclude_fn=lambda s, _: not (
            {SolixDeviceType.POWERPANEL.value, SolixDeviceType.HES.value} - s
            and {ApiCategories.powerpanel_avg_power, ApiCategories.hes_avg_power} - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="charge_power_avg",
        translation_key="charge_power",
        json_key="charge_power_avg",
        unit_fn=lambda d, _: str((d.get("average_power") or {}).get("power_unit") or "")
        .lower()
        .replace("w", "W"),
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: None
        if not (avg := d.get("average_power"))
        else avg.get(jk),
        exclude_fn=lambda s, _: not (
            {SolixDeviceType.POWERPANEL.value, SolixDeviceType.HES.value} - s
            and {ApiCategories.powerpanel_avg_power, ApiCategories.hes_avg_power} - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="solar_power_avg",
        translation_key="input_power",
        json_key="solar_power_avg",
        unit_fn=lambda d, _: str((d.get("average_power") or {}).get("power_unit") or "")
        .lower()
        .replace("w", "W"),
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: None
        if not (avg := d.get("average_power"))
        else avg.get(jk),
        exclude_fn=lambda s, _: not (
            {SolixDeviceType.POWERPANEL.value, SolixDeviceType.HES.value} - s
            and {ApiCategories.powerpanel_avg_power, ApiCategories.hes_avg_power} - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="home_usage_avg",
        translation_key="home_load_power",
        json_key="home_usage_avg",
        unit_fn=lambda d, _: str((d.get("average_power") or {}).get("power_unit") or "")
        .lower()
        .replace("w", "W"),
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: None
        if not (avg := d.get("average_power"))
        else avg.get(jk),
        exclude_fn=lambda s, _: not (
            {SolixDeviceType.POWERPANEL.value, SolixDeviceType.HES.value} - s
            and {ApiCategories.powerpanel_avg_power, ApiCategories.hes_avg_power} - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="grid_import_avg",
        translation_key="grid_to_home_power",
        json_key="grid_import_avg",
        unit_fn=lambda d, _: str((d.get("average_power") or {}).get("power_unit") or "")
        .lower()
        .replace("w", "W"),
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: None
        if not (avg := d.get("average_power"))
        else avg.get(jk),
        exclude_fn=lambda s, _: not (
            {SolixDeviceType.POWERPANEL.value, SolixDeviceType.HES.value} - s
            and {ApiCategories.powerpanel_avg_power, ApiCategories.hes_avg_power} - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="grid_export_avg",
        translation_key="photovoltaic_to_grid_power",
        json_key="grid_export_avg",
        unit_fn=lambda d, _: str((d.get("average_power") or {}).get("power_unit") or "")
        .lower()
        .replace("w", "W"),
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: None
        if not (avg := d.get("average_power"))
        else avg.get(jk),
        exclude_fn=lambda s, _: not (
            {SolixDeviceType.POWERPANEL.value, SolixDeviceType.HES.value} - s
            and {ApiCategories.powerpanel_avg_power, ApiCategories.hes_avg_power} - s
        ),
    ),
    AnkerSolixSensorDescription(
        # Power panel and HES overall SOC
        key="state_of_charge",
        translation_key="state_of_charge",
        json_key="state_of_charge",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda d, jk, _: None
        if not (avg := d.get("average_power"))
        else avg.get(jk),
        exclude_fn=lambda s, _: not (
            {SolixDeviceType.POWERPANEL.value, SolixDeviceType.HES.value} - s
            and {ApiCategories.powerpanel_avg_power, ApiCategories.hes_avg_power} - s
        ),
    ),
    AnkerSolixSensorDescription(
        # timestamp of average power data, round down valid time to 5 minutes to match energy data timestamp
        key="data_timestamp",
        translation_key="data_timestamp",
        json_key="valid_time",
        value_fn=lambda d, jk, _: None
        if not (val := (d.get("average_power") or {}).get(jk) or "")
        else (
            (tm := datetime.strptime(val, "%Y-%m-%d %H:%M:%S"))
            - timedelta(
                minutes=tm.minute % 5, seconds=tm.second, microseconds=tm.microsecond
            )
        ).isoformat(sep=" "),
        attrib_fn=lambda d, _: {
            "last_check": None
            if not (tm := (d.get("average_power") or {}).get("last_check"))
            else datetime.strptime(tm, "%Y-%m-%d %H:%M:%S").isoformat(sep=" "),
        },
        exclude_fn=lambda s, _: not (
            {SolixDeviceType.POWERPANEL.value, SolixDeviceType.HES.value} - s
            and {ApiCategories.powerpanel_avg_power, ApiCategories.hes_avg_power} - s
        ),
    ),
    AnkerSolixSensorDescription(
        # timestamp of last MQTT message with any update
        key="mqtt_timestamp",
        translation_key="mqtt_timestamp",
        json_key="last_update",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d, jk, _: None
        if not (val := d.get(jk) or "")
        else (datetime.strptime(val, "%Y-%m-%d %H:%M:%S")).isoformat(sep=" "),
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="usbc_1_power",
        translation_key="usbc_1_power",
        json_key="usbc_1_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        attrib_fn=lambda d, _: {
            "port_status": get_enum_name(
                SolixPpsPortStatus,
                str(d.get("usbc_1_status")),
                default=SolixPpsPortStatus.unknown.name,
            ),
        }
        if "usbc_1_status" in d
        else {},
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="usbc_2_power",
        translation_key="usbc_2_power",
        json_key="usbc_2_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        attrib_fn=lambda d, _: {
            "port_status": get_enum_name(
                SolixPpsPortStatus,
                str(d.get("usbc_2_status")),
                default=SolixPpsPortStatus.unknown.name,
            ),
        }
        if "usbc_2_status" in d
        else {},
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="usbc_3_power",
        translation_key="usbc_3_power",
        json_key="usbc_3_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        attrib_fn=lambda d, _: {
            "port_status": get_enum_name(
                SolixPpsPortStatus,
                str(d.get("usbc_3_status")),
                default=SolixPpsPortStatus.unknown.name,
            ),
        }
        if "usbc_3_status" in d
        else {},
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="usbc_4_power",
        translation_key="usbc_4_power",
        json_key="usbc_4_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        attrib_fn=lambda d, _: {
            "port_status": get_enum_name(
                SolixPpsPortStatus,
                str(d.get("usbc_4_status")),
                default=SolixPpsPortStatus.unknown.name,
            ),
        }
        if "usbc_4_status" in d
        else {},
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="usba_1_power",
        translation_key="usba_1_power",
        json_key="usba_1_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        attrib_fn=lambda d, _: {
            "port_status": get_enum_name(
                SolixPpsPortStatus,
                str(d.get("usba_1_status")),
                default=SolixPpsPortStatus.unknown.name,
            ),
        }
        if "usba_1_status" in d
        else {},
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="usba_2_power",
        translation_key="usba_2_power",
        json_key="usba_2_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        attrib_fn=lambda d, _: {
            "port_status": get_enum_name(
                SolixPpsPortStatus,
                str(d.get("usba_2_status")),
                default=SolixPpsPortStatus.unknown.name,
            ),
        }
        if "usba_2_status" in d
        else {},
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="dc_12v_1_power",
        translation_key="dc_12v_1_power",
        json_key="dc_12v_1_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="dc_12v_2_power",
        translation_key="dc_12v_2_power",
        json_key="dc_12v_2_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="main_battery_soc",
        translation_key="main_battery_soc",
        json_key="main_battery_soc",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        attrib_fn=lambda d, _: (
            {
                "state_of_health": v,
            }
            if (v := d.get("battery_soh"))
            else {}
        )
        | (
            {
                "serialnumber": v,
            }
            if (v := d.get("device_sn"))
            else {}
        ),
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="exp_1_soc",
        translation_key="exp_1_soc",
        json_key="exp_1_soc",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        attrib_fn=lambda d, _: (
            {
                "state_of_health": v,
            }
            if (v := d.get("exp_1_soh"))
            else {}
        )
        | (
            {
                "serialnumber": v,
            }
            if (v := d.get("exp_1_sn"))
            else {}
        )
        | (
            {
                "type": v,
            }
            if (v := d.get("exp_1_type"))
            else {}
        ),
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        check_invalid=True,
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="exp_2_soc",
        translation_key="exp_2_soc",
        json_key="exp_2_soc",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        attrib_fn=lambda d, _: (
            {
                "state_of_health": v,
            }
            if (v := d.get("exp_2_soh"))
            else {}
        )
        | (
            {
                "serialnumber": v,
            }
            if (v := d.get("exp_2_sn"))
            else {}
        )
        | (
            {
                "type": v,
            }
            if (v := d.get("exp_2_type"))
            else {}
        ),
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        check_invalid=True,
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="exp_3_soc",
        translation_key="exp_3_soc",
        json_key="exp_3_soc",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        attrib_fn=lambda d, _: (
            {
                "state_of_health": v,
            }
            if (v := d.get("exp_3_soh"))
            else {}
        )
        | (
            {
                "serialnumber": v,
            }
            if (v := d.get("exp_3_sn"))
            else {}
        )
        | (
            {
                "type": v,
            }
            if (v := d.get("exp_3_type"))
            else {}
        ),
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        check_invalid=True,
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="exp_4_soc",
        translation_key="exp_4_soc",
        json_key="exp_4_soc",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        attrib_fn=lambda d, _: (
            {
                "state_of_health": v,
            }
            if (v := d.get("exp_4_soh"))
            else {}
        )
        | (
            {
                "serialnumber": v,
            }
            if (v := d.get("exp_4_sn"))
            else {}
        )
        | (
            {
                "type": v,
            }
            if (v := d.get("exp_4_type"))
            else {}
        ),
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        check_invalid=True,
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="exp_5_soc",
        translation_key="exp_5_soc",
        json_key="exp_5_soc",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        attrib_fn=lambda d, _: (
            {
                "state_of_health": v,
            }
            if (v := d.get("exp_5_soh"))
            else {}
        )
        | (
            {
                "serialnumber": v,
            }
            if (v := d.get("exp_5_sn"))
            else {}
        )
        | (
            {
                "type": v,
            }
            if (v := d.get("exp_5_type"))
            else {}
        ),
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        check_invalid=True,
        mqtt=True,
    ),
]

SITE_SENSORS = [
    AnkerSolixSensorDescription(
        key="solarbank_list",
        translation_key="solarbank_list",
        json_key="solarbank_list",
        picture_path=AnkerSolixPicturePath.SOLARBANK,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d, jk, _: count
        if (count := len(list((d.get("solarbank_info") or {}).get(jk) or []))) > 0
        else None,
        exclude_fn=lambda s, _: not ({SolixDeviceType.SOLARBANK.value} - s),
    ),
    AnkerSolixSensorDescription(
        key="pps_list",
        translation_key="pps_list",
        json_key="pps_list",
        picture_path=AnkerSolixPicturePath.PPS,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d, jk, _: count
        if (count := len(list((d.get("pps_info") or {}).get(jk) or []))) > 0
        else None,
        exclude_fn=lambda s, _: not ({SolixDeviceType.PPS.value} - s),
    ),
    AnkerSolixSensorDescription(
        key="solar_list",
        translation_key="solar_list",
        json_key="solar_list",
        picture_path=AnkerSolixPicturePath.INVERTER,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d, jk, _: count
        if (count := len(list(d.get(jk) or []))) > 0
        else None,
        exclude_fn=lambda s, _: not ({SolixDeviceType.INVERTER.value} - s),
    ),
    AnkerSolixSensorDescription(
        key="powerpanel_list",
        translation_key="powerpanel_list",
        json_key="powerpanel_list",
        picture_path=AnkerSolixPicturePath.POWERPANEL,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d, jk, _: count
        if (count := len(list(d.get(jk) or []))) > 0
        else None,
        exclude_fn=lambda s, _: not ({SolixDeviceType.POWERPANEL.value} - s),
    ),
    AnkerSolixSensorDescription(
        key="smartmeter_list",
        translation_key="smartmeter_list",
        json_key="grid_list",
        picture_path=AnkerSolixPicturePath.SMARTMETER,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d, jk, _: count
        if (count := len(list((d.get("grid_info") or {}).get(jk) or []))) > 0
        else None,
        exclude_fn=lambda s, _: not ({SolixDeviceType.SMARTMETER.value} - s),
    ),
    AnkerSolixSensorDescription(
        key="smartplug_list",
        translation_key="smartplug_list",
        json_key="smartplug_list",
        picture_path=AnkerSolixPicturePath.SMARTPLUG,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d, jk, _: count
        if (count := len(list((d.get("smart_plug_info") or {}).get(jk) or []))) > 0
        else None,
        exclude_fn=lambda s, _: not ({SolixDeviceType.SMARTPLUG.value} - s),
    ),
    AnkerSolixSensorDescription(
        key="hes_list",
        translation_key="hes_list",
        json_key="hes_list",
        picture_path=AnkerSolixPicturePath.HES,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d, jk, _: count
        if (count := len(list((d.get("hes_info") or {}).get(jk) or []))) > 0
        else None,
        exclude_fn=lambda s, _: not ({SolixDeviceType.HES.value} - s),
    ),
    AnkerSolixSensorDescription(
        # Summary of all solarbank charing power on site
        key="solarbank_battery_power_signed",
        translation_key="solarbank_battery_power_signed",
        json_key="total_charging_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d, jk, _: (d.get("solarbank_info") or {}).get(jk),
        suggested_display_precision=0,
        # exclude sensor if unused artifacts in structure
        exclude_fn=lambda s, d: not ({SolixDeviceType.SOLARBANK.value} - s)
        or not list((d.get("solarbank_info") or {}).get("solarbank_list") or []),
        check_invalid=True,
    ),
    AnkerSolixSensorDescription(
        # Summary of all solarbank input power on site
        key="solarbank_input_power",
        translation_key="solarbank_input_power",
        json_key="total_photovoltaic_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d, jk, _: (d.get("solarbank_info") or {}).get(jk),
        suggested_display_precision=0,
        # exclude sensor if unused artifacts in structure
        exclude_fn=lambda s, d: not ({SolixDeviceType.SOLARBANK.value} - s)
        or not list((d.get("solarbank_info") or {}).get("solarbank_list") or []),
        check_invalid=True,
    ),
    AnkerSolixSensorDescription(
        # Summary of all solarbank output power on site
        key="solarbank_output_power",
        translation_key="solarbank_output_power",
        json_key="total_output_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d, jk, _: (d.get("solarbank_info") or {}).get(jk),
        suggested_display_precision=0,
        # exclude sensor if unused artifacts in structure
        exclude_fn=lambda s, d: not ({SolixDeviceType.SOLARBANK.value} - s)
        or not list((d.get("solarbank_info") or {}).get("solarbank_list") or []),
        check_invalid=True,
    ),
    AnkerSolixSensorDescription(
        # Summary of all solarbank state of charge on site
        key="solarbank_state_of_charge",
        translation_key="solarbank_state_of_charge",
        json_key="total_battery_power",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d, jk, _: 100 * float((d.get("solarbank_info") or {}).get(jk)),
        suggested_display_precision=0,
        # exclude sensor if unused artifacts in structure
        exclude_fn=lambda s, d: not ({SolixDeviceType.SOLARBANK.value} - s)
        or not list((d.get("solarbank_info") or {}).get("solarbank_list") or []),
        check_invalid=True,
    ),
    AnkerSolixSensorDescription(
        # timestamp of solabank data
        key="solarbank_timestamp",
        translation_key="solarbank_timestamp",
        json_key="updated_time",
        # value_fn=lambda d, jk, _: datetime.strptime((d.get("solarbank_info") or {}).get(jk), "%Y-%m-%d %H:%M:%S").astimezone().isoformat(),
        value_fn=lambda d, jk, _: (d.get("solarbank_info") or {}).get(jk),
        attrib_fn=lambda d, _: {"tz_offset_sec": d.get("energy_offset_tz") or 0},
        # exclude sensor if unused artifacts in structure
        exclude_fn=lambda s, d: not ({SolixDeviceType.SOLARBANK.value} - s)
        or not list((d.get("solarbank_info") or {}).get("solarbank_list") or []),
    ),
    AnkerSolixSensorDescription(
        # Summary of all pps charging power on site
        key="pps_battery_power_signed",
        translation_key="pps_battery_power_signed",
        json_key="total_charging_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d, jk, _: (d.get("pps_info") or {}).get(jk),
        suggested_display_precision=0,
        # exclude sensor if unused artifacts in structure
        exclude_fn=lambda s, d: not ({SolixDeviceType.PPS.value} - s)
        or not list((d.get("pps_info") or {}).get("pps_list") or []),
    ),
    AnkerSolixSensorDescription(
        # Summary of all pps output power on site
        key="pps_output_power",
        translation_key="pps_output_power",
        json_key="total_output_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d, jk, _: (d.get("pps_info") or {}).get(jk),
        suggested_display_precision=0,
        # exclude sensor if unused artifacts in structure
        exclude_fn=lambda s, d: not ({SolixDeviceType.PPS.value} - s)
        or not list((d.get("pps_info") or {}).get("pps_list") or []),
    ),
    AnkerSolixSensorDescription(
        # Summary of all pps state of charge on site
        key="pps_state_of_charge",
        translation_key="pps_state_of_charge",
        json_key="total_battery_power",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d, jk, _: 100 * float((d.get("pps_info") or {}).get(jk)),
        suggested_display_precision=0,
        # exclude sensor if unused artifacts in structure
        exclude_fn=lambda s, d: not ({SolixDeviceType.PPS.value} - s)
        or not list((d.get("pps_info") or {}).get("pps_list") or []),
    ),
    AnkerSolixSensorDescription(
        # Summary of all smartplug output power on site
        key="smart_plugs_power",
        translation_key="smart_plugs_power",
        json_key="total_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d, jk, _: (d.get("smart_plug_info") or {}).get(jk),
        suggested_display_precision=0,
        # exclude sensor if unused artifacts in structure
        exclude_fn=lambda s, d: not ({SolixDeviceType.SMARTPLUG.value} - s),
    ),
    AnkerSolixSensorDescription(
        # Other smart plug load given by blend plan
        key="other_loads_power",
        translation_key="other_loads_power",
        json_key="other_loads_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        # exclude sensor of main site structure when no smart plugs installed since this should only be used for blend plan in smart plug mode
        exclude_fn=lambda s, d: not ({SolixDeviceType.SMARTPLUG.value} - s)
        or not list((d.get("smart_plug_info") or {}).get("smartplug_list") or []),
    ),
    AnkerSolixSensorDescription(
        # house demand as calculated by cloud
        key="home_load_power",
        translation_key="home_load_power",
        json_key="home_load_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda d, jk, _: d.get(jk) or None
        if (
            ((d.get("grid_info") or {}).get("grid_list") or [])
            or ((d.get("smart_plug_info") or {}).get("smartplug_list") or [])
        )
        else None,
    ),
    AnkerSolixSensorDescription(
        # third party PV as calculated by cloud
        key="other_solar_power",
        translation_key="other_solar_power",
        json_key="third_party_pv",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        # use different MQTT value name if overlay
        value_fn=lambda d, jk, _: None
        if not (d.get("feature_switch") or {}).get("show_third_party_pv_panel")
        else (
            (
                (d.get("pv_power_3rd_party") or d.get(jk))
                if d.get(MQTT_OVERLAY)
                else (d.get(jk) or d.get("pv_power_3rd_party"))
            )
            or None
        ),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="total_co2_saving",
        translation_key="total_co2_saving",
        json_key="total",
        unit_fn=lambda d, _: (
            [
                stat.get("unit")
                for stat in filter(
                    lambda item: item.get("type") == "2",
                    d.get("statistics") or [{}],
                )
            ]
            or [None]
        )[0],
        attrib_fn=lambda d, _: {
            "rank": rank.get("ranking"),
            "trees": rank.get("tree"),
            "message": rank.get("content"),
        }
        if (rank := (d.get("site_details") or {}).get("co2_ranking") or {})
        else None,
        # device_class=SensorDeviceClass.WEIGHT,
        state_class=SensorStateClass.MEASUREMENT,
        force_creation_fn=lambda d: True,
        value_fn=lambda d, jk, _: (
            (
                [
                    stat.get(jk)
                    for stat in filter(
                        lambda item: item.get("type") == "2",
                        d.get("statistics") or [{}],
                    )
                ]
                or [None]
            )[0]
        ),
    ),
    AnkerSolixSensorDescription(
        key="total_saved_money",
        translation_key="total_saved_money",
        json_key="total",
        unit_fn=lambda d, _: (
            [
                stat.get("unit")
                for stat in filter(
                    lambda item: item.get("type") == "3",
                    d.get("statistics") or [{}],
                )
            ]
            or [None]
        )[0],
        # device_class=SensorDeviceClass.MONETARY,   # remove MONETARY device class as fix for issue #35
        suggested_display_precision=2,
        force_creation_fn=lambda d: True,
        value_fn=lambda d, jk, _: (
            (
                [
                    stat.get(jk)
                    for stat in filter(
                        lambda item: item.get("type") == "3",
                        d.get("statistics") or [{}],
                    )
                ]
                or [None]
            )[0]
        ),
    ),
    AnkerSolixSensorDescription(
        # Systemenergy
        key="total_output_energy",
        translation_key="total_output_energy",
        json_key="total",
        state_class=SensorStateClass.TOTAL_INCREASING,
        unit_fn=lambda d, _: str(
            (
                [
                    stat.get("unit")
                    for stat in filter(
                        lambda item: item.get("type") == "1",
                        d.get("statistics") or [{}],
                    )
                ]
                or [None]
            )[0]
        )
        .upper()
        .replace("K", "k")
        .replace("H", "h"),
        device_class=SensorDeviceClass.ENERGY,
        force_creation_fn=lambda d: True,
        feature=AnkerSolixEntityFeature.SYSTEM_INFO,
        value_fn=lambda d, jk, _: (
            (
                [
                    stat.get(jk)
                    for stat in filter(
                        lambda item: item.get("type") == "1",
                        d.get("statistics") or [{}],
                    )
                ]
                or [None]
            )[0]
        ),
    ),
    AnkerSolixSensorDescription(
        key="total_aiems_profit",
        translation_key="total_aiems_profit",
        json_key="aiems_profit_total",
        unit_fn=lambda d, _: (d.get("aiems_profit") or {}).get("unit"),
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: (d.get("aiems_profit") or {}).get(jk) or None,
        attrib_fn=lambda d, _: {
            "advantage": (d.get("aiems_profit") or {}).get("aiems_self_use_diff"),
            "percentage": (d.get("aiems_profit") or {}).get("percentage"),
        },
        exclude_fn=lambda s, d: not ({ApiCategories.site_price} - s),
    ),
    AnkerSolixSensorDescription(
        key="aiems_runtime_status",
        translation_key="aiems_runtime_status",
        json_key="status_desc",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        options=[status.name for status in SolarbankAiemsRuntimeStatus],
        value_fn=lambda d, jk, _: (
            (d.get("site_details") or {}).get("ai_ems_runtime") or {}
        ).get(jk)
        or None,
        attrib_fn=lambda d, _: {
            "status": (
                col := (d.get("site_details") or {}).get("ai_ems_runtime") or {}
            ).get("status"),
            # seconds are negative once training completed, format duration as positive string and add negative only for training phase
            "runtime": (
                ("-" if int(sec) > 0 else "") + str(timedelta(seconds=abs(int(sec))))
            )
            if str(sec := col.get("left_time"))
            .replace("-", "")
            .replace(".", "")
            .isdigit()
            else None,
        },
    ),
    AnkerSolixSensorDescription(
        key="dynamic_price_total",
        translation_key="dynamic_price_total",
        json_key="dynamic_price_total",
        unit_fn=lambda d, _: (
            (d.get("site_details") or {}).get("dynamic_price_details") or {}
        ).get("spot_price_unit"),
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: (
            (d.get("site_details") or {}).get("dynamic_price_details") or {}
        ).get(jk)
        or None,
        attrib_fn=lambda d, _: {
            "price_calc": (
                dp := (d.get("site_details") or {}).get("dynamic_price_details") or {}
            ).get("dynamic_price_calc_time"),
            "price_time": dp.get("spot_price_time"),
            "forecast": list(dp.get("dynamic_price_forecast") or []),
        },
        exclude_fn=lambda s, d: not ({ApiCategories.site_price} - s),
        force_creation_fn=lambda d: bool(
            "dynamic_price_details" in (d.get("site_details") or {})
        ),
    ),
    AnkerSolixSensorDescription(
        key="spot_price_mwh",
        translation_key="spot_price_mwh",
        json_key="spot_price_mwh",
        unit_fn=lambda d, _: str(
            ((d.get("site_details") or {}).get("dynamic_price_details") or {}).get(
                "spot_price_unit"
            )
            or ""
        )
        + "/"
        + UnitOfEnergy.MEGA_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: (
            (d.get("site_details") or {}).get("dynamic_price_details") or {}
        ).get(jk)
        or None,
        attrib_fn=lambda d, _: {
            "provider": (
                dp := (d.get("site_details") or {}).get("dynamic_price_details") or {}
            ).get("dynamic_price_provider"),
            "poll_time": dp.get("dynamic_price_poll_time"),
            "avg_today": dp.get("spot_price_mwh_avg_today"),
            "avg_tomorrow": dp.get("spot_price_mwh_avg_tomorrow"),
        },
        exclude_fn=lambda s, d: not ({ApiCategories.site_price} - s),
        force_creation_fn=lambda d: bool(
            "dynamic_price_details" in (d.get("site_details") or {})
        ),
    ),
    AnkerSolixSensorDescription(
        key="solar_forecast_today",
        translation_key="solar_forecast_today",
        json_key="forecast_today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: (
            (d.get("energy_details") or {}).get("pv_forecast_details") or {}
        ).get(jk)
        or None,
        attrib_fn=lambda d, _: {
            "remain_today": (
                fc := (d.get("energy_details") or {}).get("pv_forecast_details") or {}
            ).get("remaining_today"),
            "forecast_24h": fc.get("forecast_24h"),
            "poll_time": fc.get("poll_time"),
            "hourly_unit": fc.get("trend_unit"),
            "forecast_hourly": list(fc.get("trend") or []),
        },
        exclude_fn=lambda s, d: not ({ApiCategories.site_price} - s),
        force_creation_fn=lambda d: bool(
            "pv_forecast_details" in (d.get("energy_details") or {})
        ),
        restore=True,
    ),
    AnkerSolixSensorDescription(
        key="solar_forecast_this_hour",
        translation_key="solar_forecast_this_hour",
        json_key="trend_this_hour",
        unit_fn=lambda d, _: (
            (d.get("energy_details") or {}).get("pv_forecast_details") or {}
        ).get("trend_unit"),
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: (
            (d.get("energy_details") or {}).get("pv_forecast_details") or {}
        ).get(jk)
        or None,
        attrib_fn=lambda d, _: {
            "hour_end": (
                fc := (d.get("energy_details") or {}).get("pv_forecast_details") or {}
            ).get("time_this_hour"),
            "forecast_next_hour": fc.get("trend_next_hour"),
        },
        exclude_fn=lambda s, d: not ({ApiCategories.site_price} - s),
        force_creation_fn=lambda d: bool(
            "pv_forecast_details" in (d.get("energy_details") or {})
        ),
    ),
    AnkerSolixSensorDescription(
        # System total output setting, determined by Api via schedule slot discharge switch and W preset
        # This may also present 0 W if the switch is disabled, even if the W preset value remains and the minimum bypass per defined inverter will be used
        # This is confusing in the App and the Api, since there may be the minimum bypass W even if 0 W is shown.
        # 0 W is only applied truly if the 0 W Switch is installed for non Anker inverters, or if MI80 is used which supports the 0 W setting natively
        key="set_system_output_power",
        translation_key="set_system_output_power",
        json_key="retain_load",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        # This entry has the unit with the number and needs to be removed
        value_fn=lambda d, jk, _: str(d.get(jk) or "").replace("W", "") or None,
        # Common site field, may also be used by other devices beside solarbank
        # exclude_fn=lambda s, _: not ({SolixDeviceType.SOLARBANK.value} - s),
    ),
    AnkerSolixSensorDescription(
        key="active_scene_mode",
        translation_key="active_scene_mode",
        json_key="scene_mode",
        device_class=SensorDeviceClass.ENUM,
        options=list({m.name for m in SolarbankUsageMode}),
        # Use new field for scene mode optionally, which reports scene also for member accounts
        value_fn=lambda d, jk, _: None
        if not ((mode := d.get(jk) or d.get("user_scene_mode")) and str(mode).isdigit())
        else get_enum_name(SolarbankUsageMode, mode, SolarbankUsageMode.unknown.name),
        attrib_fn=lambda d, _: {
            "mode_type": d.get("scene_mode") or d.get("user_scene_mode"),
        },
    ),
    AnkerSolixSensorDescription(
        key="daily_discharge_energy",
        translation_key="daily_discharge_energy",
        json_key="battery_discharge",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        # ensure backward compatibility to old key in json files
        value_fn=lambda d, jk, _: None
        if not (items := (d.get("energy_details") or {}).get("today") or {})
        else items.get(jk) or items.get("solarbank_discharge"),
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": (
                items := ((d.get("energy_details") or {}).get("last_period") or {})
            ).get("battery_discharge")
            or items.get("solarbank_discharge"),
        },
        exclude_fn=lambda s, _: not (
            {
                SolixDeviceType.SOLARBANK.value,
                SolixDeviceType.POWERPANEL.value,
                SolixDeviceType.HES.value,
            }
            - s
            and {
                ApiCategories.solarbank_energy,
                ApiCategories.powerpanel_energy,
                ApiCategories.hes_energy,
            }
            - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="daily_charge_energy",
        translation_key="daily_charge_energy",
        json_key="battery_charge",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        # ensure backward compatibility to old key in json files
        value_fn=lambda d, jk, _: None
        if not (items := (d.get("energy_details") or {}).get("today") or {})
        else items.get(jk) or items.get("solarbank_charge"),
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": (
                items := ((d.get("energy_details") or {}).get("last_period") or {})
            ).get("battery_charge")
            or items.get("solarbank_charge"),
        },
        exclude_fn=lambda s, _: not (
            {
                SolixDeviceType.SOLARBANK.value,
                SolixDeviceType.POWERPANEL.value,
                SolixDeviceType.HES.value,
            }
            - s
            and {
                ApiCategories.solarbank_energy,
                ApiCategories.powerpanel_energy,
                ApiCategories.hes_energy,
            }
            - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="daily_solar_production",
        translation_key="daily_solar_production",
        json_key="solar_production",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: None
        if not (items := (d.get("energy_details") or {}).get("today") or {})
        else items.get(jk),
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": (
                (d.get("energy_details") or {}).get("last_period") or {}
            ).get("solar_production"),
        }
        # Add hourly production data if solar forecast possible for system
        | (
            {
                "hourly_unit": (
                    fc := (d.get("energy_details") or {}).get("pv_forecast_details")
                    or {}
                ).get("trend_unit"),
                "produced_hourly": fc.get("produced_hourly"),
            }
            if "pv_forecast_details" in (d.get("energy_details") or {})
            else {}
        ),
        exclude_fn=lambda s, _: not (
            {
                SolixDeviceType.INVERTER.value,
                SolixDeviceType.SOLARBANK.value,
                SolixDeviceType.POWERPANEL.value,
                SolixDeviceType.HES.value,
            }
            - s
            and {
                ApiCategories.solarbank_energy,
                ApiCategories.powerpanel_energy,
                ApiCategories.hes_energy,
            }
            - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="daily_solar_production_pv1",
        translation_key="daily_solar_production_pv1",
        json_key="solar_production_pv1",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: None
        if not (items := (d.get("energy_details") or {}).get("today") or {})
        else items.get(jk),
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": (
                (d.get("energy_details") or {}).get("last_period") or {}
            ).get("solar_production_pv1"),
        },
        exclude_fn=lambda s, _: not (
            {SolixDeviceType.SOLARBANK.value} - s
            and {ApiCategories.solarbank_energy} - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="daily_solar_production_pv2",
        translation_key="daily_solar_production_pv2",
        json_key="solar_production_pv2",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: None
        if not (items := (d.get("energy_details") or {}).get("today") or {})
        else items.get(jk),
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": (
                (d.get("energy_details") or {}).get("last_period") or {}
            ).get("solar_production_pv2"),
        },
        exclude_fn=lambda s, _: not (
            {SolixDeviceType.SOLARBANK.value} - s
            and {ApiCategories.solarbank_energy} - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="daily_solar_production_pv3",
        translation_key="daily_solar_production_pv3",
        json_key="solar_production_pv3",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: None
        if not (items := (d.get("energy_details") or {}).get("today") or {})
        else items.get(jk),
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": (
                (d.get("energy_details") or {}).get("last_period") or {}
            ).get("solar_production_pv3"),
        },
        exclude_fn=lambda s, _: not (
            {SolixDeviceType.SOLARBANK.value} - s
            and {ApiCategories.solarbank_energy} - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="daily_solar_production_pv4",
        translation_key="daily_solar_production_pv4",
        json_key="solar_production_pv4",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: None
        if not (items := (d.get("energy_details") or {}).get("today") or {})
        else items.get(jk),
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": (
                (d.get("energy_details") or {}).get("last_period") or {}
            ).get("solar_production_pv4"),
        },
        exclude_fn=lambda s, _: not (
            {SolixDeviceType.SOLARBANK.value} - s
            and {ApiCategories.solarbank_energy} - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="daily_solar_production_inverter",
        translation_key="daily_solar_production_inverter",
        json_key="solar_production_microinverter",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: None
        if not (items := (d.get("energy_details") or {}).get("today") or {})
        else items.get(jk),
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": (
                (d.get("energy_details") or {}).get("last_period") or {}
            ).get("solar_production_microinverter"),
        },
        exclude_fn=lambda s, _: not (
            {SolixDeviceType.SOLARBANK.value} - s
            and {ApiCategories.solarbank_energy} - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="daily_solar_to_home",
        translation_key="daily_solar_to_home",
        json_key="solar_to_home",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: None
        if not (items := (d.get("energy_details") or {}).get("today") or {})
        else items.get(jk),
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": (
                (d.get("energy_details") or {}).get("last_period") or {}
            ).get("solar_to_home"),
        },
        exclude_fn=lambda s, _: not (
            {
                SolixDeviceType.SOLARBANK.value,
                SolixDeviceType.POWERPANEL.value,
                SolixDeviceType.HES.value,
            }
            - s
            and {
                ApiCategories.solarbank_energy,
                ApiCategories.powerpanel_energy,
                ApiCategories.hes_energy,
            }
            - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="daily_solar_to_battery",
        translation_key="daily_solar_to_battery",
        json_key="solar_to_battery",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: None
        if not (items := (d.get("energy_details") or {}).get("today") or {})
        else items.get(jk),
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": (
                (d.get("energy_details") or {}).get("last_period") or {}
            ).get("solar_to_battery"),
        },
        exclude_fn=lambda s, _: not (
            {
                SolixDeviceType.SOLARBANK.value,
                SolixDeviceType.POWERPANEL.value,
                SolixDeviceType.HES.value,
            }
            - s
            and {
                ApiCategories.solarbank_energy,
                ApiCategories.powerpanel_energy,
                ApiCategories.hes_energy,
            }
            - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="daily_3rd_party_pv_to_bat",
        translation_key="daily_3rd_party_pv_to_bat",
        json_key="3rd_party_pv_to_bat",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: None
        if not (items := (d.get("energy_details") or {}).get("today") or {})
        else items.get(jk),
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": (
                (d.get("energy_details") or {}).get("last_period") or {}
            ).get("3rd_party_pv_to_bat"),
        },
        exclude_fn=lambda s, _: not (
            {SolixDeviceType.SOLARBANK.value, SolixDeviceType.SMARTMETER.value} - s
            and {ApiCategories.solarbank_energy} - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="daily_3rd_party_pv_to_grid",
        translation_key="daily_3rd_party_pv_to_grid",
        json_key="3rd_party_pv_to_grid",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: None
        if not (items := (d.get("energy_details") or {}).get("today") or {})
        else items.get(jk),
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": (
                (d.get("energy_details") or {}).get("last_period") or {}
            ).get("3rd_party_pv_to_grid"),
        },
        exclude_fn=lambda s, _: not (
            {SolixDeviceType.SOLARBANK.value, SolixDeviceType.SMARTMETER.value} - s
            and {ApiCategories.solarbank_energy} - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="daily_ac_socket",
        translation_key="daily_ac_socket",
        json_key="ac_socket",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: None
        if not (items := (d.get("energy_details") or {}).get("today") or {})
        else items.get(jk),
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": (
                (d.get("energy_details") or {}).get("last_period") or {}
            ).get("ac_socket"),
        },
        exclude_fn=lambda s, _: not (
            {SolixDeviceType.SOLARBANK.value} - s
            and {ApiCategories.solarbank_energy} - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="daily_home_usage",
        translation_key="daily_home_usage",
        json_key="home_usage",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: None
        if not (items := (d.get("energy_details") or {}).get("today") or {})
        else items.get(jk),
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": (
                (d.get("energy_details") or {}).get("last_period") or {}
            ).get("home_usage"),
        },
        exclude_fn=lambda s, _: not (
            {
                SolixDeviceType.SOLARBANK.value,
                SolixDeviceType.SMARTMETER.value,
                SolixDeviceType.SMARTPLUG.value,
                SolixDeviceType.POWERPANEL.value,
                SolixDeviceType.HES.value,
            }
            - s
            and {
                ApiCategories.solarbank_energy,
                ApiCategories.smartmeter_energy,
                ApiCategories.smartplug_energy,
                ApiCategories.powerpanel_energy,
                ApiCategories.hes_energy,
            }
            - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="daily_battery_to_home",
        translation_key="daily_battery_to_home",
        json_key="battery_to_home",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: None
        if not (items := (d.get("energy_details") or {}).get("today") or {})
        else items.get(jk),
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": (
                (d.get("energy_details") or {}).get("last_period") or {}
            ).get("battery_to_home"),
        },
        exclude_fn=lambda s, _: not (
            {
                SolixDeviceType.SOLARBANK.value,
                SolixDeviceType.POWERPANEL.value,
                SolixDeviceType.HES.value,
            }
            - s
            and {
                ApiCategories.solarbank_energy,
                ApiCategories.powerpanel_energy,
                ApiCategories.hes_energy,
            }
            - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="daily_smartplugs_total",
        translation_key="daily_smartplugs_total",
        json_key="smartplugs_total",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: None
        if not (items := (d.get("energy_details") or {}).get("today") or {})
        else items.get(jk),
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": (
                (d.get("energy_details") or {}).get("last_period") or {}
            ).get("smartplugs_total"),
        },
        exclude_fn=lambda s, _: not (
            {SolixDeviceType.SMARTPLUG.value} - s
            and {ApiCategories.smartplug_energy} - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="daily_grid_import",
        translation_key="daily_grid_import",
        json_key="grid_import",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: None
        if not (items := (d.get("energy_details") or {}).get("today") or {})
        else items.get(jk),
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": (
                (d.get("energy_details") or {}).get("last_period") or {}
            ).get("grid_import"),
        },
        exclude_fn=lambda s, _: not (
            {
                SolixDeviceType.SMARTMETER.value,
                SolixDeviceType.POWERPANEL.value,
                SolixDeviceType.HES.value,
            }
            - s
            and {
                ApiCategories.smartmeter_energy,
                ApiCategories.powerpanel_energy,
                ApiCategories.hes_energy,
            }
            - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="daily_grid_to_home",
        translation_key="daily_grid_to_home",
        json_key="grid_to_home",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: None
        if not (items := (d.get("energy_details") or {}).get("today") or {})
        else items.get(jk),
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": (
                (d.get("energy_details") or {}).get("last_period") or {}
            ).get("grid_to_home"),
        },
        exclude_fn=lambda s, _: not (
            {
                SolixDeviceType.SOLARBANK.value,
                SolixDeviceType.POWERPANEL.value,
                SolixDeviceType.HES.value,
            }
            - s
            and {
                ApiCategories.solarbank_energy,
                ApiCategories.powerpanel_energy,
                ApiCategories.hes_energy,
            }
            - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="daily_grid_to_battery",
        translation_key="daily_grid_to_battery",
        json_key="grid_to_battery",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: None
        if not (items := (d.get("energy_details") or {}).get("today") or {})
        else items.get(jk),
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": (
                (d.get("energy_details") or {}).get("last_period") or {}
            ).get("grid_to_battery"),
        },
        exclude_fn=lambda s, _: not (
            {
                SolixDeviceType.SOLARBANK.value,
                SolixDeviceType.POWERPANEL.value,
                SolixDeviceType.HES.value,
            }
            - s
            and {
                ApiCategories.solarbank_energy,
                ApiCategories.powerpanel_energy,
                ApiCategories.hes_energy,
            }
            - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="daily_solar_to_grid",
        translation_key="daily_solar_to_grid",
        json_key="solar_to_grid",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: None
        if not (items := (d.get("energy_details") or {}).get("today") or {})
        else items.get(jk),
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": (
                (d.get("energy_details") or {}).get("last_period") or {}
            ).get("solar_to_grid"),
        },
        exclude_fn=lambda s, _: not (
            {
                SolixDeviceType.SOLARBANK.value,
                SolixDeviceType.POWERPANEL.value,
                SolixDeviceType.HES.value,
            }
            - s
            and {
                ApiCategories.solarbank_energy,
                ApiCategories.powerpanel_energy,
                ApiCategories.hes_energy,
            }
            - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="daily_solar_share",
        translation_key="daily_solar_share",
        json_key="solar_percentage",
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
        value_fn=lambda d, jk, _: None
        if not (items := (d.get("energy_details") or {}).get("today") or {})
        else 100 * float(items.get(jk))
        if str(items.get(jk)).replace(".", "", 1).isdigit()
        else None,
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": None
            if not (items := (d.get("energy_details") or {}).get("last_period") or {})
            else 100 * float(items.get("solar_percentage"))
            if str(items.get("solar_percentage")).replace(".", "", 1).isdigit()
            else None,
        },
        exclude_fn=lambda s, _: not (
            {
                SolixDeviceType.SOLARBANK.value,
                SolixDeviceType.POWERPANEL.value,
                SolixDeviceType.HES.value,
            }
            - s
            and {
                ApiCategories.solarbank_energy,
                ApiCategories.powerpanel_energy,
                ApiCategories.hes_energy,
            }
            - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="daily_battery_share",
        translation_key="daily_battery_share",
        json_key="battery_percentage",
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
        value_fn=lambda d, jk, _: None
        if not (items := (d.get("energy_details") or {}).get("today") or {})
        else 100 * float(items.get(jk))
        if str(items.get(jk)).replace(".", "", 1).isdigit()
        else None,
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": None
            if not (items := (d.get("energy_details") or {}).get("last_period") or {})
            else 100 * float(items.get("battery_percentage"))
            if str(items.get("battery_percentage")).replace(".", "", 1).isdigit()
            else None,
        },
        exclude_fn=lambda s, _: not (
            {
                SolixDeviceType.SOLARBANK.value,
                SolixDeviceType.POWERPANEL.value,
                SolixDeviceType.HES.value,
            }
            - s
            and {
                ApiCategories.solarbank_energy,
                ApiCategories.powerpanel_energy,
                ApiCategories.hes_energy,
            }
            - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="daily_grid_share",
        translation_key="daily_grid_share",
        json_key="other_percentage",
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
        value_fn=lambda d, jk, _: None
        if not (items := (d.get("energy_details") or {}).get("today") or {})
        else 100 * float(items.get(jk))
        if str(items.get(jk)).replace(".", "", 1).isdigit()
        else None,
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": None
            if not (items := (d.get("energy_details") or {}).get("last_period") or {})
            else 100 * float(items.get("other_percentage"))
            if str(items.get("other_percentage")).replace(".", "", 1).isdigit()
            else None,
        },
        exclude_fn=lambda s, _: not (
            {
                SolixDeviceType.SOLARBANK.value,
                SolixDeviceType.POWERPANEL.value,
                SolixDeviceType.HES.value,
            }
            - s
            and {
                ApiCategories.solarbank_energy,
                ApiCategories.powerpanel_energy,
                ApiCategories.hes_energy,
            }
            - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="grid_import_energy",
        translation_key="grid_import_energy",
        json_key="grid_import_energy",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=3,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        key="grid_export_energy",
        translation_key="grid_export_energy",
        json_key="grid_export_energy",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=3,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
    ),
    AnkerSolixSensorDescription(
        # HES battery count
        key="battery_count",
        translation_key="battery_count",
        json_key="batCount",
        picture_path=AnkerSolixPicturePath.A5220,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d, jk, _: (d.get("hes_info") or {}).get(jk),
        exclude_fn=lambda s, d: not ({d.get("site_type")} - s),
    ),
    AnkerSolixSensorDescription(
        # HES parallel devices
        key="parallel_device_count",
        translation_key="parallel_device_count",
        json_key="numberOfParallelDevice",
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d, jk, _: (d.get("hes_info") or {}).get(jk),
        exclude_fn=lambda s, d: not ({d.get("site_type")} - s),
    ),
]

ACCOUNT_SENSORS = [
    AnkerSolixSensorDescription(
        key="sites_poll_time",
        translation_key="sites_poll_time",
        json_key="sites_poll_time",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        attrib_fn=lambda d, _: {
            "runtime_seconds": d.get("sites_poll_seconds"),
        },
    ),
    AnkerSolixSensorDescription(
        key="details_poll_time",
        translation_key="details_poll_time",
        json_key="details_poll_time",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        attrib_fn=lambda d, _: {
            "runtime_seconds": d.get("details_poll_seconds"),
        },
    ),
    AnkerSolixSensorDescription(
        key="energy_poll_time",
        translation_key="energy_poll_time",
        json_key="energy_poll_time",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        attrib_fn=lambda d, _: {
            "runtime_seconds": d.get("energy_poll_seconds"),
        },
    ),
    AnkerSolixSensorDescription(
        # MQTT statistics
        key="mqtt_statistic",
        translation_key="mqtt_statistic",
        json_key="mqtt_statistic",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d, jk, _: (d.get(jk) or {}).get("kb_hourly_received"),
        native_unit_of_measurement="kB/h",
        suggested_display_precision=3,
        attrib_fn=lambda d, _: {
            "start_time": (d.get("mqtt_statistic") or {}).get("start_time"),
            "bytes_received": (d.get("mqtt_statistic") or {}).get("bytes_received"),
            "bytes_sent": (d.get("mqtt_statistic") or {}).get("bytes_sent"),
            "messages": (d.get("mqtt_statistic") or {}).get("dev_messages"),
        },
        mqtt=True,
    ),
]

VEHICLE_SENSORS = [
    AnkerSolixSensorDescription(
        key="update_timestamp",
        translation_key="update_timestamp",
        json_key="update_time",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d, jk, _: datetime.fromtimestamp(int(d.get(jk)))
        if str(d.get(jk)).isdigit()
        else None,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor platform."""

    coordinator: AnkerSolixDataUpdateCoordinator = hass.data[DOMAIN].get(entry.entry_id)
    entities = []

    if coordinator and hasattr(coordinator, "data") and coordinator.data:
        # create entity based on type of entry in coordinator data, which consolidates the api.sites, api.devices and api.account dictionaries
        # the coordinator.data dict key is either account nickname, a site_id or device_sn and used as context for the entity to lookup its data
        for context, data in coordinator.data.items():
            mdev = None
            mdata = {}
            if (data_type := data.get("type")) == SolixDeviceType.SYSTEM.value:
                # Unique key for site_id entry in data
                entity_type = AnkerSolixEntityType.SITE
                entity_list = SITE_SENSORS
            elif data_type == SolixDeviceType.ACCOUNT.value:
                # Unique key for account entry in data
                entity_type = AnkerSolixEntityType.ACCOUNT
                entity_list = ACCOUNT_SENSORS
            elif data_type == SolixDeviceType.VEHICLE.value:
                # vehicle entry in data
                entity_type = AnkerSolixEntityType.VEHICLE
                entity_list = VEHICLE_SENSORS
            else:
                # device_sn entry in data
                entity_type = AnkerSolixEntityType.DEVICE
                entity_list = DEVICE_SENSORS
                # get MQTT device combined values for creation of entities
                if mdev := coordinator.client.get_mqtt_device(sn=context):
                    mdata = mdev.get_combined_cache(
                        fromFile=coordinator.client.testmode()
                    )

            for description in entity_list:
                if description.nested_sensor:
                    # concatenate device serial and subdevice serial to context
                    sn_list = [
                        context + "_" + serial
                        for serial in (data.get(description.json_key) or {})
                    ]
                else:
                    sn_list = [context]
                # create list of sensors to create based on data and config options
                for sn in (
                    serial
                    for serial in sn_list
                    if bool(CREATE_ALL_ENTITIES)
                    or (
                        not description.exclude_fn(
                            set(entry.options.get(CONF_EXCLUDE, [])), data
                        )
                        and (
                            description.force_creation_fn(data)
                            # filter MQTT entities and provide combined or only api cache
                            # Entities that should not be created without MQTT data need to use exclude option
                            or (
                                description.mqtt
                                and description.value_fn(
                                    mdata or data, description.json_key, serial
                                )
                                is not None
                            )
                            # filter API only entities
                            or (
                                not description.mqtt
                                and description.value_fn(
                                    data, description.json_key, serial
                                )
                                is not None
                            )
                        )
                    )
                ):
                    if description.restore:
                        entity = AnkerSolixRestoreSensor(
                            coordinator, description, context, entity_type
                        )
                    else:
                        entity = AnkerSolixSensor(
                            coordinator, description, sn, entity_type
                        )
                    entities.append(entity)

    # create the entities from the list
    async_add_entities(entities)

    # register the entity services
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        name=SERVICE_GET_SYSTEM_INFO,
        schema=SOLIX_ENTITY_SCHEMA,
        func=SERVICE_GET_SYSTEM_INFO,
        required_features=[AnkerSolixEntityFeature.SYSTEM_INFO],
        supports_response=SupportsResponse.ONLY,
    )
    platform.async_register_entity_service(
        name=SERVICE_GET_SOLARBANK_SCHEDULE,
        schema=SOLIX_ENTITY_SCHEMA,
        func=SERVICE_GET_SOLARBANK_SCHEDULE,
        required_features=[AnkerSolixEntityFeature.SOLARBANK_SCHEDULE],
        supports_response=SupportsResponse.ONLY,
    )
    platform.async_register_entity_service(
        name=SERVICE_CLEAR_SOLARBANK_SCHEDULE,
        schema=SOLIX_WEEKDAY_SCHEMA,
        func=SERVICE_CLEAR_SOLARBANK_SCHEDULE,
        required_features=[AnkerSolixEntityFeature.SOLARBANK_SCHEDULE],
    )
    platform.async_register_entity_service(
        name=SERVICE_SET_SOLARBANK_SCHEDULE,
        schema=SOLARBANK_TIMESLOT_SCHEMA,
        func=SERVICE_SET_SOLARBANK_SCHEDULE,
        required_features=[AnkerSolixEntityFeature.SOLARBANK_SCHEDULE],
    )
    platform.async_register_entity_service(
        name=SERVICE_UPDATE_SOLARBANK_SCHEDULE,
        schema=SOLARBANK_TIMESLOT_SCHEMA,
        func=SERVICE_UPDATE_SOLARBANK_SCHEDULE,
        required_features=[AnkerSolixEntityFeature.SOLARBANK_SCHEDULE],
    )


class AnkerSolixSensor(CoordinatorEntity, SensorEntity):
    """Represents a sensor entity for Anker device and site data."""

    coordinator: AnkerSolixDataUpdateCoordinator
    entity_description: AnkerSolixSensorDescription
    entity_type: str
    _attr_has_entity_name = True
    _context_base: str = None
    _context_nested: str = None
    _last_schedule_service_value: str = None
    _unrecorded_attributes = frozenset(
        {
            "advantage",
            "avg_today",
            "avg_tomorrow",
            "device_sn",
            "fittings",
            "forecast_24h",
            "forecast_hourly",
            "forecast_next_hour",
            "hour_end",
            "hourly_unit",
            "inverter_info",
            "message",
            "name",
            "network",
            "network_code",
            "percentage",
            "provider",
            "poll_time",
            "price_calc",
            "price_time",
            "produced_hourly",
            "rank",
            "remain_today",
            "role_status",
            "runtime",
            "schedule",
            "station_id",
            "station_type",
            "status",
            "solar_brand",
            "solar_model",
            "solar_sn",
            "sw_version",
            "trees",
            "tz_offset_sec",
            "bytes_received",
            "bytes_sent",
            "messages",
            "voltage",
            "state_of_health",
        }
    )

    def __init__(
        self,
        coordinator: AnkerSolixDataUpdateCoordinator,
        description: AnkerSolixSensorDescription,
        context: str,
        entity_type: str,
    ) -> None:
        """Initialize an Anker Solix Device coordinator entity.

        The CoordinatorEntity class provides:
        should_poll
        async_update
        async_added_to_hass
        available
        """
        super().__init__(coordinator, context)

        self.entity_description = description
        self.entity_type = entity_type
        self._attribute_name = description.key
        self._attr_attribution = f"{ATTRIBUTION}{' + MQTT' if description.mqtt else ''}"
        self._attr_unique_id = (f"{context}_{description.key}").lower()
        wwwroot = str(Path(self.coordinator.hass.config.config_dir) / "www")
        if (
            description.picture_path
            and Path(
                description.picture_path.replace(
                    AnkerSolixPicturePath.LOCALPATH, wwwroot
                )
            ).is_file()
        ):
            self._attr_entity_picture = description.picture_path
        self._attr_extra_state_attributes = None
        # Split context for nested device serials
        self._context_base = context.split("_")[0]
        if len(context.split("_")) > 1:
            self._context_nested = context.split("_")[1]

        if self.entity_type == AnkerSolixEntityType.DEVICE:
            # get the device data from device context entry of coordinator data
            data = coordinator.data.get(self._context_base) or {}
            if data.get("is_subdevice"):
                self._attr_device_info = get_AnkerSolixSubdeviceInfo(
                    data, self._context_base, data.get("main_sn")
                )
            else:
                self._attr_device_info = get_AnkerSolixDeviceInfo(
                    data, self._context_base, coordinator.client.api.apisession.email
                )
            # add service attribute for managble devices
            self._attr_supported_features: AnkerSolixEntityFeature = (
                description.feature if data.get("is_admin", False) else None
            )
            if self._attribute_name == "fittings":
                # set the correct fitting type picture for the entity
                if (
                    pn := (
                        (data.get("fittings") or {}).get(context.split("_")[1]) or {}
                    ).get("product_code")
                ) and hasattr(AnkerSolixPicturePath, pn):
                    self._attr_entity_picture = getattr(AnkerSolixPicturePath, pn)
            # disable picture again if path does not exist to allow display of icons alternatively
            if (
                self._attr_entity_picture
                and not Path(
                    self._attr_entity_picture.replace(
                        AnkerSolixPicturePath.LOCALPATH, wwwroot
                    )
                ).is_file()
            ):
                self._attr_entity_picture = None
        elif self.entity_type == AnkerSolixEntityType.ACCOUNT:
            # get the account data from account context entry of coordinator data
            # use full context since email may contain underscores
            data = coordinator.data.get(context) or {}
            self._attr_device_info = get_AnkerSolixAccountInfo(data, context)
            # add service attribute for account entities
            self._attr_supported_features: AnkerSolixEntityFeature = description.feature
        elif self.entity_type == AnkerSolixEntityType.VEHICLE:
            # get the vehicle info data from vehicle entry of coordinator data
            data = coordinator.data.get(self._context_base) or {}
            self._attr_device_info = get_AnkerSolixVehicleInfo(
                data, self._context_base, coordinator.client.api.apisession.email
            )
        else:
            # get the site info data from site context entry of coordinator data
            data = (coordinator.data.get(self._context_base) or {}).get(
                "site_info"
            ) or {}
            self._attr_device_info = get_AnkerSolixSystemInfo(
                data, self._context_base, coordinator.client.api.apisession.email
            )
            # add service attribute for site entities
            self._attr_supported_features: AnkerSolixEntityFeature = description.feature

        self._native_value = None
        self._assumed_state = False
        self.update_state_value()
        self._last_known_value = self._native_value

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.update_state_value()
        super()._handle_coordinator_update()

    @property
    def native_value(self):
        """Return the native value of the sensor."""
        return self._native_value

    @property
    def assumed_state(self):
        """Return the assumed state of the sensor."""
        return self._assumed_state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the sensor."""
        if (
            self.coordinator
            and (hasattr(self.coordinator, "data"))
            and self._context_base in self.coordinator.data
        ):
            # Api device data
            data = self.coordinator.data.get(self._context_base)
            if self.entity_description.mqtt and (
                mdev := self.coordinator.client.get_mqtt_device(self._context_base)
            ):
                # Combined MQTT device data, overlay prio depends on customized setting
                data = mdev.get_combined_cache(
                    api_prio=not mdev.device.get(MQTT_OVERLAY),
                    fromFile=self.coordinator.client.testmode(),
                )
            with suppress(ValueError, TypeError):
                self._attr_extra_state_attributes = self.entity_description.attrib_fn(
                    data, self.coordinator_context
                )
        return self._attr_extra_state_attributes

    @property
    def supported_features(self) -> AnkerSolixEntityFeature:
        """Flag supported features."""
        return self._attr_supported_features

    def update_state_value(self):
        """Update the state value of the sensor based on the coordinator data."""
        if self.coordinator and not (hasattr(self.coordinator, "data")):
            self._native_value = None
        elif self._context_base in self.coordinator.data:
            # Api device data
            data = self.coordinator.data.get(self._context_base)
            if self.entity_description.mqtt and (
                mdev := self.coordinator.client.get_mqtt_device(self._context_base)
            ):
                # Combined MQTT device data, overlay prio depends on customized setting
                data = mdev.get_combined_cache(
                    api_prio=not mdev.device.get(MQTT_OVERLAY),
                    fromFile=self.coordinator.client.testmode(),
                )
            key = self.entity_description.json_key
            with suppress(ValueError, TypeError):
                # check if FW changed for device and update device entry in registry
                # check only for single device sensor that should be common for each Solix device type
                if (
                    self._attribute_name == "sw_version"
                    and self.device_entry
                    and (
                        firmware := self.entity_description.value_fn(
                            data, key, self.coordinator_context
                        )
                    )
                ):
                    if firmware != self.state:
                        # get device registry and update the device entry attribute
                        dev_registry = dr.async_get(self.coordinator.hass)
                        dev_registry.async_update_device(
                            self.device_entry.id,
                            sw_version=firmware,
                        )
                    self._native_value = firmware
                else:
                    # update sensor unit if described by function
                    if unit := self.entity_description.unit_fn(
                        data, self.coordinator_context
                    ):
                        self._attr_native_unit_of_measurement = unit
                    if self.entity_description.check_invalid and not data.get(
                        "data_valid", True
                    ):
                        # skip update or mark unvailable
                        if not self.coordinator.config_entry.options.get(
                            CONF_SKIP_INVALID
                        ):
                            self._native_value = None
                    elif self.state_class == SensorStateClass.TOTAL_INCREASING:
                        # Fix #319: Skip energy rounding errors by cloud if decrease within suggested display precision
                        old = self._native_value
                        self._native_value = self.entity_description.value_fn(
                            data, key, self.coordinator_context
                        )
                        if old is not None and (
                            0
                            > (float(self._native_value) - float(old))
                            >= -1 / 10**self.suggested_display_precision
                        ):
                            self._native_value = old
                    else:
                        self._native_value = self.entity_description.value_fn(
                            data, key, self.coordinator_context
                        )
                        if (
                            self._native_value
                            and self.device_class == SensorDeviceClass.TEMPERATURE
                        ):
                            # Set unit of measurement as user option to allow automatic state conversion by HA core
                            if data.get("temp_unit_fahrenheit"):
                                self._sensor_option_unit_of_measurement = (
                                    UnitOfTemperature.FAHRENHEIT
                                )
                            else:
                                self._sensor_option_unit_of_measurement = (
                                    UnitOfTemperature.CELSIUS
                                )
                    # Ensure to set power sensors to None if empty strings returned
                    if (
                        self.device_class == SensorDeviceClass.POWER
                        and not self._native_value
                    ):
                        self._native_value = None

                # perform potential value conversions in testmode
                if (
                    self.coordinator.client.testmode()
                    and TEST_NUMBERVARIANCE
                    and self._native_value is not None
                    and float(self._native_value)
                ):
                    # When running in Test mode, simulate some variance for sensors with set device class
                    if self.device_class:
                        if self.device_class == SensorDeviceClass.ENUM:
                            self._native_value = choice(self.entity_description.options)
                        elif self.device_class == SensorDeviceClass.ENERGY and hasattr(
                            self, "_last_known_value"
                        ):
                            # only moderate increase from last knonw value to higher value for Energy to avoid meter reset alerts
                            self._native_value = round(
                                max(
                                    float(self._last_known_value),
                                    float(self._native_value),
                                )
                                * randrange(100, 102, 1)
                                / 100,
                                3,
                            )
                        else:
                            # value fluctuation in both directions for other classes
                            self._native_value = round(
                                float(self._native_value) * randrange(70, 130, 5) / 100,
                                3,
                            )
        else:
            self._native_value = None

        # Mark sensor availability based on a sensore value
        self._attr_available = self._native_value is not None

    async def get_system_info(self, **kwargs: Any) -> dict | None:
        """Get the actual system info from the api."""
        return await self._solix_system_service(
            service_name=SERVICE_GET_SYSTEM_INFO, **kwargs
        )

    async def get_solarbank_schedule(self, **kwargs: Any) -> dict | None:
        """Get the active solarbank schedule from the api."""
        return await self._solarbank_schedule_service(
            service_name=SERVICE_GET_SOLARBANK_SCHEDULE, **kwargs
        )

    async def clear_solarbank_schedule(self, **kwargs: Any) -> None:
        """Clear the active solarbank schedule."""
        await self._solarbank_schedule_service(
            service_name=SERVICE_CLEAR_SOLARBANK_SCHEDULE, **kwargs
        )

    async def set_solarbank_schedule(self, **kwargs: Any) -> None:
        """Set the defined solarbank schedule slot."""
        await self._solarbank_schedule_service(
            service_name=SERVICE_SET_SOLARBANK_SCHEDULE, **kwargs
        )

    async def update_solarbank_schedule(self, **kwargs: Any) -> None:
        """Update the defined solarbank schedule."""
        await self._solarbank_schedule_service(
            service_name=SERVICE_UPDATE_SOLARBANK_SCHEDULE, **kwargs
        )

    async def _solix_system_service(
        self, service_name: str, **kwargs: Any
    ) -> dict | None:
        """Execute the defined system action."""
        # Raise alerts to frontend
        if not (self.supported_features & AnkerSolixEntityFeature.SYSTEM_INFO):
            raise ServiceValidationError(
                f"The entity {self.entity_id} does not support the action {service_name}",
                translation_domain=DOMAIN,
                translation_key="service_not_supported",
                translation_placeholders={
                    "entity": self.entity_id,
                    "service": service_name,
                },
            )
        # When running in Test mode do not run services that are not supporting a testmode
        if self.coordinator.client.testmode() and service_name not in [
            SERVICE_GET_SYSTEM_INFO
        ]:
            raise ServiceValidationError(
                f"{self.entity_id} cannot be used while configuration is running in testmode",
                translation_domain=DOMAIN,
                translation_key="active_testmode",
                translation_placeholders={
                    "entity_id": self.entity_id,
                },
            )
        # When Api refresh is deactivated, do not run action to avoid kicking off other client Api token
        if not self.coordinator.client.allow_refresh():
            raise ServiceValidationError(
                f"{self.entity_id} cannot be used for requested action {service_name} while Api usage is deactivated",
                translation_domain=DOMAIN,
                translation_key="apiusage_deactivated",
                translation_placeholders={
                    "entity_id": self.entity_id,
                    "action_name": service_name,
                },
            )
        if (
            self.coordinator
            and hasattr(self.coordinator, "data")
            and self._context_base in self.coordinator.data
        ):
            if service_name in [SERVICE_GET_SYSTEM_INFO]:
                LOGGER.debug("%s action will be applied", service_name)
                # Wait until client cache is valid
                await self.coordinator.client.validate_cache()
                if kwargs.get(INCLUDE_CACHE):
                    result = (
                        await self.coordinator.client.api.update_sites(
                            siteId=self._context_base,
                            fromFile=self.coordinator.client.testmode(),
                            exclude=set(self.coordinator.client.exclude_categories),
                        )
                    ).get(self._context_base) or None
                else:
                    result = await self.coordinator.client.api.get_scene_info(
                        siteId=self._context_base,
                        fromFile=self.coordinator.client.testmode(),
                    )
                return {"system_info": result}

            raise ServiceValidationError(
                f"The entity {self.entity_id} does not support the action {service_name}",
                translation_domain=DOMAIN,
                translation_key="service_not_supported",
                translation_placeholders={
                    "entity": self.entity_id,
                    "service": service_name,
                },
            )
        return None

    async def _solarbank_schedule_service(
        self, service_name: str, **kwargs: Any
    ) -> dict | None:
        """Execute the defined solarbank schedule action."""
        # Raise alerts to frontend
        if not (self.supported_features & AnkerSolixEntityFeature.SOLARBANK_SCHEDULE):
            raise ServiceValidationError(
                f"The entity {self.entity_id} does not support the action {service_name}",
                translation_domain=DOMAIN,
                translation_key="service_not_supported",
                translation_placeholders={
                    "entity": self.entity_id,
                    "service": service_name,
                },
            )
        # When running in Test mode do not run services that are not supporting a testmode
        if self.coordinator.client.testmode() and service_name not in [
            SERVICE_SET_SOLARBANK_SCHEDULE,
            SERVICE_UPDATE_SOLARBANK_SCHEDULE,
            SERVICE_CLEAR_SOLARBANK_SCHEDULE,
            SERVICE_GET_SOLARBANK_SCHEDULE,
        ]:
            raise ServiceValidationError(
                f"{self.entity_id} cannot be used while configuration is running in testmode",
                translation_domain=DOMAIN,
                translation_key="active_testmode",
                translation_placeholders={
                    "entity_id": self.entity_id,
                },
            )
        # When Api refresh is deactivated, do not run action to avoid kicking off other client Api token
        if not self.coordinator.client.allow_refresh():
            raise ServiceValidationError(
                f"{self.entity_id} cannot be used for requested action {service_name} while Api usage is deactivated",
                translation_domain=DOMAIN,
                translation_key="apiusage_deactivated",
                translation_placeholders={
                    "entity_id": self.entity_id,
                    "action_name": service_name,
                },
            )
        if (
            self.coordinator
            and hasattr(self.coordinator, "data")
            and self._context_base in self.coordinator.data
        ):
            data: dict = self.coordinator.data.get(self._context_base)
            generation: int = int(data.get("generation") or 0)
            siteId = data.get("site_id") or ""
            if service_name in [
                SERVICE_SET_SOLARBANK_SCHEDULE,
                SERVICE_UPDATE_SOLARBANK_SCHEDULE,
            ]:
                plan = kwargs.get(PLAN)
                # Raise error if selected (active) plan not usable for the service
                if plan not in {
                    SolarbankRatePlan.smartplugs,
                    SolarbankRatePlan.manual,
                } and data.get("preset_usage_mode") not in {None, 1, 2, 3}:
                    raise ServiceValidationError(
                        f"The action {service_name} cannot be executed: {'Selected plan [' + str(plan) + '] of [' + self.entity_id + '] not usable for this action'}.",
                        translation_domain=DOMAIN,
                        translation_key="slot_time_error",
                        translation_placeholders={
                            "service": service_name,
                            "error": "Selected plan ["
                            + str(plan)
                            + "] of ["
                            + self.entity_id
                            + "] not usable for this action",
                        },
                    )
                start_time = kwargs.get(START_TIME)
                end_time = kwargs.get(END_TIME)
                if start_time and end_time:
                    if start_time < end_time:
                        weekdays = kwargs.get(WEEK_DAYS)
                        load = kwargs.get(APPLIANCE_LOAD)
                        dev_load = kwargs.get(DEVICE_LOAD)
                        allow_export = kwargs.get(ALLOW_EXPORT)
                        discharge_prio = kwargs.get(DISCHARGE_PRIORITY)
                        prio = kwargs.get(CHARGE_PRIORITY_LIMIT)
                        # check if now is in given time range and ensure preset increase is limited by min interval
                        now = datetime.now().astimezone()
                        # consider device timezone offset when checking for actual slot
                        tz_offset = (self.coordinator.data.get(siteId) or {}).get(
                            "energy_offset_tz"
                        ) or 0
                        start_time.astimezone()
                        # get old device load, which is none for single solarbanks, use old system preset instead
                        old_dev = data.get("preset_device_output_power") or data.get(
                            "preset_system_output_power"
                        )
                        old_dev = dev_load if old_dev is None else old_dev
                        # set the system load that should be checked for increase
                        check_load = (
                            load
                            if dev_load is None
                            else int(
                                self._last_schedule_service_value + (dev_load - old_dev)
                            )
                            if load is None
                            and self._last_schedule_service_value is not None
                            else None
                        )
                        if (
                            self._last_schedule_service_value
                            and check_load
                            and check_load > int(self._last_schedule_service_value)
                            and start_time.astimezone().time()
                            <= (now + timedelta(seconds=tz_offset)).time()
                            < end_time.astimezone().time()
                            and now
                            < (
                                self.hass.states.get(self.entity_id).last_changed
                                + timedelta(seconds=_SCAN_INTERVAL_MIN)
                            )
                        ):
                            LOGGER.debug(
                                "%s cannot be increased to %s because minimum change delay of %s seconds is not passed",
                                self.entity_id,
                                check_load,
                                _SCAN_INTERVAL_MIN,
                            )
                            # Raise alert to frontend
                            raise ServiceValidationError(
                                f"{self.entity_id} cannot be increased to {check_load} because minimum change delay of {_SCAN_INTERVAL_MIN} seconds is not passed",
                                translation_domain=DOMAIN,
                                translation_key="increase_blocked",
                                translation_placeholders={
                                    "entity_id": self.entity_id,
                                    "value": check_load,
                                    "delay": _SCAN_INTERVAL_MIN,
                                },
                            )

                        LOGGER.debug("%s action will be applied", service_name)
                        # Wait until client cache is valid
                        await self.coordinator.client.validate_cache()
                        if generation >= 2:
                            # SB2 schedule action
                            # Map action keys to api slot keys
                            slot = Solarbank2Timeslot(
                                start_time=start_time,
                                end_time=end_time,
                                appliance_load=load,
                                weekdays=set(weekdays) if weekdays else None,
                            )
                            if service_name == SERVICE_SET_SOLARBANK_SCHEDULE:
                                result = (
                                    await self.coordinator.client.api.set_sb2_home_load(
                                        siteId=siteId,
                                        deviceSn=self._context_base,
                                        set_slot=slot,
                                        plan_name=plan,
                                        toFile=self.coordinator.client.testmode(),
                                    )
                                )
                            elif service_name == SERVICE_UPDATE_SOLARBANK_SCHEDULE:
                                result = (
                                    await self.coordinator.client.api.set_sb2_home_load(
                                        siteId=siteId,
                                        deviceSn=self._context_base,
                                        insert_slot=slot,
                                        plan_name=plan,
                                        toFile=self.coordinator.client.testmode(),
                                    )
                                )
                            else:
                                result = False
                        else:
                            # SB1 schedule action
                            # Raise error if action currently not usable for active schedule
                            if (
                                data.get("cascaded")
                                and data.get("preset_allow_export") is None
                            ):
                                raise ServiceValidationError(
                                    f"The action {service_name} cannot be executed: {'Active schedule of [' + self.entity_id + '] not usable for this action'}.",
                                    translation_domain=DOMAIN,
                                    translation_key="slot_time_error",
                                    translation_placeholders={
                                        "service": service_name,
                                        "error": "Active schedule of ["
                                        + self.entity_id
                                        + "] not usable for this action",
                                    },
                                )
                            # Map action keys to api slot keys
                            slot = SolarbankTimeslot(
                                start_time=start_time,
                                end_time=end_time,
                                appliance_load=load,
                                device_load=dev_load,
                                allow_export=allow_export,
                                discharge_priority=discharge_prio,
                                charge_priority_limit=prio,
                            )
                            if service_name == SERVICE_SET_SOLARBANK_SCHEDULE:
                                result = (
                                    await self.coordinator.client.api.set_home_load(
                                        siteId=siteId,
                                        deviceSn=self._context_base,
                                        set_slot=slot,
                                        toFile=self.coordinator.client.testmode(),
                                    )
                                )
                            elif service_name == SERVICE_UPDATE_SOLARBANK_SCHEDULE:
                                result = (
                                    await self.coordinator.client.api.set_home_load(
                                        siteId=siteId,
                                        deviceSn=self._context_base,
                                        insert_slot=slot,
                                        toFile=self.coordinator.client.testmode(),
                                    )
                                )
                            else:
                                result = False

                        # log resulting schedule if testmode returned dict
                        if isinstance(result, dict) and ALLOW_TESTMODE:
                            LOGGER.info(
                                "%s: Applied schedule for action %s:\n%s",
                                "TESTMODE"
                                if self.coordinator.client.testmode()
                                else "LIVEMODE",
                                service_name,
                                json.dumps(
                                    result,
                                    indent=2 if len(json.dumps(result)) < 200 else None,
                                ),
                            )
                        # update sites was required to get applied output power fields, they are not provided with get_device_parm endpoint
                        # which fetches new schedule after update. Now the output power fields are updated along with a schedule update in the cache
                        # await self.coordinator.client.api.update_sites(
                        #     siteId=siteId,
                        #     fromFile=self.coordinator.client.testmode(),
                        # )
                        # trigger coordinator update with api dictionary data
                        await self.coordinator.async_refresh_data_from_apidict()
                        # refresh last applied system load
                        if result:
                            self._last_schedule_service_value = (
                                self.coordinator.data.get(self._context_base) or {}
                            ).get("preset_system_output_power") or None
                    else:
                        raise ServiceValidationError(
                            f"The action {service_name} cannot be executed: {'start_time must be earlier than end_time'}.",
                            translation_domain=DOMAIN,
                            translation_key="slot_time_error",
                            translation_placeholders={
                                "service": service_name,
                                "error": "start_time must be earlier than end_time",
                            },
                        )
                else:
                    raise ServiceValidationError(
                        f"The action {service_name} cannot be executed: {'start_time or end_time missing'}.",
                        translation_domain=DOMAIN,
                        translation_key="slot_time_error",
                        translation_placeholders={
                            "service": service_name,
                            "error": "start_time or end_time missing",
                        },
                    )

            elif service_name in [SERVICE_GET_SOLARBANK_SCHEDULE]:
                LOGGER.debug("%s action will be applied", service_name)
                # Wait until client cache is valid
                await self.coordinator.client.validate_cache()
                if generation >= 2 and (data.get("schedule") or {}):
                    # get SB2 schedule
                    result = (
                        await self.coordinator.client.api.get_device_parm(
                            siteId=siteId,
                            paramType=SolixParmType.SOLARBANK_2_SCHEDULE.value,
                            deviceSn=self._context_base,
                            fromFile=self.coordinator.client.testmode(),
                        )
                        or {}
                    ).get("param_data")
                else:
                    result = (
                        await self.coordinator.client.api.get_device_load(
                            siteId=siteId,
                            deviceSn=self._context_base,
                            fromFile=self.coordinator.client.testmode(),
                        )
                        or {}
                    ).get("home_load_data")
                # trigger coordinator update with api dictionary data
                await self.coordinator.async_refresh_data_from_apidict()
                return {"schedule": result}

            elif service_name in [SERVICE_CLEAR_SOLARBANK_SCHEDULE]:
                LOGGER.debug("%s action will be applied", service_name)
                # Wait until client cache is valid
                await self.coordinator.client.validate_cache()
                if generation >= 2:
                    # Clear SB2 schedule
                    if data.get("schedule") or {}:
                        plan = kwargs.get(PLAN)
                        weekdays = kwargs.get(WEEK_DAYS)
                        result = await self.coordinator.client.api.set_sb2_home_load(
                            siteId=siteId,
                            deviceSn=self._context_base,
                            plan_name=plan,
                            set_slot=Solarbank2Timeslot(
                                start_time=None,
                                end_time=None,
                                weekdays=set(weekdays) if weekdays else None,
                            ),
                            toFile=self.coordinator.client.testmode(),
                        )
                        # log resulting schedule if in testmode
                        if isinstance(result, dict) and ALLOW_TESTMODE:
                            LOGGER.info(
                                "%s: Applied schedule for action %s:\n%s",
                                "TESTMODE"
                                if self.coordinator.client.testmode()
                                else "LIVEMODE",
                                service_name,
                                json.dumps(
                                    result,
                                    indent=2 if len(json.dumps(result)) < 200 else None,
                                ),
                            )
                else:
                    # clear SB 1 schedule
                    # Wait until client cache is valid
                    await self.coordinator.client.validate_cache()
                    # No need to Raise error if cascaded, since clearing will directly be done against correct Api device param for custom SB1 schedule
                    result = await self.coordinator.client.api.set_device_parm(
                        siteId=siteId,
                        paramData={"ranges": []},
                        deviceSn=self._context_base,
                        toFile=self.coordinator.client.testmode(),
                    )
                    # log resulting schedule if testmode returned dict
                    if isinstance(result, dict) and ALLOW_TESTMODE:
                        LOGGER.info(
                            "%s: Applied schedule for action %s:\n%s",
                            "TESTMODE"
                            if self.coordinator.client.testmode()
                            else "LIVEMODE",
                            service_name,
                            json.dumps(
                                result,
                                indent=2 if len(json.dumps(result)) < 200 else None,
                            ),
                        )

                # update sites was required to get applied output power fields, they are not provided with get_device_parm endpoint
                # which fetches new schedule after update. Now the output power fields are updated along with a schedule update in the cache
                # await self.coordinator.client.api.update_sites(
                #     siteId=siteId,
                #     fromFile=self.coordinator.client.testmode(),
                # )
                # trigger coordinator update with api dictionary data
                await self.coordinator.async_refresh_data_from_apidict()

            else:
                raise ServiceValidationError(
                    f"The entity {self.entity_id} does not support the action {service_name}",
                    translation_domain=DOMAIN,
                    translation_key="service_not_supported",
                    translation_placeholders={
                        "entity": self.entity_id,
                        "service": service_name,
                    },
                )
        return None


class AnkerSolixRestoreSensor(AnkerSolixSensor, RestoreSensor):
    """Represents an restore sensor entity for Anker Solix site and device data."""

    coordinator: AnkerSolixDataUpdateCoordinator
    entity_description: AnkerSolixSensorDescription

    def __init__(
        self,
        coordinator: AnkerSolixDataUpdateCoordinator,
        description: AnkerSolixSensorDescription,
        context: str,
        entity_type: str,
    ) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, description, context, entity_type)
        self._assumed_state = True

    async def async_added_to_hass(self) -> None:
        """Load the last known state when added to hass."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) and (
            last_data := await self.async_get_last_sensor_data()
        ):
            # handle special entity restore actions for customized attributes even if old state was unknown
            if self._attribute_name in ["solar_forecast_today"]:
                attribute = "forecast_hourly"
                if (
                    attr_value := last_state.attributes.get(attribute)
                ) and self.extra_state_attributes.get(attribute) != attr_value:
                    LOGGER.info(
                        "Restored state attribute '%s' of entity '%s' to: %s",
                        attribute,
                        self.entity_id,
                        attr_value,
                    )
                    self.coordinator.client.api.customizeCacheId(
                        id=self.coordinator_context,
                        key="pv_forecast_details",
                        value={"trend": attr_value},
                    )
                    await self.coordinator.async_refresh_data_from_apidict(delayed=True)
            elif (
                last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE)
                and self._native_value is not None
            ):
                # set the customized value if it was modified
                if self._native_value != last_data.native_value:
                    self._native_value = last_data.native_value
                    LOGGER.info(
                        "Restored state value of entity '%s' to: %s",
                        self.entity_id,
                        self._native_value,
                    )
                    self.coordinator.client.api.customizeCacheId(
                        id=self.coordinator_context,
                        key=self.entity_description.json_key,
                        value=str(last_data.native_value),
                    )
                    await self.coordinator.async_refresh_data_from_apidict(delayed=True)
