"""Sensor platform for anker_solix."""
from __future__ import annotations  # noqa: I001

from dataclasses import dataclass
from datetime import datetime, timedelta
from collections.abc import Callable
from contextlib import suppress
import os
from random import randrange, choice
from typing import Any
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_platform
import homeassistant.helpers.config_validation as cv

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
    TEST_NUMBERVARIANCE,
    LAST_PERIOD,
    LAST_RESET,
    SERVICE_GET_SOLARBANK_SCHEDULE,
    SERVICE_SET_SOLARBANK_SCHEDULE,
    SERVICE_UPDATE_SOLARBANK_SCHEDULE,
    SOLARBANK_ENTITY_SCHEMA,
    SOLARBANK_TIMESLOT_SCHEMA,
    START_TIME,
    END_TIME,
    ALLOW_EXPORT,
    APPLIANCE_LOAD,
    CHARGE_PRIORITY_LIMIT,
)
from .coordinator import AnkerSolixDataUpdateCoordinator
from .solixapi.api import (
    SolarbankStatus,
    SolixDeviceStatus,
    SolixDeviceType,
    SolarbankTimeslot,
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
    nested_sensor: bool = False
    feature: AnkerSolixEntityFeature | None = None


DEVICE_SENSORS = [
    AnkerSolixSensorDescription(
        key="status_desc",
        translation_key="status_desc",
        json_key="status_desc",
        device_class=SensorDeviceClass.ENUM,
        options=[status.name for status in SolixDeviceStatus],  # noqa: C416
        attrib_fn=lambda d, _: {
            "status": d.get("status"),
        },
    ),
    AnkerSolixSensorDescription(
        key="charging_status_desc",
        translation_key="charging_status_desc",
        json_key="charging_status_desc",
        device_class=SensorDeviceClass.ENUM,
        options=[status.name for status in SolarbankStatus],  # noqa: C416
        attrib_fn=lambda d, _: {"charging_status": d.get("charging_status")},
    ),
    AnkerSolixSensorDescription(
        key="charging_power",
        translation_key="charging_power",
        json_key="charging_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    AnkerSolixSensorDescription(
        key="input_power",
        translation_key="input_power",
        json_key="input_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    AnkerSolixSensorDescription(
        key="output_power",
        translation_key="output_power",
        json_key="output_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    AnkerSolixSensorDescription(
        key="ac_generate_power",
        translation_key="ac_generate_power",
        json_key="generate_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    AnkerSolixSensorDescription(
        # Output preset per device
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
        # Force the creation for solarbanks, this could be empty if disconnected?
        force_creation_fn=lambda d: bool(
            d.get("type") == SolixDeviceType.SOLARBANK.value
        ),
    ),
    AnkerSolixSensorDescription(
        key="state_of_charge",
        translation_key="state_of_charge",
        json_key="battery_soc",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
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
    ),
    AnkerSolixSensorDescription(
        key="bws_surplus",
        translation_key="bws_surplus",
        json_key="bws_surplus",
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    AnkerSolixSensorDescription(
        key="temperature",
        translation_key="temperature",
        json_key="temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    AnkerSolixSensorDescription(
        key="sw_version",
        translation_key="sw_version",
        json_key="sw_version",
        entity_category=EntityCategory.DIAGNOSTIC,
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
    ),
    AnkerSolixSensorDescription(
        key="daily_discharge_energy",
        translation_key="daily_discharge_energy",
        json_key="solarbank_discharge",
        state_class=SensorStateClass.TOTAL,
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
    ),
    AnkerSolixSensorDescription(
        key="daily_charge_energy",
        translation_key="daily_charge_energy",
        json_key="solarbank_charge",
        state_class=SensorStateClass.TOTAL,
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
    ),
    AnkerSolixSensorDescription(
        key="daily_solar_production",
        translation_key="daily_solar_production",
        json_key="solar_production",
        state_class=SensorStateClass.TOTAL,
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
    ),
    AnkerSolixSensorDescription(
        key="solar_list",
        translation_key="solar_list",
        json_key="solar_list",
        picture_path=AnkerSolixPicturePath.INVERTER,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d, jk, _: len(list(d.get(jk) or [])),
        force_creation_fn=lambda d: True,
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
    ),
    AnkerSolixSensorDescription(
        # timestamp of solabank data
        key="solarbank_timestamp",
        translation_key="solarbank_timestamp",
        json_key="updated_time",
        # value_fn=lambda d, jk, _: datetime.strptime((d.get("solarbank_info") or {}).get(jk), "%Y-%m-%d %H:%M:%S").astimezone().isoformat(),
        value_fn=lambda d, jk, _: (d.get("solarbank_info") or {}).get(jk),
    ),
    AnkerSolixSensorDescription(
        # Summary of all pps charging power on site
        key="pps_charging_power",
        translation_key="pps_charging_power",
        json_key="total_charging_power",
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d, jk, _: (d.get("pps_info") or {}).get(jk),
        suggested_display_precision=0,
    ),
    AnkerSolixSensorDescription(
        # Summary of all pps output power on site
        key="pps_output_power",
        translation_key="pps_output_power",
        json_key="total_output_power",
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d, jk, _: (d.get("pps_info") or {}).get(jk),
        suggested_display_precision=0,
    ),
    AnkerSolixSensorDescription(
        # Summary of all pps state of charge on site
        key="pps_state_of_charge",
        translation_key="pps_state_of_charge",
        json_key="total_battery_power",
        entity_registry_enabled_default=False,
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d, jk, _: 100 * float((d.get("pps_info") or {}).get(jk)),
        suggested_display_precision=0,
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
        device_class=SensorDeviceClass.MONETARY,
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
                for sn in (
                    serial
                    for serial in sn_list
                    if bool(CREATE_ALL_ENTITIES)
                    or description.force_creation_fn(data)
                    or description.value_fn(data, description.json_key, serial)
                    is not None
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
        name=SERVICE_GET_SOLARBANK_SCHEDULE,
        schema=SOLARBANK_ENTITY_SCHEMA,
        func=SERVICE_GET_SOLARBANK_SCHEDULE,
        required_features=[AnkerSolixEntityFeature.SOLARBANK_SCHEDULE],
        supports_response=SupportsResponse.ONLY,
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
        wwwroot = os.path.join(self.coordinator.hass.config.config_dir, "www")
        if description.picture_path and os.path.isfile(
            description.picture_path.replace(AnkerSolixPicturePath.LOCALPATH, wwwroot)
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
            if self._attr_entity_picture and not os.path.isfile(
                self._attr_entity_picture.replace(
                    AnkerSolixPicturePath.LOCALPATH, wwwroot
                )
            ):
                self._attr_entity_picture = None

        else:
            # get the site info data from site context entry of coordinator data
            data = (coordinator.data.get(self._context_base, {})).get("site_info", {})
            self._attr_device_info = get_AnkerSolixSystemInfo(data, self._context_base)
            # add service attribute for managble sites
            self._attr_supported_features: AnkerSolixEntityFeature = (
                description.feature if data.get("site_admin", False) else None
            )

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
    async def get_solarbank_schedule(self, **kwargs: Any) -> None:
        """Get the active solarbank schedule from the api."""
        return await self._solarbank_schedule_service(
            service_name=SERVICE_GET_SOLARBANK_SCHEDULE, **kwargs
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

    async def _solarbank_schedule_service(
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
        # When running in Test mode do not run service
        if self.coordinator.client.testmode() and service_name not in [
            SERVICE_GET_SOLARBANK_SCHEDULE
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
            data = self.coordinator.data.get(self._context_base)
            if service_name in [
                SERVICE_SET_SOLARBANK_SCHEDULE,
                SERVICE_UPDATE_SOLARBANK_SCHEDULE,
            ]:
                if START_TIME in kwargs and END_TIME in kwargs:
                    if (start_time := kwargs.get(START_TIME)) < (
                        end_time := kwargs.get(END_TIME)
                    ):
                        load = kwargs.get(APPLIANCE_LOAD)
                        if load == cv.ENTITY_MATCH_NONE:
                            load = None
                        export = kwargs.get(ALLOW_EXPORT)
                        if export == cv.ENTITY_MATCH_NONE:
                            export = None
                        prio = kwargs.get(CHARGE_PRIORITY_LIMIT)
                        if prio == cv.ENTITY_MATCH_NONE:
                            prio = None
                        # check if now is in given time range and ensure preset increase is limited by min interval
                        now = datetime.now().astimezone()
                        start_time.astimezone()
                        if (
                            self._last_schedule_service_value
                            and load
                            and load > int(self._last_schedule_service_value)
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
                                load,
                                _SCAN_INTERVAL_MIN,
                            )
                            # Raise alert to frontend
                            raise ServiceValidationError(
                                f"{self.entity_id} cannot be increased to {load} because minimum change delay of {_SCAN_INTERVAL_MIN} seconds is not passed",
                                translation_domain=DOMAIN,
                                translation_key="increase_blocked",
                                translation_placeholders={
                                    "entity_id": self.entity_id,
                                    "value": load,
                                    "delay": _SCAN_INTERVAL_MIN,
                                },
                            )

                        LOGGER.debug("%s service will be applied", service_name)
                        # Map service keys to api slot keys
                        slot = SolarbankTimeslot(
                            start_time=start_time,
                            end_time=end_time,
                            appliance_load=load,
                            allow_export=export,
                            charge_priority_limit=prio,
                        )
                        if service_name == SERVICE_SET_SOLARBANK_SCHEDULE:
                            result = await self.coordinator.client.api.set_home_load(
                                siteId=data.get("site_id") or "",
                                deviceSn=self._context_base,
                                set_slot=slot,
                            )
                        elif service_name == SERVICE_UPDATE_SOLARBANK_SCHEDULE:
                            result = await self.coordinator.client.api.set_home_load(
                                siteId=data.get("site_id") or "",
                                deviceSn=self._context_base,
                                insert_slot=slot,
                            )
                        else:
                            result = False
                        if result:
                            self._last_schedule_service_value = load or None
                        # trigger coordinator update with api dictionary data
                        await self.coordinator.async_refresh_data_from_apidict()
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
                result = await self.coordinator.client.api.get_device_load(
                    siteId=data.get("site_id") or "",
                    deviceSn=self._context_base,
                    fromFile=self.coordinator.client.testmode(),
                )
                # trigger coordinator update with api dictionary data
                await self.coordinator.async_refresh_data_from_apidict()
                return {"schedule": result.get("home_load_data")}


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
        # Reset only if sensor has value to avoid mess up long term stats because of how total_increasing works
        if self._last_known_value:
            self._last_period = self._last_known_value
            self._last_known_value = 0
            self._attr_last_reset = datetime.now().astimezone()

    @property
    def native_value(self):
        """Return the native value of the sensor."""
        super_native_value = super().native_value
        # For an energy sensor a value of 0 would mess up long term stats because of how total_increasing works
        if super_native_value == 0.0:
            LOGGER.info(
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
