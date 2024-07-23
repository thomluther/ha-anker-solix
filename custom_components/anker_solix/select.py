"""Select platform for anker_solix."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
import json

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EXCLUDE, PERCENTAGE
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
from .solixapi.types import ApiCategories, SolarbankUsageMode, SolixDeviceType


@dataclass(frozen=True)
class AnkerSolixSelectDescription(
    SelectEntityDescription, AnkerSolixEntityRequiredKeyMixin
):
    """Select entity description with optional keys."""

    force_creation: bool = False
    # Use optionally to provide function for value calculation or lookup of nested values
    value_fn: Callable[[dict, str], str | None] = (
        lambda d, jk: None if d.get(jk) is None else str(d.get(jk))
    )
    options_fn: Callable[[dict, str], list | None] = (
        lambda d, jk: list(d.get(jk), []) or None
    )
    exclude_fn: Callable[[set, dict], bool] = lambda s, _: False


DEVICE_SELECTS = [
    AnkerSolixSelectDescription(
        # Solarbank Batter power cutoff setting
        key="power_cutoff",
        translation_key="power_cutoff",
        json_key="power_cutoff",
        options_fn=lambda d, _: [
            str(item.get("output_cutoff_data"))
            for item in d.get("power_cutoff_data") or []
        ],
        unit_of_measurement=PERCENTAGE,
        exclude_fn=lambda s, _: not (
            {SolixDeviceType.SOLARBANK.value} - s
            and {ApiCategories.solarbank_cutoff} - s
        ),
    ),
    AnkerSolixSelectDescription(
        # Solarbank 2 Usage Mode setting
        key="preset_usage_mode",
        translation_key="preset_usage_mode",
        json_key="preset_usage_mode",
        options_fn=lambda d, _: [
            mode.name for mode in SolarbankUsageMode if "unknown" not in mode.name
        ],
        value_fn=lambda d, jk: next(
            iter([item.name for item in SolarbankUsageMode if item.value == d.get(jk) and "unknown" not in item.name]),
            None,
        ),
        exclude_fn=lambda s, _: not ({SolixDeviceType.SOLARBANK.value} - s),
    ),
]

SITE_SELECTS = [
    AnkerSolixSelectDescription(
        # Defined Site price unit energy saving calculations by cloud
        key="system_price_unit",
        translation_key="system_price_unit",
        json_key="site_price_unit",
        options_fn=lambda d, jk: [
            "€",
            "$",
            "£",
            "¥",
            "₹",
            "원",
        ],
        value_fn=lambda d, jk: (d.get("site_details") or {}).get(jk),
        exclude_fn=lambda s, _: not ({ApiCategories.site_price} - s),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select platform."""

    coordinator = hass.data[DOMAIN].get(entry.entry_id)
    entities = []

    if coordinator and hasattr(coordinator, "data") and coordinator.data:
        # create select type based on type of entry in coordinator data, which consolidates the api.sites and api.devices dictionaries
        # the coordinator.data dict key is either a site_id or device_sn and used as context for the number entity to lookup its data
        for context, data in coordinator.data.items():
            if data.get("type") == SolixDeviceType.SYSTEM.value:
                # Unique key for site_id entry in data
                entity_type = AnkerSolixEntityType.SITE
                entity_list = SITE_SELECTS
            else:
                # device_sn entry in data
                entity_type = AnkerSolixEntityType.DEVICE
                entity_list = DEVICE_SELECTS

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
                entity = AnkerSolixSelect(
                    coordinator, description, context, entity_type
                )
                entities.append(entity)

    # create the sensors from the list
    async_add_entities(entities)


class AnkerSolixSelect(CoordinatorEntity, SelectEntity):
    """anker_solix select class."""

    coordinator: AnkerSolixDataUpdateCoordinator
    entity_description: AnkerSolixSelectDescription
    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    _unrecorded_attributes = frozenset(
        {
            "power_cutoff",
        }
    )

    def __init__(
        self,
        coordinator: AnkerSolixDataUpdateCoordinator,
        description: AnkerSolixSelectDescription,
        context: str,
        entity_type: str,
    ) -> None:
        """Initialize the select class."""
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

        self.update_state_value()
        self._attr_options = self.entity_description.options_fn(
            data, self.entity_description.json_key
        )
        # Make sure that options are limited to existing state if entity cannot be changed
        if not self._attr_options and self._attr_current_option is not None:
            self._attr_options = [self._attr_current_option]

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.update_state_value()
        super()._handle_coordinator_update()

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option to represent the entity state."""
        return self._attr_current_option

    @property
    def options(self) -> str | None:
        """Return the entity options available."""
        return self._attr_options

    def update_state_value(self):
        """Update the state value of the number based on the coordinator data."""
        if self.coordinator and self.coordinator_context in self.coordinator.data:
            data = self.coordinator.data.get(self.coordinator_context)
            key = self.entity_description.json_key
            with suppress(ValueError, TypeError):
                self._attr_current_option = self.entity_description.value_fn(data, key)
        else:
            self._attr_current_option = None

        # Mark availability based on value
        self._attr_available = self._attr_current_option is not None

    async def async_select_option(self, option: str) -> None:
        """Change the selected option.

        Args:
            option (str): The option to set.

        """
        if self.coordinator.client.testmode() and not self._attribute_name == "preset_usage_mode":
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
            if self._attribute_name == "power_cutoff":
                LOGGER.debug(
                    "%s selection change to option %s will be applied",
                    self.entity_id,
                    option,
                )
                with suppress(ValueError, TypeError):
                    if (
                        len(
                            selected_id := [
                                d.get("id")
                                for d in (data.get("power_cutoff_data") or [])
                                if str(d.get("output_cutoff_data")) == option
                            ]
                        )
                        > 0
                    ):
                        await self.coordinator.client.api.set_power_cutoff(
                            deviceSn=self.coordinator_context,
                            setId=int(selected_id[0]),
                        )
            elif self._attribute_name == "preset_usage_mode":
                LOGGER.debug(
                    "%s selection change to option %s will be applied",
                    self.entity_id,
                    option,
                )
                with suppress(ValueError, TypeError):
                    resp = await self.coordinator.client.api.set_sb2_home_load(
                        siteId=data.get("site_id") or "",
                        deviceSn=self.coordinator_context,
                        usage_mode=getattr(SolarbankUsageMode,option,None),
                        test_schedule=data.get("schedule") or {} if self.coordinator.client.testmode() else None
                    )
                    if isinstance(resp,dict) and self.coordinator.client.testmode():
                        LOGGER.info(
                            "Resulting schedule to be applied:\n%s",
                            json.dumps(resp,indent=2),
                        )
            elif self._attribute_name == "system_price_unit":
                LOGGER.debug(
                    "%s selection change to option %s will be applied",
                    self.entity_id,
                    option,
                )
                with suppress(ValueError, TypeError):
                    await self.coordinator.client.api.set_site_price(
                        siteId=self.coordinator_context,
                        unit=option,
                    )
        # trigger coordinator update with api dictionary data
        await self.coordinator.async_refresh_data_from_apidict()
