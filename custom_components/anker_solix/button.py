"""Switch platform for anker_solix."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, CREATE_ALL_ENTITIES, DOMAIN
from .coordinator import AnkerSolixDataUpdateCoordinator
from .entity import (
    AnkerSolixEntityRequiredKeyMixin,
    AnkerSolixEntityType,
    get_AnkerSolixDeviceInfo,
    get_AnkerSolixSystemInfo,
)
from .solixapi.api import SolixDeviceType


@dataclass(frozen=True)
class AnkerSolixButtonDescription(
    ButtonEntityDescription, AnkerSolixEntityRequiredKeyMixin
):
    """Button entity description with optional keys."""

    force_creation: bool = False
    # Use optionally to provide function for value calculation or lookup of nested values
    value_fn: Callable[[dict, str], bool | None] = lambda d, jk: d.get(jk)
    attrib_fn: Callable[[dict], dict | None] = lambda d: None


DEVICE_BUTTONS = [
    AnkerSolixButtonDescription(
        key="refresh_device",
        translation_key="refresh_device",
        json_key="",
        force_creation=True,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
]

SITE_BUTTONS = []


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor platform."""

    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    if coordinator and hasattr(coordinator, "data") and coordinator.data:
        # create sensor type based on type of entry in coordinator data, which consolidates the api.sites and api.devices dictionaries
        # the coordinator.data dict key is either a site_id or device_sn and used as context for the sensor to lookup its data
        for context, data in coordinator.data.items():
            if data.get("type") == SolixDeviceType.SYSTEM.value:
                # Unique key for site_id entry in data
                entity_type = AnkerSolixEntityType.SITE
                entity_list = SITE_BUTTONS
            else:
                # device_sn entry in data
                entity_type = AnkerSolixEntityType.DEVICE
                entity_list = DEVICE_BUTTONS

            for description in (
                desc
                for desc in entity_list
                if bool(CREATE_ALL_ENTITIES)
                or desc.force_creation
                or desc.value_fn(data, desc.json_key) is not None
            ):
                sensor = AnkerSolixButton(
                    coordinator, description, context, entity_type
                )
                entities.append(sensor)

    # create the sensors from the list
    async_add_entities(entities)


class AnkerSolixButton(CoordinatorEntity, ButtonEntity):
    """anker_solix button class."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    _unrecorded_attributes = frozenset({})

    def __init__(
        self,
        coordinator: AnkerSolixDataUpdateCoordinator,
        description: AnkerSolixButtonDescription,
        context: str,
        entity_type: str,
    ) -> None:
        """Initialize the button class."""
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


    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.async_execute_command(self.entity_description.key)

