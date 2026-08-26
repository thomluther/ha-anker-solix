"""Datetime platform for anker_solix."""

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
import json
import logging
from typing import Any

from homeassistant.components.datetime import DateTimeEntity, DateTimeEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EXCLUDE
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

# from homeassistant.util.dt import UTC
from .const import (
    ALLOW_TESTMODE,
    ATTRIBUTION,
    CREATE_ALL_ENTITIES,
    DOMAIN,
    LOGGER,
    MQTT_OVERLAY,
)
from .coordinator import AnkerSolixDataUpdateCoordinator
from .entity import (
    AnkerSolixEntityRequiredKeyMixin,
    AnkerSolixEntityType,
    get_AnkerSolixAccountInfo,
    get_AnkerSolixDeviceInfo,
    get_AnkerSolixSubdeviceInfo,
    get_AnkerSolixSystemInfo,
    get_AnkerSolixVehicleInfo,
)
from .solixapi.apitypes import SolixDeviceType
from .solixapi.mqtt_device import SolixMqttDevice
from .solixapi.mqttcmdmap import SolixMqttCommands


@dataclass(frozen=True)
class AnkerSolixDateTimeDescription(
    DateTimeEntityDescription, AnkerSolixEntityRequiredKeyMixin
):
    """DateTime entity description with optional keys."""

    force_creation: bool = False
    mqtt: bool = False
    mqtt_cmd: str | None = None
    mqtt_cmd_parm: str | None = None
    api_cmd: bool | None = None
    # Use optionally to provide function for value calculation or lookup of nested values
    value_fn: Callable[[dict, str], StateType | None] = lambda d, jk: d.get(jk)
    unit_fn: Callable[[dict], str | None] = lambda d: None
    attrib_fn: Callable[[dict, str], dict | None] = lambda d, jk: None
    exclude_fn: Callable[[set, dict], bool] = lambda s, d: False


DEVICE_DATETIMES = [
    AnkerSolixDateTimeDescription(
        key="preset_manual_backup_start",
        translation_key="preset_manual_backup_start",
        json_key="preset_manual_backup_start",
        value_fn=lambda d, jk: (
            datetime.fromtimestamp(int(v)).astimezone()
            if (
                v := str(d.get("backup_start_timestamp", "")) or str(d.get(jk, ""))
                if d.get(MQTT_OVERLAY)
                else str(d.get(jk, "")) or str(d.get("backup_start_timestamp", ""))
            )
            .replace(".", "", 1)
            .isdigit()
            else None
        ),
        exclude_fn=lambda s, d: (
            not (
                ({d.get("type")} - s)
                & {
                    SolixDeviceType.SOLARBANK.value,
                    SolixDeviceType.COMBINER_BOX.value,
                }
                and d.get("preset_manual_backup_start")
                and (not (sn := d.get("station_sn")) or sn == d.get("device_sn"))
            )
        ),
        mqtt=True,
        api_cmd=True,
    ),
    AnkerSolixDateTimeDescription(
        key="preset_manual_backup_end",
        translation_key="preset_manual_backup_end",
        json_key="preset_manual_backup_end",
        value_fn=lambda d, jk: (
            datetime.fromtimestamp(int(v)).astimezone()
            if (
                v := str(d.get("backup_end_timestamp", "")) or str(d.get(jk, ""))
                if d.get(MQTT_OVERLAY)
                else str(d.get(jk, "")) or str(d.get("backup_end_timestamp", ""))
            )
            .replace(".", "", 1)
            .isdigit()
            else None
        ),
        exclude_fn=lambda s, d: (
            not (
                ({d.get("type")} - s)
                & {
                    SolixDeviceType.SOLARBANK.value,
                    SolixDeviceType.COMBINER_BOX.value,
                }
                and d.get("preset_manual_backup_end")
                and (not (sn := d.get("station_sn")) or sn == d.get("device_sn"))
            )
        ),
        mqtt=True,
        api_cmd=True,
    ),
    AnkerSolixDateTimeDescription(
        key="pps_manual_backup_start",
        translation_key="preset_manual_backup_start",
        json_key="backup_start_timestamp",
        value_fn=lambda d, jk: (
            datetime.fromtimestamp(int(v)).astimezone()
            if str(
                v := d.get("customized", {}).get("backup_plan", {}).get(jk, "")
                or d.get(jk, "")
            )
            else None
        ),
        exclude_fn=lambda s, d: (
            not (
                ({d.get("type")} - s)
                & {
                    SolixDeviceType.PPS.value,
                }
            )
        ),
        mqtt=True,
        mqtt_cmd=SolixMqttCommands.backup_charge_timestamps,
        mqtt_cmd_parm="set_backup_start_timestamp",
    ),
    AnkerSolixDateTimeDescription(
        key="pps_manual_backup_end",
        translation_key="preset_manual_backup_end",
        json_key="backup_end_timestamp",
        value_fn=lambda d, jk: (
            datetime.fromtimestamp(int(v)).astimezone()
            if str(
                v := d.get("customized", {}).get("backup_plan", {}).get(jk, "")
                or d.get(jk, "")
            )
            else None
        ),
        exclude_fn=lambda s, d: (
            not (
                ({d.get("type")} - s)
                & {
                    SolixDeviceType.PPS.value,
                }
            )
        ),
        mqtt=True,
        mqtt_cmd=SolixMqttCommands.backup_charge_timestamps,
        mqtt_cmd_parm="set_backup_end_timestamp",
    ),
]

SITE_DATETIMES = []

ACCOUNT_DATETIMES = []

VEHICLE_DATETIMES = []


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up datetime platform."""

    coordinator = hass.data[DOMAIN].get(entry.entry_id)
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
                entity_list = SITE_DATETIMES
            elif data_type == SolixDeviceType.ACCOUNT.value:
                # Unique key for account entry in data
                entity_type = AnkerSolixEntityType.ACCOUNT
                entity_list = ACCOUNT_DATETIMES
            elif data_type == SolixDeviceType.VEHICLE.value:
                # vehicle entry in data
                entity_type = AnkerSolixEntityType.VEHICLE
                entity_list = VEHICLE_DATETIMES
            else:
                # device_sn entry in data
                entity_type = AnkerSolixEntityType.DEVICE
                entity_list = DEVICE_DATETIMES
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
                        desc.force_creation
                        # filter MQTT entities and provide combined or only api cache
                        # Entities that should not be created without MQTT data need to use exclude option
                        or (
                            desc.mqtt
                            and desc.value_fn(mdata or data, desc.json_key) is not None
                            # include MQTT command datetime entities only if number options or also using Api command
                            and (
                                desc.api_cmd
                                or (
                                    mdev
                                    and desc.mqtt_cmd
                                    and mdev.cmd_is_number(
                                        cmd=desc.mqtt_cmd, parm=desc.mqtt_cmd_parm
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
                entity = AnkerSolixDateTime(
                    coordinator, description, context, entity_type
                )
                entities.append(entity)

    # create the entities from the list
    async_add_entities(entities)


class AnkerSolixDateTime(CoordinatorEntity, DateTimeEntity):
    """anker_solix datetime class."""

    coordinator: AnkerSolixDataUpdateCoordinator
    entity_description: AnkerSolixDateTimeDescription
    _attr_has_entity_name = True
    _unrecorded_attributes = frozenset()

    def __init__(
        self,
        coordinator: AnkerSolixDataUpdateCoordinator,
        description: AnkerSolixDateTimeDescription,
        context: str,
        entity_type: str,
    ) -> None:
        """Initialize the number class."""
        super().__init__(coordinator, context)

        self._attribute_name = description.key
        self._attr_attribution = f"{ATTRIBUTION}{' + MQTT' if description.mqtt else ''}"
        self._attr_unique_id = (f"{context}_{description.key}").lower()
        self.entity_description = description
        self.entity_type = entity_type
        self._attr_extra_state_attributes = None

        if self.entity_type == AnkerSolixEntityType.DEVICE:
            # get the device data from device context entry of coordinator data
            data: dict = coordinator.data.get(context) or {}
            if data.get("is_subdevice"):
                self._attr_device_info = get_AnkerSolixSubdeviceInfo(data, context)
            else:
                self._attr_device_info = get_AnkerSolixDeviceInfo(data, context)
        elif self.entity_type == AnkerSolixEntityType.ACCOUNT:
            # get the account data from account context entry of coordinator data
            data = coordinator.data.get(context) or {}
            self._attr_device_info = get_AnkerSolixAccountInfo(data, context)
        elif self.entity_type == AnkerSolixEntityType.VEHICLE:
            # get the vehicle info data from vehicle entry of coordinator data
            data = coordinator.data.get(context) or {}
            self._attr_device_info = get_AnkerSolixVehicleInfo(data, context)
        else:
            # get the site info data from site context entry of coordinator data
            data: dict = (coordinator.data.get(context) or {}).get("site_info") or {}
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
        """Return the native value of the entity."""
        return self._native_value

    @property
    def assumed_state(self):
        """Return the assumed state of the entity."""
        return self._assumed_state

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
                    data, self.entity_description.json_key
                )
        return self._attr_extra_state_attributes

    def update_state_value(self):
        """Update the state value of the entity based on the coordinator data."""
        if self.coordinator and self.coordinator_context in self.coordinator.data:
            # Api device data
            data = self.coordinator.data.get(self.coordinator_context)
            key = self.entity_description.json_key
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
                self._native_value = self.entity_description.value_fn(data, key)
                # get dynamic unit if defined
                if unit := self.entity_description.unit_fn(data):
                    self._attr_native_unit_of_measurement = unit
        else:
            self._native_value = None

        self._assumed_state = False
        # Mark availability based on value
        self._attr_available = self._native_value is not None

    async def async_set_value(self, value: datetime) -> None:
        """Set the value of the entity.

        Args:
            value (datetime): The value to set.

        """
        if (
            self.coordinator
            and self.coordinator_context in self.coordinator.data
            and self._native_value is not None
        ):
            data = self.coordinator.data.get(self.coordinator_context) or {}
            if (
                self.coordinator.client.testmode()
                and not self.entity_description.mqtt_cmd
                and self._attribute_name
                not in [
                    "preset_manual_backup_start",
                    "preset_manual_backup_end",
                ]
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
            if value == self._native_value:
                return
            # Wait until client cache is valid before applying any api change
            mdev = self.coordinator.client.get_mqtt_device(self.coordinator_context)
            await self.coordinator.client.validate_cache()
            # raise error if MQTT control but device is passive
            if self.entity_description.mqtt_cmd and mdev and mdev.is_passive():
                raise ServiceValidationError(
                    f"'{self.entity_id}' cannot be used while device is running in local mode",
                    translation_domain=DOMAIN,
                    translation_key="local_mode",
                    translation_placeholders={"entity_id": self.entity_id},
                )
            # Trigger Api calls depending on changed entity
            if (
                self._attribute_name
                in [
                    "preset_manual_backup_start",
                    "preset_manual_backup_end",
                ]
                and isinstance(value, datetime)
                and (
                    data.get("type") == SolixDeviceType.COMBINER_BOX.value
                    or (data.get("generation") or 0) >= 2
                )
            ):
                LOGGER.debug("%s change to %s will be applied", self.entity_id, value)
                site_id = data.get("site_id") or ""
                resp = None
                # Note: Each field change in UI triggers value update. To avoid to many Api requests are sent for start and end time changes,
                # those changes will only be done in the Api cache and the backup switch will be disabled. Just when the backup switch entity
                # is enabled, the cached start and end times will be sent to the Api for enabling backup option (similar to App behavior)
                # Attention: Times in cache may be updated by regular schedule refresh from Api prior the backup switch is being activated
                if self._attribute_name == "preset_manual_backup_start":
                    resp = await self.coordinator.client.api.set_sb2_ac_charge(
                        siteId=site_id,
                        deviceSn=self.coordinator_context,
                        backup_start=value,
                        backup_switch=False,
                        # Use test schedule to ensure change is done in cache only
                        test_schedule=data.get("schedule") or {},
                        toFile=self.coordinator.client.testmode(),
                    )
                elif self._attribute_name == "preset_manual_backup_end":
                    resp = await self.coordinator.client.api.set_sb2_ac_charge(
                        siteId=site_id,
                        deviceSn=self.coordinator_context,
                        backup_end=value,
                        backup_switch=False,
                        # Use test schedule to ensure change is done in cache only
                        test_schedule=data.get("schedule") or {},
                        toFile=self.coordinator.client.testmode(),
                    )
                if isinstance(resp, dict) and ALLOW_TESTMODE:
                    LOGGER.info(
                        "%s: Applied schedule for %s change to %s:\n%s",
                        "TESTMODE"
                        if self.coordinator.client.testmode()
                        else "LIVEMODE",
                        self.entity_id,
                        value,
                        json.dumps(
                            resp, indent=2 if len(json.dumps(resp)) < 200 else None
                        ),
                    )
            elif (
                self._attribute_name
                in [
                    "pps_manual_backup_start",
                    "pps_manual_backup_end",
                ]
                and isinstance(value, datetime)
                and mdev
                and mdev.get_status(fromFile=self.coordinator.client.testmode()).get(
                    "backup_switch"
                )
                == 0
            ):
                LOGGER.log(
                    logging.INFO if ALLOW_TESTMODE else logging.DEBUG,
                    "%s change to %s will be applied ONLY in device cache",
                    self.entity_id,
                    value,
                )
                # update timestamps only in cache to avoid unnecessary MQTT commands while backup is disabled
                plan = data.get("customized", {}).get("backup_plan", {})
                plan[
                    "backup_start_timestamp"
                    if self._attribute_name == "pps_manual_backup_start"
                    else "backup_end_timestamp"
                ] = int(value.timestamp())
                self.coordinator.client.api.customizeCacheId(
                    id=self.coordinator_context,
                    key="backup_plan",
                    value=plan,
                )
            # Trigger MQTT commands depending on changed entity
            elif self.entity_description.mqtt_cmd and mdev:
                LOGGER.debug(
                    "'%s' change to '%s' will be applied via MQTT command '%s'",
                    self.entity_id,
                    str(value),
                    self.entity_description.mqtt_cmd,
                )
                await self._async_mqtt_datetime(mdev=mdev, value=value.timestamp())

            # trigger coordinator update with api dictionary data
            await self.coordinator.async_refresh_data_from_apidict()

    async def _async_mqtt_datetime(
        self,
        mdev: SolixMqttDevice,
        value: str | datetime | float | None = None,
        cmd: str | None = None,
        parm: str | None = None,
        parm_map: dict | None = None,
    ) -> dict | None:
        """Use MQTT device control to modify time setting."""
        resp = None
        if not isinstance(cmd, str):
            cmd = self.entity_description.mqtt_cmd
        if not isinstance(parm, str):
            parm = self.entity_description.mqtt_cmd_parm
        if not isinstance(parm_map, dict):
            parm_map = {}
        try:
            if isinstance(value, datetime):
                cmdvalue = int(value.timestamp())
            elif isinstance(value, float | int):
                cmdvalue = int(value)
            elif isinstance(value, str):
                cmdvalue = int(datetime.fromisoformat(value).astimezone().timestamp())
            else:
                cmdvalue = value
            # Use helper methods for certain MQTT commands that require special handling
            if self._attribute_name in [
                "pps_manual_backup_start",
                "pps_manual_backup_end",
            ]:
                # change dependend times and weekend mode upon time changes
                resp = await mdev.set_backup_charge_plan(
                    backup_start=parm_map.get(self.entity_description.mqtt_cmd_parm)
                    or cmdvalue
                    if self._attribute_name == "pps_manual_backup_start"
                    else None,
                    backup_end=parm_map.get(self.entity_description.mqtt_cmd_parm)
                    or cmdvalue
                    if self._attribute_name == "pps_manual_backup_end"
                    else None,
                    toFile=self.coordinator.client.testmode(),
                )
            else:
                resp = await mdev.run_command(
                    cmd=cmd,
                    parm=parm,
                    value=cmdvalue,
                    parm_map=parm_map,
                    toFile=self.coordinator.client.testmode(),
                )
            if isinstance(resp, dict):
                if ALLOW_TESTMODE:
                    LOGGER.info(
                        "%s: Applied MQTT command '%s' for '%s' change to '%s':\n%s",
                        "TESTMODE"
                        if self.coordinator.client.testmode()
                        else "LIVEMODE",
                        cmd,
                        self.entity_id,
                        str(value),
                        json.dumps(
                            resp, indent=2 if len(json.dumps(resp)) < 200 else None
                        ),
                    )
                # copy the changed state(s) of the mock response into device cache to avoid flip back of entity until real state is received
                for key, val in resp.items():
                    if key in mdev.mqttdata:
                        mdev.mqttdata[key] = val
                # trigger status request to get updated MQTT message
                await mdev.status_request(toFile=self.coordinator.client.testmode())
            else:
                LOGGER.error(
                    "'%s' could not be changed via MQTT command '%s'",
                    self.entity_id,
                    cmd,
                )
        except (ValueError, TypeError) as err:
            LOGGER.error(
                "'%s' could not be changed via MQTT command '%s':\n%s",
                self.entity_id,
                cmd,
                str(err),
            )
        if not isinstance(resp, dict):
            cmd_parm = f"{cmd!s}{(' with parm ' + str(parm)) if parm else ''}"
            alias = mdev.device.get("alias") or ""
            raise ServiceValidationError(
                f"'{cmd_parm}' for {self.coordinator.client.api.apisession.nickname} device "
                f"{alias} ({self.coordinator_context}) failed",
                translation_domain=DOMAIN,
                translation_key="mqtt_command_failed",
                translation_placeholders={
                    "command": cmd_parm,
                    "coordinator": self.coordinator.client.api.apisession.nickname,
                    "device_alias": alias,
                    "device_sn": self.coordinator_context,
                },
            )
        return resp
