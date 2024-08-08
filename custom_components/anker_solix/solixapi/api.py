"""Class for interacting with the Anker Power / Solix API.

Required Python modules:
pip install cryptography
pip install aiohttp
pip install aiofiles
"""

from __future__ import annotations

from base64 import b64encode
import contextlib
from datetime import datetime
import json
import logging
import os
import sys

import aiofiles
from aiohttp import ClientSession
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from . import poller
from .helpers import RequestCounter
from .types import (
    API_COUNTRIES,
    API_ENDPOINTS,
    API_SERVERS,
    SmartmeterStatus,
    SolarbankDeviceMetrics,
    SolarbankStatus,
    SolarbankUsageMode,
    SolixDefaults,
    SolixDeviceCapacity,
    SolixDeviceCategory,
    SolixDeviceStatus,
    SolixDeviceType,
)

_LOGGER: logging.Logger = logging.getLogger(__name__)


class AnkerSolixApi:
    """Define the API class to handle Anker server authentication and API requests, along with the last state of queried site details and Device information."""

    # import outsourced methods
    from .energy import (  # pylint: disable=import-outside-toplevel
        energy_analysis,
        energy_daily,
        home_load_chart,
    )
    from .request import (  # pylint: disable=import-outside-toplevel
        _wait_delay,
        async_authenticate,
        request,
        requestDelay,
    )
    from .schedule import (  # pylint: disable=import-outside-toplevel
        get_device_load,
        get_device_parm,
        set_device_load,
        set_device_parm,
        set_home_load,
        set_sb2_home_load,
    )

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

        # Define Encryption for password, using ECDH asymmetric key exchange for shared secret calculation, which must be used to encrypt the password using AES-256-CBC with seed of 16
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
                        if hasattr(SolixDeviceCategory, str(value)):
                            dev_type = str(
                                getattr(SolixDeviceCategory, str(value))
                            ).split("_")
                            if "type" not in device:
                                device.update({"type": dev_type[0]})
                            # update generation if specified in device type definitions
                            if len(dev_type) > 1:
                                device.update({"generation": int(dev_type[1])})
                    elif key in ["device_name"] and value:
                        if value != device.get("name", ""):
                            calc_capacity = True
                        device.update({"name": str(value)})
                    elif key in ["alias_name"] and value:
                        device.update({"alias": str(value)})
                    elif key in ["device_sw_version"] and value:
                        device.update({"sw_version": str(value)})
                    elif key in [
                        "wifi_online",
                        "data_valid",
                        "charge",
                        "auto_upgrade",
                        "is_ota_update",
                    ]:
                        device.update({key: bool(value)})
                    elif key in [
                        "wireless_type",
                        "wifi_signal",
                        "bt_ble_mac",
                        "charging_power",
                        "output_power",
                        "power_unit",
                        "bws_surplus",
                    ]:
                        device.update({key: str(value)})
                    elif key in ["wifi_name"] and value:
                        # wifi_name can be empty in details if device connected, avoid clearing name
                        device.update({"wifi_name": str(value)})
                    elif key in ["battery_power"] and value:
                        # This is a percentage value for the battery state of charge, not power
                        device.update({"battery_soc": str(value)})
                    elif key in ["photovoltaic_power"]:
                        device.update({"input_power": str(value)})
                    # Add solarbank metrics depending on device type
                    elif (
                        key
                        in [
                            "solar_power_1",
                            "solar_power_2",
                            "solar_power_3",
                            "solar_power_4",
                            "ac_power",
                            "to_home_load",
                        ]
                        and value
                    ):
                        if key in getattr(
                            SolarbankDeviceMetrics, device.get("device_pn") or "", {}
                        ):
                            device.update({key: str(value)})
                    elif key in ["sub_package_num"] and str(value).isdigit():
                        if key in getattr(
                            SolarbankDeviceMetrics, device.get("device_pn") or "", {}
                        ):
                            device.update({"sub_package_num": int(value)})
                            calc_capacity = True
                    # solarbank info shows the load preset per device, which is identical to device parallel_home_load for 2 solarbanks, or current homeload for single solarbank
                    elif key in ["set_load_power", "parallel_home_load"] and value:
                        # Value may include unit, remove unit to have content consistent
                        device.update({"set_output_power": str(value).replace("W", "")})
                    # The current_home_load from get_device_load always shows the system wide settings made via the schedule
                    # get_device_load cannot be used for SB2 schedules, but site refresh will pass this as workaround.
                    elif key in ["current_home_load"] and value:
                        # Value may include unit, remove unit to have content consistent
                        home_load = str(value).replace("W", "")
                        device.update({"set_system_output_power": home_load})
                        # Value for device set home load may be empty for single solarbank, use this setting also for device preset in this case
                        if not device.get("set_output_power"):
                            device.update(
                                {
                                    "set_output_power": str(
                                        round(
                                            int(home_load)
                                            / devData.get("solarbank_count", 1)
                                        )
                                    )
                                    if home_load.isdigit()
                                    else home_load
                                }
                            )
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
                        # This key can be passed separately, make sure the other values are looked up in provided data first, then in device details
                        # NOTE: charging power may be updated after initial device details update
                        # NOTE: SB1: If status is 3=charging and larger than preset but nothing goes out, the charge priority is active (e.g. 0 Watt switch)
                        # NOTE: SB2: Preset must be replaced by house demand for SB2 when running auto usage mode
                        preset = devData.get("set_load_power") or device.get(
                            "set_output_power"
                        )
                        out = devData.get("output_power") or device.get("output_power")
                        solar = devData.get("photovoltaic_power") or device.get(
                            "input_power"
                        )
                        generation = int(device.get("generation", 0))
                        charge = devData.get("charging_power") or device.get(
                            "charging_power"
                        )
                        homeload = devData.get("to_home_load") or device.get(
                            "to_home_load"
                        )
                        demand = devData.get("home_load_power") or 0
                        # use house demand for preset if in auto mode
                        if generation > 1 and (
                            (
                                device.get("preset_usage_mode")
                                or SolixDefaults.USAGE_MODE
                            )
                            in [SolarbankUsageMode.smartmeter.value,SolarbankUsageMode.smartplugs.value]
                        ):
                            preset = demand
                        if (
                            description == SolarbankStatus.charge.name
                            and preset is not None
                            and out is not None
                            and solar is not None
                        ):
                            with contextlib.suppress(ValueError):
                                if (
                                    int(out) == 0 and int(solar) > int(preset)
                                    # and generation < 2
                                ):
                                    # Charge and 0 W output while solar larger than preset must be active charge priority
                                    description = SolarbankStatus.charge_priority.name
                                elif int(out) > 0:
                                    # Charge with output must be bypass charging
                                    description = SolarbankStatus.charge_bypass.name
                        elif (
                            description == SolarbankStatus.detection.name
                            and generation > 1
                            and charge is not None
                            and homeload is not None
                            and preset is not None
                        ):
                            with contextlib.suppress(ValueError):
                                # Charge > 0 and home load < demand must be enforced charging
                                if int(charge) > 0 and int(homeload) < int(preset):
                                    description = SolarbankStatus.protection_charge.name
                        elif (
                            description == SolarbankStatus.bypass.name
                            and generation > 1
                            and charge is not None
                        ):
                            with contextlib.suppress(ValueError):
                                # New SB2 Mode for Bypass and discharge
                                if int(charge) < 0:
                                    description = SolarbankStatus.bypass_discharge.name

                        device.update({"charging_status_desc": description})
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
                        generation = int(device.get("generation", 0))
                        cnt = device.get("solarbank_count", 0)
                        if generation >= 2:
                            # Solarbank 2 schedule
                            device.update(
                                {
                                    "preset_system_output_power": value.get(
                                        "default_home_load"
                                    )
                                    or SolixDefaults.PRESET_NOSCHEDULE,
                                    "preset_usage_mode": value.get("mode_type")
                                    or SolixDefaults.USAGE_MODE,
                                }
                            )
                        else:
                            # Solarbank 1 schedule
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
                        now: datetime = datetime.now().time().replace(microsecond=0)
                        sys_power = None
                        dev_power = None
                        # set now to new daytime if close to end of day
                        if now >= datetime.strptime("23:59:58", "%H:%M:%S").time():
                            now = datetime.strptime("00:00", "%H:%M").time()
                        if generation >= 2:
                            # Solarbank 2 schedule, weekday starts with 0=Sunday)
                            # datetime isoweekday starts with 1=Monday - 7 = Sunday, strftime('%w') starts also 0 = Sunday
                            weekday = int(datetime.now().strftime("%w"))
                            day_ranges = next(
                                iter(
                                    [
                                        day.get("ranges") or []
                                        for day in (
                                            value.get("custom_rate_plan") or [{}]
                                        )
                                        if weekday in (day.get("week") or [])
                                    ]
                                ),
                                [],
                            )
                            for slot in day_ranges:
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
                                        sys_power = slot.get("power")
                                        device.update(
                                            {
                                                "preset_system_output_power": sys_power,
                                            }
                                        )
                                        break
                            # adjust schedule preset for eventual reuse as active presets
                            # Active Preset must only be considered if usage mode is manual
                            sys_power = str(device.get("preset_system_output_power") or "") if (value.get("mode_type") or 0) == SolarbankUsageMode.manual.value else None
                            dev_power = sys_power
                        else:
                            # Solarbank 1 schedule
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
                                        preset_power = (
                                            slot.get("appliance_loads") or [{}]
                                        )[0].get("power")
                                        export = slot.get("turn_on")
                                        prio = slot.get("charge_priority")
                                        device.update(
                                            {
                                                "preset_system_output_power": preset_power,
                                                "preset_allow_export": export,
                                                "preset_charge_priority": prio,
                                            }
                                        )
                                        # add presets for dual solarbank setups, default to None if schedule does not support new keys yet
                                        power_mode = slot.get("power_setting_mode")
                                        dev_presets = slot.get(
                                            "device_power_loads"
                                        ) or [{}]
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
                                        break
                            # adjust schedule presets for eventual reuse as active presets
                            # Charge priority and SOC must only be considered if MI80 inverter is configured for SB1
                            prio = (device.get("preset_charge_priority") or 0) if ((device.get("solar_info") or {}).get("solar_model") or "") == "A5143" else 0
                            if device.get("preset_allow_export") and int(prio) <= int(device.get("battery_soc") or "0"):
                                sys_power = str(device.get("preset_system_output_power") or "")
                                # active device power depends on SB count
                                dev_power = device.get("preset_device_output_power") or None
                                dev_power = str(dev_power if dev_power is not None and cnt > 1 else sys_power)
                            else:
                                sys_power = "0"
                                dev_power = "0"
                        # update appliance load in site cache upon device details or schedule updates not triggered by sites update
                        if not devData.get("retain_load") and (mysite:= self.sites.get(device.get("site_id") or "") or {}) and sys_power:
                            mysite.update({"retain_load": sys_power})
                            # update also device fields for output power if not provided along with schedule update
                            if not devData.get("current_home_load") and sys_power:
                                device.update({"set_system_output_power": sys_power})
                                if not devData.get("parallel_home_load") and dev_power:
                                    device.update({"set_output_power": dev_power})

                    # inverter specific keys
                    elif key in ["generate_power"]:
                        device.update({key: str(value)})

                    # smartmeter specific keys
                    elif key in ["grid_status"]:
                        device.update({"grid_status": str(value)})
                        # decode the grid status into a description
                        description = SmartmeterStatus.unknown.name
                        for status in SmartmeterStatus:
                            if str(value) == status.value:
                                description = status.name
                                break
                        device.update({"grid_status_desc": description})
                    elif key in [
                        "photovoltaic_to_grid_power",
                        "grid_to_home_power",
                    ]:
                        device.update({key: str(value)})

                    # generate extra values when certain conditions are met
                    if key in ["battery_power"] or calc_capacity:
                        # generate battery values when soc updated or device name changed or PN is known or exp packs changed
                        # recalculate only with valid data, otherwise init extra fields with 0
                        if devData.get("data_valid", True):
                            if (
                                not (cap := device.get("battery_capacity"))
                                or calc_capacity
                            ):
                                pn = device.get("device_pn") or ""
                                if hasattr(SolixDeviceCapacity, pn):
                                    # get battery capacity from known PNs
                                    cap = getattr(SolixDeviceCapacity, pn)
                                elif (
                                    device.get("type")
                                    == SolixDeviceType.SOLARBANK.value
                                ):
                                    # Derive battery capacity in Wh from latest solarbank name or alias if available
                                    cap = (
                                        (
                                            device.get("name", "")
                                            or devData.get("device_name", "")
                                            or device.get("alias", "")
                                        )
                                        .replace(" 2", "")
                                        .replace("Solarbank E", "")
                                        .replace(" Pro", "")
                                        .replace(" Plus", "")
                                    )
                                # consider battery packs for total device capacity
                                exp = (
                                    devData.get("sub_package_num")
                                    or device.get("sub_package_num")
                                    or 0
                                )
                                if str(cap).isdigit() and str(exp).isdigit():
                                    cap = int(cap) * (1 + int(exp))
                            soc = devData.get("battery_power", "") or device.get(
                                "battery_soc", ""
                            )
                            # Calculate remaining energy in Wh and add values
                            if (
                                cap
                                and soc
                                and str(cap).isdigit()
                                and str(soc).isdigit()
                            ):
                                device.update(
                                    {
                                        "battery_capacity": str(cap),
                                        "battery_energy": str(
                                            int(int(cap) * int(soc) / 100)
                                        ),
                                    }
                                )
                        else:
                            # init calculated fields with 0 if not existing
                            if "battery_capacity" not in device:
                                device.update({"battery_capacity": "0"})
                            if "battery_energy" not in device:
                                device.update({"battery_energy": "0"})

                except Exception as err:  # pylint: disable=broad-exception-caught  # noqa: BLE001
                    self._logger.error(
                        "%s occurred when updating device details for key %s with value %s: %s",
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

    async def update_sites(
        self, siteId: str | None = None, fromFile: bool = False
    ) -> dict:  # noqa: C901
        """Create/Update api sites cache structure."""
        return await poller.update_sites(self, siteId=siteId, fromFile=fromFile)

    async def update_site_details(
        self, fromFile: bool = False, exclude: set | None = None
    ) -> dict:
        """Add/Update site details in api sites cache structure."""
        return await poller.update_site_details(
            self, fromFile=fromFile, exclude=exclude
        )

    async def update_device_energy(
        self, fromFile: bool = False, exclude: set | None = None
    ) -> dict:
        """Add/Update energy details in api sites cache structure."""
        return await poller.update_device_energy(
            self, fromFile=fromFile, exclude=exclude
        )

    async def update_device_details(
        self, fromFile: bool = False, exclude: set | None = None
    ) -> dict:
        """Create/Update device details in api devices cache structure."""
        return await poller.update_device_details(
            self, fromFile=fromFile, exclude=exclude
        )

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
            resp = await self._loadFromFile(
                os.path.join(self._testdir, "site_rules.json")
            )
        else:
            resp = await self.request("post", API_ENDPOINTS["site_rules"])
        return resp.get("data") or {}

    async def get_site_list(self, fromFile: bool = False) -> dict:
        """Get the site list.

        Example data:
        {'site_list': [{'site_id': 'efaca6b5-f4a0-e82e-3b2e-6b9cf90ded8c', 'site_name': 'BKW', 'site_img': '', 'device_type_list': [3], 'ms_type': 2, 'power_site_type': 2, 'is_allow_delete': True}]}
        """
        if fromFile:
            resp = await self._loadFromFile(
                os.path.join(self._testdir, "site_list.json")
            )
        else:
            resp = await self.request("post", API_ENDPOINTS["site_list"])
        return resp.get("data") or {}

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
            resp = await self.request("post", API_ENDPOINTS["scene_info"], json=data)
        return resp.get("data") or {}

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
            resp = await self._loadFromFile(
                os.path.join(self._testdir, "homepage.json")
            )
        else:
            resp = await self.request("post", API_ENDPOINTS["homepage"])
        return resp.get("data") or {}

    async def get_bind_devices(self, fromFile: bool = False) -> dict:
        """Get the bind device information, contains firmware level of devices.

        Example data:
        {"data": [{"device_sn":"9JVB42LJK8J0P5RY","product_code":"A17C0","bt_ble_id":"BC:A2:AF:C7:55:F9","bt_ble_mac":"BCA2AFC755F9","device_name":"Solarbank E1600","alias_name":"Solarbank E1600",
        "img_url":"https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/e9478c2d-e665-4d84-95d7-dd4844f82055/20230719-144818.png",
        "link_time":1695392302068,"wifi_online":false,"wifi_name":"","relate_type":["ble","wifi"],"charge":false,"bws_surplus":0,"device_sw_version":"v1.4.4","has_manual":false}]}
        """
        if fromFile:
            resp = await self._loadFromFile(
                os.path.join(self._testdir, "bind_devices.json")
            )
        else:
            resp = await self.request("post", API_ENDPOINTS["bind_devices"])
        data = resp.get("data") or {}
        active_devices = set()
        for device in data.get("data") or []:
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
            resp = await self._loadFromFile(
                os.path.join(self._testdir, "user_devices.json")
            )
        else:
            resp = await self.request("post", API_ENDPOINTS["user_devices"])
        return resp.get("data") or {}

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
            resp = await self.request("post", API_ENDPOINTS["charging_devices"])
        return resp.get("data") or {}

    async def get_solar_info(self, solarbankSn: str, fromFile: bool = False) -> dict:
        """Get the solar info that is configured for a solarbank.

        Example data:
        {"brand_id": "3a9930f5-74ef-4e41-a797-04e6b33d3f0f","solar_brand": "ANKER","solar_model": "A5140","solar_sn": "","solar_model_name": "MI60 Microinverter"}
        """
        data = {"solarbank_sn": solarbankSn}
        if fromFile:
            resp = await self._loadFromFile(
                os.path.join(self._testdir, f"solar_info_{solarbankSn}.json")
            )
        else:
            resp = await self.request("post", API_ENDPOINTS["solar_info"], json=data)
        data = resp.get("data") or {}
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
                "post", API_ENDPOINTS["compatible_process"], json=data
            )
        data = resp.get("data") or {}
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
            resp = await self._loadFromFile(
                os.path.join(self._testdir, "auto_upgrade.json")
            )
        else:
            resp = await self.request("post", API_ENDPOINTS["get_auto_upgrade"])
        data = resp.get("data") or {}
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
        """Set auto upgrade switches for given device dictionary.

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
                await self.request("post", API_ENDPOINTS["set_auto_upgrade"], json=data)
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
            resp = await self.request("post", API_ENDPOINTS["wifi_list"], json=data)
        return resp.get("data") or {}

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
            resp = await self.request("post", API_ENDPOINTS["get_cutoff"], json=data)
        data = resp.get("data") or {}
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
        code = (await self.request("post", API_ENDPOINTS["set_cutoff"], json=data)).get(
            "code"
        )
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
                "post", API_ENDPOINTS["get_site_price"], json=data
            )
        data = resp.get("data") or {}
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
            await self.request("post", API_ENDPOINTS["update_site_price"], json=data)
        ).get("code")
        if not isinstance(code, int) or int(code) != 0:
            return False
        # update the data in api dict
        await self.get_site_price(siteId=siteId)
        return True

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
                "post", API_ENDPOINTS["get_device_fittings"], json=data
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
            resp = await self.request("post", API_ENDPOINTS["get_ota_info"], json=data)
        return resp.get("data") or {}

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
                "post", API_ENDPOINTS["get_ota_update"], json=data
            )
        # update device details only if valid response for a given sn
        if (data := resp.get("data") or {}) and deviceSn:
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
                "post", API_ENDPOINTS["check_upgrade_record"], json=data
            )
        return resp.get("data") or {}

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
                "post", API_ENDPOINTS["get_upgrade_record"], json=data
            )
        return resp.get("data") or {}

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
            resp = await self.request("get", API_ENDPOINTS["get_message_unread"])
        # save unread msg flag in each known site
        data = resp.get("data") or {}
        for siteId in self.sites:
            self._update_site(siteId, data)
        return data
