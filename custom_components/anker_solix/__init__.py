"""Custom integration to integrate anker_solix with Home Assistant.

For more details about this integration, please refer to
https://github.com/thomluther/hacs-anker-solix
"""
from __future__ import annotations

from datetime import timedelta
import os

from aiohttp import ClientTimeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_COUNTRY_CODE,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.device_registry import DeviceEntry

from . import api_client
from .config_flow import INTERVALMULT_DEF, SCAN_INTERVAL_DEF
from .const import DOMAIN, EXAMPLESFOLDER, INTERVALMULT, LOGGER, TESTFOLDER, TESTMODE
from .coordinator import AnkerSolixDataUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
]


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    hass.data.setdefault(DOMAIN, {})
    username = entry.data.get(CONF_USERNAME)
    coordinator = AnkerSolixDataUpdateCoordinator(
        hass=hass,
        client=api_client.AnkerSolixApiClient(
            username=username,
            password=entry.data.get(CONF_PASSWORD),
            countryid=entry.data.get(CONF_COUNTRY_CODE),
            session=async_create_clientsession(hass, timeout=ClientTimeout(total=10)),
        ),
        update_interval=entry.options.get(CONF_SCAN_INTERVAL, SCAN_INTERVAL_DEF),
    )
    # set testmode for client and json test file folder for api
    if coordinator and coordinator.client:
        testmode = coordinator.client.testmode(entry.options.get(TESTMODE))
        testfolder = entry.options.get(TESTFOLDER)
        if testmode and testfolder:
            # load authentication info and set json test file folder for api
            await coordinator.client.authenticate()
            coordinator.client.api.testDir(
                os.path.join(entry.data.get(EXAMPLESFOLDER, ""), testfolder)
            )
        # set device detail refresh multiplier
        coordinator.client.deviceintervals(
            entry.options.get(INTERVALMULT, INTERVALMULT_DEF)
        )

    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    await coordinator.async_config_entry_first_refresh()

    # first check for orphaned devices no longer contained in actual api data upon reloads or config option changes
    # get device registry and device ids that are orphaned
    dev_registry = dr.async_get(hass)
    active_serials = coordinator.data.keys()
    # for serial in active_serials:
    #     if device_entry := dev_registry.async_get_device((DOMAIN,serial)):
    #         # serial already registred, check if by same user account
    #         for config_id in device_entry.config_entries:
    #             if hasattr(hass.data[DOMAIN], config_id):
    #                 if entry.data.get(CONF_USERNAME) != hass.data[DOMAIN][config_id].unique_id:
    #                     pass

    # dev_list = [dev_entry.id for dev_entry in dev_registry.devices.data.values() if any(identifier for identifier in dev_entry.identifiers if identifier[0] == DOMAIN and identifier[1] not in active_serials)]
    # async_entries_for_config_entry(dev_registry, config_entry.entry_id)

    # cycle through all registered devices to check if already registered by different account (shared systems) or if obsolete for this config and can be removed
    dev_ids = [
        dev_entry.id
        for dev_entry in dev_registry.devices.data.values()
        if any(
            identifier
            for identifier in dev_entry.identifiers
            if identifier[0] == DOMAIN
        )
    ]
    obsolete_user_devs: dict = {}
    for dev_id in dev_ids:
        device_entry: DeviceEntry = dev_registry.async_get(dev_id)
        for config_id in device_entry.config_entries:
            if config_entry := hass.config_entries.async_get_entry(config_id):
                if username != config_entry.unique_id:
                    if device_entry.serial_number in active_serials:
                        # device is already registered for another account, abort configuration
                        entry.async_cancel_retry_setup()
                        raise ConfigEntryError(
                            api_client.AnkerSolixApiClientError("Duplicate Devices found"),
                            translation_key="duplicate_devices",
                            translation_domain="config",
                            translation_placeholders={
                                "username": username,
                                "shared": config_entry.unique_id,
                            },
                        )

                # device is registered for same account, check if still used in coorinator data and add to obsolete list for removal
                elif device_entry.serial_number not in active_serials:
                    obsolete_user_devs[device_entry.id] = device_entry.serial_number

    # Remove the obsolete device entries
    for dev_id, serial in obsolete_user_devs.items():
        dev_registry.async_remove_device(dev_id)
        # NOTE: removal of any underlying entities is handled by core
        LOGGER.info(
            "Removed device entry %s from registry for unused configuration entry device %s",
            dev_id,
            serial,
        )

    # Create an entry in the hass object with the coordinator
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # forward to platform to create entities
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Registers update listener to update config entry when options are updated.
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update, triggered by update listener only."""
    coordinator: AnkerSolixDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    # coordinator: AnkerSolixDataUpdateCoordinator = hass_entry.get("coordinator", {})
    do_reload = True
    if coordinator and coordinator.client:
        testmode = entry.options.get(TESTMODE)
        testfolder = entry.options.get(TESTFOLDER)
        # Check if option change does not require reload when only timeout or interval was changed
        if testmode == coordinator.client.testmode() and (
            testfolder == coordinator.client.api.testDir() or not testmode
        ):
            do_reload = False
            # modify changed intervals without reload
            seconds = int(entry.options.get(CONF_SCAN_INTERVAL, SCAN_INTERVAL_DEF))
            if seconds != int(coordinator.update_interval.seconds):
                coordinator.update_interval = timedelta(seconds=seconds)
                LOGGER.info(
                    "Api Coordinator update interval was changed to %s seconds", seconds
                )
            # set device detail refresh multiplier
            coordinator.client.deviceintervals(
                entry.options.get(INTERVALMULT, INTERVALMULT_DEF)
            )
            # add modified coordinator back to hass
            hass.data[DOMAIN][entry.entry_id] = coordinator

    if do_reload:
        await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry, also triggered when integration is reloaded by UI."""
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Support removal of devices and remove a config entry from a device."""
    coordinator: AnkerSolixDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]
    # Allow only removal of orphaned devices not contained in actual api data
    return not any(
        identifier
        for identifier in device_entry.identifiers
        if identifier[0] == DOMAIN
        for device_serial in coordinator.data
        if device_serial == identifier[1]
    )
