"""Anker Solix API Client Wrapper."""

from __future__ import annotations

import asyncio
from datetime import datetime
import logging
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

from .const import (
    ALLOW_TESTMODE,
    CONF_ENDPOINT_LIMIT,
    EXAMPLESFOLDER,
    INTERVALMULT,
    LOGGER,
    TESTMODE,
)
from .solixapi import errors
from .solixapi.api import AnkerSolixApi
from .solixapi.apitypes import ApiCategories, SolixDefaults, SolixDeviceType

_LOGGER = LOGGER
# min device refresh delay in seconds
MIN_DEVICE_REFRESH: int = 60
# default interval in seconds for refresh cycle
DEFAULT_UPDATE_INTERVAL: int = 60
# default interval multiplier for device details refresh cycle
DEFAULT_DEVICE_MULTIPLIER: int = 10
# default limit for same endpoint requests per minute, use 0 to disable endpoint throttling
DEFAULT_ENDPOINT_LIMIT: int = SolixDefaults.ENDPOINT_LIMIT_DEF
# default delay for subsequent api requests
DEFAULT_DELAY_TIME: float = SolixDefaults.REQUEST_DELAY_DEF
# Api categories and device types supported for exclusion from integration
API_CATEGORIES: list = [
    SolixDeviceType.PPS.value,
    SolixDeviceType.POWERPANEL.value,
    SolixDeviceType.INVERTER.value,
    SolixDeviceType.SOLARBANK.value,
    SolixDeviceType.SMARTMETER.value,
    SolixDeviceType.SMARTPLUG.value,
    SolixDeviceType.HES.value,
    # SolixDeviceType.POWERCOOLER.value,
    ApiCategories.solarbank_energy,
    ApiCategories.smartmeter_energy,
    ApiCategories.solar_energy,
    ApiCategories.smartplug_energy,
    ApiCategories.powerpanel_energy,
    ApiCategories.powerpanel_avg_power,
    ApiCategories.hes_energy,
    ApiCategories.hes_avg_power,
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
    ApiCategories.powerpanel_energy,
    ApiCategories.hes_energy,
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

    last_site_refresh: datetime | None
    last_device_refresh: datetime | None
    min_device_refresh: int = MIN_DEVICE_REFRESH
    exclude_categories: list
    deferred_data: bool
    cache_valid: bool
    active_device_refresh: bool
    _intervalcount: int
    _allow_refresh: bool
    _startup: bool

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
        # Initialize the api nickname from config title
        if hasattr(entry, "title"):
            self.api.apisession.nickname = entry.title
        self.api.apisession.requestDelay(
            float(data.get(CONF_DELAY_TIME, DEFAULT_DELAY_TIME))
        )
        self.api.apisession.endpointLimit(
            int(data.get(CONF_ENDPOINT_LIMIT, DEFAULT_ENDPOINT_LIMIT))
        )
        self._deviceintervals = int(data.get(INTERVALMULT, DEFAULT_DEVICE_MULTIPLIER))
        self._testmode = bool(data.get(TESTMODE, False))
        self._intervalcount = 0
        self._allow_refresh = True
        self.active_device_refresh = False
        self.last_site_refresh = None
        self.last_device_refresh = None
        self.exclude_categories = data.get(CONF_EXCLUDE, DEFAULT_EXCLUDE_CATEGORIES)
        self.startup = True
        self.deferred_data = False
        self.cache_valid = True

    def toggle_cache(self, toggle: bool) -> None:
        """Toggle the cache valid or invalid."""
        self.cache_valid = bool(toggle)
        _LOGGER.log(
            logging.INFO if ALLOW_TESTMODE else logging.DEBUG,
            "Api Coordinator %s client cache toggled %s",
            self.api.apisession.nickname,
            "VALID" if self.cache_valid else "INVALID temporarily",
        )

    async def validate_cache(self, timeout: int = 10) -> bool:
        """Check and optionally wait up to timeout seconds until cache becomes valid."""
        timeout = (
            int(timeout)
            if isinstance(timeout, float | int) and int(timeout) >= 0
            else 10
        )
        for i in range(1, timeout + 1):
            if self.cache_valid:
                return True
            _LOGGER.log(
                logging.WARNING if ALLOW_TESTMODE else logging.DEBUG,
                "Api Coordinator %s is waiting %s of %s seconds for Api cache to become valid",
                self.api.apisession.nickname,
                i,
                timeout,
            )
            await asyncio.sleep(1)
        return self.cache_valid

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

    async def request(
        self, method: str, endpoint: str, payload: dict | None = None
    ) -> dict:
        """Issue request to Api client and return response or raise error."""
        try:
            return await self.api.apisession.request(
                method=method,
                endpoint=endpoint,
                json=payload,
            )
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
        self,
        from_cache: bool = False,
        device_details: bool = False,
        reset_cache: bool = False,
    ) -> any:
        """Get data from the API."""
        try:
            if self._allow_refresh:
                if reset_cache:
                    # if reset_cache is requested, clear existing api sites and devices caches first prior refresh to avoid stale structures
                    _LOGGER.debug(
                        "Api Coordinator %s is clearing Api cache",
                        self.api.apisession.nickname,
                    )
                    # reset last refresh time to allow details refresh
                    self.last_site_refresh = None
                    self.last_device_refresh = None
                    self.api.clearCaches()
                    self.startup = True
                    self.deferred_data = False
                if from_cache:
                    # if refresh from cache is requested, only the actual api cache will be returned for coordinator data
                    _LOGGER.debug(
                        "Api Coordinator %s is updating data from Api cache",
                        self.api.apisession.nickname,
                    )
                elif device_details:
                    # if device_details requested manually, enforce site and device refresh and reset intervals
                    # avoid consecutive executions within 60 seconds
                    if (
                        self.last_device_refresh
                        and (
                            datetime.now().astimezone() - self.last_device_refresh
                        ).total_seconds()
                        < self.min_device_refresh
                    ):
                        _LOGGER.warning(
                            "Api Coordinator %s cannot enforce device update within less than %s seconds, using data from Api cache",
                            self.api.apisession.nickname,
                            str(self.min_device_refresh),
                        )
                    elif self.active_device_refresh:
                        _LOGGER.warning(
                            "Api Coordinator %s cannot enforce device update while another update is still running, using data from Api cache",
                            self.api.apisession.nickname,
                        )
                    else:
                        self.active_device_refresh = True
                        _LOGGER.log(
                            logging.INFO if ALLOW_TESTMODE else logging.DEBUG,
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
                        if self.startup:
                            _LOGGER.info(
                                "Api Coordinator %s is deferring energy updates",
                                self.api.apisession.nickname,
                            )
                        else:
                            await self.api.update_device_energy(
                                fromFile=self._testmode,
                                exclude=set(self.exclude_categories),
                            )
                        self._intervalcount = self._deviceintervals
                        self.last_site_refresh = datetime.now().astimezone()
                        self.last_device_refresh = datetime.now().astimezone()
                        self.active_device_refresh = False
                        if not self._testmode:
                            _LOGGER.debug(
                                "Api Coordinator %s request statistics: %s",
                                self.api.apisession.nickname,
                                self.api.request_count,
                            )
                else:
                    _LOGGER.log(
                        logging.INFO if ALLOW_TESTMODE else logging.DEBUG,
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
                        self.active_device_refresh = True
                        _LOGGER.log(
                            logging.INFO if ALLOW_TESTMODE else logging.DEBUG,
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
                        if self.startup:
                            _LOGGER.info(
                                "Api Coordinator %s is deferring energy updates",
                                self.api.apisession.nickname,
                            )
                        else:
                            await self.api.update_device_energy(
                                fromFile=self._testmode,
                                exclude=set(self.exclude_categories),
                            )
                        self._intervalcount = self._deviceintervals
                        self.last_device_refresh = datetime.now().astimezone()
                        self.active_device_refresh = False
                    elif self.startup and not self.deferred_data:
                        self.active_device_refresh = True
                        # Fetch deferred energy skipped from first device refresh
                        _LOGGER.info(
                            "Api Coordinator %s is updating deferred energy data",
                            self.api.apisession.nickname,
                        )
                        await self.api.update_device_energy(
                            fromFile=self._testmode,
                            exclude=set(self.exclude_categories),
                        )
                        self.deferred_data = True
                        self.startup = False
                        self.active_device_refresh = False
                    self.last_site_refresh = datetime.now().astimezone()
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
        # Ensure to disable active device refresh flag in case of any exception
        except TimeoutError as exception:
            self.active_device_refresh = False
            raise AnkerSolixApiClientCommunicationError(
                f"Timeout error fetching information: {exception}",
            ) from exception
        except (aiohttp.ClientError, socket.gaierror, errors.ConnectError) as exception:
            self.active_device_refresh = False
            raise AnkerSolixApiClientCommunicationError(
                f"Api Connection Error: {exception}",
            ) from exception
        except (errors.AuthorizationError, errors.InvalidCredentialsError) as exception:
            self.active_device_refresh = False
            raise AnkerSolixApiClientAuthenticationError(
                f"Authentication failed: {exception}",
            ) from exception
        except errors.RetryExceeded as exception:
            self.active_device_refresh = False
            raise AnkerSolixApiClientRetryExceededError(
                f"Retries exceeded: {exception}",
            ) from exception
        except Exception as exception:  # pylint: disable=broad-except
            self.active_device_refresh = False
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

    def intervalcount(self, newcount: int | None = None) -> int:
        """Query or set actual interval count for next device refresh."""
        if (
            newcount is not None
            and isinstance(newcount, float | int)
            and self._intervalcount != int(newcount)
        ):
            _LOGGER.log(
                logging.INFO if ALLOW_TESTMODE else logging.DEBUG,
                "Api Coordinator %s device refresh counter was changed from %s to %s",
                self.api.apisession.nickname,
                self._intervalcount,
                int(newcount),
            )
            self._intervalcount = int(newcount)
        return self._intervalcount

    def deviceintervals(self, intervals: int | None = None) -> int:
        """Query or set deviceintervals for client."""
        if (
            intervals is not None
            and isinstance(intervals, float | int)
            and self._deviceintervals != int(intervals)
        ):
            _LOGGER.info(
                "Api Coordinator %s device refresh multiplier was changed from %s to %s",
                self.api.apisession.nickname,
                self._deviceintervals,
                int(intervals),
            )
            self._deviceintervals = int(intervals)
            self._intervalcount = min(self._deviceintervals, self._intervalcount)
        return self._deviceintervals

    def delay_time(self, seconds: float | None = None) -> float:
        """Query or set Api request delay time for client."""
        if (
            seconds is not None
            and isinstance(seconds, float | int)
            and float(seconds) != float(self.api.apisession.requestDelay())
        ):
            _LOGGER.info(
                "Api Coordinator %s request delay time was changed from %.3f to %.3f seconds",
                self.api.apisession.nickname,
                self.api.apisession.requestDelay(),
                float(seconds),
            )
            self.api.apisession.requestDelay(float(seconds))
        return self.api.apisession.requestDelay()

    def endpoint_limit(self, limit: int | None = None) -> int:
        """Query or set Api endpoint request limit for client."""
        if (
            limit is not None
            and isinstance(limit, float | int)
            and int(limit) != int(self.api.apisession.endpointLimit())
        ):
            _LOGGER.info(
                "Api Coordinator %s endpoint request limit was changed from %s to %s",
                self.api.apisession.nickname,
                self.api.apisession.endpointLimit(),
                str(int(limit)) + " requests" if limit else "disabled",
            )
            self.api.apisession.endpointLimit(int(limit))
        return self.api.apisession.endpointLimit()

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
