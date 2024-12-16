"""DataUpdateCoordinator for Anker Solix."""

from __future__ import annotations

from datetime import timedelta
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
    skip_update: bool

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
        self.skip_update = False

        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=f"{DOMAIN}_{config_entry.title}",
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self) -> None:
        """Update data via library."""
        try:
            if self.skip_update:
                # return existing data if update via Api should be skipped during systems export randomization
                return self.data
            return await self.client.async_get_data()
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
                if isinstance(option,bool):
                    self.client.allow_refresh(allow=option)
                    if option:
                        # enable Api refresh and clear cache
                        await self.async_refresh_device_details(reset_cache=True)
                    else:
                        # disable Api refresh
                        await self.async_refresh_data_from_apidict()
