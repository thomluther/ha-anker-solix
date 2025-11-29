"""Custom integration to integrate anker_solix with Home Assistant.

For more details about this integration, please refer to
https://github.com/thomluther/ha-anker-solix
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from aiohttp import ClientTimeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DELAY_TIME,
    CONF_EXCLUDE,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryError
from homeassistant.helpers import issue_registry as ir, restore_state
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.device_registry import DeviceEntry

from . import api_client
from .config_flow import (
    CONF_API_OPTIONS,
    CONF_ENDPOINT_LIMIT,
    CONF_MQTT_OPTIONS,
    CONF_MQTT_TEST_SPEED,
    CONF_MQTT_USAGE,
    CONF_SKIP_INVALID,
    CONF_TEST_OPTIONS,
    CONF_TRIGGER_TIMEOUT,
    CONFIG_MINOR_VERSION,
    CONFIG_VERSION,
    DELAY_TIME_DEF,
    ENDPOINT_LIMIT_DEF,
    INTERVALMULT_DEF,
    MQTT_USAGE_DEF,
    SCAN_INTERVAL_DEF,
    SHARED_ACCOUNT,
    SKIP_INVALID_DEF,
    TESTFOLDER,
    TESTMODE,
    TIMEOUT_DEF,
    TRIGGER_TIMEOUT_DEF,
    async_check_and_remove_devices,
)
from .const import (
    DOMAIN,
    EXAMPLESFOLDER,
    INTERVALMULT,
    LOGGER,
    PLATFORMS,
    REGISTERED_EXCLUDES,
    SERVICE_API_REQUEST,
    SERVICE_CLEAR_SOLARBANK_SCHEDULE,
    SERVICE_EXPORT_SYSTEMS,
    SERVICE_GET_SOLARBANK_SCHEDULE,
    SERVICE_GET_SYSTEM_INFO,
    SERVICE_MODIFY_SOLIX_BACKUP_CHARGE,
    SERVICE_MODIFY_SOLIX_USE_TIME,
    SERVICE_SET_SOLARBANK_SCHEDULE,
    SERVICE_UPDATE_SOLARBANK_SCHEDULE,
)
from .coordinator import AnkerSolixDataUpdateCoordinator
from .solixapi.apitypes import ApiCategories, SolixDeviceType


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    hass.data.setdefault(DOMAIN, {})
    username = entry.data.get(CONF_USERNAME)
    excludes = set(entry.options.get(CONF_EXCLUDE, []))
    # Add the actual MQTT usage as exclude as well if disabled, it will be used to exclude certain entities
    if entry.options.get(CONF_MQTT_OPTIONS, {}).get(CONF_MQTT_USAGE):
        excludes.discard(ApiCategories.mqtt_devices)
    else:
        excludes.add(ApiCategories.mqtt_devices)
    registered_excludes = set(entry.options.get(REGISTERED_EXCLUDES, []))
    try:
        coordinator = AnkerSolixDataUpdateCoordinator(
            hass=hass,
            client=api_client.AnkerSolixApiClient(
                entry,
                session=async_create_clientsession(
                    hass, timeout=ClientTimeout(total=10)
                ),
            ),
            config_entry=entry,
            update_interval=entry.options.get(CONF_API_OPTIONS, {}).get(
                CONF_SCAN_INTERVAL, SCAN_INTERVAL_DEF
            ),
        )
        # set testmode for client and json test file folder for api
        if coordinator and coordinator.client:
            # load authentication info to get client nickname for coordinator
            await coordinator.client.authenticate()
        # Introduce delay for staggered reloads of multiple hubs
        await coordinator.async_refresh_delay()
        # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
        await coordinator.async_config_entry_first_refresh()
    except (
        api_client.AnkerSolixApiClientAuthenticationError,
        api_client.AnkerSolixApiClientRetryExceededError,
    ) as exception:
        raise ConfigEntryAuthFailed(exception) from exception
    # Registers update listener to update config entry when options are updated.
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    # check again if config shares devices with another config and also remove orphaned devices no longer contained in actual api data
    # If additional excluded categories are found, the affected devices must also be removed
    # This is run upon reloads or config option changes
    if shared_cfg := await async_check_and_remove_devices(
        hass=hass,
        user_input=entry.data,
        apidata=coordinator.data,
        excluded=(excludes - registered_excludes),
    ):
        # device is already registered for another account, abort configuration
        entry.async_cancel_retry_setup()
        # Create issue in frontend
        ir.async_create_issue(
            hass,
            DOMAIN,
            "duplicate_devices",
            is_fixable=False,
            is_persistent=True,
            issue_domain=DOMAIN,
            severity=ir.IssueSeverity.ERROR,
            translation_key="duplicate_devices",
            translation_placeholders={
                CONF_USERNAME: str(username),
                SHARED_ACCOUNT: str(shared_cfg.data.get("username")),
                CONF_NAME: str(shared_cfg.title),
            },
        )
        raise ConfigEntryError(
            api_client.AnkerSolixApiClientError(
                f"Found shared devices with {shared_cfg.title}"
            ),
            translation_key="duplicate_devices",
            translation_domain="config",
            translation_placeholders={
                CONF_USERNAME: str(username),
                SHARED_ACCOUNT: str(shared_cfg.data.get("username")),
                CONF_NAME: str(shared_cfg.title),
            },
        )
    # Create an entry in the hass object with the coordinator
    hass.data[DOMAIN][entry.entry_id] = coordinator
    # Update registered excludes in config entry to compare changes upon reloads
    registered_excludes = excludes
    # Register the MQTT usage as exclude as well if disabled
    if entry.options.get(CONF_MQTT_OPTIONS, {}).get(CONF_MQTT_USAGE):
        registered_excludes.discard(ApiCategories.mqtt_devices)
    else:
        registered_excludes.add(ApiCategories.mqtt_devices)
    hass.config_entries.async_update_entry(
        entry=entry,
        options=entry.options.copy() | {REGISTERED_EXCLUDES: list(registered_excludes)},
    )
    # Clear old issue if last enabled config loads successfully
    entries = hass.config_entries.async_entries(DOMAIN, include_disabled=False)
    active = hass.data.get(DOMAIN) or []
    if len(active) >= len(entries):
        ir.async_delete_issue(hass, DOMAIN, "duplicate_devices")

    # forward to platform to create entities
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update, triggered by update listener only."""
    coordinator: AnkerSolixDataUpdateCoordinator = hass.data[DOMAIN].get(entry.entry_id)
    do_reload = True
    if coordinator and coordinator.client:
        testmode = bool(entry.options.get(CONF_TEST_OPTIONS, {}).get(TESTMODE, False))
        testfolder = entry.options.get(CONF_TEST_OPTIONS, {}).get(TESTFOLDER, "")
        excluded = entry.options.get(CONF_EXCLUDE, [])
        mqtt = bool(
            entry.options.get(CONF_MQTT_OPTIONS, {}).get(
                CONF_MQTT_USAGE, MQTT_USAGE_DEF
            )
        )
        # Check if option change does not require reload when only timeout or interval was changed
        if (
            testmode == coordinator.client.testmode()
            and (
                not testmode
                or str(Path(entry.data.get(EXAMPLESFOLDER, "")) / testfolder)
                == coordinator.client.api.testDir()
            )
            and (mqtt or mqtt == await coordinator.client.mqtt_usage())
            and set(excluded) == set(coordinator.client.exclude_categories)
        ):
            do_reload = False
            api_options = entry.options.get(CONF_API_OPTIONS, {})
            # modify changed client parameters without reload
            seconds = int(api_options.get(CONF_SCAN_INTERVAL, SCAN_INTERVAL_DEF))
            if seconds != int(coordinator.update_interval.seconds):
                coordinator.update_interval = timedelta(seconds=seconds)
                LOGGER.info(
                    "Api Coordinator %s update interval was changed to %s seconds",
                    coordinator.config_entry.title,
                    seconds,
                )
            # update device detail refresh multiplier
            coordinator.client.deviceintervals(api_options.get(INTERVALMULT))
            # update Api request delay time
            coordinator.client.delay_time(api_options.get(CONF_DELAY_TIME))
            # update Api request timeout
            coordinator.client.timeout(api_options.get(CONF_TIMEOUT))
            # update Api request delay time
            coordinator.client.endpoint_limit(api_options.get(CONF_ENDPOINT_LIMIT))
            # set MQTT realtime trigger timeout
            coordinator.client.trigger_timeout(
                seconds=entry.options.get(CONF_MQTT_OPTIONS, {}).get(
                    CONF_TRIGGER_TIMEOUT, TRIGGER_TIMEOUT_DEF
                )
            )
            # update MQTT file poller speed
            coordinator.client.mqtt_test_speed(
                entry.options.get(CONF_TEST_OPTIONS, {}).get(CONF_MQTT_TEST_SPEED)
            )
            # Check if MQTT usage was enabled
            if mqtt != await coordinator.client.mqtt_usage():
                await coordinator.client.mqtt_usage(enable=mqtt)
                # remove registered exclude for mqtt devices from config entry since no reload is triggered
                registered_excludes = set(entry.options.get(REGISTERED_EXCLUDES, []))
                registered_excludes.discard(ApiCategories.mqtt_devices)
                hass.config_entries.async_update_entry(
                    entry=entry,
                    options=entry.options.copy()
                    | {REGISTERED_EXCLUDES: list(registered_excludes)},
                )
                # trigger immediate reload of platforms
                await coordinator.async_reload_config(
                    register_devices=coordinator.client.api.devices
                )
            # add modified coordinator back to hass
            hass.data[DOMAIN][entry.entry_id] = coordinator
        if do_reload:
            # Save actual restore states before unload and unregistering devices and entities
            await restore_state.RestoreStateData.async_save_persistent_states(hass)
            LOGGER.info(
                "Api Coordinator %s saved HA states of restore entities",
                coordinator.config_entry.title,
            )
            # Close MQTT connection threads
            if await coordinator.client.mqtt_usage():
                coordinator.client.api.stopMqttSession()
            hass.config_entries.async_schedule_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle unload of an entry, also triggered when integration is reloaded by UI."""

    other_entries = [
        e
        for e in hass.config_entries.async_loaded_entries(DOMAIN)
        if e.entry_id != entry.entry_id
    ]
    if not other_entries:
        # The last config entry is being unloaded, release shared resources, unregister services etc.
        # unregister services if no config remains
        hass.services.async_remove(DOMAIN, SERVICE_GET_SYSTEM_INFO)
        hass.services.async_remove(DOMAIN, SERVICE_EXPORT_SYSTEMS)
        hass.services.async_remove(DOMAIN, SERVICE_GET_SOLARBANK_SCHEDULE)
        hass.services.async_remove(DOMAIN, SERVICE_CLEAR_SOLARBANK_SCHEDULE)
        hass.services.async_remove(DOMAIN, SERVICE_SET_SOLARBANK_SCHEDULE)
        hass.services.async_remove(DOMAIN, SERVICE_UPDATE_SOLARBANK_SCHEDULE)
        hass.services.async_remove(DOMAIN, SERVICE_MODIFY_SOLIX_BACKUP_CHARGE)
        hass.services.async_remove(DOMAIN, SERVICE_MODIFY_SOLIX_USE_TIME)
        hass.services.async_remove(DOMAIN, SERVICE_API_REQUEST)
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of an entry. The config entry is deleted from hass.config_entries before this is called."""
    # Clear old issue if remaining configs are all loaded
    entries = hass.config_entries.async_entries(DOMAIN, include_disabled=False)
    active = hass.data.get(DOMAIN) or []
    if len(active) >= len(entries):
        ir.async_delete_issue(hass, DOMAIN, "duplicate_devices")


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Support removal of devices but remove a config entry from a device only if the device is no longer active."""
    coordinator: AnkerSolixDataUpdateCoordinator = hass.data[DOMAIN].get(
        config_entry.entry_id
    )
    active = False
    if coordinator:
        # remove vehicle device types from cloud
        if device_entry.model == SolixDeviceType.VEHICLE.value.capitalize():
            await coordinator.async_execute_command(
                command="remove_vehicle", option=device_entry.serial_number
            )
        # Allow only removal of orphaned devices not contained in actual api data
        active = any(
            identifier
            for identifier in device_entry.identifiers
            if identifier[0] == DOMAIN
            for device_serial in coordinator.data
            if device_serial == identifier[1]
        )
    return not active


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config entry."""
    if config_entry.version > 2:
        # This means the user has downgraded from a future version
        LOGGER.warning(
            "Cannot migrate hub '%s' configuration from future version %s.%s to version %s.%s",
            config_entry.title,
            config_entry.version,
            config_entry.minor_version,
            CONFIG_VERSION,
            CONFIG_MINOR_VERSION,
        )
        return False
    if config_entry.version < 2:
        # migration from version 1.x to 2.x, prior 2.1, only version 1.1 was used
        new_data = {**config_entry.data}
        new_options = {**config_entry.options}
        old_version = config_entry.version
        old_minor = config_entry.minor_version
        if config_entry.minor_version < 9:
            # modify Config Entry data with changes prior version 1.2
            new_api_options = {
                CONF_API_OPTIONS: {
                    CONF_SCAN_INTERVAL: new_options.pop(
                        CONF_SCAN_INTERVAL, SCAN_INTERVAL_DEF
                    ),
                    INTERVALMULT: new_options.pop(INTERVALMULT, INTERVALMULT_DEF),
                    CONF_DELAY_TIME: new_options.pop(CONF_DELAY_TIME, DELAY_TIME_DEF),
                    CONF_TIMEOUT: new_options.pop(CONF_TIMEOUT, TIMEOUT_DEF),
                    CONF_ENDPOINT_LIMIT: new_options.pop(
                        CONF_ENDPOINT_LIMIT, ENDPOINT_LIMIT_DEF
                    ),
                    CONF_SKIP_INVALID: new_options.pop(
                        CONF_SKIP_INVALID, SKIP_INVALID_DEF
                    ),
                }
            }
            new_test_options = {
                CONF_TEST_OPTIONS: {
                    TESTMODE: new_options.pop(TESTMODE, False),
                    TESTFOLDER: new_options.pop(TESTFOLDER, ""),
                }
            }
            new_options = new_options | new_api_options | new_test_options
        hass.config_entries.async_update_entry(
            config_entry,
            data=new_data,
            options=new_options,
            version=CONFIG_VERSION,
            minor_version=CONFIG_MINOR_VERSION,
        )
        LOGGER.info(
            "Migration of hub '%s' configuration from version %s.%s to version %s.%s successful",
            config_entry.title,
            old_version,
            old_minor,
            config_entry.version,
            config_entry.minor_version,
        )
    return True
