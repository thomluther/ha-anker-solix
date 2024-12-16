"""Anker Power/Solix Cloud API class to handle a client connection session for an account."""

from asyncio import sleep
from base64 import b64encode
import contextlib
from datetime import datetime
import json
import logging
from pathlib import Path
import time as systime

import aiofiles
from aiohttp import ClientSession
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
    API_LOGIN,
    API_SERVERS,
    SolixDefaults,
)
from .helpers import RequestCounter, getTimezoneGMTString, md5

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
            Path(Path(__file__).parent) / ".." / "examples" / "example1"
        )

        # Flag for retry after any token error
        self._retry_attempt: bool = False
        # ensure folder for authentication caching exists
        Path(Path(Path(__file__).parent) / "authcache").mkdir(
            parents=True, exist_ok=True
        )
        # filename for authentication cache
        self._authFile: str = str(
            Path(Path(__file__).parent) / "authcache" / f"{email}.json"
        )
        self._authFileTime: float = 0

        # Timezone format: 'GMT+01:00'
        self._timezone: str = getTimezoneGMTString()
        self._gtoken: str | None = None
        self._token: str | None = None
        self._token_expiration: datetime | None = None
        self._login_response: dict = {}
        self._request_delay: float = SolixDefaults.REQUEST_DELAY_DEF
        self._last_request_time: datetime | None = None

        # Define Encryption for password, using ECDH asymmetric key exchange for shared secret calculation, which must be used to encrypt the password using AES-256-CBC with seed of 16
        # uncompressed public key from EU Anker server in the format 04 [32 byte x value] [32 byte y value]
        # Both, the EU and COM Anker server public key is the same and login response is provided for both upon an authentication request
        # However, if country ID assignment is to wrong server, no sites or devices will be listed for the authenticated account.
        # Encryption curve SECP256R1 (identical to prime256v1)
        self._curve = ec.SECP256R1()
        # get EllipticCurvePrivateKey
        self._ecdh = ec.generate_private_key(self._curve, default_backend())
        # get EllipticCurvePublicKey
        self._public_key = self._ecdh.public_key()
        # get bytes of shared secret
        self._shared_key = self._ecdh.exchange(
            ec.ECDH(),
            ec.EllipticCurvePublicKey.from_encoded_point(
                self._curve, bytes.fromhex(self._api_public_key_hex)
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
        self.encrypt_body: bool = False
        self.request_count: RequestCounter = RequestCounter()

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

    def logger(self, logger: logging.Logger | None = None) -> str:
        """Get or set the logger for API client."""
        if logger:
            self._logger = logger
        return self._logger

    def testDir(self, subfolder: str | None = None) -> str:
        """Get or set the subfolder for local API test files."""
        if not subfolder or subfolder == self._testdir:
            return self._testdir
        if not Path(subfolder).is_dir():
            self._logger.error("Specified test folder does not exist: %s", subfolder)
        else:
            self._testdir = subfolder
            self._logger.info("Set Api test folder to: %s", subfolder)
        return self._testdir

    def logLevel(self, level: int | None = None) -> int:
        """Get or set the logger log level."""
        if level is not None and isinstance(level, int):
            self._logger.setLevel(level)
            self._logger.info("Set log level to: %s", level)
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
                "Set api request delay to %.3f seconds", self._request_delay
            )
        return self._request_delay

    async def _wait_delay(self, delay: float | None = None) -> None:
        """Wait at least for the defined Api request delay or for the provided delay in seconds since the last request occurred."""
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
                        # public_key is uncompressed format of points in hex (0x04 + 32 Byte + 32 Byte)
                        "public_key": self._public_key.public_bytes(
                            serialization.Encoding.X962,
                            serialization.PublicFormat.UncompressedPoint,
                        ).hex()
                    },
                    "enc": 0,
                    "email": self._email,
                    # password is AES-256-CBC encrypted by the ECDH shared key derived from server public key and local private key
                    "password": self._encryptApiData(self._password),
                    # time_zone is offset in ms, e.g. 'GMT+01:00' => 3600000
                    "time_zone": round(datetime.utcoffset(now).total_seconds() * 1000),
                    # transaction is Unix Timestamp in ms as string
                    "transaction": str(int(systime.mktime(now.timetuple()) * 1000)),
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
                self._authFileTime = Path(self._authFile).stat().st_mtime

        # Update the login params
        self._login_response = {}
        self._login_response.update(data)
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
                Path(self._authFile).is_file()
                and self._authFileTime != Path(self._authFile).stat().st_mtime
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
        if endpoint in [
            API_LOGIN,
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
                )
            )
        else:
            body_text = str(json)
        self._logger.debug("Request Body: %s", body_text)
        # enforce configured delay between any subsequent request
        await self._wait_delay()
        async with self._session.request(
            method, url, headers=mergedHeaders, json=json
        ) as resp:
            try:
                self._last_request_time = datetime.now()
                self.request_count.add(
                    request_time=self._last_request_time,
                    request_info=(f"{method.upper()} {url} {body_text}").strip(),
                )
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
                    raise ClientError(f"No data response while requesting {endpoint}")  # noqa: TRY301

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
                    # reattempt authentication with same credentials if cached token was kicked out
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

    def _encryptApiData(self, raw: str) -> str:
        """Return Base64 encoded secret as utf-8 decoded string using the shared secret with seed of 16 for the encryption."""
        # Password must be UTF-8 encoded and AES-256-CBC encrypted with block size of 16
        aes = Cipher(
            algorithms.AES(self._shared_key),
            modes.CBC(self._shared_key[0:16]),
            backend=default_backend(),
        )
        encryptor = aes.encryptor()
        # Use default PKCS7 padding for incomplete AES blocks
        padder = padding.PKCS7(128).padder()
        raw_padded = padder.update(raw.encode("utf-8")) + padder.finalize()
        return (b64encode(encryptor.update(raw_padded) + encryptor.finalize())).decode(
            "utf-8"
        )

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
                            f"{old[idx:idx+2]}###masked###{old[idx+14:idx+16]}"
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
                            data, "user_id", "auth_token", "email", "geo_key", "token"
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
