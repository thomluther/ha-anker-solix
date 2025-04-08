"""Default definitions required for the Anker Power/Solix Cloud API."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, IntEnum, StrEnum
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

"""Following are the Anker Power/Solix Cloud API power_service endpoints known so far. Some are common, others are mainly for balcony power systems"""
API_ENDPOINTS = {
    "homepage": "power_service/v1/site/get_site_homepage",  # Scene info for configured site(s), content as presented on App Home Page (mostly empty for shared accounts)
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
    "get_auto_upgrade": "power_service/v1/app/get_auto_upgrade",  # List of Auto-Upgrade configuration and enabled devices, only works for site owner account
    "set_auto_upgrade": "power_service/v1/app/set_auto_upgrade",  # Set/Enable Auto-Upgrade configuration, works only for site owner account
    "bind_devices": "power_service/v1/app/get_relate_and_bind_devices",  # List with details of locally connected/bound devices, includes firmware version, works only for owner account
    "get_device_load": "power_service/v1/app/device/get_device_home_load",  # Get defined device schedule (same data as provided with device param query)
    "set_device_load": "power_service/v1/app/device/set_device_home_load",  # Set defined device schedule, Accepts the new schedule, but does NOT change it? Maybe future use for schedules per device
    "get_ota_info": "power_service/v1/app/compatible/get_ota_info",  # Get OTA status for solarbank and/or inverter serials
    "get_ota_update": "power_service/v1/app/compatible/get_ota_update",  # Get info of available OTA update
    "solar_info": "power_service/v1/app/compatible/get_compatible_solar_info",  # Solar inverter definition for solarbanks, works only with owner account
    "get_cutoff": "power_service/v1/app/compatible/get_power_cutoff",  # Get Power Cutoff settings (Min SOC) for provided site id and device sn, works only with owner account
    "set_cutoff": "power_service/v1/app/compatible/set_power_cutoff",  # Set Min SOC for device, only works for owner accounts
    "compatible_process": "power_service/v1/app/compatible/get_compatible_process",  # contains solar_info plus OTA processing codes, works only with owner account
    "get_device_fittings": "power_service/v1/app/get_relate_device_fittings",  # Device fittings for given site id and device sn. Shows Accessories like Solarbank 0W Switch info
    "energy_analysis": "power_service/v1/site/energy_analysis",  # Fetch energy data for given time frames
    "home_load_chart": "power_service/v1/site/get_home_load_chart",  # Fetch data as displayed in home load chart for schedule adjustments for given site_id and optional device SN (empty if solarbank not connected)
    "get_upgrade_record": "power_service/v1/app/get_upgrade_record",  # get list of firmware update history
    "check_upgrade_record": "power_service/v1/app/check_upgrade_record",  # show an upgrade record for the device, types 1-3 show different info, only works for owner account
    "get_message_unread": "power_service/v1/get_message_unread",  # GET method to show if there are unread messages for account
    "get_message": "power_service/v1/get_message",  # GET method to list Messages from certain time, not explored or used (last_time format unknown)
    "get_product_categories": "power_service/v1/product_categories",  # GET method to list all supported products with details and web picture links
    "get_product_accessories": "power_service/v1/product_accessories",  # GET method to list all supported products accessories with details and web picture links
    "get_device_attributes": "power_service/v1/app/device/get_device_attrs",  # for solarbank 2 and/or smart meter? NOT IMPLEMENTED YET
    "get_config": "power_service/v1/app/get_config",  # shows empty config list, also for shared account
    "get_installation": "power_service/v1/app/compatible/get_installation",  # shows install_mode and solar_sn, also for shared account
    "set_installation": "power_service/v1/app/compatible/set_installation",  # not explored yet
    "get_third_platforms": "power_service/v1/app/third/platform/list",  # list supported third party device models
    "get_token_by_userid": "power_service/v1/app/get_token_by_userid",  # get token for authenticated user. Is that the token to be used to query shelly status?
    "get_shelly_status": "power_service/v1/app/get_user_op_shelly_status",  # get op_list with correct token
    "get_currency_list": "power_service/v1/currency/get_list",  # get list of supported currencies for power sites
    "get_ota_batch": "app/ota/batch/check_update",  # get OTA information and latest version for device SN list, works also for shared accounts, but data only received for owner accounts
    "get_mqtt_info": "app/devicemanage/get_user_mqtt_info",  # post method to list mqtt server and certificates for a site, not explored or used
}

"""Following are the Anker Power/Solix Cloud API charging_energy_service endpoints known so far. They are used for Power Panels."""
API_CHARGING_ENDPOINTS = {
    "get_error_info": "charging_energy_service/get_error_infos",  # No input param needed, show errors for account?
    "get_system_running_info": "charging_energy_service/get_system_running_info",  # Cumulative Home/System Energy Savings since Home creation date
    "energy_statistics": "charging_energy_service/energy_statistics",  # Energy stats for PPS and Home Panel, # source type [solar hes grid home pps diesel]
    "get_rom_versions": "charging_energy_service/get_rom_versions",  # Check for firmware update and download available packages, needs owner account
    "get_device_info": "charging_energy_service/get_device_infos",  # Wifi and MAC infos for provided devices, needs owner account
    "get_wifi_info": "charging_energy_service/get_wifi_info",  # Displays WiFi network connected to Home Power Panel, needs owner account
    "get_installation_inspection": "charging_energy_service/get_installation_inspection",  # appears to say which page last viewed on App, needs owner account
    "get_utility_rate_plan": "charging_energy_service/get_utility_rate_plan",  # needs owner account
    "report_device_data": "charging_energy_service/report_device_data",  # ctrol [0 1], works but data is null (may need owner account?)
    "get_configs": "charging_energy_service/get_configs",  # json={"siteId": "SITEID", "sn": "POWERPANELSN", "param_types": []})) # needs owner account, list of parm types not clear
    "get_sns": "charging_energy_service/get_sns",  # json={"main_sn": "POWERPANELSN","macs": ["F38001MAC001","F38002MAC002"]})) # needs owner account, Displays Serial Numbers of attached PPS in Home
    "get_monetary_units": "charging_energy_service/get_world_monetary_unit",  # monetary unit list for system, needs owner account
}

"""Following are the Anker Power/Solix Cloud API charging_hes_svc endpoints known so far. They are used for Home Energy Systems like X1."""
API_HES_SVC_ENDPOINTS = {
    "get_product_info": "charging_hes_svc/get_device_product_info",  # List of Anker HES devices, works with shared account
    "get_heat_pump_plan": "charging_hes_svc/get_heat_pump_plan_json",  # heat pump plan, works with shared account
    "get_electric_plan_list": "charging_hes_svc/get_electric_utility_and_electric_plan_list",  # Energy plan if available for country & state combination, works with shared account
    "get_system_running_info": "charging_hes_svc/get_system_running_info",  # system runtime info, works with shared account
    "energy_statistics": "charging_hes_svc/get_energy_statistics",  # Energy stats for HES, # source type [solar hes grid home]
    "get_monetary_units": "charging_hes_svc/get_world_monetary_unit",  # monetary unit list for system, works with shared account
    "get_install_info": "charging_hes_svc/get_install_info",  # get system install info, works with shared account. Shows installation location
    "get_wifi_info": "charging_hes_svc/get_wifi_info",  # get device wifi info, works with shared account
    "get_installer_info": "charging_hes_svc/get_installer_info",  # no shared account access, Shows contact information of the installer
    "get_system_running_time": "charging_hes_svc/get_system_running_time",  # no shared account access, needs HES site?
    "get_mi_layout": "charging_hes_svc/get_mi_layout",  # no shared account access, needs HES site?
    "get_conn_net_tips": "charging_hes_svc/get_conn_net_tips",  # no shared account access, needs HES site?
    "get_hes_dev_info": "charging_hes_svc/get_hes_dev_info",  # works with shared account, lists hes device structure and SNs
    "report_device_data": "charging_hes_svc/report_device_data",  # no shared account access, needs HES site and installer system?
}

""" Other endpoints neither implemented nor explored: 41 + 40 used => 81
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
    'power_service/v1/site/get_comb_addable_sites',
    'power_service/v1/site/shift_power_site_type',
    'power_service/v1/app/compatible/set_ota_update',
    'power_service/v1/app/compatible/save_ota_complete_status',
    'power_service/v1/app/compatible/check_third_sn',
    'power_service/v1/app/compatible/save_compatible_solar',
    'power_service/v1/app/compatible/get_confirm_permissions',
    'power_service/v1/app/compatible/confirm_permissions_settings',
    'power_service/v1/app/after_sale/check_popup',
    'power_service/v1/app/after_sale/check_sn',
    'power_service/v1/app/after_sale/mark_sn',
    'power_service/v1/app/share_site/anonymous_join_site',
    'power_service/v1/app/share_site/delete_site_member',
    'power_service/v1/app/share_site/invite_member',
    'power_service/v1/app/share_site/delete_inviting_member',
    'power_service/v1/app/share_site/get_invited_list',
    'power_service/v1/app/share_site/join_site',
    'power_service/v1/app/upgrade_event_report', # post an entry to upgrade event report
    'power_service/v1/app/get_phonecode_list',
    'power_service/v1/app/get_annual_report',  # new report starting Jan 2025?
    'power_service/v1/app/device/remove_param_config_key'
    'power_service/v1/app/device/set_device_attrs', # for solarbank 2 and/or smart meter?
    'power_service/v1/app/device/get_mes_device_info', # shows laser_sn field but no more info
    'power_service/v1/app/device/get_relate_belong' # shows belonging of site type for given device
    'power_service/v1/get_message_not_disturb',  # get do not disturb messages settings
    'power_service/v1/message_not_disturb',  # change do not disturb messages settings
    'power_service/v1/read_message',
    'power_service/v1/add_message',
    'power_service/v1/del_message',

App related: 10 + 2 used => 12 total
    'app/devicemanage/update_relate_device_info',
    'app/cloudstor/get_app_up_token_general',
    'app/cloudstor/get_app_up_token_without_login',
    'app/logging/get_device_logging',
    'app/logging/upload',
    'app/devicerelation/up_alias_name',  # Update Alias name of device? Fails with (10003) Failed to request
    'app/devicerelation/un_relate_and_unbind_device',
    'app/devicerelation/relate_device',
    'app/push/clear_count',
    'app/push/register_push_token',

Passport related: 2 + 0 used => 2 total
    'passport/get_user_param', # specify param_type which must be parsable as list of int, but does not show anything in response
    'passport/get_subscriptions,  #  get user email, accept_survey, subscribe, phone_number, sms_subscribe

PPS and Power Panel related: 6 + 12 used => 18 total
    "charging_energy_service/sync_installation_inspection", #Unknown at this time
    "charging_energy_service/sync_config",
    "charging_energy_service/restart_peak_session",
    "charging_energy_service/preprocess_utility_rate_plan",
    "charging_energy_service/ack_utility_rate_plan",
    "charging_energy_service/adjust_station_price_unit",

Home Energy System related (X1): 37 + 14 used => 51 total
    "charging_hes_svc/adjust_station_price_unit",
    "charging_hes_svc/cancel_pop",
    "charging_hes_svc/check_update",
    "charging_hes_svc/check_device_bluetooth_password",
    "charging_hes_svc/check_function",
    "charging_hes_svc/device_command",
    "charging_hes_svc/download_energy_statistics",
    "charging_hes_svc/get_auto_disaster_prepare_status",
    "charging_hes_svc/get_auto_disaster_prepare_detail",
    "charging_hes_svc/get_back_up_history",
    "charging_hes_svc/get_current_disaster_prepare_detail",
    "charging_hes_svc/get_device_command",
    "charging_hes_svc/get_device_pn_info",
    "charging_hes_svc/get_device_card_list",
    "charging_hes_svc/get_device_card_details",
    "charging_hes_svc/get_external_device_config",
    "charging_hes_svc/get_site_mi_list",
    "charging_hes_svc/get_station_config_and_status",
    "charging_hes_svc/get_system_device_time",
    "charging_hes_svc/get_system_profit_detail",
    "charging_hes_svc/get_tou_price_plan_detail",
    "charging_hes_svc/get_user_fault_info",
    "charging_hes_svc/get_utility_rate_plan",
    "charging_hes_svc/get_vpp_check_code",
    "charging_hes_svc/get_vpp_service_policy_by_agg_user",
    "charging_hes_svc/update_device_info_by_app",
    "charging_hes_svc/update_hes_utility_rate_plan",
    "charging_hes_svc/update_wifi_config",
    "charging_hes_svc/upload_device_status",
    "charging_hes_svc/user_event_alarm",
    "charging_hes_svc/user_fault_alarm",
    "charging_hes_svc/ota",
    "charging_hes_svc/quit_auto_disaster_prepare",
    "charging_hes_svc/remove_user_fault_info",
    "charging_hes_svc/restart_peak_session",
    "charging_hes_svc/start",
    "charging_hes_svc/sync_back_up_history",

related to what, seem to work with Power Panel sites: 5 + 0 used => 5 total
    'charging_disaster_prepared/get_site_device_disaster', # {"identifier_id": siteId, "type": 2})) # works with Power panel site and shared account
    'charging_disaster_prepared/get_site_device_disaster_status', # {"identifier_id": siteId, "type": 2})) # works with Power panel site and shared account
    'charging_disaster_prepared/set_site_device_disaster',
    'charging_disaster_prepared/quit_disaster_prepare',
    'charging_disaster_prepared/get_support_func', # {"identifier_id": siteId, "type": 2})) # works with Power panel site and shared account

related to what?: 10 + 0 used => 10 total
    'mini_power/v1/app/charging/get_charging_mode_list',
    'mini_power/v1/app/charging/update_charging_mode',
    'mini_power/v1/app/charging/add_charging_mode',
    'mini_power/v1/app/charging/delete_charging_mode',
    'mini_power/v1/app/setting/set_charging_mode_status',
    'mini_power/v1/app/egg/get_easter_egg_trigger_list',
    'mini_power/v1/app/egg/add_easter_egg_trigger_record',
    'mini_power/v1/app/egg/report_easter_egg_trigger_status',
    'mini_power/v1/app/setting/get_device_setting',
    'mini_power/v1/app/power/get_day_power_data',


Structure of the JSON response for an API Login Request:
An unexpired token_id must be used for API request, along with the gtoken which is an MD5 hash of the returned(encrypted) user_id.
The combination of the provided token and MD5 hashed user_id authenticate the client to the server.
The Login Response is cached in a JSON file per email user account and can be reused by this API class without further login request.

ATTENTION: Anker allows only 1 active token on the server per user account. Any login for the same account (e.g. via Anker mobile App) will kickoff the token used in this Api instance and further requests are no longer authorized.
Currently, the Api will re-authenticate automatically and therefore may kick off the other user that obtained the actual access token (e.g. kick out the App user again when used for regular Api requests)

NOTES: Parallel Api instances should use different user accounts. They may work in parallel when all using the same cached authentication data. The first API instance with failed authorization will restart a new Login request and updates
the cached JSON file. Other instances should recognize an update of the cached JSON file and will refresh their login credentials in the instance for the actual token and gtoken without new login request.
"""

# Following are the JSON filename prefixes for exported endpoint names as defined previously
API_FILEPREFIXES = {
    # power_service endpoint file prefixes
    "homepage": "homepage",
    "site_list": "site_list",
    "bind_devices": "bind_devices",
    "user_devices": "user_devices",
    "charging_devices": "charging_devices",
    "get_auto_upgrade": "auto_upgrade",
    "get_config": "config",
    "site_rules": "list_site_rules",
    "get_installation": "installation",
    "get_site_price": "price",
    "get_device_parm": "device_parm",
    "get_product_categories": "list_products",
    "get_product_accessories": "list_accessories",
    "get_third_platforms": "list_third_platforms",
    "get_token_by_userid": "get_token",
    "get_shelly_status": "shelly_status",
    "scene_info": "scene",
    "site_detail": "site_detail",
    "wifi_list": "wifi_list",
    "energy_solarbank": "energy_solarbank",
    "energy_solar_production": "energy_solar_production",
    "energy_home_usage": "energy_home_usage",
    "energy_grid": "energy_grid",
    "solar_info": "solar_info",
    "compatible_process": "compatible_process",
    "get_cutoff": "power_cutoff",
    "get_device_fittings": "device_fittings",
    "get_device_load": "device_load",
    "get_ota_batch": "ota_batch",
    "get_ota_update": "ota_update",
    "get_ota_info": "ota_info",
    "get_upgrade_record": "upgrade_record",
    "check_upgrade_record": "check_upgrade_record",
    "get_device_attributes": "device_attrs",
    "get_message_unread": "message_unread",
    "get_currency_list": "currency_list",
    "api_account": "api_account",
    "api_sites": "api_sites",
    "api_devices": "api_devices",
    # charging_energy_service endpoint file prefixes
    "charging_get_error_info": "charging_error_info",
    "charging_get_system_running_info": "charging_system_running_info",
    "charging_energy_solar": "charging_energy_solar",
    "charging_energy_hes": "charging_energy_hes",
    "charging_energy_pps": "charging_energy_pps",
    "charging_energy_home": "charging_energy_home",
    "charging_energy_grid": "charging_energy_grid",
    "charging_energy_diesel": "charging_energy_diesel",
    "charging_energy_solar_today": "charging_energy_solar_today",
    "charging_energy_hes_today": "charging_energy_hes_today",
    "charging_energy_pps_today": "charging_energy_pps_today",
    "charging_energy_home_today": "charging_energy_home_today",
    "charging_energy_grid_today": "charging_energy_grid_today",
    "charging_energy_diesel_today": "charging_energy_diesel_today",
    "charging_get_rom_versions": "charging_rom_versions",
    "charging_get_device_info": "charging_device_info",
    "charging_get_wifi_info": "charging_wifi_info",
    "charging_get_installation_inspection": "charging_installation_inspection",
    "charging_get_utility_rate_plan": "charging_utility_rate_plan",
    "charging_report_device_data": "charging_report_device_data",
    "charging_get_configs": "charging_configs",
    "charging_get_sns": "charging_sns",
    "charging_get_monetary_units": "charging_monetary_units",
    # charging_energy_service endpoint file prefixes
    "hes_get_product_info": "hes_product_info",
    "hes_get_heat_pump_plan": "hes_heat_pump_plan",
    "hes_get_electric_plan_list": "hes_electric_plan",
    "hes_get_system_running_info": "hes_system_running_info",
    "hes_energy_solar": "hes_energy_solar",
    "hes_energy_hes": "hes_energy_hes",
    "hes_energy_pps": "hes_energy_pps",
    "hes_energy_home": "hes_energy_home",
    "hes_energy_grid": "hes_energy_grid",
    "hes_energy_solar_today": "hes_energy_solar_today",
    "hes_energy_hes_today": "hes_energy_hes_today",
    "hes_energy_pps_today": "hes_energy_pps_today",
    "hes_energy_home_today": "hes_energy_home_today",
    "hes_energy_grid_today": "hes_energy_grid_today",
    "hes_get_monetary_units": "hes_monetary_units",
    "hes_get_install_info": "hes_install_info",
    "hes_get_wifi_info": "hes_wifi_info",
    "hes_get_installer_info": "hes_installer_info",
    "hes_get_system_running_time": "hes_system_running_time",
    "hes_get_mi_layout": "hes_mi_layout",
    "hes_get_conn_net_tips": "hes_conn_net_tips",
    "hes_get_hes_dev_info": "hes_dev_info",
    "hes_report_device_data": "hes_report_device_data",
}


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

    ACCOUNT = "account"
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
    SOLARBANK_SCHEDULE_ENFORCED = "9"


class SolarbankPowerMode(IntEnum):
    """Enumeration for Anker Solix Solarbank 1 Power setting modes."""

    normal = 1
    advanced = 2


class SolarbankDischargePriorityMode(IntEnum):
    """Enumeration for Anker Solix Solarbank 1 Discharge priority setting modes."""

    off = 0
    on = 1


class SolarbankUsageMode(IntEnum):
    """Enumeration for Anker Solix Solarbank 2 Power Usage modes."""

    smartmeter = 1  # AC output based on measured smart meter power
    smartplugs = 2  # AC output based on measured smart plug power
    manual = 3  # manual time plan for home load output
    backup = 4  # This is used to reflect active backup mode in scene_info, but this mode cannot be set directly in schedule and mode is just temporary
    use_time = 5  # Use Time plan with SB2 AC and smart meter


class SolixTariffTypes(IntEnum):
    """Enumeration for Anker Solix Solarbank 2 AC Use Time Tariff Types."""

    NONE = 0  # Pseudo type to reflect no tariff defined
    PEAK = 1  # maximize PV and Battery usage, no AC charge
    MID_PEAK = 2  # maximize PV and Battery usage, no AC charge
    OFF_PEAK = 3  # maximize PV and Battery usage, no AC charge, discharge only above 80% SOC, Reserve charge utilized only for PEAK & MID PEAK times
    VALLEY = (
        4  # AC charge allowed, charge power depends on SOC and available VALLEY time
    )


class SolixPriceTypes(StrEnum):
    """Enumeration for Anker Solix Solarbank 2 AC Use Time Tariff Types."""

    FIXED = "fixed"
    USE_TIME = "use_time"


class SolixDayTypes(StrEnum):
    """Enumeration for Anker Solix Solarbank 2 AC Use Time Day Types."""

    WEEKDAY = "weekday"
    WEEKEND = "weekend"
    ALL = "all"


@dataclass(frozen=True)
class SolarbankRatePlan:
    """Dataclass for Anker Solix Solarbank 2 rate plan types."""

    # rate plan per usage mode
    smartmeter: str = ""  # does not use a plan
    smartplugs: str = "blend_plan"
    manual: str = "custom_rate_plan"
    backup: str = "manual_backup"
    use_time: str = "use_time"


@dataclass(frozen=True)
class ApiEndpointServices:
    """Dataclass to specify supported Api endpoint services. Each service type should be implemented with dedicated Api class."""

    # Note: The service endpoints may not be supported on every cloud server. It may depend on supported Anker products per geo
    power: str = "power_service"
    charging: str = "charging_energy_service"
    hes_svc: str = "charging_hes_svc"


@dataclass(frozen=True)
class ApiCategories:
    """Dataclass to specify supported Api categories for regular Api cache refresh cycles."""

    site_price: str = "site_price"
    device_auto_upgrade: str = "device_auto_upgrade"
    device_tag: str = "device_tag"
    solar_energy: str = "solar_energy"
    solarbank_energy: str = "solarbank_energy"
    solarbank_fittings: str = "solarbank_fittings"
    solarbank_cutoff: str = "solarbank_cutoff"
    solarbank_solar_info: str = "solarbank_solar_info"
    smartmeter_energy: str = "smartmeter_energy"
    smartplug_energy: str = "smartplug_energy"
    powerpanel_energy: str = "powerpanel_energy"
    powerpanel_avg_power: str = "powerpanel_avg_power"
    hes_energy: str = "hes_energy"
    hes_avg_power: str = "hes_avg_power"


@dataclass(frozen=True)
class SolixDeviceNames:
    """Dataclass for Anker Solix device names that are now provided via the various product list queries."""

    SHEM3: str = "Shelly 3EM"
    SHEMP3: str = "Shelly Pro 3EM"


@dataclass(frozen=True)
class SolixDeviceCapacity:
    """Dataclass for Anker Solix device battery capacities in Wh by Part Number."""

    A17C0: int = 1600  # SOLIX E1600 Solarbank
    A17C1: int = 1600  # SOLIX E1600 Solarbank 2 Pro
    A17C2: int = 1600  # SOLIX E1600 Solarbank 2 AC
    A17C3: int = 1600  # SOLIX E1600 Solarbank 2 Plus
    A1720: int = 256  # Anker PowerHouse 521 Portable Power Station
    A1722: int = 288  # SOLIX C300 Portable Power Station
    A1723: int = 230  # SOLIX C200 Portable Power Station
    A1725: int = 230  # SOLIX C200 Portable Power Station
    A1726: int = 288  # SOLIX C300 DC Portable Power Station
    A1727: int = 230  # SOLIX C200 DC Portable Power Station
    A1728: int = 288  # SOLIX C300 X Portable Power Station
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
    A1780P: int = 2048  # SOLIX F2000 Portable Power Station (PowerHouse 767) with WIFI
    A1781: int = 2560  # SOLIX F2600 Portable Power Station
    A1790: int = 3840  # SOLIX F3800 Portable Power Station
    A1790_1: int = 3840  # SOLIX BP3800 Expansion Battery for F3800
    A5220: int = 5000  # SOLIX X1 Battery module


@dataclass(frozen=True)
class SolixSiteType:
    """Dataclass for Anker Solix System/Site types according to the main device in site rules."""

    t_1 = SolixDeviceType.INVERTER.value  # Main A5143
    t_2 = SolixDeviceType.SOLARBANK.value  # Main A17C0 SB1
    t_3 = SolixDeviceType.HES.value  # Main A5103, Note: This is not listed in actual site rules, but X1 export showing type 3 instead of 9 as site rules say
    t_4 = SolixDeviceType.POWERPANEL.value  # Main A17B1
    t_5 = SolixDeviceType.SOLARBANK.value  # Main A17C1 SB2 Pro, can also add SB1
    t_6 = SolixDeviceType.HES.value  # Main A5341
    t_7 = SolixDeviceType.HES.value  # Main A5101
    t_8 = SolixDeviceType.HES.value  # Main A5102
    t_9 = SolixDeviceType.HES.value  # Main A5103
    t_10 = SolixDeviceType.SOLARBANK.value  # Main A17C3 SB2 Plus, can also add SB1
    t_11 = SolixDeviceType.SOLARBANK.value  # Main A17C2 SB2 AC


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
    )  # SOLIX E1600 Solarbank 2 AC, generation 2
    A17C3: str = (
        SolixDeviceType.SOLARBANK.value + "_2"
    )  # SOLIX E1600 Solarbank 2 Plus, generation 2
    # Inverter
    A5140: str = SolixDeviceType.INVERTER.value  # MI60 Inverter
    A5143: str = SolixDeviceType.INVERTER.value  # MI80 Inverter
    # Smart Meter
    A17X7: str = SolixDeviceType.SMARTMETER.value  # SOLIX Smart Meter
    SHEM3: str = SolixDeviceType.SMARTMETER.value  # Shelly 3EM Smart Meter
    SHEMP3: str = SolixDeviceType.SMARTMETER.value  # Shelly 3EM Pro Smart Meter
    # Smart Plug
    A17X8: str = SolixDeviceType.SMARTPLUG.value  # SOLIX Smart Plug
    # Portable Power Stations (PPS)
    A1720: str = (
        SolixDeviceType.PPS.value
    )  # Anker PowerHouse 521 Portable Power Station
    A1722: str = SolixDeviceType.PPS.value  # SOLIX C300 Portable Power Station
    A1723: str = SolixDeviceType.PPS.value  # SOLIX C200 Portable Power Station
    A1725: str = SolixDeviceType.PPS.value  # SOLIX C200 Portable Power Station
    A1726: str = SolixDeviceType.PPS.value  # SOLIX C300 DC Portable Power Station
    A1727: str = SolixDeviceType.PPS.value  # SOLIX C200 DC Portable Power Station
    A1728: str = SolixDeviceType.PPS.value  # SOLIX C300X Portable Power Station
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
    A5101: str = SolixDeviceType.HES.value  # SOLIX X1 P6K US
    A5102: str = SolixDeviceType.HES.value  # SOLIX X1 Energy module 1P H(3.68~6)K
    A5103: str = SolixDeviceType.HES.value  # SOLIX X1 Energy module 3P H(5~12)K
    A5150: str = SolixDeviceType.HES.value  # SOLIX X1 Microinverter
    A5220: str = SolixDeviceType.HES.value  # SOLIX X1 Battery module
    A5341: str = SolixDeviceType.HES.value  # SOLIX X1 Backup Controller
    A5450: str = SolixDeviceType.HES.value  # SOLIX X1 Zigbee Dongle
    # Power Cooler
    A17A0: str = SolixDeviceType.POWERCOOLER.value  # SOLIX Power Cooler 30
    A17A1: str = SolixDeviceType.POWERCOOLER.value  # SOLIX Power Cooler 40
    A17A2: str = SolixDeviceType.POWERCOOLER.value  # SOLIX Power Cooler 50
    A17A4: str = SolixDeviceType.POWERCOOLER.value  # SOLIX Everfrost 2 40L
    A17A5: str = SolixDeviceType.POWERCOOLER.value  # SOLIX Everfrost 2 58L


@dataclass(frozen=True)
class SolarbankDeviceMetrics:
    """Dataclass for Anker Solarbank metrics which should be tracked in device details cache depending on model type."""

    # SOLIX E1600 Solarbank, single MPPT without channel reporting
    A17C0: ClassVar[set[str]] = set()
    # SOLIX E1600 Solarbank 2 Pro, with 4 MPPT channel reporting and AC socket
    A17C1: ClassVar[set[str]] = {
        "sub_package_num",
        "solar_power_1",
        "solar_power_2",
        "solar_power_3",
        "solar_power_4",
        "ac_power",
        "to_home_load",
        "pei_heating_power",
        # Following Only used correctly by AC model!
        # "micro_inverter_power",
        # "micro_inverter_power_limit",
        # "micro_inverter_low_power_limit",
        # "other_input_power",
    }
    # SOLIX E1600 Solarbank 2 AC, witho 2 MPPT channel and AC socket
    A17C2: ClassVar[set[str]] = {
        "sub_package_num",
        "bat_charge_power",
        "solar_power_1",
        "solar_power_2",
        "ac_power",
        "to_home_load",
        "pei_heating_power",
        "micro_inverter_power",  # This is external inverter input, counts to Solar power
        "micro_inverter_power_limit",
        "micro_inverter_low_power_limit",
        "grid_to_battery_power",
        "other_input_power",
    }
    # SOLIX E1600 Solarbank 2 Plus, with 2 MPPT
    A17C3: ClassVar[set[str]] = {
        "sub_package_num",
        "solar_power_1",
        "solar_power_2",
        "to_home_load",
        "pei_heating_power",
        # Following Only used correctly by AC model!
        # "micro_inverter_power",
        # "micro_inverter_power_limit",
        # "micro_inverter_low_power_limit",
        # "other_input_power",
    }


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
    # Discharge Priority preset for Solarbank schedule timeslot settings
    DISCHARGE_PRIORITY_DEF: int = SolarbankDischargePriorityMode.off.value
    # AC tariff settings for Use Time plan
    TARIFF_DEF: int = SolixTariffTypes.OFF_PEAK.value
    TARIFF_PRICE_DEF: str = "0.00"
    TARIFF_WE_SAME: bool = True
    CURRENCY_DEF: str = "€"
    # Seconds delay for subsequent Api requests in methods to update the Api cache dictionaries
    REQUEST_DELAY_MIN: float = 0.0
    REQUEST_DELAY_MAX: float = 10.0
    REQUEST_DELAY_DEF: float = 0.3
    # Request limit per endpoint per minute
    ENDPOINT_LIMIT_DEF: int = 10


class SolixDeviceStatus(StrEnum):
    """Enumeration for Anker Solix Device status."""

    # The device status code seems to be used for cloud connection status.
    offline = "0"
    online = "1"
    unknown = "unknown"


class SolarbankStatus(StrEnum):
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
    cold_wakeup = "116"  # At cold temperatures, 116 was observed instead of 4. Not sure why this state is different at low temps?
    fully_charged = "5"  # Seen for SB2 when SOC is 100%
    full_bypass = "6"  # seen at cold temperature, when battery must not be charged and the Solarbank bypasses all directly to inverter, also solar power < 25 W. More often with SB2
    standby = "7"
    unknown = "unknown"
    # TODO(AC): Is there a new mode for AC charging? Can it be distinguished from existing values?


class SmartmeterStatus(StrEnum):
    """Enumeration for Anker Solix Smartmeter status."""

    # TODO(#106) Update Smartmeter grid status description once known
    ok = "0"  # normal grid state when smart meter is measuring
    unknown = "unknown"


class SolixGridStatus(StrEnum):
    """Enumeration for Anker Solix grid status."""

    # TODO Update grid status description once known
    ok = "0"  # normal grid state when hes pcu grid status is ok
    unknown = "unknown"


class SolixRoleStatus(StrEnum):
    """Enumeration for Anker Solix role status of devices."""

    # The device role status codes as used for HES devices
    # TODO: The proper description of those codes has to be confirmed
    primary = "1"  # Master role in Api
    subordinate = "2"  # Slave role in Api, to be confirmed!!!
    unknown = "unknown"


class SolixNetworkStatus(StrEnum):
    """Enumeration for Anker Solix HES network status."""

    # TODO: The proper description of those codes has to be confirmed
    wifi = "1"  # to be confirmed
    lan = "2"  # this was seen on LAN connected systems
    mobile = "3"  # HES systems support also 5G connections, code to be confirmed
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
    discharge_priority: int | None = None  # mapped to discharge priority setting


@dataclass
class Solarbank2Timeslot:
    """Dataclass to define customizable attributes of an Anker Solix Solarbank 2 time slot as used for the schedule definition, update or deletion."""

    start_time: datetime | None
    end_time: datetime | None
    appliance_load: int | None = None  # mapped to appliance_load setting
    weekdays: set[int | str] | None = (
        None  # set of weekday numbers or abbreviations where this slot applies, defaulting to all if None. sun = 0, sat = 6
    )
