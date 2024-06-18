"""Class for interacting with the Anker Power / Solix API.

Required Python modules:
pip install cryptography
pip install aiohttp
pip install aiofiles
"""

from __future__ import annotations

from asyncio import sleep
from base64 import b64encode
import contextlib
import copy
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import json
import logging
import os
import sys
import time as systime

import aiofiles
from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientError
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, padding, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from . import errors

_LOGGER: logging.Logger = logging.getLogger(__name__)

"""Default definitions required for the Anker Power/Solix Cloud API"""
# API servers per region. Country assignment not clear, defaulting to EU server
_API_SERVERS = {
    "eu": "https://ankerpower-api-eu.anker.com",
    "com": "https://ankerpower-api.anker.com",
}
_API_LOGIN = "passport/login"
_API_HEADERS = {
    "Content-Type": "application/json",
    "Model-Type": "DESKTOP",
    "App-Name": "anker_power",
    "Os-Type": "android",
}
_API_COUNTRIES = {
    "com": [
        "DZ",
        "LB",
        "SY",
        "EG",
        "LY",
        "TN",
        "IL",
        "MA",
        "JO",
        "PS",
        "AR",
        "AU",
        "BR",
        "HK",
        "IN",
        "JP",
        "MX",
        "NG",
        "NZ",
        "RU",
        "SG",
        "ZA",
        "KR",
        "TW",
        "US",
        "CA",
    ],
    "eu": [
        "BE",
        "EL",
        "LT",
        "PT",
        "BG",
        "ES",
        "LU",
        "RO",
        "CZ",
        "FR",
        "HU",
        "SI",
        "DK",
        "HR",
        "MT",
        "SK",
        "DE",
        "IT",
        "NL",
        "FI",
        "EE",
        "CY",
        "AT",
        "SE",
        "IE",
        "LV",
        "PL",
        "UK",
        "IS",
        "NO",
        "LI",
        "CH",
        "BA",
        "ME",
        "MD",
        "MK",
        "GE",
        "AL",
        "RS",
        "TR",
        "UA",
        "XK",
        "AM",
        "BY",
        "AZ",
    ],
}  # TODO(2): Expand or update list once ID assignments are wrong or missing

"""Following are the Anker Power/Solix Cloud API endpoints known so far"""
_API_ENDPOINTS = {
    "homepage": "power_service/v1/site/get_site_homepage",  # Scene info for configured site(s), content as preseneted on App Home Page (mostly empty for shared accounts)
    "site_list": "power_service/v1/site/get_site_list",  # List of available site ids for the user, will also show sites shared withe the account
    "site_detail": "power_service/v1/site/get_site_detail",  # Information for given site_id, can also be used by shared accounts
    "site_rules": "power_service/v1/site/get_site_rules",  # Information for supported power site types and their min and max qty per device model types
    "scene_info": "power_service/v1/site/get_scen_info",  # Scene info for provided site id (contains most information as the App home screen, with some but not all device details)
    "user_devices": "power_service/v1/site/list_user_devices",  # List Device details of owned devices, not all device details information included
    "charging_devices": "power_service/v1/site/get_charging_device",  # List of Portable Power Station devices?
    "get_device_parm": "power_service/v1/site/get_site_device_param",  # Get settings of a device for the provided site id and param type (e.g. Schedules)
    "set_device_parm": "power_service/v1/site/set_site_device_param",  # Apply provided settings to a device for the provided site id and param type (e.g. Schedules), NOT IMPLEMENTED YET
    "wifi_list": "power_service/v1/site/get_wifi_info_list",  # List of available networks for provided site id
    "get_site_price": "power_service/v1/site/get_site_price",  # List defined power price and CO2 for given site, works only for site owner account
    "update_site_price": "power_service/v1/site/update_site_price",  # Update power price and CO2 for given site, works only for site owner account
    "get_auto_upgrade": "power_service/v1/app/get_auto_upgrade",  # List of Auto-Upgrade configuration and enabled devices, only works for site owner accout
    "set_auto_upgrade": "power_service/v1/app/set_auto_upgrade",  # Set/Enable Auto-Upgrade configuration, works only for site owner account
    "bind_devices": "power_service/v1/app/get_relate_and_bind_devices",  # List with details of locally connected/bound devices, includes firmware version, works only for owner account
    "get_device_load": "power_service/v1/app/device/get_device_home_load",  # Get defined device schedule (same data as provided with device param query)
    "set_device_load": "power_service/v1/app/device/set_device_home_load",  # Set defined device schedule, Accepts the new schedule, but does NOT change it? Maybe future use for schedules per device
    "get_ota_info": "power_service/v1/app/compatible/get_ota_info",  # Get OTA status for solarbank and/or inverter serials
    "get_ota_update": "power_service/v1/app/compatible/get_ota_update",  # Get info of available OTA update
    "solar_info": "power_service/v1/app/compatible/get_compatible_solar_info",  # Solar inverter definition for solarbanks, works only with owner account
    "get_cutoff": "power_service/v1/app/compatible/get_power_cutoff",  # Get Power Cutoff settings (Min SOC) for provided site id and device sn, works only with owner account
    "set_cutoff": "power_service/v1/app/compatible/set_power_cutoff",  # Set Min SOC for device, only works for onwer accounts
    "compatible_process": "power_service/v1/app/compatible/get_compatible_process",  # contains solar_info plus OTA processing codes, works only with owner account
    "get_device_fittings": "power_service/v1/app/get_relate_device_fittings",  # Device fittings for given site id and device sn. Shows Accessories like Solarbank 0W Switch info
    "energy_analysis": "power_service/v1/site/energy_analysis",  # Fetch energy data for given time frames
    "home_load_chart": "power_service/v1/site/get_home_load_chart",  # Fetch data as displayed in home load chart for schedule adjustments for given site_id and optional device SN (empty if solarbank not connected)
    "get_upgrade_record": "power_service/v1/app/get_upgrade_record",  # get list of firmware update history
    "check_upgrade_record": "power_service/v1/app/check_upgrade_record",  # show an upgrade record for the device, types 1-3 show different info, only works for owner account
    "get_message_unread": "power_service/v1/get_message_unread",  # GET method to show if there are unread messages for account
    "get_message": "power_service/v1/get_message",  # GET method to list Messages from certain time, not explored or used (last_time format unknown)
    "get_mqtt_info": "app/devicemanage/get_user_mqtt_info",  # post method to list mqtt server and certificates for a site, not explored or used
    "get_product_categories": "power_service/v1/product_categories",  # GET method to list all supported products with details and web picture links
    "get_product_accessories": "power_service/v1/product_accessories",  # GET method to list all supported products accessories with details and web picture links
}

""" Other endpoints neither implemented nor explored:
    'power_service/v1/site/can_create_site',
    'power_service/v1/site/create_site',
    'power_service/v1/site/update_site',
    'power_service/v1/site/delete_site',
    'power_service/v1/site/add_charging_device',
    'power_service/v1/site/update_charging_device',
    'power_service/v1/site/reset_charging_device',
    'power_service/v1/site/delete_charging_device',
    'power_service/v1/site/add_site_devices',
    'power_service/v1/site/delete_site_devices',
    'power_service/v1/site/update_site_devices',
    'power_service/v1/site/get_addable_site_list', # show to which defined site a given model type can be added
    'power_service/v1/app/compatible/set_ota_update',
    'power_service/v1/app/compatible/save_ota_complete_status',
    'power_service/v1/app/compatible/check_third_sn',
    'power_service/v1/app/compatible/save_compatible_solar',
    'power_service/v1/app/compatible/get_confirm_permissions',
    'power_service/v1/app/compatible/confirm_permissions_settings',
    'power_service/v1/app/after_sale/check_popup',
    'power_service/v1/app/after_sale/check_sn',
    'power_service/v1/app/after_sale/mark_sn',
    'power_service/v1/app/share_site/delete_site_member',
    'power_service/v1/app/share_site/invite_member',
    'power_service/v1/app/share_site/delete_inviting_member',
    'power_service/v1/app/share_site/get_invited_list',
    'power_service/v1/app/share_site/join_site',
    'power_service/v1/app/upgrade_event_report', # post an entry to upgrade event report
    'power_service/v1/app/get_phonecode_list',
    'power_service/v1/get_message_not_disturb',  # get do not disturb messages settings
    'power_service/v1/message_not_disturb',  # change do not disurb messages settings
    'power_service/v1/read_message',
    'power_service/v1/del_message',
    'app/devicemanage/update_relate_device_info',
    'app/cloudstor/get_app_up_token_general',
    'app/logging/get_device_logging',
    'app/devicerelation/up_alias_name',  # Update Alias name of device? Fails with (10003) Failed to request
    'app/devicerelation/un_relate_and_unbind_device',
    'app/devicerelation/relate_device',
    'power_service/v1/app/device/get_device_attrs', # not found yet on server
    'power_service/v1/app/device/set_device_attrs', # not found yet on server
    'power_service/v1/app/device/get_mes_device_info', # shows laser_sn field but no more info
    'power_service/v1/app/device/get_relate_belong' # shows belonging of given device

Structure of the JSON response for an API Login Request:
An unexpired token_id must be used for API request, along with the gtoken which is an MD5 hash of the returned(encrypted) user_id.
The combination of the provided token and MD5 hashed user_id authenticate the client to the server.
The Login Response is cached in a JSON file per email user account and can be reused by this API class without further login request.

ATTENTION: Anker allows only 1 active token on the server per user account. Any login for the same account (e.g. via Anker mobile App) will kickoff the token used in this Api instance and further requests are no longer authorized.
Currently, the Api will re-authenticate automatically and therefore may kick off the other user that obtained the actual access token (e.g. kick out the App user again when used for regular Api requests)

NOTES: Parallel Api instances should use different user accounts. They may work in parallel when all using the same cached authentication data. The first API instance with failed authorization will restart a new Login request and updates
the cached JSON file. Other instances should recognize an update of the cached JSON file and will refresh their login credentials in the instance for the actual token and gtoken without new login request.
"""

LOGIN_RESPONSE: dict = {
    "user_id": str,
    "email": str,
    "nick_name": str,
    "auth_token": str,
    "token_expires_at": int,
    "avatar": str,
    "mac_addr": str,
    "domain": str,
    "ab_code": str,
    "token_id": int,
    "geo_key": str,
    "privilege": int,
    "phone": str,
    "phone_number": str,
    "phone_code": str,
    "server_secret_info": {"public_key": str},
    "params": list,
    "trust_list": list,
    "fa_info": {"step": int, "info": str},
    "country_code": str,
}


class SolixDeviceType(Enum):
    """Enumuration for Anker Solix device types."""

    SYSTEM = "system"
    SOLARBANK = "solarbank"
    INVERTER = "inverter"
    SMARTMETER = "smartmeter"
    PPS = "pps"
    POWERPANEL = "powerpanel"
    POWERCOOLER = "powercooler"


class SolixParmType(Enum):
    """Enumuration for Anker Solix Parameter types."""

    SOLARBANK_SCHEDULE = "4"


class SolarbankPowerMode(Enum):
    """Enumuration for Anker Solix Solarbank Power setting modes."""

    normal = 1
    advanced = 2


@dataclass(frozen=True)
class ApiCategories:
    """Dataclass to specify supported Api categorties for regular Api cache refresh cycles."""

    site_price: str = "site_price"
    device_auto_upgrade: str = "device_auto_upgrade"
    solarbank_energy: str = "solarbank_energy"
    solarbank_fittings: str = "solarbank_fittings"
    solarbank_cutoff: str = "solarbank_cutoff"
    solarbank_solar_info: str = "solarbank_solar_info"


@dataclass(frozen=True)
class SolixDeviceCapacity:
    """Dataclass for Anker Solix device battery capacities in Wh by Part Number."""

    A17C0: int = 1600  # SOLIX E1600 Solarbank
    A17C1: int = 1600  # SOLIX E1600 Solarbank 2 Pro
    A17C1321: int = 1600  # SOLIX E1600 Solarbank 2 Expansion battery
    A17C3: int = 1600  # SOLIX E1600 Solarbank 2 Plus
    A1720: int = 256  # Anker PowerHouse 521 Portable Power Station
    A1751: int = 512  # Anker PowerHouse 535 Portable Power Station
    A1753: int = 768  # SOLIX C800 Portable Power Station
    A1754: int = 768  # SOLIX C800 Plus Portable Power Station
    A1755: int = 768  # SOLIX C800X Portable Power Station
    A1760: int = 1024  # Anker PowerHouse 555 Portable Power Station
    A1761: int = 1056  # SOLIX C1000(X) Portable Power Station
    #A17C1: int = 1056  # SOLIX C1000 Expansion Battery # same PN as Solarbank 2?
    A1770: int = 1229  # Anker PowerHouse 757 Portable Power Station
    A1771: int = 1229  # SOLIX F1200 Portable Power Station
    A1772: int = 1536  # SOLIX F1500 Portable Power Station
    A1780: int = 2048  # SOLIX F2000 Portable Power Station (PowerHouse 767)
    A1780_1: int = 2048  # Expansion Battery for F2000
    A1780P: int = 2048  # SOLIX F2000 Portable Power Station (PowerHouse 767) with WLAN
    A1781: int = 2560  # SOLIX F2600 Portable Power Station
    A1790: int = 3840  # SOLIX F3800 Portable Power Station
    A1790_1: int = 3840  # SOLIX BP3800 Expansion Battery for F3800


@dataclass(frozen=True)
class SolixDeviceCategory:
    """Dataclass for Anker Solix device types by Part Number to be used for standalone/unbound device categorization."""

    # Solarbanks
    A17C0: str = SolixDeviceType.SOLARBANK.value  # SOLIX E1600 Solarbank
    A17C1: str = SolixDeviceType.SOLARBANK.value  # SOLIX E1600 Solarbank 2 Pro
    A17C3: str = SolixDeviceType.SOLARBANK.value  # SOLIX E1600 Solarbank 2 Plus
    # Inverter
    A5140: str = SolixDeviceType.INVERTER.value  # MI60 Inverter
    A5143: str = SolixDeviceType.INVERTER.value  # MI80 Inverter
    # Smart Meter
    A17X7: str = SolixDeviceType.SMARTMETER.value  # SOLIX Smart Meter
    # Portable Power Stations (PPS)
    A1720: str = (
        SolixDeviceType.PPS.value
    )  # Anker PowerHouse 521 Portable Power Station
    A1751: str = (
        SolixDeviceType.PPS.value
    )  # Anker PowerHouse 535 Portable Power Station
    A1753: str = SolixDeviceType.PPS.value  # SOLIX C800 Portable Power Station
    A1754: str = SolixDeviceType.PPS.value  # SOLIX C800 Plus Portable Power Station
    A1755: str = SolixDeviceType.PPS.value  # SOLIX C800X Portable Power Station
    A1760: str = (
        SolixDeviceType.PPS.value
    )  # Anker PowerHouse 555 Portable Power Station
    A1761: str = SolixDeviceType.PPS.value  # SOLIX C1000(X) Portable Power Station
    A1770: str = (
        SolixDeviceType.PPS.value
    )  # Anker PowerHouse 757 Portable Power Station
    A1771: str = SolixDeviceType.PPS.value  # SOLIX F1200 Portable Power Station
    A1772: str = SolixDeviceType.PPS.value  # SOLIX F1500 Portable Power Station
    A1780: str = (
        SolixDeviceType.PPS.value
    )  # SOLIX F2000 Portable Power Station (PowerHouse 767)
    A1781: str = SolixDeviceType.PPS.value  # SOLIX F2600 Portable Power Station
    A1790: str = SolixDeviceType.PPS.value  # SOLIX F3800 Portable Power Station
    # Home Power Panels
    A17B1: str = SolixDeviceType.POWERPANEL.value  # SOLIX Home Power Panel
    # Power Cooler
    A17A0: str = SolixDeviceType.POWERCOOLER.value  # SOLIX Power Cooler 30
    A17A1: str = SolixDeviceType.POWERCOOLER.value  # SOLIX Power Cooler 40
    A17A2: str = SolixDeviceType.POWERCOOLER.value  # SOLIX Power Cooler 50


@dataclass(frozen=True)
class SolixDefaults:
    """Dataclass for Anker Solix defaults to be used."""

    # Output Power presets for Solarbank schedule timeslot settings
    PRESET_MIN: int = 100
    PRESET_MAX: int = 800
    PRESET_DEF: int = 100
    PRESET_NOSCHEDULE: int = 200
    # Export Switch preset for Solarbank schedule timeslot settings
    ALLOW_EXPORT: bool = True
    # Preset power mode for Solarbank schedule timeslot settings
    POWER_MODE: int = SolarbankPowerMode.normal.value
    # Charge Priority limit preset for Solarbank schedule timeslot settings
    CHARGE_PRIORITY_MIN: int = 0
    CHARGE_PRIORITY_MAX: int = 100
    CHARGE_PRIORITY_DEF: int = 80
    # Seconds delay for subsequent Api requests in methods to update the Api cache dictionaries
    REQUEST_DELAY_MIN: float = 0.0
    REQUEST_DELAY_MAX: float = 5.0
    REQUEST_DELAY_DEF: float = 0.3


class SolixDeviceStatus(Enum):
    """Enumuration for Anker Solix Device status."""

    # The device status code seems to be used for cloud connection status.
    offline = "0"
    online = "1"
    unknown = "unknown"


class SolarbankStatus(Enum):
    """Enumuration for Anker Solix Solarbank status."""

    detection = "0"
    bypass = "1"
    discharge = "2"
    charge = "3"
    charge_bypass = "35"  # pseudo state, the solarbank does not distinguish this
    charge_priority = "37"  # pseudo state, the solarbank does not distinguish this but reports 3 as seen so far
    wakeup = "4"  # Not clear what happens during this state, but observed short intervals during night as well
    # TODO(3): Add descriptions once status code usage is observed/known
    # code 5 was not observed yet
    full_bypass = "6"  # seen at cold temperature, when battery must not be charged and the Solarbank bypasses all directly to inverter, also solar power < 25 W
    standby = "7"
    unknown = "unknown"


@dataclass
class SolarbankTimeslot:
    """Dataclass to define customizable attributes of an Anker Solix Solarbank time slot as used for the schedule definition or update."""

    start_time: datetime
    end_time: datetime
    appliance_load: int | None = (
        None  # mapped to appliance_loads setting using a default 50% share for dual solarbank setups
    )
    device_load: int | None = (
        None  # mapped to device load setting of provided solarbank serial
    )
    allow_export: bool | None = None  # mapped to the turn_on boolean
    charge_priority_limit: int | None = None  # mapped to charge_priority setting


class RequestCounter:
    """Counter for datetime entries in last minute and last hour."""

    def __init__(
        self,
    ) -> None:
        """Initialize."""
        self.elements: list = []

    def __str__(self) -> str:
        """Print the counters."""
        return f"{self.last_hour()} last hour, {self.last_minute()} last minute"

    def add(self, request_time: datetime = datetime.now()) -> None:
        """Add new timestamp to end of counter."""
        self.elements.append(request_time)
        # limit the counter entries to 1 hour when adding new
        self.recycle()

    def recycle(
        self, last_time: datetime = datetime.now() - timedelta(hours=1)
    ) -> None:
        """Remove oldest timestamps from beginning of counter until last_time is reached, default is 1 hour ago."""
        self.elements = [x for x in self.elements if x > last_time]

    def last_minute(self) -> int:
        """Get numnber of timestamps for last minute."""
        last_time = datetime.now() - timedelta(minutes=1)
        return len([x for x in self.elements if x > last_time])

    def last_hour(self) -> int:
        """Get numnber of timestamps for last minute."""
        last_time = datetime.now() - timedelta(hours=1)
        return len([x for x in self.elements if x > last_time])


class AnkerSolixApi:
    """Define the API class to handle Anker server authentication and API requests, along with the last state of queried site details and Device information."""

    def __init__(
        self,
        email: str,
        password: str,
        countryId: str,
        websession: ClientSession,
        logger=None,
    ) -> None:
        """Initialize."""
        self._countryId: str = countryId.upper()
        self._api_base: str | None = None
        for region, countries in _API_COUNTRIES.items():
            if self._countryId in countries:
                self._api_base = _API_SERVERS.get(region)
        # default to EU server
        if not self._api_base:
            self._api_base = _API_SERVERS.get("eu")
        self._email: str = email
        self._password: str = password
        self._session: ClientSession = websession
        self._loggedIn: bool = False
        self._testdir: str = os.path.join(
            os.path.dirname(__file__), "..", "examples", "example1"
        )
        self._retry_attempt: bool = False  # Flag for retry after any token error
        os.makedirs(
            os.path.join(os.path.dirname(__file__), "authcache"), exist_ok=True
        )  # ensure folder for authentication caching exists
        self._authFile: str = os.path.join(
            os.path.dirname(__file__), "authcache", f"{email}.json"
        )  # filename for authentication cache
        self._authFileTime: float = 0
        # initialize logger for object
        if logger:
            self._logger = logger
        else:
            self._logger = _LOGGER
            self._logger.setLevel(logging.WARNING)
        if not self._logger.hasHandlers():
            self._logger.addHandler(logging.StreamHandler(sys.stdout))

        self._timezone: str = (
            self._getTimezoneGMTString()
        )  # Timezone format: 'GMT+01:00'
        self._gtoken: str | None = None
        self._token: str | None = None
        self._token_expiration: datetime | None = None
        self._login_response: dict = {}
        self.mask_credentials: bool = True
        self.encrypt_body: bool = False
        self.request_count: RequestCounter = RequestCounter()
        self._request_delay: float = SolixDefaults.REQUEST_DELAY_DEF
        self._last_request_time: datetime | None = None

        # Define Encryption for password, using ECDH assymetric key exchange for shared secret calculation, which must be used to encrypt the password using AES-256-CBC with seed of 16
        # uncompressed public key from EU Anker server in the format 04 [32 byte x value] [32 byte y value]
        # Both, the EU and COM Anker server public key is the same and login response is provided for both upon an authentication request
        # However, if country ID assignment is to wrong server, no sites or devices will be listed for the authenticated account.
        self._api_public_key_hex = "04c5c00c4f8d1197cc7c3167c52bf7acb054d722f0ef08dcd7e0883236e0d72a3868d9750cb47fa4619248f3d83f0f662671dadc6e2d31c2f41db0161651c7c076"
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

        # track active devices bound to any site
        self._site_devices: set = set()

        # reset class variables for saving the most recent site and device data (Api cache)
        self.nickname: str = ""
        self.sites: dict = {}
        self.devices: dict = {}

    def _md5(self, text: str) -> str:
        """Return MD5 hash in hex for given string."""
        h = hashes.Hash(hashes.MD5())
        h.update(text.encode("utf-8"))
        return h.finalize().hex()

    def _getTimezoneGMTString(self) -> str:
        """Construct timezone GMT string with offset, e.g. GMT+01:00."""
        tzo = datetime.now().astimezone().strftime("%z")
        return f"GMT{tzo[:3]}:{tzo[3:5]}"

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

    async def _loadFromFile(self, filename: str) -> dict:
        """Load json data from given file for testing."""
        if self.mask_credentials:
            masked_filename = filename.replace(
                self._email, self.mask_values(self._email)
            )
        else:
            masked_filename = filename
        try:
            if os.path.isfile(filename):
                async with aiofiles.open(filename, encoding="utf-8") as file:
                    data = json.loads(await file.read())
                    self._logger.debug("Loaded JSON from file %s:", masked_filename)
                    self._logger.debug(
                        "Data: %s",
                        self.mask_values(
                            data, "user_id", "auth_token", "email", "geo_key"
                        ),
                    )
                    return data
        except OSError as err:
            self._logger.error(
                "ERROR: Failed to load JSON from file %s", masked_filename
            )
            self._logger.error(err)
        return {}

    async def _saveToFile(self, filename: str, data: dict | None = None) -> bool:
        """Save json data to given file for testing."""
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

    def _update_site(  # noqa: C901
        self,
        siteId: str,
        details: dict,
    ) -> None:
        """Update the internal sites dictionary with data provided for the nested site details dictionary.

        This method is used to consolidate site details from various less frequent requests that are not covered with the update_sites method.
        """
        # lookup old site details if any
        if siteId in self.sites:
            site_details = (self.sites[siteId]).get("site_details") or {}
            site_details.update(details)
        else:
            site_details = details
            self.sites[siteId] = {}
        self.sites[siteId]["site_details"] = site_details

    def _update_dev(  # noqa: C901
        self,
        devData: dict,
        devType: str | None = None,
        siteId: str | None = None,
        isAdmin: bool | None = None,
    ) -> str | None:
        """Update the internal device details dictionary with the given data. The device_sn key must be set in the data dict for the update to be applied.

        This method is used to consolidate various device related key values from various requests under a common set of device keys.
        """
        sn = devData.get("device_sn")
        if sn:
            device: dict = self.devices.get(sn, {})  # lookup old device info if any
            device.update({"device_sn": str(sn)})
            if devType:
                device.update({"type": devType.lower()})
            if siteId:
                device.update({"site_id": str(siteId)})
            if isAdmin:
                device.update({"is_admin": True})
            elif isAdmin is False and device.get("is_admin") is None:
                device.update({"is_admin": False})
            calc_capacity = False  # Flag whether capacity may need recalculation
            for key, value in devData.items():
                try:
                    if key in ["product_code", "device_pn"] and value:
                        device.update({"device_pn": str(value)})
                        # try to get type for standalone device from category definitions if not defined yet
                        if "type" not in device and hasattr(
                            SolixDeviceCategory, str(value)
                        ):
                            device.update(
                                {"type": getattr(SolixDeviceCategory, str(value))}
                            )
                    elif key in ["device_name"] and value:
                        if value != device.get("name", ""):
                            calc_capacity = True
                        device.update({"name": str(value)})
                    elif key in ["alias_name"] and value:
                        device.update({"alias": str(value)})
                    elif key in ["device_sw_version"] and value:
                        device.update({"sw_version": str(value)})
                    elif key in ["wifi_online"]:
                        device.update({"wifi_online": bool(value)})
                    elif key in ["wireless_type"]:
                        device.update({"wireless_type": str(value)})
                    elif key in ["wifi_name"] and value:
                        # wifi_name can be empty in details if device connected, avoid clearing name
                        device.update({"wifi_name": str(value)})
                    elif key in ["wifi_signal"]:
                        device.update({"wifi_signal": str(value)})
                    elif key in ["bt_ble_mac"] and value:
                        device.update({"bt_ble_mac": str(value)})
                    elif key in ["battery_power"] and value:
                        # This is a percentage value for the battery state of charge, not power
                        device.update({"battery_soc": str(value)})
                    elif key in ["charging_power"]:
                        device.update({"charging_power": str(value)})
                    elif key in ["photovoltaic_power"]:
                        device.update({"input_power": str(value)})
                    elif key in ["output_power"]:
                        device.update({"output_power": str(value)})
                    # solarbank info shows the load preset per device, which is identical to device parallel_home_load for 2 solarbanks, or current homeload for single solarbank
                    elif key in ["set_load_power", "parallel_home_load"] and value:
                        # Value may include unit, remove unit to have content consistent
                        device.update({"set_output_power": str(value).replace("W", "")})
                    # The current_home_load from get_device_load always shows the system wide settings made via the schedule
                    elif key in ["current_home_load"] and value:
                        # Value may include unit, remove unit to have content consistent
                        device.update(
                            {"set_system_output_power": str(value).replace("W", "")}
                        )
                        # Value for device home load may be empty for single solarbank, use this setting also for device preset in this case
                        if not device.get("set_output_power"):
                            device.update(
                                {"set_output_power": str(value).replace("W", "")}
                            )
                    elif key in ["power_unit"]:
                        device.update({"power_unit": str(value)})
                    elif key in ["status"]:
                        device.update({"status": str(value)})
                        # decode the status into a description
                        description = SolixDeviceStatus.unknown.name
                        for status in SolixDeviceStatus:
                            if str(value) == status.value:
                                description = status.name
                                break
                        device.update({"status_desc": description})
                    elif key in ["charging_status"]:
                        device.update({"charging_status": str(value)})
                        # decode the status into a description
                        description = SolarbankStatus.unknown.name
                        for status in SolarbankStatus:
                            if str(value) == status.value:
                                description = status.name
                                break
                        # check if battery has bypass during charge (if output during charge)
                        # NOTE: charging power may be updated after initial device details update
                        # NOTE: If status is 3=charging and larger than preset but nothing goes out, the charge priority is active (e.g. 0 Watt switch)
                        # This key can be passed separately, make sure the other values are looked up in passed data first, then in device details
                        preset = devData.get("set_load_power") or device(
                            "set_output_power"
                        )
                        out = devData.get("output_power") or device.get("output_power")
                        solar = devData.get("photovoltaic_power") or device.get(
                            "input_power"
                        )
                        if (
                            description == SolarbankStatus.charge.name
                            and preset is not None
                            and out is not None
                            and solar is not None
                        ):
                            with contextlib.suppress(ValueError):
                                if int(out) == 0 and int(solar) > int(preset):
                                    # Bypass but 0 W output must be active charge priority
                                    description = SolarbankStatus.charge_priority.name
                                elif int(out) > 0:
                                    # Charge with output must be bypass charging
                                    description = SolarbankStatus.charge_bypass.name
                        device.update({"charging_status_desc": description})
                    elif key in ["bws_surplus"]:
                        device.update({"bws_surplus": str(value)})
                    elif key in ["charge"]:
                        device.update({"charge": bool(value)})
                    elif key in ["auto_upgrade"]:
                        device.update({"auto_upgrade": bool(value)})
                    elif key in ["is_ota_update"]:
                        device.update({"is_ota_update": bool(value)})
                    elif (
                        key in ["power_cutoff", "output_cutoff_data"]
                        and str(value).isdigit()
                    ):
                        device.update({"power_cutoff": int(value)})
                    elif key in ["power_cutoff_data"] and value:
                        device.update({"power_cutoff_data": list(value)})
                    elif key in ["fittings"]:
                        # update nested dictionary
                        if "fittings" in device:
                            device["fittings"].update(dict(value))
                        else:
                            device["fittings"] = dict(value)
                    elif key in ["solar_info"] and isinstance(value, dict) and value:
                        # remove unnecessary keys from solar_info
                        keylist = value.keys()
                        for key in [
                            x
                            for x in ("brand_id", "model_img", "version", "ota_status")
                            if x in keylist
                        ]:
                            value.pop(key, None)
                        device.update({"solar_info": dict(value)})
                    elif key in ["solarbank_count"] and value:
                        device.update({"solarbank_count": value})
                    # schedule is currently a site wide setting. However, we save this with device details to retain info across site updates
                    # When individual device schedules are supported in future, this info is needed per device anyway
                    elif key in ["schedule"] and isinstance(value, dict):
                        device.update({"schedule": dict(value)})
                        # set default presets for no active schedule slot
                        cnt = device.get("solarbank_count", 0)
                        device.update(
                            {
                                "preset_system_output_power": SolixDefaults.PRESET_NOSCHEDULE,
                                "preset_allow_export": SolixDefaults.ALLOW_EXPORT,
                                "preset_charge_priority": SolixDefaults.CHARGE_PRIORITY_DEF,
                                "preset_power_mode": SolixDefaults.POWER_MODE
                                if cnt > 1
                                else None,
                                "preset_device_output_power": int(
                                    SolixDefaults.PRESET_NOSCHEDULE / cnt
                                )
                                if cnt > 1
                                else None,
                            }
                        )
                        # get actual presets from current slot
                        now = datetime.now().time().replace(microsecond=0)
                        # set now to new daytime if close to end of day
                        if now >= datetime.strptime("23:59:58", "%H:%M:%S").time():
                            now = datetime.strptime("00:00", "%H:%M").time()
                        for slot in value.get("ranges") or []:
                            with contextlib.suppress(ValueError):
                                start_time = datetime.strptime(
                                    slot.get("start_time") or "00:00", "%H:%M"
                                ).time()
                                end_time = slot.get("end_time") or "00:00"
                                # "24:00" format not supported in strptime
                                if end_time == "24:00":
                                    end_time = datetime.strptime(
                                        "23:59:59", "%H:%M:%S"
                                    ).time()
                                else:
                                    end_time = datetime.strptime(
                                        end_time, "%H:%M"
                                    ).time()
                                if start_time <= now < end_time:
                                    preset_power = (slot.get("appliance_loads") or [{}])[0].get("power")
                                    device.update(
                                        {
                                            "preset_system_output_power": preset_power,
                                            "preset_allow_export": slot.get("turn_on"),
                                            "preset_charge_priority": slot.get(
                                                "charge_priority"
                                            ),
                                        }
                                    )
                                    # add presets for dual solarbank setups, default to None if schedule does not support new keys yet
                                    power_mode = slot.get("power_setting_mode")
                                    dev_presets = slot.get("device_power_loads") or [{}]
                                    dev_power = next(
                                        iter(
                                            [
                                                d.get("power")
                                                for d in dev_presets
                                                if d.get("device_sn") == sn
                                            ]
                                        ),
                                        None,
                                    )
                                    if cnt > 1:
                                        # adjust device power value for default share which is always using 50%, also for single solarbank setups
                                        device.update(
                                            {
                                                "preset_power_mode": power_mode,
                                                "preset_device_output_power": dev_power,
                                            }
                                        )

                    # inverter specific keys
                    elif key in ["generate_power"]:
                        device.update({"generate_power": str(value)})

                    # generate extra values when certain conditions are met
                    if key in ["battery_power"] or calc_capacity:
                        # generate battery values when soc updated or device name changed or PN is known
                        if not (cap := device.get("battery_capacity")):
                            pn = device.get("device_pn") or ""
                            if hasattr(SolixDeviceCapacity, pn):
                                # get battery capacity from known PNs
                                cap = getattr(SolixDeviceCapacity, pn)
                            elif device.get("type") == SolixDeviceType.SOLARBANK.value:
                                # Derive battery capacity in Wh from latest solarbank name or alias if available
                                cap = (
                                    device.get("name", "")
                                    or devData.get("device_name", "")
                                    or device.get("alias", "")
                                ).replace("Solarbank E", "")
                        soc = devData.get("battery_power", "") or device.get(
                            "battery_soc", ""
                        )
                        # Calculate remaining energy in Wh and add values
                        if cap and soc and str(cap).isdigit() and str(soc).isdigit():
                            device.update(
                                {
                                    "battery_capacity": str(cap),
                                    "battery_energy": str(
                                        int(int(cap) * int(soc) / 100)
                                    ),
                                }
                            )
                except Exception as err:  # pylint: disable=broad-exception-caught  # noqa: BLE001
                    self._logger.error(
                        "%s occured when updating device details for key %s with value %s: %s",
                        type(err),
                        key,
                        value,
                        err,
                    )

            self.devices.update({str(sn): device})
        return sn

    def testDir(self, subfolder: str | None = None) -> str:
        """Get or set the subfolder for local API test files."""
        if not subfolder or subfolder == self._testdir:
            return self._testdir
        if not os.path.isdir(subfolder):
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
                _API_LOGIN,
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
        if endpoint != _API_LOGIN and (
            not self._loggedIn
            or (
                os.path.isfile(self._authFile)
                and self._authFileTime != os.path.getmtime(self._authFile)
            )
        ):
            await self.async_authenticate()

        url: str = f"{self._api_base}/{endpoint}"
        mergedHeaders = _API_HEADERS
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
        if endpoint == _API_LOGIN:
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

                if endpoint == _API_LOGIN:
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

    async def update_sites(self, fromFile: bool = False) -> dict:
        """Get the latest info for all accessible sites and update class site and device variables.

        Example data:
        {'efaca6b5-f4a0-e82e-3b2e-6b9cf90ded8c':
            {'site_info': {'site_id': 'efaca6b5-f4a0-e82e-3b2e-6b9cf90ded8c', 'site_name': 'BKW', 'site_img': '', 'device_type_list': [3], 'ms_type': 1, 'power_site_type': 2, 'is_allow_delete': True},
            'site_admin': True,
            'home_info': {'home_name': 'Home', 'home_img': '', 'charging_power': '0.00', 'power_unit': 'W'},
            'solar_list': [],
            'pps_info': {'pps_list': [], 'total_charging_power': '0.00', 'power_unit': 'W', 'total_battery_power': '0.00', 'updated_time': '', 'pps_status': 0},
            'statistics': [{'type': '1', 'total': '89.75', 'unit': 'kwh'}, {'type': '2', 'total': '89.48', 'unit': 'kg'}, {'type': '3', 'total': '35.90', 'unit': '€'}],
            'topology_type': '1',
            'solarbank_info': {'solarbank_list': [{'device_pn': 'A17C0', 'device_sn': '9JVB42LJK8J0P5RY', 'device_name': 'Solarbank E1600',
                'device_img': 'https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/e9478c2d-e665-4d84-95d7-dd4844f82055/20230719-144818.png',
                'battery_power': '75', 'bind_site_status': '', 'charging_power': '0', 'power_unit': 'W', 'charging_status': '2', 'status': '0', 'wireless_type': '1', 'main_version': '', 'photovoltaic_power': '0',
                'output_power': '0', 'create_time': 1695392386, 'set_load_power': ''}],
                'total_charging_power': '0', 'power_unit': 'W', 'charging_status': '0', 'total_battery_power': '0.00', 'updated_time': '2023-12-28 18:53:27', 'total_photovoltaic_power': '0', 'total_output_power': '0.00',
                'display_set_power': False},
            'retain_load': '0W',
            'updated_time': '01-01-0001 00:00:00',
            'power_site_type': 2,
            'site_id': 'efaca6b5-f4a0-e82e-3b2e-6b9cf90ded8c',
            'powerpanel_list': []}}
        """
        self._logger.debug("Updating Sites data")
        new_sites = {}
        self._logger.debug("Getting site list")
        sites = await self.get_site_list(fromFile=fromFile)
        self._site_devices = set()
        for site in sites.get("site_list", []):
            if myid := site.get("site_id"):
                # Update site info
                mysite = self.sites.get(myid, {})
                siteInfo = mysite.get("site_info", {})
                siteInfo.update(site)
                mysite.update(
                    {"type": SolixDeviceType.SYSTEM.value, "site_info": siteInfo}
                )
                admin = (
                    siteInfo.get("ms_type", 0) in [0, 1]
                )  # add boolean key to indicate whether user is site admin (ms_type 1 or not known) and can query device details
                mysite.update({"site_admin": admin})
                # Update scene info for site
                self._logger.debug("Getting scene info for site")
                scene = await self.get_scene_info(myid, fromFile=fromFile)
                mysite.update(scene)
                new_sites.update({myid: mysite})
                # Update device details from scene info
                sb_total_charge = (mysite.get("solarbank_info", {})).get(
                    "total_charging_power", ""
                )
                sb_total_output = (mysite.get("solarbank_info", {})).get(
                    "total_output_power", ""
                )
                sb_total_solar = (mysite.get("solarbank_info", {})).get(
                    "total_photovoltaic_power", ""
                )
                sb_total_charge_calc = 0
                sb_charges = {}
                sb_list = (mysite.get("solarbank_info", {})).get("solarbank_list", [])
                for index, solarbank in enumerate(sb_list):
                    # work around for device_name which is actually the device_alias in scene info
                    if "device_name" in solarbank:
                        # modify only a copy of the device dict to prevent changing the scene info dict
                        solarbank = dict(solarbank).copy()
                        solarbank.update({"alias_name": solarbank.pop("device_name")})
                    # work around for system and device output presets, which are not set correctly and cannot be queried with load schedule for shared accounts
                    if not str(solarbank.get("set_load_power")).isdigit():
                        total_preset = str(mysite.get("retain_load", "")).replace(
                            "W", ""
                        )
                        if total_preset.isdigit():
                            solarbank.update(
                                {
                                    "set_load_power": f"{(int(total_preset)/len(sb_list)):.0f}",
                                    "current_home_load": total_preset,
                                }
                            )
                    # Work around for weird charging power fields in SB totals and device list: They have same names, but completely different usage
                    # SB total charging power shows only power into the battery. At this time, charging power in device list seems to reflect the output power. This is seen for status 3
                    # SB total charging power show 0 when discharging, but then device charging power shows correct value. This is seen for status 2
                    # Conclusion: SB total charging power is correct total power INTO the batteries. When discharging it is 0
                    # Device list charging power is ONLY correct power OUT of the batteries. When charging it is 0 or shows the output power.
                    # Need to simplify this per device details and SB totals, will use positive value on both for charging power and negative for discharging power
                    # calculate estimate based on total for proportional split across available solarbanks and their calculated charge power
                    with contextlib.suppress(ValueError):
                        charge_calc = 0
                        power_in = int(solarbank.get("photovoltaic_power", ""))
                        power_out = int(solarbank.get("output_power", ""))
                        # power_charge = int(solarbank.get("charging_power", "")) # This value seems to reflect the output power, which is corect for status 2, but may be wrong for other states
                        charge_calc = power_in - power_out
                        solarbank["charging_power"] = str(
                            charge_calc
                        )  # allow negative values
                        sb_total_charge_calc += charge_calc
                    mysite["solarbank_info"]["solarbank_list"][index] = solarbank
                    new_sites.update({myid: mysite})
                    # add count of solarbanks to device details
                    sn = self._update_dev(
                        solarbank | {"solarbank_count": len(sb_list)},
                        devType=SolixDeviceType.SOLARBANK.value,
                        siteId=myid,
                        isAdmin=admin,
                    )
                    if sn:
                        self._site_devices.add(sn)
                        sb_charges[sn] = charge_calc
                        # as time progressed, update actual schedule slot presets from a cached schedule if available
                        if schedule := (self.devices.get(sn, {})).get("schedule"):
                            self._update_dev(
                                {
                                    "device_sn": sn,
                                    "schedule": schedule,
                                }
                            )
                # adjust calculated SB charge to match total
                if len(sb_charges) == len(sb_list) and str(sb_total_charge).isdigit():
                    sb_total_charge = int(sb_total_charge)
                    if sb_total_charge_calc < 0:
                        with contextlib.suppress(ValueError):
                            # discharging, adjust sb total charge value in scene info and allow negativ value to indicate discharge
                            sb_total_charge = float(sb_total_solar) - float(
                                sb_total_output
                            )
                            mysite["solarbank_info"]["total_charging_power"] = str(
                                sb_total_charge
                            )
                    for sn, charge in sb_charges.items():
                        self.devices[sn]["charging_power"] = str(
                            0
                            if sb_total_charge_calc == 0
                            else int(sb_total_charge / sb_total_charge_calc * charge)
                        )
                        # Update also the charge status description which may change after charging power correction
                        charge_status = self.devices[sn].get("charging_status")
                        if charge_status == SolarbankStatus.charge:
                            self._update_dev(
                                {
                                    "device_sn": sn,
                                    "charging_status": charge_status,
                                }
                            )
                # make sure to write back any changes to the solarbank info in sites dict
                new_sites.update({myid: mysite})

                for pps in (mysite.get("pps_info", {})).get("pps_list", []):
                    # work around for device_name which is actually the device_alias in scene info
                    if "device_name" in pps:
                        # modify only a copy of the device dict to prevent changing the scene info dict
                        pps = dict(pps).copy()
                        pps.update({"alias_name": pps.pop("device_name")})
                    sn = self._update_dev(
                        pps,
                        devType=SolixDeviceType.PPS.value,
                        siteId=myid,
                        isAdmin=admin,
                    )
                    if sn:
                        self._site_devices.add(sn)
                for solar in mysite.get("solar_list", []):
                    # work around for device_name which is actually the device_alias in scene info
                    if "device_name" in solar:
                        # modify only a copy of the device dict to prevent changing the scene info dict
                        solar = dict(solar).copy()
                        solar.update({"alias_name": solar.pop("device_name")})
                    sn = self._update_dev(
                        solar,
                        devType=SolixDeviceType.INVERTER.value,
                        siteId=myid,
                        isAdmin=admin,
                    )
                    if sn:
                        self._site_devices.add(sn)
                for powerpanel in mysite.get("powerpanel_list", []):
                    # work around for device_name which is actually the device_alias in scene info
                    if "device_name" in powerpanel:
                        # modify only a copy of the device dict to prevent changing the scene info dict
                        powerpanel = dict(powerpanel).copy()
                        powerpanel.update({"alias_name": powerpanel.pop("device_name")})
                    sn = self._update_dev(
                        powerpanel,
                        devType=SolixDeviceType.POWERPANEL.value,
                        siteId=myid,
                        isAdmin=admin,
                    )
                    if sn:
                        self._site_devices.add(sn)
        # Write back the updated sites
        self.sites = new_sites
        return self.sites

    async def update_site_details(
        self, fromFile: bool = False, exclude: set | None = None
    ) -> dict:
        """Get the latest updates for additional site related details updated less frequently.

        Most of theses requests return data only when user has admin rights for sites owning the devices.
        To limit API requests, this update site details method should be called less frequently than update site method,
        and it updates just the nested site_details dictionary in the sites dictionary.
        """
        # define excluded categories to skip for queries
        if not exclude:
            exclude = set()
        self._logger.debug("Updating Sites Details")
        # Fetch unread account messages once and put in site details for all sites
        self._logger.debug("Getting unread messages indicator")
        await self.get_message_unread(fromFile=fromFile)
        for site_id, site in self.sites.items():
            # Fetch details that only work for site admins
            if site.get("site_admin", False):
                # Fetch site price and CO2 settings
                if {ApiCategories.site_price} - exclude:
                    self._logger.debug("Getting price and CO2 settings for site")
                    await self.get_site_price(siteId=site_id, fromFile=fromFile)
        return self.sites

    async def update_device_details(
        self, fromFile: bool = False, exclude: set | None = None
    ) -> dict:
        """Get the latest updates for additional device info updated less frequently.

        Most of theses requests return data only when user has admin rights for sites owning the devices.
        To limit API requests, this update device details method should be called less frequently than update site method,
        which will also update most device details as found in the site data response.
        """
        # define excluded device types or categories to skip for queries
        if not exclude:
            exclude = set()
        self._logger.debug("Updating Device Details")
        # Fetch firmware version of device
        # This response will also contain unbound / standalone devices not added to a site
        self._logger.debug("Getting bind devices")
        await self.get_bind_devices(fromFile=fromFile)
        # Get the setting for effective automated FW upgrades
        if {ApiCategories.device_auto_upgrade} - exclude:
            self._logger.debug("Getting OTA settings")
            await self.get_auto_upgrade(fromFile=fromFile)
        # Fetch other relevant device information that requires site id and/or SN
        site_wifi: dict[str, list[dict | None]] = {}
        for sn, device in self.devices.items():
            site_id = device.get("site_id", "")
            dev_Type = device.get("type", "")

            # Fetch details that only work for site admins
            if device.get("is_admin", False) and site_id:
                # Fetch wifi networks and signal strength and map to usage of device
                if wifi_index := device.get("wireless_type", ""):
                    self._logger.debug(
                        "Getting wifi list of site for mapping to device"
                    )
                    if str(wifi_index).isdigit():
                        wifi_index = int(wifi_index)
                    else:
                        wifi_index = 0
                    # fetch site wifi list if not queried yet
                    if site_id not in site_wifi:
                        site_wifi[site_id] = (
                            await self.get_wifi_list(siteId=site_id, fromFile=fromFile)
                        ).get("wifi_info_list") or []
                    wifi_list = site_wifi.get(site_id, [{}])
                    if 0 < wifi_index <= len(wifi_list):
                        device.update(wifi_list[wifi_index - 1])

                # Fetch device type specific details, if device type not excluded

                if dev_Type in ({SolixDeviceType.SOLARBANK.value} - exclude):
                    # Fetch active Power Cutoff setting for solarbanks
                    if {ApiCategories.solarbank_cutoff} - exclude:
                        self._logger.debug("Getting Power Cutoff settings for device")
                        await self.get_power_cutoff(
                            siteId=site_id, deviceSn=sn, fromFile=fromFile
                        )
                    # Fetch available OTA update for solarbanks
                    self._logger.debug("Getting OTA update info for device")
                    await self.get_ota_update(deviceSn=sn, fromFile=fromFile)
                    # Fetch defined inverter details for solarbanks
                    if {ApiCategories.solarbank_solar_info} - exclude:
                        self._logger.debug("Getting inverter settings for device")
                        await self.get_solar_info(solarbankSn=sn, fromFile=fromFile)
                    # Fetch schedule for device types supporting it
                    self._logger.debug("Getting schedule details for device")
                    await self.get_device_load(
                        siteId=site_id, deviceSn=sn, fromFile=fromFile
                    )
                    # Fetch device fittings for device types supporting it
                    if {ApiCategories.solarbank_fittings} - exclude:
                        self._logger.debug("Getting fittings for device")
                        await self.get_device_fittings(
                            siteId=site_id, deviceSn=sn, fromFile=fromFile
                        )

                # update entry in devices
                self.devices.update({sn: device})

            # TODO(#0): Fetch other details of specific device types as known and relevant

        return self.devices

    async def update_device_energy(self, exclude: set | None = None) -> dict:
        """Get the energy statistics for given device types from today and yesterday.

        Yesterday energy will be queried only once if not available yet, but not updated in subsequent refreshes.
        Energy data can also be fetched by shared accounts.
        It was found that energy data is tracked only per site, but not individual devices even if a device SN parameter is required.
        """
        # define allowed device types to query, default to all energy data
        if not exclude:
            exclude = set()
        for sn, device in self.devices.items():
            site_id = device.get("site_id", "")
            dev_Type = device.get("type", "")
            queried_sites: dict = {}
            if (
                dev_Type in ({SolixDeviceType.SOLARBANK.value} - exclude)
                and {ApiCategories.solarbank_energy} - exclude
            ):
                # check if site was already queried for device
                if site_id in queried_sites:
                    # copy energy data returned for other device
                    self._logger.debug("Copying Energy details for device")
                    energy = queried_sites.get(site_id)
                else:
                    self._logger.debug("Getting Energy details for device")
                    energy = device.get("energy_details") or {}
                    today = datetime.today().strftime("%Y-%m-%d")
                    yesterday = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
                    # Fetch energy from today
                    data = await self.energy_daily(
                        siteId=site_id,
                        deviceSn=sn,
                        startDay=datetime.fromisoformat(today),
                        numDays=1,
                        dayTotals=True,
                    )
                    energy["today"] = data.get(today) or {}
                    if yesterday != (energy.get("last_period") or {}).get("date"):
                        # Fetch energy from previous day once
                        data = await self.energy_daily(
                            siteId=site_id,
                            deviceSn=sn,
                            startDay=datetime.fromisoformat(yesterday),
                            numDays=1,
                            dayTotals=True,
                        )
                        energy["last_period"] = data.get(yesterday) or {}
                    queried_sites[site_id] = energy
                device["energy_details"] = energy
                self.devices[sn] = device

    async def get_site_rules(self, fromFile: bool = False) -> dict:
        """Get the site rules supported by the api.

        Example data:
        {'rule_list': [
            {'power_site_type': 1, 'main_device_models': ['A5143'], 'device_models': ['A5143', 'A1771'], 'can_empty_site': False,
                'quantity_min_limit_map': {'A1771': 1, 'A5143': 1},'quantity_max_limit_map': {'A1771': 2, 'A5143': 1}},
            {'power_site_type': 2, 'main_device_models': ['A17C0'], 'device_models': ['A17C0', 'A5143', 'A1771'], 'can_empty_site': False,
                'quantity_min_limit_map': {'A17C0': 1}, 'quantity_max_limit_map': {'A1771': 2, 'A17C0': 2, 'A5143': 1}},
            {'power_site_type': 4, 'main_device_models': ['A17B1'], 'device_models': ['A17B1'], 'can_empty_site': True,
                'quantity_min_limit_map': None, 'quantity_max_limit_map': {'A17B1': 1}},
            {'power_site_type': 5, 'main_device_models': ['A17C1'], 'device_models': ['A17C1', 'A17X7'], 'can_empty_site': True,
                'quantity_min_limit_map': None, 'quantity_max_limit_map': {'A17C1': 1}},
            {'power_site_type': 6, 'main_device_models': ['A5341'], 'device_models': ['A5341', 'A5101', 'A5220'], 'can_empty_site': False,
                'quantity_min_limit_map': {'A5341': 1}, 'quantity_max_limit_map': {'A5341': 1}},
            {'power_site_type': 7, 'main_device_models': ['A5101'], 'device_models': ['A5101', 'A5220'], 'can_empty_site': False,
                'quantity_min_limit_map': {'A5101': 1}, 'quantity_max_limit_map': {'A5101': 6}},
            {'power_site_type': 8, 'main_device_models': ['A5102'], 'device_models': ['A5102', 'A5220'], 'can_empty_site': False,
                'quantity_min_limit_map': {'A5102': 1}, 'quantity_max_limit_map': {'A5102': 6}},
            {'power_site_type': 9, 'main_device_models': ['A5103'], 'device_models': ['A5103', 'A5220'], 'can_empty_site': False,
                'quantity_min_limit_map': {'A5103': 1}, 'quantity_max_limit_map': {'A5103': 6}}]}
        """
        if fromFile:
            resp = await self._loadFromFile(os.path.join(self._testdir, "site_rules.json"))
        else:
            resp = await self.request("post", _API_ENDPOINTS["site_rules"])
        return resp.get("data", {})

    async def get_site_list(self, fromFile: bool = False) -> dict:
        """Get the site list.

        Example data:
        {'site_list': [{'site_id': 'efaca6b5-f4a0-e82e-3b2e-6b9cf90ded8c', 'site_name': 'BKW', 'site_img': '', 'device_type_list': [3], 'ms_type': 2, 'power_site_type': 2, 'is_allow_delete': True}]}
        """
        if fromFile:
            resp = await self._loadFromFile(os.path.join(self._testdir, "site_list.json"))
        else:
            resp = await self.request("post", _API_ENDPOINTS["site_list"])
        return resp.get("data", {})

    async def get_scene_info(self, siteId: str, fromFile: bool = False) -> dict:
        """Get scene info. This can be queried for each siteId listed in the homepage info site_list. It shows also data for accounts that are only site members.

        Example data for provided site_id:
        {"home_info":{"home_name":"Home","home_img":"","charging_power":"0.00","power_unit":"W"},
        "solar_list":[],
        "pps_info":{"pps_list":[],"total_charging_power":"0.00","power_unit":"W","total_battery_power":"0.00","updated_time":"","pps_status":0},
        "statistics":[{"type":"1","total":"89.75","unit":"kwh"},{"type":"2","total":"89.48","unit":"kg"},{"type":"3","total":"35.90","unit":"€"}],
        "topology_type":"1","solarbank_info":{"solarbank_list":
            [{"device_pn":"A17C0","device_sn":"9JVB42LJK8J0P5RY","device_name":"Solarbank E1600",
                "device_img":"https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/e9478c2d-e665-4d84-95d7-dd4844f82055/20230719-144818.png",
                "battery_power":"75","bind_site_status":"","charging_power":"0","power_unit":"W","charging_status":"2","status":"0","wireless_type":"1","main_version":"","photovoltaic_power":"0",
                "output_power":"0","create_time":1695392386}],
            "total_charging_power":"0","power_unit":"W","charging_status":"0","total_battery_power":"0.00","updated_time":"2023-12-28 18:53:27","total_photovoltaic_power":"0","total_output_power":"0.00"},
        "retain_load":"0W","updated_time":"01-01-0001 00:00:00","power_site_type":2,"site_id":"efaca6b5-f4a0-e82e-3b2e-6b9cf90ded8c"}
        """
        data = {"site_id": siteId}
        if fromFile:
            resp = await self._loadFromFile(
                os.path.join(self._testdir, f"scene_{siteId}.json")
            )
        else:
            resp = await self.request("post", _API_ENDPOINTS["scene_info"], json=data)
        return resp.get("data", {})

    async def get_homepage(self, fromFile: bool = False) -> dict:
        """Get the latest homepage info.

        NOTE: This returns only data if the site is owned by the account. No data returned for site member accounts
        Example data:
        {"site_list":[{"site_id":"efaca6b5-f4a0-e82e-3b2e-6b9cf90ded8c","site_name":"BKW","site_img":"","device_type_list":[3],"ms_type":0,"power_site_type":0,"is_allow_delete":false}],
        "solar_list":[],"pps_list":[],
        "solarbank_list":[{"device_pn":"","device_sn":"9JVB42LJK8J0P5RY","device_name":"Solarbank E1600",
            "device_img":"https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/e9478c2d-e665-4d84-95d7-dd4844f82055/20230719-144818.png",
            "battery_power":"75","bind_site_status":"1","charging_power":"","power_unit":"","charging_status":"","status":"","wireless_type":"","main_version":"","photovoltaic_power":"","output_power":"","create_time":0}],
        "powerpanel_list":[]}
        """
        if fromFile:
            resp = await self._loadFromFile(os.path.join(self._testdir, "homepage.json"))
        else:
            resp = await self.request("post", _API_ENDPOINTS["homepage"])
        return resp.get("data", {})

    async def get_bind_devices(self, fromFile: bool = False) -> dict:
        """Get the bind device information, contains firmware level of devices.

        Example data:
        {"data": [{"device_sn":"9JVB42LJK8J0P5RY","product_code":"A17C0","bt_ble_id":"BC:A2:AF:C7:55:F9","bt_ble_mac":"BCA2AFC755F9","device_name":"Solarbank E1600","alias_name":"Solarbank E1600",
        "img_url":"https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/e9478c2d-e665-4d84-95d7-dd4844f82055/20230719-144818.png",
        "link_time":1695392302068,"wifi_online":false,"wifi_name":"","relate_type":["ble","wifi"],"charge":false,"bws_surplus":0,"device_sw_version":"v1.4.4","has_manual":false}]}
        """
        if fromFile:
            resp = await self._loadFromFile(os.path.join(self._testdir, "bind_devices.json"))
        else:
            resp = await self.request("post", _API_ENDPOINTS["bind_devices"])
        data = resp.get("data", {})
        active_devices = set()
        for device in data.get("data", []):
            if sn := self._update_dev(device):
                active_devices.add(sn)
        # recycle api device list and remove devices no longer used in sites or bind devices
        rem_devices = [
            dev
            for dev in self.devices
            if dev not in (self._site_devices | active_devices)
        ]
        for dev in rem_devices:
            self.devices.pop(dev, None)
        return data

    async def get_user_devices(self, fromFile: bool = False) -> dict:
        """Get device details of all devices owned by user.

        Example data: (Information is mostly empty when device is bound to site)
        {'solar_list': [], 'pps_list': [], 'solarbank_list': [{'device_pn': 'A17C0', 'device_sn': '9JVB42LJK8J0P5RY', 'device_name': 'Solarbank E1600',
        'device_img': 'https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/e9478c2d-e665-4d84-95d7-dd4844f82055/20230719-144818.png',
        'battery_power': '', 'bind_site_status': '1', 'charging_power': '', 'power_unit': '', 'charging_status': '', 'status': '', 'wireless_type': '1', 'main_version': '',
        'photovoltaic_power': '', 'output_power': '', 'create_time': 0}]}
        """
        if fromFile:
            resp = await self._loadFromFile(os.path.join(self._testdir, "user_devices.json"))
        else:
            resp = await self.request("post", _API_ENDPOINTS["user_devices"])
        return resp.get("data", {})

    async def get_charging_devices(self, fromFile: bool = False) -> dict:
        """Get the charging devices (Power stations?).

        Example data:
        {'device_list': None, 'guide_txt': ''}
        """
        if fromFile:
            resp = await self._loadFromFile(
                os.path.join(self._testdir, "charging_devices.json")
            )
        else:
            resp = await self.request("post", _API_ENDPOINTS["charging_devices"])
        return resp.get("data", {})

    async def get_solar_info(self, solarbankSn: str, fromFile: bool = False) -> dict:
        """Get the solar info that is condigured for a solarbank.

        Example data:
        {"brand_id": "3a9930f5-74ef-4e41-a797-04e6b33d3f0f","solar_brand": "ANKER","solar_model": "A5140","solar_sn": "","solar_model_name": "MI60 Microinverter"}
        """
        data = {"solarbank_sn": solarbankSn}
        if fromFile:
            resp = await self._loadFromFile(
                os.path.join(self._testdir, f"solar_info_{solarbankSn}.json")
            )
        else:
            resp = await self.request("post", _API_ENDPOINTS["solar_info"], json=data)
        data = resp.get("data", {})
        if data:
            self._update_dev({"device_sn": solarbankSn, "solar_info": data})
        return data

    async def get_compatible_info(
        self, solarbankSn: str, fromFile: bool = False
    ) -> dict:
        """Get the solar info and OTA processing info for a solarbank.

        Example data:
        {"ota_complete_status": 2,"process_skip_type": 1,"solar_info": {
            "solar_sn": "","solar_brand": "ANKER","solar_model": "A5140","brand_id": "3a9930f5-74ef-4e41-a797-04e6b33d3f0f",
            "model_img": "https://public-aiot-ore-qa.s3.us-west-2.amazonaws.com/product/870cd979-95d8-4cc1-89c4-04a26511c9b1/picl_A1771_normal.png",
            "version": "","ota_status": 1,"solar_model_name": "MI60 Microinverter"}
        """
        data = {"solarbank_sn": solarbankSn}
        if fromFile:
            resp = await self._loadFromFile(
                os.path.join(self._testdir, f"compatible_process_{solarbankSn}.json")
            )
        else:
            resp = await self.request(
                "post", _API_ENDPOINTS["compatible_process"], json=data
            )
        data = resp.get("data", {})
        if info := data.get("solar_info", {}):
            self._update_dev({"device_sn": solarbankSn, "solar_info": info})
        return data

    async def get_auto_upgrade(self, fromFile: bool = False) -> dict:
        """Get auto upgrade settings and devices enabled for auto upgrade.

        Example data:
        {'main_switch': True, 'device_list': [{'device_sn': '9JVB42LJK8J0P5RY', 'device_name': 'Solarbank E1600', 'auto_upgrade': True, 'alias_name': 'Solarbank E1600',
        'icon': 'https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/e9478c2d-e665-4d84-95d7-dd4844f82055/20230719-144818.png'}]}
        """
        if fromFile:
            resp = await self._loadFromFile(os.path.join(self._testdir, "auto_upgrade.json"))
        else:
            resp = await self.request("post", _API_ENDPOINTS["get_auto_upgrade"])
        data = resp.get("data", {})
        main = data.get("main_switch")
        devicelist = data.get("device_list", [])  # could be null for non owning account
        if not devicelist:
            devicelist = []
        for device in devicelist:
            dev_ota = device.get("auto_upgrade")
            if isinstance(dev_ota, bool):
                # update device setting based on main setting if available
                if isinstance(main, bool):
                    device.update({"auto_upgrade": main and dev_ota})
                self._update_dev(device)
        return data

    async def set_auto_upgrade(self, devices: dict[str, bool]) -> bool:
        """Set auto upgrade switches for given device dictonary.

        Example input:
        devices = {'9JVB42LJK8J0P5RY': True}
        The main switch must be set True if any device switch is set True. The main switch does not need to be changed to False if no device is True.
        But if main switch is set to False, all devices will automatically be set to False and individual setting is ignored by Api.
        """
        # get actual settings
        settings = await self.get_auto_upgrade()
        if (main_switch := settings.get("main_switch")) is None:
            return False
        dev_switches = {}
        main = None
        change_list = []
        for dev_setting in settings.get("device_list") or []:
            if (
                isinstance(dev_setting, dict)
                and (device_sn := dev_setting.get("device_sn"))
                and (dev_upgrade := dev_setting.get("auto_upgrade")) is not None
            ):
                dev_switches[device_sn] = dev_upgrade
        # Loop through provided device list and compose the request data device list that needs to be send
        for sn, upgrade in devices.items():
            if sn in dev_switches:
                if upgrade != dev_switches[sn]:
                    change_list.append({"device_sn": sn, "auto_upgrade": upgrade})
                    if upgrade:
                        main = True

        if change_list:
            # json example for endpoint
            # {"main_switch": False, "device_list": [{"device_sn": "9JVB42LJK8J0P5RY","auto_upgrade": True}]}
            data = {
                "main_switch": main if main is not None else main_switch,
                "device_list": change_list,
            }
            # Make the Api call and check for return code
            code = (
                await self.request(
                    "post", _API_ENDPOINTS["set_auto_upgrade"], json=data
                )
            ).get("code")
            if not isinstance(code, int) or int(code) != 0:
                return False
            # update the data in api dict
            await self.get_auto_upgrade()

        return True

    async def get_wifi_list(self, siteId: str, fromFile: bool = False) -> dict:
        """Get the wifi list.

        Example data:
        {'wifi_info_list': [{'wifi_name': 'wifi-network-1', 'wifi_signal': '100'}]}
        """
        data = {"site_id": siteId}
        if fromFile:
            resp = await self._loadFromFile(
                os.path.join(self._testdir, f"wifi_list_{siteId}.json")
            )
        else:
            resp = await self.request("post", _API_ENDPOINTS["wifi_list"], json=data)
        return resp.get("data", {})

    async def get_power_cutoff(
        self, deviceSn: str, siteId: str = "", fromFile: bool = False
    ) -> dict:
        """Get power cut off settings.

        Example data:
        {'power_cutoff_data': [
        {'id': 1, 'is_selected': 1, 'output_cutoff_data': 10, 'lowpower_input_data': 5, 'input_cutoff_data': 10},
        {'id': 2, 'is_selected': 0, 'output_cutoff_data': 5, 'lowpower_input_data': 4, 'input_cutoff_data': 5}]}
        """
        data = {"site_id": siteId, "device_sn": deviceSn}
        if fromFile:
            resp = await self._loadFromFile(
                os.path.join(self._testdir, f"power_cutoff_{deviceSn}.json")
            )
        else:
            resp = await self.request("post", _API_ENDPOINTS["get_cutoff"], json=data)
        data = resp.get("data", {})
        # add whole list to device details to provide option selection capabilities
        details = {
            "device_sn": deviceSn,
            "power_cutoff_data": data.get("power_cutoff_data") or [],
        }
        for setting in data.get("power_cutoff_data") or []:
            if (
                int(setting.get("is_selected", 0)) > 0
                and int(setting.get("output_cutoff_data", 0)) > 0
            ):
                details.update(
                    {
                        "power_cutoff": int(setting.get("output_cutoff_data")),
                    }
                )
        self._update_dev(details)
        return data

    async def set_power_cutoff(self, deviceSn: str, setId: int) -> bool:
        """Set power cut off settings.

        Example input:
        {'device_sn': '9JVB42LJK8J0P5RY', 'cutoff_data_id': 1}
        The id must be one of the ids listed with the get_power_cutoff endpoint
        """
        data = {
            "device_sn": deviceSn,
            "cutoff_data_id": setId,
        }
        # Make the Api call and check for return code
        code = (
            await self.request("post", _API_ENDPOINTS["set_cutoff"], json=data)
        ).get("code")
        if not isinstance(code, int) or int(code) != 0:
            return False
        # update the data in api dict
        await self.get_power_cutoff(deviceSn=deviceSn)
        return True

    async def get_site_price(self, siteId: str, fromFile: bool = False) -> dict:
        """Get the power price set for the site.

        Example data:
        {"site_id": "efaca6b5-f4a0-e82e-3b2e-6b9cf90ded8c","price": 0.4,"site_co2": 0,"site_price_unit": "\u20ac"}
        """
        data = {"site_id": siteId}
        if fromFile:
            resp = await self._loadFromFile(
                os.path.join(self._testdir, f"price_{siteId}.json")
            )
        else:
            resp = await self.request(
                "post", _API_ENDPOINTS["get_site_price"], json=data
            )
        data = resp.get("data", {})
        # update site details in sites dict
        details = data.copy()
        if "site_id" in details:
            details.pop("site_id")
        self._update_site(siteId, details)
        return data

    async def set_site_price(
        self,
        siteId: str,
        price: float | None = None,
        unit: str | None = None,
        co2: float | None = None,
    ) -> bool:
        """Set the power price, the unit and/or CO2 for a site.

        Example input:
        {"site_id": 'efaca6b5-f4a0-e82e-3b2e-6b9cf90ded8c', "price": 0.325, "site_price_unit": "\u20ac", "site_co2": 0}
        The id must be one of the ids listed with the get_power_cutoff endpoint
        """
        # First get the old settings if only single setting should be updated
        details = {}
        if siteId in self.sites:
            details = (self.sites.get(siteId) or {}).get("site_details") or {}
        new_price = details.get("price") if price is None else price
        new_unit = details.get("site_price_unit") if unit is None else unit
        new_co2 = details.get("site_co2") if co2 is None else co2
        data = {}
        # Need to query old setting to avoid changing them if parameter not provided
        if new_price is None or new_unit is None or new_co2 is None:
            data = await self.get_site_price(siteId=siteId)
            if new_price is not None:
                data["price"] = new_price
            if new_unit is not None:
                data["site_price_unit"] = new_unit
            if new_co2 is not None:
                data["site_co2"] = new_co2
        else:
            data.update(
                {
                    "site_id": siteId,
                    "price": new_price,
                    "site_price_unit": new_unit,
                    "site_co2": new_co2,
                }
            )
        # Make the Api call and check for return code
        code = (
            await self.request("post", _API_ENDPOINTS["update_site_price"], json=data)
        ).get("code")
        if not isinstance(code, int) or int(code) != 0:
            return False
        # update the data in api dict
        await self.get_site_price(siteId=siteId)
        return True

    async def get_device_load(
        self, siteId: str, deviceSn: str, fromFile: bool = False
    ) -> dict:
        r"""Get device load settings.

        Example data:
        {"site_id": "efaca6b5-f4a0-e82e-3b2e-6b9cf90ded8c",
        "home_load_data": "{\"ranges\":[
            {\"id\":0,\"start_time\":\"00:00\",\"end_time\":\"08:30\",\"turn_on\":true,\"appliance_loads\":[{\"id\":0,\"name\":\"Benutzerdefiniert\",\"power\":300,\"number\":1}],\"charge_priority\":80},
            {\"id\":0,\"start_time\":\"08:30\",\"end_time\":\"17:00\",\"turn_on\":false,\"appliance_loads\":[{\"id\":0,\"name\":\"Benutzerdefiniert\",\"power\":100,\"number\":1}],\"charge_priority\":80},
            {\"id\":0,\"start_time\":\"17:00\",\"end_time\":\"24:00\",\"turn_on\":true,\"appliance_loads\":[{\"id\":0,\"name\":\"Benutzerdefiniert\",\"power\":300,\"number\":1}],\"charge_priority\":0}],
            \"min_load\":100,\"max_load\":800,\"step\":0,\"is_charge_priority\":0,\"default_charge_priority\":0,\"is_zero_output_tips\":1}",
        "current_home_load": "300W","parallel_home_load": "","parallel_display": false}
        """
        data = {"site_id": siteId, "device_sn": deviceSn}
        if fromFile:
            resp = await self._loadFromFile(
                os.path.join(self._testdir, f"device_load_{deviceSn}.json")
            )
        else:
            resp = await self.request(
                "post", _API_ENDPOINTS["get_device_load"], json=data
            )
        # The home_load_data is provided as string instead of object...Convert into object for proper handling
        # It must be converted back to a string when passing this as input to set home load
        string_data = (resp.get("data") or {}).get("home_load_data") or {}
        if isinstance(string_data, str):
            resp["data"].update({"home_load_data": json.loads(string_data)})
        data = resp.get("data") or {}
        # update schedule also for all device serials found in schedule
        schedule = data.get("home_load_data") or {}
        dev_serials = []
        for slot in schedule.get("ranges") or []:
            for dev in slot.get("device_power_loads") or []:
                if (sn := dev.get("device_sn")) and sn not in dev_serials:
                    dev_serials.append(sn)
        # add the given serial to list if not existing yet
        if deviceSn and deviceSn not in dev_serials:
            dev_serials.append(deviceSn)
        for sn in dev_serials:
            self._update_dev(
                {
                    "device_sn": sn,
                    "schedule": schedule,
                    "current_home_load": data.get("current_home_load") or "",
                    "parallel_home_load": data.get("parallel_home_load") or "",
                }
            )
        return data

    async def set_device_load(
        self,
        siteId: str,
        deviceSn: str,
        loadData: dict,
    ) -> bool:
        """Set device home load (e.g. solarbank schedule).

        Example input for system with single solarbank:
        {'site_id': 'efaca6b5-f4a0-e82e-3b2e-6b9cf90ded8c', 'device_sn': '9JVB42LJK8J0P5RY',
        'home_load_data': '{"ranges":['
            '{"id":0,"start_time":"00:00","end_time":"06:30","turn_on":true,"appliance_loads":[{"id":0,"name":"Benutzerdefiniert","power":300,"number":1}],'
            '"charge_priority":0,"power_setting_mode":1,"device_power_loads":[{"device_sn":"9JVB42LJK8J0P5RY","power":150}]},'
            '{"id":0,"start_time":"07:30","end_time":"18:00","turn_on":false,"appliance_loads":[{"id":0,"name":"Benutzerdefiniert","power":100,"number":1}],'
            '"charge_priority":80,"power_setting_mode":1,"device_power_loads":[{"device_sn":"9JVB42LJK8J0P5RY","power":50}]},'
            '{"id":0,"start_time":"18:00","end_time":"24:00","turn_on":true,"appliance_loads":[{"id":0,"name":"Benutzerdefiniert","power":300,"number":1}],'
            '"charge_priority":0,"power_setting_mode":1,"device_power_loads":[{"device_sn":"9JVB42LJK8J0P5RY","power":150}]}],'
            '"min_load":100,"max_load":800,"step":0,"is_charge_priority":0,"default_charge_priority":0,"is_zero_output_tips":1,"display_advanced_mode":0,"advanced_mode_min_load":0}'
        }
        Attention: This method and endpoint actually accepts the input data, but does not change anything on the solarbank.
        The set_device_parm endpoint may have to be used. Eventually this method is used for Solarbank 2 since that will use a different schedule structure?
        """
        data = {
            "site_id": siteId,
            "device_sn": deviceSn,
            "home_load_data": json.dumps(loadData),
        }
        # Make the Api call and check for return code
        code = (
            await self.request("post", _API_ENDPOINTS["set_device_load"], json=data)
        ).get("code")
        if not isinstance(code, int) or int(code) != 0:
            return False
        # update the data in api dict
        await self.get_device_load(siteId=siteId, deviceSn=deviceSn)
        return True

    async def get_device_parm(
        self,
        siteId: str,
        paramType: str = SolixParmType.SOLARBANK_SCHEDULE.value,
        deviceSn: str | None = None,
        fromFile: bool = False,
    ) -> dict:
        r"""Get device parameters (e.g. solarbank schedule). This can be queried for each siteId listed in the homepage info site_list. The paramType is always 4, but can be modified if necessary.

        Example data for provided site_id:
        {"param_data": "{\"ranges\":[
            {\"id\":0,\"start_time\":\"00:00\",\"end_time\":\"08:30\",\"turn_on\":true,\"appliance_loads\":[{\"id\":0,\"name\":\"Benutzerdefiniert\",\"power\":300,\"number\":1}],\"charge_priority\":80},
            {\"id\":0,\"start_time\":\"08:30\",\"end_time\":\"17:00\",\"turn_on\":false,\"appliance_loads\":[{\"id\":0,\"name\":\"Benutzerdefiniert\",\"power\":100,\"number\":1}],\"charge_priority\":80},
            {\"id\":0,\"start_time\":\"17:00\",\"end_time\":\"24:00\",\"turn_on\":true,\"appliance_loads\":[{\"id\":0,\"name\":\"Benutzerdefiniert\",\"power\":300,\"number\":1}],\"charge_priority\":0}],
            \"min_load\":100,\"max_load\":800,\"step\":0,\"is_charge_priority\":0,\"default_charge_priority\":0,\"is_zero_output_tips\":1}"}
        """
        data = {"site_id": siteId, "param_type": paramType}
        if fromFile:
            resp = await self._loadFromFile(
                os.path.join(self._testdir, f"device_parm_{siteId}.json")
            )
        else:
            resp = await self.request(
                "post", _API_ENDPOINTS["get_device_parm"], json=data
            )
        # The home_load_data is provided as string instead of object...Convert into object for proper handling
        # It must be converted back to a string when passing this as input to set home load
        string_data = (resp.get("data", {})).get("param_data", {})
        if isinstance(string_data, str):
            resp["data"].update({"param_data": json.loads(string_data)})

        # update api device dict with latest data if optional device SN was provided, e.g. when called by set_device_parm for device details update
        data = resp.get("data") or {}
        # update schedule also for all device serials found in schedule
        schedule = data.get("param_data") or {}
        dev_serials = []
        for slot in schedule.get("ranges") or []:
            for dev in slot.get("device_power_loads") or []:
                if (sn := dev.get("device_sn")) and sn not in dev_serials:
                    dev_serials.append(sn)
        # add the given serial to list if not existing yet
        if deviceSn and deviceSn not in dev_serials:
            dev_serials.append(deviceSn)
        for sn in dev_serials:
            self._update_dev(
                {
                    "device_sn": sn,
                    "schedule": schedule,
                    "current_home_load": data.get("current_home_load") or "",
                    "parallel_home_load": data.get("parallel_home_load") or "",
                }
            )
        return data

    async def set_device_parm(
        self,
        siteId: str,
        paramData: dict,
        paramType: str = SolixParmType.SOLARBANK_SCHEDULE.value,
        command: int = 17,
        deviceSn: str | None = None,
    ) -> bool:
        """Set device parameters (e.g. solarbank schedule).

        command: Must be 17 for solarbank schedule.
        paramType: was always string "4"
        Example paramData:
        {"param_data": '{"ranges":['
            '{"id":0,"start_time":"00:00","end_time":"08:30","turn_on":true,"appliance_loads":[{"id":0,"name":"Benutzerdefiniert","power":300,"number":1}],"charge_priority":80},'
            '{"id":0,"start_time":"08:30","end_time":"17:00","turn_on":false,"appliance_loads":[{"id":0,"name":"Benutzerdefiniert","power":100,"number":1}],"charge_priority":80},'
            '{"id":0,"start_time":"17:00","end_time":"24:00","turn_on":true,"appliance_loads":[{"id":0,"name":"Benutzerdefiniert","power":300,"number":1}],"charge_priority":0}],'
        '"min_load":100,"max_load":800,"step":0,"is_charge_priority":0,default_charge_priority":0}}'
        """
        data = {
            "site_id": siteId,
            "param_type": paramType,
            "cmd": command,
            "param_data": json.dumps(paramData),  # Must be string type
        }
        code = (
            await self.request("post", _API_ENDPOINTS["set_device_parm"], json=data)
        ).get("code")
        if not isinstance(code, int) or int(code) != 0:
            return False
        # update the data in api dict
        await self.get_device_parm(siteId=siteId, deviceSn=deviceSn)
        return True

    async def set_home_load(  # noqa: C901
        self,
        siteId: str,
        deviceSn: str,
        all_day: bool = False,
        preset: int | None = None,
        dev_preset: int | None = None,
        export: bool | None = None,
        charge_prio: int | None = None,
        set_slot: SolarbankTimeslot | None = None,
        insert_slot: SolarbankTimeslot | None = None,
        test_schedule: dict
        | None = None,  # used only for testing instead of real schedule
        test_count: int
        | None = None,  # used only for testing instead of real solarbank count
    ) -> bool | dict:
        """Set the home load parameters for a given site id and device for actual or all slots in the existing schedule.

        If no time slot is defined for current time, a new slot will be inserted for the gap. This will result in full day definition when no slot is defined.
        Optionally when set_slot SolarbankTimeslot is provided, the given slot will replace the existing schedule completely.
        When insert_slot SolarbankTimeslot is provided, the given slot will be incoorporated into existing schedule. Adjacent overlapping slot times will be updated and overlayed slots will be replaced.

        Example schedules for Solarbank as provided via Api:
        {"ranges":[
            {"id":0,"start_time":"00:00","end_time":"08:30","turn_on":true,"appliance_loads":[{"id":0,"name":"Benutzerdefiniert","power":300,"number":1}],"charge_priority":80},
            {"id":0,"start_time":"08:30","end_time":"17:00","turn_on":false,"appliance_loads":[{"id":0,"name":"Benutzerdefiniert","power":100,"number":1}],"charge_priority":80},
            {"id":0,"start_time":"17:00","end_time":"24:00","turn_on":true,"appliance_loads":[{"id":0,"name":"Benutzerdefiniert","power":300,"number":1}],"charge_priority":0}],
        "min_load":100,"max_load":800,"step":0,"is_charge_priority":0,default_charge_priority":0}

        Newer ranges structure with individual device power loads:
        {"ranges":[
            {"id":0,"start_time":"00:00","end_time":"08:00","turn_on":true,"appliance_loads":[{"id":0,"name":"Custom","power":270,"number":1}],"charge_priority":10,
                "power_setting_mode":1,"device_power_loads":[{"device_sn":"W8Z0AY4TF8L03KMS","power":135},{"device_sn":"XGR9TZEI1N9OO8BN","power":135}]},
            {"id":0,"start_time":"08:00","end_time":"24:00","turn_on":true,"appliance_loads":[{"id":0,"name":"Custom","power":300,"number":1}],"charge_priority":10,
                "power_setting_mode":2,"device_power_loads":[{"device_sn":"W8Z0AY4TF8L03KMS","power":100},{"device_sn":"XGR9TZEI1N9OO8BN","power":200}]}],
        "min_load":100,"max_load":800,"step":0,"is_charge_priority":1,"default_charge_priority":80,"is_zero_output_tips":0,"display_advanced_mode":1,"advanced_mode_min_load":50}
        """
        # fast quit if nothing to change
        charge_prio = (
            int(charge_prio)
            if str(charge_prio).isdigit() or isinstance(charge_prio, int | float)
            else None
        )
        preset = (
            int(preset)
            if str(preset).isdigit() or isinstance(preset, int | float)
            else None
        )
        dev_preset = (
            int(dev_preset)
            if str(dev_preset).isdigit() or isinstance(dev_preset, int | float)
            else None
        )
        if (
            preset is None
            and dev_preset is None
            and export is None
            and charge_prio is None
            and set_slot is None
            and insert_slot is None
        ):
            return False
        # set flag for required current parameter update
        pending_now_update = bool(set_slot is None and insert_slot is None)
        # obtain actual device schedule from internal dict or fetch via api
        if test_schedule is not None:
            schedule = test_schedule
        elif not (schedule := (self.devices.get(deviceSn) or {}).get("schedule") or {}):
            schedule = (
                await self.get_device_load(siteId=siteId, deviceSn=deviceSn)
            ).get("home_load_data") or {}
        ranges = schedule.get("ranges") or []
        # get appliance load name from first existing slot to avoid mixture
        # NOTE: The solarbank may behave weird if a mixture is found or the name does not match with some internal settings
        # The name cannot be queried, but seems to be 'custom' by default. However, the mobile app translates it to whather language is defined in the App
        appliance_name = None
        pending_insert = False
        sb_count = 0
        if len(ranges) > 0:
            appliance_name = (ranges[0].get("appliance_loads") or [{}])[0].get("name")
            # default to single solarbank if schedule does not include device parms yet (old firmware?)
            sb_count = len(ranges[0].get("device_power_loads") or [{}])
            if insert_slot:
                # set flag for pending insert slot
                pending_insert = True
        elif insert_slot:
            # use insert_slot for set_slot to define a single new slot when no slots exist
            set_slot = insert_slot
        # try to update solarbank count from Api dict if no schedule defined
        if sb_count == 0 and not (
            sb_count := (self.devices.get(deviceSn) or {}).get("solarbank_count")
        ):
            sb_count = 1
        if test_count is not None and isinstance(test_count, int):
            sb_count = test_count
        # get appliance and device limits based on number of solar banks
        if (min_load := str(schedule.get("min_load"))).isdigit():
            # min_load = int(min_load)
            # Allow lower min setting as defined by API minimum. This however may be ignored if outsite of appliance defined slot boundaries.
            min_load = SolixDefaults.PRESET_MIN
        else:
            min_load = SolixDefaults.PRESET_MIN
        if (max_load := str(schedule.get("max_load"))).isdigit():
            max_load = int(max_load)
        else:
            max_load = SolixDefaults.PRESET_MAX
        # adjust appliance max limit based on number of solar banks
        max_load = int(max_load * sb_count)
        if (min_load_dev := str(schedule.get("advanced_mode_min_load"))).isdigit():
            min_load_dev = int(min_load_dev)
        else:
            min_load_dev = int(SolixDefaults.PRESET_MIN / 2)
        # max load of device is not specified separately, use appliance default
        max_load_dev = SolixDefaults.PRESET_MAX
        # verify if and which power mode to be considered
        # If only appliance preset provided, always use normal power mode. The device presets must not be specified in schedule, default of 50% share will be applied automatically
        # If device preset provided, always use advanced power mode if supported by existing schedule structure and adjust appliance load. Fall back to legacy appliance load usage
        # If appliance and device preset provided, always use advanced power mode if supported by existing schedule structure and adjust other device load. Fall back to legacy appliance load usage
        # If neither appliance nor device preset provided, leave power mode unchanged. Legacy mode will be used with default 50% share when default applicane load must be set
        if sb_count > 1:
            if (
                dev_preset is not None
                or (insert_slot and insert_slot.device_load is not None)
                or (set_slot and set_slot.device_load is not None)
            ):
                power_mode = SolarbankPowerMode.advanced.value
                # ensure any provided device load is within limits
                if dev_preset is not None:
                    dev_preset = min(max(dev_preset, min_load_dev), max_load_dev)
                if insert_slot and insert_slot.device_load is not None:
                    insert_slot.device_load = min(
                        max(insert_slot.device_load, min_load_dev), max_load_dev
                    )
                if set_slot and set_slot.device_load is not None:
                    set_slot.device_load = min(
                        max(set_slot.device_load, min_load_dev), max_load_dev
                    )
            elif (
                preset is not None
                or (insert_slot and insert_slot.appliance_load is not None)
                or (set_slot and set_slot.appliance_load is not None)
            ):
                power_mode = SolarbankPowerMode.normal.value
            else:
                power_mode = None
        else:
            power_mode = None
            # For single solarbank systems, use a given device load as appliance load if no appliance load provided. Ignore device loads otherwise
            if dev_preset is not None:
                preset = dev_preset if preset is None else preset
                dev_preset = None
            if insert_slot and insert_slot.device_load is not None:
                insert_slot.appliance_load = (
                    insert_slot.device_load
                    if insert_slot.appliance_load is None
                    else insert_slot.appliance_load
                )
                insert_slot.device_load = None
            if set_slot and set_slot.device_load is not None:
                set_slot.appliance_load = (
                    set_slot.device_load
                    if set_slot.appliance_load is None
                    else set_slot.appliance_load
                )
                set_slot.device_load = None
        # Adjust provided appliance limits
        # appliance limits depend on device load setting and other device setting. Must be reduced for individual slots if necessary
        if preset is not None:
            preset = min(max(preset, min_load), max_load)
        if insert_slot and insert_slot.appliance_load is not None:
            insert_slot.appliance_load = min(
                max(insert_slot.appliance_load, min_load), max_load
            )
        if set_slot and set_slot.appliance_load is not None:
            set_slot.appliance_load = min(
                max(set_slot.appliance_load, min_load), max_load
            )

        new_ranges = []
        # update individual values in current slot or insert SolarbankTimeslot and adjust adjacent slots
        if not set_slot:
            now = datetime.now().time().replace(microsecond=0)
            last_time = datetime.strptime("00:00", "%H:%M").time()
            # set now to new daytime if close to end of day to determine which slot to modify
            if now >= datetime.strptime("23:59:58", "%H:%M:%S").time():
                now = datetime.strptime("00:00", "%H:%M").time()
            next_start = None
            split_slot = {}
            for idx, slot in enumerate(ranges, start=1):
                with contextlib.suppress(ValueError):
                    start_time = datetime.strptime(
                        slot.get("start_time") or "00:00", "%H:%M"
                    ).time()
                    # "24:00" format not supported in strptime
                    end_time = datetime.strptime(
                        (
                            str(slot.get("end_time") or "00:00").replace(
                                "24:00", "23:59"
                            )
                        ),
                        "%H:%M",
                    ).time()
                    # check slot timings to update current, or insert new and modify adjacent slots
                    insert = {}

                    # Check if parameter update required for current time but it falls into gap of no defined slot.
                    # Create insert slot for the gap and add before or after current slot at the end of the current slot checks/modifications required for allday usage
                    if (
                        not insert_slot
                        and pending_now_update
                        and (
                            last_time <= now < start_time
                            or (idx == len(ranges) and now >= end_time)
                        )
                    ):
                        # Use daily end time if now after last slot
                        insert = copy.deepcopy(slot)
                        insert.update(
                            {
                                "start_time": last_time.isoformat(timespec="minutes")
                                if now < start_time
                                else end_time.isoformat(timespec="minutes")
                            }
                        )
                        insert.update(
                            {
                                "end_time": (
                                    start_time.isoformat(timespec="minutes")
                                ).replace("23:59", "24:00")
                                if now < start_time
                                else "24:00"
                            }
                        )
                        # adjust appliance load depending on device load preset and ensure appliance load is consistent with device load min/max values
                        appliance_load = (
                            SolixDefaults.PRESET_DEF
                            if preset is None and dev_preset is None
                            else (dev_preset * sb_count)
                            if preset is None
                            else preset
                            if dev_preset is None
                            or power_mode is None
                            or "power_setting_mode" not in insert
                            else max(
                                min(
                                    preset,
                                    dev_preset + max_load_dev * (sb_count - 1),
                                ),
                                dev_preset + min_load_dev * (sb_count - 1),
                            )
                        )
                        (insert.get("appliance_loads") or [{}])[0].update(
                            {
                                "power": min(
                                    max(
                                        int(appliance_load),
                                        min_load,
                                    ),
                                    max_load,
                                ),
                            }
                        )
                        # optional advanced power mode settings if supported by schedule
                        if "power_setting_mode" in insert and power_mode is not None:
                            insert.update({"power_setting_mode": power_mode})
                            if (
                                power_mode == SolarbankPowerMode.advanced.value
                                and dev_preset is not None
                            ):
                                for dev in insert.get("device_power_loads") or []:
                                    if (
                                        isinstance(dev, dict)
                                        and dev.get("device_sn") == deviceSn
                                    ):
                                        dev.update({"power": int(dev_preset)})
                                    elif isinstance(dev, dict):
                                        # other solarbanks get the difference equally shared
                                        dev.update(
                                            {
                                                "power": int(
                                                    (appliance_load - dev_preset)
                                                    / (sb_count - 1)
                                                ),
                                            }
                                        )
                        insert.update(
                            {
                                "turn_on": SolixDefaults.ALLOW_EXPORT
                                if export is None
                                else export
                            }
                        )
                        insert.update(
                            {
                                "charge_priority": min(
                                    max(
                                        int(
                                            SolixDefaults.CHARGE_PRIORITY_DEF
                                            if charge_prio is None
                                            else charge_prio
                                        ),
                                        SolixDefaults.CHARGE_PRIORITY_MIN,
                                    ),
                                    SolixDefaults.CHARGE_PRIORITY_MAX,
                                )
                            }
                        )

                        # if gap is before current slot, insert now
                        if now < start_time:
                            new_ranges.append(insert)
                            last_time = start_time
                            insert = {}

                    if pending_insert and (
                        insert_slot.start_time.time() <= start_time
                        or idx == len(ranges)
                    ):
                        # copy slot, update and insert the new slot
                        overwrite = (
                            insert_slot.start_time.time() != start_time
                            and insert_slot.end_time.time() != end_time
                        )
                        # re-use old slot parms if insert slot has not defined optional parms
                        insert = copy.deepcopy(slot)
                        insert.update(
                            {
                                "start_time": datetime.strftime(
                                    insert_slot.start_time, "%H:%M"
                                )
                            }
                        )
                        insert.update(
                            {
                                "end_time": datetime.strftime(
                                    insert_slot.end_time, "%H:%M"
                                ).replace("23:59", "24:00")
                            }
                        )
                        # reuse old appliance load if not overwritten
                        if insert_slot.appliance_load is None and not overwrite:
                            insert_slot.appliance_load = (
                                insert.get("appliance_loads") or [{}]
                            )[0].get("power")
                            # reuse an active advanced power mode setting
                            if (
                                insert.get("power_setting_mode")
                                == SolarbankPowerMode.advanced.value
                                and insert_slot.device_load is None
                            ):
                                insert_slot.device_load = next(
                                    iter(
                                        [
                                            dev.get("power")
                                            for dev in insert.get("device_power_loads")
                                            or []
                                            if isinstance(dev, dict)
                                            and dev.get("device_sn") == deviceSn
                                        ]
                                    ),
                                    None,
                                )
                                if insert_slot.device_load is not None:
                                    power_mode = SolarbankPowerMode.advanced.value
                            elif isinstance(insert_slot.device_load, int | float):
                                # correct appliance load with other device loads and new device load
                                insert_slot.appliance_load = (
                                    insert_slot.device_load
                                    + sum(
                                        [
                                            dev.get("power")
                                            for dev in (
                                                insert.get("device_power_loads") or []
                                            )
                                            if dev.get("device_sn") != deviceSn
                                        ]
                                    )
                                )
                        # adjust appliance load depending on device load preset and ensure appliance load is consistent with device load min/max values
                        insert_slot.appliance_load = (
                            SolixDefaults.PRESET_DEF
                            if insert_slot.appliance_load is None
                            and insert_slot.device_load is None
                            else (insert_slot.device_load * sb_count)
                            if insert_slot.appliance_load is None
                            else insert_slot.appliance_load
                            if insert_slot.device_load is None
                            or power_mode is None
                            or "power_setting_mode" not in insert
                            else max(
                                min(
                                    insert_slot.appliance_load,
                                    insert_slot.device_load
                                    + max_load_dev * (sb_count - 1),
                                ),
                                insert_slot.device_load + min_load_dev * (sb_count - 1),
                            )
                        )
                        if insert_slot.appliance_load is not None:
                            insert_slot.appliance_load = min(
                                max(insert_slot.appliance_load, min_load), max_load
                            )
                        if insert_slot.appliance_load is not None or overwrite:
                            (insert.get("appliance_loads") or [{}])[0].update(
                                {
                                    "power": min(
                                        max(
                                            int(
                                                insert_slot.appliance_load
                                                if insert_slot.appliance_load
                                                is not None
                                                else SolixDefaults.PRESET_DEF
                                            ),
                                            min_load,
                                        ),
                                        max_load,
                                    ),
                                }
                            )
                            # optional advanced power mode settings if supported by schedule
                            if "power_setting_mode" in insert:
                                insert.update(
                                    {
                                        "power_setting_mode": power_mode
                                        or SolixDefaults.POWER_MODE
                                    }
                                )
                                # if power_mode == SolarbankPowerMode.advanced.value or overwrite:
                                for dev in insert.get("device_power_loads") or []:
                                    if (
                                        isinstance(dev, dict)
                                        and dev.get("device_sn") == deviceSn
                                    ):
                                        dev.update(
                                            {
                                                "power": int(
                                                    insert_slot.appliance_load
                                                    / sb_count
                                                )
                                                if insert_slot.device_load is None
                                                else int(insert_slot.device_load)
                                            }
                                        )
                                    elif isinstance(dev, dict):
                                        # other solarbanks get the difference equally shared
                                        dev.update(
                                            {
                                                "power": int(
                                                    insert_slot.appliance_load
                                                    / sb_count
                                                )
                                                if insert_slot.device_load is None
                                                else int(
                                                    (
                                                        insert_slot.appliance_load
                                                        - insert_slot.device_load
                                                    )
                                                    / (sb_count - 1)
                                                ),
                                            }
                                        )
                        if insert_slot.allow_export is not None or overwrite:
                            insert.update(
                                {
                                    "turn_on": SolixDefaults.ALLOW_EXPORT
                                    if insert_slot.allow_export is None
                                    else insert_slot.allow_export
                                }
                            )
                        if insert_slot.charge_priority_limit is not None or overwrite:
                            insert.update(
                                {
                                    "charge_priority": min(
                                        max(
                                            int(
                                                SolixDefaults.CHARGE_PRIORITY_DEF
                                                if insert_slot.charge_priority_limit
                                                is None
                                                else insert_slot.charge_priority_limit
                                            ),
                                            SolixDefaults.CHARGE_PRIORITY_MIN,
                                        ),
                                        SolixDefaults.CHARGE_PRIORITY_MAX,
                                    )
                                }
                            )
                        # insert slot before current slot if not last
                        if insert_slot.start_time.time() <= start_time:
                            new_ranges.append(insert)
                            insert = {}
                            pending_insert = False
                            if insert_slot.end_time.time() >= end_time:
                                # set start of next slot if not end of day
                                if (
                                    end_time
                                    < datetime.strptime("23:59", "%H:%M").time()
                                ):
                                    next_start = insert_slot.end_time.time()
                                last_time = insert_slot.end_time.time()
                                # skip current slot since overlapped by insert slot
                                continue
                            if split_slot:
                                # insert second part of a preceeding slot that was split
                                new_ranges.append(split_slot)
                                split_slot = {}
                                # delay start time of current slot not needed if previous slot was split
                            else:
                                # delay start time of current slot
                                slot.update(
                                    {
                                        "start_time": datetime.strftime(
                                            insert_slot.end_time, "%H:%M"
                                        ).replace("23:59", "24:00")
                                    }
                                )
                        else:
                            # create copy of slot when insert slot will split last slot to add it later as well
                            if insert_slot.end_time.time() < end_time:
                                split_slot = copy.deepcopy(slot)
                                split_slot.update(
                                    {
                                        "start_time": datetime.strftime(
                                            insert_slot.end_time, "%H:%M"
                                        ).replace("23:59", "24:00")
                                    }
                                )
                            if insert_slot.start_time.time() < end_time:
                                # shorten end time of current slot when appended at the end
                                slot.update(
                                    {
                                        "end_time": datetime.strftime(
                                            insert_slot.start_time, "%H:%M"
                                        ).replace("23:59", "24:00")
                                    }
                                )

                    elif pending_insert and insert_slot.start_time.time() <= end_time:
                        # create copy of slot when insert slot will split current slot to add it later
                        if insert_slot.end_time.time() < end_time:
                            split_slot = copy.deepcopy(slot)
                            split_slot.update(
                                {
                                    "start_time": datetime.strftime(
                                        insert_slot.end_time, "%H:%M"
                                    ).replace("23:59", "24:00")
                                }
                            )
                        # shorten end of preceeding slot
                        slot.update(
                            {
                                "end_time": datetime.strftime(
                                    insert_slot.start_time, "%H:%M"
                                )
                            }
                        )
                        # re-use old slot parms for insert if end time of insert slot is same as original slot
                        if insert_slot.end_time.time() == end_time:
                            # reuse old appliance load
                            if insert_slot.appliance_load is None:
                                insert_slot.appliance_load = (
                                    slot.get("appliance_loads") or [{}]
                                )[0].get("power")
                                # reuse an active advanced power mode setting
                                if (
                                    slot.get("power_setting_mode")
                                    == SolarbankPowerMode.advanced.value
                                    and insert_slot.device_load is None
                                ):
                                    insert_slot.device_load = next(
                                        iter(
                                            [
                                                dev.get("power")
                                                for dev in slot.get(
                                                    "device_power_loads"
                                                )
                                                or []
                                                if isinstance(dev, dict)
                                                and dev.get("device_sn") == deviceSn
                                            ]
                                        ),
                                        None,
                                    )
                                    if insert_slot.device_load is not None:
                                        power_mode = SolarbankPowerMode.advanced.value
                                elif isinstance(insert_slot.device_load, int | float):
                                    # correct appliance load with other device loads and new device load
                                    insert_slot.appliance_load = (
                                        insert_slot.device_load
                                        + sum(
                                            [
                                                dev.get("power")
                                                for dev in (
                                                    slot.get("device_power_loads") or []
                                                )
                                                if dev.get("device_sn") != deviceSn
                                            ]
                                        )
                                    )

                            if insert_slot.allow_export is None:
                                insert_slot.allow_export = slot.get("turn_on")
                            if insert_slot.charge_priority_limit is None:
                                insert_slot.charge_priority_limit = slot.get(
                                    "charge_priority"
                                )

                    elif next_start and next_start < end_time:
                        # delay start of slot following an insert
                        slot.update(
                            {
                                "start_time": (
                                    next_start.isoformat(timespec="minutes")
                                ).replace("23:59", "24:00")
                            }
                        )
                        next_start = None

                    elif not insert_slot and (all_day or start_time <= now < end_time):
                        # update required parameters in current slot or all slots
                        # Get other device loads if device load is provided
                        dev_other = 0
                        if dev_preset is not None:
                            dev_other = sum(
                                [
                                    dev.get("power")
                                    for dev in (slot.get("device_power_loads") or [])
                                    if dev.get("device_sn") != deviceSn
                                ]
                            )
                        # adjust appliance load depending on device load preset and ensure appliance load is consistent with device load min/max values
                        preset = (
                            preset
                            if dev_preset is None
                            else (dev_preset + dev_other)
                            if preset is None
                            else max(
                                min(
                                    preset,
                                    dev_preset + max_load_dev * (sb_count - 1),
                                ),
                                dev_preset + min_load_dev * (sb_count - 1),
                            )
                        )
                        if preset is not None:
                            (slot.get("appliance_loads") or [{}])[0].update(
                                {"power": int(preset)}
                            )
                        # optional advanced power mode settings if supported by schedule
                        if "power_setting_mode" in slot and power_mode is not None:
                            slot.update({"power_setting_mode": power_mode})
                            if (
                                power_mode == SolarbankPowerMode.advanced.value
                                and dev_preset is not None
                            ):
                                for dev in slot.get("device_power_loads") or []:
                                    if (
                                        isinstance(dev, dict)
                                        and dev.get("device_sn") == deviceSn
                                    ):
                                        dev.update({"power": int(dev_preset)})
                                    elif isinstance(dev, dict):
                                        # other solarbanks get the difference equally shared
                                        dev.update(
                                            {
                                                "power": int(
                                                    (preset - dev_preset)
                                                    / (sb_count - 1)
                                                ),
                                            }
                                        )
                        if export is not None:
                            slot.update({"turn_on": export})
                        if charge_prio is not None:
                            slot.update(
                                {
                                    "charge_priority": min(
                                        max(
                                            int(charge_prio),
                                            SolixDefaults.CHARGE_PRIORITY_MIN,
                                        ),
                                        SolixDefaults.CHARGE_PRIORITY_MAX,
                                    )
                                }
                            )
                        # clear flag for pending parameter update for actual time
                        if start_time <= now < end_time:
                            pending_now_update = False

                if (
                    last_time
                    <= datetime.strptime(
                        (slot.get("start_time") or "00:00").replace("24:00", "23:59"),
                        "%H:%M",
                    ).time()
                ):
                    new_ranges.append(slot)

                # fill gap after last slot for current time parameter changes or insert slots
                if insert:
                    slot = insert
                    new_ranges.append(slot)
                    if split_slot:
                        # insert second part of a preceeding slot that was split
                        new_ranges.append(split_slot)
                        split_slot = {}

                # Track end time of last appended slot in list
                last_time = datetime.strptime(
                    (
                        str(new_ranges[-1].get("end_time") or "00:00").replace(
                            "24:00", "23:59"
                        )
                    ),
                    "%H:%M",
                ).time()

        # If no slot exists or new slot to be set, set defaults or given set_slot parameters
        if len(new_ranges) == 0:
            if not set_slot:
                # fill set_slot with given parameters
                set_slot = SolarbankTimeslot(
                    start_time=datetime.strptime("00:00", "%H:%M"),
                    end_time=datetime.strptime("23:59", "%H:%M"),
                    appliance_load=preset,
                    device_load=dev_preset,
                    allow_export=export,
                    charge_priority_limit=charge_prio,
                )
            # generate the new slot
            # adjust appliance load depending on device load preset and ensure appliance load is consistent with device load min/max values
            appliance_load = (
                SolixDefaults.PRESET_DEF
                if set_slot.appliance_load is None and set_slot.device_load is None
                else (set_slot.device_load * sb_count)
                if set_slot.appliance_load is None
                else set_slot.appliance_load
                if set_slot.device_load is None
                else max(
                    min(
                        set_slot.appliance_load,
                        set_slot.device_load + max_load_dev * (sb_count - 1),
                    ),
                    set_slot.device_load + min_load_dev * (sb_count - 1),
                )
            )

            slot = {
                "start_time": datetime.strftime(set_slot.start_time, "%H:%M"),
                "end_time": datetime.strftime(set_slot.end_time, "%H:%M").replace(
                    "23:59", "24:00"
                ),
                "turn_on": SolixDefaults.ALLOW_EXPORT
                if set_slot.allow_export is None
                else set_slot.allow_export,
                "appliance_loads": [
                    {
                        "power": min(
                            max(
                                int(appliance_load),
                                min_load,
                            ),
                            max_load,
                        ),
                    }
                ],
                "charge_priority": min(
                    max(
                        int(
                            SolixDefaults.CHARGE_PRIORITY_DEF
                            if set_slot.charge_priority_limit is None
                            else set_slot.charge_priority_limit
                        ),
                        SolixDefaults.CHARGE_PRIORITY_MIN,
                    ),
                    SolixDefaults.CHARGE_PRIORITY_MAX,
                ),
            }
            # optional advanced power mode settings if device load and appliance load got provided
            if (
                power_mode is SolarbankPowerMode.advanced.value
                and set_slot.device_load is not None
                and set_slot.appliance_load is not None
            ):
                # try to get solarbank serials from site dict
                solarbanks = {
                    sb.get("device_sn")
                    for sb in (
                        (
                            (self.sites.get(siteId) or {}).get("solarbank_info") or {}
                        ).get("solarbank_list")
                        or [{}]
                    )
                }
                if len(solarbanks) == sb_count and deviceSn in solarbanks:
                    slot.update({"power_setting_mode": power_mode})
                    device_power_loads = []
                    for sn in solarbanks:
                        if sn == deviceSn:
                            device_power_loads.append(
                                {
                                    "device_sn": sn,
                                    "power": int(set_slot.device_load),
                                },
                            )
                        else:
                            # other solarbanks get the difference equally shared
                            device_power_loads.append(
                                {
                                    "device_sn": sn,
                                    "power": int(
                                        (appliance_load - set_slot.device_load)
                                        / (sb_count - 1)
                                    ),
                                },
                            )
                    slot.update({"device_power_loads": device_power_loads})

            # use previous appliance name if a slot was defined originally
            if appliance_name:
                (slot.get("appliance_loads") or [{}])[0].update(
                    {"name": appliance_name}
                )
            new_ranges.append(slot)
        self._logger.debug(
            "Ranges to apply: %s",
            new_ranges,
        )
        schedule.update({"ranges": new_ranges})
        # return resulting schedule for test purposes without Api call
        if test_count is not None or test_schedule is not None:
            return schedule
        # Make the Api call with final schedule and check for return code, the set call will also update api dict
        # NOTE: set_device_load does not seem to be usable yet for changing the home load, or is only usable in dual bank setups for changing the appliance load share as well?
        return await self.set_device_parm(
            siteId=siteId,
            paramData=schedule,
            deviceSn=deviceSn,
        )

    async def get_device_fittings(
        self, siteId: str, deviceSn: str, fromFile: bool = False
    ) -> dict:
        r"""Get device fittings.

        Example data:
        {"data": [{
            "device_sn": "ZDL32D6A3HKXUTN1","product_code": "A17Y0","device_name": "E1600 0W Output Switch","alias_name": "E1600 0W Output Switch",
            "img_url": "https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/2024/01/10/iot-admin/EPBsJ3a5JyMGqA1j/picl_A17Y0_normal.png",
            "bt_ble_id": "","bt_ble_mac": "FC1CEA253CDB","link_time": 1707127936
        }]}
        """
        data = {"site_id": siteId, "device_sn": deviceSn}
        if fromFile:
            resp = await self._loadFromFile(
                os.path.join(self._testdir, f"device_fittings_{deviceSn}.json")
            )
        else:
            resp = await self.request(
                "post", _API_ENDPOINTS["get_device_fittings"], json=data
            )
        data = resp.get("data") or {}
        # update devices dict with new fittings data
        fittings = {}
        for fitting in [
            x
            for x in data.get("data") or []
            if isinstance(x, dict) and x.get("device_sn")
        ]:
            # remove unnecessary keys from fitting device
            keylist = fitting.keys()
            for key in [
                x for x in ("img_url", "bt_ble_id", "link_time") if x in keylist
            ]:
                fitting.pop(key, None)
            fittings[fitting.get("device_sn")] = fitting
        self._update_dev({"device_sn": deviceSn, "fittings": fittings})
        return data

    async def get_ota_info(
        self, solarbankSn: str = "", inverterSn: str = "", fromFile: bool = False
    ) -> dict:
        """Get the solar info and OTA processing info for a solarbank.

        Example data:
        {"ota_status": 3,"current_version": "EZ1 2.0.5","timestamp": 1708277846,"version_type": 3}
        """
        data = {"solar_bank_sn": solarbankSn, "solar_sn": inverterSn}
        if fromFile:
            resp = await self._loadFromFile(
                os.path.join(
                    self._testdir, f"ota_info_{solarbankSn or inverterSn}.json"
                )
            )
        else:
            resp = await self.request("post", _API_ENDPOINTS["get_ota_info"], json=data)
        return resp.get("data", {})

    async def get_ota_update(
        self, deviceSn: str, insertSn: str = "", fromFile: bool = False
    ) -> dict:
        """Usage not Clear, process OTA update with confirmation in insertSn?.

        Example data:
        {"is_ota_update": true,"need_retry": true,"retry_interval": 2000,"device_list": null}
        """
        data = {"device_sn": deviceSn, "insert_sn": insertSn}
        if fromFile:
            resp = await self._loadFromFile(
                os.path.join(self._testdir, f"ota_update_{deviceSn}.json")
            )
        else:
            resp = await self.request(
                "post", _API_ENDPOINTS["get_ota_update"], json=data
            )
        data = resp.get("data") or {}
        # update devices dict with new ota data
        self._update_dev(
            {"device_sn": deviceSn, "is_ota_update": data.get("is_ota_update")}
        )
        return data

    async def check_upgrade_record(
        self, recordType: int = 2, fromFile: bool = False
    ) -> dict:
        """Check upgrade record, shows device updates with their last version. Type 0-3 work.

        Example data:
        {"is_record": true,"device_list": [{
            "device_sn": "9JVB42LJK8J0P5RY","device_name": "","icon": "","last_version": "v1.4.4","device_pn": ""}
        ]}
        """
        data = {"type": recordType}
        if fromFile:
            resp = await self._loadFromFile(
                os.path.join(self._testdir, f"check_upgrade_record_{recordType}.json")
            )
        else:
            resp = await self.request(
                "post", _API_ENDPOINTS["check_upgrade_record"], json=data
            )
        return resp.get("data", {})

    async def get_upgrade_record(
        self,
        deviceSn: str | None = None,
        siteId: str | None = None,
        recordType: int | None = None,
        fromFile: bool = False,
    ) -> dict:
        """Get upgrade record for a device serial or site ID, shows update history. Type 1 works for solarbank, type 2 for site ID.

        Example data:
        {"device_sn": "9JVB42LJK8J0P5RY", "site_id": "", "upgrade_record_list": [
            {"upgrade_time": "2024-02-29 12:38:23","upgrade_version": "v1.5.6","pre_version": "v1.4.4","upgrade_type": "1","upgrade_desc": "",
            "device_sn": "9JVB42LJK8J0P5RY","device_name": "9JVB42LJK8J0P5RY","child_upgrade_records": null},
            {"upgrade_time": "2023-12-29 10:23:06","upgrade_version": "v1.4.4","pre_version": "v0.0.6.6","upgrade_type": "1","upgrade_desc": "",
            "device_sn": "9JVB42LJK8J0P5RY","device_name": "9JVB42LJK8J0P5RY","child_upgrade_records": null},
            {"upgrade_time": "2023-11-02 13:43:09","upgrade_version": "v1.4.1","pre_version": "v0.0.6.5","upgrade_type": "1","upgrade_desc": "",
            "device_sn": "9JVB42LJK8J0P5RY","device_name": "9JVB42LJK8J0P5RY","child_upgrade_records": null}]},
        """
        if deviceSn:
            data = {
                "device_sn": deviceSn,
                "type": 1 if recordType is None else recordType,
            }
        elif siteId:
            data = {"site_id": siteId, "type": 2 if recordType is None else recordType}
        else:
            recordType = 0 if recordType is None else recordType
            data = {"type": recordType}
        if fromFile:
            resp = await self._loadFromFile(
                os.path.join(
                    self._testdir,
                    f"get_upgrade_record_{deviceSn if deviceSn else siteId if siteId else recordType}.json",
                )
            )
        else:
            resp = await self.request(
                "post", _API_ENDPOINTS["get_upgrade_record"], json=data
            )
        return resp.get("data", {})

    async def energy_analysis(
        self,
        siteId: str,
        deviceSn: str,
        rangeType: str | None = None,
        startDay: datetime | None = None,
        endDay: datetime | None = None,
        devType: str | None = None,
    ) -> dict:
        """Fetch Energy data for given device and optional time frame.

        siteId: site ID of device
        deviceSn: Device to fetch data
        rangeType: "day" | "week" | "year"
        startTime: optional start Date and time
        endTime: optional end Date and time
        devType: "solar_production" | "solarbank"
        Example Data for solar_production:
        {'power': [{'time': '2023-10-01', 'value': '3.67'}, {'time': '2023-10-02', 'value': '3.29'}, {'time': '2023-10-03', 'value': '0.55'}],
        'charge_trend': None, 'charge_level': [], 'power_unit': 'wh', 'charge_total': '3.67', 'charge_unit': 'kwh', 'discharge_total': '3.11', 'discharge_unit': 'kwh',
        'charging_pre': '0.49', 'electricity_pre': '0.51', 'others_pre': '0',
        'statistics': [{'type': '1', 'total': '7.51', 'unit': 'kwh'}, {'type': '2', 'total': '7.49', 'unit': 'kg'}, {'type': '3', 'total': '3.00', 'unit': '€'}]}
        """
        data = {
            "site_id": siteId,
            "device_sn": deviceSn,
            "type": rangeType if rangeType in ["day", "week", "year"] else "day",
            "start_time": startDay.strftime("%Y-%m-%d")
            if startDay
            else datetime.today().strftime("%Y-%m-%d"),
            "device_type": devType
            if devType in ["solar_production", "solarbank"]
            else "solar_production",
            "end_time": endDay.strftime("%Y-%m-%d") if endDay else "",
        }
        resp = await self.request("post", _API_ENDPOINTS["energy_analysis"], json=data)
        return resp.get("data", {})

    async def energy_daily(
        self,
        siteId: str,
        deviceSn: str,
        startDay: datetime = datetime.today(),
        numDays: int = 1,
        dayTotals: bool = False,
    ) -> dict:
        """Fetch daily Energy data for given interval and provide it in a table format dictionary.

        Example:
        {"2023-09-29": {"date": "2023-09-29", "solar_production": "1.21", "solarbank_discharge": "0.47", "solarbank_charge": "0.56"},
         "2023-09-30": {"date": "2023-09-30", "solar_production": "3.07", "solarbank_discharge": "1.06", "solarbank_charge": "1.39"}}
        """  # noqa: D413
        table = {}
        today = datetime.today()
        # check daily range and limit to 1 year max and avoid future days
        if startDay > today:
            startDay = today
            numDays = 1
        elif (startDay + timedelta(days=numDays)) > today:
            numDays = (today - startDay).days + 1
        numDays = min(366, max(1, numDays))
        # first get solarbank export
        resp = await self.energy_analysis(
            siteId=siteId,
            deviceSn=deviceSn,
            rangeType="week",
            startDay=startDay,
            endDay=startDay + timedelta(days=numDays - 1),
            devType="solarbank",
        )
        for item in resp.get("power", []):
            daystr = item.get("time", None)
            if daystr:
                table.update(
                    {
                        daystr: {
                            "date": daystr,
                            "solarbank_discharge": item.get("value", ""),
                        }
                    }
                )
        # Add solar production which contains percentages
        resp = await self.energy_analysis(
            siteId=siteId,
            deviceSn=deviceSn,
            rangeType="week",
            startDay=startDay,
            endDay=startDay + timedelta(days=numDays - 1),
            devType="solar_production",
        )
        for item in resp.get("power", []):
            daystr = item.get("time", None)
            if daystr:
                entry = table.get(daystr, {})
                entry.update(
                    {"date": daystr, "solar_production": item.get("value", "")}
                )
                table.update({daystr: entry})
        # Solarbank charge and percentages are only received as total value for given interval. If requested, make daily queries for given interval with some delay
        if dayTotals:
            if numDays == 1:
                daystr = startDay.strftime("%Y-%m-%d")
                entry = table.get(daystr, {})
                entry.update(
                    {
                        "date": daystr,
                        "solarbank_charge": resp.get("charge_total", ""),
                        "battery_percentage": resp.get("charging_pre", ""),
                        "solar_percentage": resp.get("electricity_pre", ""),
                        "other_percentage": resp.get("others_pre", ""),
                    }
                )
                table.update({daystr: entry})
            else:
                daylist = [startDay + timedelta(days=x) for x in range(numDays)]
                for day in daylist:
                    daystr = day.strftime("%Y-%m-%d")
                    resp = await self.energy_analysis(
                        siteId=siteId,
                        deviceSn=deviceSn,
                        rangeType="week",
                        startDay=day,
                        endDay=day,
                        devType="solar_production",
                    )
                    entry = table.get(daystr, {})
                    entry.update(
                        {
                            "date": daystr,
                            "solarbank_charge": resp.get("charge_total", ""),
                            "battery_percentage": resp.get("charging_pre", ""),
                            "solar_percentage": resp.get("electricity_pre", ""),
                            "other_percentage": resp.get("others_pre", ""),
                        }
                    )
                    table.update({daystr: entry})
        return table

    async def home_load_chart(self, siteId: str, deviceSn: str | None = None) -> dict:
        """Get home load chart data.

        Example data:
        {"data": []}
        """
        data = {"site_id": siteId}
        if deviceSn:
            data.update({"device_sn": deviceSn})
        resp = await self.request("post", _API_ENDPOINTS["home_load_chart"], json=data)
        return resp.get("data", {})

    async def get_message_unread(self, fromFile: bool = False) -> dict:
        """Get the unread messages for account.

        Example data:
        {"has_unread_msg": false}
        """
        if fromFile:
            resp = await self._loadFromFile(
                os.path.join(self._testdir, "message_unread.json")
            )
        else:
            resp = await self.request("get", _API_ENDPOINTS["get_message_unread"])
        # save unread msg flag in each known site
        data = resp.get("data", {})
        for siteId in self.sites:
            self._update_site(siteId, data)
        return data
