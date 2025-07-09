"""Datetime platform for anker_solix."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
import json
from typing import Any

from homeassistant.components.datetime import DateTimeEntity, DateTimeEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EXCLUDE
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.dt import UTC

from .const import ALLOW_TESTMODE, ATTRIBUTION, CREATE_ALL_ENTITIES, DOMAIN, LOGGER
from .coordinator import AnkerSolixDataUpdateCoordinator
from .entity import (
    AnkerSolixEntityRequiredKeyMixin,
    AnkerSolixEntityType,
    get_AnkerSolixAccountInfo,
    get_AnkerSolixDeviceInfo,
    get_AnkerSolixSubdeviceInfo,
    get_AnkerSolixSystemInfo,
)
from .solixapi.apitypes import SolixDeviceType


@dataclass(frozen=True)
class AnkerSolixDateTimeDescription(
    DateTimeEntityDescription, AnkerSolixEntityRequiredKeyMixin
):
    """DateTime entity description with optional keys."""

    force_creation: bool = False
    # Use optionally to provide function for value calculation or lookup of nested values
    value_fn: Callable[[dict, str], StateType | None] = lambda d, jk: d.get(jk)
    unit_fn: Callable[[dict], str | None] = lambda d: None
    attrib_fn: Callable[[dict], dict | None] = lambda d: None
    exclude_fn: Callable[[set, dict], bool] = lambda s, d: False


DEVICE_DATETIMES = [
    AnkerSolixDateTimeDescription(
        key="preset_manual_backup_start",
        translation_key="preset_manual_backup_start",
        json_key="preset_manual_backup_start",
        value_fn=lambda d, jk: datetime.fromtimestamp(d.get(jk), UTC).astimezone()
        if d.get(jk) is not None
        else None,
        exclude_fn=lambda s, d: not ({SolixDeviceType.SOLARBANK.value} - s),
    ),
    AnkerSolixDateTimeDescription(
        key="preset_manual_backup_end",
        translation_key="preset_manual_backup_end",
        json_key="preset_manual_backup_end",
        value_fn=lambda d, jk: datetime.fromtimestamp(d.get(jk), UTC).astimezone()
        if d.get(jk) is not None
        else None,
        exclude_fn=lambda s, d: not ({SolixDeviceType.SOLARBANK.value} - s),
    ),
]

SITE_DATETIMES = []

ACCOUNT_DATETIMES = []


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
            if (data_type := data.get("type")) == SolixDeviceType.SYSTEM.value:
                # Unique key for site_id entry in data
                entity_type = AnkerSolixEntityType.SITE
                entity_list = SITE_DATETIMES
            elif data_type == SolixDeviceType.ACCOUNT.value:
                # Unique key for account entry in data
                entity_type = AnkerSolixEntityType.ACCOUNT
                entity_list = ACCOUNT_DATETIMES
            else:
                # device_sn entry in data
                entity_type = AnkerSolixEntityType.DEVICE
                entity_list = DEVICE_DATETIMES

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
    _attr_attribution = ATTRIBUTION
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
        self._attr_unique_id = (f"{context}_{description.key}").lower()
        self.entity_description = description
        self.entity_type = entity_type
        self._attr_extra_state_attributes = None

        if self.entity_type == AnkerSolixEntityType.DEVICE:
            # get the device data from device context entry of coordinator data
            data: dict = coordinator.data.get(context) or {}
            if data.get("is_subdevice"):
                self._attr_device_info = get_AnkerSolixSubdeviceInfo(
                    data, context, data.get("main_sn")
                )
            else:
                self._attr_device_info = get_AnkerSolixDeviceInfo(
                    data, context, coordinator.client.api.apisession.email
                )
        elif self.entity_type == AnkerSolixEntityType.ACCOUNT:
            # get the account data from account context entry of coordinator data
            data = coordinator.data.get(context) or {}
            self._attr_device_info = get_AnkerSolixAccountInfo(data, context)
        else:
            # get the site info data from site context entry of coordinator data
            data: dict = (coordinator.data.get(context) or {}).get("site_info") or {}
            self._attr_device_info = get_AnkerSolixSystemInfo(
                data, context, coordinator.client.api.apisession.email
            )

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
            data = self.coordinator.data.get(self.coordinator_context)
            with suppress(ValueError, TypeError):
                self._attr_extra_state_attributes = self.entity_description.attrib_fn(
                    data, self.coordinator_context
                )
        return self._attr_extra_state_attributes

    def update_state_value(self):
        """Update the state value of the entity based on the coordinator data."""
        if self.coordinator and self.coordinator_context in self.coordinator.data:
            data = self.coordinator.data.get(self.coordinator_context)
            key = self.entity_description.json_key
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
        if self.coordinator.client.testmode() and self._attribute_name not in [
            "preset_manual_backup_start",
            "preset_manual_backup_end",
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
        if (
            self.coordinator
            and self.coordinator_context in self.coordinator.data
            and self._native_value is not None
        ):
            data = self.coordinator.data.get(self.coordinator_context) or {}
            # Skip Api calls if entity does not change
            if value == self._native_value:
                return
            # Wait until client cache is valid before applying any api change
            await self.coordinator.client.validate_cache()
            if (
                self._attribute_name
                in [
                    "preset_manual_backup_start",
                    "preset_manual_backup_end",
                ]
                and isinstance(value, datetime)
                and self._native_value != value
                and (data.get("generation") or 0) >= 2
            ):
                LOGGER.debug("%s change to %s will be applied", self.entity_id, value)
                siteId = data.get("site_id") or ""
                resp = None
                # Note: Each field change in UI triggers value update. To avoid to many Api requests are sent for start and end time changes,
                # those changes will only be done in the Api cache and the backup switch will be disabled. Just when the backup switch entity
                # is enabled, the cached start and end times will be sent to the Api for enabling backup option (similar to App behavior)
                # Attention: Times in cache may be updated by regular schedule refresh from Api prior the backup switch is being activated
                if self._attribute_name == "preset_manual_backup_start":
                    resp = await self.coordinator.client.api.set_sb2_ac_charge(
                        siteId=siteId,
                        deviceSn=self.coordinator_context,
                        backup_start=value,
                        backup_switch=False,
                        # Use test schedule to ensure change is done in cache only
                        test_schedule=data.get("schedule") or {},
                        toFile=self.coordinator.client.testmode(),
                    )
                elif self._attribute_name == "preset_manual_backup_end":
                    resp = await self.coordinator.client.api.set_sb2_ac_charge(
                        siteId=siteId,
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
        # trigger coordinator update with api dictionary data
        await self.coordinator.async_refresh_data_from_apidict()
        self._assumed_state = True
