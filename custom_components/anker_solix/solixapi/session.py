"""Anker Power/Solix Cloud API class to handle a client connection session for an account."""

from asyncio import sleep
from base64 import b64decode, b64encode
import contextlib
from datetime import datetime

# TODO(COMPRESSION): from gzip import compress, decompress
import hashlib
import json
import logging
import os
from pathlib import Path
from random import randbytes, randrange
import tempfile

import aiofiles
import aiofiles.os
from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientError
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, padding, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from . import errors
from .apitypes import (
    API_COUNTRIES,
    API_ENDPOINTS,
    API_HEADERS,
    API_KEY_EXCHANGE,
    API_LOGIN,
    API_SERVERS,
    SolixDefaults,
)
from .helpers import RequestCounter, generateTimestamp, getTimezoneGMTString, md5

_LOGGER: logging.Logger = logging.getLogger(__name__)


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
        for region, countries in API_COUNTRIES.items():
            if self._countryId in countries:
                self._api_base = API_SERVERS.get(region)
        # default to EU server
        if not self._api_base:
            self._api_base = API_SERVERS.get("eu")
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
    def server(self) -> str | None:
        """Get the server used for the active session."""
        return self._api_base

    def logger(self, logger: logging.Logger | None = None) -> logging.Logger:
        """Get or set the logger for API client."""
        if logger:
            self._logger = logger
        return self._logger

    def testDir(self, subfolder: str | None = None) -> str:
        """Get or set the subfolder for local API test files."""
        if not subfolder or subfolder == self._testdir:
            return self._testdir
        if not Path(subfolder).is_dir():
            self._logger.error(
                "Specified test folder for api %s does not exist: %s",
                self.nickname,
                subfolder,
            )
        else:
            self._testdir = subfolder
            self._logger.info("Set api %s test folder to: %s", self.nickname, subfolder)
        return self._testdir

    def logLevel(self, level: int | None = None) -> int:
        """Get or set the logger log level."""
        if level is not None and isinstance(level, int):
            self._logger.setLevel(level)
            self._logger.info("Set api %s log level to: %s", self.nickname, level)
        return self._logger.getEffectiveLevel()

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
        header = API_HEADERS
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
                65 - (datetime.now() - same_requests[0][0]).total_seconds()
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
                delay - (datetime.now() - self._last_request_time).total_seconds()
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
                datetime.fromtimestamp(self._authFileTime).isoformat(),
            )
            self._logger.debug(
                "%s",
                self.mask_values(
                    data,
                    "user_id",
                    "auth_token",
                    "email",
                    "geo_key",
                    "ap_cloud_user_id",
                ),
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
                    "user_id",
                    "auth_token",
                    "email",
                    "geo_key",
                    "ap_cloud_user_id",
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
            )
        else:
            self._token_expiration = None
            self._loggedIn = False
        if data.get("user_id"):
            # gtoken is MD5 hash of user_id from login response
            self._gtoken = md5(data.get("user_id"))
            # reset retry flag upon valid authentication response for normal request retry attempts
            self._retry_attempt = False
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
        if not isinstance(headers, dict):
            headers = {}
        if not isinstance(json, dict):
            json = {}
        # check token expiration (7 days)
        if (
            self._token_expiration
            and (self._token_expiration - datetime.now()).total_seconds() < 60
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
        mergedHeaders = self.generate_header()
        mergedHeaders.update(headers)
        # TODO(ENCRYPTION): Handle payload encryption once known
        if self.encrypt_payload and self._login_response:
            if not self._eh and self._token:
                # init encryption handler
                self._eh = AnkerEncryptionHandler(
                    login_response=self._login_response,
                    session=self._session,
                    logger=self._logger,
                )
            if not self._eh.shared_secret:
                # Perform key exchange
                await self._eh.perform_key_exchange(
                    api_base=self._api_base, headers=mergedHeaders
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

            # Mandatory extra api header arguments for key exchange
            #     'x-app-key': '' # empty is fine
            #     'x-encryption-info': 'algo_ecdh'
            #     'x-replay-info': 'replay'
            #     'x-auth-ts': [authentication timestamp] # Unix Timestamp in s as string
            #     'x-key-ident': [generated key ident] # 16 Byte MD5 hash
            #     'x-request-once': [generated request once] # 16 Byte MD5 hash
            #     'x-request-ts': [request timestamp] # Unix Timestamp in s as string
            #     'x-signature': [generated signature] # 32 Byte SHA256 hash
            # Response will return encrypted body and a signature field
            timestamp = generateTimestamp()
            mergedHeaders.update(
                self._eh.generate_x_header(timestamp=timestamp, data=json)
                | {
                    "content-type": "text/plain",
                }
            )

        self._logger.debug("Request Url: %s %s", method.upper(), url)
        self._logger.debug(
            "Request Headers: %s",
            self.mask_values(mergedHeaders, "x-auth-token", "gtoken"),
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
                    "user_id",
                    "auth_token",
                    "email",
                    "geo_key",
                    "token",
                    "password",
                    "ap_cloud_user_id",
                )
            )
        else:
            body_text = str(json)
        self._logger.debug("Request Body: %s", body_text)
        # enforce configured delay between any subsequent request
        await self._wait_delay(endpoint=endpoint)
        # uncompressed body must use json parameter, pre-compressed body must use data parameter
        # make the request, auto_decompression of body enabled by default
        async with self._session.request(
            method,
            url,
            headers=mergedHeaders,
            json=json,
            # TODO(COMPRESSION): only response encoding seems to be accepted by servers
            # json=None if self.compress_data else json,
            # data=compress(str(json).encode()) if self.compress_data else None,
        ) as resp:
            try:
                self._last_request_time = datetime.now()
                self.request_count.add(
                    request_time=self._last_request_time,
                    request_info=(f"{method.upper()} {url} {body_text}").strip(),
                )
                # request handler has auto-decompression enabled
                self._logger.debug(
                    "Api %s request %s %s response received", self.nickname, method, url
                )
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
                    raise ClientError(f"No data response while requesting {endpoint}")  # noqa: TRY301
                if endpoint == API_LOGIN:
                    self._logger.debug(
                        "Response Data: %s",
                        self.mask_values(
                            data,
                            "user_id",
                            "auth_token",
                            "email",
                            "geo_key",
                            "ap_cloud_user_id",
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

                # TODO(ENCRYPTION): data field has to be decoded when encrypted and signature field in response
                if self.encrypt_payload and data.get("signature"):
                    data["data"] = self._eh.decryptApiData(data.get("data"))
                return data  # noqa: TRY300

            # Exception from ClientSession based on standard response status codes
            except ClientError as err:
                # Prepare data dict for Api error lookup
                if not data:
                    data = {}
                if not hasattr(data, "code"):
                    data["code"] = resp.status
                if not hasattr(data, "msg"):
                    data["msg"] = body_text
                if resp.status in [401, 403]:
                    # Unauthorized or forbidden request
                    self._logger.error("Api %s Request Error: %s", self.nickname, err)
                    self._logger.error("Response Text: %s", body_text)
                    # reattempt authentication with same credentials if cached token was kicked out
                    # retry attempt is set if login response data were not cached to fail immediately
                    if not self._retry_attempt:
                        self._logger.warning(
                            "Login failed, retrying authentication%s",
                            (" for " + str(self.nickname)) if self.nickname else "",
                        )
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
                                    for i in self.request_count.last_minute(
                                        details=True
                                    )
                                    if endpoint in i[1]
                                ]
                            ),
                            endpoint,
                        )
                        return await self.request(
                            method, endpoint, headers=headers, json=json
                        )
                    # Too Many Requests, add stats to message
                    self._logger.error("Api %s Request Error: %s", self.nickname, err)
                    self._logger.error("Response Text: %s", body_text)
                    errors.raise_error(
                        data, prefix=f"Too Many Requests: {self.request_count}"
                    )
                else:
                    # raise Anker Solix error if code is known
                    self._logger.error("Api %s Request Error: %s", self.nickname, err)
                    self._logger.error("Response Text: %s", body_text)
                    errors.raise_error(data)
                # raise Client error otherwise
                raise ClientError(
                    f"Api Request Error: {err}", f"response={body_text}"
                ) from err
            except errors.AnkerSolixError as err:  # Other Exception from API
                if isinstance(err, errors.BusyError):
                    # Api fails to respond to standard query, repeat once after delay
                    self._logger.error("Api %s Busy Error: %s", self.nickname, err)
                    self._logger.error("Response Text: %s", body_text)
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
                self._logger.error("%s", err)
                self._logger.error("Response Text: %s", body_text)
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
                    data = json.loads(await file.read())
                    self._logger.debug("Loaded JSON from file %s:", masked_filename)
                    self._logger.debug(
                        "Data: %s",
                        self.mask_values(
                            data,
                            "user_id",
                            "auth_token",
                            "email",
                            "geo_key",
                            "token",
                            "ap_cloud_user_id",
                        ),
                    )
                    self.request_count.add(request_info=f"LOAD {masked_filename}")
                    return data
        except OSError as err:
            self._logger.error(
                "ERROR: Failed to load JSON from file %s", masked_filename
            )
            self._logger.error(err)
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
            self._logger.error("ERROR: Failed to save JSON to file %s", masked_filename)
            self._logger.error(err)
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
                "ERROR: Failed to remove modified JSON file %s", masked_filename
            )
            self._logger.error(err)
            return False
        return True


class AnkerEncryptionHandler:
    """Anker Solix encryption handler class.

    ATTENTION: This class is experimental and does not work yet since various x header field value generation is unknown.
    """

    def __init__(
        self,
        login_response: dict,
        session: ClientSession,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize the encryption handler."""
        self._login_response = login_response
        self._session = session
        # Create ECDH key pair for encryption key exchange using NIST P-256 curve
        self.private_key = ec.generate_private_key(ec.SECP256R1())
        self.public_key = self.private_key.public_key()
        self.server_public_key = None
        self.shared_secret = None
        # initialize logger for class
        if logger:
            self._logger = logger
        else:
            self._logger = _LOGGER
            self._logger.setLevel(logging.WARNING)
        if not self._logger.hasHandlers():
            self._logger.addHandler(logging.StreamHandler())

    def _generate_client_key(self, timestamp: str) -> str:
        """Generate the client public key in Anker's format."""
        # Get raw public key bytes
        raw_public_key = self.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint,
        )
        # Construct the key with timestamp and marker as observed in Api communication
        key_data = bytearray()
        key_data.extend(timestamp.encode())  # First 16 bytes: timestamp
        key_data.append(0x1F)  # Marker byte ?
        key_data.extend(raw_public_key)  # Public key uncompressed point format in bytes
        # return base64 encoded string representation of key format
        return b64encode(key_data).decode()

    def generate_x_header(self, timestamp: str, data: dict) -> dict:
        """Generate extra header fields for encryption."""
        # request_once using timestamp in s and random? data (to be adjusted as required)
        request_once = md5(timestamp.encode() + randbytes(16))
        request_once = md5(
            timestamp.encode() + self._login_response.get("geo_key").encode()
        )
        # key_ident using timestamp in ms and random? data (to be adjusted as required)
        key_ident = md5(timestamp.encode() + randbytes(16))
        key_ident = md5(
            timestamp.encode() + self._login_response.get("auth_token").encode()
        )
        # SHA256 signature using timestamp, request-once, key_ident and body?  (to be adjusted as required)
        signature = hashlib.sha256(
            timestamp.encode()
            + request_once.encode()
            + key_ident.encode()
            + json.dumps(data).encode()
        ).hexdigest()
        return {
            "content-type": "text/plain",
            "x-app-key": "",  # Can be empty
            "x-encryption-info": "algo_ecdh",
            "x-replay-info": "replay",
            "x-key-ident": key_ident,
            "x-request-once": request_once,
            "x-request-ts": timestamp,
            "x-signature": signature,
        }

    async def perform_key_exchange(
        self,
        api_base: str,
        auth_ts: str | None = None,
        headers: dict | None = None,
    ) -> str | None:
        """Perform the key exchange with Anker's server and return shared secret."""
        if not isinstance(headers, dict):
            headers = {}
        timestamp = generateTimestamp()
        if not auth_ts:
            auth_ts = timestamp
        # Prepare request
        url = f"{api_base}/{API_KEY_EXCHANGE}"
        data = {"client_public_key": self._generate_client_key(timestamp=auth_ts)}
        # obtain encryption header fields and add/modify fields for key exchange request
        headers.update(
            self.generate_x_header(timestamp=timestamp, data=data)
            | {
                "content-type": "application/json",
                "x-auth-ts": auth_ts,
            }
        )
        self._logger.debug("Request Url: %s %s", "POST", url)
        self._logger.debug(
            "Request Headers: %s",
            headers,
        )
        self._logger.debug("Request Body: %s", str(data))
        async with self._session.request(
            "post",
            url,
            headers=headers,
            json=data,
        ) as resp:
            try:
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
                    f"AnkerEncryptionHandler Key exchange failed: {err}",
                    f"response={body_text}",
                ) from err

    def derive_shared_key(self, server_public_key_b64: str) -> bytes:
        """Derive the shared AES key from the server's public key."""
        # Decode server's public key
        server_key_bytes = b64decode(server_public_key_b64)
        # Extract the actual key portion (first 96 bytes based on analysis, but may need to be adopted)
        key_portion = server_key_bytes[:96]
        # Load server's public key
        server_public_key = ec.EllipticCurvePublicKey.from_encoded_point(
            ec.SECP256R1(), key_portion
        )
        # Compute shared secret
        shared_secret = self.private_key.exchange(ec.ECDH(), server_public_key)
        # Derive AES key using HKDF
        hkdf = HKDF(
            algorithm=hashes.SHA256(), length=32, salt=None, info=b"ecdh handshake"
        )
        self.shared_secret = hkdf.derive(shared_secret)
        return self.shared_secret

    def decryptApiData(self, encrypted_payload: str) -> str:
        """Decrypt an encrypted payload using the derived shared AES key."""
        # Decode base64 payload
        encrypted_data = b64decode(encrypted_payload)
        # Split IV and ciphertext by first 16 bytes
        iv = encrypted_data[:16]
        ciphertext = encrypted_data[16:]
        # Create AES cipher
        cipher = Cipher(algorithms.AES(self.shared_secret), modes.CBC(iv))
        # Decrypt
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(ciphertext) + decryptor.finalize()
        # Remove PKCS7 padding
        padding_length = decrypted[-1]
        return decrypted[:-padding_length].decode()
