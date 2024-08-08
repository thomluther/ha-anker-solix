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
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EXCLUDE, PERCENTAGE, UnitOfPower
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .config_flow import _SCAN_INTERVAL_MIN
from .const import ATTRIBUTION, CREATE_ALL_ENTITIES, DOMAIN, LOGGER
from .coordinator import AnkerSolixDataUpdateCoordinator
from .entity import (
    AnkerSolixEntityRequiredKeyMixin,
    AnkerSolixEntityType,
    get_AnkerSolixDeviceInfo,
    get_AnkerSolixSystemInfo,
)
from .solixapi.types import ApiCategories, SolixDefaults, SolixDeviceType


@dataclass(frozen=True)
class AnkerSolixNumberDescription(
    NumberEntityDescription, AnkerSolixEntityRequiredKeyMixin
):
    """Number entity description with optional keys."""

    force_creation: bool = False
    # Use optionally to provide function for value calculation or lookup of nested values
    value_fn: Callable[[dict, str], StateType | None] = lambda d, jk: d.get(jk)
    unit_fn: Callable[[dict], str | None] = lambda d: None
    attrib_fn: Callable[[dict], dict | None] = lambda d: None
    exclude_fn: Callable[[set, dict], bool] = lambda s, _: False


DEVICE_NUMBERS = [
    AnkerSolixNumberDescription(
        # System total output setting, determined by schedule, the limits will be adopted during creation
        key="preset_system_output_power",
        translation_key="preset_system_output_power",
        json_key="preset_system_output_power",
        mode=NumberMode.SLIDER,
        native_min_value=SolixDefaults.PRESET_MIN,
        native_max_value=SolixDefaults.PRESET_MAX,
        native_step=10,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=NumberDeviceClass.POWER,
        exclude_fn=lambda s, d: not (
            {SolixDeviceType.SOLARBANK.value} - s
        ),
    ),
    AnkerSolixNumberDescription(
        # Device output setting, determined by schedule
        key="preset_device_output_power",
        translation_key="preset_device_output_power",
        json_key="preset_device_output_power",
        mode=NumberMode.SLIDER,
        native_min_value=SolixDefaults.PRESET_MIN,
        native_max_value=SolixDefaults.PRESET_MAX,
        native_step=5,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=NumberDeviceClass.POWER,
        exclude_fn=lambda s, _: not ({SolixDeviceType.SOLARBANK.value} - s),
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
    ),
]

SITE_NUMBERS = [
    AnkerSolixNumberDescription(
        # Defined Site price for energy saving calculations by cloud
        key="system_price",
        translation_key="system_price",
        json_key="price",
        unit_fn=lambda d: (d.get("site_details") or {}).get("site_price_unit"),
        device_class=NumberDeviceClass.MONETARY,
        value_fn=lambda d, jk: (d.get("site_details") or {}).get(jk),
        native_min_value=0,
        native_max_value=1000,
        native_step=0.01,
        exclude_fn=lambda s, _: not ({ApiCategories.site_price} - s),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number platform."""

    coordinator = hass.data[DOMAIN].get(entry.entry_id)
    entities = []

    if coordinator and hasattr(coordinator, "data") and coordinator.data:
        # create number type based on type of entry in coordinator data, which consolidates the api.sites and api.devices dictionaries
        # the coordinator.data dict key is either a site_id or device_sn and used as context for the number entity to lookup its data
        for context, data in coordinator.data.items():
            if data.get("type") == SolixDeviceType.SYSTEM.value:
                # Unique key for site_id entry in data
                entity_type = AnkerSolixEntityType.SITE
                entity_list = SITE_NUMBERS
            else:
                # device_sn entry in data
                entity_type = AnkerSolixEntityType.DEVICE
                entity_list = DEVICE_NUMBERS

            for description in (
                desc
                for desc in entity_list
                if bool(CREATE_ALL_ENTITIES)
                or (
                    not desc.exclude_fn(set(entry.options.get(CONF_EXCLUDE, [])), data)
                    and (
                        desc.force_creation
                        or desc.value_fn(data, desc.json_key) is not None
                    )
                )
            ):
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
    _attr_attribution = ATTRIBUTION
    _unrecorded_attributes = frozenset(
        {
            "schedule",
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
        self._attr_unique_id = (f"{context}_{description.key}").lower()
        self.entity_description = description
        self.entity_type = entity_type
        self.last_changed: datetime | None = None
        self._attr_extra_state_attributes = None

        if self.entity_type == AnkerSolixEntityType.DEVICE:
            # get the device data from device context entry of coordinator data
            data: dict = coordinator.data.get(context) or {}
            self._attr_device_info = get_AnkerSolixDeviceInfo(data, context)
            # update number limits based on solarbank count in system
            if self._attribute_name == "preset_system_output_power":
                if (data.get("generation") or 0) > 1:
                    # SB2 has min limit of 0W, they are typically correctly set in the schedule depending on device settings
                    self.native_min_value = (data.get("schedule") or {}).get(
                        "min_load"
                    ) or 0
                    self.native_max_value = (data.get("schedule") or {}).get(
                        "max_load"
                    ) or self.native_max_value
                else:
                    self.native_max_value = int(
                        self.native_max_value * (data.get("solarbank_count") or 1)
                    )
            if self._attribute_name == "preset_device_output_power":
                self.native_min_value = int(
                    self.native_min_value / (data.get("solarbank_count") or 1)
                )
        else:
            # get the site info data from site context entry of coordinator data
            data: dict = (coordinator.data.get(context, {})).get("site_info") or {}
            self._attr_device_info = get_AnkerSolixSystemInfo(data, context)

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
            data = self.coordinator.data.get(self.coordinator_context)
            with suppress(ValueError, TypeError):
                self._attr_extra_state_attributes = self.entity_description.attrib_fn(
                    data, self.coordinator_context
                )
        return self._attr_extra_state_attributes

    def update_state_value(self):
        """Update the state value of the number based on the coordinator data."""
        if self.coordinator and self.coordinator_context in self.coordinator.data:
            data = self.coordinator.data.get(self.coordinator_context)
            key = self.entity_description.json_key
            with suppress(ValueError, TypeError):
                self._native_value = self.entity_description.value_fn(data, key)
                # get dynamic unit if defined
                if unit := self.entity_description.unit_fn(data):
                    self._attr_native_unit_of_measurement = unit
        else:
            self._native_value = None

        self._assumed_state = False
        # Mark availability based on value
        self._attr_available = self._native_value is not None

    async def async_set_native_value(self, value: float) -> None:
        """Set the native value of the number entity.

        Args:
            value (float): The value to set.

        """
        if self.coordinator.client.testmode() and self._attribute_name not in [
            "preset_system_output_power",
            "preset_device_output_power",
            "preset_charge_priority",
        ]:
            # Raise alert to frontend
            raise ServiceValidationError(
                f"{self.entity_id} cannot be changed while configuration is running in testmode",
                translation_domain=DOMAIN,
                translation_key="active_testmode",
                translation_placeholders={
                    "entity_id": self.entity_id,
                },
            )
        if self.coordinator and self.coordinator_context in self.coordinator.data:
            data = self.coordinator.data.get(self.coordinator_context) or {}
            if self.min_value <= value <= self.max_value:
                # round the number to the defined steps if set via service call
                if self.step:
                    value = self.step * round(value / self.step)
                if self._attribute_name in [
                    "preset_system_output_power",
                    "preset_device_output_power",
                ]:
                    # for increasing load value, change only if min delay passed
                    if (
                        (
                            (
                                str(self._native_value).isdigit()
                                or isinstance(self._native_value, int | float)
                            )
                            and value < int(self._native_value)
                        )
                        or not self.last_changed
                        or datetime.now().astimezone()
                        > self.last_changed + timedelta(seconds=_SCAN_INTERVAL_MIN)
                    ):
                        LOGGER.debug(
                            "%s change to %s will be applied", self.entity_id, value
                        )
                        siteId = data.get("site_id") or ""
                        if (data.get("generation") or 0) > 1:
                            # SB2 preset change
                            resp = await self.coordinator.client.api.set_sb2_home_load(
                                siteId=siteId,
                                deviceSn=self.coordinator_context,
                                preset=int(value),
                                test_schedule=data.get("schedule") or {}
                                if self.coordinator.client.testmode()
                                else None,
                            )
                            if (
                                isinstance(resp, dict)
                                and self.coordinator.client.testmode()
                            ):
                                LOGGER.info(
                                    "TESTMODE ONLY: Resulting schedule to be applied:\n%s",
                                    json.dumps(resp, indent=2),
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
                                test_schedule=data.get("schedule") or {}
                                if self.coordinator.client.testmode()
                                else None,
                            )
                            if (
                                isinstance(resp, dict)
                                and self.coordinator.client.testmode()
                            ):
                                LOGGER.info(
                                    "TESTMODE ONLY: Resulting schedule to be applied:\n%s",
                                    json.dumps(resp, indent=2),
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
                            "%s cannot be increased to %s because minimum change delay of %s seconds is not passed",
                            self.entity_id,
                            value,
                            _SCAN_INTERVAL_MIN,
                        )
                        # Raise alert to frontend
                        raise ServiceValidationError(
                            f"{self.entity_id} cannot be increased to {value} because minimum change delay of {_SCAN_INTERVAL_MIN} seconds is not passed",
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
                        "%s change to %s will be applied", self.entity_id, value
                    )
                    resp = await self.coordinator.client.api.set_home_load(
                        siteId=data.get("site_id") or "",
                        deviceSn=self.coordinator_context,
                        charge_prio=int(value),
                        test_schedule=data.get("schedule") or {}
                        if self.coordinator.client.testmode()
                        else None,
                    )
                    if isinstance(resp, dict) and self.coordinator.client.testmode():
                        LOGGER.info(
                            "TESTMODE ONLY: Resulting schedule to be applied:\n%s",
                            json.dumps(resp, indent=2),
                        )
                elif self._attribute_name == "system_price":
                    LOGGER.debug(
                        "%s change to %s will be applied", self.entity_id, value
                    )
                    await self.coordinator.client.api.set_site_price(
                        siteId=self.coordinator_context,
                        price=float(value),
                    )
            else:
                LOGGER.debug(
                    "%s cannot be set because the value %s is out of range %s-%s",
                    self.entity_id,
                    value,
                    self.min_value,
                    self.max_value,
                )
                # Raise alert to frontend
                raise ServiceValidationError(
                    f"{self.entity_id} cannot be set to {value} because it is outsite of allowed range {self.min_value}-{self.max_value}",
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
        self._assumed_state = True
        self._native_value = value
