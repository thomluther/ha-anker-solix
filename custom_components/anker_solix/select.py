"""Select platform for anker_solix."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
import json
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EXCLUDE, PERCENTAGE, UnitOfPower
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_platform
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, datetime

from .const import (
    ALLOW_TESTMODE,
    ATTRIBUTION,
    CREATE_ALL_ENTITIES,
    DAY_TYPE,
    DELETE,
    DOMAIN,
    END_HOUR,
    END_MONTH,
    LOGGER,
    SERVICE_MODIFY_SOLIX_USE_TIME,
    SOLIX_USE_TIME_SCHEMA,
    START_HOUR,
    START_MONTH,
    TARIFF,
    TARIFF_PRICE,
)
from .coordinator import AnkerSolixDataUpdateCoordinator
from .entity import (
    AnkerSolixEntityFeature,
    AnkerSolixEntityRequiredKeyMixin,
    AnkerSolixEntityType,
    get_AnkerSolixAccountInfo,
    get_AnkerSolixDeviceInfo,
    get_AnkerSolixSubdeviceInfo,
    get_AnkerSolixSystemInfo,
)
from .solixapi.apitypes import (
    ApiCategories,
    SolarbankDeviceMetrics,
    SolarbankUsageMode,
    SolixDeviceType,
    SolixPriceTypes,
    SolixTariffTypes,
)


@dataclass(frozen=True)
class AnkerSolixSelectDescription(
    SelectEntityDescription, AnkerSolixEntityRequiredKeyMixin
):
    """Select entity description with optional keys."""

    force_creation_fn: Callable[[dict, str], bool] = lambda d, _: False
    # Use optionally to provide function for value calculation or lookup of nested values
    value_fn: Callable[[dict, str], str | None] = (
        lambda d, jk: None if d.get(jk) is None else str(d.get(jk))
    )
    options_fn: Callable[[dict, str], list | None] = (
        lambda d, jk: list(d.get(jk), []) or None
    )
    exclude_fn: Callable[[set, dict], bool] = lambda s, _: False
    attrib_fn: Callable[[dict, str], dict | None] = lambda d, _: None
    feature: AnkerSolixEntityFeature | None = None


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
                    if item.value == d.get(jk)
                ]
            ),
            str(d.get(jk)) if jk in d else None,
        ),
        exclude_fn=lambda s, _: not ({SolixDeviceType.SOLARBANK.value} - s),
    ),
    AnkerSolixSelectDescription(
        # Solarbank 2 AC Tariff type
        key="preset_tariff",
        translation_key="preset_tariff",
        json_key="preset_tariff",
        options_fn=lambda d, _: [
            item.name.lower()
            for item in SolixTariffTypes
            if item.value != SolixTariffTypes.NONE.value
        ],
        value_fn=lambda d, jk: next(
            iter(
                [
                    item.name.lower()
                    for item in SolixTariffTypes
                    if item.value == d.get(jk)
                ]
            ),
            None,
        ),
        feature=AnkerSolixEntityFeature.AC_CHARGE,
        exclude_fn=lambda s, _: not ({SolixDeviceType.SOLARBANK.value} - s),
    ),
    AnkerSolixSelectDescription(
        # Inverter limit supported options
        key="preset_inverter_limit",
        translation_key="preset_inverter_limit",
        json_key="preset_inverter_limit",
        options_fn=lambda d, _: SolarbankDeviceMetrics.INVERTER_OUTPUT_OPTIONS.get(
            d.get("device_pn") or ""
        )
        or [],
        unit_of_measurement=UnitOfPower.WATT,
        exclude_fn=lambda s, _: not ({SolixDeviceType.INVERTER.value} - s),
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
        options_fn=lambda d, _: [t.value for t in SolixPriceTypes],
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
                        desc.force_creation_fn(data, desc.json_key)
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

    # register the entity services
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        name=SERVICE_MODIFY_SOLIX_USE_TIME,
        schema=SOLIX_USE_TIME_SCHEMA,
        func=SERVICE_MODIFY_SOLIX_USE_TIME,
        required_features=[AnkerSolixEntityFeature.AC_CHARGE],
    )


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
            if data.get("is_subdevice"):
                self._attr_device_info = get_AnkerSolixSubdeviceInfo(
                    data, context, data.get("main_sn")
                )
            else:
                self._attr_device_info = get_AnkerSolixDeviceInfo(
                    data, context, coordinator.client.api.apisession.email
                )
            # add service attribute for manageable devices
            self._attr_supported_features: AnkerSolixEntityFeature = (
                description.feature if data.get("is_admin", False) else None
            )
        elif self.entity_type == AnkerSolixEntityType.ACCOUNT:
            # get the account data from account context entry of coordinator data
            data = coordinator.data.get(context) or {}
            self._attr_device_info = get_AnkerSolixAccountInfo(data, context)
            # add service attribute for account entities
            self._attr_supported_features: AnkerSolixEntityFeature = description.feature
        else:
            # get the site info data from site context entry of coordinator data
            data = (coordinator.data.get(context, {})).get("site_info", {})
            self._attr_device_info = get_AnkerSolixSystemInfo(
                data, context, coordinator.client.api.apisession.email
            )
            # add service attribute for site entities
            self._attr_supported_features: AnkerSolixEntityFeature = description.feature

        self.update_state_value()
        self._attr_options = self.entity_description.options_fn(
            data, self.entity_description.json_key
        )
        # update options based on other devices configured in system
        if self._attribute_name == "preset_usage_mode":
            site_data = coordinator.data.get(data.get("site_id") or "") or {}
            options = set(self._attr_options)
            if not ((site_data.get("grid_info") or {}).get("grid_list") or []):
                # Remove smart meter usage mode if no smart meter installed
                options.discard(SolarbankUsageMode.smartmeter.name)
            if not (
                (site_data.get("smart_plug_info") or {}).get("smartplug_list") or []
            ):
                # Remove smart plugs usage mode if no smart plugs installed
                options.discard(SolarbankUsageMode.smartplugs.name)
            # if not (data.get("generation") or 0) >= 3:
            #     # Remove options introduced with SB3
            #     options.discard(SolarbankUsageMode.smart.name)
            #     options.discard(SolarbankUsageMode.time_slot.name)
            if "grid_to_battery_power" not in data:
                # Remove AC model specific modes if not AC model
                options.discard(SolarbankUsageMode.use_time.name)
                options.discard(SolarbankUsageMode.backup.name)
            elif not (
                options
                & {
                    SolarbankUsageMode.smartmeter.name,
                    SolarbankUsageMode.smartplugs.name,
                }
            ):
                # Remove modes requiring either smart plugs or smart meter in system
                options.discard(SolarbankUsageMode.use_time.name)
                # options.discard(SolarbankUsageMode.smart.name)
                # options.discard(SolarbankUsageMode.time_slot.name)
            self._attr_options = list(options)
        elif self._attribute_name == "system_price_unit":
            options = set(self._attr_options) | {
                item.get("symbol")
                for item in (
                    (
                        coordinator.data.get(coordinator.client.api.apisession.email)
                        or {}
                    ).get("currency_list")
                    or []
                )
            }
            self._attr_options = list(options)
        elif self._attribute_name == "system_price_type":
            options = set(self._attr_options)
            site_data = coordinator.data.get(data.get("site_id") or "") or {}
            if not (
                data.get("power_site_type") in [11]
                and (
                    ((site_data.get("grid_info") or {}).get("grid_list") or [])
                    or (
                        (site_data.get("smart_plug_info") or {}).get("smartplug_list")
                        or []
                    )
                )
            ):
                # Remove AC model specific types if no AC model or smart meter or smart plugs in site
                options.discard(SolixPriceTypes.USE_TIME.value)
            self._attr_options = list(options)
        # elif self._attribute_name == "preset_inverter_limit":
        #     data = self.coordinator.data.get(self.coordinator_context) or {}
        #     options = set(self._attr_options)
        #     if data.get("device_pn") == "A5143":
        #         # Remove unsupported power settings for MI80
        #         options.discard("350")
        #     self._attr_options = list(options)
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
        # update the options depending on conditions
        if self._attribute_name == "preset_usage_mode":
            data = self.coordinator.data.get(self.coordinator_context) or {}
            options = set(self._attr_options)
            schedule = data.get("schedule") or {}
            # TODO(SB3): Update option dependencies as required for new SB3 modes
            if schedule.get("use_time"):
                # Add Usage Time option
                options.add(SolarbankUsageMode.use_time.name)
                # if (data.get("generation") or 0) >= 3:
                #    options.add(SolarbankUsageMode.smart.name)
            else:
                options.discard(SolarbankUsageMode.use_time.name)
                # options.discard(SolarbankUsageMode.smart.name)
            # TODO(SB3): Update options as required for new SB3 modes
            if set(self._attr_options) != options:
                self._attr_options = list(options)
        elif self._attribute_name == "system_price_type":
            data = self.coordinator.data.get(self.coordinator_context) or {}
            options = set(self._attr_options)
            if sn := next(
                iter((data.get("solarbank_info") or {}).get("solarbank_list") or []), {}
            ).get("device_sn"):
                if ((self.coordinator.data.get(sn) or {}).get("schedule") or {}).get(
                    "use_time"
                ):
                    # Add tariff price option if use time plan defined
                    options.add(SolixPriceTypes.USE_TIME.value)
                else:
                    # remove tariff price option if use time plan missing
                    options.discard(SolixPriceTypes.USE_TIME.value)
            if set(self._attr_options) != options:
                self._attr_options = list(options)
        elif (
            self._attribute_name == "preset_inverter_limit"
            and self._attr_current_option is not None
        ):
            data = self.coordinator.data.get(self.coordinator_context) or {}
            options = set(self._attr_options)
            # Add actual power setting to options if not included
            options.add(self._attr_current_option)
            if set(self._attr_options) != options:
                self._attr_options = list(options)
                self._attr_options.sort()
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

    async def modify_solix_use_time(self, **kwargs: Any) -> dict | None:
        """Modify the use time schedule of devices supporting AC charge."""
        return await self._solix_ac_charge_service(
            service_name=SERVICE_MODIFY_SOLIX_USE_TIME, **kwargs
        )

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
                "preset_tariff",
                "system_price_unit",
                "system_price_type",
                "preset_inverter_limit",
            ]:
                # Raise alert to frontend
                raise ServiceValidationError(
                    f"{self.entity_id} cannot be used while configuration is running in testmode",
                    translation_domain=DOMAIN,
                    translation_key="active_testmode",
                    translation_placeholders={
                        "entity_id": self.entity_id,
                    },
                )
            # Skip Api calls if entity does not change
            if str(option) == str(self._attr_current_option):
                return
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
                            toFile=self.coordinator.client.testmode(),
                        )
                    else:
                        # Ensure an active backup mode will be disabled first in cache, the Api call will be done in the home load method
                        if (
                            getattr(SolarbankUsageMode, self._attr_current_option, None)
                            == SolarbankUsageMode.backup
                        ):
                            resp = await self.coordinator.client.api.set_sb2_ac_charge(
                                siteId=data.get("site_id") or "",
                                deviceSn=self.coordinator_context,
                                backup_switch=False,
                                # Use test schedule to ensure change is done in cache only
                                test_schedule=data.get("schedule") or {},
                                toFile=self.coordinator.client.testmode(),
                            )
                        resp = await self.coordinator.client.api.set_sb2_home_load(
                            siteId=data.get("site_id") or "",
                            deviceSn=self.coordinator_context,
                            usage_mode=usage_mode,
                            toFile=self.coordinator.client.testmode(),
                        )
                    if isinstance(resp, dict) and ALLOW_TESTMODE:
                        LOGGER.info(
                            "%s: Applied schedule for %s change to %s:\n%s",
                            "TESTMODE"
                            if self.coordinator.client.testmode()
                            else "LIVEMODE",
                            self.entity_id,
                            option,
                            json.dumps(
                                resp, indent=2 if len(json.dumps(resp)) < 200 else None
                            ),
                        )
            elif (
                self._attribute_name == "preset_tariff"
                and option != cv.ENTITY_MATCH_NONE
            ):
                LOGGER.debug(
                    "%s selection change to option %s will be applied",
                    self.entity_id,
                    option,
                )
                with suppress(ValueError, TypeError):
                    resp = await self.coordinator.client.api.set_sb2_use_time(
                        siteId=data.get("site_id") or "",
                        deviceSn=self.coordinator_context,
                        tariff_type=option,
                        # Ensure that only the tariff is changed without modification of slot times or clearance of tariff price
                        merge_tariff_slots=False,
                        clear_unused_tariff=False,
                        toFile=self.coordinator.client.testmode(),
                    )

                    if isinstance(resp, dict) and ALLOW_TESTMODE:
                        LOGGER.info(
                            "%s: Applied site price settings for %s change to %s:\n%s",
                            "TESTMODE"
                            if self.coordinator.client.testmode()
                            else "LIVEMODE",
                            self.entity_id,
                            option,
                            json.dumps(
                                resp, indent=2 if len(json.dumps(resp)) < 200 else None
                            ),
                        )
            elif self._attribute_name == "system_price_unit":
                LOGGER.debug(
                    "%s selection change to option %s will be applied",
                    self.entity_id,
                    option,
                )
                with suppress(ValueError, TypeError):
                    if str(self.coordinator_context).startswith(
                        SolixDeviceType.VIRTUAL.value
                    ):
                        # change standalone inverter price of virtual system
                        resp = await self.coordinator.client.api.set_device_pv_price(
                            deviceSn=str(self.coordinator_context).split("-")[1],
                            unit=option,
                            toFile=self.coordinator.client.testmode(),
                        )
                    else:
                        # change real system price
                        resp = await self.coordinator.client.api.set_site_price(
                            siteId=self.coordinator_context,
                            unit=option,
                            toFile=self.coordinator.client.testmode(),
                        )
                    if isinstance(resp, dict) and ALLOW_TESTMODE:
                        LOGGER.info(
                            "%s: Applied site price settings for %s change to %s:\n%s",
                            "TESTMODE"
                            if self.coordinator.client.testmode()
                            else "LIVEMODE",
                            self.entity_id,
                            option,
                            json.dumps(
                                resp, indent=2 if len(json.dumps(resp)) < 200 else None
                            ),
                        )
                    # Ensure currency change will also be applied to existing use time plan
                    deviceSn = next(
                        iter(
                            [
                                item.get("device_sn")
                                for item in self.coordinator.data.values()
                                if item.get("site_id") == self.coordinator_context
                                and (item.get("schedule") or {}).get("use_time")
                            ]
                        ),
                        None,
                    )
                    if deviceSn:
                        resp = await self.coordinator.client.api.set_sb2_use_time(
                            siteId=self.coordinator_context,
                            deviceSn=deviceSn,
                            currency=option,
                            toFile=self.coordinator.client.testmode(),
                        )
                        if isinstance(resp, dict) and ALLOW_TESTMODE:
                            LOGGER.info(
                                "%s: Applied schedule for %s change to %s:\n%s",
                                "TESTMODE"
                                if self.coordinator.client.testmode()
                                else "LIVEMODE",
                                self.entity_id,
                                option,
                                json.dumps(
                                    resp,
                                    indent=2 if len(json.dumps(resp)) < 200 else None,
                                ),
                            )
            elif self._attribute_name == "preset_inverter_limit":
                with suppress(ValueError, TypeError):
                    LOGGER.debug(
                        "%s selection change to option %s will be applied",
                        self.entity_id,
                        option,
                    )
                    resp = await self.coordinator.client.api.set_device_pv_power(
                        deviceSn=self.coordinator_context,
                        limit=int(option),
                        toFile=self.coordinator.client.testmode(),
                    )
                    if isinstance(resp, dict) and ALLOW_TESTMODE:
                        LOGGER.info(
                            "%s: Applied inverter limit setting:\n%s",
                            "TESTMODE"
                            if self.coordinator.client.testmode()
                            else "LIVEMODE",
                            json.dumps(
                                resp, indent=2 if len(json.dumps(resp)) < 200 else None
                            ),
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
                        toFile=self.coordinator.client.testmode(),
                    )
                    if isinstance(resp, dict) and ALLOW_TESTMODE:
                        LOGGER.info(
                            "%s: Applied site price settings for %s change to %s:\n%s",
                            "TESTMODE"
                            if self.coordinator.client.testmode()
                            else "LIVEMODE",
                            self.entity_id,
                            option,
                            json.dumps(
                                resp, indent=2 if len(json.dumps(resp)) < 200 else None
                            ),
                        )

        # trigger coordinator update with api dictionary data
        await self.coordinator.async_refresh_data_from_apidict()

    async def _solix_ac_charge_service(
        self, service_name: str, **kwargs: Any
    ) -> dict | None:
        """Execute the defined solix ac charge action."""
        # Raise alerts to frontend
        if not (self.supported_features & AnkerSolixEntityFeature.AC_CHARGE):
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
            SERVICE_MODIFY_SOLIX_USE_TIME,
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
        if self.coordinator and hasattr(self.coordinator, "data"):
            result = False
            data: dict = self.coordinator.data.get(self.coordinator_context) or {}
            if service_name in [SERVICE_MODIFY_SOLIX_USE_TIME]:
                LOGGER.debug("%s action will be applied", service_name)
                result = await self.coordinator.client.api.set_sb2_use_time(
                    siteId=data.get("site_id") or "",
                    deviceSn=self.coordinator_context,
                    start_month=kwargs.get(START_MONTH),
                    end_month=kwargs.get(END_MONTH),
                    start_hour=kwargs.get(START_HOUR),
                    end_hour=kwargs.get(END_HOUR),
                    day_type=kwargs.get(DAY_TYPE),
                    tariff_type=kwargs.get(TARIFF),
                    tariff_price=kwargs.get(TARIFF_PRICE),
                    delete=kwargs.get(DELETE),
                    toFile=self.coordinator.client.testmode(),
                )
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
            # log resulting schedule if testmode returned dict
            if isinstance(result, dict) and ALLOW_TESTMODE:
                LOGGER.info(
                    "%s: Applied schedule for action %s:\n%s",
                    "TESTMODE" if self.coordinator.client.testmode() else "LIVEMODE",
                    service_name,
                    json.dumps(
                        result, indent=2 if len(json.dumps(result)) < 200 else None
                    ),
                )
            await self.coordinator.async_refresh_data_from_apidict()
        return None
