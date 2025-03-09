"""Select platform for anker_solix."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
import json
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EXCLUDE, PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, datetime

from .const import ATTRIBUTION, CREATE_ALL_ENTITIES, DOMAIN, LOGGER
from .coordinator import AnkerSolixDataUpdateCoordinator
from .entity import (
    AnkerSolixEntityRequiredKeyMixin,
    AnkerSolixEntityType,
    get_AnkerSolixAccountInfo,
    get_AnkerSolixDeviceInfo,
    get_AnkerSolixSystemInfo,
)
from .solixapi.apitypes import (
    ApiCategories,
    SolarbankPriceTypes,
    SolarbankUsageMode,
    SolixDeviceType,
)


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
    attrib_fn: Callable[[dict, str], dict | None] = lambda d, _: None


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
            iter(
                [
                    item.name
                    for item in SolarbankUsageMode
                    if item.value == d.get(jk) and "unknown" not in item.name
                ]
            ),
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
        options_fn=lambda d, _: [
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
    AnkerSolixSelectDescription(
        # Defined Site price type for saving calculations by cloud
        key="system_price_type",
        translation_key="system_price_type",
        json_key="price_type",
        options_fn=lambda d, _: [t.value for t in SolarbankPriceTypes],
        value_fn=lambda d, jk: (d.get("site_details") or {}).get(jk),
        attrib_fn=lambda d, _: {
            "current_mode": (d.get("site_details") or {}).get("current_mode"),
        },
        exclude_fn=lambda s, _: not ({ApiCategories.site_price} - s),
    ),
]

ACCOUNT_SELECTS = []


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select platform."""

    coordinator = hass.data[DOMAIN].get(entry.entry_id)
    entities = []

    if coordinator and hasattr(coordinator, "data") and coordinator.data:
        # create entity based on type of entry in coordinator data, which consolidates the api.sites, api.devices and api.account dictionaries
        # the coordinator.data dict key is either account nickname, a site_id or device_sn and used as context for the entity to lookup its data
        for context, data in coordinator.data.items():
            if (data_type := data.get("type")) == SolixDeviceType.SYSTEM.value:
                # Unique key for site_id entry in data
                entity_type = AnkerSolixEntityType.SITE
                entity_list = SITE_SELECTS
            elif data_type == SolixDeviceType.ACCOUNT.value:
                # Unique key for account entry in data
                entity_type = AnkerSolixEntityType.ACCOUNT
                entity_list = ACCOUNT_SELECTS
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
            self._attr_device_info = get_AnkerSolixDeviceInfo(
                data, context, coordinator.client.api.apisession.email
            )
        elif self.entity_type == AnkerSolixEntityType.ACCOUNT:
            # get the account data from account context entry of coordinator data
            data = coordinator.data.get(context) or {}
            self._attr_device_info = get_AnkerSolixAccountInfo(data, context)
        else:
            # get the site info data from site context entry of coordinator data
            data = (coordinator.data.get(context, {})).get("site_info", {})
            self._attr_device_info = get_AnkerSolixSystemInfo(
                data, context, coordinator.client.api.apisession.email
            )

        self.update_state_value()
        self._attr_options = self.entity_description.options_fn(
            data, self.entity_description.json_key
        )
        # update options based on other devices configured in system
        if self._attribute_name == "preset_usage_mode":
            site_data = coordinator.data.get(data.get("site_id") or "") or {}
            options = set(self._attr_options)
            if not ((site_data.get("grid_info") or {}).get("grid_list") or []):
                # Remove smart meter and use_time usage mode if no smart meter installed
                options = options - {
                    SolarbankUsageMode.smartmeter.name,
                    SolarbankUsageMode.use_time.name,
                }
            if not (
                (site_data.get("smart_plug_info") or {}).get("smartplug_list") or []
            ):
                # Remove smart plugs usage mode if no smart plugs installed
                options = options - {SolarbankUsageMode.smartplugs.name}
            if "grid_to_battery_power" not in data:
                # Remove AC model specific modes if not AC model
                options = options - {
                    SolarbankUsageMode.use_time.name,
                    SolarbankUsageMode.backup.name,
                }
            self._attr_options = list(options)
        elif self._attribute_name == "system_price_type":
            options = set(self._attr_options)
            if data.get("power_site_type") not in [11]:
                # Remove AC model specific types if no AC model in site
                options = options - {SolarbankPriceTypes.USE_TIME.value}
            self._attr_options = list(options)
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

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the sensor."""
        if (
            self.coordinator
            and (hasattr(self.coordinator, "data"))
            and self.coordinator_context in self.coordinator.data
        ):
            data = self.coordinator.data.get(self.coordinator_context)
            key = self.entity_description.json_key
            with suppress(ValueError, TypeError):
                self._attr_extra_state_attributes = self.entity_description.attrib_fn(
                    data, key
                )
        return self._attr_extra_state_attributes

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
        if (
            self.coordinator
            and self.coordinator_context in self.coordinator.data
            and self._attr_current_option is not None
        ):
            data = self.coordinator.data.get(self.coordinator_context) or {}
            if self.coordinator.client.testmode() and self._attribute_name not in [
                "preset_usage_mode",
                "system_price_unit",
                "system_price_type",
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
            # Wait until client cache is valid before applying any api change
            await self.coordinator.client.validate_cache()
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
                    usage_mode = getattr(SolarbankUsageMode, option, None)
                    if usage_mode == SolarbankUsageMode.backup:
                        # Backup option cannot be enabled directly, instead activate backup mode switch
                        # This will reactivate an existing interval or start a new backup with default duration
                        resp = await self.coordinator.client.api.set_sb2_ac_charge(
                            siteId=data.get("site_id") or "",
                            deviceSn=self.coordinator_context,
                            backup_switch=True,
                            backup_start=datetime.now().astimezone(),
                            test_schedule=data.get("schedule") or {}
                            if self.coordinator.client.testmode()
                            else None,
                        )
                    else:
                        # Ensure an active backup mode will be disabled first in cache
                        if (
                            getattr(SolarbankUsageMode, self._attr_current_option, None)
                            == SolarbankUsageMode.backup
                        ):
                            resp = await self.coordinator.client.api.set_sb2_ac_charge(
                                siteId=data.get("site_id") or "",
                                deviceSn=self.coordinator_context,
                                backup_switch=False,
                                test_schedule=data.get("schedule") or {},
                            )
                        resp = await self.coordinator.client.api.set_sb2_home_load(
                            siteId=data.get("site_id") or "",
                            deviceSn=self.coordinator_context,
                            usage_mode=getattr(SolarbankUsageMode, option, None),
                            test_schedule=data.get("schedule") or {}
                            if self.coordinator.client.testmode()
                            else None,
                        )
                    if isinstance(resp, dict) and self.coordinator.client.testmode():
                        LOGGER.info(
                            "Resulting schedule to be applied:\n%s",
                            json.dumps(resp, indent=2),
                        )
            elif self._attribute_name == "system_price_unit":
                LOGGER.debug(
                    "%s selection change to option %s will be applied",
                    self.entity_id,
                    option,
                )
                with suppress(ValueError, TypeError):
                    resp = await self.coordinator.client.api.set_site_price(
                        siteId=self.coordinator_context,
                        unit=option,
                        cache_only=self.coordinator.client.testmode(),
                    )
                    if isinstance(resp, dict) and self.coordinator.client.testmode():
                        LOGGER.info(
                            "Applied site price settings:\n%s",
                            json.dumps(resp, indent=2),
                        )
            elif self._attribute_name == "system_price_type":
                LOGGER.debug(
                    "%s selection change to option %s will be applied",
                    self.entity_id,
                    option,
                )
                with suppress(ValueError, TypeError):
                    resp = await self.coordinator.client.api.set_site_price(
                        siteId=self.coordinator_context,
                        price_type=option,
                        cache_only=self.coordinator.client.testmode(),
                    )
                    if isinstance(resp, dict) and self.coordinator.client.testmode():
                        LOGGER.info(
                            "Applied site price settings:\n%s",
                            json.dumps(resp, indent=2),
                        )

        # trigger coordinator update with api dictionary data
        await self.coordinator.async_refresh_data_from_apidict()
