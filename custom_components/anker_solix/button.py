"""Switch platform for anker_solix."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
import json
import logging
from pathlib import Path

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EXCLUDE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ALLOW_TESTMODE, ATTRIBUTION, CREATE_ALL_ENTITIES, DOMAIN, LOGGER
from .coordinator import AnkerSolixDataUpdateCoordinator
from .entity import (
    AnkerSolixEntityRequiredKeyMixin,
    AnkerSolixEntityType,
    AnkerSolixPicturePath,
    get_AnkerSolixAccountInfo,
    get_AnkerSolixDeviceInfo,
    get_AnkerSolixSubdeviceInfo,
    get_AnkerSolixSystemInfo,
    get_AnkerSolixVehicleInfo,
)
from .solixapi.apitypes import SolixDeviceType, SolixVehicle


@dataclass(frozen=True)
class AnkerSolixButtonDescription(
    ButtonEntityDescription, AnkerSolixEntityRequiredKeyMixin
):
    """Button entity description with optional keys."""

    force_creation: bool = False
    picture_path: str = None
    # Use optionally to provide function for value calculation or lookup of nested values
    value_fn: Callable[[dict, str], bool | None] = lambda d, jk: d.get(jk)
    attrib_fn: Callable[[dict], dict | None] = lambda d: None
    exclude_fn: Callable[[set, dict], bool] = lambda s, d: False


DEVICE_BUTTONS = [
    AnkerSolixButtonDescription(
        key="refresh_device",
        translation_key="refresh_device",
        json_key="",
        force_creation=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        exclude_fn=lambda s, d: not ({d.get("type")} - s),
    ),
]

SITE_BUTTONS = []

ACCOUNT_BUTTONS = [
    AnkerSolixButtonDescription(
        key="refresh_vehicles",
        translation_key="refresh_vehicles",
        json_key="",
        force_creation=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        picture_path=getattr(
            AnkerSolixPicturePath, SolixDeviceType.VEHICLE.value.upper(), None
        ),
        exclude_fn=lambda s, d: not ({SolixDeviceType.VEHICLE.value} - s),
    ),
]

VEHICLE_BUTTONS = [
    # Restore button is actually not needed since restore is done via model_id selection
    # AnkerSolixButtonDescription(
    #     key="restore_attributes",
    #     translation_key="restore_attributes",
    #     json_key="restore_attributes",
    #     force_creation=True,
    #     exclude_fn=lambda s, d: not ({d.get("type")} - s),
    # ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button platform."""

    coordinator = hass.data[DOMAIN].get(entry.entry_id)
    entities = []
    if coordinator and hasattr(coordinator, "data") and coordinator.data:
        # create entity based on type of entry in coordinator data, which consolidates the api.sites, api.devices and api.account dictionaries
        # the coordinator.data dict key is either account nickname, a site_id or device_sn and used as context for the entity to lookup its data
        for context, data in coordinator.data.items():
            if (data_type := data.get("type")) == SolixDeviceType.SYSTEM.value:
                # Unique key for site_id entry in data
                entity_type = AnkerSolixEntityType.SITE
                entity_list = SITE_BUTTONS
            elif data_type == SolixDeviceType.ACCOUNT.value:
                # Unique key for account entry in data
                entity_type = AnkerSolixEntityType.ACCOUNT
                entity_list = ACCOUNT_BUTTONS
            elif data_type == SolixDeviceType.VEHICLE.value:
                # vehicle entry in data
                entity_type = AnkerSolixEntityType.VEHICLE
                entity_list = VEHICLE_BUTTONS
            else:
                # device_sn entry in data
                entity_type = AnkerSolixEntityType.DEVICE
                entity_list = DEVICE_BUTTONS

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
                entity = AnkerSolixButton(
                    coordinator, description, context, entity_type
                )
                entities.append(entity)

    # create the buttons from the list
    async_add_entities(entities)


class AnkerSolixButton(CoordinatorEntity, ButtonEntity):
    """anker_solix button class."""

    coordinator: AnkerSolixDataUpdateCoordinator
    entity_description: AnkerSolixButtonDescription
    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    _unrecorded_attributes = frozenset({})

    def __init__(
        self,
        coordinator: AnkerSolixDataUpdateCoordinator,
        description: AnkerSolixButtonDescription,
        context: str,
        entity_type: str,
    ) -> None:
        """Initialize the button class."""
        super().__init__(coordinator, context)

        self._attribute_name = description.key
        self._attr_unique_id = (f"{context}_{description.key}").lower()
        wwwroot = str(Path(self.coordinator.hass.config.config_dir) / "www")
        if (
            description.picture_path
            and Path(
                description.picture_path.replace(
                    AnkerSolixPicturePath.LOCALPATH, wwwroot
                )
            ).is_file()
        ):
            self._attr_entity_picture = description.picture_path
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
            if self._attribute_name in ["refresh_device"]:
                # set the correct device type picture for the device refresh entity, which is available for any device and account type
                if (pn := str(data.get("device_pn") or "").upper()) and hasattr(
                    AnkerSolixPicturePath, pn
                ):
                    self._attr_entity_picture = getattr(AnkerSolixPicturePath, pn)
                elif (dev_type := str(data.get("type") or "").upper()) and hasattr(
                    AnkerSolixPicturePath, dev_type
                ):
                    self._attr_entity_picture = getattr(AnkerSolixPicturePath, dev_type)
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
            data = (coordinator.data.get(context, {})).get("site_info", {})
            self._attr_device_info = get_AnkerSolixSystemInfo(
                data, context, coordinator.client.api.apisession.email
            )

    async def async_press(self) -> None:
        """Handle the button press."""
        # Wait until client cache is valid before running any api action
        await self.coordinator.client.validate_cache()
        if self._attribute_name == "refresh_device":
            if (
                self.coordinator.client.last_device_refresh
                and (
                    datetime.now().astimezone()
                    - self.coordinator.client.last_device_refresh
                ).total_seconds()
                < self.coordinator.client.min_device_refresh
            ):
                raise ServiceValidationError(
                    f"Devices for {self.coordinator.client.api.apisession.nickname} cannot be updated within less than {self.coordinator.client.min_device_refresh} seconds",
                    translation_domain=DOMAIN,
                    translation_key="device_refresh",
                    translation_placeholders={
                        "coordinator": self.coordinator.client.api.apisession.nickname,
                        "min_dev_refresh": str(
                            self.coordinator.client.min_device_refresh
                        ),
                    },
                )
            if (
                self.coordinator.client.active_device_refresh
                or self.coordinator.client.startup
            ):
                raise ServiceValidationError(
                    f"Devices for {self.coordinator.client.api.apisession.nickname} cannot be updated while another update is still running",
                    translation_domain=DOMAIN,
                    translation_key="device_refresh_active",
                    translation_placeholders={
                        "coordinator": self.coordinator.client.api.apisession.nickname,
                    },
                )
            LOGGER.debug(
                "%s triggered device refresh",
                self.entity_id,
            )
            await self.coordinator.async_execute_command(self.entity_description.key)
        elif self._attribute_name == "refresh_vehicles":
            if (
                self.coordinator.client.active_device_refresh
                or self.coordinator.client.startup
            ):
                raise ServiceValidationError(
                    f"Devices for {self.coordinator.client.api.apisession.nickname} cannot be updated while another update is still running",
                    translation_domain=DOMAIN,
                    translation_key="device_refresh_active",
                    translation_placeholders={
                        "coordinator": self.coordinator.client.api.apisession.nickname,
                    },
                )
            LOGGER.debug(
                "%s triggered vehicles refresh",
                self.entity_id,
            )
            await self.coordinator.async_execute_command(self.entity_description.key)
        elif self._attribute_name == "restore_attributes":
            LOGGER.debug(
                "%s triggered restore of vehicle attributes",
                self.entity_id,
            )
            data = (self.coordinator.data or {}).get(self.coordinator_context) or {}
            # keep the existing capacity as selection critera for multiple attribute versions
            vehicle = SolixVehicle(
                brand=data.get("brand"),
                model=data.get("model"),
                productive_year=data.get("productive_year"),
                model_id=data.get("id"),
                battery_capacity=data.get("battery_capacity"),
            )
            resp = await self.coordinator.client.api.manage_vehicle(
                vehicleId=self.coordinator_context,
                action="restore",
                vehicle=vehicle,
                toFile=self.coordinator.client.testmode(),
            )
            if isinstance(resp, dict):
                LOGGER.log(
                    logging.INFO if ALLOW_TESTMODE else logging.DEBUG,
                    "%s: '%s' Restored vehicle attributes from '%s':\n%s",
                    "TESTMODE" if self.coordinator.client.testmode() else "LIVEMODE",
                    self.entity_id,
                    str(vehicle),
                    json.dumps(resp, indent=2 if len(json.dumps(resp)) < 200 else None),
                )
                # trigger cache update for selected vehicle option
                await self.coordinator.client.api.update_vehicle_options(
                    vehicle=vehicle
                )
                # trigger coordinator update with api dictionary data
                await self.coordinator.async_refresh_data_from_apidict()
            else:
                LOGGER.log(
                    logging.INFO if ALLOW_TESTMODE else logging.DEBUG,
                    "%s: '%s' Restore of vehicle attributes from '%s' could not be applied",
                    "TESTMODE" if self.coordinator.client.testmode() else "LIVEMODE",
                    self.entity_id,
                    str(vehicle),
                )
