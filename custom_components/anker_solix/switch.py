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

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_EXCLUDE,
    CONF_METHOD,
    CONF_PAYLOAD,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    EntityCategory,
)
from homeassistant.core import HomeAssistant, SupportsResponse, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
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
    INCLUDE_MQTT,
    LOGGER,
    MQTT_OVERLAY,
    SERVICE_API_REQUEST,
    SERVICE_EXPORT_SYSTEMS,
    SERVICE_MODIFY_SOLIX_BACKUP_CHARGE,
    SOLIX_BACKUP_CHARGE_SCHEMA,
    SOLIX_EXPORT_SCHEMA,
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
from .solixapi.mqtt_device import SolixMqttDevice
from .solixapi.mqttcmdmap import SolixMqttCommands


@dataclass(frozen=True)
class AnkerSolixSwitchDescription(
    SwitchEntityDescription, AnkerSolixEntityRequiredKeyMixin
):
    """Switch entity description with optional keys."""

    feature: AnkerSolixEntityFeature | None = None
    restore: bool = False
    mqtt: bool = False
    mqtt_cmd: str | None = None
    mqtt_cmd_parm: str | None = None
    api_cmd: bool | None = None
    inverted: bool = False

    # Use optionally to provide function for value calculation or lookup of nested values
    value_fn: Callable[[dict, str], bool | None] = lambda d, jk: d.get(jk)
    attrib_fn: Callable[[dict, str], dict | None] = lambda d, ctx: None
    exclude_fn: Callable[[set, dict], bool] = lambda s, d: False
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
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        force_creation_fn=lambda d, jk: jk in d and d.get("cascaded"),
    ),
    AnkerSolixSwitchDescription(
        key="preset_discharge_priority",
        translation_key="preset_discharge_priority",
        json_key="preset_discharge_priority",
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        force_creation_fn=lambda d, jk: jk in d and d.get("cascaded"),
    ),
    AnkerSolixSwitchDescription(
        key="preset_backup_option",
        translation_key="preset_backup_option",
        json_key="preset_backup_option",
        feature=AnkerSolixEntityFeature.AC_CHARGE,
        exclude_fn=lambda s, d: not (
            {d.get("type")} - s
            and (not (sn := d.get("station_sn")) or sn == d.get("device_sn"))
        ),
    ),
    AnkerSolixSwitchDescription(
        key="allow_grid_export",
        translation_key="allow_grid_export",
        json_key="allow_grid_export",
        value_fn=lambda d, jk: (
            not v if (v := d.get("grid_export_disabled")) is not None else d.get(jk)
        )
        if d.get(MQTT_OVERLAY)
        else (
            v
            if (v := d.get(jk)) is not None
            else not v
            if (v := d.get("grid_export_disabled")) is not None
            else None
        ),
        exclude_fn=lambda s, d: not (
            {d.get("type")} - s
            and (not (sn := d.get("station_sn")) or sn == d.get("device_sn"))
        ),
        mqtt=True,
        mqtt_cmd=SolixMqttCommands.sb_disable_grid_export_switch,
        mqtt_cmd_parm="set_disable_grid_export_switch",
        api_cmd=True,
    ),
    AnkerSolixSwitchDescription(
        # SB Light switch
        key="light_switch",
        translation_key="light_switch",
        json_key="light_off_switch",
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        device_class=SwitchDeviceClass.SWITCH,
        mqtt=True,
        mqtt_cmd=SolixMqttCommands.sb_light_switch,
        inverted=True,
    ),
    AnkerSolixSwitchDescription(
        # PPS Light switch
        key="light_switch",
        translation_key="light_switch",
        json_key="light_switch",
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        device_class=SwitchDeviceClass.SWITCH,
        mqtt=True,
        mqtt_cmd=SolixMqttCommands.light_switch,
    ),
    AnkerSolixSwitchDescription(
        # Customizable device option for MQTT value overlay
        key=MQTT_OVERLAY,
        translation_key=MQTT_OVERLAY,
        json_key=MQTT_OVERLAY,
        entity_category=EntityCategory.DIAGNOSTIC,
        attrib_fn=lambda d, _: {"customized": c}
        if (c := (d.get("customized") or {}).get(MQTT_OVERLAY)) is not None
        else {},
        exclude_fn=lambda s, d: not (({d.get("type")} - s) and d.get("mqtt_data")),
        restore=True,
        mqtt=True,
    ),
    AnkerSolixSwitchDescription(
        key="ac_socket_switch",
        translation_key="ac_socket_switch",
        json_key="ac_socket_switch",
        device_class=SwitchDeviceClass.OUTLET,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
        mqtt_cmd=SolixMqttCommands.sb_ac_socket_switch,
    ),
    AnkerSolixSwitchDescription(
        key="ac_output_power_switch",
        translation_key="ac_output_power_switch",
        json_key="ac_output_power_switch",
        device_class=SwitchDeviceClass.OUTLET,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
        mqtt_cmd=SolixMqttCommands.ac_output_switch,
    ),
    AnkerSolixSwitchDescription(
        key="dc_output_power_switch",
        translation_key="dc_output_power_switch",
        json_key="dc_output_power_switch",
        device_class=SwitchDeviceClass.OUTLET,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        mqtt=True,
        mqtt_cmd=SolixMqttCommands.dc_output_switch,
    ),
    AnkerSolixSwitchDescription(
        key="ac_charge_switch",
        translation_key="ac_charge_switch",
        json_key="ac_charge_switch",
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        device_class=SwitchDeviceClass.SWITCH,
        mqtt=True,
        mqtt_cmd=SolixMqttCommands.ac_charge_switch,
    ),
    AnkerSolixSwitchDescription(
        key="ac_fast_charge_switch",
        translation_key="ac_fast_charge_switch",
        json_key="ac_fast_charge_switch",
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        device_class=SwitchDeviceClass.SWITCH,
        mqtt=True,
        mqtt_cmd=SolixMqttCommands.ac_fast_charge_switch,
    ),
    AnkerSolixSwitchDescription(
        key="display_switch",
        translation_key="display_switch",
        json_key="display_switch",
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        device_class=SwitchDeviceClass.SWITCH,
        mqtt=True,
        mqtt_cmd=SolixMqttCommands.display_switch,
    ),
    AnkerSolixSwitchDescription(
        key="port_memory_switch",
        translation_key="port_memory_switch",
        json_key="port_memory_switch",
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
        device_class=SwitchDeviceClass.SWITCH,
        mqtt=True,
        mqtt_cmd=SolixMqttCommands.port_memory_switch,
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
                            # include MQTT command switch entities only if switch options or also using Api command
                            and (
                                desc.api_cmd
                                or not (
                                    mdev
                                    and desc.mqtt_cmd
                                    and not mdev.cmd_is_switch(
                                        desc.mqtt_cmd, parm=desc.mqtt_cmd_parm
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
                    entity = AnkerSolixRestoreSwitch(
                        coordinator, description, context, entity_type
                    )
                else:
                    entity = AnkerSolixSwitch(
                        coordinator, description, context, entity_type
                    )
                entities.append(entity)

    # create the sensors from the list
    async_add_entities(entities)

    # register the entity services
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        name=SERVICE_EXPORT_SYSTEMS,
        schema=SOLIX_EXPORT_SCHEMA,
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
    _unrecorded_attributes = frozenset(
        {
            "requests_last_min",
            "requests_last_hour",
            "customized",
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
        self._attr_attribution = f"{ATTRIBUTION}{' + MQTT' if description.mqtt else ''}"
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
            self._attr_is_on = self.entity_description.value_fn(data, key)
        else:
            self._attr_is_on = self.entity_description.value_fn(
                self.coordinator.data, self.entity_description.json_key
            )
        if self._attr_is_on is not None:
            # invert the state for inverted switch entity
            self._attr_is_on ^= self.entity_description.inverted

        # Mark availability based on value
        self._attr_available = self._attr_is_on is not None

    async def async_turn_on(self, **_: any) -> None:
        """Turn on the switch."""
        await self._async_toggle(enable=True)

    async def async_turn_off(self, **_: any) -> None:
        """Turn off the switch."""
        await self._async_toggle(enable=False)

    async def _async_toggle(self, enable: bool) -> None:
        """Enable or disable the entity."""
        # Skip Api calls if entity does not change
        if self._attr_is_on in [None, enable]:
            return
        if self._attribute_name == "allow_refresh":
            await self.coordinator.async_execute_command(
                command=self.entity_description.key,
                option=enable ^ self.entity_description.inverted,
            )
            return
        # When running in Test mode do not switch for entities not supporting test mode
        if (
            self.coordinator.client.testmode()
            and self._attribute_name
            not in [
                "preset_allow_export",
                "preset_discharge_priority",
                "preset_backup_option",
                "default_vehicle",
                "allow_grid_export",
                MQTT_OVERLAY,
            ]
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
        # Wait until client cache is valid before applying any api change
        await self.coordinator.client.validate_cache()
        mdev = self.coordinator.client.get_mqtt_device(self.coordinator_context)
        if self.entity_description.restore:
            LOGGER.info(
                "%s will be %s",
                self.entity_id,
                "enabled" if enable else "disabled",
            )
            # Customize cache if restore entity
            value = enable ^ self.entity_description.inverted
            self.coordinator.client.api.customizeCacheId(
                id=self.coordinator_context,
                key=self.entity_description.json_key,
                value=value,
            )
            if ALLOW_TESTMODE:
                LOGGER.info(
                    "%s: State value of entity '%s' has been customized in Api cache to: %s",
                    "TESTMODE" if self.coordinator.client.testmode() else "LIVEMODE",
                    self.entity_id,
                    value,
                )
            await self.coordinator.async_refresh_data_from_apidict()
        elif self._attribute_name == "auto_upgrade":
            resp = await self.coordinator.client.api.set_auto_upgrade(
                devices={
                    self.coordinator_context: enable ^ self.entity_description.inverted
                }
            )
            if isinstance(resp, dict) and ALLOW_TESTMODE:
                LOGGER.info(
                    "Applied upgrade settings for '%s' change to '%s':\n%s",
                    self.entity_id,
                    "ON" if enable else "OFF",
                    json.dumps(resp, indent=2 if len(json.dumps(resp)) < 200 else None),
                )
            await self.coordinator.async_refresh_data_from_apidict()
        elif self._attribute_name == "default_vehicle":
            # if default is disabled, another registered vehicle must be enabled or disabling being skipped
            if (enable ^ self.entity_description.inverted) or len(
                registered := set(self.coordinator.client.get_registered_vehicles())
            ) > 1:
                if enable ^ self.entity_description.inverted:
                    vehicleId = self.coordinator_context
                else:
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
                        "Applied toggle for '%s' change to '%s' by enabling %svehicle as default:\n%s",
                        self.entity_id,
                        "ON" if enable else "OFF",
                        "" if enable else "other ",
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
                resp = None
                LOGGER.debug(
                    "'%s' will be %s",
                    self.entity_id,
                    "enabled" if enable else "disabled",
                )
                if self._attribute_name in ["preset_backup_option"]:
                    # SB2 AC option
                    resp = await self.coordinator.client.api.set_sb2_ac_charge(
                        siteId=data.get("site_id") or "",
                        deviceSn=self.coordinator_context,
                        backup_start=datetime.fromtimestamp(
                            data.get("preset_manual_backup_start") or 0, UTC
                        ).astimezone()
                        if enable ^ self.entity_description.inverted
                        else None,
                        backup_end=datetime.fromtimestamp(
                            data.get("preset_manual_backup_end") or 0, UTC
                        ).astimezone()
                        if enable ^ self.entity_description.inverted
                        else None,
                        backup_switch=enable ^ self.entity_description.inverted,
                        toFile=self.coordinator.client.testmode(),
                    )
                elif self._attribute_name in ["allow_grid_export"]:
                    if (
                        data.get("type") in [SolixDeviceType.COMBINER_BOX.value]
                        or data.get("station_sn") is not None
                    ):
                        # control station settings via Api
                        resp = await self.coordinator.client.api.set_station_parm(
                            deviceSn=self.coordinator_context,
                            gridExport=enable ^ self.entity_description.inverted,
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
                                f"mqtt_control_{md.sn}": await self._async_mqtt_toggle(
                                    mdev=md,
                                    enable=not enable,  # only MQTT control is inverted
                                    # re-use same existing limit (no MQTT state)
                                    parm_map={
                                        "set_grid_export_limit": int(
                                            mdev.device.get("grid_export_limit", 0)
                                        )
                                    },
                                )
                            }
                else:
                    # SB1 schedule options
                    resp = await self.coordinator.client.api.set_home_load(
                        siteId=data.get("site_id") or "",
                        deviceSn=self.coordinator_context,
                        export=(enable ^ self.entity_description.inverted)
                        if self._attribute_name == "preset_allow_export"
                        else None,
                        discharge_prio=(enable ^ self.entity_description.inverted)
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
                        "ON" if enable else "OFF",
                        json.dumps(
                            resp, indent=2 if len(json.dumps(resp)) < 200 else None
                        ),
                    )
                await self.coordinator.async_refresh_data_from_apidict()
            else:
                LOGGER.error(
                    "'%s' cannot be toggled because entity data was not found",
                    self.entity_id,
                )
        # Trigger MQTT commands depending on changed entity
        elif self.entity_description.mqtt_cmd and mdev:
            LOGGER.debug(
                "'%s' will be %s via MQTT command '%s'",
                self.entity_id,
                "enabled" if enable else "disabled",
                self.entity_description.mqtt_cmd,
            )
            await self._async_mqtt_toggle(mdev=mdev, enable=enable)

    async def _async_mqtt_toggle(
        self,
        mdev: SolixMqttDevice,
        enable: bool,
        cmd: str | None = None,
        parm: str | None = None,
        parm_map: dict | None = None,
    ) -> dict | None:
        """Enable or disable the entity via MQTT device control."""
        resp = None
        if not isinstance(cmd, str):
            cmd = self.entity_description.mqtt_cmd
        if not isinstance(parm, str):
            parm = self.entity_description.mqtt_cmd_parm
        try:
            cmdvalue = enable ^ self.entity_description.inverted
            resp = await mdev.run_command(
                cmd=cmd,
                parm=parm,
                value=1 if cmdvalue else 0,
                parm_map=parm_map,
                toFile=self.coordinator.client.testmode(),
            )
            if isinstance(resp, dict) and ALLOW_TESTMODE:
                LOGGER.info(
                    "%s: Applied MQTT command '%s' for '%s' toggle to '%s':\n%s",
                    "TESTMODE" if self.coordinator.client.testmode() else "LIVEMODE",
                    cmd,
                    self.entity_id,
                    "ON" if enable else "OFF",
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
                    "'%s' could not be toggled via MQTT command '%s'",
                    self.entity_id,
                    cmd,
                )
        except (ValueError, TypeError) as err:
            LOGGER.error(
                "'%s' could not be toggled via MQTT command '%s':\n%s",
                self.entity_id,
                cmd,
                str(err),
            )
        return resp

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
        # Ensure Export can be triggered only once and startup is finished
        if self.coordinator.client.startup and not self.last_run:
            self.last_run = datetime.now().astimezone() - timedelta(minutes=9)
        if self.last_run and datetime.now().astimezone() < (
            timeout := self.last_run + timedelta(minutes=10)
        ):
            LOGGER.debug(
                "The action '%s' cannot be executed again while still running or startup in progress",
                service_name,
            )
            # Raise alert to frontend
            raise ServiceValidationError(
                f"The action '{service_name}' cannot be executed again while still running or startup in progress (Timeout at {timeout.strftime('%H:%M:%S')})",
                translation_domain=DOMAIN,
                translation_key="action_blocked",
                translation_placeholders={
                    "service": service_name,
                    "timeout": timeout.strftime("%H:%M:%S"),
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
                try:
                    if await myexport.export_data(
                        export_path=exportpath,
                        mqttdata=bool(kwargs.get(INCLUDE_MQTT)),
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
                except (
                    AnkerSolixApiClientError,
                    AnkerSolixApiClientCommunicationError,
                ) as exception:
                    result = {
                        "error": str(exception),
                    }
                finally:
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
                if not isinstance(result, dict):
                    raise ServiceValidationError(
                        f"The action '{service_name}' failed, review log for error details",
                        translation_domain=DOMAIN,
                        translation_key="service_error",
                        translation_placeholders={
                            "service": service_name,
                        },
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


class AnkerSolixRestoreSwitch(AnkerSolixSwitch, RestoreEntity):
    """anker_solix switch class with restore capability."""

    def __init__(
        self,
        coordinator: AnkerSolixDataUpdateCoordinator,
        description: AnkerSolixSwitchDescription,
        context: str,
        entity_type: str,
    ) -> None:
        """Initialize the switch class."""
        super().__init__(coordinator, description, context, entity_type)
        self._assumed_state = True

    async def async_added_to_hass(self) -> None:
        """Load the last known state when added to hass."""
        await super().async_added_to_hass()
        if last_state := await self.async_get_last_state():
            # First try to get customization from state attributes if last state was unknown
            if last_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                if (customized := last_state.attributes.get("customized")) is not None:
                    last_state.state = STATE_ON if customized else STATE_OFF
            if (
                last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE)
                and self._attr_is_on is not None
            ):
                # set the customized value if it was modified
                # NOTE: State may have string representation of boolean according to device class
                if self._attr_is_on != (last_state.state == STATE_ON):
                    self._attr_is_on = last_state.state == STATE_ON
                    LOGGER.info(
                        "Restored state value of entity '%s' to: %s",
                        self.entity_id,
                        last_state.state,
                    )
                    self.coordinator.client.api.customizeCacheId(
                        id=self.coordinator_context,
                        key=self.entity_description.json_key,
                        value=self._attr_is_on,
                    )
                    await self.coordinator.async_refresh_data_from_apidict(delayed=True)
