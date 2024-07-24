"""Anker Power/Solix Cloud API class request related methods."""

from asyncio import sleep
import contextlib
from datetime import datetime
import json
import os
import time as systime

import aiofiles
from aiohttp.client_exceptions import ClientError
from cryptography.hazmat.primitives import serialization

from . import errors
from .types import API_HEADERS, API_LOGIN, SolixDefaults


def requestDelay(self, delay: float | None = None) -> float:
    """Get or set the api request delay in seconds."""
    if (
        delay is not None
        and isinstance(delay, float | int)
        and float(delay) != float(self._request_delay)
    ):
        self._request_delay = float(
            min(
                SolixDefaults.REQUEST_DELAY_MAX,
                max(SolixDefaults.REQUEST_DELAY_MIN, delay),
            )
        )
        self._logger.info(
            "Set api request delay to %.3f seconds", self._request_delay
        )
    return self._request_delay

async def _wait_delay(self, delay: float | None = None) -> None:
    """Wait at least for the defined Api request delay or for the provided delay in seconds since the last request occured."""
    if delay is not None and isinstance(delay, float | int):
        delay = float(
            min(
                SolixDefaults.REQUEST_DELAY_MAX,
                max(SolixDefaults.REQUEST_DELAY_MIN, delay),
            )
        )
    else:
        delay = self._request_delay
    if isinstance(self._last_request_time, datetime):
        await sleep(
            max(
                0,
                delay - (datetime.now() - self._last_request_time).total_seconds(),
            )
        )

async def async_authenticate(self, restart: bool = False) -> bool:
    """Authenticate with server and get an access token. If restart is not enforced, cached login data may be used to obtain previous token."""
    if restart:
        self._token = None
        self._token_expiration = None
        self._gtoken = None
        self._loggedIn = False
        self._authFileTime = 0
        self.nickname = ""
        if os.path.isfile(self._authFile):
            with contextlib.suppress(Exception):
                os.remove(self._authFile)
    # First check if cached login response is availble and login params can be filled, otherwise query server for new login tokens
    if os.path.isfile(self._authFile):
        data = await self._loadFromFile(self._authFile)
        self._authFileTime = os.path.getmtime(self._authFile)
        self._logger.debug(
            "Cached Login for %s from %s:",
            self.mask_values(self._email),
            datetime.fromtimestamp(self._authFileTime).isoformat(),
        )
        self._logger.debug(
            "%s",
            self.mask_values(data, "user_id", "auth_token", "email", "geo_key"),
        )
        # clear retry attempt to allow retry for authentication refresh
        self._retry_attempt = False
    else:
        self._logger.debug("Fetching new Login credentials from server")
        now = datetime.now().astimezone()
        # set retry attempt to avoid retry on failed authentication
        self._retry_attempt = True
        auth_resp = await self.request(
            "post",
            API_LOGIN,
            json={
                "ab": self._countryId,
                "client_secret_info": {
                    "public_key": self._public_key.public_bytes(
                        serialization.Encoding.X962,
                        serialization.PublicFormat.UncompressedPoint,
                    ).hex()  # Uncompressed format of points in hex (0x04 + 32 Byte + 32 Byte)
                },
                "enc": 0,
                "email": self._email,
                "password": self._encryptApiData(
                    self._password
                ),  # AES-256-CBC encrypted by the ECDH shared key derived from server public key and local private key
                "time_zone": round(
                    datetime.utcoffset(now).total_seconds() * 1000
                ),  # timezone offset in ms, e.g. 'GMT+01:00' => 3600000
                "transaction": str(
                    int(systime.mktime(now.timetuple()) * 1000)
                ),  # Unix Timestamp in ms as string
            },
        )
        data = auth_resp.get("data", {})
        self._logger.debug(
            "Login Response: %s",
            self.mask_values(data, "user_id", "auth_token", "email", "geo_key"),
        )
        self._loggedIn = True
        # Cache login response in file for reuse
        async with aiofiles.open(self._authFile, "w", encoding="utf-8") as authfile:
            await authfile.write(json.dumps(data, indent=2, skipkeys=True))
            self._logger.debug("Response cached in file: %s", self._authFile)
            self._authFileTime = os.path.getmtime(self._authFile)

    # Update the login params
    self._login_response = {}
    self._login_response.update(data)
    self._token = data.get("auth_token")
    self.nickname = data.get("nick_name")
    if data.get("token_expires_at"):
        self._token_expiration = datetime.fromtimestamp(
            data.get("token_expires_at")
        )
    else:
        self._token_expiration = None
        self._loggedIn = False
    if data.get("user_id"):
        self._gtoken = self._md5(
            data.get("user_id")
        )  # gtoken is MD5 hash of user_id from login response
    else:
        self._gtoken = None
        self._loggedIn = False
    return self._loggedIn

async def request(
    self,
    method: str,
    endpoint: str,
    *,
    headers: dict | None = None,
    json: dict | None = None,  # pylint: disable=redefined-outer-name
) -> dict:
    """Handle all requests to the API. This is also called recursively by login requests if necessary."""
    if not headers:
        headers = {}
    if not json:
        data = {}
    if (
        self._token_expiration
        and (self._token_expiration - datetime.now()).total_seconds() < 60
    ):
        self._logger.warning("WARNING: Access token expired, fetching a new one")
        await self.async_authenticate(restart=True)
    # For non-Login requests, ensure authentication will be updated if not logged in yet or cached file was refreshed
    if endpoint != API_LOGIN and (
        not self._loggedIn
        or (
            os.path.isfile(self._authFile)
            and self._authFileTime != os.path.getmtime(self._authFile)
        )
    ):
        await self.async_authenticate()

    url: str = f"{self._api_base}/{endpoint}"
    mergedHeaders = API_HEADERS
    mergedHeaders.update(headers)
    if self._countryId:
        mergedHeaders.update({"Country": self._countryId})
    if self._timezone:
        mergedHeaders.update({"Timezone": self._timezone})
    if self._token:
        mergedHeaders.update({"x-auth-token": self._token})
        mergedHeaders.update({"gtoken": self._gtoken})
    if self.encrypt_body:
        # TODO(#70): Test and Support optional encryption for body
        # Unknowns: Which string is signed? Method + Request?
        # How does the signing work?
        # What is the key-ident? Ident of the shared secret?
        # What is request-once?
        # Is the separate timestamp relevant for encryption?
        pass
        # Extra Api header arguments used by the mobile App for request encryption
        # Response will return encrypted body and a signature field
        # mergedHeaders.update({
        #     "x-replay-info": "replay",
        #     "x-encryption-info": "algo_ecdh",
        #     "x-signature": "",  # 32 Bit hex
        #     "x-request-once": "",  # 16 Bit hex
        #     "x-key-ident": "",  # 16 Bit hex
        #     "x-request-ts": str(
        #         int(systime.mktime(datetime.now().timetuple()) * 1000)
        #     ),  # Unix Timestamp in ms as string
        # })

    self._logger.debug("Request Url: %s %s", method.upper(), url)
    self._logger.debug(
        "Request Headers: %s",
        self.mask_values(mergedHeaders, "x-auth-token", "gtoken"),
    )
    if endpoint == API_LOGIN:
        self._logger.debug(
            "Request Body: %s",
            self.mask_values(json, "user_id", "auth_token", "email", "geo_key"),
        )
    else:
        self._logger.debug("Request Body: %s", json)
    body_text = ""
    # enforce configured delay between any subsequent request
    await self._wait_delay()
    async with self._session.request(
        method, url, headers=mergedHeaders, json=json
    ) as resp:
        try:
            self._last_request_time = datetime.now()
            self.request_count.add(self._last_request_time)
            self._logger.debug(
                "%s request %s %s response received", self.nickname, method, url
            )
            # print response headers
            self._logger.debug("Response Headers: %s", resp.headers)
            # get first the body text for usage in error detail logging if necessary
            body_text = await resp.text()
            data = {}
            resp.raise_for_status()  # any response status >= 400
            if (data := await resp.json(content_type=None)) and self.encrypt_body:
                # TODO(#70): Test and Support optional encryption for body
                # data dict has to be decoded when encrypted
                # if signature := data.get("signature"):
                #     pass
                pass
            if not data:
                self._logger.error("Response Text: %s", body_text)
                raise ClientError(f"No data response while requesting {endpoint}")

            if endpoint == API_LOGIN:
                self._logger.debug(
                    "Response Data: %s",
                    self.mask_values(
                        data, "user_id", "auth_token", "email", "geo_key"
                    ),
                )
            else:
                self._logger.debug("Response Data: %s", data)
                # reset retry flag only when valid token received and not another login request
                self._retry_attempt = False

            # check the Api response status code in the data
            errors.raise_error(data)

            # valid response at this point, mark login and return data
            self._loggedIn = True
            return data  # noqa: TRY300

        # Exception from ClientSession based on standard response status codes
        except ClientError as err:
            self._logger.error("Api Request Error: %s", err)
            self._logger.error("Response Text: %s", body_text)
            # Prepare data dict for Api error lookup
            if not data:
                data = {}
            if not hasattr(data, "code"):
                data["code"] = resp.status
            if not hasattr(data, "msg"):
                data["msg"] = body_text
            if resp.status in [401, 403]:
                # Unauthorized or forbidden request
                # reattempt autentication with same credentials if cached token was kicked out
                # retry attempt is set if login response data were not cached to fail immediately
                if not self._retry_attempt:
                    self._logger.warning("Login failed, retrying authentication")
                    if await self.async_authenticate(restart=True):
                        return await self.request(
                            method, endpoint, headers=headers, json=json
                        )
                    self._logger.error("Re-Login failed for user %s", self._email)
                errors.raise_error(
                    data, prefix=f"Login failed for user {self._email}"
                )
                # catch error if Api code not defined
                raise errors.AuthorizationError(
                    f"Login failed for user {self._email}"
                ) from err
            if resp.status in [429]:
                # Too Many Requests, add stats to message
                errors.raise_error(
                    data, prefix=f"Too Many Requests: {self.request_count}"
                )
            else:
                # raise Anker Solix error if code is known
                errors.raise_error(data)
            # raise Client error otherwise
            raise ClientError(
                f"Api Request Error: {err}", f"response={body_text}"
            ) from err
        except errors.AnkerSolixError as err:  # Other Exception from API
            self._logger.error("%s", err)
            self._logger.error("Response Text: %s", body_text)
            raise

