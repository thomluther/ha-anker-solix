"""Default definitions required for the Anker Power/Solix Cloud API."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, IntEnum
from typing import ClassVar

# API servers per region. Country assignment not clear, defaulting to EU server
API_SERVERS = {
    "eu": "https://ankerpower-api-eu.anker.com",
    "com": "https://ankerpower-api.anker.com",
}
API_LOGIN = "passport/login"
API_HEADERS = {
    "Content-Type": "application/json",
    "Model-Type": "DESKTOP",
    "App-Name": "anker_power",
    "Os-Type": "android",
}
API_COUNTRIES = {
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
        "DE",
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
API_ENDPOINTS = {
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
    "get_device_attributes": "power_service/v1/app/device/get_device_attrs",  # for solarbank 2 and/or smartreader? NOT IMPLEMENTED YET
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
    '/power_service/v1/site/get_comb_addable_sites'
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
    'power_service/v1/app/device/set_device_attrs', # for solarbank 2 and/or smartreader?
    'power_service/v1/app/device/get_mes_device_info', # shows laser_sn field but no more info
    'power_service/v1/app/device/get_relate_belong' # shows belonging of site type for given device
    'power_service/v1/get_message_not_disturb',  # get do not disturb messages settings
    'power_service/v1/message_not_disturb',  # change do not disurb messages settings
    'power_service/v1/read_message',
    'power_service/v1/add_message',
    'power_service/v1/del_message',
    'app/devicemanage/update_relate_device_info',
    'app/cloudstor/get_app_up_token_general',
    'app/logging/get_device_logging',
    'app/devicerelation/up_alias_name',  # Update Alias name of device? Fails with (10003) Failed to request
    'app/devicerelation/un_relate_and_unbind_device',
    'app/devicerelation/relate_device',
    'app/push/clear_count',
    'app/ota/batch/check_update',
PPS and Power Panel related:
    "charging_energy_service/energy_statistics",  # Energy stats for PPS and Home Panel
    "charging_energy_service/get_system_running_info", # Cumulative Home/System Energy Savings since Home creation date
    "charging_energy_service/get_device_infos", # Home Panel Info
    "charging_energy_service/get_rom_versions”, # Check for firmware update and download available packages
    "charging_energy_service/get_error_infos", # Unknown at this time
    "charging_energy_service/get_wifi_info", # Displays WiFi network connected to Home Power Panel
    "charging_energy_service/get_installation_inspection", # Unknown at this time - appears to say which page last viewed on App
    "charging_energy_service/sync_installation_inspection", #Unknown at this time
    "charging_energy_service/get_utility_rate_plan",
    "charging_energy_service/report_device_data",
    "charging_energy_service/restart_peak_session",
    "charging_energy_service/preprocess_utility_rate_plan",
    "charging_energy_service/ack_utility_rate_plan",
    "charging_energy_service/get_configs",
    "charging_energy_service/adjust_station_price_unit",
    "charging_energy_service/sync_config",
    "charging_energy_service/get_sns", # Displays Serial Numbers of attached PPS in Home
    "charging_energy_service/get_world_monetary_unit",

    "charging_hes_svc/ota",
    "charging_hes_svc/check_update",
    "charging_hes_svc/get_installer_info",
    "charging_hes_svc/download_energy_statistics",
    "charging_hes_svc/get_wifi_info", # ssid and rssi for a device
    "charging_hes_svc/update_wifi_config",
    "charging_hes_svc/get_device_product_info", # List of Anker power devices
    "charging_hes_svc/report_device_data",
    "charging_hes_svc/get_auto_disaster_prepare_status",
    "charging_hes_svc/get_install_info",
    "charging_hes_svc/get_device_pn_info",
    "charging_hes_svc/get_device_card_list",
    "charging_hes_svc/get_device_card_details",
    "charging_hes_svc/get_system_running_time",
    "charging_hes_svc/get_system_profit_detail",
    "charging_hes_svc/get_tou_price_plan_detail",
    "charging_hes_svc/get_electric_utility_and_electric_plan_list",
    "charging_hes_svc/get_station_config_and_status",
    "charging_hes_svc/get_current_disaster_prepare_details",
    "charging_hes_svc/adjust_station_price_unit",
    "charging_hes_svc/update_hes_utility_rate_plan",
    "charging_hes_svc/quit_auto_disaster_prepare",
    "charging_hes_svc/restart_peak_session",
    "charging_hes_svc/check_function",
    "charging_hes_svc/remove_user_fault_info",
    "charging_hes_svc/user_event_alarm",
    "charging_hes_svc/sync_back_up_history",
    "charging_hes_svc/cancel_pop",


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
    """Enumeration for Anker Solix device types."""

    SYSTEM = "system"
    SOLARBANK = "solarbank"
    INVERTER = "inverter"
    SMARTMETER = "smartmeter"
    SMARTPLUG = "smartplug"
    PPS = "pps"
    POWERPANEL = "powerpanel"
    POWERCOOLER = "powercooler"
    HES = "hes"


class SolixParmType(Enum):
    """Enumeration for Anker Solix Parameter types."""

    SOLARBANK_SCHEDULE = "4"
    SOLARBANK_2_SCHEDULE = "6"


class SolarbankPowerMode(IntEnum):
    """Enumeration for Anker Solix Solarbank Power setting modes."""

    normal = 1
    advanced = 2

class SolarbankUsageMode(IntEnum):
    """Enumeration for Anker Solix Solarbank Power Usage modes."""

    automatic = 1
    unknown_2 = 2   # Does it exist?
    manual = 3

@dataclass(frozen=True)
class ApiCategories:
    """Dataclass to specify supported Api categories for regular Api cache refresh cycles."""

    site_price: str = "site_price"
    device_auto_upgrade: str = "device_auto_upgrade"
    solar_energy: str = "solar_energy"
    solarbank_energy: str = "solarbank_energy"
    solarbank_fittings: str = "solarbank_fittings"
    solarbank_cutoff: str = "solarbank_cutoff"
    solarbank_solar_info: str = "solarbank_solar_info"
    smartmeter_energy: str = "smartmeter_energy"
    smartplug_energy: str = "smartplug_energy"

@dataclass(frozen=True)
class SolixDeviceCapacity:
    """Dataclass for Anker Solix device battery capacities in Wh by Part Number."""

    A17C0: int = 1600  # SOLIX E1600 Solarbank
    A17C1: int = 1600  # SOLIX E1600 Solarbank 2 Pro
    A17C2: int = 1600  # SOLIX E1600 Solarbank 2
    A17C3: int = 1600  # SOLIX E1600 Solarbank 2 Plus
    A1720: int = 256  # Anker PowerHouse 521 Portable Power Station
    A1751: int = 512  # Anker PowerHouse 535 Portable Power Station
    A1753: int = 768  # SOLIX C800 Portable Power Station
    A1754: int = 768  # SOLIX C800 Plus Portable Power Station
    A1755: int = 768  # SOLIX C800X Portable Power Station
    A1760: int = 1024  # Anker PowerHouse 555 Portable Power Station
    A1761: int = 1056  # SOLIX C1000(X) Portable Power Station
    # A17C1: int = 1056  # SOLIX C1000 Expansion Battery # same PN as Solarbank 2?
    A1770: int = 1229  # Anker PowerHouse 757 Portable Power Station
    A1771: int = 1229  # SOLIX F1200 Portable Power Station
    A1772: int = 1536  # SOLIX F1500 Portable Power Station
    A1780: int = 2048  # SOLIX F2000 Portable Power Station (PowerHouse 767)
    A1780_1: int = 2048  # Expansion Battery for F2000
    A1780P: int = 2048  # SOLIX F2000 Portable Power Station (PowerHouse 767) with WLAN
    A1781: int = 2560  # SOLIX F2600 Portable Power Station
    A1790: int = 3840  # SOLIX F3800 Portable Power Station
    A1790_1: int = 3840  # SOLIX BP3800 Expansion Battery for F3800
    A5220: int = 5000  # SOLIX X1 Battery module


@dataclass(frozen=True)
class SolixDeviceCategory:
    """Dataclass for Anker Solix device types by Part Number to be used for standalone/unbound device categorization."""

    # Solarbanks
    A17C0: str = (
        SolixDeviceType.SOLARBANK.value + "_1"
    )  # SOLIX E1600 Solarbank, generation 1
    A17C1: str = (
        SolixDeviceType.SOLARBANK.value + "_2"
    )  # SOLIX E1600 Solarbank 2 Pro, generation 2
    A17C2: str = (
        SolixDeviceType.SOLARBANK.value + "_2"
    )  # SOLIX E1600 Solarbank 2, generation 2
    A17C3: str = (
        SolixDeviceType.SOLARBANK.value + "_2"
    )  # SOLIX E1600 Solarbank 2 Plus, generation 2
    # Inverter
    A5140: str = SolixDeviceType.INVERTER.value  # MI60 Inverter
    A5143: str = SolixDeviceType.INVERTER.value  # MI80 Inverter
    # Smart Meter
    A17X7: str = SolixDeviceType.SMARTMETER.value  # SOLIX Smart Meter
    # Smart Plug
    A17X8: str = SolixDeviceType.SMARTPLUG.value  # SOLIX Smart Plug
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
    A17B1: str = (
        SolixDeviceType.POWERPANEL.value
    )  # SOLIX Home Power Panel for SOLIX F3800
    # Home Energy System (HES)
    A5102: str = SolixDeviceType.HES.value  # SOLIX X1 Energy module 1P
    A5103: str = SolixDeviceType.HES.value  # SOLIX X1 Energy module 3P
    A5220: str = SolixDeviceType.HES.value  # SOLIX X1 Battery module
    # Power Cooler
    A17A0: str = SolixDeviceType.POWERCOOLER.value  # SOLIX Power Cooler 30
    A17A1: str = SolixDeviceType.POWERCOOLER.value  # SOLIX Power Cooler 40
    A17A2: str = SolixDeviceType.POWERCOOLER.value  # SOLIX Power Cooler 50


@dataclass(frozen=True)
class SolarbankDeviceMetrics:
    """Dataclass for Anker Solarbank metrics which should be tracked in device details cache depending on model type."""

    A17C0: ClassVar[set[str]] = (
        set()
    )  # SOLIX E1600 Solarbank, single MPPT without channel reporting
    A17C1: ClassVar[set[str]] = {
        "sub_package_num",
        "solar_power_1",
        "solar_power_2",
        "solar_power_3",
        "solar_power_4",
        "ac_power",
        "to_home_load",
    }  # SOLIX E1600 Solarbank 2 Pro, with 4 MPPT channel reporting and AC socket
    A17C2: ClassVar[set[str]] = {
        "sub_package_num",
        "to_home_load",
    }  # SOLIX E1600 Solarbank 2, without MPPT
    A17C3: ClassVar[set[str]] = {
        "sub_package_num",
        "solar_power_1",
        "solar_power_2",
        "to_home_load",
    }  # SOLIX E1600 Solarbank 2 Plus, with 2 MPPT


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
    # Preset usage mode for Solarbank 2 schedules
    USAGE_MODE: int = SolarbankUsageMode.manual.value
    # Charge Priority limit preset for Solarbank schedule timeslot settings
    CHARGE_PRIORITY_MIN: int = 0
    CHARGE_PRIORITY_MAX: int = 100
    CHARGE_PRIORITY_DEF: int = 80
    # Seconds delay for subsequent Api requests in methods to update the Api cache dictionaries
    REQUEST_DELAY_MIN: float = 0.0
    REQUEST_DELAY_MAX: float = 5.0
    REQUEST_DELAY_DEF: float = 0.3


class SolixDeviceStatus(Enum):
    """Enumeration for Anker Solix Device status."""

    # The device status code seems to be used for cloud connection status.
    offline = "0"
    online = "1"
    unknown = "unknown"

class SolarbankStatus(Enum):
    """Enumeration for Anker Solix Solarbank status."""

    detection = "0"  # Rare for SB1, frequent for SB2 especially in combination with Smartmeter in the morning
    protection_charge = "03"  # For SB2 only when there is charge while output below demand in detection mode
    bypass = "1"  # Bypass solar without charge
    bypass_discharge = (
        "12"  # pseudo state for SB2 if discharging in bypass mode, not possible for SB1
    )
    discharge = "2"  # only seen if no solar available
    charge = "3"  # normal charge for battery
    charge_bypass = "31"  # pseudo state, the solarbank does not distinguish this
    charge_priority = "37"  # pseudo state, the solarbank does not distinguish this, when no output power exists while preset is ignored
    wakeup = "4"  # Not clear what happens during this state, but observed short intervals during night, probably hourly? resync with the cloud
    # TODO(3): Add descriptions once status code usage is observed/known
    # code 5 was not observed yet
    full_bypass = "6"  # seen at cold temperature, when battery must not be charged and the Solarbank bypasses all directly to inverter, also solar power < 25 W. More often with SB2
    standby = "7"
    unknown = "unknown"


class SmartmeterStatus(Enum):
    """Enumeration for Anker Solix Smartmeter status."""

    # TODO(#106) Update Smartmeter grid status description once known
    ok = "0"  # normal grid state when smart meter is measuring
    unknown_1 = "1"  # does it exist?
    unknown_2 = "2"  # does it exist?
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


@dataclass
class Solarbank2Timeslot:
    """Dataclass to define customizable attributes of an Anker Solix Solarbank 2 time slot as used for the schedule definition or update."""

    start_time: datetime
    end_time: datetime
    appliance_load: int | None = None  # mapped to appliance_load setting
    weekdays: set[int] | None = None  # set of weekdays where this slow applies, defaulting to all if None. Sun = 0, Sat = 6
