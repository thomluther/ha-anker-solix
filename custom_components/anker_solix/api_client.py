"""Anker Solix API Client Wrapper."""
from __future__ import annotations

import asyncio
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
        return [
            f.name
            for f in os.scandir(examplesfolder)
            if f.is_dir()
        ]
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

    async def authenticate(self, restart: bool = False) -> bool:
        """Get (chached) login response from api, if restart is True, the login will be refreshed from server to test credentials."""
        try:
            return (
                await self.api.async_authenticate(restart=restart) or not restart
            )
        except asyncio.TimeoutError as exception:
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
                f"Api Request Error: {exception}"
            ) from exception

    async def async_get_data(self, from_cache: bool=False) -> any:
        """Get data from the API."""
        try:
            # if refresh from cache is requested, only the actual api dictionaries will be returned of coordinator data
            if from_cache:
                _LOGGER.info(
                    "Api Coordinator %s is updating data from api dictionaries",self.api.nickname,
                ) # TODO(RELEASE): Disable after testing
            else:
                _LOGGER.info(
                    "Api Coordinator %s is updating sites %s",self.api.nickname, f"from folder {self.api.testDir()}" if self._testmode else ""
                )  # TODO(RELEASE): Disable after testing
                await self.api.update_sites(fromFile=self._testmode)
                # update device details only after given refresh interval count
                self._intervalcount -= 1
                if self._intervalcount <= 0:
                    _LOGGER.info(
                        "Api Coordinator %s is updating devices %s",self.api.nickname, f"from folder {self.api.testDir()}" if self._testmode else ""
                    )  # TODO(RELEASE): Disable after testing
                    await self.api.update_device_details(fromFile=self._testmode)
                    self._intervalcount = self._deviceintervals
            # combine site and device details dict
            data = self.api.sites | self.api.devices

            _LOGGER.debug("Coordinator data: %s", data)
            return data
        except asyncio.TimeoutError as exception:
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
                f"Api Request Error: {exception}"
            ) from exception

    def testmode(self, mode: bool = None) -> bool:
        """Query or set testmode for client."""
        if mode is None:
            return self._testmode
        if self._testmode != mode:
            _LOGGER.info(
                "Api Coordinator testmode was changed to %s",
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
                "Api Coordinator device refresh multiplier was changed to %s", intervals
            )
            self._deviceintervals = intervals
            self._intervalcount = min(intervals,self._intervalcount)
        return self._deviceintervals
