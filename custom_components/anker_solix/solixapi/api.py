"""Class for interacting with the Anker Power / Solix API.

Required Python modules:
pip install cryptography
pip install aiohttp
"""

from __future__ import annotations

from base64 import b64encode
import contextlib
from datetime import datetime, timedelta
from enum import Enum
import json
import logging
import os
import sys
import time

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
    "scene_info": "power_service/v1/site/get_scen_info",  # Scene info for provided site id (contains most information as the App home screen, with some but not all device details)
    "user_devices": "power_service/v1/site/list_user_devices",  # List Device details of owned devices, not all device details information included
    "charging_devices": "power_service/v1/site/get_charging_device",  # List of Portable Power Station devices?
    "get_device_parm": "power_service/v1/site/get_site_device_param",  # Get settings of a device for the provided site id and param type (e.g. Schedules)
    "set_device_parm": "power_service/v1/site/set_site_device_param",  # Apply provided settings to a device for the provided site id and param type (e.g. Schedules), NOT IMPLEMENTED YET
    "wifi_list": "power_service/v1/site/get_wifi_info_list",  # List of available networks for provided site id
    "get_site_price": "power_service/v1/site/get_site_price",  # List defined power price and CO2 for given site, works only for site owner account
    "update_site_price": "power_service/v1/site/update_site_price",  # Update power price for given site, REQUIRED PARAMETERS UNKNOWN
    "get_auto_upgrade": "power_service/v1/app/get_auto_upgrade",  # List of Auto-Upgrade configuration and enabled devices, onyl works for site owner accout
    "set_auto_upgrade": "power_service/v1/app/set_auto_upgrade",  # Set/Enable Auto-Upgrade configuration, not implemented yet, REQUIRED PARAMETERS UNKNOWN
    "bind_devices": "power_service/v1/app/get_relate_and_bind_devices",  # List with details of locally connected/bound devices, includes firmware version, works only for owner account
    "get_device_load": "power_service/v1/app/device/get_device_home_load",  # Get defined device schedule (same data as provided with device param query)
    "set_device_load": "power_service/v1/app/device/set_device_home_load",  # Set defined device schedule (Not implemented yet, REQUIRED PARAMETERS UNKNOWN)
    "get_ota_info": "power_service/v1/app/compatible/get_ota_info",  # Get OTA status for solarbank and/or inverter serials
    "get_ota_update": "power_service/v1/app/compatible/get_ota_update",  # Not clear what this does, shows some OTA settings
    "solar_info": "power_service/v1/app/compatible/get_compatible_solar_info",  # Solar inverter definition for solarbanks, works only with owner account
    "get_cutoff": "power_service/v1/app/compatible/get_power_cutoff",  # Get Power Cutoff settings (Min SOC) for provided site id and device sn, works only with owner account
    "set_cutoff": "power_service/v1/app/compatible/set_power_cutoff",  # Set Min SOC for device, only works for onwer accounts
    "compatible_process": "power_service/v1/app/compatible/get_compatible_process",  # contains solar_info plus OTA processing codes, works only with owner account
    "get_device_fittings": "power_service/v1/app/get_relate_device_fittings",  # Device fittings for given site id and device sn. Solarbank/inverter responses do not contain info
    "energy_analysis": "power_service/v1/site/energy_analysis",  # Fetch energy data for given time frames
    "home_load_chart": "power_service/v1/site/get_home_load_chart",  # Fetch data as displayed in home load chart for given site_id and optional device SN (empty if solarbank not connected)
    "check_upgrade_record": "power_service/v1/app/check_upgrade_record",  # show an upgrade record for the device, types 1-3 show different info, only works for owner account
    "get_message": "power_service/v1/get_message",  # get list of max Messages from certain time, last_time format unknown
    "get_upgrade_record": "power_service/v1/app/get_upgrade_record",  # get list of firmware update history
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
    'power_service/v1/site/update_site_device',
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
    'power_service/v1/app/upgrade_event_report',
    'power_service/v1/app/get_phonecode_list',
    'power_service/v1/message_not_disturb',
    'power_service/v1/get_message_not_disturb',
    'power_service/v1/read_message',
    'power_service/v1/del_message',
    'power_service/v1/product_categories',
    'power_service/v1/product_accessories',


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
    PPS = "pps"
    POWERPANEL = "powerpanel"


class SolixParmType(Enum):
    """Enumuration for Anker Solix Parameter types."""

    SOLARBANK_SCHEDULE = "4"


class SolixDeviceCapacity(Enum):
    """Enumuration for Anker Solix device capacities in Wh by Part Number."""

    A17C0 = 1600


class SolixDeviceStatus(Enum):
    """Enumuration for Anker Solix Device status."""

    # TODO(3): Add descriptions once status code usage is observed/known
    off = "0"
    on = "1"
    unknown = "unknown"


class SolarbankStatus(Enum):
    """Enumuration for Anker Solix Solarbank status."""

    charging = "1"
    discharging = "2"
    bypass = "3"
    bypass_charging = "35"  # pseudo state, the solarbank does not distinguish this
    charge_priority = "37"  # pseudo state, the solarbank does not distinguish this but reports 3 as seen so far
    wakeup = "4"  # Not clear what happens during this state, but observed short intervals during night as well
    # TODO(3): Add descriptions once status code usage is observed/known
    # There is also a deep standby / full bypass mode at cold temperatures when the battery cannot be loaded.
    # full_bypass = "unknown"
    standby = "7"
    unknown = "unknown"


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

        # Define Encryption for password, using ECDH assymetric key exchange for shared secret calculation, which must be used to encrypt the password using AES-256-CBC with seed of 16
        # uncompressed public key from EU Anker server in the format 04 [32 byte x vlaue] [32 byte y value]
        # TODO(2): COM Anker server public key usage must still be validated
        self._api_public_key_hex = "04c5c00c4f8d1197cc7c3167c52bf7acb054d722f0ef08dcd7e0883236e0d72a3868d9750cb47fa4619248f3d83f0f662671dadc6e2d31c2f41db0161651c7c076"
        self._curve = (
            ec.SECP256R1()
        )  # Encryption curve SECP256R1 (identical to prime256v1)
        self._ecdh = ec.generate_private_key(
            self._curve, default_backend()
        )  # returns EllipticCurvePrivateKey
        self._public_key = self._ecdh.public_key()  # returns EllipticCurvePublicKey
        self._shared_key = self._ecdh.exchange(
            ec.ECDH(),
            ec.EllipticCurvePublicKey.from_encoded_point(
                self._curve, bytes.fromhex(self._api_public_key_hex)
            ),
        )  # returns bytes of shared secret

        # Define class variables saving the most recent site and device data
        self.nickname: str = ""
        self.sites: dict = {}
        self.devices: dict = {}

    def _md5(self, text: str) -> str:
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

    def _loadFromFile(self, filename: str) -> dict:
        """Load json data from given file for testing."""
        if self.mask_credentials:
            masked_filename = filename.replace(
                self._email, self.mask_values(self._email)
            )
        else:
            masked_filename = filename
        try:
            if os.path.isfile(filename):
                with open(filename, encoding="utf-8") as file:
                    data = json.load(file)
                    self._logger.debug("Loaded JSON from file %s:", masked_filename)
                    self._logger.debug(
                        "Data: %s",
                        self.mask_values(
                            data, "user_id", "auth_token", "email", "geo_key"
                        ),
                    )
                    return data
            return {}
        except OSError as err:
            self._logger.error(
                "ERROR: Failed to load JSON from file %s", masked_filename
            )
            self._logger.error(err)
            return {}

    def _saveToFile(self, filename: str, data: dict = None) -> bool:
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
            with open(filename, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=2)
                self._logger.debug("Saved JSON to file %s:", masked_filename)
                return True
        except OSError as err:
            self._logger.error("ERROR: Failed to save JSON to file %s", masked_filename)
            self._logger.error(err)
            return False

    def _update_dev(  # noqa: C901
        self,
        devData: dict,
        devType: str = None,
        siteId: str = None,
        isAdmin: bool = None,
    ) -> str | None:
        """Update the internal device details dictionary with the given data. The device_sn key must be set in the data dict for the update to be applied.

        This method is used to consolidate various device related key values from various requests under a common set of device keys.
        """
        sn = devData.get("device_sn")
        if sn:
            device = self.devices.get(sn, {})  # lookup old device info if any
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
            try:
                for key, value in devData.items():
                    if key in ["product_code", "device_pn"] and value:
                        device.update({"device_pn": str(value)})
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
                            device.update({"set_output_power": str(value).replace("W", "")})
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
                        # check if battery charging during bypass and if output during bypass
                        # NOTE: charging power may be updated after initial device details update
                        # NOTE: If status is 3=Bypass but nothing goes out, the charge priority is active (e.g. 0 Watt switch)
                        if (
                            description == SolarbankStatus.bypass.name
                            and (charge := devData.get("charging_power"))
                            and (out := devData.get("output_power"))
                        ):
                            with contextlib.suppress(ValueError):
                                if int(out) == 0:
                                    # Bypass but 0 W output must be active charge priority
                                    description = SolarbankStatus.charge_priority.name
                                elif int(charge) > 0:
                                    # Bypass with output and charge must be bypass charging
                                    description = SolarbankStatus.bypass_charging.name
                        device.update({"charging_status_desc": description})
                    elif key in ["bws_surplus"]:
                        device.update({"bws_surplus": str(value)})
                    elif key in ["charge"]:
                        device.update({"charge": bool(value)})
                    elif key in ["auto_upgrade"]:
                        device.update({"auto_upgrade": bool(value)})
                    elif key in ["power_cutoff"]:
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
                            value.pop(key)
                        device.update({"solar_info": dict(value)})
                    # schedule is currently a site wide setting. However, we save this with device details to retain info across site updates
                    # When individual device schedules are support in future, this info is needed per device anyway
                    elif key in ["schedule"] and isinstance(value, dict) and value:
                        device.update({"schedule": dict(value)})

                    # inverter specific keys
                    elif key in ["generate_power"]:
                        device.update({"generate_power": str(value)})

                    # generate extra values when certain conditions are met
                    if key in ["battery_power"] or calc_capacity:
                        # generate battery values when soc updated or device name changed or PN is known
                        if not (cap := device.get("battery_capacity")):
                            if hasattr(SolixDeviceCapacity, device.get("device_pn", "")):
                                # get battery capacity from known PNs
                                cap = SolixDeviceCapacity[device.get("device_pn", "")].value
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
                                    "battery_energy": str(int(int(cap) * int(soc) / 100)),
                                }
                            )
            except Exception as err: #pylint: disable=broad-exception-caught
                self._logger.error("%s occured when updating device details for key %s with value %s: %s", type(err), key, value, err)

            self.devices.update({str(sn): device})
        return sn

    def testDir(self, subfolder: str = None) -> str:
        """Get or set the subfolder for local API test files."""
        if not subfolder or subfolder == self._testdir:
            return self._testdir
        if not os.path.isdir(subfolder):
            self._logger.error("Specified test folder does not exist: %s", subfolder)
        else:
            self._testdir = subfolder
            self._logger.info("Set Api test folder to: %s", subfolder)
        return self._testdir

    def logLevel(self, level: int = None) -> int:
        """Get or set the logger log level."""
        if level:
            self._logger.setLevel(level)
            self._logger.info("Set log level to: %s", level)
        return self._logger.getEffectiveLevel()

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
            data = self._loadFromFile(self._authFile)
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
            self._retry_attempt = (
                False  # clear retry attempt to allow retry for authentication refresh
            )
        else:
            self._logger.debug("Fetching new Login credentials from server")
            now = datetime.now().astimezone()
            self._retry_attempt = (
                True  # set retry attempt to avoid retry on failed authentication
            )
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
                        int(time.mktime(now.timetuple()) * 1000)
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
            with open(self._authFile, "w", encoding="utf-8") as authfile:
                json.dump(data, authfile, indent=2, skipkeys=True)
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
        async with self._session.request(
            method, url, headers=mergedHeaders, json=json
        ) as resp:
            try:
                # get first the body text for usage in error detail logging if necessary
                body_text = await resp.text()
                resp.raise_for_status()
                data: dict = await resp.json(content_type=None)
                if endpoint == _API_LOGIN:
                    self._logger.debug(
                        "Request Response: %s",
                        self.mask_values(
                            data, "user_id", "auth_token", "email", "geo_key"
                        ),
                    )
                else:
                    self._logger.debug("Request Response: %s", data)

                if not data:
                    self._logger.error("Response Text: %s", body_text)
                    raise ClientError(f"No data response while requesting {endpoint}")

                errors.raise_error(data)  # check the response code in the data
                if endpoint != _API_LOGIN:
                    self._retry_attempt = False  # reset retry flag only when valid token received and not another login request

                # valid response at this point, mark login and return data
                self._loggedIn = True
                return data

            except (
                ClientError
            ) as err:  # Exception from ClientSession based on standard response codes
                self._logger.error("Request Error: %s", err)
                self._logger.error("Response Text: %s", body_text)
                if "401" in str(err) or "403" in str(err):
                    # Unauthorized or forbidden request
                    if self._retry_attempt:
                        raise errors.AuthorizationError(
                            f"Login failed for user {self._email}"
                        ) from err
                    self._logger.warning("Login failed, retrying authentication")
                    if await self.async_authenticate(restart=True):
                        return await self.request(
                            method, endpoint, headers=headers, json=json
                        )
                    self._logger.error("Login failed for user %s", self._email)
                    raise errors.AuthorizationError(
                        f"Login failed for user {self._email}"
                    ) from err
                raise ClientError(
                    f"There was an error while requesting {endpoint}: {err}"
                ) from err
            except (
                errors.InvalidCredentialsError,
                errors.TokenKickedOutError,
            ) as err:  # Exception for API specific response codes
                self._logger.error("API ERROR: %s", err)
                self._logger.error("Response Text: %s", body_text)
                if self._retry_attempt:
                    raise errors.AuthorizationError(
                        f"Login failed for user {self._email}"
                    ) from err
                self._logger.warning("Login failed, retrying authentication")
                if await self.async_authenticate(restart=True):
                    return await self.request(
                        method, endpoint, headers=headers, json=json
                    )
                self._logger.error("Login failed for user %s", self._email)
                raise errors.AuthorizationError(
                    f"Login failed for user {self._email}"
                ) from err
            except errors.AnkerSolixError as err:  # Other Exception from API
                self._logger.error("ANKER API ERROR: %s", err)
                self._logger.error("Response Text: %s", body_text)
                raise err

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
        self.sites = {}
        self._logger.debug("Getting site list")
        sites = await self.get_site_list(fromFile=fromFile)
        act_devices = []
        for site in sites.get("site_list", []):
            if site.get("site_id"):
                # Update site info
                myid = site.get("site_id")
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
                self.sites.update({myid: mysite})
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
                    if not solarbank.get("set_load_power"):
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
                        solarbank["charging_power"] = str(charge_calc)  # allow negative values
                        sb_total_charge_calc += charge_calc
                    mysite["solarbank_info"]["solarbank_list"][index] = solarbank
                    self.sites.update({myid: mysite})
                    sn = self._update_dev(
                        solarbank,
                        devType=SolixDeviceType.SOLARBANK.value,
                        siteId=myid,
                        isAdmin=admin,
                    )
                    if sn:
                        act_devices.append(sn)
                        sb_charges[sn] = charge_calc
                # adjust calculated SB charge to match total
                if len(sb_charges) == len(sb_list) and str(sb_total_charge).isdigit():
                    sb_total_charge = int(sb_total_charge)
                    if sb_total_charge_calc < 0:
                        with contextlib.suppress(ValueError):
                            # discharging, adjust sb total charge value in scene info and allow negativ value to indicate discharge
                            sb_total_charge = float(sb_total_solar) - float(sb_total_output)
                            mysite["solarbank_info"]["total_charging_power"] = str(sb_total_charge)
                    for sn, charge in sb_charges.items():
                        self.devices[sn]["charging_power"] = str(
                            0
                            if sb_total_charge_calc == 0
                            else int(sb_total_charge / sb_total_charge_calc * charge)
                        )
                        # Update also the charge status description which may change after charging power correction
                        charge_status = self.devices[sn].get("charging_status")
                        if charge_status == SolarbankStatus.bypass:
                            self._update_dev(
                                {
                                    "device_sn": sn,
                                    "charging_status": charge_status,
                                }
                            )
                # make sure to write back any changes to the solarbank info in sites dict
                self.sites.update({myid: mysite})

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
                        act_devices.append(sn)
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
                        act_devices.append(sn)
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
                        act_devices.append(sn)
        # recycle device list and remove devices no longer used in sites
        rem_devices = [dev for dev in self.devices if dev not in act_devices]
        for dev in rem_devices:
            self.devices.pop(dev)
        return self.sites

    async def update_device_details(self, fromFile: bool = False) -> dict:
        """Get the latest updates for additional device info updated less frequently.

        Most of theses requests return data only when user has admin rights for sites owning the devices.
        To limit API requests, this update device details method should be called less frequently than update site method, which will also update most device details as found in the site data response.
        """
        self._logger.debug("Updating Device Details")
        # Fetch firmware version of device
        self._logger.debug("Getting bind devices")
        await self.get_bind_devices(fromFile=fromFile)
        # Get the setting for effective automated FW upgrades
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

                # Fetch device type specific details
                if dev_Type in [SolixDeviceType.SOLARBANK.value]:
                    # Fetch active Power Cutoff setting for solarbanks
                    self._logger.debug("Getting Power Cutoff settings for device")
                    await self.get_power_cutoff(
                        siteId=site_id, deviceSn=sn, fromFile=fromFile
                    )

                    # Fetch defined inverter details for solarbanks
                    self._logger.debug("Getting inverter settings for device")
                    await self.get_solar_info(solarbankSn=sn, fromFile=fromFile)

                    # Fetch schedule for device types supporting it
                    self._logger.debug("Getting schedule details for device")
                    await self.get_device_load(
                        siteId=site_id, deviceSn=sn, fromFile=fromFile
                    )

                    # Fetch device fittings for device types supporting it
                    self._logger.debug("Getting fittings for device")
                    await self.get_device_fittings(
                        siteId=site_id, deviceSn=sn, fromFile=fromFile
                    )

                # update entry in devices
                self.devices.update({sn: device})

            # TODO(#0): Fetch other details of specific device types as known and relevant

        return self.devices

    async def get_site_list(self, fromFile: bool = False) -> dict:
        """Get the site list.

        Example data:
        {'site_list': [{'site_id': 'efaca6b5-f4a0-e82e-3b2e-6b9cf90ded8c', 'site_name': 'BKW', 'site_img': '', 'device_type_list': [3], 'ms_type': 2, 'power_site_type': 2, 'is_allow_delete': True}]}
        """
        if fromFile:
            resp = self._loadFromFile(os.path.join(self._testdir, "site_list.json"))
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
            resp = self._loadFromFile(
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
            resp = self._loadFromFile(os.path.join(self._testdir, "homepage.json"))
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
            resp = self._loadFromFile(os.path.join(self._testdir, "bind_devices.json"))
        else:
            resp = await self.request("post", _API_ENDPOINTS["bind_devices"])
        data = resp.get("data", {})
        for device in data.get("data", []):
            self._update_dev(device)
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
            resp = self._loadFromFile(os.path.join(self._testdir, "user_devices.json"))
        else:
            resp = await self.request("post", _API_ENDPOINTS["user_devices"])
        return resp.get("data", {})

    async def get_charging_devices(self, fromFile: bool = False) -> dict:
        """Get the charging devices (Power stations?).

        Example data:
        {'device_list': None, 'guide_txt': ''}
        """
        if fromFile:
            resp = self._loadFromFile(
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
            resp = self._loadFromFile(
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
            resp = self._loadFromFile(
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
            resp = self._loadFromFile(os.path.join(self._testdir, "auto_upgrade.json"))
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
            resp = self._loadFromFile(
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
            resp = self._loadFromFile(
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
            resp = self._loadFromFile(
                os.path.join(self._testdir, f"device_load_{deviceSn}.json")
            )
        else:
            resp = await self.request(
                "post", _API_ENDPOINTS["get_device_load"], json=data
            )
        # API Bug? home_load_data provided as string instead of object...Convert into object for proper handling
        string_data = (resp.get("data") or {}).get("home_load_data") or {}
        if isinstance(string_data, str):
            resp["data"].update({"home_load_data": json.loads(string_data)})
        data = resp.get("data") or {}
        if schedule := data.get("home_load_data") or {}:
            self._update_dev(
                {
                    "device_sn": deviceSn,
                    "schedule": schedule,
                    "current_home_load": data.get("current_home_load") or "",
                    "parallel_home_load": data.get("parallel_home_load") or "",
                }
            )
        return data

    async def get_device_parm(
        self,
        siteId: str,
        paramType: str = SolixParmType.SOLARBANK_SCHEDULE.value,
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
            resp = self._loadFromFile(
                os.path.join(self._testdir, f"device_parm_{siteId}.json")
            )
        else:
            resp = await self.request(
                "post", _API_ENDPOINTS["get_device_parm"], json=data
            )
        # API Bug? param_data provided as string instead of object...Convert into object for proper handling
        string_data = (resp.get("data", {})).get("param_data", {})
        if isinstance(string_data, str):
            resp["data"].update({"param_data": json.loads(string_data)})
        return resp.get("data", {})

    async def set_device_parm(
        self,
        siteId: str,
        paramData: dict,
        paramType: str = SolixParmType.SOLARBANK_SCHEDULE.value,
        command: int = 17,
        toFile: bool = False,
    ) -> dict:
        """Set device parameters (e.g. solarbank schedule).

        command: Must be 17 for solarbank schedule.
        paramType: was always string "4"
        Example paramData:
        {"param_data":{"ranges":[
            {"id":0,"start_time":"00:00","end_time":"08:30","turn_on":true,"appliance_loads":[{"id":0,"name":"Benutzerdefiniert","power":300,"number":1}],"charge_priority":80},
            {"id":0,"start_time":"08:30","end_time":"17:00","turn_on":false,"appliance_loads":[{"id":0,"name":"Benutzerdefiniert","power":100,"number":1}],"charge_priority":80},
            {"id":0,"start_time":"17:00","end_time":"24:00","turn_on":true,"appliance_loads":[{"id":0,"name":"Benutzerdefiniert","power":300,"number":1}],"charge_priority":0}],
        "min_load":100,"max_load":800,"step":0,"is_charge_priority":0,default_charge_priority":0}}
        """
        data = {
            "site_id": siteId,
            "param_type": paramType,
            "cmd": command,
            "param_data": json.dumps(paramData),
        }
        if toFile:
            resp = self._saveToFile(
                os.path.join(self._testdir, f"set_device_parm_{siteId}.json"), data=data
            )
        else:
            resp = await self.request(
                "post", _API_ENDPOINTS["set_device_parm"], json=data
            )
        return resp.get("data", {})

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
            resp = self._loadFromFile(
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
                fitting.pop(key)
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
            resp = self._loadFromFile(
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
            resp = self._loadFromFile(
                os.path.join(self._testdir, f"ota_update_{deviceSn}.json")
            )
        else:
            resp = await self.request(
                "post", _API_ENDPOINTS["get_ota_update"], json=data
            )
        return resp.get("data", {})

    async def get_upgrade_record(
        self, recordType: int = 2, fromFile: bool = False
    ) -> dict:
        """Get upgrade record, shows device updates with their last version. Type 0-3 work.

        Example data:
        {"is_record": true,"device_list": [{
            "device_sn": "9JVB42LJK8J0P5RY","device_name": "","icon": "","last_version": "v1.4.4","device_pn": ""}
        ]}
        """
        data = {"type": recordType}
        if fromFile:
            resp = self._loadFromFile(
                os.path.join(self._testdir, f"upgrade_record_{recordType}.json")
            )
        else:
            resp = await self.request(
                "post", _API_ENDPOINTS["check_upgrade_record"], json=data
            )
        return resp.get("data", {})

    async def energy_analysis(
        self,
        siteId: str,
        deviceSn: str,
        rangeType: str = None,
        startDay: datetime = None,
        endDay: datetime = None,
        devType: str = None,
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
        # first get solar production
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
                table.update(
                    {
                        daystr: {
                            "date": daystr,
                            "solar_production": item.get("value", ""),
                        }
                    }
                )
        # Add solarbank discharge
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
                entry = table.get(daystr, {})
                entry.update(
                    {"date": daystr, "solarbank_discharge": item.get("value", "")}
                )
                table.update({daystr: entry})
        # Solarbank charge is only received as total value for given interval. If requested, make daily queries for given interval with some delay
        if dayTotals:
            if numDays == 1:
                daystr = startDay.strftime("%Y-%m-%d")
                entry = table.get(daystr, {})
                entry.update(
                    {"date": daystr, "solarbank_charge": resp.get("charge_total", "")}
                )
                table.update({daystr: entry})
            else:
                daylist = [startDay + timedelta(days=x) for x in range(numDays)]
                for day in daylist:
                    daystr = day.strftime("%Y-%m-%d")
                    if day != daylist[0]:
                        time.sleep(1)  # delay to avoid hammering API
                    resp = await self.energy_analysis(
                        siteId=siteId,
                        deviceSn=deviceSn,
                        rangeType="week",
                        startDay=day,
                        endDay=day,
                        devType="solarbank",
                    )
                    entry = table.get(daystr, {})
                    entry.update(
                        {
                            "date": daystr,
                            "solarbank_charge": resp.get("charge_total", ""),
                        }
                    )
                    table.update({daystr: entry})
        return table

    async def home_load_chart(self, siteId: str, deviceSn: str = None) -> dict:
        """Get home load chart data.

        Example data:
        {"data": []}
        """
        data = {"site_id": siteId}
        if deviceSn:
            data.update({"device_sn": deviceSn})
        resp = await self.request("post", _API_ENDPOINTS["home_load_chart"], json=data)
        return resp.get("data", {})
