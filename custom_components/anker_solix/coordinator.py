"""DataUpdateCoordinator for Anker Solix."""

from __future__ import annotations

from asyncio import TimerHandle, sleep
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api_client import (
    AnkerSolixApiClient,
    AnkerSolixApiClientAuthenticationError,
    AnkerSolixApiClientCommunicationError,
    AnkerSolixApiClientError,
    AnkerSolixApiClientRetryExceededError,
)
from .const import ALLOW_TESTMODE, DOMAIN, LOGGER, PLATFORMS
from .solixapi.apitypes import SolixDeviceType


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class AnkerSolixDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to coordinate fetching of all data from the API."""

    config_entry: ConfigEntry
    client: AnkerSolixApiClient
    details_delayed: datetime | None
    update_handler: TimerHandle | None
    registered_devices: set

    def __init__(
        self,
        hass: HomeAssistant,
        client: AnkerSolixApiClient,
        config_entry: ConfigEntry,
        update_interval: int,
    ) -> None:
        """Initialize."""
        self.config_entry = config_entry
        self.client = client
        self.details_delayed = None
        self.update_handler = None
        self.registered_devices = set()

        super().__init__(
            hass=hass,
            logger=LOGGER,
            config_entry=config_entry,
            name=f"{DOMAIN}_{config_entry.title}",
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self) -> dict:
        """Update data via library."""
        try:
            if (
                not await self.client.validate_cache()
                or self.client.active_device_refresh
            ):
                # return existing data if cache stays invalid during systems export randomization or manual update still active
                return self.data
            # stagger non-initial updates if required
            if not self.client.startup:
                await self.async_refresh_delay()
                await self.async_details_delay()
            data = await self.client.async_get_data()
            # get device IDs for dynamic entity and device creation
            ids = set(data.keys())
            # make sure deferred data will create additional entities
            if self.client.deferred_data and self.config_entry:
                # trigger reload and register all current devices
                if await self.async_reload_config(register_devices=data):
                    self.client.deferred_data = False
            # initial device registration
            elif self.client.startup:
                self.registered_devices = ids
            # trigger reload if additional devices are found
            elif ids - self.registered_devices:
                await self.async_reload_config(register_devices=data)
            # trigger device removal if not found anymore
            elif (
                ids
                and self.registered_devices
                and (removed := self.registered_devices - ids)
            ):
                await self.async_remove_device(devices=removed)
        except (
            AnkerSolixApiClientAuthenticationError,
            AnkerSolixApiClientRetryExceededError,
        ) as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except (
            AnkerSolixApiClientError,
            AnkerSolixApiClientCommunicationError,
        ) as exception:
            raise UpdateFailed(exception) from exception
        else:
            return data

    async def async_refresh_data_from_apidict(self, delayed: bool = False) -> None:
        """Update data from client api dictionaries without resetting update interval.

        The delayed option will wait 2 seconds before listeners are notified to allow
        consolidating parallel update requests during the state restore processing.
        """
        self.data = await self.client.async_get_data(from_cache=True)
        if delayed and not self.update_handler:
            # get handler for delayed listener update
            self.update_handler = self.hass.loop.call_later(
                delay=(delay := 2.0), callback=self.async_update_listeners
            )
            LOGGER.log(
                logging.INFO if ALLOW_TESTMODE else logging.DEBUG,
                "Coordinator %s delayed listener update for %s seconds during entity restore processing",
                self.client.api.apisession.nickname,
                int(delay),
            )
            return
        if self.update_handler:
            # check if upate handler execution was done and remove handler
            if self.hass.loop.time() - self.update_handler.when() <= 0:
                # skip listener update for now
                LOGGER.log(
                    logging.INFO if ALLOW_TESTMODE else logging.DEBUG,
                    "Coordinator %s skipped listener update due to active delayed processing",
                    self.client.api.apisession.nickname,
                )
                return
            self.update_handler = None
        # inform listeners about changed data
        self.async_update_listeners()

    async def async_refresh_device_details(
        self, reset_cache: bool = False, categories: set | str | None = None
    ) -> None:
        """Update data including device details or dedicated categories only and reset update interval."""
        categories = (
            categories
            if isinstance(categories, set)
            else {categories}
            if isinstance(categories, str)
            else None
        )
        if SolixDeviceType.VEHICLE.value in categories:
            # Refresh only device details for user account
            data = await self.client.async_get_data(vehicle_details=True)
        else:
            data = await self.client.async_get_data(
                device_details=True, reset_cache=reset_cache
            )
        if reset_cache:
            # ensure to refresh entity setup when cache was reset to unload all entities and reload remaining entities
            # This will also restore states from previous state in state machine if required
            self.data = data
            await self.async_reload_config(register_devices=data)
        else:
            # update coordinator data and notify listeners
            self.async_set_updated_data(data)
            # get device IDs for dynamic entity and device creation
            ids = set(data.keys())
            # trigger reload if additional devices are found
            if ids - self.registered_devices:
                await self.async_reload_config(register_devices=data)
            # trigger device removal if not found anymore
            elif (
                ids
                and self.registered_devices
                and (removed := self.registered_devices - ids)
            ):
                await self.async_remove_device(devices=removed)

    async def async_reload_config(
        self, register_devices: set | dict | None = None
    ) -> bool:
        """Reload the configuration entry for all platforms to add missing entities and devices and register found devices."""
        # Wait until client cache is valid before running api action
        await self.client.validate_cache()
        # ensure to refresh entity setup to unload all entities and reload found entities
        if await self.hass.config_entries.async_unload_platforms(
            self.config_entry, PLATFORMS
        ):
            # refresh restore state cache
            await self.hass.config_entries.async_forward_entry_setups(
                self.config_entry, PLATFORMS
            )
            # register current devices to monitor changes
            self.registered_devices = (
                register_devices
                if isinstance(register_devices, set)
                else set(register_devices.keys())
                if isinstance(register_devices, dict)
                else set()
            )
            return True
        return False

    async def async_remove_device(self, devices: set) -> None:
        """Remove given devices if they have no active data."""
        device_entries = dr.async_entries_for_config_entry(
            dr.async_get(self.hass), self.config_entry.entry_id
        )
        for dev_entry in [
            dev for dev in device_entries if dev.serial_number in devices
        ]:
            # check that device has no active entity
            if not any(
                identifier
                for identifier in dev_entry.identifiers
                if identifier[0] == DOMAIN
                for device_serial in self.data
                if device_serial == identifier[1]
            ):
                # remove config entry from device to trigger cleanup
                dr.async_get(self.hass).async_update_device(
                    dev_entry.id,
                    remove_config_entry_id=self.config_entry.entry_id,
                )
                self.registered_devices.discard(dev_entry.serial_number)
                LOGGER.warning(
                    "Api Coordinator %s removed orphaned %s device %s, ID %s",
                    self.config_entry.title,
                    dev_entry.model,
                    dev_entry.name,
                    dev_entry.serial_number,
                )

    async def async_execute_command(
        self, command: str, option: Any = None
    ) -> bool | None:
        """Execute the given command."""
        match command:
            case "refresh_device":
                await self.async_refresh_device_details()
            case "refresh_vehicles":
                await self.async_refresh_device_details(
                    categories=SolixDeviceType.VEHICLE.value
                )
            case "allow_refresh":
                if isinstance(option, bool):
                    self.client.allow_refresh(allow=option)
                    if option:
                        # first restore previous states from cache in state machine to have valid restore state during reload
                        await self.async_refresh_data_from_apidict()
                        # refresh states from recreated cache, which will do the reload
                        await self.async_refresh_device_details(reset_cache=True)
                    else:
                        # refresh states from cache that is virtually empty while refresh not allowed
                        await self.async_refresh_data_from_apidict()
            case "remove_vehicle":
                # Wait until client cache is valid before running api action
                await self.client.validate_cache()
                if option in self.data and isinstance(
                    await self.client.api.manage_vehicle(
                        vehicleId=option,
                        action="delete",
                        toFile=self.client.testmode(),
                    ),
                    dict,
                ):
                    vehicle = self.data.pop(option)
                    self.registered_devices.discard(option)
                    LOGGER.info(
                        "Api Coordinator %s removed vehicle %s device %s",
                        self.config_entry.title,
                        vehicle.get("model") or "",
                        option,
                    )
        return None

    async def async_refresh_delay(self) -> None:
        """Introduce a refresh delay for staggered data collection."""

        # stagger interval for sites update cycle
        sites_shift = timedelta(
            seconds=5
        )  # if self.client.startup else timedelta(seconds=10)
        # get all defined config entries
        cfg_ids: list[str] = [
            cfg.entry_id
            for cfg in self.hass.config_entries.async_entries(domain=DOMAIN)
        ]
        # hass data contains only completely loaded configuration IDs (with coordinators)
        # exclude own coordinator if active already
        active_crds: list[AnkerSolixDataUpdateCoordinator] = [
            c
            for c in (self.hass.data.get(DOMAIN) or {}).values()
            if c.config_entry.entry_id != self.config_entry.entry_id
        ]
        # determine a staggered delay based on last data collections of active coordinators or configuration index if none active yet
        next_refreshes: list[datetime] = [
            c.client.last_site_refresh + c.update_interval + timedelta(seconds=5)
            for c in active_crds
        ]
        next_refreshes.sort()
        # find next gap in active clients
        delay = None
        time_now = datetime.now().astimezone()
        start_time = time_now
        for x in next_refreshes:
            LOGGER.log(
                logging.INFO if ALLOW_TESTMODE else logging.DEBUG,
                "Api Coordinator %s: Other client data refresh expected by %s (in %s seconds)%s",
                self.client.api.apisession.nickname,
                x.strftime("%H:%M:%S"),
                f"{(diff := round((x - time_now).total_seconds()))!s:>3s}",
                " => THROTTLED?"
                if diff < -10
                else " => ACTIVE?"
                if diff < 0
                else " => IN RANGE"
                if diff < sites_shift.total_seconds()
                else "",
            )
            if x - start_time >= sites_shift:
                # existing gap, break with required delay
                delay = round(max(0, (start_time - time_now).total_seconds()))
                break
            # next gap at least site shift from now
            start_time = max(x, time_now) + sites_shift
        if delay is None:
            # set delay according config index or next possible start time
            delay = (
                int(
                    sites_shift.total_seconds()
                    * cfg_ids.index(self.config_entry.entry_id)
                )
                if start_time <= time_now
                else int((start_time - time_now).total_seconds())
            )
        # set client last sites refresh to previous interval for initial run
        if not self.client.last_site_refresh:
            self.client.last_site_refresh = time_now - self.update_interval
        if delay:
            LOGGER.info(
                "Delaying coordinator %s for %s seconds to stagger data refresh",
                self.client.api.apisession.nickname,
                int(delay),
            )
            # delay also last refresh to allow other clients proper next refresh check
            self.client.last_site_refresh = (
                time_now - self.update_interval + timedelta(seconds=delay)
            )
            await sleep(delay)

    async def async_details_delay(self) -> None:
        """Delay next details refresh for staggered data collection."""

        if self.client.intervalcount() >= self.client.deviceintervals():
            # reset delayed time once device details refresh was done
            self.details_delayed = None
        elif self.details_delayed:
            # Adjust projected starttime
            self.details_delayed = (
                datetime.now().astimezone()
                + (self.client.intervalcount() - 1) * self.update_interval
            )
        # return if delay should be skipped
        if (
            (count := self.client.intervalcount()) > 1
            or self.client.deviceintervals() <= 2
            or self.details_delayed
        ):
            return
        # ignore own and short interval coordinators for active coordinators
        active_crds: list[AnkerSolixDataUpdateCoordinator] = [
            c
            for c in (self.hass.data.get(DOMAIN) or {}).values()
            if c.config_entry.entry_id != self.config_entry.entry_id
            and c.client.deviceintervals() > 2
        ]
        # determine a staggered delay based on running or delayed clients that cannot be delayed further
        durations: list[timedelta] = [
            c.details_delayed - datetime.now().astimezone()
            if c.details_delayed
            else max(0, c.client.intervalcount() - 1) * c.update_interval
            for c in active_crds
            if c.client.active_device_refresh or c.details_delayed
        ]
        if durations and min(durations) < timedelta(seconds=70):
            # stagger interval for details update cycle, delay at least 2 min and 1 minute of largest delay remaining
            details_shift = round(
                max(
                    timedelta(seconds=110),
                    max(durations) + timedelta(seconds=110),
                )
                / self.update_interval
                + 0.5
            )
            LOGGER.info(
                "Delaying coordinator %s for %s intervals to stagger device details update",
                self.client.api.apisession.nickname,
                int(details_shift),
            )
            self.client.intervalcount(count + details_shift)
            # calculate projected start time
            self.details_delayed = (
                datetime.now().astimezone()
                + (count + details_shift - 1) * self.update_interval
            )
