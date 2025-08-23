"""Select platform for anker_solix."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
import json
import logging
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_EXCLUDE,
    PERCENTAGE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr, entity_platform
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import UNDEFINED
from homeassistant.helpers.update_coordinator import CoordinatorEntity

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
    get_AnkerSolixVehicleInfo,
)
from .solixapi.apitypes import (
    ApiCategories,
    SolarbankDeviceMetrics,
    SolarbankUsageMode,
    SolixDeviceType,
    SolixPriceProvider,
    SolixPriceTypes,
    SolixTariffTypes,
    SolixVehicle,
)


@dataclass(frozen=True)
class AnkerSolixSelectDescription(
    SelectEntityDescription, AnkerSolixEntityRequiredKeyMixin
):
    """Select entity description with optional keys."""

    force_creation_fn: Callable[[dict, str], bool] = lambda d, jk: False
    # Use optionally to provide function for value calculation or lookup of nested values
    value_fn: Callable[[dict, str], str | None] = (
        lambda d, jk: None if d.get(jk) is None else str(d.get(jk))
    )
    options_fn: Callable[[dict, str], list | None] = (
        lambda d, jk: list(d.get(jk) or []) or None
    )
    exclude_fn: Callable[[set, dict], bool] = lambda s, d: False
    attrib_fn: Callable[[dict, str], dict | None] = lambda d, jk: None
    feature: AnkerSolixEntityFeature | None = None
    restore: bool = False


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
            iter([item.name for item in SolarbankUsageMode if item.value == d.get(jk)]),
            str(d.get(jk)) if jk in d else None,
        ),
        attrib_fn=lambda d, jk: {"mode": d.get(jk)},
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
            if "unknown" not in item.name.lower()
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
        attrib_fn=lambda d, jk: {"tariff": d.get(jk)},
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
        options_fn=lambda d, _: [
            t.value for t in SolixPriceTypes if "unknown" not in t.name.lower()
        ],
        value_fn=lambda d, jk: (d.get("site_details") or {}).get(jk),
        attrib_fn=lambda d, _: {
            "type": (det := d.get("site_details") or {}).get("price_type"),
            "current_mode": det.get("current_mode"),
        },
        exclude_fn=lambda s, _: not ({ApiCategories.site_price} - s),
    ),
    AnkerSolixSelectDescription(
        # Solarbank 3 Dynamic price
        key="dynamic_price_provider",
        translation_key="dynamic_price_provider",
        json_key="dynamic_price",
        options_fn=lambda d, _: None,
        value_fn=lambda d, jk: str(SolixPriceProvider(provider=p))
        if (
            p := (d.get("site_details") or {}).get(jk)
            or (d.get("customized") or {}).get(jk)
            or {}
        )
        else None,
        attrib_fn=lambda d, jk: SolixPriceProvider(
            provider=(d.get("site_details") or {}).get(jk)
            or (d.get("customized") or {}).get(jk)
            or {}
        ).asdict()
        | ({"customized": c} if (c := (d.get("customized") or {}).get(jk)) else {}),
        exclude_fn=lambda s, _: not ({ApiCategories.site_price} - s),
        force_creation_fn=lambda d, _: bool(
            "dynamic_price_details" in (d.get("site_details") or {})
        ),
        restore=True,
    ),
]

ACCOUNT_SELECTS = []

VEHICLE_SELECTS = [
    AnkerSolixSelectDescription(
        key="vehicle_brand",
        translation_key="vehicle_brand",
        json_key="brand",
        options_fn=lambda d, _: None,
        exclude_fn=lambda s, _: not ({SolixDeviceType.VEHICLE.value} - s),
    ),
    AnkerSolixSelectDescription(
        key="vehicle_model",
        translation_key="vehicle_model",
        json_key="model",
        options_fn=lambda d, _: None,
        exclude_fn=lambda s, _: not ({SolixDeviceType.VEHICLE.value} - s),
    ),
    AnkerSolixSelectDescription(
        key="vehicle_year",
        translation_key="vehicle_year",
        json_key="productive_year",
        options_fn=lambda d, _: None,
        exclude_fn=lambda s, _: not ({SolixDeviceType.VEHICLE.value} - s),
    ),
    AnkerSolixSelectDescription(
        key="vehicle_variant",
        translation_key="vehicle_variant",
        json_key="id",
        options_fn=lambda d, _: None,
        value_fn=lambda d, jk: SolixVehicle(vehicle=d).idAttributes(),
        exclude_fn=lambda s, _: not ({SolixDeviceType.VEHICLE.value} - s),
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
        # create entity based on type of entry in coordinator data, which consolidates the api.sites, api.devices and api.account dictionaries
        # the coordinator.data dict key is either account nickname, a site_id or device_sn and used as context for the entity to lookup its data
        for context, data in coordinator.data.items():
            if (data_type := data.get("type")) == SolixDeviceType.SYSTEM.value:
                # site_id entry in data
                entity_type = AnkerSolixEntityType.SITE
                entity_list = SITE_SELECTS
            elif data_type == SolixDeviceType.ACCOUNT.value:
                # Unique key for account entry in data
                entity_type = AnkerSolixEntityType.ACCOUNT
                entity_list = ACCOUNT_SELECTS
            elif data_type == SolixDeviceType.VEHICLE.value:
                # vehicle entry in data
                entity_type = AnkerSolixEntityType.VEHICLE
                entity_list = VEHICLE_SELECTS
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
                if description.restore:
                    entity = AnkerSolixRestoreSelect(
                        coordinator, description, context, entity_type
                    )
                else:
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
            "type",
            "current_mode",
            "mode",
            "tariff",
            "country",
            "company",
            "area",
            "customized",
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
        elif self.entity_type == AnkerSolixEntityType.VEHICLE:
            # get the vehicle info data from vehicle entry of coordinator data
            data = coordinator.data.get(context) or {}
            self._attr_device_info = get_AnkerSolixVehicleInfo(
                data, context, coordinator.client.api.apisession.email
            )
            # add service attribute for vehicle entities
            self._attr_supported_features: AnkerSolixEntityFeature = description.feature
        else:
            # get the site info data from site context entry of coordinator data
            data = (coordinator.data.get(context) or {}).get("site_info") or {}
            self._attr_device_info = get_AnkerSolixSystemInfo(
                data, context, coordinator.client.api.apisession.email
            )
            # add service attribute for site entities
            self._attr_supported_features: AnkerSolixEntityFeature = description.feature

        self.update_state_value()
        self._attr_options = self.entity_description.options_fn(
            data, self.entity_description.json_key
        )
        # Initial options update for static information not changed during Api session
        if self._attribute_name == "system_price_unit":
            # merge currencies from entity description and from Api currency list
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
            self._attr_options.sort()
        # Make sure that options are set to existing state if no options defined
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
        if self._attribute_name == ("vehicle_variant"):
            # Make sure that the only available option is automatically set
            if len(self._attr_options) == 1 and self._attr_current_option in [
                "unknown",
                None,
            ]:
                self._attr_current_option = self._attr_options[0]
        return self._attr_current_option

    @property
    def options(self) -> str | None:
        """Return the entity options available."""
        # update the options depending on conditions
        if self._attribute_name == "preset_usage_mode":
            options = self.coordinator.client.api.solarbank_usage_mode_options(
                deviceSn=self.coordinator_context
            )
            if options != set(self._attr_options):
                self._attr_options = list(options)
                self._attr_options.sort()
        elif self._attribute_name == "system_price_type":
            options = self.coordinator.client.api.price_type_options(
                siteId=self.coordinator_context
            )
            if options != set(self._attr_options):
                self._attr_options = list(options)
                self._attr_options.sort()
        elif self._attribute_name == "dynamic_price_provider":
            options = self.coordinator.client.api.price_provider_options(
                siteId=self.coordinator_context
            )
            # TODO(SB3): Add None as option only if the provider can ever be removed
            # options.add("none")
            if options != set(self._attr_options):
                self._attr_options = list(options)
                self._attr_options.sort()
        elif (
            self._attribute_name == "preset_inverter_limit"
            and self._attr_current_option is not None
        ):
            options = set(self._attr_options)
            # Add actual power setting to options if not included
            options.add(self._attr_current_option)
            if options != set(self._attr_options):
                self._attr_options = list(options)
                self._attr_options.sort()
        elif self._attribute_name == "vehicle_brand":
            self._attr_options = self.coordinator.client.api.get_vehicle_options()
            self._attr_options.sort()
        elif self._attribute_name == "vehicle_model":
            data = (self.coordinator.data or {}).get(self.coordinator_context) or {}
            self._attr_options = (
                self.coordinator.client.api.get_vehicle_options(
                    vehicle=SolixVehicle(brand=brand)
                )
                if (brand := data.get("brand"))
                else []
            )
            self._attr_options.sort()
        elif self._attribute_name == "vehicle_year":
            data = (self.coordinator.data or {}).get(self.coordinator_context) or {}
            self._attr_options = (
                self.coordinator.client.api.get_vehicle_options(
                    vehicle=SolixVehicle(brand=brand, model=model)
                )
                if (brand := data.get("brand")) and (model := data.get("model"))
                else []
            )
            self._attr_options.sort()
        elif self._attribute_name == "vehicle_variant":
            data = (self.coordinator.data or {}).get(self.coordinator_context) or {}
            if (
                (brand := data.get("brand"))
                and (model := data.get("model"))
                and (year := data.get("productive_year"))
            ):
                self._attr_options = self.coordinator.client.api.get_vehicle_options(
                    vehicle=SolixVehicle(
                        brand=brand, model=model, productive_year=year
                    ),
                    extendAttributes=True,
                )
                # If current state should be added as option although no model ID could be identified
                # if (state := SolixVehicle(vehicle=data).idAttributes()) not in self._attr_options:
                #     self._attr_options.append(state)
                self._attr_options.sort()
            else:
                self._attr_options = []
        # Make sure that options are limited to existing state if no options defined
        if not self._attr_options and self._attr_current_option is not None:
            self._attr_options = [self._attr_current_option]
        return self._attr_options

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the entity."""
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

    async def async_select_option(self, option: str) -> None:  # noqa: C901
        """Change the selected option.

        Args:
            option (str): The option to set.

        """
        if (
            self.coordinator
            and self.coordinator_context in self.coordinator.data
            and (
                self._attr_current_option is not None or self.entity_description.restore
            )
        ):
            data = self.coordinator.data.get(self.coordinator_context) or {}
            customize = True
            if (
                self.coordinator.client.testmode()
                and self._attribute_name
                not in [
                    "preset_usage_mode",
                    "preset_tariff",
                    "system_price_unit",
                    "system_price_type",
                    "preset_inverter_limit",
                    "vehicle_brand",
                    "vehicle_model",
                    "vehicle_year",
                    "vehicle_variant",
                ]
                and not self.entity_description.restore
            ):
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
            # Customize cache first if restore entity
            if self.entity_description.restore:
                if self._attribute_name in ["dynamic_price_provider"]:
                    # refresh the price details for new provider prior customizing cache or switching provider
                    await self.coordinator.client.api.refresh_provider_prices(
                        provider=option,
                        siteId=self.coordinator_context,
                        fromFile=self.coordinator.client.testmode(),
                    )
                    # skip customization of cache for site owners
                    customize = not bool(data.get("site_admin"))
                # customize cache with json key
                if customize:
                    self.coordinator.client.api.customizeCacheId(
                        id=self.coordinator_context,
                        key=self.entity_description.json_key,
                        value=str(option),
                    )
                    if ALLOW_TESTMODE:
                        LOGGER.info(
                            "%s: State value of entity '%s' has been customized in Api cache to: %s",
                            "TESTMODE"
                            if self.coordinator.client.testmode()
                            else "LIVEMODE",
                            self.entity_id,
                            option,
                        )
            # Trigger Api calls depending on changed entity
            if self._attribute_name == "power_cutoff":
                LOGGER.debug(
                    "'%s' selection change to option '%s' will be applied",
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
                        resp = await self.coordinator.client.api.set_power_cutoff(
                            deviceSn=self.coordinator_context,
                            setId=int(selected_id[0]),
                        )
                        if resp and ALLOW_TESTMODE:
                            LOGGER.info(
                                "%s: Applied power cutoff settings for '%s' change to '%s':\n%s",
                                self.entity_id,
                                option,
                                json.dumps(selected_id[0], indent=2),
                            )

            elif self._attribute_name == "preset_usage_mode":
                LOGGER.debug(
                    "'%s' selection change to option '%s' will be applied",
                    self.entity_id,
                    option,
                )
                with suppress(ValueError, TypeError):
                    if not (usage_mode := getattr(SolarbankUsageMode, option, None)):
                        return
                    if usage_mode == SolarbankUsageMode.backup.value:
                        # Backup option cannot be enabled directly, instead activate backup mode switch
                        # This will reactivate an existing interval or start a new backup with default duration
                        resp = await self.coordinator.client.api.set_sb2_ac_charge(
                            siteId=data.get("site_id") or "",
                            deviceSn=self.coordinator_context,
                            backup_switch=True,
                            toFile=self.coordinator.client.testmode(),
                        )
                    else:
                        # Ensure an active backup mode will be disabled first in cache, the Api call will be done in the home load method
                        if (
                            getattr(SolarbankUsageMode, self._attr_current_option, None)
                            == SolarbankUsageMode.backup.value
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
                            "%s: Applied schedule for '%s' change to '%s':\n%s",
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
                    "'%s' selection change to option '%s' will be applied",
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
                            "%s: Applied site price settings for '%s' change to '%s':\n%s",
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
                    "'%s' selection change to option '%s' will be applied",
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
                        # change real system price unit
                        resp = await self.coordinator.client.api.set_site_price(
                            siteId=self.coordinator_context,
                            unit=option,
                            toFile=self.coordinator.client.testmode(),
                        )
                    if isinstance(resp, dict) and ALLOW_TESTMODE:
                        LOGGER.info(
                            "%s: Applied site price settings for '%s' change to '%s':\n%s",
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
                                "%s: Applied schedule for '%s' change to '%s':\n%s",
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
                        "'%s' selection change to option '%s' will be applied",
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

            # Ensure site price type changes only performed by site owners
            elif self._attribute_name in [
                "system_price_type",
                "dynamic_price_provider",
            ] and data.get("site_admin"):
                LOGGER.debug(
                    "'%s' selection change to option '%s' will be applied",
                    self.entity_id,
                    option,
                )
                with suppress(ValueError, TypeError):
                    resp = await self.coordinator.client.api.set_site_price(
                        siteId=self.coordinator_context,
                        price_type=option
                        if self._attribute_name == "system_price_type"
                        else None,
                        provider=SolixPriceProvider(provider=option)
                        if self._attribute_name == "dynamic_price_provider"
                        else None,
                        toFile=self.coordinator.client.testmode(),
                    )
                    if isinstance(resp, dict) and ALLOW_TESTMODE:
                        LOGGER.info(
                            "%s: Applied site price settings for '%s' change to '%s':\n%s",
                            "TESTMODE"
                            if self.coordinator.client.testmode()
                            else "LIVEMODE",
                            self.entity_id,
                            option,
                            json.dumps(
                                resp, indent=2 if len(json.dumps(resp)) < 200 else None
                            ),
                        )
                    # trigger dynamic price calculation refresh upon provider change
                    if self._attribute_name == "dynamic_price_provider":
                        self.coordinator.client.api.customizeCacheId(
                            id=self.coordinator_context,
                            key=self.entity_description.json_key,
                            value=str(option),
                        )

            elif self._attribute_name.startswith("vehicle_"):
                LOGGER.debug(
                    "'%s' selection change to option '%s' will be applied",
                    self.entity_id,
                    option,
                )
                data = (self.coordinator.data or {}).get(self.coordinator_context) or {}
                if self._attribute_name == "vehicle_brand":
                    vehicle = SolixVehicle(brand=str(option))
                elif self._attribute_name == "vehicle_model":
                    vehicle = SolixVehicle(brand=data.get("brand"), model=str(option))
                elif self._attribute_name == "vehicle_year":
                    vehicle = SolixVehicle(
                        brand=data.get("brand"),
                        model=data.get("model"),
                        productive_year=str(option),
                    )
                else:
                    # extract model ID from selected option
                    vehicle = SolixVehicle(
                        brand=data.get("brand"),
                        model=data.get("model"),
                        productive_year=data.get("productive_year"),
                        model_id=str(option).split("/")[0],
                    )
                # restore attributes if variant was selected, otherwise just update selected option
                resp = await self.coordinator.client.api.manage_vehicle(
                    vehicleId=self.coordinator_context,
                    action="restore"
                    if self._attribute_name == "vehicle_variant"
                    else "update",
                    vehicle=vehicle,
                    toFile=self.coordinator.client.testmode(),
                )
                if isinstance(resp, dict):
                    LOGGER.log(
                        logging.INFO if ALLOW_TESTMODE else logging.DEBUG,
                        "%s: Applied vehicle '%s' change to '%s':\n%s",
                        "TESTMODE"
                        if self.coordinator.client.testmode()
                        else "LIVEMODE",
                        self.entity_id,
                        option,
                        json.dumps(
                            resp, indent=2 if len(json.dumps(resp)) < 200 else None
                        ),
                    )
                    # trigger cache update for selected vehicle option
                    await self.coordinator.client.api.update_vehicle_options(
                        vehicle=vehicle
                    )
                    # get device registry and update the device entry attribute
                    if self._attribute_name != "vehicle_variant":
                        dev_registry = dr.async_get(self.coordinator.hass)
                        dev_registry.async_update_device(
                            self.device_entry.id,
                            manufacturer=vehicle.brand or UNDEFINED,
                            model_id=vehicle.model or UNDEFINED,
                            hw_version=str(vehicle.productive_year or "") or UNDEFINED,
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


class AnkerSolixRestoreSelect(AnkerSolixSelect, RestoreEntity):
    """anker_solix select class with restore capability."""

    def __init__(
        self,
        coordinator: AnkerSolixDataUpdateCoordinator,
        description: AnkerSolixSelectDescription,
        context: str,
        entity_type: str,
    ) -> None:
        """Initialize the select class."""
        super().__init__(coordinator, description, context, entity_type)
        self._assumed_state = True

    async def async_added_to_hass(self) -> None:
        """Load the last known state when added to hass."""
        await super().async_added_to_hass()
        # Note: Only last state object can be restored, but not extra data
        if last_state := await self.async_get_last_state():
            # First try to get customization from state attributes if last state was unknown
            if last_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                if customized := last_state.attributes.get("customized"):
                    last_state.state = customized
            if (
                last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE)
                and last_state.state in self.options
                and not self._attr_current_option
            ):
                if self._attribute_name in ["dynamic_price_provider"]:
                    # refresh the price details for restored provider
                    await self.coordinator.client.api.refresh_provider_prices(
                        provider=last_state.state,
                        siteId=self.coordinator_context,
                        fromFile=self.coordinator.client.testmode(),
                    )
                # set last known option as current option if not available
                self._attr_current_option = last_state.state
                LOGGER.info(
                    "Restored state value of entity '%s' to: %s",
                    self.entity_id,
                    last_state.state,
                )
                # customize cache with json key
                self.coordinator.client.api.customizeCacheId(
                    id=self.coordinator_context,
                    key=self.entity_description.json_key,
                    value=str(last_state.state),
                )
                await self.coordinator.async_refresh_data_from_apidict(delayed=True)
