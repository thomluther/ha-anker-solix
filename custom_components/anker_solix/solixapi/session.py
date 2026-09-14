"""Anker Power/Solix Cloud API class to handle a client connection session for an account."""

from asyncio import sleep
from base64 import b64decode, b64encode
import contextlib
from datetime import datetime

# TODO(COMPRESSION): from gzip import compress, decompress
import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
from random import randbytes, randrange
import tempfile
from types import SimpleNamespace
from typing import Any

import aiofiles
import aiofiles.os
from aiohttp import ClientSession, ClientTimeout
from aiohttp.client_exceptions import ClientError
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from . import errors
from .apitypes import (
    API_COUNTRIES,
    API_ENDPOINTS,
    API_HEADERS,
    API_KEY_EXCHANGE,
    API_LOGIN,
    API_PRESET_KEYS,
    API_SERVERS,
    SolixDefaults,
)
from .helpers import RequestCounter, generateTimestamp, getTimezoneGMTString, md5

_LOGGER: logging.Logger = logging.getLogger(__name__)
_MASK_VALUES = [
    "user_id",
    "auth_token",
    "email",
    "geo_key",
    "ap_cloud_user_id",
    "phone",
]


class AnkerSolixClientSession:
    """Define the class to handle a client for Anker server authentication and API requests."""

    # Public key of Anker Api servers
    _api_public_key_hex = "04c5c00c4f8d1197cc7c3167c52bf7acb054d722f0ef08dcd7e0883236e0d72a3868d9750cb47fa4619248f3d83f0f662671dadc6e2d31c2f41db0161651c7c076"

    def __init__(
        self,
        email: str,
        password: str,
        countryId: str,
        websession: ClientSession,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize."""
        self._countryId: str = countryId.upper()
        self._api_base: str | None = None
        self._region: str | None = None
        for region, countries in API_COUNTRIES.items():
            if self._countryId in countries:
                self._api_base = API_SERVERS.get(region)
                self._region = region
        # default to EU server
        if not self._api_base:
            self._api_base = API_SERVERS.get("eu")
            self._region = self._region or "eu"
        self._email: str = email
        self._password: str = password
        self._session: ClientSession = websession
        self._loggedIn: bool = False
        self._testdir: str = str(
            (Path(__file__).parent / ".." / "examples" / "example1").resolve()
        )

        # Flag for retry of any or certain error
        self._retry_attempt: bool | int = False

        # ensure folder for authentication caching exists
        auth_cache_dir = Path(__file__).parent / "authcache"
        if not os.access(auth_cache_dir.parent, os.W_OK):
            auth_cache_dir = Path(tempfile.gettempdir()) / "authcache"
        auth_cache_dir.mkdir(parents=True, exist_ok=True)

        # filename for authentication cache
        self._authFile: str = str(auth_cache_dir / f"{email}.json")
        self._authFileTime: float = 0

        # Timezone format: 'GMT+01:00'
        self._timezone: str = getTimezoneGMTString()
        self._gtoken: str | None = None
        self._token: str | None = None
        self._token_expiration: datetime | None = None
        self._login_response: dict = {}
        self._request_delay: float = SolixDefaults.REQUEST_DELAY_DEF
        self._request_timeout: int = SolixDefaults.REQUEST_TIMEOUT_DEF
        self._last_request_time: datetime | None = None
        # define limit of same endpoint requests per minute
        self._endpoint_limit: int = SolixDefaults.ENDPOINT_LIMIT_DEF

        # Define authentication Encryption for password, using ECDH asymmetric key exchange for shared secret calculation, which must be used to encrypt the password using AES-256-CBC with seed of 16
        # uncompressed public key from EU Anker server in the format 04 [32 byte x value] [32 byte y value]
        # Both, the EU and COM Anker server public key is the same and login response is provided for both upon an authentication request
        # However, if country ID assignment is to wrong server, no sites or devices will be listed for the authenticated account.

        # Create ECDH key pair using NIST P-256 curve SECP256R1 (identical to prime256v1)
        # get EllipticCurvePrivateKey
        self._private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
        # get EllipticCurvePublicKey
        self._public_key = self._private_key.public_key()
        # get bytes of shared secret
        self._shared_key = self._private_key.exchange(
            ec.ECDH(),
            ec.EllipticCurvePublicKey.from_encoded_point(
                ec.SECP256R1(), bytes.fromhex(self._api_public_key_hex)
            ),
        )

        # initialize logger for class
        if logger:
            self._logger = logger
        else:
            self._logger = _LOGGER
            self._logger.setLevel(logging.WARNING)
        if not self._logger.hasHandlers():
            self._logger.addHandler(logging.StreamHandler())

        # reset class variables
        self.nickname: str = ""
        self.mask_credentials: bool = True
        self.request_count: RequestCounter = RequestCounter()
        # Flag whether compression should be used (Actually not supported by Anker Power servers)
        self.compress_data: bool = False
        # handler for encryption
        self.encrypt_payload: bool = False
        self._eh: AnkerEncryptionHandler | None = None

    @property
    def email(self) -> str:
        """Get the email used for the active session."""
        return self._email

    @property
    def countryId(self) -> str:
        """Get the country ID used for the active session."""
        return self._countryId

    @property
    def region(self) -> str:
        """Get the region used for the active session."""
        return self._region

    @property
    def server(self) -> str | None:
        """Get the server used for the active session."""
        return self._api_base

    @property
    def session(self) -> ClientSession:
        """Get the active client session."""
        return self._session

    def logger(self, logger: logging.Logger | None = None) -> logging.Logger:
        """Get or set the logger for API client."""
        if logger:
            self._logger = logger
        return self._logger

    def testDir(self, subfolder: str | None = None) -> str:
        """Get or set the subfolder for local API test files."""
        if not subfolder or str(subfolder) == self._testdir:
            return self._testdir
        if not Path(subfolder).is_dir():
            self._logger.error(
                "Specified test folder for api %s does not exist: %s",
                self.nickname,
                subfolder,
            )
        else:
            self._testdir = str(subfolder)
            self._logger.info(
                "Set api %s test folder to: %s", self.nickname, self._testdir
            )
        return self._testdir

    def logLevel(self, level: int | None = None) -> int:
        """Get or set the logger log level."""
        if level is not None and isinstance(level, int):
            self._logger.setLevel(level)
            self._logger.info("Set api %s log level to: %s", self.nickname, level)
        return self._logger.getEffectiveLevel()

    def payloadEncryption(self, enable: bool | None = None) -> bool:
        """Get or set the Api payload encryption flag."""
        if enable is not None and isinstance(enable, bool):
            self.encrypt_payload = enable
            self._logger.info(
                "Set api %s payload encryption to: %s", self.nickname, enable
            )
        return self.encrypt_payload

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
                "Set api %s request delay to %.3f seconds",
                self.nickname,
                self._request_delay,
            )
        return self._request_delay

    def requestTimeout(self, seconds: int | None = None) -> int:
        """Get or set the api request timeout in seconds."""
        if (
            seconds is not None
            and isinstance(seconds, float | int)
            and round(seconds) != self._request_timeout
        ):
            self._request_timeout = round(
                min(
                    SolixDefaults.REQUEST_TIMEOUT_MAX,
                    max(SolixDefaults.REQUEST_TIMEOUT_MIN, seconds),
                )
            )
            self._logger.info(
                "Set api %s request timeout to %s seconds",
                self.nickname,
                str(self._request_timeout),
            )
        return self._request_timeout

    def endpointLimit(self, limit: int | None = None) -> int:
        """Get or set the api request limit per endpoint per minute."""
        if (
            limit is not None
            and isinstance(limit, float | int)
            and int(limit) != int(self._endpoint_limit)
        ):
            self._endpoint_limit = int(max(0, limit))
            if self._endpoint_limit:
                self._logger.info(
                    "Set api %s request limit to %s requests per endpoint per minute",
                    self.nickname,
                    self._endpoint_limit,
                )
            else:
                self._logger.info(
                    "Disabled api %s request limit and cleared %s throttled endpoints",
                    self.nickname,
                    len(self.request_count.throttled),
                )
                self.request_count.throttled.clear()
        return self._endpoint_limit

    def generate_header(self) -> dict:
        """Generate common header fields for Api requests."""
        # Start with fixed header fields
        header = API_HEADERS.copy()
        # {"content-type": "application/json",
        # "model-type": "DESKTOP",
        # "app-name": "anker_power",
        # "os-type": "android"}
        if self._countryId:
            header.update({"country": self._countryId})
        if self._timezone:
            header.update({"timezone": self._timezone})
        if self._token:
            header.update({"gtoken": self._gtoken, "x-auth-token": self._token})
        if self.compress_data:
            header.update(
                {
                    "accept-encoding": "gzip",
                    # TODO(COMPRESSION): only response encoding seems to be accepted by servers
                    # "content-type": "text/plain",
                    # "content-encoding": "gzip",
                }
            )
        return header

    async def _wait_delay(
        self, delay: float | None = None, endpoint: str | None = None
    ) -> None:
        """Wait at least for the defined Api request delay or for the provided delay in seconds since the last request occurred.

        If the endpoint is provided and a request limit is defined, the request will be throttled to avoid exceeding endpoint limit per minute.
        """
        if delay is not None and isinstance(delay, float | int):
            delay = float(
                min(
                    SolixDefaults.REQUEST_DELAY_MAX,
                    max(SolixDefaults.REQUEST_DELAY_MIN, delay),
                )
            )
        else:
            delay = self._request_delay
        # throttle requests to same endpoint
        throttle = 0
        if (
            endpoint
            and delay == self._request_delay
            and self._endpoint_limit
            and endpoint in self.request_count.throttled
        ):
            same_requests = [
                i
                for i in self.request_count.last_minute(details=True)
                if endpoint in i[1]
            ]
            # delay at least 1 minute from oldest request
            throttle = (
                65 - (datetime.now().astimezone() - same_requests[0][0]).total_seconds()
                if len(same_requests) >= self._endpoint_limit
                else 0
            )
            if throttle:
                self._logger.warning(
                    "Throttling next request of api %s for %.1f seconds to maintain request limit of %s for endpoint %s",
                    self.nickname,
                    throttle,
                    self._endpoint_limit,
                    endpoint,
                )
        await sleep(
            max(
                0,
                throttle,
                delay
                - (
                    datetime.now().astimezone() - self._last_request_time
                ).total_seconds()
                if isinstance(self._last_request_time, datetime)
                else 0,
            )
        )

    async def async_authenticate(self, restart: bool = False) -> bool:
        """Authenticate with server and get an access token. If restart is not enforced, cached login data may be used to obtain previous token."""
        if restart:
            self._token = None
            self._token_expiration = None
            self._gtoken = None
            self._loggedIn = False
            self._login_response = {}
            self._eh = None
            self._authFileTime = 0
            self.nickname = ""
            # remove auth file if existing
            if Path(self._authFile).is_file():
                with contextlib.suppress(Exception):
                    Path(self._authFile).unlink()
        # First check if cached login response is available and login params can be filled, otherwise query server for new login tokens
        if Path(self._authFile).is_file():
            data = await self.loadFromFile(self._authFile)
            self._authFileTime = Path(self._authFile).stat().st_mtime
            self._logger.debug(
                "Cached Login for %s from %s:",
                self.mask_values(self._email),
                datetime.fromtimestamp(self._authFileTime).astimezone().isoformat(),
            )
            self._logger.debug(
                "%s",
                self.mask_values(data, *_MASK_VALUES),
            )
            # clear retry attempt to allow retry for authentication refresh
            if isinstance(self._retry_attempt, bool):
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
                        # client public_key is uncompressed format of points in hex (0x04 + 32 Byte + 32 Byte)
                        "public_key": self._rawPublicKey()
                    },
                    "enc": 0,
                    "email": self._email,
                    # password is AES-256-CBC encrypted by the ECDH shared key derived from server public key and local private key
                    "password": self._encryptApiData(self._password),
                    # time_zone is offset in ms, e.g. 'GMT+01:00' => 3600000
                    "time_zone": round(datetime.utcoffset(now).total_seconds() * 1000),
                    # transaction is Unix Timestamp in ms as string
                    "transaction": generateTimestamp(in_ms=True),
                },
            )
            data = auth_resp.get("data", {})
            self._logger.debug(
                "Login Response: %s",
                self.mask_values(
                    data,
                    *_MASK_VALUES,
                ),
            )
            self._loggedIn = True
            # Cache login response in file for reuse
            async with aiofiles.open(self._authFile, "w", encoding="utf-8") as authfile:
                await authfile.write(json.dumps(data, indent=2, skipkeys=True))
                self._logger.debug("Response cached in file: %s", self._authFile)
                self._authFileTime = Path(self._authFile).stat().st_mtime

        # Update the login params
        self._login_response = dict(data)
        self._token = data.get("auth_token")
        self.nickname = data.get("nick_name") or ""
        if data.get("token_expires_at"):
            self._token_expiration = datetime.fromtimestamp(
                data.get("token_expires_at")
            ).astimezone()
        else:
            self._token_expiration = None
            self._loggedIn = False
            self._eh = None
        if data.get("user_id"):
            # gtoken is MD5 hash of user_id from login response
            self._gtoken = md5(data.get("user_id"))
            # reset retry flag upon valid authentication response for normal request retry attempts
            if isinstance(self._retry_attempt, bool):
                self._retry_attempt = False
        else:
            self._gtoken = None
            self._loggedIn = False
            self._eh = None
        return self._loggedIn

    async def request(  # noqa: C901
        self,
        method: str,
        endpoint: str,
        *,
        headers: dict | None = None,
        json: dict | None = None,  # pylint: disable=redefined-outer-name
    ) -> dict:
        """Handle all requests to the API. This is also called recursively by login requests if necessary."""
        if not isinstance(headers, dict):
            headers = {}
        if not isinstance(json, dict):
            json = {}
        # check token expiration (7 days)
        if (
            self._token_expiration
            and (self._token_expiration - datetime.now().astimezone()).total_seconds()
            < 60
        ):
            self._logger.warning(
                "WARNING: Access token expired, fetching a new one%s",
                (" for " + str(self.nickname)) if self.nickname else "",
            )
            await self.async_authenticate(restart=True)
        # For non-Login requests, ensure authentication will be updated if not logged in yet or cached file was refreshed
        if endpoint != API_LOGIN and (
            not self._loggedIn
            or (
                Path(self._authFile).is_file()
                and self._authFileTime != Path(self._authFile).stat().st_mtime
            )
        ):
            await self.async_authenticate()

        url: str = f"{self._api_base}/{endpoint}"
        # use required headers and merge provided/optional headers
        merged_headers = self.generate_header()
        merged_headers.update(headers)
        # base64 ciphertext to send as the request body when payload encryption is on
        encrypted_body: str | None = None
        if self.encrypt_payload and self._login_response:
            if not self._eh and self._token:
                # initialize the encryption handler
                self._eh = AnkerEncryptionHandler(client=self)
            if not self._eh.shared_secret:
                # Perform key exchange for encryption handler to get the shared secret for the session
                await self._eh.perform_key_exchange(
                    api_base=self._api_base, headers=merged_headers
                )

            # App Example request with encrypted payload
            #   curl --request POST \
            #     --url https://ankerpower-api-eu.anker.com/power_service/v1/app/device/get_device_attrs \
            #     --compressed \
            #     --header 'accept-encoding: gzip' \
            #     --header 'app-name: anker_power' \
            #     --header 'app-version: 3.6.0' \
            #     --header 'content-type: text/plain' \
            #     --header 'gtoken: GTOKEN' \
            #     --header 'host: ankerpower-api-eu.anker.com' \
            #     --header 'language: en' \
            #     --header 'x-app-key: ' \
            #     --header 'x-auth-token: TOKEN' \
            #     --header 'x-encryption-info: algo_ecdh' \
            #     --header 'x-replay-info: replay' \
            #     --header 'x-key-ident: 487c4d59721f02c22112c46c1ea038bf' \
            #     --header 'x-request-once: cba657a9e6b9da45d89658b6a281ff97' \
            #     --header 'x-request-ts: 1745103679' \
            #     --header 'x-signature: d93f441a9951cc4f4069f13d21248764619e42336315dcc93022f93fddcc7cbb' \
            #     --data 'MTc0NTEwMzY3OTIyMjAwMIUJ7p7z1Zk4ra+8lqNwWY8l//5+uEyzztV+MglhAvvv3/xuqxYyn9heRVIRHje482N8BuZEVklJEnernTGFyEY='
            # App Example response with encrypted payload
            #     {"signature": "98444e7105fbdc29a4e969d8b24d6e757ea9c495c6c8158cefbecdaf2cbf72b0",
            #     "msg": "success!",
            #     "code": 0,
            #     "trace_id": "9d0bd9c0a328bcfde9e60f5a33284977",
            #     "data": "ybF4Sg9vCKt3V75DnvTddszD0m6qJH4ZhjcN4DQC2RMlvqCthrJ1qK4DLvJ7l8jwYYbMooaE2QXmtfGebt8d1wfzCnl3XqLhpM8dxXX7ghw="}

            # Mandatory extra api header arguments for encrypted requests
            #     'x-app-key': '' # empty is fine
            #     'x-encryption-info': 'algo_ecdh'
            #     'x-replay-info': 'replay'
            #     'x-key-ident': the key pair id, 32 hex chars, constant per session
            #     'x-request-once': a fresh random nonce, 32 hex chars, per request
            #     'x-request-ts': [request timestamp] # Unix Timestamp in s as string
            #     'x-signature': HMAC-SHA256(presetKey_hex, ts+once+encrypted_body)
            # The body goes on the wire as text/plain base64 ciphertext, and the
            # response returns an encrypted "data" field alongside a "signature".
            timestamp = generateTimestamp()
            encrypted_body = self._eh.encrypt_body(json)
            merged_headers.update(
                self._eh.generate_x_header(
                    timestamp=timestamp, encrypted_body_b64=encrypted_body
                )
                | {
                    "content-type": "text/plain",
                }
            )

        self._logger.debug("Request Url: %s %s", method.upper(), url)
        self._logger.debug(
            "Request Headers: %s",
            self.mask_values(merged_headers, "x-auth-token", "gtoken"),
        )
        if endpoint in [
            API_LOGIN,
            API_KEY_EXCHANGE,
            API_ENDPOINTS["get_token_by_userid"],
            API_ENDPOINTS["get_shelly_status"],
        ]:
            body_text = str(
                self.mask_values(
                    json,
                    *_MASK_VALUES,
                    "token",
                    "password",
                )
            )
        else:
            body_text = str(json)
        self._logger.debug("Request Body: %s", body_text)
        # enforce configured delay between any subsequent request
        await self._wait_delay(endpoint=endpoint)
        # uncompressed body must use json parameter, pre-compressed body must use data parameter
        data = {}
        # predefine response to handle TimeoutError like 522 timeouts from server
        resp = SimpleNamespace(status=0)
        try:
            # make the request, auto_decompression of body enabled by default
            async with self._session.request(
                method,
                url,
                headers=merged_headers,
                # encrypted requests send base64 ciphertext as text/plain via data,
                # plain requests let aiohttp serialize the dict via json
                json=json if encrypted_body is None else None,
                data=encrypted_body,
                # TODO(COMPRESSION): only response encoding seems to be accepted by servers
                # json=None if self.compress_data else json,
                # data=compress(str(json).encode()) if self.compress_data else None,
                timeout=ClientTimeout(total=self._request_timeout),
            ) as resp:
                self._last_request_time = datetime.now().astimezone()
                self.request_count.add(
                    request_time=self._last_request_time,
                    request_info=(f"{method.upper()} {url} {body_text}").strip(),
                )
                # request handler has auto-decompression enabled
                self._logger.debug(
                    "Api %s response received for request: %s %s",
                    self.nickname,
                    method,
                    url,
                )
                # print response headers
                self._logger.debug("Response Headers: %s", resp.headers)
                # first get the body text for usage in error detail logging if necessary
                body_text = await resp.text()
                resp.raise_for_status()  # any response status >= 400
                # get json data without strict checking for json content
                data = await resp.json(content_type=None)
                if not data:
                    self._logger.error(
                        "Api %s no data response for request: %s %s\nResponse Text: %s",
                        self.nickname,
                        method.upper(),
                        url,
                        body_text,
                    )
                    raise ClientError(  # noqa: TRY301
                        f"Api {self.nickname} no data response for request: {method.upper()} {url}"
                    )
                if endpoint == API_LOGIN:
                    self._logger.debug(
                        "Response Data: %s",
                        self.mask_values(
                            data,
                            *_MASK_VALUES,
                        ),
                    )
                else:
                    self._logger.debug("Response Data: %s", data)

                # valid client response at this point, mark login to avoid repeated authentication
                self._loggedIn = True
                # check the Api response status code in the data
                errors.raise_error(data)

                # reset retry flag for normal request retry attempts
                self._retry_attempt = False

                # data field has to be decoded when encrypted and signature field found in response
                if self.encrypt_payload and data.get("signature"):
                    data["data"] = self._eh.decryptApiData(data.get("data"))
                    self._logger.debug("Decrypted Data: %s", data["data"])
                return data

        # Exception from ClientSession based on standard response status codes
        except (ClientError, TimeoutError) as err:
            if isinstance(err, TimeoutError):
                resp.status = 522
                body_text = "Timeout Error"
            # Prepare data dict for Api error lookup
            if not data:
                data = {}
            if not hasattr(data, "code"):
                data["code"] = resp.status
            if not hasattr(data, "msg"):
                data["msg"] = body_text
            if resp.status in [401, 403]:
                # Unauthorized or forbidden request
                self._logger.error(
                    "Api %s Error %s for request: %s %s\nResponse Text: %s",
                    self.nickname,
                    err,
                    method.upper(),
                    url,
                    body_text,
                )
                # reattempt authentication with same credentials if cached token was kicked out
                # retry attempt is set if login response data were not cached to fail immediately
                if not self._retry_attempt:
                    self._logger.warning(
                        "Invalid Login, retrying authentication%s",
                        (" for " + str(self.nickname)) if self.nickname else "",
                    )
                    if await self.async_authenticate(restart=True):
                        return await self.request(
                            method, endpoint, headers=headers, json=json
                        )
                    self._logger.error("Login failed for user %s", self._email)
                errors.raise_error(data, prefix=f"Login failed for user {self._email}")
                # catch error if Api code not defined
                raise errors.AuthorizationError(
                    f"Login failed for user {self._email}"
                ) from err
            if resp.status == 429:
                # Too Many Requests for endpoint, repeat once after throttle delay and add endpoint to throttle
                if self._retry_attempt not in [True, 429] and self._endpoint_limit:
                    self._retry_attempt = resp.status
                    self.request_count.add_throttle(endpoint=endpoint)
                    self._logger.warning(
                        "Api %s exceeded request limit with %s known requests in last minute, throttle will be enabled for endpoint: %s",
                        self.nickname,
                        len(
                            [
                                i
                                for i in self.request_count.last_minute(details=True)
                                if endpoint in i[1]
                            ]
                        ),
                        endpoint,
                    )
                    return await self.request(
                        method, endpoint, headers=headers, json=json
                    )
                # Raise error if retry failed too, add stats to message
                self._logger.error(
                    "Api %s Error %s for request: %s %s\nResponse Text: %s",
                    self.nickname,
                    err,
                    method.upper(),
                    url,
                    body_text,
                )
                errors.raise_error(
                    data,
                    prefix=f"Api {self.nickname} Too Many Requests: {self.request_count}",
                )
            elif resp.status in [502, 504, 522]:
                # Server may be temporarily overloaded and does not respond
                # 502 is Gateway error
                # 504 is Gateway timeout error
                # 522 is Server timeout error
                if self._retry_attempt not in [True, 502, 504, 522]:
                    self._retry_attempt = resp.status
                    delay = randrange(2, 6)  # random wait time 2-5 seconds
                    self._logger.info(
                        "Http error '%s', retrying request of api %s after delay of %s seconds for endpoint: %s",
                        "Timeout Error"
                        if isinstance(err, TimeoutError)
                        else resp.status,
                        self.nickname,
                        delay,
                        endpoint,
                    )
                    await self._wait_delay(delay=delay)
                    return await self.request(
                        method, endpoint, headers=headers, json=json
                    )
            self._logger.error(
                "Api %s Error %s for request: %s %s\nResponse Text: %s",
                self.nickname,
                err,
                method.upper(),
                url,
                body_text,
            )
            # raise Anker Solix error if code is known
            errors.raise_error(data)
            # raise Client error otherwise
            raise ClientError(
                f"Api {self.nickname} Request Error: {str(err) or 'Timeout'}, response={body_text}"
            ) from err
        except errors.AnkerSolixError as err:  # Other Exception from API
            if isinstance(err, errors.BusyError):
                # Api fails to respond to standard query, repeat once after delay
                self._logger.error(
                    "Api %s Busy Error %s for request: %s %s\nResponse Text: %s",
                    self.nickname,
                    err,
                    method.upper(),
                    url,
                    body_text,
                )
                if self._retry_attempt not in [True, 21105]:
                    self._retry_attempt = 21105
                    delay = randrange(2, 6)  # random wait time 2-5 seconds
                    self._logger.warning(
                        "Server busy, retrying request of api %s after delay of %s seconds for endpoint %s",
                        self.nickname,
                        delay,
                        endpoint,
                    )
                    await self._wait_delay(delay=delay)
                    return await self.request(
                        method, endpoint, headers=headers, json=json
                    )
            self._logger.error(
                "Api %s Error %s for request: %s %s\nResponse Text: %s",
                self.nickname,
                err,
                method.upper(),
                url,
                body_text,
            )
            raise

    def _rawPublicKey(self) -> bytes:
        """Generate raw client public_key in uncompressed format of points in hex (0x04 + 32 Byte + 32 Byte)."""
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint,
        ).hex()

    def _encryptApiData(self, raw_data: str) -> str:
        """Return Base64 encoded secret as utf-8 encoded string using the shared secret with seed of 16 for the encryption."""
        # Password must be UTF-8 encoded and AES-256-CBC encrypted with block size of 16
        # Create AES cipher
        cipher = Cipher(
            algorithms.AES(self._shared_key),
            modes.CBC(self._shared_key[:16]),
            backend=default_backend(),
        )
        # Encrypt
        encryptor = cipher.encryptor()
        # Use default PKCS7 padding for incomplete AES blocks
        padder = padding.PKCS7(128).padder()
        raw_padded = padder.update(raw_data.encode()) + padder.finalize()
        return (b64encode(encryptor.update(raw_padded) + encryptor.finalize())).decode()

    def mask_values(self, data: dict | str, *args: str) -> dict | str:
        """Mask values in dictionary for provided keys or the given string."""
        if self.mask_credentials:
            if isinstance(data, str):
                datacopy: dict = {"text": data}
                args: list = ["text"]
            else:
                datacopy = data.copy()
            for key in args:
                if old := datacopy.get(key):
                    new = ""
                    for idx in range(0, len(old), 16):
                        new = new + (
                            f"{old[idx : idx + 2]}###masked###{old[idx + 14 : idx + 16]}"
                        )
                    new = new[: len(old)]
                    datacopy[key] = new
            if isinstance(data, str):
                return datacopy.get("text")
            return datacopy
        return data

    async def loadFromFile(self, filename: str | Path) -> dict:
        """Load json data from given file for testing."""
        filename = str(filename)
        if self.mask_credentials:
            masked_filename = filename.replace(
                self._email, self.mask_values(self._email)
            )
        else:
            masked_filename = filename
        try:
            if Path(filename).is_file():
                async with aiofiles.open(filename, encoding="utf-8") as file:
                    data = json.loads(await file.read() or "{}")
                    self._logger.debug("Loaded JSON from file %s:", masked_filename)
                    self._logger.debug(
                        "Data: %s",
                        self.mask_values(
                            data,
                            *_MASK_VALUES,
                        ),
                    )
                    self.request_count.add(request_info=f"LOAD {masked_filename}")
                    return data
        except OSError as err:
            self._logger.error(
                "ERROR: Failed to load JSON from file %s\n%s", masked_filename, err
            )
        return {}

    async def saveToFile(self, filename: str | Path, data: dict | None = None) -> bool:
        """Save json data to given file for testing."""
        filename = str(filename)
        if self.mask_credentials:
            masked_filename = filename.replace(
                self._email, self.mask_values(self._email)
            )
        else:
            masked_filename = filename
        if not data:
            data = {}
        try:
            async with aiofiles.open(filename, "w", encoding="utf-8") as file:
                await file.write(json.dumps(data, indent=2))
                self._logger.debug("Saved JSON to file %s:", masked_filename)
                return True
        except OSError as err:
            self._logger.error(
                "ERROR: Failed to save JSON to file %s\n%s", masked_filename, err
            )
            return False

    async def deleteModifiedFile(self, filename: str | Path) -> bool:
        """Delete given modified json file for testing."""
        filename = str(filename)
        if "modified" not in filename:
            return False
        if self.mask_credentials:
            masked_filename = filename.replace(
                self._email, self.mask_values(self._email)
            )
        else:
            masked_filename = filename
        try:
            await aiofiles.os.remove(masked_filename)
            self._logger.debug("Remove modified JSON file %s:", masked_filename)
        except OSError as err:
            self._logger.error(
                "ERROR: Failed to remove modified JSON file %s\n%s",
                masked_filename,
                err,
            )
            return False
        return True

    async def get_mqtt_info(self) -> dict:
        r"""Get the Anker MQTT server info with account certificates from session.

        Example data:
        {"user_id": "1541fc0a3db5a23e3c4ee27c6ed0616444e1ab8c","app_name": "anker_power","thing_name": "1541fc0a3db5a23e3c4ee27c6ed0616444e1ab8c-anker_power",
        "certificate_id": "36167916173028037311485710012973829433","certificate_pem": "-----BEGIN CERTIFICATE-----\n<base64Cert>\n-----END CERTIFICATE-----\n",
        "private_key": "-----BEGIN RSA PRIVATE KEY-----\n<base64Key>\n-----END RSA PRIVATE KEY-----\n","public_key": "",
        "endpoint_addr": "aiot-mqtt-eu.anker.com","aws_root_ca1_pem": "-----BEGIN CERTIFICATE-----\n<base64Cert>\n-----END CERTIFICATE-----",
        "origin": "","pkcs12": "<base64pkcs12Data>"}
        """
        return (await self.request("post", API_ENDPOINTS["get_mqtt_info"])).get(
            "data"
        ) or {}

    def get_login_info(self, key: str) -> Any | None:
        """Get a certain key from authenticated client login info."""
        return self._login_response.get(key)


class AnkerEncryptionHandler:
    """Anker Solix encryption handler class.

    Implements the app's ECDH payload encryption for the api and is confirmed working
    end to end against the live server: the key exchange, x-header composition, request
    signature, request body encryption and response decryption all round-trip. The
    handshake signs with the presetKey; every request after it signs and encrypts with
    the derived session key shared_secret[:16].
    """

    def __init__(
        self,
        client: AnkerSolixClientSession,
    ) -> None:
        """Initialize the encryption handler."""
        self._client = client
        # region presetKey (API_PRESET_KEYS) as hex string; the HMAC signature keys on
        # this ascii hex, while the AES envelope keys on its raw bytes - keep both forms.
        self._preset_key_hex = API_PRESET_KEYS.get(client.region)
        if not self._preset_key_hex:
            raise ClientError(
                f"No presetKey defined for region '{client.region}' (country '{client.get_login_info('country_code') or 'unknown'}'), payload encryption unavailable!"
            )
        self._preset_key = bytes.fromhex(self._preset_key_hex)
        # Create ECDH key pair for encryption key exchange using NIST P-256 curve
        self._private_key = ec.generate_private_key(ec.SECP256R1())
        self.public_key = self._private_key.public_key()
        # key_ident is a random id generated once per key pair and sent unchanged as
        # x-key-ident on every request; the server uses it to look up the shared secret.
        self.key_ident = os.urandom(16).hex()
        self.server_public_key = None
        self.shared_secret = None
        # initialize logger for class
        self._logger = self._client.logger()
        if not self._logger.hasHandlers():
            self._logger.addHandler(logging.StreamHandler())

    def _preset_encrypt(self, plaintext: bytes) -> str:
        """AES-128-CBC encrypt with the region presetKey, random IV prepended, base64.

        The 16-byte IV is generated per call and prepended to the ciphertext before
        base64 encoding, so the wrapped blob is iv(16) + ciphertext.
        """
        iv = randbytes(16)
        padder = padding.PKCS7(128).padder()
        padded = padder.update(plaintext) + padder.finalize()
        encryptor = Cipher(algorithms.AES(self._preset_key), modes.CBC(iv)).encryptor()
        return b64encode(iv + encryptor.update(padded) + encryptor.finalize()).decode()

    def _preset_decrypt(self, blob_b64: str) -> bytes:
        """Reverse of _preset_encrypt: strip the leading IV, AES-128-CBC decrypt, unpad."""
        blob = b64decode(blob_b64)
        iv, ciphertext = blob[:16], blob[16:]
        decryptor = Cipher(algorithms.AES(self._preset_key), modes.CBC(iv)).decryptor()
        padded = decryptor.update(ciphertext) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        return unpadder.update(padded) + unpadder.finalize()

    def _client_public_key_field(self) -> str:
        """Return the client public key for the key-exchange body.

        The uncompressed EC point (0x04 + X(32) + Y(32)) is taken as its 130-char
        ascii hex string, which is what gets wrapped with the region presetKey; the
        server unwraps it the same way.
        """
        raw_point = self.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint,
        )
        return self._preset_encrypt(raw_point.hex().encode())

    def generate_x_header(self, timestamp: str, encrypted_body_b64: str) -> dict:
        """Generate the encryption x-header fields for a request.

        Args:
            timestamp: unix seconds string, also sent as x-request-ts.
            encrypted_body_b64: the base64 body actually placed on the wire - for the
                key exchange this is the client_public_key value, for normal requests
                the encrypted request body. The signature is computed over it.

        The signature is HMAC-SHA256 over "<ts>+<once>+<encrypted_body_b64>", keyed on
        the ascii-hex string (not raw bytes) of:
        - the presetKey, for the session key exchange, or
        - the session key shared_secret[:16] (the securityKey), for every request once
          the handshake has derived it.

        """
        sign_key_hex = (
            self._preset_key_hex
            if self.shared_secret is None
            else self.shared_secret[:16].hex()
        )
        request_once = os.urandom(16).hex()
        signature = hmac.new(
            sign_key_hex.encode(),
            f"{timestamp}+{request_once}+{encrypted_body_b64}".encode(),
            hashlib.sha256,
        ).hexdigest()
        return {
            "x-app-key": "",  # Can be empty
            "x-encryption-info": "algo_ecdh",
            "x-replay-info": "replay",
            "x-key-ident": self.key_ident,
            "x-request-once": request_once,
            "x-request-ts": timestamp,
            "x-signature": signature,
        }

    async def perform_key_exchange(
        self,
        api_base: str,
        headers: dict | None = None,
    ) -> str | None:
        """Perform the key exchange with Anker's server and return shared secret."""
        if not isinstance(headers, dict):
            headers = {}
        # Prepare request. The key-exchange body is plain json holding only the
        # presetKey-wrapped client public key; the signature is over that value.
        url = f"{api_base}/{API_KEY_EXCHANGE}"
        method = "post"
        client_public_key = self._client_public_key_field()
        data = {"client_public_key": client_public_key}
        timestamp = generateTimestamp()
        # obtain encryption header fields and add/modify fields for key exchange request
        headers.update(
            self.generate_x_header(
                timestamp=timestamp, encrypted_body_b64=client_public_key
            )
            | {
                "content-type": "application/json",
                "x-auth-ts": timestamp,
            }
        )
        self._logger.debug("Request Url: %s %s", method.upper(), url)
        self._logger.debug(
            "Request Headers: %s",
            self._client.mask_values(headers, "x-auth-token", "gtoken"),
        )
        self._logger.debug("Request Body: %s", str(data))
        async with self._client.session.request(
            method,
            url,
            headers=headers,
            json=data,
            timeout=ClientTimeout(total=self._client.requestTimeout()),
        ) as resp:
            try:
                if self._client.request_count:
                    self._client.request_count.add(
                        request_time=datetime.now().astimezone(),
                        request_info=(f"{method.upper()} {url} {data}").strip(),
                    )
                self._logger.debug("AnkerEncryptionHandler request response received")
                # print response headers
                self._logger.debug("Response Headers: %s", resp.headers)
                # get first the body text for usage in error detail logging if necessary
                body_text = await resp.text()
                data = {}
                resp.raise_for_status()  # any response status >= 400
                # get json data without strict checking for json content
                data = await resp.json(content_type=None)
                if not data:
                    self._logger.error("Response Text: %s", body_text)
                    raise ClientError(  # noqa: TRY301
                        f"No data response while requesting {API_KEY_EXCHANGE}"
                    )
                self._logger.debug("Response Data: %s", data)
                self.server_public_key = (data.get("data") or {}).get(
                    "server_public_key"
                ) or None
                if not self.server_public_key:
                    return None
                return self.derive_shared_key(self.server_public_key)

            # Exception from ClientSession based on standard response status codes
            except ClientError as err:
                # Prepare data dict for Api error lookup
                if not data:
                    data = {}
                if not hasattr(data, "code"):
                    data["code"] = resp.status
                if not hasattr(data, "msg"):
                    data["msg"] = body_text
                # raise Client error otherwise
                raise ClientError(
                    f"AnkerEncryptionHandler Key exchange failed: {err}, response={body_text}",
                ) from err

    def derive_shared_key(self, server_public_key_b64: str) -> bytes:
        """Derive the ECDH shared secret from the server's public key.

        The server_public_key is presetKey-wrapped exactly like the client key; unwrap
        it to the 130-char ascii hex point, then ECDH. The shared secret is the raw ECDH
        output (32 bytes, the X coordinate) used directly - there is no HKDF step.
        """
        point = bytes.fromhex(self._preset_decrypt(server_public_key_b64).decode())
        server_public_key = ec.EllipticCurvePublicKey.from_encoded_point(
            ec.SECP256R1(), point
        )
        self.shared_secret = self._private_key.exchange(ec.ECDH(), server_public_key)
        return self.shared_secret

    def _body_key(self) -> bytes:
        """Return the AES-128 key for request/response body encryption.

        shared_secret[:16], the per-auth session key the app calls the securityKey.
        Confirmed live end to end: a request body encrypted with it is accepted and the
        encrypted response decrypts with it. Cipher is AES-128-CBC, leading iv, PKCS7.
        """
        return self.shared_secret[:16]

    def encrypt_body(self, body: dict) -> str:
        """Encrypt a request body: AES-128-CBC, random IV prepended, PKCS7, base64.

        The body dict is serialized to compact json (no spaces) before encryption.
        """
        plaintext = json.dumps(body, separators=(",", ":")).encode()
        iv = randbytes(16)
        padder = padding.PKCS7(128).padder()
        padded = padder.update(plaintext) + padder.finalize()
        encryptor = Cipher(algorithms.AES(self._body_key()), modes.CBC(iv)).encryptor()
        return b64encode(iv + encryptor.update(padded) + encryptor.finalize()).decode()

    def decryptApiData(self, encrypted_payload: str) -> Any:
        """Decrypt an encrypted body: strip leading IV, AES-128-CBC decrypt, unpad, deserialize."""
        encrypted_data = b64decode(encrypted_payload)
        iv = encrypted_data[:16]
        ciphertext = encrypted_data[16:]
        decryptor = Cipher(algorithms.AES(self._body_key()), modes.CBC(iv)).decryptor()
        decrypted = decryptor.update(ciphertext) + decryptor.finalize()
        # Remove PKCS7 padding
        padding_length = decrypted[-1]
        return json.loads(decrypted[:-padding_length].decode())
