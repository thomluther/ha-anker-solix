"""Datetime platform for anker_solix."""

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityDescription,
    UpdateEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EXCLUDE, EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, CREATE_ALL_ENTITIES, DOMAIN, MQTT_OVERLAY
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


@dataclass(frozen=True)
class AnkerSolixUpdateDescription(
    UpdateEntityDescription, AnkerSolixEntityRequiredKeyMixin
):
    """Update entity description with optional keys."""

    force_creation: bool = False
    mqtt: bool = False
    # Use optionally to provide function for value calculation or lookup of nested values
    value_fn: Callable[[dict, str], StateType | None] = lambda d, jk: d.get(jk)
    unit_fn: Callable[[dict], str | None] = lambda d: None
    attrib_fn: Callable[[dict], dict | None] = lambda d: None
    exclude_fn: Callable[[set, dict], bool] = lambda s, d: False


DEVICE_UPDATES = [
    AnkerSolixUpdateDescription(
        key="sw_version",
        translation_key="sw_version",
        json_key="sw_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=UpdateDeviceClass.FIRMWARE,
        value_fn=lambda d, jk: str(d.get(jk) or "").lstrip("v") or None,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
    ),
]

SITE_TIMES = []

ACCOUNT_TIMES = []

VEHICLE_TIMES = []


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up time platform."""

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
                entity_list = SITE_TIMES
            elif data_type == SolixDeviceType.ACCOUNT.value:
                # Unique key for account entry in data
                entity_type = AnkerSolixEntityType.ACCOUNT
                entity_list = ACCOUNT_TIMES
            elif data_type == SolixDeviceType.VEHICLE.value:
                # vehicle entry in data
                entity_type = AnkerSolixEntityType.VEHICLE
                entity_list = VEHICLE_TIMES
            else:
                # device_sn entry in data
                entity_type = AnkerSolixEntityType.DEVICE
                entity_list = DEVICE_UPDATES
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
                        )
                        # filter API only entities
                        or (
                            not desc.mqtt
                            and desc.value_fn(data, desc.json_key) is not None
                        )
                    )
                )
            ):
                entity = AnkerSolixUpdate(
                    coordinator, description, context, entity_type
                )
                entities.append(entity)

    # create the entities from the list
    async_add_entities(entities)


class AnkerSolixUpdate(CoordinatorEntity, UpdateEntity):
    """anker_solix update class."""

    coordinator: AnkerSolixDataUpdateCoordinator
    entity_description: AnkerSolixUpdateDescription
    _attr_has_entity_name = True
    _unrecorded_attributes = frozenset()

    def __init__(
        self,
        coordinator: AnkerSolixDataUpdateCoordinator,
        description: AnkerSolixUpdateDescription,
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
        self._attr_supported_features = UpdateEntityFeature.RELEASE_NOTES

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
        elif self.entity_type == AnkerSolixEntityType.VEHICLE:
            # get the vehicle info data from vehicle entry of coordinator data
            data = coordinator.data.get(context) or {}
            self._attr_device_info = get_AnkerSolixVehicleInfo(
                data, context, coordinator.client.api.apisession.email
            )
        else:
            # get the site info data from site context entry of coordinator data
            data: dict = (coordinator.data.get(context) or {}).get("site_info") or {}
            self._attr_device_info = get_AnkerSolixSystemInfo(
                data, context, coordinator.client.api.apisession.email
            )
        self._attr_title = f"{data.get('name') or data.get("alias")} ({data.get('device_pn')})"
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
                # get dynamic unit if defined
                if unit := self.entity_description.unit_fn(data):
                    self._attr_native_unit_of_measurement = unit
                # check if FW changed for device and update device entry in registry
                firmware = self.entity_description.value_fn(data, key)
                if (
                    firmware
                    and self._attr_installed_version
                    and firmware != self._attr_installed_version
                    and self.device_entry
                ):
                    # get device registry and update the device entry attribute
                    dev_registry = dr.async_get(self.coordinator.hass)
                    dev_registry.async_update_device(
                        self.device_entry.id,
                        sw_version=firmware,
                    )
                self._attr_installed_version = firmware
                # Latest version might be unknown, use empty str to ensure entity state
                self._attr_latest_version = str(data.get("ota_version") or "").lstrip(
                    "v"
                )
                self._attr_release_summary = (
                    "Components available" if data.get("ota_children") else ""
                )
        else:
            self._attr_installed_version = None

        # Mark availability based on value
        self._attr_available = self._attr_installed_version is not None

    def release_notes(self) -> str | None:
        """Return the release notes."""
        if self.coordinator and (
            data := (self.coordinator.data or {}).get(self.coordinator_context)
        ):
            markdown = "### Component details:\n\n"
            markdown += "Component|OTA-Version|Upgrade|Forced\n"
            markdown += "---|---|---|---\n"
            for child in (childs := data.get("ota_children") or []):
                b = "**" if child.get('need_update') else ""
                markdown += f"{child.get('device_type') or '-'}|{b}{child.get('rom_version_name') or '-'}{b}|{b}{'YES' if b else 'NO'}{b}|{'**YES**' if child.get('force_upgrade') else 'NO'}\n"
            return markdown if childs else None
        return None

    def version_is_newer(self, latest_version: str, installed_version: str) -> bool:
        """Return True if latest_version is newer than installed_version."""
        if self.coordinator and (
            (data := (self.coordinator.data or {}).get(self.coordinator_context) or {})
            and "is_ota_update" in data
        ):
            # Return update flag as indicated by Api if available
            return bool(data.get("is_ota_update"))
        if not (latest_version and installed_version):
            # Return False if any of the 2 versions is empty
            return False
        return super().version_is_newer(latest_version, installed_version)
