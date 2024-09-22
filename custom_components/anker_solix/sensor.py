"""Sensor platform for anker_solix."""

from __future__ import annotations  # noqa: I001

from dataclasses import dataclass
from datetime import datetime, timedelta
from collections.abc import Callable
from contextlib import suppress
import logging
from pathlib import Path
from random import randrange, choice
from typing import Any

import urllib.parse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_platform
import homeassistant.helpers.config_validation as cv
import json

from .config_flow import _SCAN_INTERVAL_MIN

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
    UnitOfPower,
    UnitOfEnergy,
    UnitOfTemperature,
    PERCENTAGE,
    CONF_EXCLUDE,
)

from homeassistant.core import HomeAssistant, SupportsResponse, callback

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.typing import StateType
from homeassistant.helpers import device_registry as dr

from .const import (
    DOMAIN,
    LOGGER,
    ATTRIBUTION,
    CREATE_ALL_ENTITIES,
    EXPORTFOLDER,
    TEST_NUMBERVARIANCE,
    LAST_PERIOD,
    LAST_RESET,
    SERVICE_CLEAR_SOLARBANK_SCHEDULE,
    SERVICE_EXPORT_SYSTEMS,
    SERVICE_GET_SOLARBANK_SCHEDULE,
    SERVICE_GET_SYSTEM_INFO,
    SERVICE_SET_SOLARBANK_SCHEDULE,
    SERVICE_UPDATE_SOLARBANK_SCHEDULE,
    SOLIX_ENTITY_SCHEMA,
    SOLIX_WEEKDAY_SCHEMA,
    SOLARBANK_TIMESLOT_SCHEMA,
    START_TIME,
    END_TIME,
    ALLOW_EXPORT,
    APPLIANCE_LOAD,
    DEVICE_LOAD,
    CHARGE_PRIORITY_LIMIT,
    WEEK_DAYS,
    CONF_SKIP_INVALID,
)
from .coordinator import AnkerSolixDataUpdateCoordinator
from .solixapi import export
from .solixapi.apitypes import (
    ApiCategories,
    SmartmeterStatus,
    SolarbankStatus,
    SolarbankPowerMode,
    SolixDeviceStatus,
    SolixDeviceType,
    SolixParmType,
    SolarbankTimeslot,
    Solarbank2Timeslot,
)
from .entity import (
    AnkerSolixPicturePath,
    AnkerSolixEntityType,
    AnkerSolixEntityRequiredKeyMixin,
    get_AnkerSolixDeviceInfo,
    get_AnkerSolixSystemInfo,
    AnkerSolixEntityFeature,
)


@dataclass(frozen=True)
class AnkerSolixSensorDescription(
    SensorEntityDescription, AnkerSolixEntityRequiredKeyMixin
):
    """Sensor entity description with optional keys."""

    reset_at_midnight: bool = False
    picture_path: str = None
    # Use optionally to provide function for value calculation or lookup of nested values
    value_fn: Callable[[dict, str, str], StateType] = lambda d, jk, _: d.get(jk)
    attrib_fn: Callable[[dict, str], dict | None] = lambda d, _: None
    unit_fn: Callable[[dict, str], dict | None] = lambda d, _: None
    force_creation_fn: Callable[[dict], bool] = lambda d: False
    exclude_fn: Callable[[set, dict], bool] = lambda s, _: False
    nested_sensor: bool = False
    feature: AnkerSolixEntityFeature | None = None
    check_invalid: bool = False


DEVICE_SENSORS = [
    AnkerSolixSensorDescription(
        key="status_desc",
        translation_key="status_desc",
        json_key="status_desc",
        device_class=SensorDeviceClass.ENUM,
        options=[status.name for status in SolixDeviceStatus],
        attrib_fn=lambda d, _: {
            "status": d.get("status"),
        },
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
    ),
    AnkerSolixSensorDescription(
        key="charging_status_desc",
        translation_key="charging_status_desc",
        json_key="charging_status_desc",
        device_class=SensorDeviceClass.ENUM,
        options=[status.name for status in SolarbankStatus],
        attrib_fn=lambda d, _: {"charging_status": d.get("charging_status")},
        exclude_fn=lambda s, _: not ({SolixDeviceType.SOLARBANK.value} - s),
        check_invalid=True,
    ),
    AnkerSolixSensorDescription(
        key="charging_power",
        translation_key="charging_power",
        json_key="charging_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, _: not ({SolixDeviceType.SOLARBANK.value} - s),
        check_invalid=True,
    ),
    AnkerSolixSensorDescription(
        key="input_power",
        translation_key="input_power",
        json_key="input_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, _: not ({SolixDeviceType.SOLARBANK.value} - s),
        check_invalid=True,
    ),
    AnkerSolixSensorDescription(
        key="solar_power_1",
        translation_key="solar_power_1",
        json_key="solar_power_1",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, _: not ({SolixDeviceType.SOLARBANK.value} - s),
        check_invalid=True,
    ),
    AnkerSolixSensorDescription(
        key="solar_power_2",
        translation_key="solar_power_2",
        json_key="solar_power_2",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, _: not ({SolixDeviceType.SOLARBANK.value} - s),
        check_invalid=True,
    ),
    AnkerSolixSensorDescription(
        key="solar_power_3",
        translation_key="solar_power_3",
        json_key="solar_power_3",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, _: not ({SolixDeviceType.SOLARBANK.value} - s),
        check_invalid=True,
    ),
    AnkerSolixSensorDescription(
        key="solar_power_4",
        translation_key="solar_power_4",
        json_key="solar_power_4",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, _: not ({SolixDeviceType.SOLARBANK.value} - s),
        check_invalid=True,
    ),
    AnkerSolixSensorDescription(
        key="ac_socket",
        translation_key="ac_socket",
        json_key="ac_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, _: not ({SolixDeviceType.SOLARBANK.value} - s),
        check_invalid=True,
    ),
    AnkerSolixSensorDescription(
        key="output_power",
        translation_key="output_power",
        json_key="output_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, _: not ({SolixDeviceType.SOLARBANK.value} - s),
        check_invalid=True,
    ),
    AnkerSolixSensorDescription(
        key="ac_to_home_load",
        translation_key="ac_to_home_load",
        json_key="to_home_load",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, _: not ({SolixDeviceType.SOLARBANK.value} - s),
        check_invalid=True,
    ),
    AnkerSolixSensorDescription(
        key="home_load_power",
        translation_key="home_load_power",
        json_key="home_load_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, _: not ({SolixDeviceType.SMARTMETER.value} - s),
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
        # Resulting Output preset per device
        # This may also present 0 W if the allow discharge switch is disabled, even if the W preset value remains and the minimum bypass per defined inverter will be used
        # This is confusing in the App and the Api, since there may be the minimum bypass W applied even if 0 W is shown.
        # 0 W is only applied truly if the 0 W Switch is installed for non Anker inverters, or if MI80 is used which supports the 0 W setting natively
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
            d.get("type") == SolixDeviceType.SOLARBANK.value
        ),
        exclude_fn=lambda s, _: not ({SolixDeviceType.SOLARBANK.value} - s),
    ),
    AnkerSolixSensorDescription(
        key="set_power_mode",
        translation_key="set_power_mode",
        json_key="preset_power_mode",
        device_class=SensorDeviceClass.ENUM,
        options=[mode.name for mode in SolarbankPowerMode],
        value_fn=lambda d, jk, _: next(
            iter([item.name for item in SolarbankPowerMode if item.value == d.get(jk)]),
            None,
        ),
        attrib_fn=lambda d, _: {
            "mode": d.get("preset_power_mode"),
        },
        exclude_fn=lambda s, _: not ({SolixDeviceType.SOLARBANK.value} - s),
    ),
    AnkerSolixSensorDescription(
        key="state_of_charge",
        translation_key="state_of_charge",
        json_key="battery_soc",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, _: not ({SolixDeviceType.SOLARBANK.value} - s),
        check_invalid=True,
    ),
    AnkerSolixSensorDescription(
        key="battery_energy",
        translation_key="battery_energy",
        json_key="battery_energy",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        suggested_display_precision=0,
        attrib_fn=lambda d, _: {
            "capacity": " ".join(
                [str(d.get("battery_capacity") or "----"), UnitOfEnergy.WATT_HOUR]
            )
        },
        exclude_fn=lambda s, _: not ({SolixDeviceType.SOLARBANK.value} - s),
    ),
    AnkerSolixSensorDescription(
        key="bws_surplus",
        translation_key="bws_surplus",
        json_key="bws_surplus",
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        check_invalid=True,
    ),
    AnkerSolixSensorDescription(
        key="temperature",
        translation_key="temperature",
        json_key="temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
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
        exclude_fn=lambda s, _: not ({SolixDeviceType.SOLARBANK.value} - s),
        check_invalid=True,
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
        key="photovoltaic_to_grid_power",
        translation_key="photovoltaic_to_grid_power",
        json_key="photovoltaic_to_grid_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exclude_fn=lambda s, _: not ({SolixDeviceType.SMARTMETER.value} - s),
        check_invalid=True,
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
    ),
    AnkerSolixSensorDescription(
        key="grid_status_desc",
        translation_key="grid_status_desc",
        json_key="grid_status_desc",
        device_class=SensorDeviceClass.ENUM,
        options=[status.name for status in SmartmeterStatus],
        attrib_fn=lambda d, _: {"grid_status": d.get("grid_status")},
        exclude_fn=lambda s, _: not ({SolixDeviceType.SMARTMETER.value} - s),
        check_invalid=True,
    ),
    AnkerSolixSensorDescription(
        key="tag",
        translation_key="tag",
        json_key="tag",
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
    ),
]

SITE_SENSORS = [
    AnkerSolixSensorDescription(
        key="solarbank_list",
        translation_key="solarbank_list",
        json_key="solarbank_list",
        picture_path=AnkerSolixPicturePath.SOLARBANK,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d, jk, _: len(
            list((d.get("solarbank_info") or {}).get(jk) or [])
        ),
        force_creation_fn=lambda d: True,
        exclude_fn=lambda s, _: not ({SolixDeviceType.SOLARBANK.value} - s),
    ),
    AnkerSolixSensorDescription(
        key="pps_list",
        translation_key="pps_list",
        json_key="pps_list",
        # entity_registry_enabled_default=False,
        picture_path=AnkerSolixPicturePath.PPS,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d, jk, _: len(list((d.get("pps_info") or {}).get(jk) or [])),
        force_creation_fn=lambda d: True,
        exclude_fn=lambda s, _: not ({SolixDeviceType.PPS.value} - s),
    ),
    AnkerSolixSensorDescription(
        key="solar_list",
        translation_key="solar_list",
        json_key="solar_list",
        picture_path=AnkerSolixPicturePath.INVERTER,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d, jk, _: len(list(d.get(jk) or [])),
        force_creation_fn=lambda d: True,
        exclude_fn=lambda s, _: not ({SolixDeviceType.INVERTER.value} - s),
    ),
    AnkerSolixSensorDescription(
        key="powerpanel_list",
        translation_key="powerpanel_list",
        json_key="powerpanel_list",
        # entity_registry_enabled_default=False,
        picture_path=AnkerSolixPicturePath.POWERPANEL,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d, jk, _: len(list(d.get(jk) or [])),
        force_creation_fn=lambda d: True,
        exclude_fn=lambda s, _: not ({SolixDeviceType.POWERPANEL.value} - s),
    ),
    AnkerSolixSensorDescription(
        key="smartmeter_list",
        translation_key="smartmeter_list",
        json_key="grid_list",
        # entity_registry_enabled_default=False,
        picture_path=AnkerSolixPicturePath.SMARTMETER,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d, jk, _: len(list((d.get("grid_info") or {}).get(jk) or [])),
        force_creation_fn=lambda d: True,
        exclude_fn=lambda s, _: not ({SolixDeviceType.SMARTMETER.value} - s),
    ),
    AnkerSolixSensorDescription(
        key="smart_plug_list",
        translation_key="smart_plug_list",
        json_key="smartplug_list",
        # entity_registry_enabled_default=False,
        picture_path=AnkerSolixPicturePath.SMARTPLUG,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d, jk, _: len(
            list((d.get("smart_plug_info") or {}).get(jk) or [])
        ),
        force_creation_fn=lambda d: True,
        exclude_fn=lambda s, _: not ({SolixDeviceType.SMARTPLUG.value} - s),
    ),
    AnkerSolixSensorDescription(
        # Summary of all solarbank charing power on site
        key="solarbank_charging_power",
        translation_key="solarbank_charging_power",
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
        # exclude sensor if unused artifacts in structure
        exclude_fn=lambda s, d: not ({SolixDeviceType.SOLARBANK.value} - s)
        or not list((d.get("solarbank_info") or {}).get("solarbank_list") or []),
    ),
    AnkerSolixSensorDescription(
        # Summary of all pps charging power on site
        key="pps_charging_power",
        translation_key="pps_charging_power",
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
        device_class=SensorDeviceClass.WEIGHT,
        state_class=SensorStateClass.MEASUREMENT,
        force_creation_fn=lambda d: True,
        value_fn=lambda d, jk, _: float(
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
        value_fn=lambda d, jk, _: float(
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
        ).replace("w", "W")
        or None,
        device_class=SensorDeviceClass.ENERGY,
        force_creation_fn=lambda d: True,
        feature=AnkerSolixEntityFeature.SYSTEM_INFO,
        value_fn=lambda d, jk, _: float(
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
    # Following sensor delivers meaningless values if any, home_info charging_power reports same value as inverter generated_power?!?
    # AnkerSolixSensorDescription(
    #     # System charging power
    #     key="site_charging_power",
    #     translation_key="site_charging_power",
    #     json_key="charging_power",
    #     entity_registry_enabled_default=False,
    #     native_unit_of_measurement=UnitOfPower.WATT,
    #     device_class=SensorDeviceClass.POWER,
    #     value_fn=lambda d, jk, _: (d.get("home_info") or {}).get(jk),
    #     suggested_display_precision=0,
    # ),
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
        key="daily_discharge_energy",
        translation_key="daily_discharge_energy",
        json_key="solarbank_discharge",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: (
            (d.get("energy_details") or {}).get("today") or {}
        ).get(jk),
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": (
                (d.get("energy_details") or {}).get("last_period") or {}
            ).get("solarbank_discharge"),
        },
        exclude_fn=lambda s, _: not (
            {SolixDeviceType.SOLARBANK.value} - s
            and {ApiCategories.solarbank_energy} - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="daily_charge_energy",
        translation_key="daily_charge_energy",
        json_key="solarbank_charge",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: (
            (d.get("energy_details") or {}).get("today") or {}
        ).get(jk),
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": (
                (d.get("energy_details") or {}).get("last_period") or {}
            ).get("solarbank_charge"),
        },
        exclude_fn=lambda s, _: not (
            {SolixDeviceType.SOLARBANK.value} - s
            and {ApiCategories.solarbank_energy} - s
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
        value_fn=lambda d, jk, _: (
            (d.get("energy_details") or {}).get("today") or {}
        ).get(jk),
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": (
                (d.get("energy_details") or {}).get("last_period") or {}
            ).get("solar_production"),
        },
        exclude_fn=lambda s, _: not (
            {SolixDeviceType.SOLARBANK.value} - s
            and {ApiCategories.solarbank_energy} - s
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
        value_fn=lambda d, jk, _: (
            (d.get("energy_details") or {}).get("today") or {}
        ).get(jk),
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
        value_fn=lambda d, jk, _: (
            (d.get("energy_details") or {}).get("today") or {}
        ).get(jk),
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
        value_fn=lambda d, jk, _: (
            (d.get("energy_details") or {}).get("today") or {}
        ).get(jk),
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
        value_fn=lambda d, jk, _: (
            (d.get("energy_details") or {}).get("today") or {}
        ).get(jk),
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
        key="daily_ac_socket",
        translation_key="daily_ac_socket",
        json_key="ac_socket",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: (
            (d.get("energy_details") or {}).get("today") or {}
        ).get(jk),
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
        key="daily_battery_to_home",
        translation_key="daily_battery_to_home",
        json_key="battery_to_home",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: (
            (d.get("energy_details") or {}).get("today") or {}
        ).get(jk),
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": (
                (d.get("energy_details") or {}).get("last_period") or {}
            ).get("battery_to_home"),
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
        value_fn=lambda d, jk, _: (
            (d.get("energy_details") or {}).get("today") or {}
        ).get(jk),
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": (
                (d.get("energy_details") or {}).get("last_period") or {}
            ).get("home_usage"),
        },
        exclude_fn=lambda s, _: not (
            {SolixDeviceType.SOLARBANK.value, SolixDeviceType.SMARTMETER.value} - s
            and {ApiCategories.solarbank_energy, ApiCategories.smartmeter_energy} - s
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
        value_fn=lambda d, jk, _: (
            (d.get("energy_details") or {}).get("today") or {}
        ).get(jk),
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
        key="daily_grid_to_home",
        translation_key="daily_grid_to_home",
        json_key="grid_to_home",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
        value_fn=lambda d, jk, _: (
            (d.get("energy_details") or {}).get("today") or {}
        ).get(jk),
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": (
                (d.get("energy_details") or {}).get("last_period") or {}
            ).get("grid_to_home"),
        },
        exclude_fn=lambda s, _: not (
            {SolixDeviceType.SMARTMETER.value} - s
            and {ApiCategories.smartmeter_energy} - s
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
        value_fn=lambda d, jk, _: (
            (d.get("energy_details") or {}).get("today") or {}
        ).get(jk),
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": (
                (d.get("energy_details") or {}).get("last_period") or {}
            ).get("solar_to_grid"),
        },
        exclude_fn=lambda s, _: not (
            {SolixDeviceType.SMARTMETER.value} - s
            and {ApiCategories.smartmeter_energy} - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="daily_solar_share",
        translation_key="daily_solar_share",
        json_key="solar_percentage",
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
        value_fn=lambda d, jk, _: None
        if not d.get("energy_details")
        else 100 * float(((d.get("energy_details") or {}).get("today") or {}).get(jk)),
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": None
            if not d.get("energy_details")
            else 100
            * float(
                ((d.get("energy_details") or {}).get("last_period") or {}).get(
                    "solar_percentage"
                )
            ),
        },
        exclude_fn=lambda s, _: not (
            {SolixDeviceType.SOLARBANK.value} - s
            and {ApiCategories.solarbank_energy} - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="daily_battery_share",
        translation_key="daily_battery_share",
        json_key="battery_percentage",
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
        value_fn=lambda d, jk, _: None
        if not d.get("energy_details")
        else 100 * float(((d.get("energy_details") or {}).get("today") or {}).get(jk)),
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": None
            if not d.get("energy_details")
            else 100
            * float(
                ((d.get("energy_details") or {}).get("last_period") or {}).get(
                    "battery_percentage"
                )
            ),
        },
        exclude_fn=lambda s, _: not (
            {SolixDeviceType.SOLARBANK.value} - s
            and {ApiCategories.solarbank_energy} - s
        ),
    ),
    AnkerSolixSensorDescription(
        key="daily_grid_share",
        translation_key="daily_grid_share",
        json_key="other_percentage",
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
        value_fn=lambda d, jk, _: None
        if not d.get("energy_details")
        else 100 * float(((d.get("energy_details") or {}).get("today") or {}).get(jk)),
        attrib_fn=lambda d, _: {
            "date": ((d.get("energy_details") or {}).get("today") or {}).get("date"),
            "last_period": None
            if not d.get("energy_details")
            else 100
            * float(
                ((d.get("energy_details") or {}).get("last_period") or {}).get(
                    "other_percentage"
                )
            ),
        },
        exclude_fn=lambda s, _: not (
            {SolixDeviceType.SMARTMETER.value} - s
            and {ApiCategories.smartmeter_energy} - s
        ),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor platform."""

    coordinator = hass.data[DOMAIN].get(entry.entry_id)
    entities = []

    if coordinator and hasattr(coordinator, "data") and coordinator.data:
        # create entity type based on type of entry in coordinator data, which consolidates the api.sites and api.devices dictionaries
        # the coordinator.data dict key is either a site_id or device_sn and used as context for the entity to lookup its data
        for context, data in coordinator.data.items():
            if data.get("type") == SolixDeviceType.SYSTEM.value:
                # Unique key for site_id entry in data
                entity_type = AnkerSolixEntityType.SITE
                entity_list = SITE_SENSORS
            else:
                # device_sn entry in data
                entity_type = AnkerSolixEntityType.DEVICE
                entity_list = DEVICE_SENSORS

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
                            or description.value_fn(data, description.json_key, serial)
                            is not None
                        )
                    )
                ):
                    if description.device_class == SensorDeviceClass.ENERGY:
                        entity = AnkerSolixEnergySensor(
                            coordinator, description, sn, entity_type
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
        name=SERVICE_EXPORT_SYSTEMS,
        schema=SOLIX_ENTITY_SCHEMA,
        func=SERVICE_EXPORT_SYSTEMS,
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
    _attr_attribution = ATTRIBUTION
    _context_base: str = None
    _context_nested: str = None
    _last_schedule_service_value: str = None
    _unrecorded_attributes = frozenset(
        {
            "sw_version",
            "device_sn",
            "schedule",
            "inverter_info",
            "solar_brand",
            "solar_model",
            "solar_sn",
            "fittings",
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
            self._attr_device_info = get_AnkerSolixDeviceInfo(data, self._context_base)
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

        else:
            # get the site info data from site context entry of coordinator data
            data = (coordinator.data.get(self._context_base, {})).get("site_info", {})
            self._attr_device_info = get_AnkerSolixSystemInfo(data, self._context_base)
            # add service attribute for managble sites
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
            data = self.coordinator.data.get(self._context_base)
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
            data = self.coordinator.data.get(self._context_base)
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
                    if self.entity_description.check_invalid and not data.get(
                        "data_valid", True
                    ):
                        # skip update or mark unvailable
                        if not self.coordinator.config_entry.options.get(
                            CONF_SKIP_INVALID
                        ):
                            self._native_value = None
                    else:
                        self._native_value = self.entity_description.value_fn(
                            data, key, self.coordinator_context
                        )
                    # update sensor unit if described by function
                    if unit := self.entity_description.unit_fn(
                        data, self.coordinator_context
                    ):
                        self._attr_native_unit_of_measurement = unit
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

    @callback
    async def get_system_info(self, **kwargs: Any) -> None:
        """Get the actual system info from the api."""
        return await self._solix_system_service(
            service_name=SERVICE_GET_SYSTEM_INFO, **kwargs
        )

    @callback
    async def export_systems(self, **kwargs: Any) -> None:
        """Export the actual api responses for accessible systems and devices into zipped JSON files."""
        return await self._solix_system_service(
            service_name=SERVICE_EXPORT_SYSTEMS, **kwargs
        )

    @callback
    async def get_solarbank_schedule(self, **kwargs: Any) -> None:
        """Get the active solarbank schedule from the api."""
        return await self._solarbank_schedule_service(
            service_name=SERVICE_GET_SOLARBANK_SCHEDULE, **kwargs
        )

    @callback
    async def clear_solarbank_schedule(self, **kwargs: Any) -> None:
        """Clear the active solarbank schedule."""
        return await self._solarbank_schedule_service(
            service_name=SERVICE_CLEAR_SOLARBANK_SCHEDULE, **kwargs
        )

    @callback
    async def set_solarbank_schedule(self, **kwargs: Any) -> None:
        """Set the defined solarbank schedule slot."""
        return await self._solarbank_schedule_service(
            service_name=SERVICE_SET_SOLARBANK_SCHEDULE, **kwargs
        )

    @callback
    async def update_solarbank_schedule(self, **kwargs: Any) -> None:
        """Update the defined solarbank schedule."""
        return await self._solarbank_schedule_service(
            service_name=SERVICE_UPDATE_SOLARBANK_SCHEDULE, **kwargs
        )

    async def _solix_system_service(self, service_name: str, **kwargs: Any) -> None:
        """Execute the defined solarbank schedule service."""
        # Raise alerts to frontend
        if not (self.supported_features & AnkerSolixEntityFeature.SYSTEM_INFO):
            raise ServiceValidationError(
                f"The entity {self.entity_id} does not support the service {service_name}",
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
                f"{self.entity_id} cannot be used for requested service while running in testmode",
                translation_domain=DOMAIN,
                translation_key="active_testmode",
                translation_placeholders={
                    "entity_id": self.entity_id,
                },
            )
        if (
            self.coordinator
            and hasattr(self.coordinator, "data")
            and self._context_base in self.coordinator.data
        ):
            if service_name in [SERVICE_GET_SYSTEM_INFO]:
                LOGGER.debug("%s service will be applied", service_name)
                result = await self.coordinator.client.api.get_scene_info(
                    siteId=self._context_base,
                    fromFile=self.coordinator.client.testmode(),
                )
                return {"system_info": result}

            if service_name in [SERVICE_EXPORT_SYSTEMS]:
                LOGGER.debug("%s service will be applied", service_name)
                exportlogger: logging.Logger = logging.getLogger("anker_solix_export")
                exportlogger.setLevel(logging.DEBUG)
                # disable updates via coordinator while using Api client and caches for randomized system export
                self.coordinator.skip_update = True
                myexport = export.AnkerSolixApiExport(
                    client=self.coordinator.client.api,
                    logger=exportlogger,
                )
                wwwroot = str(Path(self.coordinator.hass.config.config_dir) / "www")
                exportpath: str = str(
                    Path(wwwroot) / "community" / DOMAIN / EXPORTFOLDER
                )
                if await myexport.export_data(export_path=exportpath):
                    # convert path to public available url folder and filename
                    result = urllib.parse.quote(
                        myexport.zipfilename.replace(
                            wwwroot, AnkerSolixPicturePath.LOCALPATH
                        )
                    )
                else:
                    result = None
                # re-enable updates via coordinator
                self.coordinator.skip_update = False
                return {"export_filename": result}

            raise ServiceValidationError(
                f"The entity {self.entity_id} does not support the service {service_name}",
                translation_domain=DOMAIN,
                translation_key="service_not_supported",
                translation_placeholders={
                    "entity": self.entity_id,
                    "service": service_name,
                },
            )
        return None

    async def _solarbank_schedule_service(  # noqa: C901
        self, service_name: str, **kwargs: Any
    ) -> None:
        """Execute the defined solarbank schedule service."""
        # Raise alerts to frontend
        if not (self.supported_features & AnkerSolixEntityFeature.SOLARBANK_SCHEDULE):
            raise ServiceValidationError(
                f"The entity {self.entity_id} does not support the service {service_name}",
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
                f"{self.entity_id} cannot be changed while configuration is running in testmode",
                translation_domain=DOMAIN,
                translation_key="active_testmode",
                translation_placeholders={
                    "entity_id": self.entity_id,
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
                if START_TIME in kwargs and END_TIME in kwargs:
                    if (start_time := kwargs.get(START_TIME)) < (
                        end_time := kwargs.get(END_TIME)
                    ):
                        weekdays = kwargs.get(WEEK_DAYS)
                        if weekdays == cv.ENTITY_MATCH_NONE:
                            weekdays = None
                        load = kwargs.get(APPLIANCE_LOAD)
                        if load == cv.ENTITY_MATCH_NONE:
                            load = None
                        dev_load = kwargs.get(DEVICE_LOAD)
                        if dev_load == cv.ENTITY_MATCH_NONE:
                            dev_load = None
                        allow_export = kwargs.get(ALLOW_EXPORT)
                        if allow_export == cv.ENTITY_MATCH_NONE:
                            allow_export = None
                        prio = kwargs.get(CHARGE_PRIORITY_LIMIT)
                        if prio == cv.ENTITY_MATCH_NONE:
                            prio = None
                        # check if now is in given time range and ensure preset increase is limited by min interval
                        now = datetime.now().astimezone()
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
                            <= now.time()
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

                        LOGGER.debug("%s service will be applied", service_name)
                        if generation > 1:
                            # SB2 schedule service
                            # Map service keys to api slot keys
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
                                        test_schedule=data.get("schedule") or {}
                                        if self.coordinator.client.testmode()
                                        else None,
                                    )
                                )
                            elif service_name == SERVICE_UPDATE_SOLARBANK_SCHEDULE:
                                result = (
                                    await self.coordinator.client.api.set_sb2_home_load(
                                        siteId=siteId,
                                        deviceSn=self._context_base,
                                        insert_slot=slot,
                                        test_schedule=data.get("schedule") or {}
                                        if self.coordinator.client.testmode()
                                        else None,
                                    )
                                )
                            else:
                                result = False
                        else:
                            # SB1 schedule service
                            # Map service keys to api slot keys
                            slot = SolarbankTimeslot(
                                start_time=start_time,
                                end_time=end_time,
                                appliance_load=load,
                                device_load=dev_load,
                                allow_export=allow_export,
                                charge_priority_limit=prio,
                            )
                            if service_name == SERVICE_SET_SOLARBANK_SCHEDULE:
                                result = (
                                    await self.coordinator.client.api.set_home_load(
                                        siteId=siteId,
                                        deviceSn=self._context_base,
                                        set_slot=slot,
                                        test_schedule=data.get("schedule") or {}
                                        if self.coordinator.client.testmode()
                                        else None,
                                    )
                                )
                            elif service_name == SERVICE_UPDATE_SOLARBANK_SCHEDULE:
                                result = (
                                    await self.coordinator.client.api.set_home_load(
                                        siteId=siteId,
                                        deviceSn=self._context_base,
                                        insert_slot=slot,
                                        test_schedule=data.get("schedule") or {}
                                        if self.coordinator.client.testmode()
                                        else None,
                                    )
                                )
                            else:
                                result = False

                        # log resulting schedule if testmode returned dict
                        if (
                            isinstance(result, dict)
                            and self.coordinator.client.testmode()
                        ):
                            LOGGER.info(
                                "TESTMODE ONLY: Resulting schedule to be applied:\n%s",
                                json.dumps(result, indent=2),
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
                            f"The service {service_name} cannot be executed: {'start_time must be earlier than end_time'}.",
                            translation_domain=DOMAIN,
                            translation_key="slot_time_error",
                            translation_placeholders={
                                "service": service_name,
                                "error": "start_time must be earlier than end_time",
                            },
                        )
                else:
                    raise ServiceValidationError(
                        f"The service {service_name} cannot be executed: {'start_time or end_time missing'}.",
                        translation_domain=DOMAIN,
                        translation_key="slot_time_error",
                        translation_placeholders={
                            "service": service_name,
                            "error": "start_time or end_time missing",
                        },
                    )

            elif service_name in [SERVICE_GET_SOLARBANK_SCHEDULE]:
                LOGGER.debug("%s service will be applied", service_name)
                if generation > 1 and (schedule := data.get("schedule") or {}):
                    # get SB2 schedule
                    result = (
                        await self.coordinator.client.api.get_device_parm(
                            siteId=siteId,
                            paramType=SolixParmType.SOLARBANK_2_SCHEDULE.value,
                            deviceSn=self._context_base,
                            fromFile=self.coordinator.client.testmode(),
                        )
                    ).get("param_data")
                else:
                    result = (
                        await self.coordinator.client.api.get_device_load(
                            siteId=siteId,
                            deviceSn=self._context_base,
                            fromFile=self.coordinator.client.testmode(),
                        )
                    ).get("home_load_data")
                # trigger coordinator update with api dictionary data
                await self.coordinator.async_refresh_data_from_apidict()
                return {"schedule": result}

            elif service_name in [SERVICE_CLEAR_SOLARBANK_SCHEDULE]:
                LOGGER.debug("%s service will be applied", service_name)
                if generation > 1:
                    # Clear SB2 schedule
                    if schedule := data.get("schedule") or {}:
                        weekdays = kwargs.get(WEEK_DAYS)
                        if weekdays == cv.ENTITY_MATCH_NONE:
                            weekdays = None
                        result = await self.coordinator.client.api.set_sb2_home_load(
                            siteId=siteId,
                            deviceSn=self._context_base,
                            set_slot=Solarbank2Timeslot(
                                start_time=None,
                                end_time=None,
                                weekdays=set(weekdays) if weekdays else None,
                            ),
                            test_schedule=schedule
                            if self.coordinator.client.testmode()
                            else None,
                        )
                        # log resulting schedule if testmode returned dict
                        if (
                            isinstance(result, dict)
                            and self.coordinator.client.testmode()
                        ):
                            LOGGER.info(
                                "TESTMODE ONLY: Resulting schedule to be applied:\n%s",
                                json.dumps(result, indent=2),
                            )
                else:
                    # clear SB 1 schedule
                    schedule = {"ranges": []}
                    if self.coordinator.client.testmode():
                        LOGGER.info(
                            "TESTMODE ONLY: Resulting schedule to be applied:\n%s",
                            json.dumps(schedule, indent=2),
                        )
                    else:
                        await self.coordinator.client.api.set_device_parm(
                            siteId=siteId,
                            paramData=schedule,
                            deviceSn=self._context_base,
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
                    f"The entity {self.entity_id} does not support the service {service_name}",
                    translation_domain=DOMAIN,
                    translation_key="service_not_supported",
                    translation_placeholders={
                        "entity": self.entity_id,
                        "service": service_name,
                    },
                )
        return None


class AnkerSolixEnergySensor(AnkerSolixSensor, RestoreSensor):
    """Represents an energy sensor entity for Anker Solix site and device data."""

    _last_period: str | None = None
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
        # Important to set last known value to None to not mess with long term stats
        self._last_known_value = None

    def schedule_midnight_reset(self, reset_sensor_value: bool = True):
        """Schedule the reset function to run again at the next midnight."""
        now = datetime.now().astimezone()
        midnight = (
            datetime.now()
            .astimezone()
            .replace(hour=0, minute=0, second=0, microsecond=0)
        )
        midnight = midnight + timedelta(days=1) if now > midnight else midnight
        time_until_midnight = (midnight - datetime.now().astimezone()).total_seconds()

        if reset_sensor_value:
            self.reset_sensor_value()
        self.hass.loop.call_later(time_until_midnight, self.schedule_midnight_reset)

    def reset_sensor_value(self):
        """Reset the sensor value."""
        self._last_known_value = 0

    @property
    def native_value(self):
        """Return the native value of the sensor."""
        super_native_value = super().native_value
        # For an energy sensor a value of 0 would mess up long term stats because of how total_increasing works
        if super_native_value == 0.0:
            LOGGER.debug(
                "Returning last known value instead of 0.0 for %s to avoid resetting total_increasing counter",
                self.name,
            )
            self._assumed_state = True
            return self._last_known_value
        self._last_known_value = super_native_value
        self._assumed_state = False
        return super_native_value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the sensor."""
        if self.entity_description.reset_at_midnight:
            last_reset = None
            if hasattr(self, "_attr_last_reset"):
                last_reset = self._attr_last_reset.isoformat()
            return {
                LAST_PERIOD: self._last_period,
                LAST_RESET: last_reset,
            }
        if (
            self.coordinator
            and (hasattr(self.coordinator, "data"))
            and self._context_base in self.coordinator.data
        ):
            data = self.coordinator.data.get(self._context_base)
            with suppress(ValueError, TypeError):
                self._attr_extra_state_attributes = self.entity_description.attrib_fn(
                    data, self.coordinator_context
                )
        return self._attr_extra_state_attributes

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        await super().async_added_to_hass()

        state = await self.async_get_last_sensor_data()
        if state:
            self._last_known_value = state.native_value

        if self.entity_description.reset_at_midnight:
            self.schedule_midnight_reset(reset_sensor_value=False)
