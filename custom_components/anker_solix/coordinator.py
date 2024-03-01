"""DataUpdateCoordinator for Anker Solix."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api_client import (
    AnkerSolixApiClient,
    AnkerSolixApiClientAuthenticationError,
    AnkerSolixApiClientCommunicationError,
    AnkerSolixApiClientError,
)
from .const import DOMAIN, LOGGER


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class AnkerSolixDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to coordinate fetching of all data from the API."""

    config_entry: ConfigEntry

    def __init__(
        self, hass: HomeAssistant, client: AnkerSolixApiClient, update_interval: int
    ) -> None:
        """Initialize."""
        self.client = client
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=f"{DOMAIN}_{client.api._email}",
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self):
        """Update data via library."""
        try:
            return await self.client.async_get_data()
        except AnkerSolixApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except (
            AnkerSolixApiClientError,
            AnkerSolixApiClientCommunicationError,
        ) as exception:
            raise UpdateFailed(exception) from exception

    async def async_refresh_data_from_apidict(self):
        """Update data from client api dictionaries."""
        self.data = await self.client.async_get_data(from_cache=True)
        # inform listeners about changed data
        self.async_update_listeners()

    async def async_refresh_device_details(self):
        """Update data including device details and reset update interval."""
        self.async_set_updated_data(await self.client.async_get_data(device_details=True))

    async def async_execute_command(self, command: str):
        """Execute the given command."""
        match(command):
            case "refresh_device":
                await self.async_refresh_device_details()

