"""Class for interacting with the Anker Power / Solix API.

Required Python modules:
pip install cryptography
pip install aiohttp
pip install aiofiles
"""

from __future__ import annotations

import contextlib
from datetime import datetime
import logging
from pathlib import Path

from aiohttp import ClientSession

from .apibase import AnkerSolixBaseApi
from .apitypes import (
    API_ENDPOINTS,
    API_FILEPREFIXES,
    SmartmeterStatus,
    SolarbankDeviceMetrics,
    SolarbankRatePlan,
    SolarbankStatus,
    SolarbankUsageMode,
    SolixDefaults,
    SolixDeviceCapacity,
    SolixDeviceCategory,
    SolixDeviceNames,
    SolixDeviceStatus,
    SolixDeviceType,
    SolixGridStatus,
    SolixNetworkStatus,
    SolixPriceTypes,
    SolixRoleStatus,
    SolixTariffTypes,
)
from .hesapi import AnkerSolixHesApi
from .poller import (
    poll_device_details,
    poll_device_energy,
    poll_site_details,
    poll_sites,
)
from .powerpanel import AnkerSolixPowerpanelApi
from .session import AnkerSolixClientSession

_LOGGER: logging.Logger = logging.getLogger(__name__)


class AnkerSolixApi(AnkerSolixBaseApi):
    """Define the API class to handle API data for Anker balcony power sites and devices using power_service endpoints."""

    # import outsourced methods
    from .energy import (  # pylint: disable=import-outside-toplevel
        device_pv_energy_daily,
        energy_analysis,
        energy_daily,
        get_device_pv_statistics,
        home_load_chart,
    )
    from .schedule import (  # pylint: disable=import-outside-toplevel
        get_device_load,
        get_device_parm,
        set_device_load,
        set_device_parm,
        set_home_load,
        set_sb2_ac_charge,
        set_sb2_home_load,
        set_sb2_use_time,
    )

    def __init__(
        self,
        email: str | None = None,
        password: str | None = None,
        countryId: str | None = None,
        websession: ClientSession | None = None,
        logger: logging.Logger | None = None,
        apisession: AnkerSolixClientSession | None = None,
    ) -> None:
        """Initialize."""
        super().__init__(
            email=email,
            password=password,
            countryId=countryId,
            websession=websession,
            logger=logger,
            apisession=apisession,
        )
        # link previous api methods to apisession for refactoring backward compatibility
        self.request_count = self.apisession.request_count
        self.async_authenticate = self.apisession.async_authenticate
        self.powerpanelApi: AnkerSolixPowerpanelApi | None = None
        self.hesApi: AnkerSolixHesApi | None = None

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
        sn = devData.pop("device_sn", None)
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
                        # preset default device name if only alias provided, fallback to alias if product name not listed
                        if (pn := device.get("device_pn") or None) and (
                            not device.get("name") or devData.get("device_name")
                        ):
                            device.update(
                                {
                                    "name": devData.get("device_name")
                                    or (
                                        (self.account.get("products") or {}).get(pn)
                                        or {}
                                    ).get("name")
                                    or getattr(SolixDeviceNames, pn, "")
                                    or str(value)
                                }
                            )
                    elif key in ["device_sw_version"] and value:
                        device.update({"sw_version": str(value)})
                    elif key in ["preset_inverter_limit"] and str(value):
                        device.update({"preset_inverter_limit": str(value).lower().replace("w","")})
                    elif (
                        key
                        in [
                            # keys with boolean values that should only be updated if value returned
                            "wifi_online",
                            "data_valid",
                            "charge",
                            "auto_upgrade",
                            "is_ota_update",
                            "cascaded",
                        ]
                        and value is not None
                    ):
                        device.update({key: bool(value)})
                    elif key in [
                        # keys with string values
                        "wireless_type",
                        "charging_power",
                        "output_power",
                        "power_unit",
                        "bws_surplus",
                        "current_power",
                        "tag",
                        "err_code",
                        "ota_version",
                        "bat_charge_power",
                    ] or (
                        key
                        in [
                            # keys with string values that should only updated if value returned
                            "wifi_name",
                            "bt_ble_mac",
                            "energy_today",
                            "energy_last_period",
                        ]
                        and value
                    ):
                        device.update({key: str(value)})
                    elif (
                        key in ["bt_ble_id"] and value and not devData.get("bt_ble_mac")
                    ):
                        # Make sure that BT ID is added if mac not in data
                        device.update({"bt_ble_mac": str(value).replace(":", "")})
                    elif key in ["wifi_signal"]:
                        # Make sure that key is added, but update only if new value provided to avoid deletion of value from rssi calculation
                        if value or device.get(key) is None:
                            device.update({key: str(value)})
                    elif key in ["rssi"]:
                        # This is actually not a relative rssi value (0-255), but a negative value and seems to be the absolute dBm of the signal strength
                        device.update({key: str(value)})
                        # calculate the wifi_signal percentage if that is not provided for the device while rssi is available
                        with contextlib.suppress(ValueError):
                            if float(value) and str(devData.get("wifi_signal")) == "":
                                # the percentage will be calculated in the range between -50 dBm (very good) and -85 dBm (no connection) as following.
                                dbmmax = -50
                                dbmmin = -85
                                device.update(
                                    {
                                        "wifi_signal": str(
                                            round(
                                                max(
                                                    0,
                                                    min(
                                                        100,
                                                        (float(value) - dbmmin)
                                                        * 100
                                                        / (dbmmax - dbmmin),
                                                    ),
                                                )
                                            )
                                        )
                                    }
                                )
                    elif key in ["battery_power"] and value:
                        # This is a percentage value for the battery state of charge, not power
                        device.update({"battery_soc": str(value)})
                    elif key in ["photovoltaic_power"]:
                        device.update({"input_power": str(value)})
                    # Add solarbank metrics depending on device type or generation
                    elif (
                        key
                        in [
                            "solar_power_1",
                            "solar_power_2",
                            "solar_power_3",
                            "solar_power_4",
                            "ac_power",
                            "to_home_load",
                            "other_input_power",
                            "micro_inverter_power",
                            "micro_inverter_power_limit",
                            "micro_inverter_low_power_limit",
                            "grid_to_battery_power",
                            "pei_heating_power",
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
                            device.update({key: int(value)})
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
                        # decode the device status into a description
                        device.update(
                            {
                                key: str(value),
                                "status_desc": next(
                                    iter(
                                        [
                                            item.name
                                            for item in SolixDeviceStatus
                                            if item.value == str(value)
                                        ]
                                    ),
                                    SolixDeviceStatus.unknown.name,
                                ),
                            }
                        )
                    elif key in ["charging_status"]:
                        device.update({key: str(value)})
                        # decode the charging status into a description
                        description = next(
                            iter(
                                [
                                    item.name
                                    for item in SolarbankStatus
                                    if item.value == str(value)
                                ]
                            ),
                            SolarbankStatus.unknown.name,
                        )
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
                        if generation >= 2 and (
                            (
                                device.get("preset_usage_mode")
                                or SolixDefaults.USAGE_MODE
                            )
                            in [
                                SolarbankUsageMode.smartmeter.value,
                                SolarbankUsageMode.smartplugs.value,
                                SolarbankUsageMode.use_time.value,
                            ]
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
                            and generation >= 2
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
                            and generation >= 2
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
                        device.update({key: int(value)})
                    elif key in ["power_cutoff_data", "ota_children"] and value:
                        # list items with value
                        device.update({key: list(value)})
                    elif key in ["fittings"]:
                        # update nested dictionary
                        if key in device:
                            device[key].update(dict(value))
                        else:
                            device[key] = dict(value)
                    elif key in ["solar_info"] and isinstance(value, dict):
                        # remove unnecessary keys from solar_info
                        keylist = value.keys()
                        for extra in [
                            x
                            for x in ("brand_id", "model_img", "version", "ota_status")
                            if x in keylist
                        ]:
                            value.pop(extra, None)
                        device.update({key: value})
                    elif key in ["solarbank_count"] and value:
                        device.update({key: value})
                    # schedule is currently a site wide setting. However, we save this with device details to retain info across site updates
                    # When individual device schedules are supported in future, this info is needed per device anyway
                    elif key in ["schedule"] and isinstance(value, dict):
                        device.update({key: dict(value)})
                        # set default presets for no active schedule slot
                        generation = int(device.get("generation", 0))
                        ac_type = bool(device.get("grid_to_battery_power") or False)
                        cnt = device.get("solarbank_count", 0)
                        mysite = self.sites.get(device.get("site_id") or "") or {}
                        if generation >= 2:
                            # Solarbank 2 schedule
                            mode_type = (
                                value.get("mode_type") or SolixDefaults.USAGE_MODE
                            )
                            # define default presets, will be updated if active slot found for mode
                            device.update(
                                {
                                    "preset_usage_mode": mode_type,
                                    "preset_system_output_power": value.get(
                                        "default_home_load"
                                    )
                                    or SolixDefaults.PRESET_NOSCHEDULE
                                    if mode_type in [SolarbankUsageMode.manual.value]
                                    else 0
                                    if mode_type
                                    in [SolarbankUsageMode.smartplugs.value]
                                    else None,
                                }
                            )
                            if ac_type:
                                # update default with site currency if found
                                if not (curr_def := (mysite.get("site_details") or {}).get("site_price_unit") or ""):
                                    curr_def = SolixDefaults.CURRENCY_DEF
                                device.update(
                                    {
                                        "preset_manual_backup_start": 0,
                                        "preset_manual_backup_end": 0,
                                        "preset_backup_option": False,
                                        "preset_tariff": SolixTariffTypes.NONE.value,
                                        "preset_tariff_price": SolixDefaults.TARIFF_PRICE_DEF,
                                        "preset_tariff_currency": curr_def,
                                    }
                                )
                        else:
                            # Solarbank 1 schedule
                            # define default presets, will be updated if active slot found
                            device.update(
                                {
                                    "preset_system_output_power": SolixDefaults.PRESET_NOSCHEDULE,
                                    "preset_allow_export": SolixDefaults.ALLOW_EXPORT,
                                    "preset_discharge_priority": SolixDefaults.DISCHARGE_PRIORITY_DEF,
                                    "preset_charge_priority": SolixDefaults.CHARGE_PRIORITY_DEF,
                                }
                            )
                            if cnt > 1:
                                device.update(
                                    {
                                        "preset_power_mode": SolixDefaults.POWER_MODE,
                                        "preset_device_output_power": int(
                                            SolixDefaults.PRESET_NOSCHEDULE / cnt
                                        ),
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
                            month = datetime.now().month
                            # get rate_plan_name depending on use usage mode_type
                            rate_plan_name = getattr(
                                SolarbankRatePlan,
                                next(
                                    iter(
                                        [
                                            item.name
                                            for item in SolarbankUsageMode
                                            if item.value == mode_type
                                        ]
                                    ),
                                    SolarbankUsageMode.manual.name,
                                ),
                                SolarbankRatePlan.manual,
                            )
                            day_ranges = next(
                                iter(
                                    [
                                        day.get("ranges") or []
                                        for day in (value.get(rate_plan_name) or [{}])
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
                            if ac_type and (
                                backup := value.get(SolarbankRatePlan.backup) or {}
                            ):
                                # check whether now in active backup interval to update usage mode info because active backup mode is not reflected in schedule object
                                start = (backup.get("ranges") or [{}])[0].get(
                                    "start_time"
                                ) or 0
                                end = (backup.get("ranges") or [{}])[0].get(
                                    "end_time"
                                ) or 0
                                switch = backup.get("switch") or False
                                # update valid backup list item data
                                device.update(
                                    {
                                        "preset_usage_mode": SolarbankUsageMode.backup
                                        if switch
                                        and start < datetime.now().timestamp() < end
                                        else mode_type,
                                        "preset_manual_backup_start": start,
                                        "preset_manual_backup_end": end,
                                        "preset_backup_option": switch,
                                    }
                                )
                            if ac_type and (
                                use_time := value.get(SolarbankRatePlan.use_time) or {}
                            ):
                                for season in [
                                    sea
                                    for sea in use_time
                                    if ((sea.get("sea") or {}).get("start_month") or 1)
                                    <= month
                                    <= ((sea.get("sea") or {}).get("end_month") or 12)
                                ]:
                                    if weekday in range(1, 6) or season.get("is_same"):
                                        dayplan = season.get("weekday") or []
                                        prices = season.get("weekday_price") or []
                                    else:
                                        dayplan = season.get("weekend") or []
                                        prices = season.get("weekend_price") or []
                                    tariff = next(
                                        iter(
                                            [
                                                slot
                                                for slot in dayplan
                                                if (slot.get("start_time") or 0)
                                                <= now.hour
                                                < (slot.get("end_time") or 24)
                                            ]
                                        ),
                                        {},
                                    ).get("type")
                                    price = next(
                                        iter(
                                            [
                                                slot
                                                for slot in prices
                                                if slot.get("type") == tariff
                                            ]
                                        ),
                                        {},
                                    ).get("price")
                                    device.update(
                                        {
                                            "preset_tariff": tariff
                                            or SolixTariffTypes.NONE.value,
                                            "preset_tariff_price": price
                                            or SolixDefaults.TARIFF_PRICE_DEF,
                                            "preset_tariff_currency": season.get("unit")
                                            or curr_def,
                                        }
                                    )

                            # adjust schedule preset for eventual reuse as active presets
                            # Active Preset must only be considered if usage mode is manual
                            sys_power = (
                                str(device.get("preset_system_output_power") or "")
                                if (mode_type or 0) == SolarbankUsageMode.manual.value
                                else None
                            )
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
                                        if bool(
                                            value.get("is_show_priority_discharge")
                                        ):
                                            discharge_prio = slot.get(
                                                "priority_discharge_switch"
                                            )
                                        else:
                                            discharge_prio = None
                                        # For enforced SB1 schedule by SB2, the export switch setting is None and all other will be set to None either
                                        device.update(
                                            {
                                                "preset_system_output_power": None
                                                if export is None
                                                else preset_power,
                                                "preset_allow_export": None
                                                if export is None
                                                else export,
                                                "preset_discharge_priority": None
                                                if export is None
                                                else discharge_prio,
                                                "preset_charge_priority": None
                                                if export is None
                                                else prio,
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
                                            # For enforced SB1 schedule by SB2, the export switch setting is None and all other will be set to None either
                                            device.update(
                                                {
                                                    "preset_power_mode": None
                                                    if export is None
                                                    else power_mode,
                                                    "preset_device_output_power": None
                                                    if export is None
                                                    else dev_power,
                                                }
                                            )
                                        break
                            # adjust schedule presets for eventual reuse as active presets
                            # Charge priority and SOC must only be considered if MI80 inverter is configured for SB1
                            prio = (
                                (device.get("preset_charge_priority") or 0)
                                if (
                                    (device.get("solar_info") or {}).get("solar_model")
                                    or ""
                                )
                                == "A5143"
                                else 0
                            )
                            if device.get("preset_allow_export") and int(prio) <= int(
                                device.get("battery_soc") or "0"
                            ):
                                sys_power = str(
                                    device.get("preset_system_output_power") or ""
                                )
                                # active device power depends on SB count
                                dev_power = (
                                    device.get("preset_device_output_power") or None
                                )
                                dev_power = str(
                                    dev_power
                                    if dev_power is not None and cnt > 1
                                    else sys_power
                                )
                            else:
                                sys_power = "0"
                                dev_power = "0"
                        # update appliance load in site cache upon device details or schedule updates not triggered by sites update
                        if not devData.get("retain_load") and mysite and sys_power:
                            mysite.update({"retain_load": sys_power})
                            # update also device fields for output power if not provided along with schedule update
                            if not devData.get("current_home_load") and sys_power:
                                device.update({"set_system_output_power": sys_power})
                                if not devData.get("parallel_home_load") and dev_power:
                                    device.update({"set_output_power": dev_power})

                    # inverter specific keys
                    elif key in ["generate_power"]:
                        device.update({key: str(value)})

                    # Power Panel specific keys
                    elif key in ["average_power"] and isinstance(value, dict):
                        device.update({key: value})

                    # smartmeter specific keys
                    elif key in ["grid_status"]:
                        # decode the grid status into a description
                        device.update(
                            {
                                key: str(value),
                                "grid_status_desc": next(
                                    iter(
                                        [
                                            item.name
                                            for item in SmartmeterStatus
                                            if item.value == str(value)
                                        ]
                                    ),
                                    SmartmeterStatus.unknown.name,
                                ),
                            }
                        )
                    elif key in [
                        "photovoltaic_to_grid_power",
                        "grid_to_home_power",
                    ]:
                        device.update({key: str(value)})

                    # hes specific keys
                    elif key in ["hes_data"] and isinstance(value, dict):
                        # decode the status into a description
                        if "online_status" in value:
                            code = str(value.get("online_status"))
                            # use same field name as for balcony power devices
                            value["status_desc"] = next(
                                iter(
                                    [
                                        item.name
                                        for item in SolixDeviceStatus
                                        if item.value == code
                                    ]
                                ),
                                SolixDeviceStatus.unknown.name,
                            )
                        if "master_slave_status" in value:
                            code = str(value.get("master_slave_status"))
                            value["role_status_desc"] = next(
                                iter(
                                    [
                                        item.name
                                        for item in SolixRoleStatus
                                        if item.value == code
                                    ]
                                ),
                                SolixRoleStatus.unknown.name,
                            )
                        if "grid_status" in value:
                            code = str(value.get("grid_status"))
                            value["grid_status_desc"] = next(
                                iter(
                                    [
                                        item.name
                                        for item in SolixGridStatus
                                        if item.value == code
                                    ]
                                ),
                                SolixGridStatus.unknown.name,
                            )
                        if "network_status" in value:
                            code = str(value.get("network_status"))
                            value["network_status_desc"] = next(
                                iter(
                                    [
                                        item.name
                                        for item in SolixNetworkStatus
                                        if item.value == code
                                    ]
                                ),
                                SolixNetworkStatus.unknown.name,
                            )
                        device.update({key: value})

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
                                        .replace(" 3", "")
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
                                # TODO(#SB3): Expansions for SB2 + 3 can have mixed capacity, how to identify expansion capacity?
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
                        "Api %s error %s occurred when updating device details for key %s with value %s: %s",
                        self.apisession.nickname,
                        type(err),
                        key,
                        value,
                        err,
                    )

            self.devices.update({str(sn): device})
        return sn

    def clearCaches(self) -> None:
        """Clear the api cache dictionaries except the account cache."""
        super().clearCaches()
        if self.powerpanelApi:
            self.powerpanelApi.clearCaches()
        if self.hesApi:
            self.hesApi.clearCaches()

    async def update_sites(
        self,
        siteId: str | None = None,
        fromFile: bool = False,
        exclude: set | None = None,
    ) -> dict:
        """Create/Update api sites cache structure."""
        resp = await poll_sites(self, siteId=siteId, fromFile=fromFile, exclude=exclude)
        # Clean up other api classes sites cache if used
        if self.powerpanelApi:
            self.powerpanelApi.recycleSites(activeSites=set(self.sites.keys()))
        if self.hesApi:
            self.hesApi.recycleSites(activeSites=set(self.sites.keys()))
        return resp

    async def update_site_details(
        self, fromFile: bool = False, exclude: set | None = None
    ) -> dict:
        """Add/Update site details in api sites cache structure."""
        return await poll_site_details(self, fromFile=fromFile, exclude=exclude)

    async def update_device_energy(
        self, fromFile: bool = False, exclude: set | None = None
    ) -> dict:
        """Add/Update energy details in api sites cache structure."""
        return await poll_device_energy(self, fromFile=fromFile, exclude=exclude)

    async def update_device_details(
        self, fromFile: bool = False, exclude: set | None = None
    ) -> dict:
        """Create/Update device details in api devices cache structure."""
        resp = await poll_device_details(self, fromFile=fromFile, exclude=exclude)
        # Clean up other api class devices cache if used
        if self.powerpanelApi:
            self.powerpanelApi.recycleDevices(activeDevices=set(self.devices.keys()))
        if self.hesApi:
            self.hesApi.recycleDevices(activeDevices=set(self.devices.keys()))
        return resp

    async def get_homepage(self, fromFile: bool = False) -> dict:
        """Get the latest homepage info.

        NOTE: This returns only data if the site is owned by the account. No data returned for site member accounts, therefore not really useful.
        Example data:
        {"site_list":[{"site_id":"efaca6b5-f4a0-e82e-3b2e-6b9cf90ded8c","site_name":"BKW","site_img":"","device_type_list":[3],"ms_type":0,"power_site_type":0,"is_allow_delete":false}],
        "solar_list":[],"pps_list":[],
        "solarbank_list":[{"device_pn":"","device_sn":"9JVB42LJK8J0P5RY","device_name":"Solarbank E1600",
            "device_img":"https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/e9478c2d-e665-4d84-95d7-dd4844f82055/20230719-144818.png",
            "battery_power":"75","bind_site_status":"1","charging_power":"","power_unit":"","charging_status":"","status":"","wireless_type":"","main_version":"","photovoltaic_power":"","output_power":"","create_time":0}],
        "powerpanel_list":[]}
        """
        if fromFile:
            resp = await self.apisession.loadFromFile(
                Path(self.testDir()) / f"{API_FILEPREFIXES['homepage']}.json"
            )
        else:
            resp = await self.apisession.request("post", API_ENDPOINTS["homepage"])
        return resp.get("data") or {}

    async def get_user_devices(self, fromFile: bool = False) -> dict:
        """Get device details of all devices owned by user. The response fields are pretty much empty, not really useful.

        Example data: (Information is mostly empty when device is bound to site)
        {'solar_list': [], 'pps_list': [], 'solarbank_list': [{'device_pn': 'A17C0', 'device_sn': '9JVB42LJK8J0P5RY', 'device_name': 'Solarbank E1600',
        'device_img': 'https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/e9478c2d-e665-4d84-95d7-dd4844f82055/20230719-144818.png',
        'battery_power': '', 'bind_site_status': '1', 'charging_power': '', 'power_unit': '', 'charging_status': '', 'status': '', 'wireless_type': '1', 'main_version': '',
        'photovoltaic_power': '', 'output_power': '', 'create_time': 0}]}
        """
        if fromFile:
            resp = await self.apisession.loadFromFile(
                Path(self.testDir()) / f"{API_FILEPREFIXES['user_devices']}.json"
            )
        else:
            resp = await self.apisession.request("post", API_ENDPOINTS["user_devices"])
        return resp.get("data") or {}

    async def get_charging_devices(self, fromFile: bool = False) -> dict:
        """Get the charging devices. The response fields are pretty much empty, not really useful for anything, not even for PPS devices.

        Example data:
        {'device_list': None, 'guide_txt': ''}
        """
        if fromFile:
            resp = await self.apisession.loadFromFile(
                Path(self.testDir()) / f"{API_FILEPREFIXES['charging_devices']}.json"
            )
        else:
            resp = await self.apisession.request(
                "post", API_ENDPOINTS["charging_devices"]
            )
        return resp.get("data") or {}

    async def get_solar_info(self, solarbankSn: str, fromFile: bool = False) -> dict:
        """Get the solar info that is configured for a solarbank.

        Example data:
        {"brand_id": "3a9930f5-74ef-4e41-a797-04e6b33d3f0f","solar_brand": "ANKER","solar_model": "A5140","solar_sn": "","solar_model_name": "MI60 Microinverter"}
        """
        data = {"solarbank_sn": solarbankSn}
        if fromFile:
            resp = await self.apisession.loadFromFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['solar_info']}_{solarbankSn}.json"
            )
        else:
            resp = await self.apisession.request(
                "post", API_ENDPOINTS["solar_info"], json=data
            )
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
            resp = await self.apisession.loadFromFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['compatible_process']}_{solarbankSn}.json"
            )
        else:
            resp = await self.apisession.request(
                "post", API_ENDPOINTS["compatible_process"], json=data
            )
        data = resp.get("data") or {}
        if info := data.get("solar_info", {}):
            self._update_dev({"device_sn": solarbankSn, "solar_info": info})
        return data

    async def get_power_cutoff(
        self, deviceSn: str, siteId: str = "", fromFile: bool = False
    ) -> dict:
        """Get power cut off settings. This works for any device in a Solarbank system, but only SB cutoffs are returned.

        Example data:
        {'power_cutoff_data': [
        {'id': 1, 'is_selected': 1, 'output_cutoff_data': 10, 'lowpower_input_data': 5, 'input_cutoff_data': 10},
        {'id': 2, 'is_selected': 0, 'output_cutoff_data': 5, 'lowpower_input_data': 4, 'input_cutoff_data': 5}]}
        """
        data = {"site_id": siteId, "device_sn": deviceSn}
        if fromFile:
            resp = await self.apisession.loadFromFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['get_cutoff']}_{deviceSn}.json"
            )
        else:
            resp = await self.apisession.request(
                "post", API_ENDPOINTS["get_cutoff"], json=data
            )
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
        code = (
            await self.apisession.request(
                "post", API_ENDPOINTS["set_cutoff"], json=data
            )
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
        Enhanced data from 2025 to support dynamic prices for systems:
        {"site_id": "8b0bdb3e-c2c6-95dc-5a3d-dfa4356ab0d8","price": 0.29,"site_co2": 0,"site_price_unit": "\u20ac","price_type": "fixed","current_mode": 3}
        """
        data = {"site_id": siteId}
        if fromFile:
            # For file data, verify first if there is a modified file to be used for testing
            if not (
                resp := await self.apisession.loadFromFile(
                    Path(self.testDir())
                    / f"{API_FILEPREFIXES['get_site_price']}_modified_{siteId}.json"
                )
            ):
                resp = await self.apisession.loadFromFile(
                    Path(self.testDir())
                    / f"{API_FILEPREFIXES['get_site_price']}_{siteId}.json"
                )
        else:
            resp = await self.apisession.request(
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
        price_type: str | None = None,  # "fixed" | "use_time"
        toFile: bool = False,
    ) -> bool | dict:
        """Set the power price, the unit, CO2 and price type for a site.

        Example input:
        {"site_id": 'efaca6b5-f4a0-e82e-3b2e-6b9cf90ded8c', "price": 0.325, "site_price_unit": "\u20ac", "site_co2": 0}
        Additional fields have been added to support dynamic prices
        {"site_id": 'efaca6b5-f4a0-e82e-3b2e-6b9cf90ded8c', "price": 0.325, "site_price_unit": "\u20ac", "site_co2": 0, "price_type": "fixed"}
        """
        # First get the old settings from api dict or Api call to update only requested parameter
        if not (details := (self.sites.get(siteId) or {}).get("site_details") or {}):
            details = await self.get_site_price(siteId=siteId, fromFile=toFile)
        if not details or not isinstance(details, dict):
            return False
        # Validate parameters
        price_type = (
            str(price_type).lower()
            if str(price_type).lower() in {item.value for item in SolixPriceTypes}
            else None
        )
        # Prepare payload from details
        data: dict = {}
        data["price"] = (
            float(price) if isinstance(price, float | int) else details.get("price")
        )
        data["site_price_unit"] = unit if unit else details.get("site_price_unit")
        data["site_co2"] = (
            float(co2) if isinstance(co2, float | int) else details.get("site_co2")
        )
        if "price_type" in details or price_type:
            data["price_type"] = price_type if price_type else details.get("price_type")

        # Make the Api call and check for return code
        data["site_id"] = siteId
        if toFile:
            # Write updated response to file for testing purposes
            if not await self.apisession.saveToFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['get_site_price']}_modified_{siteId}.json",
                data={
                    "code": 0,
                    "msg": "success!",
                    "data": data | {"current_mode": details.get("current_mode")},
                },
            ):
                return False
        else:
            code = (
                await self.apisession.request(
                    "post", API_ENDPOINTS["update_site_price"], json=data
                )
            ).get("code")
            if not isinstance(code, int) or int(code) != 0:
                return False
        # update the data in api dict and return active data
        return await self.get_site_price(siteId=siteId, fromFile=toFile)

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
            resp = await self.apisession.loadFromFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['get_device_fittings']}_{deviceSn}.json"
            )
        else:
            resp = await self.apisession.request(
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
            resp = await self.apisession.loadFromFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['get_ota_info']}_{solarbankSn or inverterSn}.json"
            )
        else:
            resp = await self.apisession.request(
                "post", API_ENDPOINTS["get_ota_info"], json=data
            )
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
            resp = await self.apisession.loadFromFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['get_ota_update']}_{deviceSn}.json"
            )
        else:
            resp = await self.apisession.request(
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
            resp = await self.apisession.loadFromFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['check_upgrade_record']}_{recordType}.json"
            )
        else:
            resp = await self.apisession.request(
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
            resp = await self.apisession.loadFromFile(
                Path(
                    self.testDir()
                    / f"{API_FILEPREFIXES['get_upgrade_record']}_{recordType}_{deviceSn if deviceSn else siteId if siteId else recordType}.json"
                )
            )
        else:
            resp = await self.apisession.request(
                "post", API_ENDPOINTS["get_upgrade_record"], json=data
            )
        return resp.get("data") or {}

    async def get_device_pv_status(
        self, devices: str | list[str], fromFile: bool = False
    ) -> dict:
        """Get the current pv status for an inverter device.

        Example data:
        {"pvStatuses": [{"sn": "JJY4QAVAFKT9","power": 169,"status": 1}]}
        """
        sns = (
            devices
            if isinstance(devices, str)
            else ",".join(devices)
            if isinstance(devices, list)
            else ""
        )
        data = {"sns": sns}
        if fromFile:
            # combine status of each device file into single response for multiple devices
            resp = {}
            for sn in sns.split(","):
                sn_resp = await self.apisession.loadFromFile(
                    Path(self.testDir())
                    / f"{API_FILEPREFIXES['get_device_pv_status']}_{sn.strip()}.json"
                )
                if not resp:
                    resp = sn_resp
                else:
                    new = (sn_resp.get("data") or {}).get("pvStatuses") or []
                    resp.update(
                        {
                            "data": {
                                "pvStatuses": (
                                    (resp.get("data") or {}).get("pvStatuses") or []
                                ) + new
                            }
                        }
                    )
        else:
            resp = await self.apisession.request(
                "post", API_ENDPOINTS["get_device_pv_status"], json=data
            )
        # update device details only if valid response for a given sn
        if (data := resp.get("data") or {}) and sns:
            # update devices dict with new power data
            for dev in data.get("pvStatuses") or []:
                # convert to string to merge with other response format
                self._update_dev(
                    {
                        "device_sn": dev.get("sn") or "",
                        "generate_power": "" if dev.get("power") is None else str(dev.get("power")),
                        "status": "" if dev.get("status") is None else str(dev.get("status")),
                    }
                )
        return data

    async def get_device_pv_total_statistics(
        self, deviceSn: str, fromFile: bool = False
    ) -> dict:
        """Get the total pv statistic data for an inverter device.

        Example data:
        {"energy": 66.15, "energyUnit": "kWh", "reductionCo2": 66, "reductionCo2Unit": "kg",
        "saveMoney": 0, "saveMoneyUnit": "\u20ac", "powerConfig": "800W", "powerPopUpFlag": 0}
        """
        data = {"sn": deviceSn}
        if fromFile:
            # For file data, verify first if there is a modified file to be used for testing
            if not (
                resp := await self.apisession.loadFromFile(
                    Path(self.testDir())
                    / f"{API_FILEPREFIXES['get_device_pv_total_statistics']}_modified_{deviceSn}.json"
                )
            ):
                resp = await self.apisession.loadFromFile(
                    Path(self.testDir())
                    / f"{API_FILEPREFIXES['get_device_pv_total_statistics']}_{deviceSn}.json"
                )
        else:
            resp = await self.apisession.request(
                "post", API_ENDPOINTS["get_device_pv_total_statistics"], json=data
            )
        data = resp.get("data") or {}
        # Save data in virtual site of api cache
        siteId = f"{SolixDeviceType.VIRTUAL.value}-{deviceSn}"
        if data and (mysite := self.sites.get(siteId)):
            # create statistics dictionary as used in scene_info for other sites to allow direct replacement
            stats = []
            # Total Energy
            stats.append(
                {
                    "type": "1",
                    "total": ""
                    if data.get("energy") is None
                    else str(data.get("energy")),
                    "unit": str(data.get("energyUnit") or "").lower(),
                }
            )
            # Total carbon
            stats.append(
                {
                    "type": "2",
                    "total": ""
                    if data.get("reductionCo2") is None
                    else str(data.get("reductionCo2")),
                    "unit": str(data.get("reductionCo2Unit") or "").lower(),
                }
            )
            # Total savings
            stats.append(
                {
                    "type": "3",
                    "total": ""
                    if data.get("saveMoney") is None
                    else str(data.get("saveMoney")),
                    "unit": str(data.get("saveMoneyUnit") or ""),
                }
            )
            # Add stats and other system infos to sites cache
            myinfo: dict = mysite.get("solar_info") or {}
            myinfo.update({"micro_inverter_power_limit": data.get("powerConfig")})
            mysite.update({"solar_info": myinfo, "statistics": stats})
            self.sites[siteId] = mysite
            # Update device cache with device details
            self._update_dev(
                {
                    "device_sn": deviceSn,
                    "preset_inverter_limit": data.get("powerConfig"),
                }
            )
        return data

    async def get_device_pv_price(self, deviceSn: str, fromFile: bool = False) -> dict:
        """Get the PV price set for the stand alone inverter.

        Example data:
        {"currencyUnit": "€","tieredElecPrices": [
            {"from": "00:00","to": "23:59","price": 0.4}]}
        """
        data = {"sn": deviceSn}
        if fromFile:
            # For file data, verify first if there is a modified file to be used for testing
            if not (
                resp := await self.apisession.loadFromFile(
                    Path(self.testDir())
                    / f"{API_FILEPREFIXES['get_device_pv_price']}_modified_{deviceSn}.json"
                )
            ):
                resp = await self.apisession.loadFromFile(
                    Path(self.testDir())
                    / f"{API_FILEPREFIXES['get_device_pv_price']}_{deviceSn}.json"
                )
        else:
            resp = await self.apisession.request(
                "post", API_ENDPOINTS["get_device_pv_price"], json=data
            )
        data = resp.get("data") or {}
        if tiers := data.get("tieredElecPrices") or []:
            # update virtual site details in sites dict with price info (only first tier is applied)
            siteId = f"{SolixDeviceType.VIRTUAL.value}-{deviceSn}"
            self._update_site(
                siteId,
                {
                    "price": (tiers[0] or {}).get("price"),
                    "site_price_unit": data.get("currencyUnit") or "",
                },
            )
        return data

    async def set_device_pv_price(
        self,
        deviceSn: str,
        price: float | None = None,
        unit: str | None = None,
        toFile: bool = False,
    ) -> bool | dict:
        """Set the PV device price and the unit.

        Example input:
        {"sn": "E071000XXXXX","currencyUnit": "€","tieredElecPrices": [
            {"from": "00:00","to": "23:59","price": 0.40}]}
        """
        # First get the old settings from api dict or Api call to update only requested parameter
        siteId = f"{SolixDeviceType.VIRTUAL.value}-{deviceSn}"
        if not (details := (self.sites.get(siteId) or {}).get("site_details") or {}):
            data = await self.get_device_pv_price(deviceSn=deviceSn, fromFile=toFile)
            if tiers := data.get("tieredElecPrices") or []:
                details = {
                    "price": (tiers[0] or {}).get("price"),
                    "site_price_unit": data.get("currencyUnit") or "",
                }
            else:
                details = {}
        if not details or not isinstance(details, dict):
            return False
        # Prepare payload from details
        data: dict = {}
        data["currencyUnit"] = unit if unit else details.get("site_price_unit")
        # limit tiers to single full day tier since others are ignored by the cloud
        data["tieredElecPrices"] = [
            {
                "from": "00:00",
                "to": "23:59",
                "price": float(price)
                if isinstance(price, float | int)
                else details.get("price"),
            }
        ]
        # Make the Api call and check for return code
        if toFile:
            # Write updated response to file for testing purposes
            if not await self.apisession.saveToFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['get_device_pv_price']}_modified_{deviceSn}.json",
                data={
                    "code": 0,
                    "msg": "success!",
                    "data": data,
                },
            ):
                return False
        else:
            data["sn"] = deviceSn
            code = (
                await self.apisession.request(
                    "post", API_ENDPOINTS["set_device_pv_price"], json=data
                )
            ).get("code")
            if not isinstance(code, int) or int(code) != 0:
                return False
        # update the data in api dict and return active data
        return await self.get_device_pv_price(deviceSn=deviceSn, fromFile=toFile)

    async def set_device_pv_power(
        self,
        deviceSn: str,
        limit: int,
        toFile: bool = False,
    ) -> bool | dict:
        """Set the PV device power limit in Watt.

        It is assumed, this is the persistant inverter limit which has limited write cycles in the inverter HW
        Example input:
        {"sn": "E071000XXXXX","power": 800}
        """
        # validate parameter
        if not (isinstance(limit, float | int) and limit >= 0):
            return False
        if toFile:
            # Get last data of file to be modified
            if not (data := await self.get_device_pv_total_statistics(deviceSn=deviceSn, fromFile=toFile)):
                return False
            data["powerConfig"] = f"{int(limit)}W"
            # Write updated response to file for testing purposes
            if not await self.apisession.saveToFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['get_device_pv_total_statistics']}_modified_{deviceSn}.json",
                data={
                    "code": 0,
                    "msg": "success!",
                    "data": data,
                },
            ):
                return False
        else:
            # Prepare payload from details
            data = {"sn": deviceSn, "power": int(limit)}
            # Make the Api call and check for return code
            code = (
                await self.apisession.request(
                    "post", API_ENDPOINTS["set_device_pv_power"], json=data
                )
            ).get("code")
            if not isinstance(code, int) or int(code) != 0:
                return False
        # update the data in api dict and return active data
        return await self.get_device_pv_total_statistics(deviceSn=deviceSn, fromFile=toFile)
