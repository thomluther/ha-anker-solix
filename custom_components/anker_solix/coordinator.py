"""DataUpdateCoordinator for Anker Solix."""

from __future__ import annotations

from asyncio import sleep
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api_client import (
    AnkerSolixApiClient,
    AnkerSolixApiClientAuthenticationError,
    AnkerSolixApiClientCommunicationError,
    AnkerSolixApiClientError,
    AnkerSolixApiClientRetryExceededError,
)
from .const import DOMAIN, LOGGER, PLATFORMS


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class AnkerSolixDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to coordinate fetching of all data from the API."""

    config_entry: ConfigEntry
    client: AnkerSolixApiClient

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

        super().__init__(
            hass=hass,
            logger=LOGGER,
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
            # stagger non-initial device details updates if required
            if not self.client.startup:
                await self.async_details_delay()
            data = await self.client.async_get_data()
            # make sure deferred data will create additional entities
            if self.client.deferred_data and self.config_entry:
                if await self.hass.config_entries.async_unload_platforms(
                    self.config_entry, PLATFORMS
                ):
                    self.client.deferred_data = False
                    await self.hass.config_entries.async_forward_entry_setups(
                        self.config_entry, PLATFORMS
                    )
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

    async def async_refresh_data_from_apidict(self) -> None:
        """Update data from client api dictionaries without resetting update interval."""
        self.data = await self.client.async_get_data(from_cache=True)
        # inform listeners about changed data
        self.async_update_listeners()

    async def async_refresh_device_details(self, reset_cache: bool = False) -> None:
        """Update data including device details and reset update interval."""
        data = await self.client.async_get_data(
            device_details=True, reset_cache=reset_cache
        )
        if reset_cache:
            # ensure to refresh entity setup when cache was reset to unload all entities and reload remaining entities
            self.data = data
            if await self.hass.config_entries.async_unload_platforms(
                self.config_entry, PLATFORMS
            ):
                await self.hass.config_entries.async_forward_entry_setups(
                    self.config_entry, PLATFORMS
                )
        else:
            # update only coordinator data and notify listeners
            self.async_set_updated_data(data)

    async def async_execute_command(self, command: str, option: Any = None) -> None:
        """Execute the given command."""
        match command:
            case "refresh_device":
                await self.async_refresh_device_details()
            case "allow_refresh":
                if isinstance(option, bool):
                    self.client.allow_refresh(allow=option)
                    if option:
                        # enable Api refresh and clear cache
                        await self.async_refresh_device_details(reset_cache=True)
                    else:
                        # disable Api refresh
                        await self.async_refresh_data_from_apidict()

    async def async_refresh_delay(self) -> None:
        """Introduce a refresh delay for staggered data collection."""

        # stagger interval for sites update cycle
        sites_shift = timedelta(seconds=10)
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
            c.client.last_site_refresh + c.update_interval for c in active_crds
        ]
        next_refreshes.sort()
        # find next 10 sec gap in active clients
        delay = 0
        time_now = datetime.now().astimezone()
        start_time = time_now
        for x in next_refreshes:
            if x - start_time >= sites_shift:
                delay = int(max(0, (start_time - time_now).total_seconds()))
                break
            start_time = x + sites_shift
        if not delay:
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
            self.client.last_site_refresh = (
                time_now - self.update_interval + timedelta(seconds=delay)
            )
        if delay:
            LOGGER.info(
                "Delaying coordinator %s for %s seconds to stagger data refresh",
                self.client.api.apisession.nickname,
                int(delay),
            )
            await sleep(delay)

    async def async_details_delay(self) -> None:
        """Delay next details refresh for staggered data collection."""

        if (count := self.client.intervalcount()) > 1:
            return
        # exclude own coordinator from active coordinators
        active_crds: list[AnkerSolixDataUpdateCoordinator] = [
            c
            for c in (self.hass.data.get(DOMAIN) or {}).values()
            if c.config_entry.entry_id != self.config_entry.entry_id
        ]
        # determine a staggered delay based on other active client min intervals
        durations: list[timedelta] = [
            max(0, c.client.intervalcount() - 1) * self.update_interval
            for c in active_crds
        ]
        if durations and min(durations) < timedelta(seconds=60):
            # stagger interval for details update cycle, delay at least 2 min
            details_shift = round(timedelta(seconds=110) / self.update_interval + 0.5)
            LOGGER.info(
                "Delaying coordinator %s for %s intervals to stagger device details update",
                self.client.api.apisession.nickname,
                int(details_shift),
            )
            self.client.intervalcount(count + details_shift)
