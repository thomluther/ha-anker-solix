"""Anker Solix API Client Wrapper."""

from __future__ import annotations

import asyncio
from datetime import datetime
import os
from pathlib import Path
import socket

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_COUNTRY_CODE,
    CONF_DELAY_TIME,
    CONF_EXCLUDE,
    CONF_PASSWORD,
    CONF_USERNAME,
)

from .const import EXAMPLESFOLDER, INTERVALMULT, LOGGER, TESTMODE
from .solixapi import errors
from .solixapi.api import AnkerSolixApi
from .solixapi.apitypes import ApiCategories, SolixDefaults, SolixDeviceType

_LOGGER = LOGGER
MIN_DEVICE_REFRESH: int = 30  # min device refresh delay in seconds
DEFAULT_UPDATE_INTERVAL: int = 60  # default interval in seconds for refresh cycle
DEFAULT_DEVICE_MULTIPLIER: int = (
    10  # default interval multiplier for device details refresh cycle
)
# Api categories and device types supported for exclusion from integration
API_CATEGORIES: list = [
    SolixDeviceType.PPS.value,
    SolixDeviceType.POWERPANEL.value,
    SolixDeviceType.INVERTER.value,
    SolixDeviceType.SOLARBANK.value,
    SolixDeviceType.SMARTMETER.value,
    SolixDeviceType.SMARTPLUG.value,
    # SolixDeviceType.POWERCOOLER.value,
    ApiCategories.solarbank_energy,
    ApiCategories.smartmeter_energy,
    ApiCategories.solar_energy,
    ApiCategories.smartplug_energy,
    ApiCategories.powerpanel_energy,
    ApiCategories.solarbank_cutoff,
    ApiCategories.solarbank_fittings,
    ApiCategories.solarbank_solar_info,
    ApiCategories.device_auto_upgrade,
    ApiCategories.device_tag,
    ApiCategories.site_price,
]
DEFAULT_EXCLUDE_CATEGORIES: list = [
    ApiCategories.solarbank_energy,
    ApiCategories.smartmeter_energy,
    ApiCategories.solar_energy,
    ApiCategories.smartplug_energy,
]


async def json_example_folders() -> list:
    """Get actual list of json example folders."""
    examplesfolder: Path = Path(__file__).parent / EXAMPLESFOLDER
    if examplesfolder.is_dir():
        loop = asyncio.get_running_loop()
        contentlist = await loop.run_in_executor(None, os.scandir, examplesfolder)
        return [f.name for f in contentlist if f.is_dir()]
    return []


class AnkerSolixApiClientError(Exception):
    """Exception to indicate a general API error."""


class AnkerSolixApiClientCommunicationError(AnkerSolixApiClientError):
    """Exception to indicate a communication error."""


class AnkerSolixApiClientAuthenticationError(AnkerSolixApiClientError):
    """Exception to indicate an authentication error."""


class AnkerSolixApiClientRetryExceededError(AnkerSolixApiClientError):
    """Exception to indicate an authentication error."""


class AnkerSolixApiClient:
    """API Client using the AnkerSolixApi class.

    deviceinterval: Optionally specify on how many refresh intervals a device update is fetched, that needs additional API requires per device
    """

    last_device_refresh: datetime | None
    min_device_refresh: int = MIN_DEVICE_REFRESH
    exclude_categories: list
    _intervalcount: int
    _allow_refresh: bool

    def __init__(
        self,
        entry: ConfigEntry | dict,
        session: aiohttp.ClientSession,
    ) -> None:
        """Init API Client."""
        data = {}
        # Merge data and options into flat dictionary
        if isinstance(entry, ConfigEntry):
            if hasattr(entry, "data"):
                data.update(entry.data)
            if hasattr(entry, "options"):
                data.update(entry.options)
        else:
            data = entry

        self.api = AnkerSolixApi(
            data.get(CONF_USERNAME),
            data.get(CONF_PASSWORD),
            data.get(CONF_COUNTRY_CODE),
            session,
            _LOGGER,
        )
        self.api.apisession.requestDelay(
            float(data.get(CONF_DELAY_TIME, SolixDefaults.REQUEST_DELAY_DEF))
        )
        self._deviceintervals = int(data.get(INTERVALMULT, DEFAULT_DEVICE_MULTIPLIER))
        self._testmode = bool(data.get(TESTMODE, False))
        self._intervalcount = 0
        self._allow_refresh = True
        self.last_device_refresh = None
        self.exclude_categories = data.get(CONF_EXCLUDE, DEFAULT_EXCLUDE_CATEGORIES)

    async def authenticate(self, restart: bool = False) -> bool:
        """Get (chached) login response from api, if restart is True, the login will be refreshed from server to test credentials."""
        try:
            return await self.api.async_authenticate(restart=restart) or not restart
        except TimeoutError as exception:
            raise AnkerSolixApiClientCommunicationError(
                f"Timeout error fetching information: {exception}",
            ) from exception
        except (aiohttp.ClientError, socket.gaierror, errors.ConnectError) as exception:
            raise AnkerSolixApiClientCommunicationError(
                f"Api Connection Error: {exception}",
            ) from exception
        except (errors.AuthorizationError, errors.InvalidCredentialsError) as exception:
            raise AnkerSolixApiClientAuthenticationError(
                f"Authentication failed: {exception}",
            ) from exception
        except errors.RetryExceeded as exception:
            raise AnkerSolixApiClientRetryExceededError(
                f"Login Retries exceeded: {exception}",
            ) from exception
        except Exception as exception:  # pylint: disable=broad-except
            raise AnkerSolixApiClientError(
                f"Api Request Error: {type(exception)}: {exception}"
            ) from exception

    async def async_get_data(
        self, from_cache: bool = False, device_details: bool = False
    ) -> any:
        """Get data from the API."""
        try:
            if self._allow_refresh:
                if from_cache:
                    # if refresh from cache is requested, only the actual api dictionaries will be returned of coordinator data
                    _LOGGER.debug(
                        "Api Coordinator %s is updating data from Api dictionaries",
                        self.api.apisession.nickname,
                    )
                elif device_details:
                    # if device_details requested, enforce site and device refresh and reset intervals
                    # avoid consecutive executions within 30 seconds
                    if (
                        self.last_device_refresh
                        and (
                            datetime.now().astimezone() - self.last_device_refresh
                        ).total_seconds()
                        < self.min_device_refresh
                    ):
                        _LOGGER.warning(
                            "Api Coordinator %s cannot enforce device update within less than %s seconds, using data from Api dictionaries",
                            self.api.apisession.nickname,
                            str(self.min_device_refresh),
                        )
                    else:
                        _LOGGER.debug(
                            "Api Coordinator %s is enforcing site and device update %s",
                            self.api.apisession.nickname,
                            f"from folder {self.api.testDir()}"
                            if self._testmode
                            else "",
                        )
                        await self.api.update_sites(
                            fromFile=self._testmode,
                            exclude=set(self.exclude_categories),
                        )
                        # Fetch site details without excluded types or categories
                        await self.api.update_site_details(
                            fromFile=self._testmode,
                            exclude=set(self.exclude_categories),
                        )
                        # Fetch device details without excluded types or categories
                        await self.api.update_device_details(
                            fromFile=self._testmode,
                            exclude=set(self.exclude_categories),
                        )
                        # Fetch energy if not excluded via options
                        await self.api.update_device_energy(
                            fromFile=self._testmode,
                            exclude=set(self.exclude_categories),
                        )
                        self._intervalcount = self._deviceintervals
                        self.last_device_refresh = datetime.now().astimezone()
                        if not self._testmode:
                            _LOGGER.debug(
                                "Api Coordinator %s request statistics: %s",
                                self.api.apisession.nickname,
                                self.api.request_count,
                            )
                else:
                    _LOGGER.debug(
                        "Api Coordinator %s is updating sites %s",
                        self.api.apisession.nickname,
                        f"from folder {self.api.testDir()}" if self._testmode else "",
                    )
                    await self.api.update_sites(
                        fromFile=self._testmode,
                        exclude=set(self.exclude_categories),
                    )
                    # update device details only after given refresh interval count
                    self._intervalcount -= 1
                    if self._intervalcount <= 0:
                        _LOGGER.debug(
                            "Api Coordinator %s is updating devices %s",
                            self.api.apisession.nickname,
                            f"from folder {self.api.testDir()}"
                            if self._testmode
                            else "",
                        )
                        # Fetch site details without excluded types or categories
                        await self.api.update_site_details(
                            fromFile=self._testmode,
                            exclude=set(self.exclude_categories),
                        )
                        # Fetch device details without excluded types or categories
                        await self.api.update_device_details(
                            fromFile=self._testmode,
                            exclude=set(self.exclude_categories),
                        )
                        # Fetch energy if not excluded via options
                        await self.api.update_device_energy(
                            fromFile=self._testmode,
                            exclude=set(self.exclude_categories),
                        )
                        self._intervalcount = self._deviceintervals
                        self.last_device_refresh = datetime.now().astimezone()
                    if not self._testmode:
                        _LOGGER.debug(
                            "Api Coordinator %s request statistics: %s",
                            self.api.apisession.nickname,
                            self.api.request_count,
                        )
                # combine api sites, devices and account dictionaries for single data cache
                data = self.api.getCaches()
            else:
                # do not provide data when refresh suspended to avoid stale data from cache is used for real
                data = {}
            _LOGGER.debug("Coordinator %s data: %s", self.api.apisession.nickname, data)
            return data  # noqa: TRY300
        except TimeoutError as exception:
            raise AnkerSolixApiClientCommunicationError(
                f"Timeout error fetching information: {exception}",
            ) from exception
        except (aiohttp.ClientError, socket.gaierror, errors.ConnectError) as exception:
            raise AnkerSolixApiClientCommunicationError(
                f"Api Connection Error: {exception}",
            ) from exception
        except (errors.AuthorizationError, errors.InvalidCredentialsError) as exception:
            raise AnkerSolixApiClientAuthenticationError(
                f"Authentication failed: {exception}",
            ) from exception
        except errors.RetryExceeded as exception:
            raise AnkerSolixApiClientRetryExceededError(
                f"Retries exceeded: {exception}",
            ) from exception
        except Exception as exception:  # pylint: disable=broad-except
            raise AnkerSolixApiClientError(
                f"Api Request Error: {type(exception)}: {exception}"
            ) from exception

    def testmode(self, mode: bool | None = None) -> bool:
        """Query or set testmode for client."""
        if mode is not None and self._testmode != mode:
            self._testmode = mode
            _LOGGER.info(
                "Api Coordinator %s testmode was changed to %s",
                self.api.apisession.nickname,
                ("ENABLED" if mode else "DISABLED"),
            )
        return self._testmode

    def deviceintervals(self, intervals: int | None = None) -> int:
        """Query or set deviceintervals for client."""
        if (
            intervals is not None
            and isinstance(intervals, float | int)
            and self._deviceintervals != int(intervals)
        ):
            self._deviceintervals = int(intervals)
            self._intervalcount = min(self._deviceintervals, self._intervalcount)
            _LOGGER.info(
                "Api Coordinator %s device refresh multiplier was changed to %s",
                self.api.apisession.nickname,
                self._deviceintervals,
            )
        return self._deviceintervals

    def delay_time(self, seconds: float | None = None) -> float:
        """Query or set Api request delay time for client."""
        if (
            seconds is not None
            and isinstance(seconds, float | int)
            and float(seconds) != float(self.api.apisession.requestDelay())
        ):
            newdelay = self.api.apisession.requestDelay(float(seconds))
            _LOGGER.info(
                "Api Coordinator %s Api request delay time was changed to %.3f seconds",
                self.api.apisession.nickname,
                newdelay,
            )
        return self.api.apisession.requestDelay()

    def allow_refresh(self, allow: bool | None = None) -> bool:
        """Query or set api refresh capability for client."""
        if allow is not None and allow != self._allow_refresh:
            self._allow_refresh = allow
            _LOGGER.info(
                "Api Coordinator %s refresh was changed to %s",
                self.api.apisession.nickname,
                ("ENABLED" if allow else "DISABLED"),
            )
        return self._allow_refresh
