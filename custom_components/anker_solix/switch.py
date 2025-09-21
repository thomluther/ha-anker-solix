"""Switch platform for anker_solix."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
from typing import Any
import urllib.parse

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EXCLUDE, CONF_METHOD, CONF_PAYLOAD, EntityCategory
from homeassistant.core import HomeAssistant, SupportsResponse, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.dt import UTC

from .api_client import AnkerSolixApiClientCommunicationError, AnkerSolixApiClientError
from .const import (
    ALLOW_TESTMODE,
    ATTRIBUTION,
    BACKUP_DURATION,
    BACKUP_END,
    BACKUP_START,
    CREATE_ALL_ENTITIES,
    DOMAIN,
    ENABLE_BACKUP,
    ENDPOINT,
    EXPORTFOLDER,
    LOGGER,
    SERVICE_API_REQUEST,
    SERVICE_EXPORT_SYSTEMS,
    SERVICE_MODIFY_SOLIX_BACKUP_CHARGE,
    SOLIX_BACKUP_CHARGE_SCHEMA,
    SOLIX_ENTITY_SCHEMA,
    SOLIX_REQUEST_SCHEMA,
)
from .coordinator import AnkerSolixDataUpdateCoordinator
from .entity import (
    AnkerSolixEntityFeature,
    AnkerSolixEntityRequiredKeyMixin,
    AnkerSolixEntityType,
    AnkerSolixPicturePath,
    get_AnkerSolixAccountInfo,
    get_AnkerSolixDeviceInfo,
    get_AnkerSolixSubdeviceInfo,
    get_AnkerSolixSystemInfo,
    get_AnkerSolixVehicleInfo,
)
from .solixapi import export
from .solixapi.apitypes import SolixDeviceType


@dataclass(frozen=True)
class AnkerSolixSwitchDescription(
    SwitchEntityDescription, AnkerSolixEntityRequiredKeyMixin
):
    """Switch entity description with optional keys."""

    # Use optionally to provide function for value calculation or lookup of nested values
    value_fn: Callable[[dict, str], bool | None] = lambda d, jk: d.get(jk)
    attrib_fn: Callable[[dict], dict | None] = lambda d: None
    exclude_fn: Callable[[set, dict], bool] = lambda s, d: False
    feature: AnkerSolixEntityFeature | None = None
    force_creation_fn: Callable[[dict, str], bool] = lambda d, jk: False


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
        force_creation_fn=lambda d, jk: jk in d and d.get("cascaded"),
    ),
    AnkerSolixSwitchDescription(
        key="preset_discharge_priority",
        translation_key="preset_discharge_priority",
        json_key="preset_discharge_priority",
        exclude_fn=lambda s, _: not ({SolixDeviceType.SOLARBANK.value} - s),
        force_creation_fn=lambda d, jk: jk in d and d.get("cascaded"),
    ),
    AnkerSolixSwitchDescription(
        key="preset_backup_option",
        translation_key="preset_backup_option",
        json_key="preset_backup_option",
        feature=AnkerSolixEntityFeature.AC_CHARGE,
        exclude_fn=lambda s, _: not ({SolixDeviceType.SOLARBANK.value} - s),
    ),
    AnkerSolixSwitchDescription(
        key="allow_grid_export",
        translation_key="allow_grid_export",
        json_key="allow_grid_export",
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
        force_creation_fn=lambda d, _: True,
        value_fn=lambda d, _: len(d) > 0,
        attrib_fn=lambda d, _: {
            "requests_last_min": d.get("requests_last_min"),
            "requests_last_hour": d.get("requests_last_hour"),
        },
    ),
]

VEHICLE_SWITCHES = [
    AnkerSolixSwitchDescription(
        key="default_vehicle",
        translation_key="default_vehicle",
        json_key="is_default_vehicle",
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
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
            elif data_type == SolixDeviceType.VEHICLE.value:
                # vehicle entry in data
                entity_type = AnkerSolixEntityType.VEHICLE
                entity_list = VEHICLE_SWITCHES
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
                        desc.force_creation_fn(data, desc.json_key)
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
    platform.async_register_entity_service(
        name=SERVICE_API_REQUEST,
        schema=SOLIX_REQUEST_SCHEMA,
        func=SERVICE_API_REQUEST,
        required_features=[AnkerSolixEntityFeature.ACCOUNT_INFO],
        supports_response=SupportsResponse.ONLY,
    )
    platform.async_register_entity_service(
        name=SERVICE_MODIFY_SOLIX_BACKUP_CHARGE,
        schema=SOLIX_BACKUP_CHARGE_SCHEMA,
        func=SERVICE_MODIFY_SOLIX_BACKUP_CHARGE,
        required_features=[AnkerSolixEntityFeature.AC_CHARGE],
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
        self.last_run: datetime | None = None
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
            data = (coordinator.data.get(context, {})).get("site_info", {})
            self._attr_device_info = get_AnkerSolixSystemInfo(
                data, context, coordinator.client.api.apisession.email
            )
            # add service attribute for site entities
            self._attr_supported_features: AnkerSolixEntityFeature = description.feature

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

    async def export_systems(self, **kwargs: Any) -> dict | None:
        """Export the actual api responses for accessible systems and devices into zipped JSON files."""
        return await self._solix_account_service(
            service_name=SERVICE_EXPORT_SYSTEMS, **kwargs
        )

    async def api_request(self, **kwargs: Any) -> dict | None:
        """Submit the api request to selected entity account."""
        return await self._solix_account_service(
            service_name=SERVICE_API_REQUEST, **kwargs
        )

    async def modify_solix_backup_charge(self, **kwargs: Any) -> dict | None:
        """Modify the backup charge settings of devices supporting AC charge."""
        return await self._solix_ac_charge_service(
            service_name=SERVICE_MODIFY_SOLIX_BACKUP_CHARGE, **kwargs
        )

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
        # Skip Api calls if entity does not change
        if self._attr_is_on in [None, True]:
            return
        if self._attribute_name == "allow_refresh":
            await self.coordinator.async_execute_command(
                command=self.entity_description.key, option=True
            )
        # When running in Test mode do not switch for entities not supporting test mode
        elif self.coordinator.client.testmode() and self._attribute_name not in [
            "preset_allow_export",
            "preset_discharge_priority",
            "preset_backup_option",
            "default_vehicle",
            "allow_grid_export",
        ]:
            # Raise alert to frontend
            raise ServiceValidationError(
                f"'{self.entity_id}' cannot be used while configuration is running in testmode",
                translation_domain=DOMAIN,
                translation_key="active_testmode",
                translation_placeholders={
                    "entity_id": self.entity_id,
                },
            )
        elif self._attribute_name == "auto_upgrade":
            resp = await self.coordinator.client.api.set_auto_upgrade(
                {self.coordinator_context: True}
            )
            if isinstance(resp, dict) and ALLOW_TESTMODE:
                LOGGER.info(
                    "Applied upgrade settings for '%s' change to '%s':\n%s",
                    self.entity_id,
                    "ON",
                    json.dumps(resp, indent=2 if len(json.dumps(resp)) < 200 else None),
                )
            await self.coordinator.async_refresh_data_from_apidict()
        elif self._attribute_name == "default_vehicle":
            resp = await self.coordinator.client.api.manage_vehicle(
                vehicleId=self.coordinator_context,
                action="setdefault",
                vehicle=(self.coordinator.data or {}).get(self.coordinator_context)
                or {},
                toFile=self.coordinator.client.testmode(),
            )
            if isinstance(resp, dict) and ALLOW_TESTMODE:
                LOGGER.info(
                    "Applied toggle for '%s' change to '%s':\n%s",
                    self.entity_id,
                    "ON",
                    json.dumps(resp, indent=2 if len(json.dumps(resp)) < 200 else None),
                )
            await self.coordinator.async_refresh_data_from_apidict()
        elif self._attribute_name in [
            "preset_allow_export",
            "preset_discharge_priority",
            "preset_backup_option",
            "allow_grid_export",
        ]:
            if (
                self.coordinator
                and hasattr(self.coordinator, "data")
                and self.coordinator_context in self.coordinator.data
            ):
                data = self.coordinator.data.get(self.coordinator_context)
                LOGGER.debug("%s will be enabled", self.entity_id)
                if self._attribute_name in ["preset_backup_option"]:
                    # SB2 AC option, get cached start and end times when activating
                    resp = await self.coordinator.client.api.set_sb2_ac_charge(
                        siteId=data.get("site_id") or "",
                        deviceSn=self.coordinator_context,
                        backup_start=datetime.fromtimestamp(
                            data.get("preset_manual_backup_start") or 0, UTC
                        ).astimezone(),
                        backup_end=datetime.fromtimestamp(
                            data.get("preset_manual_backup_end") or 0, UTC
                        ).astimezone(),
                        backup_switch=True,
                        toFile=self.coordinator.client.testmode(),
                    )
                elif self._attribute_name in ["allow_grid_export"]:
                    if data.get("type") in [SolixDeviceType.COMBINER_BOX.value] or data.get("station_sn") is not None:
                        # control via station setting
                        resp = await self.coordinator.client.api.set_station_parm(
                            deviceSn=self.coordinator_context,
                            gridExport=True,
                            toFile=self.coordinator.client.testmode(),
                        )
                    else:
                        # TODO: control via individual device setting to be implemented once supported
                        resp = None
                else:
                    # SB1 schedule options
                    resp = await self.coordinator.client.api.set_home_load(
                        siteId=data.get("site_id") or "",
                        deviceSn=self.coordinator_context,
                        export=True
                        if self._attribute_name == "preset_allow_export"
                        else None,
                        discharge_prio=True
                        if self._attribute_name == "preset_discharge_priority"
                        else None,
                        toFile=self.coordinator.client.testmode(),
                    )
                if isinstance(resp, dict) and ALLOW_TESTMODE:
                    LOGGER.info(
                        "%s: Applied settings for '%s' change to '%s':\n%s",
                        "TESTMODE"
                        if self.coordinator.client.testmode()
                        else "LIVEMODE",
                        self.entity_id,
                        "ON",
                        json.dumps(
                            resp, indent=2 if len(json.dumps(resp)) < 200 else None
                        ),
                    )
                await self.coordinator.async_refresh_data_from_apidict()
            else:
                LOGGER.error(
                    "'%s' cannot be enabled because entity data was not found",
                    self.entity_id,
                )

    async def async_turn_off(self, **_: any) -> None:
        """Turn off the switch."""
        # Skip Api calls if entity does not change
        if self._attr_is_on in [None, False]:
            return
        if self._attribute_name == "allow_refresh":
            await self.coordinator.async_execute_command(
                command=self.entity_description.key, option=False
            )
        # When running in Test mode do not switch for entities not supporting test mode
        elif self.coordinator.client.testmode() and self._attribute_name not in [
            "preset_allow_export",
            "preset_discharge_priority",
            "preset_backup_option",
            "default_vehicle",
            "allow_grid_export",
        ]:
            # Raise alert to frontend
            raise ServiceValidationError(
                f"'{self.entity_id}' cannot be used while configuration is running in testmode",
                translation_domain=DOMAIN,
                translation_key="active_testmode",
                translation_placeholders={
                    "entity_id": self.entity_id,
                },
            )
        elif self._attribute_name == "auto_upgrade":
            resp = await self.coordinator.client.api.set_auto_upgrade(
                {self.coordinator_context: False}
            )
            if isinstance(resp, dict) and ALLOW_TESTMODE:
                LOGGER.info(
                    "Applied upgrade settings for '%s' change to '%s':\n%s",
                    self.entity_id,
                    "OFF",
                    json.dumps(resp, indent=2 if len(json.dumps(resp)) < 200 else None),
                )
            await self.coordinator.async_refresh_data_from_apidict()
        elif self._attribute_name == "default_vehicle":
            # if default is disabled, another registered vehicle must be enabled or disabling being skipped
            if (
                len(
                    registered := set(self.coordinator.client.get_registered_vehicles())
                )
                > 1
            ):
                # get first other vehicle from list to set as new default
                vehicleId = list(registered - {self.coordinator_context})[0]
                resp = await self.coordinator.client.api.manage_vehicle(
                    vehicleId=vehicleId,
                    action="setdefault",
                    vehicle=(self.coordinator.data or {}).get(vehicleId) or {},
                    toFile=self.coordinator.client.testmode(),
                )
                if isinstance(resp, dict) and ALLOW_TESTMODE:
                    LOGGER.info(
                        "Applied toggle for '%s' change to '%s' by enabling other vehicle as default:\n%s",
                        self.entity_id,
                        "OFF",
                        json.dumps(
                            resp, indent=2 if len(json.dumps(resp)) < 200 else None
                        ),
                    )
                await self.coordinator.async_refresh_data_from_apidict()
        elif self._attribute_name in [
            "preset_allow_export",
            "preset_discharge_priority",
            "preset_backup_option",
            "allow_grid_export",
        ]:
            if (
                self.coordinator
                and hasattr(self.coordinator, "data")
                and self.coordinator_context in self.coordinator.data
            ):
                data = self.coordinator.data.get(self.coordinator_context)
                LOGGER.debug("'%s' will be disabled", self.entity_id)
                if self._attribute_name in ["preset_backup_option"]:
                    # SB2 AC option
                    resp = await self.coordinator.client.api.set_sb2_ac_charge(
                        siteId=data.get("site_id") or "",
                        deviceSn=self.coordinator_context,
                        backup_switch=False,
                        toFile=self.coordinator.client.testmode(),
                    )
                elif self._attribute_name in ["allow_grid_export"]:
                    if data.get("type") in [SolixDeviceType.COMBINER_BOX.value] or data.get("station_sn") is not None:
                        # control via station setting
                        resp = await self.coordinator.client.api.set_station_parm(
                            deviceSn=self.coordinator_context,
                            gridExport=False,
                            toFile=self.coordinator.client.testmode(),
                        )
                    else:
                        # TODO: control via individual device setting to be implemented once supported
                        resp = None
                else:
                    # SB1 schedule options
                    resp = await self.coordinator.client.api.set_home_load(
                        siteId=data.get("site_id") or "",
                        deviceSn=self.coordinator_context,
                        export=False
                        if self._attribute_name == "preset_allow_export"
                        else None,
                        discharge_prio=False
                        if self._attribute_name == "preset_discharge_priority"
                        else None,
                        toFile=self.coordinator.client.testmode(),
                    )
                if isinstance(resp, dict) and ALLOW_TESTMODE:
                    LOGGER.info(
                        "%s: Applied settings for '%s' change to '%s':\n%s",
                        "TESTMODE"
                        if self.coordinator.client.testmode()
                        else "LIVEMODE",
                        self.entity_id,
                        "OFF",
                        json.dumps(
                            resp, indent=2 if len(json.dumps(resp)) < 200 else None
                        ),
                    )
                await self.coordinator.async_refresh_data_from_apidict()
            else:
                LOGGER.error(
                    "'%s' cannot be disabled because entity data was not found",
                    self.entity_id,
                )

    async def _solix_account_service(
        self, service_name: str, **kwargs: Any
    ) -> dict | None:
        """Execute the defined solarbank account action."""
        # Raise alerts to frontend
        if not (self.supported_features & AnkerSolixEntityFeature.ACCOUNT_INFO):
            raise ServiceValidationError(
                f"The entity '{self.entity_id}' does not support the action '{service_name}'",
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
                f"'{self.entity_id}' cannot be used while configuration is running in testmode",
                translation_domain=DOMAIN,
                translation_key="active_testmode",
                translation_placeholders={
                    "entity_id": self.entity_id,
                },
            )
        # When Api refresh is deactivated, do not run action to avoid kicking off other client Api token
        if not self.coordinator.client.allow_refresh():
            raise ServiceValidationError(
                f"'{self.entity_id}' cannot be used for requested action '{service_name}' while Api usage is deactivated",
                translation_domain=DOMAIN,
                translation_key="apiusage_deactivated",
                translation_placeholders={
                    "entity_id": self.entity_id,
                    "action_name": service_name,
                },
            )
        # Ensure Export can be triggered only once
        if self.last_run and datetime.now().astimezone() < (
            timeout := self.last_run + timedelta(minutes=10)
        ):
            LOGGER.debug(
                "The action '%s' cannot be executed again while still running",
                service_name,
            )
            # Raise alert to frontend
            raise ServiceValidationError(
                f"The action '{service_name}' cannot be executed again while still running (Timeout at {timeout.strftime('%H:%M:%S')})",
                translation_domain=DOMAIN,
                translation_key="action_blocked",
                translation_placeholders={
                    "service": service_name,
                    "timeout": timeout.strftime('%H:%M:%S'),
                },
            )
        # Reset last run after timeout (for unexpected exceptions)
        self.last_run = None
        if self.coordinator and hasattr(self.coordinator, "data"):
            if service_name in [SERVICE_EXPORT_SYSTEMS]:
                LOGGER.debug("'%s' action will be applied", service_name)
                self.last_run = datetime.now().astimezone()
                exportlogger: logging.Logger = logging.getLogger("anker_solix_export")
                exportlogger.setLevel(logging.DEBUG)
                myexport = export.AnkerSolixApiExport(
                    client=self.coordinator.client.api,
                    logger=exportlogger,
                )
                wwwroot = str(Path(self.coordinator.hass.config.config_dir) / "www")
                exportpath: str = str(
                    Path(wwwroot) / "community" / DOMAIN / EXPORTFOLDER
                )
                # Toogle coordinator client cache invalid during the cache export randomization of the randomized system export
                if await myexport.export_data(
                    export_path=exportpath,
                    toggle_cache=self.coordinator.client.toggle_cache,
                ):
                    # convert path to public available url folder and filename
                    result = urllib.parse.quote(
                        myexport.zipfilename.replace(
                            wwwroot, AnkerSolixPicturePath.LOCALPATH
                        )
                    )
                else:
                    result = None
                # Ensure to validate the coordinator client cache again
                self.coordinator.client.toggle_cache(True)
                # reset action blocker
                self.last_run = None
                return {"export_filename": result}
            if service_name in [SERVICE_API_REQUEST]:
                LOGGER.debug("%s action will be applied", service_name)
                self.last_run = datetime.now().astimezone()
                # Wait until client cache is valid
                await self.coordinator.client.validate_cache()
                try:
                    result = await self.coordinator.client.request(
                        method=kwargs.get(CONF_METHOD),
                        endpoint=kwargs.get(ENDPOINT),
                        payload=kwargs.get(CONF_PAYLOAD),
                    )
                except (
                    AnkerSolixApiClientError,
                    AnkerSolixApiClientCommunicationError,
                ) as exception:
                    return {
                        "request": {
                            "method": kwargs.get(CONF_METHOD),
                            "endpoint": kwargs.get(ENDPOINT),
                            "payload": kwargs.get(CONF_PAYLOAD),
                        },
                        "error": str(exception),
                    }
                else:
                    # only when no exception occurs
                    return {
                        "request": {
                            "server": self.coordinator.client.api.apisession.server,
                            "method": kwargs.get(CONF_METHOD),
                            "endpoint": kwargs.get(ENDPOINT),
                            "payload": kwargs.get(CONF_PAYLOAD),
                        },
                        "response": result,
                    }
                finally:
                    # always executed even upon return in except block
                    # reset action blocker
                    self.last_run = None

            raise ServiceValidationError(
                f"The entity '{self.entity_id}' does not support the action '{service_name}'",
                translation_domain=DOMAIN,
                translation_key="service_not_supported",
                translation_placeholders={
                    "entity": self.entity_id,
                    "service": service_name,
                },
            )
        return None

    async def _solix_ac_charge_service(
        self, service_name: str, **kwargs: Any
    ) -> dict | None:
        """Execute the defined solix ac charge action."""
        # Raise alerts to frontend
        if not (self.supported_features & AnkerSolixEntityFeature.AC_CHARGE):
            raise ServiceValidationError(
                f"The entity '{self.entity_id}' does not support the action '{service_name}'",
                translation_domain=DOMAIN,
                translation_key="service_not_supported",
                translation_placeholders={
                    "entity": self.entity_id,
                    "service": service_name,
                },
            )
        # When running in Test mode do not run services that are not supporting a testmode
        if self.coordinator.client.testmode() and service_name not in [
            SERVICE_MODIFY_SOLIX_BACKUP_CHARGE,
        ]:
            raise ServiceValidationError(
                f"'{self.entity_id}' cannot be used while configuration is running in testmode",
                translation_domain=DOMAIN,
                translation_key="active_testmode",
                translation_placeholders={
                    "entity_id": self.entity_id,
                },
            )
        # When Api refresh is deactivated, do not run action to avoid kicking off other client Api token
        if not self.coordinator.client.allow_refresh():
            raise ServiceValidationError(
                f"'{self.entity_id}' cannot be used for requested action '{service_name}' while Api usage is deactivated",
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
            if service_name in [SERVICE_MODIFY_SOLIX_BACKUP_CHARGE]:
                LOGGER.debug("'%s' action will be applied", service_name)
                # backup_start = None if not isinstance(kwargs.get(BACKUP_START), datetime) else kwargs.get(BACKUP_START)
                # backup_end = None if not isinstance(kwargs.get(BACKUP_END), datetime) else kwargs.get(BACKUP_END)
                # duration = None if not isinstance(kwargs.get(BACKUP_DURATION), timedelta) else kwargs.get(BACKUP_DURATION)
                result = await self.coordinator.client.api.set_sb2_ac_charge(
                    siteId=data.get("site_id") or "",
                    deviceSn=self.coordinator_context,
                    backup_start=kwargs.get(BACKUP_START),
                    backup_end=kwargs.get(BACKUP_END),
                    backup_duration=kwargs.get(BACKUP_DURATION),
                    backup_switch=kwargs.get(ENABLE_BACKUP),
                    toFile=self.coordinator.client.testmode(),
                )
                await self.coordinator.async_refresh_data_from_apidict()
            else:
                raise ServiceValidationError(
                    f"The entity '{self.entity_id}' does not support the action '{service_name}'",
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
                    "%s: Applied result for action '%s':\n%s",
                    "TESTMODE" if self.coordinator.client.testmode() else "LIVEMODE",
                    service_name,
                    json.dumps(
                        result, indent=2 if len(json.dumps(result)) < 200 else None
                    ),
                )
            await self.coordinator.async_refresh_data_from_apidict()
        return None
