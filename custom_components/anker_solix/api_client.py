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
    CONF_TIMEOUT,
    CONF_USERNAME,
)

from .const import (
    ALLOW_TESTMODE,
    CONF_API_OPTIONS,
    CONF_ENDPOINT_LIMIT,
    CONF_MQTT_OPTIONS,
    CONF_MQTT_TEST_SPEED,
    CONF_MQTT_USAGE,
    CONF_TEST_OPTIONS,
    CONF_TRIGGER_TIMEOUT,
    DEFAULT_MQTT_USAGE,
    EXAMPLESFOLDER,
    INTERVALMULT,
    LOGGER,
    TESTFOLDER,
    TESTMODE,
)
from .solixapi import errors
from .solixapi.api import AnkerSolixApi
from .solixapi.apitypes import ApiCategories, SolixDefaults, SolixDeviceType
from .solixapi.mqtt_device import SolixMqttDevice
from .solixapi.mqtt_factory import SolixMqttDeviceFactory

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
# default timeout for api requests
DEFAULT_TIMEOUT: int = SolixDefaults.REQUEST_TIMEOUT_DEF
# default MQTT usage
DEFAULT_MQTT: bool = DEFAULT_MQTT_USAGE
# default timeout for MQTT realtime trigger
DEFAULT_TRIGGER_TIMEOUT: int = SolixDefaults.TRIGGER_TIMEOUT_DEF
# Api categories and device types supported for exclusion from integration
API_CATEGORIES: list = [
    SolixDeviceType.PPS.value,
    SolixDeviceType.POWERPANEL.value,
    SolixDeviceType.INVERTER.value,
    SolixDeviceType.SOLARBANK.value,
    SolixDeviceType.SMARTMETER.value,
    SolixDeviceType.SMARTPLUG.value,
    SolixDeviceType.COMBINER_BOX.value,
    SolixDeviceType.HES.value,
    SolixDeviceType.VEHICLE.value,
    # SolixDeviceType.CHARGER.value,
    # SolixDeviceType.SOLARBANK_PPS.value,
    # SolixDeviceType.EV_CHARGER.value,
    # SolixDeviceType.POWERCOOLER.value,
    ApiCategories.account_info,
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
        # Initialize the api nickname from config title or extra data field
        if hasattr(entry, "title"):
            self.api.apisession.nickname = entry.title
        else:
            self.api.apisession.nickname = data.get("nickname", "")
        self.api.apisession.requestDelay(
            float(
                (data.get(CONF_API_OPTIONS) or {}).get(
                    CONF_DELAY_TIME, DEFAULT_DELAY_TIME
                )
            )
        )
        self.api.apisession.requestTimeout(
            int((data.get(CONF_API_OPTIONS) or {}).get(CONF_TIMEOUT, DEFAULT_TIMEOUT))
        )
        self.api.apisession.endpointLimit(
            int(
                (data.get(CONF_API_OPTIONS) or {}).get(
                    CONF_ENDPOINT_LIMIT, DEFAULT_ENDPOINT_LIMIT
                )
            )
        )
        self._testmode = bool((data.get(CONF_TEST_OPTIONS) or {}).get(TESTMODE, False))
        if self._testmode and (
            testfolder := (data.get(CONF_TEST_OPTIONS) or {}).get(TESTFOLDER)
        ):
            # set json test file folder for api
            self.api.testDir(
                subfolder=str(Path(entry.data.get(EXAMPLESFOLDER, "")) / testfolder)
            )
        self._deviceintervals = int(
            (data.get(CONF_API_OPTIONS) or {}).get(
                INTERVALMULT, DEFAULT_DEVICE_MULTIPLIER
            )
        )
        self._intervalcount = 0
        self._allow_refresh = True
        self._mqtt_usage = bool(
            (data.get(CONF_MQTT_OPTIONS) or {}).get(CONF_MQTT_USAGE, DEFAULT_MQTT_USAGE)
        )
        self._trigger_timeout: int = int(
            (data.get(CONF_MQTT_OPTIONS) or {}).get(
                CONF_TRIGGER_TIMEOUT, DEFAULT_TRIGGER_TIMEOUT
            )
        )
        self._mqtt_task: asyncio.Task | None = None
        self._task_dict: dict = {}
        self._mqtt_test_speed: float = float(
            (data.get(CONF_TEST_OPTIONS) or {}).get(CONF_MQTT_TEST_SPEED, 1)
        )
        # track created MQTT device instances
        self.mqtt_devices: dict[str, SolixMqttDevice] = {}
        self.active_device_refresh = False
        self.last_site_refresh = None
        self.last_device_refresh = None
        self.exclude_categories = data.get(CONF_EXCLUDE, DEFAULT_EXCLUDE_CATEGORIES)
        self.startup = True
        self.deferred_data = False
        self.cache_valid = True

    def toggle_cache(self, toggle: bool) -> None:
        """Define export callback to toggle the cache valid or invalid."""
        if self.cache_valid != toggle:
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
            _LOGGER.exception("Api Client Exception:")
            raise AnkerSolixApiClientError(
                f"Api Client Error: {type(exception)}: {exception}"
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
            _LOGGER.exception("Api Client Exception:")
            raise AnkerSolixApiClientError(
                f"Api Client Error: {type(exception)}: {exception}"
            ) from exception

    async def async_get_data(
        self,
        from_cache: bool = False,
        device_details: bool = False,
        vehicle_details: bool = False,
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
                    # stop any active file poller task
                    if self._mqtt_task:
                        self._mqtt_task.cancel()
                        self._mqtt_task = None
                    # Clear cache, this will also stop active MQTT session
                    self.api.clearCaches()
                    # drop MQTT device instances
                    self.mqtt_devices = {}
                    self.startup = True
                    self.deferred_data = False
                if from_cache:
                    # if refresh from cache is requested, only the actual api cache will be returned for coordinator data
                    _LOGGER.debug(
                        "Api Coordinator %s is updating data from Api cache",
                        self.api.apisession.nickname,
                    )
                elif vehicle_details:
                    # if vehicle refresh is requested, run only the vehicle routines if not excluded
                    if {SolixDeviceType.VEHICLE.value} - set(self.exclude_categories):
                        _LOGGER.log(
                            logging.INFO if ALLOW_TESTMODE else logging.DEBUG,
                            "Api Coordinator %s is enforcing vehicle update %s",
                            self.api.apisession.nickname,
                            f"from folder {self.api.testDir()}"
                            if self._testmode
                            else "",
                        )
                        # Fetch vehicle details for account
                        for vehicle in (
                            await self.api.get_vehicle_list(fromFile=self._testmode)
                        ).get("vehicle_list") or []:
                            await self.api.get_vehicle_details(
                                vehicleId=vehicle.get("vehicle_id"),
                                fromFile=self._testmode,
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
                        # Fetch device details without excluded types or categories
                        await self.api.update_device_details(
                            fromFile=self._testmode,
                            exclude=set(self.exclude_categories),
                        )
                        # Fetch site details without excluded types or categories
                        # This must be run after the device details, which may create virtual sites for standalone devices
                        await self.api.update_site_details(
                            fromFile=self._testmode,
                            exclude=set(self.exclude_categories),
                        )
                        # Re-Start MQTT session if usage enabled
                        await self.check_mqtt_session()
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
                        # Fetch device details without excluded types or categories
                        await self.api.update_device_details(
                            fromFile=self._testmode,
                            exclude=set(self.exclude_categories),
                        )
                        # Fetch site details without excluded types or categories
                        # This must be run after the device details, which may create virtual sites for standalone devices
                        await self.api.update_site_details(
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
                        # ensure MQTT session status is as required
                        await self.check_mqtt_session()
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
            _LOGGER.exception("Api Client Exception:")
            raise AnkerSolixApiClientError(
                f"Api Client Error: {type(exception)}: {exception}"
            ) from exception
        # Ensure to disable active device refresh flag in case of any exception
        finally:
            self.active_device_refresh = False

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

    def timeout(self, seconds: int | None = None) -> int:
        """Query or set Api request timeout for client."""
        if (
            seconds is not None
            and isinstance(seconds, float | int)
            and round(seconds) != self.api.apisession.requestTimeout()
        ):
            _LOGGER.info(
                "Api Coordinator %s request timeout was changed from %s to %s seconds",
                self.api.apisession.nickname,
                str(self.api.apisession.requestTimeout()),
                str(round(seconds)),
            )
            self.api.apisession.requestTimeout(round(seconds))
        return self.api.apisession.requestTimeout()

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

    def mqtt_test_speed(self, factor: float | None = None) -> float:
        """Query or set factor for MQTT file polling speed in test mode."""
        if (
            factor is not None
            and isinstance(factor, float | int)
            and float(factor) != float(self._mqtt_test_speed)
        ):
            _LOGGER.info(
                "Api Coordinator %s MQTT file polling speed factor was changed from %.2f to %.2f",
                self.api.apisession.nickname,
                self._mqtt_test_speed,
                float(factor),
            )
            self._mqtt_test_speed = float(factor)
            # update speed also in task dictionary for active task
            self._task_dict["speed"] = self._mqtt_test_speed
        return self._mqtt_test_speed

    def get_registered_vehicles(self) -> list:
        """Get the registered vehicles of api client."""
        return self.api.account.get("vehicles_registered") or []

    async def mqtt_usage(self, enable: bool | None = None) -> bool:
        """Query or set MQTT usage for Api, which will also start or stop the MQTT session upon change."""
        if (
            enable is not None
            and isinstance(enable, bool)
            and enable != self._mqtt_usage
        ):
            _LOGGER.info(
                "Api Coordinator %s MQTT usage was changed from %s to %s",
                self.api.apisession.nickname,
                self._mqtt_usage,
                enable,
            )
            self._mqtt_usage = enable
            if enable:
                await self.check_mqtt_session()
            else:
                self.api.stopMqttSession()
                # drop MQTT device instances
                self.mqtt_devices = {}
        return self._mqtt_usage

    def trigger_timeout(self, seconds: int | None = None) -> int:
        """Query or set Api MQTT real time trigger timeout for client."""
        if (
            seconds is not None
            and isinstance(seconds, float | int)
            and (seconds := round(seconds)) != self._trigger_timeout
        ):
            _LOGGER.info(
                "Api Coordinator %s MQTT real time trigger timeout was changed from %s to %s seconds",
                self.api.apisession.nickname,
                str(self._trigger_timeout),
                str(seconds),
            )
            self._trigger_timeout = seconds
        return self._trigger_timeout

    def get_mqtt_device(self, sn: str) -> SolixMqttDevice | None:
        """Get the MQTT device instance for given SN."""
        return (isinstance(sn, str) and self.mqtt_devices.get(sn)) or None

    def get_mqtt_devices(
        self,
        siteId: str | None = None,
        stationSn: str | None = None,
        extraDeviceSn: str | None = None,
        mqttControl: str | None = None,
    ) -> list[SolixMqttDevice]:
        """Get the MQTT devices that match the siteId and/or stationSn, or the extraDeviceSn parameters and the optional mqttControl."""
        return [
            md
            for md in self.mqtt_devices.values()
            if (not mqttControl or mqttControl in md.controls)
            and (
                md.sn == extraDeviceSn
                or (
                    (siteId is None or md.device.get("site_id") == siteId)
                    and (stationSn is None or md.device.get("station_sn") == stationSn)
                )
            )
        ]

    def get_mqtt_valuecount(self, sn: str | None = None) -> int:
        """Get the MQTT value count for all or the provided device serial."""
        count = 0
        for mdev in self.mqtt_devices.values():
            count += len(mdev.mqttdata) if (not sn or sn == mdev.sn) else 0
        return count

    async def check_mqtt_session(self) -> None:
        """Check mqtt usage and status of session, restart if required."""
        if self._mqtt_usage and (
            not self.api.mqttsession or not self.api.mqttsession.is_connected()
        ):
            _LOGGER.info(
                "Api Coordinator %s is (re-)starting MQTT session",
                self.api.apisession.nickname,
            )
            if await self.api.startMqttSession(fromFile=self._testmode):
                mqtt_devs = [
                    dev
                    for dev in self.api.devices.values()
                    if dev.get("mqtt_supported")
                ]
                if self._testmode:
                    # start MQTT file poller in file mode
                    # update the folder in the task dictionary for MQTT file polling
                    self._task_dict["folder"] = self.api.testDir()
                    self._task_dict["speed"] = self._mqtt_test_speed
                    # Create task for polling mqtt messages from files for testing
                    self._mqtt_task = asyncio.get_running_loop().create_task(
                        self.api.mqttsession.file_poller(
                            folderdict=self._task_dict,
                        )
                    )
                    _LOGGER.info(
                        "Api Coordinator %s MQTT file data poller task was started with speed %s for folder: %s",
                        self.api.apisession.nickname,
                        self._task_dict["speed"],
                        self._task_dict["folder"],
                    )
                else:
                    # subscribe eligible devices in live mode
                    _LOGGER.info(
                        "Api Coordinator %s MQTT session connected, subscribing eligible devices",
                        self.api.apisession.nickname,
                    )
                    for dev in mqtt_devs:
                        topic = (
                            f"{self.api.mqttsession.get_topic_prefix(deviceDict=dev)}#"
                        )
                        resp = self.api.mqttsession.subscribe(topic)
                        if resp and resp.is_failure:
                            _LOGGER.warning(
                                "Api Coordinator %s failed subscription for MQTT topic: %s",
                                self.api.apisession.nickname,
                                topic,
                            )
                        else:
                            _LOGGER.log(
                                logging.INFO if ALLOW_TESTMODE else logging.DEBUG,
                                "Api Coordinator %s subscribed to MQTT topic %s",
                                self.api.apisession.nickname,
                                topic,
                            )
                    if not mqtt_devs:
                        _LOGGER.warning(
                            "Api Coordinator %s did not find eligible devices for MQTT subscription",
                            self.api.apisession.nickname,
                        )
                # create MQTT device instances
                for dev in mqtt_devs:
                    sn = dev.get("device_sn")
                    if sn and (
                        mdev := SolixMqttDeviceFactory(
                            api_instance=self.api, device_sn=sn
                        ).create_device()
                    ):
                        self.mqtt_devices[sn] = mdev
                # Note: The method for update callback will be checked and set during coordinator updates
            else:
                _LOGGER.error(
                    "Api Coordinator %s failed to start MQTT session",
                    self.api.apisession.nickname,
                )
