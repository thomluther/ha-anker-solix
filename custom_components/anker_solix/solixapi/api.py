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
    SolixDeviceStatus,
    SolixDeviceType,
)
from .poller import (
    poll_device_details,
    poll_device_energy,
    poll_site_details,
    poll_sites,
)
from .session import AnkerSolixClientSession

_LOGGER: logging.Logger = logging.getLogger(__name__)


class AnkerSolixApi(AnkerSolixBaseApi):
    """Define the API class to handle API data for Anker balcony power sites and devices using power_service endpoints."""

    # import outsourced methods
    from .energy import (  # pylint: disable=import-outside-toplevel
        energy_analysis,
        energy_daily,
        home_load_chart,
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
                        # keys with string values
                        "wireless_type",
                        "bt_ble_mac",
                        "charging_power",
                        "output_power",
                        "power_unit",
                        "bws_surplus",
                        "current_power",
                        "tag",
                        "err_code",
                        "ota_version",
                    ] or (
                        key
                        in [
                            # keys with string values that should only updated if value returned
                            "wifi_name",
                            "energy_today",
                            "energy_last_period",
                        ]
                        and value
                    ):
                        device.update({key: str(value)})
                    elif key in ["wifi_signal"]:
                        # Make sure that key is added, but update only if new value provided to avoid deletion of value from rssi calculation
                        if value or device.get("wifi_signal") is None:
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
                            in [
                                SolarbankUsageMode.smartmeter.value,
                                SolarbankUsageMode.smartplugs.value,
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
                            mode_type = (
                                value.get("mode_type") or SolixDefaults.USAGE_MODE
                            )
                            # define default presets, will be updated if active slot found
                            device.update(
                                {
                                    "preset_usage_mode": mode_type,
                                    "preset_system_output_power": 0
                                    if mode_type == SolarbankUsageMode.smartplugs.value
                                    else value.get("default_home_load")
                                    or SolixDefaults.PRESET_NOSCHEDULE,
                                }
                            )
                        else:
                            # Solarbank 1 schedule
                            # define default presets, will be updated if active slot found
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
                        if (
                            not devData.get("retain_load")
                            and (
                                mysite := self.sites.get(device.get("site_id") or "")
                                or {}
                            )
                            and sys_power
                        ):
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

    async def update_sites(
        self, siteId: str | None = None, fromFile: bool = False
    ) -> dict:  # noqa: C901
        """Create/Update api sites cache structure."""
        return await poll_sites(self, siteId=siteId, fromFile=fromFile)

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
        return await poll_device_details(self, fromFile=fromFile, exclude=exclude)

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
                Path(self._testdir) / f"{API_FILEPREFIXES['homepage']}.json"
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
                Path(self._testdir) / f"{API_FILEPREFIXES['user_devices']}.json"
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
                Path(self._testdir) / f"{API_FILEPREFIXES['charging_devices']}.json"
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
                Path(self._testdir)
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
                Path(self._testdir)
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
                Path(self._testdir)
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
        """
        data = {"site_id": siteId}
        if fromFile:
            resp = await self.apisession.loadFromFile(
                Path(self._testdir)
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
            await self.apisession.request(
                "post", API_ENDPOINTS["update_site_price"], json=data
            )
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
            resp = await self.apisession.loadFromFile(
                Path(self._testdir)
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
                Path(self._testdir)
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
                Path(self._testdir)
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
                Path(self._testdir)
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
                    self._testdir
                    / f"{API_FILEPREFIXES['get_upgrade_record']}_{recordType}_{deviceSn if deviceSn else siteId if siteId else recordType}.json"
                )
            )
        else:
            resp = await self.apisession.request(
                "post", API_ENDPOINTS["get_upgrade_record"], json=data
            )
        return resp.get("data") or {}
