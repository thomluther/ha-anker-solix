"""Switch platform for anker_solix."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
import json
import logging
from pathlib import Path
from typing import Any
import urllib.parse

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EXCLUDE, EntityCategory
from homeassistant.core import HomeAssistant, SupportsResponse, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION,
    CREATE_ALL_ENTITIES,
    DOMAIN,
    EXPORTFOLDER,
    LOGGER,
    SERVICE_EXPORT_SYSTEMS,
    SOLIX_ENTITY_SCHEMA,
)
from .coordinator import AnkerSolixDataUpdateCoordinator
from .entity import (
    AnkerSolixEntityFeature,
    AnkerSolixEntityRequiredKeyMixin,
    AnkerSolixEntityType,
    AnkerSolixPicturePath,
    get_AnkerSolixAccountInfo,
    get_AnkerSolixDeviceInfo,
    get_AnkerSolixSystemInfo,
)
from .solixapi import export
from .solixapi.apitypes import SolixDeviceType


@dataclass(frozen=True)
class AnkerSolixSwitchDescription(
    SwitchEntityDescription, AnkerSolixEntityRequiredKeyMixin
):
    """Switch entity description with optional keys."""

    force_creation: bool = False
    # Use optionally to provide function for value calculation or lookup of nested values
    value_fn: Callable[[dict, str], bool | None] = lambda d, jk: d.get(jk)
    attrib_fn: Callable[[dict], dict | None] = lambda d: None
    exclude_fn: Callable[[set, dict], bool] = lambda s, _: False
    feature: AnkerSolixEntityFeature | None = None


DEVICE_SWITCHES = [
    AnkerSolixSwitchDescription(
        key="auto_upgrade",
        translation_key="auto_upgrade",
        json_key="auto_upgrade",
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
    ),
    AnkerSolixSwitchDescription(
        key="preset_allow_export",
        translation_key="preset_allow_export",
        json_key="preset_allow_export",
        exclude_fn=lambda s, _: not ({SolixDeviceType.SOLARBANK.value} - s),
    ),
    AnkerSolixSwitchDescription(
        key="preset_discharge_priority",
        translation_key="preset_discharge_priority",
        json_key="preset_discharge_priority",
        exclude_fn=lambda s, _: not ({SolixDeviceType.SOLARBANK.value} - s),
    ),
]


SITE_SWITCHES = []


ACCOUNT_SWITCHES = [
    AnkerSolixSwitchDescription(
        key="allow_refresh",
        translation_key="allow_refresh",
        json_key="allow_refresh",
        entity_category=EntityCategory.DIAGNOSTIC,
        feature=AnkerSolixEntityFeature.ACCOUNT_INFO,
        force_creation=True,
        value_fn=lambda d, _: len(d) > 0,
        attrib_fn=lambda d, _: {
            "requests_last_min": d.get("requests_last_min"),
            "requests_last_hour": d.get("requests_last_hour"),
        },
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
        # create entity based on type of entry in coordinator data, which consolidates the api.sites, api.devices and api.account dictionaries
        # the coordinator.data dict key is either account nickname, a site_id or device_sn and used as context for the entity to lookup its data
        for context, data in coordinator.data.items():
            if (data_type := data.get("type")) == SolixDeviceType.SYSTEM.value:
                # Unique key for site_id entry in data
                entity_type = AnkerSolixEntityType.SITE
                entity_list = SITE_SWITCHES
            elif data_type == SolixDeviceType.ACCOUNT.value:
                # Unique key for account entry in data
                entity_type = AnkerSolixEntityType.ACCOUNT
                entity_list = ACCOUNT_SWITCHES
            else:
                # device_sn entry in data
                entity_type = AnkerSolixEntityType.DEVICE
                entity_list = DEVICE_SWITCHES

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
                sensor = AnkerSolixSwitch(
                    coordinator, description, context, entity_type
                )
                entities.append(sensor)

    # create the sensors from the list
    async_add_entities(entities)

    # register the entity services
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        name=SERVICE_EXPORT_SYSTEMS,
        schema=SOLIX_ENTITY_SCHEMA,
        func=SERVICE_EXPORT_SYSTEMS,
        required_features=[AnkerSolixEntityFeature.ACCOUNT_INFO],
        supports_response=SupportsResponse.ONLY,
    )


class AnkerSolixSwitch(CoordinatorEntity, SwitchEntity):
    """anker_solix switch class."""

    coordinator: AnkerSolixDataUpdateCoordinator
    entity_description: AnkerSolixSwitchDescription
    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    _unrecorded_attributes = frozenset(
        {
            "requests_last_min",
            "requests_last_hour",
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
            self._attr_device_info = get_AnkerSolixDeviceInfo(
                data, context, coordinator.client.api.apisession.email
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

        self._attr_is_on = None
        self.update_state_value()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.update_state_value()
        super()._handle_coordinator_update()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the entity."""
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

    async def export_systems(self, **kwargs: Any) -> dict | None:
        """Export the actual api responses for accessible systems and devices into zipped JSON files."""
        return await self._solix_account_service(
            service_name=SERVICE_EXPORT_SYSTEMS, **kwargs
        )

    async def async_turn_on(self, **_: any) -> None:
        """Turn on the switch."""
        if self._attribute_name == "allow_refresh":
            await self.coordinator.async_execute_command(
                command=self.entity_description.key, option=True
            )
        # When running in Test mode do not switch for entities not supporting test mode
        elif self.coordinator.client.testmode() and self._attribute_name not in [
            "preset_allow_export",
            "preset_discharge_priority",
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
        elif self._attribute_name == "auto_upgrade":
            # When running in Test mode do not switch
            if not self.coordinator.client.testmode():
                await self.coordinator.client.api.set_auto_upgrade(
                    {self.coordinator_context: True}
                )
                await self.coordinator.async_refresh_data_from_apidict()
        elif self._attribute_name in [
            "preset_allow_export",
            "preset_discharge_priority",
        ]:
            if (
                self.coordinator
                and hasattr(self.coordinator, "data")
                and self.coordinator_context in self.coordinator.data
            ):
                data = self.coordinator.data.get(self.coordinator_context)
                LOGGER.debug("%s will be enabled", self.entity_id)
                resp = await self.coordinator.client.api.set_home_load(
                    siteId=data.get("site_id") or "",
                    deviceSn=self.coordinator_context,
                    export=True if self._attribute_name == "preset_allow_export" else None,
                    discharge_prio=True if self._attribute_name == "preset_discharge_priority" else None,
                    test_schedule=data.get("schedule") or {}
                    if self.coordinator.client.testmode()
                    else None,
                )
                if isinstance(resp, dict) and self.coordinator.client.testmode():
                    LOGGER.info(
                        "TESTMODE ONLY: Resulting schedule to be applied:\n%s",
                        json.dumps(resp, indent=2),
                    )
                await self.coordinator.async_refresh_data_from_apidict()
            else:
                LOGGER.error(
                    "%s cannot be enabled because entity data was not found",
                    self.entity_id,
                )

    async def async_turn_off(self, **_: any) -> None:
        """Turn off the switch."""
        if self._attribute_name == "allow_refresh":
            await self.coordinator.async_execute_command(
                command=self.entity_description.key, option=False
            )
        # When running in Test mode do not switch for entities not supporting test mode
        elif self.coordinator.client.testmode() and self._attribute_name not in [
            "preset_allow_export",
            "preset_discharge_priority",
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
        elif self._attribute_name == "auto_upgrade":
            await self.coordinator.client.api.set_auto_upgrade(
                {self.coordinator_context: False}
            )
            await self.coordinator.async_refresh_data_from_apidict()
        elif self._attribute_name in [
            "preset_allow_export",
            "preset_discharge_priority",
        ]:
            if (
                self.coordinator
                and hasattr(self.coordinator, "data")
                and self.coordinator_context in self.coordinator.data
            ):
                data = self.coordinator.data.get(self.coordinator_context)
                LOGGER.debug("%s will be disabled", self.entity_id)
                resp = await self.coordinator.client.api.set_home_load(
                    siteId=data.get("site_id") or "",
                    deviceSn=self.coordinator_context,
                    export=False if self._attribute_name == "preset_allow_export" else None,
                    discharge_prio=False if self._attribute_name == "preset_discharge_priority" else None,
                    test_schedule=data.get("schedule") or {}
                    if self.coordinator.client.testmode()
                    else None,
                )
                if isinstance(resp, dict) and self.coordinator.client.testmode():
                    LOGGER.info(
                        "TESTMODE ONLY: Resulting schedule to be applied:\n%s",
                        json.dumps(resp, indent=2),
                    )
                await self.coordinator.async_refresh_data_from_apidict()
            else:
                LOGGER.error(
                    "%s cannot be disabled because entity data was not found",
                    self.entity_id,
                )

    async def _solix_account_service(
        self, service_name: str, **kwargs: Any
    ) -> dict | None:
        """Execute the defined solarbank account action."""
        # Raise alerts to frontend
        if not (self.supported_features & AnkerSolixEntityFeature.ACCOUNT_INFO):
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
        if self.coordinator.client.testmode() and service_name not in []:
            raise ServiceValidationError(
                f"{self.entity_id} cannot be used for requested action while running in testmode",
                translation_domain=DOMAIN,
                translation_key="active_testmode",
                translation_placeholders={
                    "entity_id": self.entity_id,
                },
            )
        # When Api refresh is deactivated, do not run action to avoid kicking off other client Api token
        if not self.coordinator.client.allow_refresh():
            raise ServiceValidationError(
                f"{self.entity_id} cannot be used for requested action while Api usage is deactivated",
                translation_domain=DOMAIN,
                translation_key="apiusage_deactivated",
                translation_placeholders={
                    "entity_id": self.entity_id,
                },
            )
        if self.coordinator and hasattr(self.coordinator, "data"):
            if service_name in [SERVICE_EXPORT_SYSTEMS]:
                LOGGER.debug("%s action will be applied", service_name)
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
                f"The entity {self.entity_id} does not support the action {service_name}",
                translation_domain=DOMAIN,
                translation_key="service_not_supported",
                translation_placeholders={
                    "entity": self.entity_id,
                    "service": service_name,
                },
            )
        return None
