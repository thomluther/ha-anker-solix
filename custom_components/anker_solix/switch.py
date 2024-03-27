"""Switch platform for anker_solix."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, CREATE_ALL_ENTITIES, DOMAIN, LOGGER
from .coordinator import AnkerSolixDataUpdateCoordinator
from .entity import (
    AnkerSolixEntityRequiredKeyMixin,
    AnkerSolixEntityType,
    get_AnkerSolixDeviceInfo,
    get_AnkerSolixSystemInfo,
)
from .solixapi.api import SolixDeviceType


@dataclass(frozen=True)
class AnkerSolixSwitchDescription(
    SwitchEntityDescription, AnkerSolixEntityRequiredKeyMixin
):
    """Switch entity description with optional keys."""

    force_creation: bool = False
    # Use optionally to provide function for value calculation or lookup of nested values
    value_fn: Callable[[dict, str], bool | None] = lambda d, jk: d.get(jk)
    attrib_fn: Callable[[dict], dict | None] = lambda d: None


DEVICE_SWITCHES = [
    AnkerSolixSwitchDescription(
        key="auto_upgrade",
        translation_key="auto_upgrade",
        json_key="auto_upgrade",
    ),
    AnkerSolixSwitchDescription(
        key="preset_allow_export",
        translation_key="preset_allow_export",
        json_key="preset_allow_export",
    ),
]

SITE_SWITCHES = [
    AnkerSolixSwitchDescription(
        key="allow_refresh",
        translation_key="allow_refresh",
        json_key="allow_refresh",
        entity_category=EntityCategory.DIAGNOSTIC,
        force_creation=True,
        value_fn=lambda d, _: len(d) > 0,
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
        # create sensor type based on type of entry in coordinator data, which consolidates the api.sites and api.devices dictionaries
        # the coordinator.data dict key is either a site_id or device_sn and used as context for the sensor to lookup its data
        for context, data in coordinator.data.items():
            if data.get("type") == SolixDeviceType.SYSTEM.value:
                # Unique key for site_id entry in data
                entity_type = AnkerSolixEntityType.SITE
                entity_list = SITE_SWITCHES
            else:
                # device_sn entry in data
                entity_type = AnkerSolixEntityType.DEVICE
                entity_list = DEVICE_SWITCHES

            for description in (
                desc
                for desc in entity_list
                if bool(CREATE_ALL_ENTITIES)
                or desc.force_creation
                or desc.value_fn(data, desc.json_key) is not None
            ):
                sensor = AnkerSolixSwitch(
                    coordinator, description, context, entity_type
                )
                entities.append(sensor)

    # create the sensors from the list
    async_add_entities(entities)


class AnkerSolixSwitch(CoordinatorEntity, SwitchEntity):
    """anker_solix switch class."""

    coordinator: AnkerSolixDataUpdateCoordinator
    entity_description: AnkerSolixSwitchDescription
    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    _unrecorded_attributes = frozenset(
        {
            "auto_upgrade",
        }
    )

    def __init__(
        self,
        coordinator: AnkerSolixDataUpdateCoordinator,
        description: AnkerSolixSwitchDescription,
        context: str,
        entity_type: str,
    ) -> None:
        """Initialize the switch class."""
        super().__init__(coordinator, context)

        self._attribute_name = description.key
        self._attr_unique_id = (f"{context}_{description.key}").lower()
        self.entity_description = description
        self.entity_type = entity_type
        self._attr_extra_state_attributes = None

        if self.entity_type == AnkerSolixEntityType.DEVICE:
            # get the device data from device context entry of coordinator data
            data = coordinator.data.get(context) or {}
            self._attr_device_info = get_AnkerSolixDeviceInfo(data, context)
        else:
            # get the site info data from site context entry of coordinator data
            data = (coordinator.data.get(context, {})).get("site_info", {})
            self._attr_device_info = get_AnkerSolixSystemInfo(data, context)

        self._attr_is_on = None
        self.update_state_value()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.update_state_value()
        super()._handle_coordinator_update()

    def update_state_value(self):
        """Update the state value of the switch based on the coordinator data."""
        if self.coordinator and not (hasattr(self.coordinator, "data")):
            self._attr_is_on = None
        elif self.coordinator_context in self.coordinator.data:
            data = self.coordinator.data.get(self.coordinator_context)
            key = self.entity_description.json_key
            self._attr_is_on = self.entity_description.value_fn(data, key)
        else:
            self._attr_is_on = self.entity_description.value_fn(
                self.coordinator.data, self.entity_description.json_key
            )

        # Mark availability based on value
        self._attr_available = self._attr_is_on is not None

    async def async_turn_on(self, **_: any) -> None:
        """Turn on the switch."""
        if self._attribute_name == "allow_refresh":
            self.coordinator.client.allow_refresh(allow=True)
            await self.coordinator.async_refresh_device_details()
        # When running in Test mode do not switch
        elif self.coordinator.client.testmode():
            # Raise alert to frontend
            raise ServiceValidationError(
                f"{self.entity_id} cannot be changed while configuration is running in testmode",
                translation_domain=DOMAIN,
                translation_key="active_testmode",
                translation_placeholders={
                    "entity_id": self.entity_id,
                },
            )
        elif self._attribute_name == "auto_upgrade":
            # When running in Test mode do not switch
            if not self.coordinator.client.testmode():
                await self.coordinator.client.api.set_auto_upgrade(
                    {self.coordinator_context: True}
                )
                await self.coordinator.async_refresh_data_from_apidict()
        elif self._attribute_name == "preset_allow_export":
            if (
                self.coordinator
                and hasattr(self.coordinator, "data")
                and self.coordinator_context in self.coordinator.data
            ):
                data = self.coordinator.data.get(self.coordinator_context)
                LOGGER.debug(
                    "%s System allow export will be set %s", self.entity_id, True
                )
                await self.coordinator.client.api.set_home_load(
                    siteId=data.get("site_id") or "",
                    deviceSn=self.coordinator_context,
                    export=True,
                )
                await self.coordinator.async_refresh_data_from_apidict()
            else:
                LOGGER.error(
                    "%s System allow export cannot be set %s because entity data was not found",
                    self.entity_id,
                    True,
                )

    async def async_turn_off(self, **_: any) -> None:
        """Turn off the switch."""
        if self._attribute_name == "allow_refresh":
            self.coordinator.client.allow_refresh(allow=False)
            await self.coordinator.async_refresh_data_from_apidict()
        # When running in Test mode do not switch
        elif self.coordinator.client.testmode():
            # Raise alert to frontend
            raise ServiceValidationError(
                f"{self.entity_id} cannot be changed while configuration is running in testmode",
                translation_domain=DOMAIN,
                translation_key="active_testmode",
                translation_placeholders={
                    "entity_id": self.entity_id,
                },
            )
        elif self._attribute_name == "auto_upgrade":
            await self.coordinator.client.api.set_auto_upgrade(
                {self.coordinator_context: False}
            )
            await self.coordinator.async_refresh_data_from_apidict()
        elif self._attribute_name == "preset_allow_export":
            if (
                self.coordinator
                and hasattr(self.coordinator, "data")
                and self.coordinator_context in self.coordinator.data
            ):
                data = self.coordinator.data.get(self.coordinator_context)
                LOGGER.debug(
                    "%s System allow export will be set %s", self.entity_id, False
                )
                await self.coordinator.client.api.set_home_load(
                    siteId=data.get("site_id") or "",
                    deviceSn=self.coordinator_context,
                    export=False,
                )
                await self.coordinator.async_refresh_data_from_apidict()
            else:
                LOGGER.error(
                    "%s System allow export cannot be set %s because entity data was not found",
                    self.entity_id,
                    False,
                )
