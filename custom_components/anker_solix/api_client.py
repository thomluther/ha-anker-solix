"""Anker Solix API Client Wrapper."""
from __future__ import annotations

from datetime import datetime
import os
import socket

import aiohttp

from .const import EXAMPLESFOLDER, LOGGER
from .solixapi import api, errors

_LOGGER = LOGGER


def json_example_folders() -> list:
    """Get actual list of json example folders."""
    examplesfolder: str = os.path.join(os.path.dirname(__file__), EXAMPLESFOLDER)
    if os.path.isdir(examplesfolder):
        return [f.name for f in os.scandir(examplesfolder) if f.is_dir()]
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

    MIN_DEVICE_REFRESH = 30

    def __init__(
        self,
        username: str,
        password: str,
        countryid: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Init API Client."""
        self.api = api.AnkerSolixApi(username, password, countryid, session, _LOGGER)
        self._deviceintervals = 10
        self._intervalcount = 0
        self._testmode = False
        self.last_device_refresh: datetime | None = None
        self._allow_refresh: bool = True

    async def authenticate(self, restart: bool = False) -> bool:
        """Get (chached) login response from api, if restart is True, the login will be refreshed from server to test credentials."""
        try:
            return await self.api.async_authenticate(restart=restart) or not restart
        except TimeoutError as exception:
            raise AnkerSolixApiClientCommunicationError(
                f"Timeout error fetching information: {exception}",
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            raise AnkerSolixApiClientCommunicationError(
                f"Error fetching information: {exception}",
            ) from exception
        except errors.AuthorizationError as exception:
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
                        self.api.nickname,
                    )
                elif device_details:
                    # if device_details requested, enforce site and device refresh and reset intervals
                    # avoid consecutive executions within 30 seconds
                    if (
                        self.last_device_refresh
                        and (
                            datetime.now().astimezone() - self.last_device_refresh
                        ).total_seconds()
                        < self.MIN_DEVICE_REFRESH
                    ):
                        _LOGGER.warning(
                            "Api Coordinator %s cannot enforce device update within less than %s seconds, using data from Api dictionaries",
                            self.api.nickname,
                            str(self.MIN_DEVICE_REFRESH),
                        )
                    else:
                        _LOGGER.debug(
                            "Api Coordinator %s is enforcing site and device update %s",
                            self.api.nickname,
                            f"from folder {self.api.testDir()}"
                            if self._testmode
                            else "",
                        )
                        await self.api.update_sites(fromFile=self._testmode)
                        await self.api.update_device_details(fromFile=self._testmode)
                        self._intervalcount = self._deviceintervals
                        self.last_device_refresh = datetime.now().astimezone()
                else:
                    _LOGGER.debug(
                        "Api Coordinator %s is updating sites %s",
                        self.api.nickname,
                        f"from folder {self.api.testDir()}" if self._testmode else "",
                    )
                    await self.api.update_sites(fromFile=self._testmode)
                    # update device details only after given refresh interval count
                    self._intervalcount -= 1
                    if self._intervalcount <= 0:
                        _LOGGER.debug(
                            "Api Coordinator %s is updating devices %s",
                            self.api.nickname,
                            f"from folder {self.api.testDir()}"
                            if self._testmode
                            else "",
                        )
                        await self.api.update_device_details(fromFile=self._testmode)
                        self._intervalcount = self._deviceintervals
                        self.last_device_refresh = datetime.now().astimezone()
                # combine site and device details dict
                data = self.api.sites | self.api.devices
            else:
                # do not provide data when refresh suspended to avoid stale data from cache are used for real
                data = {}
            _LOGGER.debug("Coordinator %s data: %s", self.api.nickname, data)
            return data
        except TimeoutError as exception:
            raise AnkerSolixApiClientCommunicationError(
                f"Timeout error fetching information: {exception}",
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            raise AnkerSolixApiClientCommunicationError(
                f"Error fetching information: {exception}",
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

    def testmode(self, mode: bool = None) -> bool:
        """Query or set testmode for client."""
        if mode is None:
            return self._testmode
        if self._testmode != mode:
            _LOGGER.info(
                "Api Coordinator %s testmode was changed to %s",
                self.api.nickname,
                ("ENABLED" if mode else "DISABLED"),
            )
            self._testmode = mode
        return self._testmode

    def deviceintervals(self, intervals: int = None) -> int:
        """Query or set deviceintervals for client."""
        if intervals is None:
            return self._deviceintervals
        if self._deviceintervals != intervals:
            _LOGGER.info(
                "Api Coordinator %s device refresh multiplier was changed to %s",
                self.api.nickname,
                intervals,
            )
            self._deviceintervals = intervals
            self._intervalcount = min(intervals, self._intervalcount)
        return self._deviceintervals

    def allow_refresh(self, allow: bool = None) -> bool:
        """Query or set api refresh capability for client."""
        if allow is None:
            return self._allow_refresh
        self._allow_refresh = allow
        return self._allow_refresh
