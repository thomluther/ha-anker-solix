"""Number platform for anker_solix."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from typing import Any

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
    RestoreNumber,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_EXCLUDE,
    PERCENTAGE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfEnergy,
    UnitOfEnergyDistance,
    UnitOfPower,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .config_flow import _SCAN_INTERVAL_MIN
from .const import (
    ALLOW_TESTMODE,
    ATTRIBUTION,
    CREATE_ALL_ENTITIES,
    DOMAIN,
    LOGGER,
    MQTT_OVERLAY,
)
from .coordinator import AnkerSolixDataUpdateCoordinator
from .entity import (
    AnkerSolixEntityRequiredKeyMixin,
    AnkerSolixEntityType,
    get_AnkerSolixAccountInfo,
    get_AnkerSolixDeviceInfo,
    get_AnkerSolixSubdeviceInfo,
    get_AnkerSolixSystemInfo,
    get_AnkerSolixVehicleInfo,
)
from .solixapi.apitypes import ApiCategories, SolixDefaults, SolixDeviceType
from .solixapi.helpers import round_by_factor
from .solixapi.mqtt_device import SolixMqttDevice
from .solixapi.mqttcmdmap import VALUE_MAX, VALUE_MIN, VALUE_STEP, SolixMqttCommands


@dataclass(frozen=True)
class AnkerSolixNumberDescription(
    NumberEntityDescription, AnkerSolixEntityRequiredKeyMixin
):
    """Number entity description with optional keys."""

    restore: bool = False
    mqtt: bool = False
    mqtt_cmd: str | None = None
    mqtt_cmd_parm: str | None = None
    # Use optionally to provide function for value calculation or lookup of nested values
    value_fn: Callable[[dict, str], StateType] = lambda d, jk: d.get(jk)
    unit_fn: Callable[[dict], str | None] = lambda d: None
    attrib_fn: Callable[[dict, str], dict | None] = lambda d, ctx: None
    exclude_fn: Callable[[set, dict], bool] = lambda s, d: False
    force_creation_fn: Callable[[dict, str], bool] = lambda d, jk: False


DEVICE_NUMBERS = [
    AnkerSolixNumberDescription(
        # System total output setting, determined by schedule, the limits will be adopted during creation
        key="preset_system_output_power",
        translation_key="preset_system_output_power",
        json_key="preset_system_output_power",
        mode=NumberMode.BOX,
        native_min_value=SolixDefaults.PRESET_MIN,
        native_max_value=SolixDefaults.PRESET_MAX,
        native_step=10,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=NumberDeviceClass.POWER,
        exclude_fn=lambda s, d: not (
            {d.get("type")} - s
            and (not (sn := d.get("station_sn")) or sn == d.get("device_sn"))
        ),
        force_creation_fn=lambda d, jk: jk in d,
    ),
    AnkerSolixNumberDescription(
        # Device output setting, determined by schedule
        key="preset_device_output_power",
        translation_key="preset_device_output_power",
        json_key="preset_device_output_power",
        mode=NumberMode.BOX,
        native_min_value=SolixDefaults.PRESET_MIN,
        native_max_value=SolixDefaults.PRESET_MAX,
        native_step=5,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=NumberDeviceClass.POWER,
        exclude_fn=lambda s, d: not (
            {d.get("type")} - s
            and (not (sn := d.get("station_sn")) or sn == d.get("device_sn"))
        ),
        force_creation_fn=lambda d, jk: jk in d,
    ),
    AnkerSolixNumberDescription(
        # Charge Priority level to use for schedule slot
        key="preset_charge_priority",
        translation_key="preset_charge_priority",
        json_key="preset_charge_priority",
        mode=NumberMode.SLIDER,
        native_min_value=SolixDefaults.CHARGE_PRIORITY_MIN,
        native_max_value=SolixDefaults.CHARGE_PRIORITY_MAX,
        native_step=5,
        native_unit_of_measurement=PERCENTAGE,
        device_class=NumberDeviceClass.BATTERY,
        exclude_fn=lambda s, _: not ({SolixDeviceType.SOLARBANK.value} - s),
        force_creation_fn=lambda d, jk: jk in d,
    ),
    AnkerSolixNumberDescription(
        # Defined tariff price for energy saving calculations by cloud
        key="preset_tariff_price",
        translation_key="preset_tariff_price",
        json_key="preset_tariff_price",
        unit_fn=lambda d: d.get("preset_tariff_currency"),
        device_class=NumberDeviceClass.MONETARY,
        native_min_value=0,
        native_max_value=1000,
        native_step=0.01,
        exclude_fn=lambda s, d: not (
            {d.get("type")} - s
            and (not (sn := d.get("station_sn")) or sn == d.get("device_sn"))
        ),
    ),
    AnkerSolixNumberDescription(
        # Customizable installed battery capacity
        key="battery_capacity",
        translation_key="battery_capacity",
        json_key="battery_capacity",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=NumberDeviceClass.ENERGY_STORAGE,
        native_min_value=1,
        native_max_value=100000,
        native_step=1,
        mode=NumberMode.BOX,
        value_fn=lambda d, jk: (d.get("customized") or {}).get(jk) or d.get(jk),
        attrib_fn=lambda d, _: {
            "expansions": d.get("sub_package_num"),
            "calculated": d.get("battery_capacity"),
        }
        | (
            {"customized": c}
            if (c := (d.get("customized") or {}).get("battery_capacity"))
            else {}
        ),
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        restore=True,
    ),
    AnkerSolixNumberDescription(
        key="ac_output_timeout",
        translation_key="ac_output_timeout",
        json_key="ac_output_timeout_seconds",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=NumberDeviceClass.DURATION,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
        mqtt_cmd=SolixMqttCommands.ac_output_timeout_seconds,
    ),
    AnkerSolixNumberDescription(
        key="dc_output_timeout",
        translation_key="dc_output_timeout",
        json_key="dc_output_timeout_seconds",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=NumberDeviceClass.DURATION,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
        mqtt_cmd=SolixMqttCommands.dc_output_timeout_seconds,
    ),
    AnkerSolixNumberDescription(
        key="preset_ac_input_limit",
        translation_key="preset_ac_input_limit",
        json_key="ac_input_limit",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=NumberDeviceClass.POWER,
        exclude_fn=lambda s, d: not ({d.get("type")} - s and d.get("mqtt_data")),
        mqtt=True,
        mqtt_cmd=SolixMqttCommands.ac_charge_limit,
    ),
    AnkerSolixNumberDescription(
        key="grid_export_limit",
        translation_key="grid_export_limit",
        json_key="grid_export_limit",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=NumberDeviceClass.POWER,
        exclude_fn=lambda s, d: not (
            {d.get("type")} - s
            and d.get("mqtt_data")
            and (not (sn := d.get("station_sn")) or sn == d.get("device_sn"))
        ),
        mqtt=True,
        mqtt_cmd=SolixMqttCommands.sb_disable_grid_export_switch,
        mqtt_cmd_parm="set_grid_export_limit",
    ),
]

SITE_NUMBERS = [
    AnkerSolixNumberDescription(
        # Defined Site price for energy saving calculations by cloud
        key="system_price",
        translation_key="system_price",
        json_key="price",
        unit_fn=lambda d: (d.get("site_details") or {}).get("site_price_unit"),
        # device_class=NumberDeviceClass.MONETARY,
        value_fn=lambda d, jk: (d.get("site_details") or {}).get(jk),
        native_min_value=0,
        native_max_value=1000,
        native_step=0.00001,
        mode=NumberMode.BOX,
        exclude_fn=lambda s, _: not ({ApiCategories.site_price} - s),
    ),
    AnkerSolixNumberDescription(
        key="dynamic_price_fee",
        translation_key="dynamic_price_fee",
        json_key="dynamic_price_fee",
        # device_class=NumberDeviceClass.MONETARY,
        unit_fn=lambda d: (
            (d.get("site_details") or {}).get("dynamic_price_details") or {}
        ).get("spot_price_unit"),
        value_fn=lambda d, jk: (
            (d.get("site_details") or {}).get("dynamic_price_details") or {}
        ).get(jk)
        or None,
        attrib_fn=lambda d, _: {"customized": c}
        if (c := (d.get("customized") or {}).get("dynamic_price_fee"))
        else {},
        native_min_value=0,
        native_max_value=100,
        native_step=0.0001,
        mode=NumberMode.BOX,
        exclude_fn=lambda s, d: not ({ApiCategories.site_price} - s),
        force_creation_fn=lambda d, _: bool(
            "dynamic_price_details" in (d.get("site_details") or {})
        ),
        restore=True,
    ),
    AnkerSolixNumberDescription(
        key="dynamic_price_vat",
        translation_key="dynamic_price_vat",
        json_key="dynamic_price_vat",
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d, jk: (
            (d.get("site_details") or {}).get("dynamic_price_details") or {}
        ).get(jk)
        or None,
        attrib_fn=lambda d, _: {"customized": c}
        if (c := (d.get("customized") or {}).get("dynamic_price_vat"))
        else {},
        native_min_value=0,
        native_max_value=100,
        native_step=0.01,
        mode=NumberMode.BOX,
        exclude_fn=lambda s, d: not ({ApiCategories.site_price} - s),
        force_creation_fn=lambda d, _: bool(
            "dynamic_price_details" in (d.get("site_details") or {})
        ),
        restore=True,
    ),
]

ACCOUNT_NUMBERS = []

VEHICLE_NUMBERS = [
    AnkerSolixNumberDescription(
        key="battery_capacity",
        translation_key="battery_capacity",
        json_key="battery_capacity",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=NumberDeviceClass.ENERGY_STORAGE,
        native_min_value=1,
        native_max_value=1000,
        native_step=0.1,
        mode=NumberMode.BOX,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
    ),
    AnkerSolixNumberDescription(
        key="ac_max_charging_power",
        translation_key="ac_max_charging_power",
        json_key="ac_max_charging_power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=NumberDeviceClass.POWER,
        native_min_value=1,
        native_max_value=1000,
        native_step=0.1,
        mode=NumberMode.BOX,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
    ),
    AnkerSolixNumberDescription(
        key="energy_consumption_per_100km",
        translation_key="energy_consumption_per_100km",
        json_key="energy_consumption_per_100km",
        native_unit_of_measurement=UnitOfEnergyDistance.KILO_WATT_HOUR_PER_100_KM,
        device_class=NumberDeviceClass.ENERGY_DISTANCE,
        native_min_value=1,
        native_max_value=100,
        native_step=0.1,
        mode=NumberMode.BOX,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number platform."""

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
                entity_list = SITE_NUMBERS
            elif data_type == SolixDeviceType.ACCOUNT.value:
                # Unique key for account entry in data
                entity_type = AnkerSolixEntityType.ACCOUNT
                entity_list = ACCOUNT_NUMBERS
            elif data_type == SolixDeviceType.VEHICLE.value:
                # vehicle entry in data
                entity_type = AnkerSolixEntityType.VEHICLE
                entity_list = VEHICLE_NUMBERS
            else:
                # device_sn entry in data
                entity_type = AnkerSolixEntityType.DEVICE
                entity_list = DEVICE_NUMBERS
                # get MQTT device combined values for creation of entities
                if mdev := coordinator.client.get_mqtt_device(sn=context):
                    mdata = mdev.get_combined_cache(
                        fromFile=coordinator.client.testmode()
                    )

            for description in (
                desc
                for desc in entity_list
                if bool(CREATE_ALL_ENTITIES)
                or (
                    not desc.exclude_fn(set(entry.options.get(CONF_EXCLUDE, [])), data)
                    and (
                        desc.force_creation_fn(data, desc.json_key)
                        # filter MQTT entities and provide combined or only api cache
                        # Entities that should not be created without MQTT data need to use exclude option
                        or (
                            desc.mqtt
                            and desc.value_fn(mdata or data, desc.json_key) is not None
                            # include command number entities only if more than 20 options
                            and not (
                                mdev
                                and desc.mqtt_cmd
                                and (
                                    mdev.get_cmd_parm_option_map(
                                        cmd=desc.mqtt_cmd,
                                        parm=desc.mqtt_cmd_parm,
                                        limit=20,
                                    )
                                    or not mdev.cmd_is_number(
                                        cmd=desc.mqtt_cmd, parm=desc.mqtt_cmd_parm
                                    )
                                )
                            )
                        )
                        # filter API only entities
                        or (
                            not desc.mqtt
                            and desc.value_fn(data, desc.json_key) is not None
                        )
                    )
                )
            ):
                if description.restore:
                    entity = AnkerSolixRestoreNumber(
                        coordinator, description, context, entity_type
                    )
                else:
                    entity = AnkerSolixNumber(
                        coordinator, description, context, entity_type
                    )
                entities.append(entity)

    # create the entities from the list
    async_add_entities(entities)


class AnkerSolixNumber(CoordinatorEntity, NumberEntity):
    """anker_solix number class."""

    coordinator: AnkerSolixDataUpdateCoordinator
    entity_description: AnkerSolixNumberDescription
    _attr_has_entity_name = True
    _unrecorded_attributes = frozenset(
        {
            "expansions",
            "schedule",
            "calculated",
            "customized",
        }
    )

    def __init__(
        self,
        coordinator: AnkerSolixDataUpdateCoordinator,
        description: AnkerSolixNumberDescription,
        context: str,
        entity_type: str,
    ) -> None:
        """Initialize the number class."""
        super().__init__(coordinator, context)

        self._attribute_name = description.key
        self._attr_attribution = f"{ATTRIBUTION}{' + MQTT' if description.mqtt else ''}"
        self._attr_unique_id = (f"{context}_{description.key}").lower()
        self.entity_description = description
        self.entity_type = entity_type
        self.last_changed: datetime | None = None
        self._attr_extra_state_attributes = None

        if self.entity_type == AnkerSolixEntityType.DEVICE:
            # get the device data from device context entry of coordinator data
            data: dict = coordinator.data.get(context) or {}
            if data.get("is_subdevice"):
                self._attr_device_info = get_AnkerSolixSubdeviceInfo(
                    data, context, data.get("main_sn")
                )
            else:
                self._attr_device_info = get_AnkerSolixDeviceInfo(
                    data, context, coordinator.client.api.apisession.email
                )
            # Setup number ranges for MQTT command numbers
            if self.entity_description.mqtt_cmd and (
                mdev := self.coordinator.client.get_mqtt_device(context)
            ):
                # first get parameter description
                if self.entity_description.mqtt_cmd_parm:
                    desc = mdev.get_cmd_parms(
                        cmd=self.entity_description.mqtt_cmd, all=True
                    ).get(self.entity_description.mqtt_cmd_parm, {})
                else:
                    desc = next(
                        iter(
                            mdev.get_cmd_parms(
                                cmd=self.entity_description.mqtt_cmd
                            ).values()
                        ),
                        {},
                    )
                # define number range from control description
                if self._attribute_name in ["ac_output_timeout", "dc_output_timeout"]:
                    # convert seconds to minutes
                    self.native_min_value = (
                        round(num / 60)
                        if isinstance(num := desc.get(VALUE_MIN), float | int)
                        else None
                    )
                    self.native_max_value = (
                        round(num / 60)
                        if isinstance(num := desc.get(VALUE_MAX), float | int)
                        else None
                    )
                    self.native_step = (
                        round(num / 60)
                        if isinstance(num := desc.get(VALUE_STEP), float | int)
                        else None
                    )
                else:
                    self.native_min_value = desc.get(VALUE_MIN)
                    self.native_max_value = desc.get(VALUE_MAX)
                    self.native_step = desc.get(VALUE_STEP)
        elif self.entity_type == AnkerSolixEntityType.ACCOUNT:
            # get the account data from account context entry of coordinator data
            data = coordinator.data.get(context) or {}
            self._attr_device_info = get_AnkerSolixAccountInfo(data, context)
        elif self.entity_type == AnkerSolixEntityType.VEHICLE:
            # get the vehicle info data from vehicle entry of coordinator data
            data = coordinator.data.get(context) or {}
            self._attr_device_info = get_AnkerSolixVehicleInfo(
                data, context, coordinator.client.api.apisession.email
            )
        else:
            # get the site info data from site context entry of coordinator data
            data: dict = (coordinator.data.get(context, {})).get("site_info") or {}
            self._attr_device_info = get_AnkerSolixSystemInfo(
                data, context, coordinator.client.api.apisession.email
            )

        self._native_value = None
        self._assumed_state = False
        self.update_state_value()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.update_state_value()
        super()._handle_coordinator_update()

    @property
    def native_value(self):
        """Return the native value of the number entity."""
        return self._native_value

    @property
    def assumed_state(self):
        """Return the assumed state of the entity."""
        return self._assumed_state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the number entity."""
        if (
            self.coordinator
            and (hasattr(self.coordinator, "data"))
            and self.coordinator_context in self.coordinator.data
        ):
            # Api device data
            data = self.coordinator.data.get(self.coordinator_context)
            if self.entity_description.mqtt and (
                mdev := self.coordinator.client.get_mqtt_device(
                    self.coordinator_context
                )
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

    def update_state_value(self):
        """Update the state value of the number based on the coordinator data."""
        if self.coordinator and self.coordinator_context in self.coordinator.data:
            # Api device data
            data = self.coordinator.data.get(self.coordinator_context)
            if self.entity_description.mqtt and (
                mdev := self.coordinator.client.get_mqtt_device(
                    self.coordinator_context
                )
            ):
                # Combined MQTT device data, overlay prio depends on customized setting
                data = mdev.get_combined_cache(
                    api_prio=not mdev.device.get(MQTT_OVERLAY),
                    fromFile=self.coordinator.client.testmode(),
                )
            key = self.entity_description.json_key
            with suppress(ValueError, TypeError):
                self._native_value = self.entity_description.value_fn(data, key)
                # get dynamic unit if defined
                if unit := self.entity_description.unit_fn(data):
                    self._attr_native_unit_of_measurement = unit
                # update number limits for presets based on solarbank count in system or active max
                if self._attribute_name == "preset_system_output_power":
                    if (
                        data.get("type") in [SolixDeviceType.COMBINER_BOX.value]
                        or (data.get("generation") or 0) >= 2
                    ):
                        # SB2 has min limit of 0W, they are typically correctly set in the schedule depending on device settings
                        self.native_min_value = (data.get("schedule") or {}).get(
                            "min_load"
                        ) or 0
                        self.native_max_value = (data.get("schedule") or {}).get(
                            "max_load"
                        ) or self.native_max_value
                    else:
                        # Use minimum from schedule fields (depends on defined interter)
                        self.native_min_value = (data.get("schedule") or {}).get(
                            "min_load"
                        ) or self.native_min_value
                        # SB1 max must consider multiple SB1 devices with MI80 inverter
                        # newer schedule limits could already contain adopted appliance limit instead of device limit
                        max_load = int(
                            (data.get("schedule") or {}).get("max_load")
                            or self.native_max_value
                        )
                        self.native_max_value = (
                            max_load
                            if max_load > SolixDefaults.PRESET_MAX
                            else int(
                                SolixDefaults.PRESET_MAX
                                * (data.get("solarbank_count") or 1),
                            )
                        )
                elif self._attribute_name == "preset_device_output_power":
                    # Multiple SB1 with device setting only supported for MI80 whose limits apply
                    self.native_min_value = int(
                        (
                            (data.get("schedule") or {}).get("min_load")
                            or self.native_min_value
                        )
                        / (data.get("solarbank_count") or 1)
                    )
                    self.native_max_value = max(
                        SolixDefaults.PRESET_MAX,
                        int(
                            (
                                (data.get("schedule") or {}).get("max_load")
                                or self.native_max_value
                            )
                            / (data.get("solarbank_count") or 1)
                        ),
                    )
                # convert seconds to minutes
                elif self._attribute_name in ["ac_output_timeout", "dc_output_timeout"]:
                    if self._native_value is not None:
                        self._native_value = round(self._native_value / 60)
        else:
            self._native_value = None
        self._assumed_state = False
        # Mark availability based on value
        self._attr_available = self._native_value is not None

    async def async_set_native_value(self, value: float) -> None:  # noqa: C901
        """Set the native value of the number entity.

        Args:
            value (float): The value to set.

        """
        if (
            self.coordinator.client.testmode()
            and self._attribute_name
            not in [
                "preset_system_output_power",
                "preset_device_output_power",
                "preset_charge_priority",
                "preset_tariff_price",
                "system_price",
                "battery_capacity",
                "ac_max_charging_power",
                "energy_consumption_per_100km",
            ]
            and not self.entity_description.restore
            and not self.entity_description.mqtt_cmd
        ):
            # Raise alert to frontend
            raise ServiceValidationError(
                f"'{self.entity_id}' cannot be used while configuration is running in testmode",
                translation_domain=DOMAIN,
                translation_key="active_testmode",
                translation_placeholders={
                    "entity_id": self.entity_id,
                },
            )
        if (
            self.coordinator
            and self.coordinator_context in self.coordinator.data
            and (self._native_value is not None or self.entity_description.restore)
        ):
            data = self.coordinator.data.get(self.coordinator_context) or {}
            if self.min_value <= value <= self.max_value:
                # round the number to the defined steps if set via service call
                if self.step:
                    value = round_by_factor(
                        self.step * round(value / self.step),
                        self.step,
                    )
                # Skip Api calls if value does not change
                if str(self._native_value).replace(".", "", 1).isdigit() and float(
                    value
                ) == float(self._native_value):
                    return
                # Wait until client cache is valid before applying any api change
                await self.coordinator.client.validate_cache()
                # Customize cache first if restore entity
                if self.entity_description.restore:
                    self.coordinator.client.api.customizeCacheId(
                        id=self.coordinator_context,
                        key=self.entity_description.json_key,
                        value=str(value),
                    )
                    if ALLOW_TESTMODE:
                        LOGGER.info(
                            "%s: State value of entity '%s' has been customized in Api cache to: %s",
                            "TESTMODE"
                            if self.coordinator.client.testmode()
                            else "LIVEMODE",
                            self.entity_id,
                            value,
                        )
                mdev = self.coordinator.client.get_mqtt_device(self.coordinator_context)
                # Trigger Api calls depending on changed entity
                if self._attribute_name in [
                    "preset_system_output_power",
                    "preset_device_output_power",
                ]:
                    # for increasing load value, change only if min delay passed
                    if (
                        (
                            (str(self._native_value).replace(".", "", 1).isdigit())
                            and value < int(self._native_value)
                        )
                        or not self.last_changed
                        or datetime.now().astimezone()
                        > self.last_changed + timedelta(seconds=_SCAN_INTERVAL_MIN)
                    ):
                        LOGGER.debug(
                            "'%s' change to %s will be applied", self.entity_id, value
                        )
                        siteId = data.get("site_id") or ""
                        if (
                            data.get("type") in [SolixDeviceType.COMBINER_BOX.value]
                            or (data.get("generation") or 0) >= 2
                        ):
                            # SB2 preset change
                            resp = await self.coordinator.client.api.set_sb2_home_load(
                                siteId=siteId,
                                deviceSn=self.coordinator_context,
                                preset=int(value),
                                toFile=self.coordinator.client.testmode(),
                            )
                            if isinstance(resp, dict) and ALLOW_TESTMODE:
                                LOGGER.info(
                                    "%s: Applied schedule for '%s' change to %s:\n%s",
                                    "TESTMODE"
                                    if self.coordinator.client.testmode()
                                    else "LIVEMODE",
                                    self.entity_id,
                                    value,
                                    json.dumps(
                                        resp,
                                        indent=2
                                        if len(json.dumps(resp)) < 200
                                        else None,
                                    ),
                                )
                        else:
                            # SB1 preset change
                            resp = await self.coordinator.client.api.set_home_load(
                                siteId=siteId,
                                deviceSn=self.coordinator_context,
                                preset=int(value)
                                if self._attribute_name == "preset_system_output_power"
                                else None,
                                dev_preset=int(value)
                                if self._attribute_name == "preset_device_output_power"
                                else None,
                                toFile=self.coordinator.client.testmode(),
                            )
                            if isinstance(resp, dict) and ALLOW_TESTMODE:
                                LOGGER.info(
                                    "%s: Applied schedule for '%s' change to %s:\n%s",
                                    "TESTMODE"
                                    if self.coordinator.client.testmode()
                                    else "LIVEMODE",
                                    self.entity_id,
                                    value,
                                    json.dumps(
                                        resp,
                                        indent=2
                                        if len(json.dumps(resp)) < 200
                                        else None,
                                    ),
                                )
                        # update sites was required to get applied output power fields, they are not provided with get_device_parm endpoint
                        # which fetches new schedule after update. Now the output power fields are updated along with a schedule update in the cache
                        # await self.coordinator.client.api.update_sites(
                        #     siteId=siteId,
                        #     fromFile=self.coordinator.client.testmode(),
                        # )
                        self.last_changed = datetime.now().astimezone()
                    else:
                        LOGGER.debug(
                            "'%s' cannot be increased to %s because minimum change delay of %s seconds is not passed",
                            self.entity_id,
                            value,
                            _SCAN_INTERVAL_MIN,
                        )
                        # Raise alert to frontend
                        raise ServiceValidationError(
                            f"'{self.entity_id}' cannot be increased to {value} because minimum change delay of {_SCAN_INTERVAL_MIN} seconds is not passed",
                            translation_domain=DOMAIN,
                            translation_key="increase_blocked",
                            translation_placeholders={
                                "entity_id": self.entity_id,
                                "value": value,
                                "delay": _SCAN_INTERVAL_MIN,
                            },
                        )
                elif self._attribute_name == "preset_charge_priority":
                    LOGGER.debug(
                        "'%s' change to %s will be applied", self.entity_id, value
                    )
                    resp = await self.coordinator.client.api.set_home_load(
                        siteId=data.get("site_id") or "",
                        deviceSn=self.coordinator_context,
                        charge_prio=int(value),
                        toFile=self.coordinator.client.testmode(),
                    )
                    if isinstance(resp, dict) and ALLOW_TESTMODE:
                        LOGGER.info(
                            "%s: Applied schedule for '%s' change to %s:\n%s",
                            "TESTMODE"
                            if self.coordinator.client.testmode()
                            else "LIVEMODE",
                            self.entity_id,
                            value,
                            json.dumps(
                                resp, indent=2 if len(json.dumps(resp)) < 200 else None
                            ),
                        )
                elif self._attribute_name == "preset_tariff_price":
                    LOGGER.debug(
                        "'%s' change to %s will be applied", self.entity_id, value
                    )
                    resp = await self.coordinator.client.api.set_sb2_use_time(
                        siteId=data.get("site_id") or "",
                        deviceSn=self.coordinator_context,
                        tariff_price=value,
                        # Ensure that only the tariff is changed without modification of slot times or clearance of tariff price
                        merge_tariff_slots=False,
                        clear_unused_tariff=False,
                        toFile=self.coordinator.client.testmode(),
                    )
                    if isinstance(resp, dict) and ALLOW_TESTMODE:
                        LOGGER.info(
                            "%s: Applied schedule for '%s' change to %s:\n%s",
                            "TESTMODE"
                            if self.coordinator.client.testmode()
                            else "LIVEMODE",
                            self.entity_id,
                            value,
                            json.dumps(
                                resp, indent=2 if len(json.dumps(resp)) < 200 else None
                            ),
                        )
                elif self._attribute_name == "system_price":
                    LOGGER.debug(
                        "'%s' change to %s will be applied", self.entity_id, value
                    )
                    if str(self.coordinator_context).startswith(
                        SolixDeviceType.VIRTUAL.value
                    ):
                        # change standalone inverter price of virtual system
                        resp = await self.coordinator.client.api.set_device_pv_price(
                            deviceSn=str(self.coordinator_context).split("-")[1],
                            price=round(float(value), 5),
                            toFile=self.coordinator.client.testmode(),
                        )
                    else:
                        # change real system price
                        resp = await self.coordinator.client.api.set_site_price(
                            siteId=self.coordinator_context,
                            price=round(float(value), 5),
                            toFile=self.coordinator.client.testmode(),
                        )
                    if isinstance(resp, dict) and ALLOW_TESTMODE:
                        LOGGER.info(
                            "%s: Applied site price settings:\n%s",
                            "TESTMODE"
                            if self.coordinator.client.testmode()
                            else "LIVEMODE",
                            json.dumps(
                                resp, indent=2 if len(json.dumps(resp)) < 200 else None
                            ),
                        )
                elif (
                    self._attribute_name
                    in [
                        "battery_capacity",
                        "ac_max_charging_power",
                        "energy_consumption_per_100km",
                    ]
                    and data.get("type") == SolixDeviceType.VEHICLE.value
                ):
                    LOGGER.debug(
                        "'%s' change to %s will be applied", self.entity_id, value
                    )
                    # change vehicle setting
                    resp = await self.coordinator.client.api.manage_vehicle(
                        vehicleId=self.coordinator_context,
                        action="update",
                        vehicle={self._attribute_name: value},
                        toFile=self.coordinator.client.testmode(),
                    )
                    if isinstance(resp, dict) and ALLOW_TESTMODE:
                        LOGGER.info(
                            "%s: Applied vehicle settings:\n%s",
                            "TESTMODE"
                            if self.coordinator.client.testmode()
                            else "LIVEMODE",
                            json.dumps(
                                resp, indent=2 if len(json.dumps(resp)) < 200 else None
                            ),
                        )
                elif self._attribute_name == "grid_export_limit":
                    LOGGER.debug(
                        "'%s' change to %s will be applied", self.entity_id, value
                    )
                    resp = None
                    if (
                        data.get("type") in [SolixDeviceType.COMBINER_BOX.value]
                        or data.get("station_sn") is not None
                    ):
                        # control station settings via Api
                        resp = await self.coordinator.client.api.set_station_parm(
                            deviceSn=self.coordinator_context,
                            gridExportLimit=int(value),
                            toFile=self.coordinator.client.testmode(),
                        )
                    # Control all solarbank devices via individual MQTT device setting
                    if siteId := data.get("site_id"):
                        stationSn = (
                            self.coordinator_context
                            if data.get("type") in [SolixDeviceType.COMBINER_BOX.value]
                            else data.get("station_sn", "")
                        )
                        for md in self.coordinator.client.get_mqtt_devices(
                            siteId=siteId,
                            stationSn=stationSn,
                            extraDeviceSn=self.coordinator_context,
                            mqttControl=self.entity_description.mqtt_cmd,
                        ):
                            resp = (resp or {}) | {
                                f"mqtt_control_{md.sn}": await self._async_mqtt_value(
                                    mdev=md,
                                    value=value,
                                    # use same export switch state for all devices, MQTT state is inverted
                                    parm_map={
                                        "set_disable_grid_export_switch": 0
                                        if mdev.device.get("allow_grid_export", True)
                                        else 1
                                    },
                                )
                            }
                    if isinstance(resp, dict) and ALLOW_TESTMODE:
                        LOGGER.info(
                            "%s: Applied settings for '%s' change to %s:\n%s",
                            "TESTMODE"
                            if self.coordinator.client.testmode()
                            else "LIVEMODE",
                            self.entity_id,
                            value,
                            json.dumps(
                                resp, indent=2 if len(json.dumps(resp)) < 200 else None
                            ),
                        )
                # Trigger MQTT commands depending on changed entity
                elif self.entity_description.mqtt_cmd and mdev:
                    LOGGER.debug(
                        "'%s' change to '%s' will be applied via MQTT command '%s'",
                        self.entity_id,
                        value,
                        self.entity_description.mqtt_cmd,
                    )
                    # convert seconds to minutes for dedicated entities
                    if self._attribute_name in [
                        "ac_output_timeout",
                        "dc_output_timeout",
                    ]:
                        value = round(value * 60)
                    await self._async_mqtt_value(mdev=mdev, value=value)
            else:
                LOGGER.debug(
                    "'%s' cannot be set because the value %s is out of range %s-%s",
                    self.entity_id,
                    value,
                    self.min_value,
                    self.max_value,
                )
                # Raise alert to frontend
                raise ServiceValidationError(
                    f"'{self.entity_id}' cannot be set to {value} because it is outside of allowed range {self.min_value}-{self.max_value}",
                    translation_domain=DOMAIN,
                    translation_key="out_of_range",
                    translation_placeholders={
                        "entity_id": self.entity_id,
                        "value": value,
                        "min": self.min_value,
                        "max": self.max_value,
                    },
                )
            # trigger coordinator update with api dictionary data
            await self.coordinator.async_refresh_data_from_apidict()

    async def _async_mqtt_value(
        self,
        mdev: SolixMqttDevice,
        value: Any,
        cmd: str | None = None,
        parm: str | None = None,
        parm_map: dict | None = None,
    ) -> dict | None:
        """Use MQTT device control to modify value setting."""
        resp = None
        if not isinstance(cmd, str):
            cmd = self.entity_description.mqtt_cmd
        if not isinstance(parm, str):
            parm = self.entity_description.mqtt_cmd_parm
        try:
            resp = await mdev.run_command(
                cmd=cmd,
                parm=parm,
                value=value,
                parm_map=parm_map,
                toFile=self.coordinator.client.testmode(),
            )
            if isinstance(resp, dict) and ALLOW_TESTMODE:
                LOGGER.info(
                    "%s: Applied MQTT command '%s' for '%s' change to '%s':\n%s",
                    "TESTMODE" if self.coordinator.client.testmode() else "LIVEMODE",
                    cmd,
                    self.entity_id,
                    str(value),
                    json.dumps(resp, indent=2 if len(json.dumps(resp)) < 200 else None),
                )
                # copy the changed state(s) of the mock response into device cache to avoid flip back of entity until real state is received
                for key, val in resp.items():
                    if key in mdev.mqttdata:
                        mdev.mqttdata[key] = val
                # trigger status request to get updated MQTT message
                await mdev.status_request(toFile=self.coordinator.client.testmode())
            else:
                LOGGER.error(
                    "'%s' value could not be changed via MQTT command '%s'",
                    self.entity_id,
                    cmd,
                )
        except (ValueError, TypeError) as err:
            LOGGER.error(
                "'%s' value could not be changed via MQTT command '%s':\n%s",
                self.entity_id,
                cmd,
                str(err),
            )
        return resp


class AnkerSolixRestoreNumber(AnkerSolixNumber, RestoreNumber):
    """anker_solix number class with restore capability."""

    def __init__(
        self,
        coordinator: AnkerSolixDataUpdateCoordinator,
        description: AnkerSolixNumberDescription,
        context: str,
        entity_type: str,
    ) -> None:
        """Initialize the number class."""
        super().__init__(coordinator, description, context, entity_type)
        self._assumed_state = True

    async def async_added_to_hass(self) -> None:
        """Load the last known state when added to hass."""
        await super().async_added_to_hass()
        if last_state := await self.async_get_last_state():
            # First try to get customization from state attributes if last state was unknown
            if last_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                if customized := last_state.attributes.get("customized"):
                    last_state.state = customized
            if (
                last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE)
                and self._native_value is not None
            ):
                # set the customized value if it was modified
                if self._native_value != last_state.state:
                    if self._attribute_name == "battery_capacity":
                        # skip value restore if config was changed, actual native value initially contains calculated value
                        if (
                            last_state.attributes.get("calculated")
                            != self._native_value
                        ):
                            return
                    self._native_value = last_state.state
                    LOGGER.info(
                        "Restored state value of entity '%s' to: %s",
                        self.entity_id,
                        self._native_value,
                    )
                    self.coordinator.client.api.customizeCacheId(
                        id=self.coordinator_context,
                        key=self.entity_description.json_key,
                        value=str(last_state.state),
                    )
                    await self.coordinator.async_refresh_data_from_apidict(delayed=True)
