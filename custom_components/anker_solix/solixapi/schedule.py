"""Anker Power/Solix Cloud API class outsourced schedule related methods."""

import contextlib
import copy
from dataclasses import fields
from datetime import UTC, datetime, time, timedelta
import json
from pathlib import Path

from .apitypes import (
    API_ENDPOINTS,
    API_FILEPREFIXES,
    Solarbank2Timeslot,
    SolarbankDeviceMetrics,
    SolarbankPowerMode,
    SolarbankRatePlan,
    SolarbankTimeslot,
    SolarbankUsageMode,
    SolixDayTypes,
    SolixDefaults,
    SolixParmType,
    SolixPriceProvider,
    SolixPriceTypes,
    SolixTariffTypes,
)


async def get_device_load(
    self,
    siteId: str,
    deviceSn: str,
    fromFile: bool = False,
    testSchedule: dict | None = None,
) -> dict:
    r"""Get device load settings. This provides only SB1 schedule structure, not useful for SB2.

    Example data:
    {"site_id": "efaca6b5-f4a0-e82e-3b2e-6b9cf90ded8c",
    "home_load_data": "{\"ranges\":[
        {\"id\":0,\"start_time\":\"00:00\",\"end_time\":\"08:30\",\"turn_on\":true,\"appliance_loads\":[{\"id\":0,\"name\":\"Benutzerdefiniert\",\"power\":300,\"number\":1}],\"charge_priority\":80},
        {\"id\":0,\"start_time\":\"08:30\",\"end_time\":\"17:00\",\"turn_on\":false,\"appliance_loads\":[{\"id\":0,\"name\":\"Benutzerdefiniert\",\"power\":100,\"number\":1}],\"charge_priority\":80},
        {\"id\":0,\"start_time\":\"17:00\",\"end_time\":\"24:00\",\"turn_on\":true,\"appliance_loads\":[{\"id\":0,\"name\":\"Benutzerdefiniert\",\"power\":300,\"number\":1}],\"charge_priority\":0}],
        \"min_load\":100,\"max_load\":800,\"step\":0,\"is_charge_priority\":0,\"default_charge_priority\":0,\"is_zero_output_tips\":1}",
    "current_home_load": "300W","parallel_home_load": "","parallel_display": false}
    Attention: This method and endpoint actually returns only solarbank 1 schedule structure, which is invalid for different Solarbank 2 structures.
    While it also returns the applied home load settings, it cannot be used for Solarbank 2 due to wrong schedule data.
    """
    if not isinstance(testSchedule, dict):
        testSchedule = None
    if testSchedule is None or fromFile:
        data = {"site_id": siteId, "device_sn": deviceSn}
        if fromFile:
            # For file data, verify first if there is a modified schedule to be used for testing
            if not (
                resp := await self.apisession.loadFromFile(
                    Path(self.testDir())
                    / f"{API_FILEPREFIXES['get_device_load']}_modified_{deviceSn}.json"
                )
            ):
                resp = await self.apisession.loadFromFile(
                    Path(self.testDir())
                    / f"{API_FILEPREFIXES['get_device_load']}_{deviceSn}.json"
                )
        else:
            resp = await self.apisession.request(
                "post", API_ENDPOINTS["get_device_load"], json=data
            )
        # The home_load_data is provided as string instead of object...Convert into object for proper handling
        # It must be converted back to a string when passing this as input to set home load
        string_data = (resp.get("data") or {}).get("home_load_data") or {}
        if isinstance(string_data, str):
            resp["data"].update({"home_load_data": json.loads(string_data)})
        data = resp.get("data") or {}
        # update schedule also for all device serials found in schedule
        schedule = data.get("home_load_data") or {}
    else:
        # For testing purpose only, use test schedule to update dependent fields in device cache
        schedule = testSchedule
        data = {}
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
    self, siteId: str, deviceSn: str, loadData: dict, toFile: bool = False
) -> bool | dict:
    """Set device home load. This supports only SB1 schedule structure, but does not apply them. The set_device_parm method must be used instead.

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
    Attention: This method and endpoint actually accepts the input data, but does not change anything on the solarbank 1.
    The set_device_parm endpoint has to be used instead.
    """
    data = {
        "site_id": siteId,
        "device_sn": deviceSn,
        "home_load_data": json.dumps(loadData),
    }
    if toFile:
        # Write updated response to file for testing purposes
        if not await self.apisession.saveToFile(
            Path(self.testDir())
            / f"{API_FILEPREFIXES['get_device_load']}_modified_{deviceSn}.json",
            data={
                "code": 0,
                "msg": "success!",
                "data": {
                    "site_id": siteId,
                    "home_load_data": data.get("home_load_data"),
                    "current_home_load": "",
                    "parallel_home_load": "",
                },
            },
        ):
            return False
    else:
        # Make the Api call and check for return code
        code = (
            await self.apisession.request(
                "post", API_ENDPOINTS["set_device_load"], json=data
            )
        ).get("code")
        if not isinstance(code, int) or int(code) != 0:
            return False
    # update and return the data in api dict
    return await self.get_device_load(siteId=siteId, deviceSn=deviceSn, fromFile=toFile)


async def get_device_parm(
    self,
    siteId: str,
    paramType: str = SolixParmType.SOLARBANK_SCHEDULE.value,
    deviceSn: str | None = None,
    fromFile: bool = False,
    testSchedule: dict | None = None,
) -> dict:
    r"""Get device parameters (e.g. solarbank schedule). This can be queried for each siteId responded in the site_list query.

    Working paramType is 4 for SB1 schedules, 6 for SB2 schedules, 9 for enforced SB1 schedules when in coupled SB2 system (9 no longer supported since Jul 2025?), but can be modified if necessary.
    SB3 also supports 12 and 13 to list various options/settings for Smart mode and dynamic tariff plans.
    Example data for provided site_id with param_type 4 for SB1:
    {"param_data": "{\"ranges\":[
        {\"id\":0,\"start_time\":\"00:00\",\"end_time\":\"08:30\",\"turn_on\":true,\"appliance_loads\":[{\"id\":0,\"name\":\"Benutzerdefiniert\",\"power\":300,\"number\":1}],\"charge_priority\":80},
        {\"id\":0,\"start_time\":\"08:30\",\"end_time\":\"17:00\",\"turn_on\":false,\"appliance_loads\":[{\"id\":0,\"name\":\"Benutzerdefiniert\",\"power\":100,\"number\":1}],\"charge_priority\":80},
        {\"id\":0,\"start_time\":\"17:00\",\"end_time\":\"24:00\",\"turn_on\":true,\"appliance_loads\":[{\"id\":0,\"name\":\"Benutzerdefiniert\",\"power\":300,\"number\":1}],\"charge_priority\":0}],
        \"min_load\":100,\"max_load\":800,\"step\":0,\"is_charge_priority\":0,\"default_charge_priority\":0,\"is_zero_output_tips\":1}"}
    Example data for provided site_id with param_type 6 for SB2:
    {"param_data":"{\"mode_type\":3,\"custom_rate_plan\":[
        {\"index\":0,\"week\":[0,6],\"ranges\":[
            {\"start_time\":\"00:00\",\"end_time\":\"24:00\",\"power\":110}]},
        {\"index\":1,\"week\":[1,2,3,4,5],\"ranges\":[
            {\"start_time\":\"00:00\",\"end_time\":\"08:00\",\"power\":90},{\"start_time\":\"08:00\",\"end_time\":\"22:00\",\"power\":120},{\"start_time\":\"22:00\",\"end_time\":\"24:00\",\"power\":90}]}],
    \"blend_plan\":[
        {\"index\":0,\"week\":[0,1,2,3,4,5,6],\"ranges\":[
            {\"start_time\":\"00:00\",\"end_time\":\"24:00\",\"power\":20}]}],
    \"default_home_load\":200,\"max_load\":800,\"min_load\":0,\"step\":10}"}
    Example data for provided site_id with param_type 9 for SB1 in SB2 system:
    "param_data": "{\"ranges\":[
        {\"id\":0,\"start_time\":\"00:00\",\"end_time\":\"24:00\",\"turn_on\":null,\"appliance_loads\":[{\"id\":0,\"name\":\"Custom\",\"power\":0,\"number\":1}],
            \"charge_priority\":0,\"power_setting_mode\":null,\"device_power_loads\":null,\"priority_discharge_switch\":0}],
        \"min_load\":0,\"max_load\":800,\"step\":0,\"is_charge_priority\":0,\"default_charge_priority\":0,\"is_zero_output_tips\":0,\"display_advanced_mode\":0,\"advanced_mode_min_load\":0,
        \"is_show_install_mode\":1,\"display_priority_discharge_tips\":0,\"priority_discharge_upgrade_devices\":\"\",\"default_home_load\":200,\"is_show_priority_discharge\":0}"
    Example data for provided site_id with param_type 12 for SB3 system:
    {"param_data":"{\"price_type\":\"dynamic\",
        \"use_time\":[{\"sea\":{\"start_month\":1,\"end_month\":12},\"weekday\":[
            {\"start_time\":0,\"end_time\":18,\"type\":3},{\"start_time\":18,\"end_time\":21,\"type\":1},{\"start_time\":21,\"end_time\":24,\"type\":3}],
            \"weekend\":[{\"start_time\":0,\"end_time\":18,\"type\":3},{\"start_time\":18,\"end_time\":21,\"type\":1},{\"start_time\":21,\"end_time\":24,\"type\":3}],
            \"weekday_price\":[{\"price\":\"0.2\",\"type\":3},{\"price\":\"0.4\",\"type\":1}],
            \"weekend_price\":[{\"price\":\"0.2\",\"type\":3},{\"price\":\"0.4\",\"type\":1}],
            \"unit\":\"\u20ac\",\"is_same\":false}],
        \"dynamic_price\":{\"country\":\"DE\",\"company\":\"Nordpool\",\"area\":\"GER\",\"pct\":null,\"currency\":\"\u20ac\",\"adjust_coef\":null},
        \"fixed_price\":{\"price\":\"0.4\",\"unit\":\"\u20ac\",\"accuracy\":2},
        \"time_slot_data\":null}"}
    Example data for provided site_id with param_type 13 for SB3 system:
    {"param_data":"{\"step\":5,\"ai_ems\":null,\"max_load\":1200,\"min_load\":null,\"data_auth\":true,\"mode_type\":null,
        \"blend_plan\":null,\"custom_rate_plan\":null,\"default_home_load\":null}"}
    """
    if not isinstance(testSchedule, dict):
        testSchedule = None
    if testSchedule is None or fromFile:
        data = {"site_id": siteId, "param_type": paramType}
        if fromFile:
            # For file data, verify first if there is a modified schedule to be used for testing
            if not (
                resp := await self.apisession.loadFromFile(
                    Path(self.testDir())
                    / f"{API_FILEPREFIXES['get_device_parm']}_{paramType}_modified_{siteId}.json"
                )
            ):
                resp = await self.apisession.loadFromFile(
                    Path(self.testDir())
                    / f"{API_FILEPREFIXES['get_device_parm']}_{paramType}_{siteId}.json"
                )
            # ensure backward filename compatibility without parm type in name
            if not resp and paramType == SolixParmType.SOLARBANK_SCHEDULE.value:
                resp = await self.apisession.loadFromFile(
                    Path(self.testDir())
                    / f"{API_FILEPREFIXES['get_device_parm']}_{siteId}.json"
                )
        else:
            resp = await self.apisession.request(
                "post", API_ENDPOINTS["get_device_parm"], json=data
            )
        # The home_load_data is provided as string instead of object...Convert into object for proper handling
        # It must be converted back to a string when passing this as input to set home load
        string_data = (resp.get("data", {})).get("param_data", {})
        if string_data and isinstance(string_data, str):
            resp["data"].update({"param_data": json.loads(string_data)})

        # update api device dict with latest data if optional device SN was provided, e.g. when called by set_device_parm for device details update
        data = resp.get("data") or {}
        # update schedule also for other device serials found in Solarbank 1 schedules
        schedule = data.get("param_data") or {}
    else:
        # For testing purpose only, use test schedule to update dependent fields in device cache
        schedule = testSchedule
        data = {}
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
                # "current_home_load": data.get("current_home_load") or "",   # This field is not provided with get_device_parm
                # "parallel_home_load": data.get("parallel_home_load") or "",   # This field is not provided with get_device_parm
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
    toFile: bool = False,
) -> bool | dict:
    r"""Set device parameters (e.g. solarbank schedule).

    command: Must be 17 for SB1, SB2 and SB3 solarbank schedules. Maybe new models require other command value?
    paramType: was always string "4" for SB1, SB2 needs "6" and a different structure. SB3 may need 12 or 13 depending on settings
    Example paramData for type "4":
    {"param_data": '{"ranges":['
        '{"id":0,"start_time":"00:00","end_time":"08:30","turn_on":true,"appliance_loads":[{"id":0,"name":"Benutzerdefiniert","power":300,"number":1}],"charge_priority":80},'
        '{"id":0,"start_time":"08:30","end_time":"17:00","turn_on":false,"appliance_loads":[{"id":0,"name":"Benutzerdefiniert","power":100,"number":1}],"charge_priority":80},'
        '{"id":0,"start_time":"17:00","end_time":"24:00","turn_on":true,"appliance_loads":[{"id":0,"name":"Benutzerdefiniert","power":300,"number":1}],"charge_priority":0}],'
    '"min_load":100,"max_load":800,"step":0,"is_charge_priority":0,default_charge_priority":0}}'

    Example data for provided site_id with param_type "6" for SB2:
    {"param_data":"{\"mode_type\":3,\"custom_rate_plan\":[
        {\"index\":0,\"week\":[0,6],\"ranges\":[
            {\"start_time\":\"00:00\",\"end_time\":\"24:00\",\"power\":110}]},
        {\"index\":1,\"week\":[1,2,3,4,5],\"ranges\":[
            {\"start_time\":\"00:00\",\"end_time\":\"08:00\",\"power\":90},{\"start_time\":\"08:00\",\"end_time\":\"22:00\",\"power\":120},{\"start_time\":\"22:00\",\"end_time\":\"24:00\",\"power\":90}]}],
    \"blend_plan\":null,\"default_home_load\":200,\"max_load\":800,\"min_load\":0,\"step\":10}"}
    """
    data = {
        "site_id": siteId,
        "param_type": paramType,
        "cmd": command,
        "param_data": json.dumps(paramData),  # Must be string type
    }
    if toFile:
        # Write updated response to file for testing purposes
        if not await self.apisession.saveToFile(
            Path(self.testDir())
            / f"{API_FILEPREFIXES['get_device_parm']}_{paramType}_modified_{siteId}.json",
            data={
                "code": 0,
                "msg": "success!",
                "data": {"param_data": data.get("param_data")},
            },
        ):
            return False
    else:
        code = (
            await self.apisession.request(
                "post", API_ENDPOINTS["set_device_parm"], json=data
            )
        ).get("code")
        if not isinstance(code, int) or int(code) != 0:
            return False
    # update the data in api dict, distinguish which schedule to query for updates
    respdata: dict = {}
    if (self.devices.get(deviceSn) or {}).get("device_pn") in ["A17C0"]:
        # Active SB1 schedule data should be queried like on details refresh
        respdata = await self.get_device_load(
            siteId=siteId, deviceSn=deviceSn, fromFile=toFile
        )
        data = respdata
    else:
        # Other solarbank models
        respdata = await self.get_device_parm(
            siteId=siteId, paramType=paramType, deviceSn=deviceSn, fromFile=toFile
        )
        data = {}
    # update also cascaded solarbanks schedule
    sb_info = (self.sites.get(siteId) or {}).get("solarbank_info") or {}
    if sb_info.get("sb_cascaded"):
        # Update schedule only for other SB1 that are cascaded
        for casc_sn in [
            sb.get("device_sn")
            for sb in (sb_info.get("solarbank_list") or [])
            if sb.get("cascaded") and sb.get("device_sn") != deviceSn
        ]:
            # For two cascaded SB1, their enforced schedule may no longer list the other SB1 anymore when SB2 is in manual mode
            if not data:
                data = await self.get_device_load(
                    siteId=siteId, deviceSn=casc_sn, fromFile=toFile
                )
            if data:
                self._update_dev(
                    {
                        "device_sn": casc_sn,
                        "schedule": data.get("home_load_data") or {},
                        "current_home_load": data.get("current_home_load") or "",
                        "parallel_home_load": data.get("parallel_home_load") or "",
                    }
                )
    return respdata


async def set_home_load(  # noqa: C901
    self,
    siteId: str,
    deviceSn: str,
    all_day: bool = False,
    preset: int | None = None,
    dev_preset: int | None = None,
    export: bool | None = None,
    charge_prio: int | None = None,
    discharge_prio: int | None = None,
    set_slot: SolarbankTimeslot | None = None,
    insert_slot: SolarbankTimeslot | None = None,
    test_schedule: dict | None = None,  # used only for testing instead of real schedule
    test_count: int
    | None = None,  # used only for testing instead of real solarbank count
    toFile: bool = False,  # used for testing with files
) -> bool | dict:
    """Set the home load parameters for a given site id and solarbank 1 device for actual or all slots in the existing schedule.

    If no time slot is defined for current time, a new slot will be inserted for the gap. This will result in full day definition when no slot is defined.
    Optionally when set_slot is provided, the given slot will replace the existing schedule completely.
    When insert_slot is provided, the given slot will be incorporated into existing schedule. Adjacent overlapping slot times will be updated and overlay slots will be replaced.

    Example schedules for Solarbank 1 as provided via Api:
    {"ranges":[
        {"id":0,"start_time":"00:00","end_time":"08:30","turn_on":true,"appliance_loads":[{"id":0,"name":"Benutzerdefiniert","power":300,"number":1}],"charge_priority":80},
        {"id":0,"start_time":"08:30","end_time":"17:00","turn_on":false,"appliance_loads":[{"id":0,"name":"Benutzerdefiniert","power":100,"number":1}],"charge_priority":80},
        {"id":0,"start_time":"17:00","end_time":"24:00","turn_on":true,"appliance_loads":[{"id":0,"name":"Benutzerdefiniert","power":300,"number":1}],"charge_priority":0}],
    "min_load":100,"max_load":800,"step":0,"is_charge_priority":0,default_charge_priority":0}

    New ranges structure with individual device power loads:
    {"ranges":[
        {"id":0,"start_time":"00:00","end_time":"08:00","turn_on":true,"appliance_loads":[{"id":0,"name":"Custom","power":270,"number":1}],"charge_priority":10,
            "power_setting_mode":1,"device_power_loads":[{"device_sn":"W8Z0AY4TF8L03KMS","power":135},{"device_sn":"XGR9TZEI1N9OO8BN","power":135}]},
        {"id":0,"start_time":"08:00","end_time":"24:00","turn_on":true,"appliance_loads":[{"id":0,"name":"Custom","power":300,"number":1}],"charge_priority":10,
            "power_setting_mode":2,"device_power_loads":[{"device_sn":"W8Z0AY4TF8L03KMS","power":100},{"device_sn":"XGR9TZEI1N9OO8BN","power":200}]}],
    "min_load":100,"max_load":800,"step":0,"is_charge_priority":1,"default_charge_priority":80,"is_zero_output_tips":0,"display_advanced_mode":1,"advanced_mode_min_load":50}

    Minimal ranges structure when enforced by SB2 manual mode in combined systems:
    {"ranges":[
        {"id":0,"start_time":"00:00","end_time":"24:00","turn_on":null,"appliance_loads":[{"id":0,"name":"Custom","power":0,"number":1}],
          "charge_priority":0,"power_setting_mode":null,"device_power_loads":null,"priority_discharge_switch":0}],
    "min_load":0,"max_load":800,"step":0,"is_charge_priority":0,"default_charge_priority":0,"is_zero_output_tips":0,"display_advanced_mode":0,"advanced_mode_min_load":0,
    "is_show_install_mode":1,"display_priority_discharge_tips":0,"priority_discharge_upgrade_devices":"","default_home_load":200,"is_show_priority_discharge":0}
    """
    # fast quit if nothing to change
    charge_prio = (
        int(charge_prio)
        if str(charge_prio).isdigit() or isinstance(charge_prio, int | float)
        else None
    )
    discharge_prio = (
        int(discharge_prio)
        if str(discharge_prio).isdigit() or isinstance(discharge_prio, int | float)
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
        and discharge_prio is None
        and set_slot is None
        and insert_slot is None
    ):
        return False
    # set flag for required current parameter update
    pending_now_update = bool(set_slot is None and insert_slot is None)
    # obtain actual device schedule from internal dict or fetch via api
    if not isinstance(test_schedule, dict):
        test_schedule = None
    if test_schedule:
        schedule = test_schedule
    elif not (schedule := (self.devices.get(deviceSn) or {}).get("schedule") or {}):
        schedule = (
            await self.get_device_load(
                siteId=siteId, deviceSn=deviceSn, fromFile=toFile
            )
        ).get("home_load_data") or {}
    ranges = schedule.get("ranges") or []
    # get appliance load name from first existing slot to avoid mixture
    # NOTE: The solarbank may behave weird if a mixture is found or the name does not match with some internal settings
    # The name cannot be queried, but seems to be 'custom' by default. However, the mobile app translates it to whatever language is defined in the App
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
        # Allow lower min setting as defined by API minimum. This however may be ignored if outside of appliance defined slot boundaries.
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
    # If neither appliance nor device preset provided, leave power mode unchanged. Legacy mode will be used with default 50% share when default appliance load must be set
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
        set_slot.appliance_load = min(max(set_slot.appliance_load, min_load), max_load)

    new_ranges = []
    # Consider time zone shifts of HA server to modify correct device time slot
    tz_offset = (self.sites.get(siteId) or {}).get("energy_offset_tz") or 0
    now = datetime.now() + timedelta(seconds=tz_offset)
    # update individual values in current slot or insert SolarbankTimeslot and adjust adjacent slots
    if not set_slot:
        now_time = now.time().replace(microsecond=0)
        last_time = datetime.strptime("00:00", "%H:%M").time()
        # set now to new daytime if close to end of day to determine which slot to modify
        if now_time >= datetime.strptime("23:59:58", "%H:%M:%S").time():
            now_time = datetime.strptime("00:00", "%H:%M").time()
        next_start = None
        split_slot: dict = {}
        for idx, slot in enumerate(ranges, start=1):
            with contextlib.suppress(ValueError):
                start_time = datetime.strptime(
                    slot.get("start_time") or "00:00", "%H:%M"
                ).time()
                # "24:00" format not supported in strptime
                end_time = datetime.strptime(
                    (str(slot.get("end_time") or "00:00").replace("24:00", "23:59")),
                    "%H:%M",
                ).time()
                # check slot timings to update current, or insert new and modify adjacent slots
                insert: dict = {}

                # Check if parameter update required for current time but it falls into gap of no defined slot.
                # Create insert slot for the gap and add before or after current slot at the end of the current slot checks/modifications required for allday usage
                if (
                    not insert_slot
                    and pending_now_update
                    and (
                        last_time <= now_time < start_time
                        or (idx == len(ranges) and now_time >= end_time)
                    )
                ):
                    # Use daily end time if now after last slot
                    insert: dict = copy.deepcopy(slot)
                    insert.update(
                        {
                            "start_time": last_time.isoformat(timespec="minutes")
                            if now_time < start_time
                            else end_time.isoformat(timespec="minutes")
                        }
                    )
                    insert.update(
                        {
                            "end_time": (
                                start_time.isoformat(timespec="minutes")
                            ).replace("23:59", "24:00")
                            if now_time < start_time
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
                    # optional discharge priority update if supported by schedule
                    if "priority_discharge_switch" in insert:
                        insert.update(
                            {
                                "priority_discharge_switch": SolixDefaults.DISCHARGE_PRIORITY_DEF
                                if discharge_prio is None
                                else discharge_prio
                            }
                        )

                    # if gap is before current slot, insert now
                    if now_time < start_time:
                        new_ranges.append(insert)
                        last_time = start_time
                        insert = {}

                if pending_insert and (
                    insert_slot.start_time.time() <= start_time or idx == len(ranges)
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
                            insert_slot.appliance_load = insert_slot.device_load + sum(
                                [
                                    dev.get("power")
                                    for dev in (insert.get("device_power_loads") or [])
                                    if dev.get("device_sn") != deviceSn
                                ]
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
                                insert_slot.device_load + max_load_dev * (sb_count - 1),
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
                                            if insert_slot.appliance_load is not None
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
                                                insert_slot.appliance_load / sb_count
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
                                                insert_slot.appliance_load / sb_count
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
                    # optional priority_discharge_switch settings if supported by schedule
                    if "priority_discharge_switch" in insert and (
                        insert_slot.discharge_priority is not None or overwrite
                    ):
                        insert.update(
                            {
                                "priority_discharge_switch": SolixDefaults.DISCHARGE_PRIORITY_DEF
                                if insert_slot.discharge_priority is None
                                else int(insert_slot.discharge_priority)
                            }
                        )
                    if insert_slot.charge_priority_limit is not None or overwrite:
                        insert.update(
                            {
                                "charge_priority": min(
                                    max(
                                        int(
                                            SolixDefaults.CHARGE_PRIORITY_DEF
                                            if insert_slot.charge_priority_limit is None
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
                            if end_time < datetime.strptime("23:59", "%H:%M").time():
                                next_start = insert_slot.end_time.time()
                            last_time = insert_slot.end_time.time()
                            # skip current slot since overlapped by insert slot
                            continue
                        if split_slot:
                            # insert second part of a preceding slot that was split
                            new_ranges.append(split_slot)
                            split_slot = {}
                            # delay start time of current slot not needed if previous slot was split
                        elif insert_slot.end_time.time() > start_time:
                            # delay start time of current slot if insert slot end falls into current slot
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
                    # shorten end of preceding slot
                    slot.update(
                        {"end_time": datetime.strftime(insert_slot.start_time, "%H:%M")}
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
                                            for dev in slot.get("device_power_loads")
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
                        if insert_slot.discharge_priority is None:
                            insert_slot.discharge_priority = slot.get(
                                "priority_discharge_switch"
                            )
                        if insert_slot.charge_priority_limit is None:
                            insert_slot.charge_priority_limit = slot.get(
                                "charge_priority"
                            )

                elif next_start and next_start < end_time:
                    # delay start of slot following an insert if it falls into the slot
                    if next_start > start_time:
                        slot.update(
                            {
                                "start_time": (
                                    next_start.isoformat(timespec="minutes")
                                ).replace("23:59", "24:00")
                            }
                        )
                    next_start = None

                elif not insert_slot and (all_day or start_time <= now_time < end_time):
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
                                                (preset - dev_preset) / (sb_count - 1)
                                            ),
                                        }
                                    )
                    if export is not None:
                        slot.update({"turn_on": export})
                    # optional priority_discharge_switch settings if supported by schedule
                    if (
                        "priority_discharge_switch" in slot
                        and discharge_prio is not None
                    ):
                        slot.update({"priority_discharge_switch": discharge_prio})
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
                    if start_time <= now_time < end_time:
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
                    # insert second part of a preceding slot that was split
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
                discharge_priority=discharge_prio,
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
                    ((self.sites.get(siteId) or {}).get("solarbank_info") or {}).get(
                        "solarbank_list"
                    )
                    or [{}]
                )
                if sb.get("device_pn") == "A17C0"
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
        # optional priority_discharge_switch settings if supported by schedule
        if "is_show_priority_discharge" in schedule:
            slot.update(
                {
                    "priority_discharge_switch": SolixDefaults.DISCHARGE_PRIORITY_DEF
                    if set_slot.discharge_priority is None
                    else set_slot.discharge_priority
                }
            )

        # use previous appliance name if a slot was defined originally
        if appliance_name:
            (slot.get("appliance_loads") or [{}])[0].update({"name": appliance_name})
        new_ranges.append(slot)
    schedule.update({"ranges": new_ranges})
    self._logger.debug(
        "Api %s schedule to be applied: %s", self.apisession.nickname, schedule
    )
    # return resulting schedule for test purposes without Api call
    if test_count or test_schedule:
        # ensure schedule is updated also in cache for dependent devices
        await self.get_device_parm(
            siteId=siteId,
            testSchedule=schedule,
            deviceSn=deviceSn,
        )
        return schedule
    # Make the Api call with final schedule and return result, the set call will also update api dict
    # NOTE: set_device_load does not seem to be usable yet for changing the home load, or is only usable in dual bank setups for changing the appliance load share as well?
    return await self.set_device_parm(
        siteId=siteId,
        paramData=schedule,
        deviceSn=deviceSn,
        toFile=toFile,
    )


async def set_sb2_home_load(  # noqa: C901
    self,
    siteId: str,
    deviceSn: str,
    preset: int | None = None,
    usage_mode: int | None = None,
    plan_name: str | None = None,
    set_slot: Solarbank2Timeslot | None = None,
    insert_slot: Solarbank2Timeslot | None = None,
    test_schedule: dict
    | None = None,  # used for testing or to apply changes only to api cache
    toFile: bool = False,  # for testing in file usage mode
) -> bool | dict:
    """Set or change the home load parameters for a given site id and solarbank 2 device for any slot in the existing schedule.

    If no time slot is defined for current time, a new slot will be inserted for the gap. This will result in full day definition when no slot is defined.
    Optionally when set_slot is provided, the given slot will replace the existing schedule for the requested weekdays completely.
    When insert_slot is provided, the given slot will be incorporated into existing schedule for the requested weekdays.
    Adjacent overlapping slot times will be updated and overlay slots will be replaced.
    If no weekdays are provided, the actual day or all days will be used, depending whether rate plan definitions exist already
    Weekday rate plans can be separated and merged depending on provided weekdays in the Solarbank2Timeslot object.
    When set_slot provides a Solarbank2Timeslot object with missing start or end time, it will be used to delete the rate plans the provided weekdays or delete all
    if no weekdays are provided.
    If rate_plan is specified, the changes will be applied to the given plan, otherwise the active plan according to active or provided usage mode will be modified.
    custom_rate_plan: Used for the Manual usage mode
    blend_plan: Used for the Smart Plug usage mode
    custom_rate_plan: Used for smart plug mode to define additional base load
    manual_backup: Used for SB2 AC emergency charge, use method set_sb2_ac_charge for changes
    use_time: Used for SB2 AC Usage Time mode, use method set_sb2_use_time for changes

    Example data for provided site_id with param_type 6 for SB2:
    "schedule": {
        "mode_type": 3,
        "custom_rate_plan": [
            {"index": 0,"week": [0,6],"ranges": [
                {"start_time": "00:00","end_time": "24:00","power": 110}]},
            {"index": 1,"week": [1,2,3,4,5],"ranges": [
                {"start_time": "00:00","end_time": "08:00","power": 100},
                {"start_time": "08:00","end_time": "22:00","power": 120},
                {"start_time": "22:00","end_time": "24:00","power": 90}]}],
        "blend_plan": null,
        "manual_backup": null,
        "use_time": null,
        "default_home_load": 200,"max_load": 800,"min_load": 0,"step": 10}
    """
    # fast quit if nothing to change
    preset = (
        int(preset)
        if str(preset).isdigit() or isinstance(preset, int | float)
        else None
    )
    # Validate if selected mode is possible
    usage_mode_options = self.solarbank_usage_mode_options(deviceSn=deviceSn)
    usage_mode = (
        usage_mode
        if usage_mode in iter(SolarbankUsageMode)
        and SolarbankUsageMode(usage_mode).name in usage_mode_options
        else None
    )
    if (
        preset is None
        and usage_mode is None
        and set_slot is None
        and insert_slot is None
    ):
        self._logger.error(
            "Api %s no valid schedule options provided", self.apisession.nickname
        )
        return False

    # set flag for required current parameter update
    pending_now_update = bool(set_slot is None and insert_slot is None)
    # obtain actual device schedule from internal dict or fetch via api
    if not isinstance(test_schedule, dict):
        test_schedule = None
    if test_schedule:
        schedule = test_schedule
    elif not (schedule := (self.devices.get(deviceSn) or {}).get("schedule") or {}):
        schedule = (
            await self.get_device_parm(
                siteId=siteId,
                paramType=SolixParmType.SOLARBANK_2_SCHEDULE.value,
                deviceSn=deviceSn,
                fromFile=toFile,
            )
        ).get("param_data") or {}

    # get appliance limits
    if (min_load := str(schedule.get("min_load"))).isdigit():
        min_load = int(min_load)
    else:
        min_load = 0
    if (max_load := str(schedule.get("max_load"))).isdigit():
        max_load = int(max_load)
    else:
        max_load = SolixDefaults.PRESET_MAX
    # Adjust provided appliance limits
    # Relaxed max_load to device type max if schedule max_load no longer reflecting active device limit, see issue #309
    if ((d := self.devices.get(deviceSn) or {}).get("generation") or 0) >= 2:
        model = d.get("device_pn") or ""
        max_load = max(
            [
                int(x)
                for x in (
                    SolarbankDeviceMetrics.INVERTER_OUTPUT_OPTIONS.get(model) or []
                )
            ]
            + [max_load]
        )
    # appliance limits depend on device load setting and other device setting. Must be reduced for individual slots if necessary
    if preset is not None:
        preset = min(max(preset, min_load), max_load)
    if insert_slot and insert_slot.appliance_load is not None:
        insert_slot.appliance_load = min(
            max(insert_slot.appliance_load, min_load), max_load
        )
    if set_slot and set_slot.appliance_load is not None:
        set_slot.appliance_load = min(max(set_slot.appliance_load, min_load), max_load)

    # set flag for plan deletion when set slot provided but any time field missing
    delete_plan: bool = set_slot and (not set_slot.start_time or not set_slot.end_time)

    # update the usage mode in the overall schedule object or set it to the one used in the schedule
    if usage_mode is None:
        usage_mode = schedule.get("mode_type")

    # get validated rate plan name from optional plan_name parameter or use plan name for given/active user mode, default to custom rate plan name
    rate_plan_name = next(
        iter(
            [
                field.default
                for field in fields(SolarbankRatePlan)
                if field.default == plan_name
            ]
        ),
        # default name if plan_name not provided or invalid
        getattr(
            SolarbankRatePlan,
            next(
                iter(
                    [
                        item.name
                        for item in SolarbankUsageMode
                        if item.value == usage_mode
                    ]
                ),
                SolarbankUsageMode.manual.name,
            ),
            SolarbankRatePlan.manual,
        ),
    )
    rate_plan = schedule.get(rate_plan_name) or []
    new_rate_plan = []

    # identify week days to be used, default to todays weekday or all
    # Consider time zone shifts
    tz_offset = (self.sites.get(siteId) or {}).get("energy_offset_tz") or 0
    now = datetime.now() + timedelta(seconds=tz_offset)
    days: list[str] = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]
    weekdays = (
        {int(now.strftime("%w"))} if rate_plan and not delete_plan else set(range(7))
    )
    # set flag to match weekdays with current plan if no weekdays provided
    match_plan = True
    if insert_slot and isinstance(insert_slot, Solarbank2Timeslot):
        if insert_slot.weekdays:
            weekdays = insert_slot.weekdays
            match_plan = False
        # Check insert_slot has required time parameters
        if not (insert_slot.start_time and insert_slot.end_time):
            self._logger.error(
                "Api %s incomplete interval definitions for insert_slot, missing %s",
                self.apisession.nickname,
                "& ".join(
                    (["start_time"] if not insert_slot.start_time else [])
                    + (["end_time"] if not insert_slot.end_time else [])
                ),
            )
            return False
    elif set_slot and isinstance(set_slot, Solarbank2Timeslot) and set_slot.weekdays:
        weekdays = set_slot.weekdays
        match_plan = False
    # allow weekday strings as used by HA and convert to proper weekday number as required for api
    weekdays = {days.index(day) for day in weekdays if day in days} | (
        weekdays & set(range(7))
    )
    if not weekdays:
        self._logger.error(
            "Api %s  invalid weekdays provided for schedule change: %s",
            self.apisession.nickname,
            insert_slot.weekdays or set_slot.weekdays,
        )
        return False
    # First identify a matching rate plan for provided week days
    # When weekday combination exists, re-use the same. When provided weekdays have extra days to existing, merge extra weekdays to existing
    # When existing weekdays are partial subset of provided weekdays, clone first plan with most matching days as new plan for the defined weekdays to separate them from existing plan
    matched_days = set()
    index = None
    if rate_plan_name in {SolarbankRatePlan.manual, SolarbankRatePlan.smartplugs} and (
        preset is not None or set_slot or insert_slot
    ):
        if not delete_plan:
            for idx, rate in enumerate(rate_plan):
                if len((days := set(rate.get("week") or [])) & weekdays) > len(
                    matched_days & weekdays
                ):
                    matched_days = days.copy()
                    index = idx
                    # re-use matching plan days if no weekdays provided
                    if match_plan:
                        weekdays = days.copy()
                    # quit loop on total match
                    if (matched_days & weekdays) == weekdays:
                        # all days defined, reuse plan
                        break
            if index is None:
                # set next used index number if no matching days found
                index = (
                    int(dict(rate_plan[-1]).get("index") or -1) + 1 if rate_plan else 0
                )
                rate_plan.append({"index": index, "week": weekdays, "ranges": []})
            elif (matched_days & weekdays) != matched_days:
                # Clone existing ranges to new plan if only partial subset of provided days
                new_ranges = list(rate_plan[index].get("ranges") or [])
                index = int(dict(rate_plan[-1]).get("index") or len(rate_plan) - 1) + 1
                rate_plan.append(
                    {"index": index, "week": weekdays, "ranges": new_ranges}
                )
            else:
                # Merge new and existing weekdays since existing plan is for complete subset of new weekdays
                weekdays = weekdays | set(rate_plan[index].get("week") or [])
                index = rate_plan[index].get("index")
        # create new rate plan and curate existing weekdays
        removed = 0
        for idx, rate in enumerate(rate_plan):
            new_rate = copy.deepcopy(rate)
            if new_days := (
                sorted(weekdays)
                if rate.get("index") == index
                else sorted(set(rate.get("week") or []) - weekdays)
            ):
                # add merged weekdays
                new_rate.update({"index": idx - removed, "week": new_days})
                new_rate_plan.append(new_rate)
                # adjust rate plan list index to new number
                if rate.get("index") == index:
                    index = idx - removed
            else:
                # skip index in new rate plan and adjust remaining
                removed += 1
    elif delete_plan:
        new_rate_plan = None
    else:
        # Reuse existing plan
        new_rate_plan: dict = copy.deepcopy(rate_plan)

    # get the time ranges that may have to be modified
    ranges = [] if index is None else (new_rate_plan[index].get("ranges") or [])
    new_ranges = []
    pending_insert = False
    if len(ranges) > 0:
        if insert_slot:
            # set flag for pending insert slot
            pending_insert = True
    elif insert_slot:
        # use insert_slot for set_slot to define a single new slot when no slots exist
        set_slot = insert_slot

    # update individual values in current slot or insert SolarbankTimeslot and adjust adjacent slots
    if rate_plan_name in {SolarbankRatePlan.manual, SolarbankRatePlan.smartplugs} and (
        preset is not None or pending_insert
    ):
        now_time = now.time().replace(microsecond=0)
        last_time = datetime.strptime("00:00", "%H:%M").time()
        # set now to new daytime if close to end of day to determine which slot to modify
        if now_time >= datetime.strptime("23:59:58", "%H:%M:%S").time():
            now_time = datetime.strptime("00:00", "%H:%M").time()
        next_start = None
        split_slot: dict = {}
        for idx, slot in enumerate(ranges, start=1):
            with contextlib.suppress(ValueError):
                start_time = datetime.strptime(
                    slot.get("start_time") or "00:00", "%H:%M"
                ).time()
                # "24:00" format not supported in strptime
                end_time = datetime.strptime(
                    (str(slot.get("end_time") or "00:00").replace("24:00", "23:59")),
                    "%H:%M",
                ).time()
                # check slot timings to update current, or insert new and modify adjacent slots
                insert: dict = {}

                # Check if parameter update required for current time but it falls into gap of no defined slot.
                # Create insert slot for the gap and add before or after current slot at the end of the current slot checks/modifications (required for allday usage)
                if (
                    not insert_slot
                    and pending_now_update
                    and (
                        last_time <= now_time < start_time
                        or (idx == len(ranges) and now_time >= end_time)
                    )
                ):
                    # Use daily end time if now after last slot
                    insert: dict = copy.deepcopy(slot)
                    insert.update(
                        {
                            "start_time": last_time.isoformat(timespec="minutes")
                            if now_time < start_time
                            else end_time.isoformat(timespec="minutes")
                        }
                    )
                    insert.update(
                        {
                            "end_time": (
                                start_time.isoformat(timespec="minutes")
                            ).replace("23:59", "24:00")
                            if now_time < start_time
                            else "24:00"
                        }
                    )
                    # adjust appliance load depending on device load preset and ensure appliance load is consistent with device load min/max values
                    appliance_load = (
                        SolixDefaults.PRESET_DEF if preset is None else preset
                    )
                    insert.update(
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

                    # if gap is before current slot, insert now
                    if now_time < start_time:
                        new_ranges.append(insert)
                        last_time = start_time
                        insert: dict = {}

                if pending_insert and (
                    insert_slot.start_time.time() <= start_time or idx == len(ranges)
                ):
                    # copy slot, update and insert the new slot
                    overwrite = (
                        insert_slot.start_time.time() != start_time
                        and insert_slot.end_time.time() != end_time
                    )
                    # re-use old slot parms if insert slot has not defined optional parms
                    insert: dict = copy.deepcopy(slot)
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
                        insert_slot.appliance_load = insert.get("power")
                    if insert_slot.appliance_load is not None or overwrite:
                        insert.update(
                            {
                                "power": min(
                                    max(
                                        int(
                                            insert_slot.appliance_load
                                            if insert_slot.appliance_load is not None
                                            else SolixDefaults.PRESET_DEF
                                        ),
                                        min_load,
                                    ),
                                    max_load,
                                ),
                            }
                        )
                    # insert slot before current slot if not last
                    if insert_slot.start_time.time() <= start_time:
                        new_ranges.append(insert)
                        insert = {}
                        pending_insert = False
                        if insert_slot.end_time.time() >= end_time:
                            # set start of next slot if not end of day
                            if end_time < datetime.strptime("23:59", "%H:%M").time():
                                next_start = insert_slot.end_time.time()
                            last_time = insert_slot.end_time.time()
                            # skip current slot since overlapped by insert slot
                            continue
                        if split_slot:
                            # insert second part of a preceding slot that was split
                            new_ranges.append(split_slot)
                            split_slot: dict = {}
                            # delay start time of current slot not needed if previous slot was split
                        elif insert_slot.end_time.time() > start_time:
                            # delay start time of current slot if insert slot end falls into current slot
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
                            split_slot: dict = copy.deepcopy(slot)
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
                        split_slot: dict = copy.deepcopy(slot)
                        split_slot.update(
                            {
                                "start_time": datetime.strftime(
                                    insert_slot.end_time, "%H:%M"
                                ).replace("23:59", "24:00")
                            }
                        )
                    # shorten end of preceding slot
                    slot.update(
                        {"end_time": datetime.strftime(insert_slot.start_time, "%H:%M")}
                    )
                    # re-use old slot parms for insert if end time of insert slot is same as original slot
                    if insert_slot.end_time.time() == end_time:
                        # reuse old appliance load
                        if insert_slot.appliance_load is None:
                            insert_slot.appliance_load = slot.get("power")

                elif next_start and next_start < end_time:
                    # delay start of slot following an insert if it falls into the slot
                    if next_start > start_time:
                        slot.update(
                            {
                                "start_time": (
                                    next_start.isoformat(timespec="minutes")
                                ).replace("23:59", "24:00")
                            }
                        )
                    next_start = None

                elif not insert_slot and (start_time <= now_time < end_time):
                    # update required parameters in current slot
                    # adjust appliance load
                    if preset is not None:
                        slot.update(
                            {
                                "power": min(
                                    max(
                                        int(preset),
                                        min_load,
                                    ),
                                    max_load,
                                ),
                            }
                        )
                    # clear flag for pending parameter update for actual time
                    if start_time <= now_time < end_time:
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
                    # insert second part of a preceding slot that was split
                    new_ranges.append(split_slot)
                    split_slot: dict = {}

            # Track end time of last appended slot in list
            last_time = datetime.strptime(
                (
                    str(new_ranges[-1].get("end_time") or "00:00").replace(
                        "24:00", "23:59"
                    )
                ),
                "%H:%M",
            ).time()

    # If no rate plan or new ranges exists or new slot to be set, set defaults or given set_slot parameters
    if (
        (not new_rate_plan or not new_ranges)
        and (set_slot or preset is not None)
        and not delete_plan
        and rate_plan_name in {SolarbankRatePlan.manual, SolarbankRatePlan.smartplugs}
    ):
        if not set_slot:
            # fill set_slot with given parameters
            set_slot = Solarbank2Timeslot(
                start_time=datetime.strptime("00:00", "%H:%M"),
                end_time=datetime.strptime("23:59", "%H:%M"),
                appliance_load=preset,
            )
        slot = {
            "start_time": datetime.strftime(set_slot.start_time, "%H:%M"),
            "end_time": datetime.strftime(set_slot.end_time, "%H:%M").replace(
                "23:59", "24:00"
            ),
            "power": SolixDefaults.PRESET_DEF
            if set_slot.appliance_load is None
            else set_slot.appliance_load,
        }
        new_ranges.append(slot)

    if new_rate_plan:
        if index is not None:
            new_rate_plan[index].update({"ranges": new_ranges})
    elif (
        rate_plan_name in {SolarbankRatePlan.manual, SolarbankRatePlan.smartplugs}
        and not delete_plan
    ):
        new_rate_plan: list = [
            {
                "index": 0,
                "week": list(weekdays),
                "ranges": new_ranges,
            }
        ]
    if rate_plan_name:
        schedule.update({rate_plan_name: new_rate_plan})
    # Update existing usage mode, reset to an available automatic or manual mode if required rate plan deleted
    # TODO(SB3): Once time_slot rate plan is available in schedule, verify against existing plan instead of dynamic provider setup
    mode_type = (
        getattr(
            SolarbankUsageMode,
            ({usage_mode_options} & {SolarbankUsageMode.smartmeter.name})
            or ({usage_mode_options} & {SolarbankUsageMode.smartplug.name})
            or SolarbankUsageMode.manual.name,
        )
        if (
            usage_mode == SolarbankUsageMode.use_time.value
            and not schedule.get(SolarbankRatePlan.use_time)
        )
        or (
            usage_mode == SolarbankUsageMode.time_slot.value
            and not schedule.get("dynamic_price")
        )
        else usage_mode
    )
    schedule["mode_type"] = mode_type
    self._logger.debug(
        "Api %s schedule to be applied: %s", self.apisession.nickname, schedule
    )
    # update Api dict and return resulting schedule for test purposes without Api call
    if test_schedule:
        # ensure complete schedule is updated in cache for dependent fields
        await self.get_device_parm(
            siteId=siteId,
            paramType=SolixParmType.SOLARBANK_2_SCHEDULE.value,
            testSchedule=schedule,
            deviceSn=deviceSn,
        )
        return schedule
    # The applied schedule need to separate plans for AC model and common SB2 plans
    # The mode_type must always be contained
    # TODO(SB3): This may need updates once plan names for SB3 are known and modification was tested, e.g. time_slot plan
    new_schedule = {"mode_type": mode_type}
    if rate_plan_name in {SolarbankRatePlan.manual, SolarbankRatePlan.smartplugs}:
        new_schedule.update(
            {
                SolarbankRatePlan.manual: schedule.get(SolarbankRatePlan.manual) or [],
                SolarbankRatePlan.smartplugs: schedule.get(SolarbankRatePlan.smartplugs)
                or [],
            }
        )
    else:
        # AC unique plans to be separated for Api call
        new_schedule.update(
            {
                SolarbankRatePlan.backup: schedule.get(SolarbankRatePlan.backup) or {},
                SolarbankRatePlan.use_time: schedule.get(SolarbankRatePlan.use_time)
                or [],
            }
        )
    # Make the Api call with the schedule subset to be applied and return result, the set call will also re-read full schedule and update api dict
    resp = await self.set_device_parm(
        siteId=siteId,
        paramType=SolixParmType.SOLARBANK_2_SCHEDULE.value,
        paramData=schedule if toFile else new_schedule,
        deviceSn=deviceSn,
        toFile=toFile,
    )
    # Make also the price type change if required by usage mode change
    # The mobile App only activates use_time price automatically with use_time mode, but may not toggle back to fixed price automatically
    price_type = ((self.sites.get(siteId) or {}).get("site_details") or {}).get(
        "price_type"
    )
    new_price_type: str | None = None
    provider = (
        SolixPriceProvider(provider=p)
        if (p := schedule.get("dynamic_price") or {})
        else None
    )
    if mode_type in iter(SolarbankUsageMode) and price_type:
        if (
            mode_type in [SolarbankUsageMode.use_time.value]
            and price_type != SolixPriceTypes.USE_TIME.value
            and schedule.get(SolarbankRatePlan.use_time)
        ):
            new_price_type = SolixPriceTypes.USE_TIME.value
        elif (
            mode_type in [SolarbankUsageMode.time_slot.value]
            and price_type != SolixPriceTypes.DYNAMIC.value
            and provider
        ):
            new_price_type = SolixPriceTypes.DYNAMIC.value
    if new_price_type:
        self._logger.debug(
            "Toggling api %s price type to: %s",
            self.apisession.nickname,
            new_price_type,
        )
        await self.set_site_price(
            siteId=siteId, price_type=new_price_type, provider=provider, toFile=toFile
        )
    return resp


async def set_sb2_ac_charge(
    self,
    siteId: str,
    deviceSn: str,
    backup_start: datetime | None = None,
    backup_end: datetime | None = None,
    backup_duration: timedelta | None = None,
    backup_switch: bool | None = None,
    test_schedule: dict
    | None = None,  # used for testing or to apply changes only to api cache
    toFile: bool = False,  # used for testing with files
) -> bool | dict:
    """Set or change the AC charge parameters for a given site id and solarbank 2 AC device.

    The backup definition is part of the SB2 device schedule object. If no end_time or duration is specified, a default duration of 1 hour will be used
    manual_backup: Used for the manual backup period definition for max AC charge.
    Example data for provided site_id with param_type 6 for SB2:
    "schedule": {
        "mode_type": 3,
        "custom_rate_plan": null,
        "blend_plan": null,
        "use_time": null,
        "manual_backup": {
            "ranges": [
            {
                "start_time": 1734693780,
                "end_time": 1734700980
            }
            ],
            "switch": true
        "default_home_load": 200,"max_load": 800,"min_load": 0,"step": 10}
    """
    # validate parameters
    def_duration = timedelta(hours=3)
    backup_start = (
        backup_start.astimezone() if isinstance(backup_start, datetime) else None
    )
    backup_duration = (
        max(backup_duration, timedelta(minutes=5))
        if isinstance(backup_duration, timedelta)
        else None
    )
    backup_end = backup_end.astimezone() if isinstance(backup_end, datetime) else None
    backup_switch = backup_switch if isinstance(backup_switch, bool) else None
    # fast quit if nothing to change
    if backup_start is None and backup_end is None and backup_switch is None:
        self._logger.error(
            "Api %s no valid AC charge options provided", self.apisession.nickname
        )
        return False

    # obtain actual device schedule from internal dict or fetch via api
    if not isinstance(test_schedule, dict):
        test_schedule = None
    if test_schedule:
        schedule = test_schedule
    elif not (schedule := (self.devices.get(deviceSn) or {}).get("schedule") or {}):
        schedule = (
            await self.get_device_parm(
                siteId=siteId,
                paramType=SolixParmType.SOLARBANK_2_SCHEDULE.value,
                deviceSn=deviceSn,
                fromFile=toFile,
            )
        ).get("param_data") or {}

    rate_plan_name = SolarbankRatePlan.backup
    # Consider time zone shifts of device, timestamp conversion is absolute and timezone aware
    now = datetime.now().replace(second=0, microsecond=0).astimezone()
    # create new structure if none exists yet or get old times if not provided for validation
    if not (new_rate_plan := schedule.get(rate_plan_name) or {}):
        new_rate_plan["ranges"] = []
        new_rate_plan["switch"] = False
    else:
        if not backup_start:
            backup_start = datetime.fromtimestamp(
                (new_rate_plan.get("ranges") or [{}])[0].get("start_time") or 0, UTC
            ).astimezone()
        if not backup_end:
            backup_end = datetime.fromtimestamp(
                (new_rate_plan.get("ranges") or [{}])[0].get("end_time") or 0, UTC
            ).astimezone()

    if backup_switch is None:
        backup_switch = bool(new_rate_plan.get("switch"))
    else:
        # switch provided as parameter, first ensure start time is set correctly if backup range will be activated
        if backup_switch:
            backup_start = backup_start or now
            if not new_rate_plan.get("switch") and (backup_end or now) <= now:
                # switch will be changed to enabled, ensure start time is at least now if now passed a previous interval
                backup_start = now
        new_rate_plan["switch"] = backup_switch

    # make sure backup start and end time are valid and merged with optional parameters before applying them
    if backup_start or backup_end:
        # TODO(AC): Modify if more than one range supported for device
        backup_end = max(backup_start or backup_end, backup_end or backup_start)
        backup_start = min(backup_start or backup_end, backup_end or backup_start)
        if backup_start == backup_end or backup_duration:
            backup_end = backup_start + (backup_duration or def_duration)
        new_rate_plan["ranges"] = [
            {
                "start_time": int(backup_start.timestamp()),
                "end_time": int(backup_end.timestamp()),
            }
        ]

    schedule.update({rate_plan_name: new_rate_plan})
    self._logger.debug(
        "Api %s schedule to be applied: %s", self.apisession.nickname, schedule
    )
    # return resulting schedule for test purposes without Api call
    if test_schedule:
        # ensure complete schedule is updated in cache for dependent fields
        await self.get_device_parm(
            siteId=siteId,
            paramType=SolixParmType.SOLARBANK_2_SCHEDULE.value,
            testSchedule=schedule,
            deviceSn=deviceSn,
        )
        return schedule
    # The applied schedule need to separate plans for AC model and common SB2 plans
    # The mode_type must always be contained
    # TODO(SB3): This may need updates once plan names for SB3 are known and modification was tested, e.g. time_slot plan
    new_schedule = {"mode_type": schedule.get("mode_type")}
    if rate_plan_name in {SolarbankRatePlan.manual, SolarbankRatePlan.smartplugs}:
        new_schedule.update(
            {
                SolarbankRatePlan.manual: schedule.get(SolarbankRatePlan.manual) or [],
                SolarbankRatePlan.smartplugs: schedule.get(SolarbankRatePlan.smartplugs)
                or [],
            }
        )
    else:
        # AC unique plans to be separated for Api call
        new_schedule.update(
            {
                SolarbankRatePlan.backup: schedule.get(SolarbankRatePlan.backup) or {},
                SolarbankRatePlan.use_time: schedule.get(SolarbankRatePlan.use_time)
                or [],
            }
        )
    # Make the Api call with the schedule subset to be applied and return result, the set call will also re-read full schedule and update api dict
    return await self.set_device_parm(
        siteId=siteId,
        paramType=SolixParmType.SOLARBANK_2_SCHEDULE.value,
        paramData=schedule if toFile else new_schedule,
        deviceSn=deviceSn,
        toFile=toFile,
    )


async def set_sb2_use_time(  # noqa: C901
    self,
    siteId: str,
    deviceSn: str,
    start_month: int | str | None = None,  # 1-12
    end_month: int | str | None = None,  # 1-12
    start_hour: int | datetime | time | None = None,  # 0-23
    end_hour: int | datetime | time | None = None,  # 1-24
    day_type: str | None = None,  # Anker Solix use time day types
    tariff_type: int | str | None = None,  # Any SolixTariffTypes
    tariff_price: float | str | None = None,
    currency: str | None = None,
    delete: bool | None = False,
    merge_tariff_slots: bool = True,  # merge time slots with same tariff
    clear_unused_tariff: bool = True,  # clear price of unsused tariff in season/daytype
    test_schedule: dict
    | None = None,  # used for testing or to apply changes only to api cache
    toFile: bool = False,  # for testing with files
) -> bool | dict:
    r"""Set or change the AC use time parameters for a given site id and solarbank 2 AC device.

    !!! THIS IS NOT IMPLEMENTED YET !!!

    The is part of the device schedule object
    Example schedule for Solarbank 2 AC as provided via Api:
    "{"mode_type":3,
    "custom_rate_plan":[{"index":0,"week":[0,1,2,3,4,5,6],"ranges":[{"start_time":"00:00","end_time":"24:00","power":0}]}],
    "blend_plan":null,
    "use_time":[
        {"sea":{"start_month":1,"end_month":3},
            "weekday":[
                {"start_time":0,"end_time":6,"type":3},{"start_time":6,"end_time":11,"type":1},{"start_time":11,"end_time":14,"type":3},
                {"start_time":14,"end_time":17,"type":2},{"start_time":17,"end_time":22,"type":3},{"start_time":22,"end_time":24,"type":4}],
            "weekend":[{"start_time":0,"end_time":16,"type":3},{"start_time":16,"end_time":21,"type":1},{"start_time":21,"end_time":24,"type":3}],
            "weekday_price":[{"price":"0.25","type":3},{"price":"0.5","type":1},{"price":"0.35","type":2},{"price":"0.2","type":4}],
            "weekend_price":[{"price":"0.25","type":3},{"price":"0.5","type":1}],
            "unit":"\u20ac","is_same":false},
        {"sea":{"start_month":4,"end_month":9},
            "weekday":[{"start_time":0,"end_time":16,"type":3},{"start_time":16,"end_time":21,"type":1},{"start_time":21,"end_time":24,"type":3}],
            "weekend":[{"start_time":0,"end_time":6,"type":3},{"start_time":6,"end_time":13,"type":1},{"start_time":13,"end_time":16,"type":3},
                {"start_time":16,"end_time":20,"type":2},{"start_time":20,"end_time":24,"type":3}],
            "weekday_price":[{"price":"0.25","type":3},{"price":"0.35","type":1}],
            "weekend_price":[{"price":"0.25","type":3},{"price":"0.35","type":1},{"price":"0.31","type":2}],
            "unit":"\u20ac","is_same":false},
        {"sea":{"start_month":10,"end_month":12},
            "weekday":[{"start_time":0,"end_time":16,"type":3},{"start_time":16,"end_time":21,"type":1},{"start_time":21,"end_time":24,"type":3}],
            "weekend":[{"start_time":0,"end_time":16,"type":3},{"start_time":16,"end_time":21,"type":1},{"start_time":21,"end_time":24,"type":3}],
            "weekday_price":[{"price":"0.23","type":3},{"price":"0.38","type":1}],
            "weekend_price":[{"price":"0.23","type":3},{"price":"0.38","type":1}],
            "unit":"$","is_same":true}],
    "manual_backup":null,
    "default_home_load":200,"max_load":800,"min_load":0,"step":10}

    Applied Parameter logic:
    - Optional season start_month
        - Default to season start of current month's season if end month not provided, else use start month of season containing the end month
           - If no season exists, use 1
        - If start month matches existing season start, use it without change
        - If start month splits existing season, reduce end month of previous season slot
            - Copy matching season data to use as default for new season
    - Optional season end_month
        - Default to season end month of season containing the start month
            - If no season exists, use 12
        - If end month matches existing season end, use it without change
        - If end month splits existing season, copy season and increase start month for the remaining seasion
        - If end month exceeds existing season, increase start month of next season with start month < end and end month > end
    - Optional selection for days weekday, weekend, all
        - If None, use current day and modify active weekday and/or weekend. If same active, modify weekday and copy to weekend including tariffs
        - If weekday or weekend and same active, modify selected and disable the same setting
        - If all and same active, modify weekday and copy to weekend, otherwise modify all independently
        - How to activate the same switch? Delete the unwanted daytype, which will copy the other and enable the same switch
    - => If no day structure identified, define default 0-24 hour, use default tariff low peak and fixed site price (0 if not defined)
    - Optional start hour
        - Default to start of current hour interval if end hour not provided, else use start hour of end hour interval
            - If no interval exists, use 0
        - If start hour matches existing interval start, use it without change
        - If start hour splits existing interval, reduce end hour of previous interval
            - Copy interval data to use as default for new interval
    - Optional end hour
        - Default to end hour of interval containing the start hour
            - If no day exists, use 24
        - If end hour matches existing interval end, use it without change
        - If end hour splits existing interval, copy interval and increase start hour for the remaining interval
        - If end hour exceeds existing interval, increase start hour of next interval with start hour < end and end hour > end
    - Optional tariff
        - Default to existing interval tariff
            - If no exists, use off peak tariff
        - Set given tariff
    - Optional tariff price
        - Default to existing day tariff prices and currency (no change)
            - If no price exists for interval tariff, use site fixed price, or 0
            - Default to currency in day defined tariffs currency or site currency or set default currency
        - Add or change given tariff price and currency
    - Optional currency
        - Set default currency to site currency or default account currency or hard coded default
        - Change currency in all seasons if provided
    - Optional delete
        - Deletion has various scope, depending which other options provided
        - If tariff given, delete tariff and all slots with it from selected day type(s)
            - If no time slots left for day type, make them same if odd. Otherwise delete also the season and fill the season gap
        - Else if start or end hour given, delete the time slot(s) from given day type and fill the gap with other slot start and end times
            - If no time slots left for day type, make them same if odd.
            - Otherwise delete also the season and fill the season gap
        - Else if day types given, delete the given day types
            - If only one day type given, make them same and use time and tariff definition of other day type
            - Otherwise delete also the season and fill the season gap
        - Else if start or end month given, delete the season(s) and fill the gap with other seasons start and end month
            - If no season remains, delete use time plan
        - Else delete whole use time plan
    """

    # Validate parameters
    months: list[str] = [
        "jan",
        "feb",
        "mar",
        "apr",
        "may",
        "jun",
        "jul",
        "aug",
        "sep",
        "oct",
        "nov",
        "dec",
    ]
    # convert month to recognizable string if string provided
    start_month = (
        str(start_month).lower()[0:3] if isinstance(start_month, str) else start_month
    )
    end_month = str(end_month).lower()[0:3] if isinstance(end_month, str) else end_month
    # get valid integer for month or set None
    start_month = (
        max(1, min(12, int(start_month)))
        if (str(start_month).isdigit() or isinstance(start_month, int | float))
        else months.index(start_month) + 1
        if str(start_month) in months
        else None
    )
    end_month = (
        max(1, min(12, int(end_month)))
        if (str(end_month).isdigit() or isinstance(end_month, int | float))
        else months.index(end_month) + 1
        if str(end_month) in months
        else None
    )
    # ensure end month is equal or larger than start month for considering valid range
    if start_month and end_month:
        end_month = end_month if end_month >= start_month else None
    # get valid integer for hour or set None
    if isinstance(start_hour, datetime):
        start_hour = start_hour.time()
    start_hour = (
        max(0, min(23, int(start_hour)))
        if (str(start_hour).isdigit() or isinstance(start_hour, int | float))
        else start_hour.hour
        if isinstance(start_hour, time)
        else None
    )
    if isinstance(end_hour, datetime):
        end_hour = end_hour.time()
    end_hour = (
        max(1, min(24, int(end_hour)))
        if (str(end_hour).isdigit() or isinstance(end_hour, int | float))
        else end_hour.hour
        if isinstance(end_hour, time)
        and end_hour < datetime.strptime("23:59", "%H:%M").time()
        else 24
        if isinstance(end_hour, time)
        else None
    )
    # ensure end hour is larger than start hour for considering valid range
    if not (start_hour is None or end_hour is None):
        end_hour = end_hour if end_hour > start_hour else None
    day_type = (
        str(day_type).lower()
        if str(day_type).lower() in {item.value for item in SolixDayTypes}
        else None
    )
    # ensure NONE tariff type is ignored for any modifications
    tariff_type = (
        int(getattr(SolixTariffTypes, str(tariff_type).upper()))
        if hasattr(SolixTariffTypes, str(tariff_type).upper())
        and str(tariff_type).upper() != SolixTariffTypes.UNKNOWN.name
        else int(tariff_type)
        if (str(tariff_type).isdigit() or isinstance(tariff_type, int | float))
        and int(tariff_type) in iter(SolixTariffTypes)
        and int(tariff_type) != SolixTariffTypes.UNKNOWN.value
        else None
    )
    tariff_price = (
        f"{float(tariff_price):.2f}"
        if str(tariff_price).replace(".", "", 1).isdigit()
        else None
    )
    currency = str(currency)[0:3] if currency else None
    delete = delete if isinstance(delete, bool) else False
    merge_tariff_slots = (
        merge_tariff_slots if isinstance(merge_tariff_slots, bool) else True
    )
    clear_unused_tariff = (
        clear_unused_tariff if isinstance(clear_unused_tariff, bool) else True
    )

    # fast return if no valid options provided
    if not (
        start_month
        or end_month
        or start_hour is not None
        or end_hour
        or day_type
        or tariff_type
        or tariff_price
        or currency
        or delete
    ):
        self._logger.error(
            "Api %s no valid use time plan options provided", self.apisession.nickname
        )
        return False
    # set parameters for the lookup
    # Consider time zone shifts
    tz_offset = (self.sites.get(siteId) or {}).get("energy_offset_tz") or 0
    now = datetime.now() + timedelta(seconds=tz_offset)
    find_month = (
        start_month
        if start_month is not None
        else end_month
        if end_month is not None
        else now.month
    )
    find_hour = (
        start_hour
        if start_hour is not None
        else end_hour - 1
        if end_hour is not None
        else now.hour
    )

    # set parameters for the deletion scope, starting from smallest to largest
    delete_scope = None
    if delete:
        if start_hour is not None or end_hour:
            delete_scope = "slot"
        elif tariff_type:
            delete_scope = "tariff"
        elif day_type in [SolixDayTypes.WEEKDAY.value, SolixDayTypes.WEEKEND.value]:
            delete_scope = "daytype"
        elif start_month or end_month:
            delete_scope = "season"
        elif not (tariff_price or currency):
            delete_scope = "plan"

    # set defaults if needed
    def_day_type = (
        SolixDayTypes.WEEKDAY
        if 0 < int(now.strftime("%w")) < 6
        else SolixDayTypes.WEEKEND
    )
    def_currency = (
        currency
        or
        # extract active site currency
        next(
            iter(
                item.get("unit")
                for item in ((self.sites.get(siteId) or {}).get("statistics") or [])
                if item.get("type") == "3"
            ),
            None,
        )
        # get default currency for account
        or (self.account.get("default_currency") or {}).get("symbol")
        # use hard coded currency
        or SolixDefaults.CURRENCY_DEF
    )
    def_tariff_type = SolixDefaults.TARIFF_DEF if tariff_type is None else tariff_type
    def_tariff_price = (
        tariff_price
        or str(
            ((self.sites.get(siteId) or {}).get("site_details") or {}).get("price")
            or ""
        )
        or SolixDefaults.TARIFF_PRICE_DEF
    )

    # obtain actual device schedule from internal dict or fetch via api
    if not isinstance(test_schedule, dict):
        test_schedule = None
    if test_schedule:
        schedule = test_schedule
    elif not (schedule := (self.devices.get(deviceSn) or {}).get("schedule") or {}):
        schedule = (
            await self.get_device_parm(
                siteId=siteId,
                paramType=SolixParmType.SOLARBANK_2_SCHEDULE.value,
                deviceSn=deviceSn,
                fromFile=toFile,
            )
        ).get("param_data") or {}

    rate_plan_name = SolarbankRatePlan.use_time
    new_ranges = []
    if not (ranges := schedule.get(rate_plan_name) or []):
        # define default season to be modified
        ranges = [
            {
                "sea": {"start_month": 1, "end_month": 12},
                "weekday": [
                    {"start_time": 0, "end_time": 24, "type": def_tariff_type},
                ],
                "weekend": [
                    {"start_time": 0, "end_time": 24, "type": def_tariff_type},
                ],
                "weekday_price": [
                    {"price": def_tariff_price, "type": def_tariff_type},
                ],
                "weekend_price": [
                    {"price": def_tariff_price, "type": def_tariff_type},
                ],
                "unit": def_currency,
                "is_same": SolixDefaults.TARIFF_WE_SAME,
            },
        ]

    # traverse plan and update as required
    if delete_scope != "plan":
        split_season: dict = {}
        split_slot: dict = {}
        delay_hour = None
        delay_month = None
        is_same = False
        for season in ranges:
            # update currency for each season if provided
            if currency:
                season["unit"] = currency
            sea = season.get("sea") or {}
            sea_start = sea.get("start_month")
            sea_end = sea.get("end_month")
            if delay_month:
                if (
                    len(new_ranges) == 0
                    and delay_month <= 12
                    and find_month < sea_start
                ):
                    # no previous slot after deletion, expand slot to beginning and skip remaining changes
                    delay_month = None
                    season["sea"]["start_month"] = 1
                    new_ranges.append(season)
                    continue
                if sea_end >= delay_month or find_month >= sea_start:
                    season["sea"]["start_month"] = (
                        1 if len(new_ranges) == 0 else delay_month
                    )
                    delay_month = None
                else:
                    # skip season if overwritten
                    continue
            if sea_start <= find_month <= sea_end:
                if delete_scope == "season":
                    # deletion scope can just extend actual season if range was defined
                    end_month = max(
                        end_month if start_month and end_month else sea_end, sea_end
                    )
                    delay_month = end_month + 1
                    # adjust previous season to fill gap of deleted season(s)
                    if len(new_ranges) > 0:
                        new_ranges[-1]["sea"]["end_month"] = end_month
                    continue
                # use start month of matching season if not provided and adjust split season
                if delete_scope in ["daytype", "tariff", "slot"]:
                    # always set start month to current season start for repetiive traversal without month changes
                    start_month = sea_start
                elif not start_month:
                    start_month = sea_start
                    # overwrite end_month with season end to prevent split or expand when no range was given
                    end_month = sea_end
                elif start_month and start_month > sea_start and end_month:
                    # split season by copy
                    split_season = copy.deepcopy(season)
                    split_season["sea"]["end_month"] = start_month - 1
                    new_ranges.append(split_season)
                    split_season = {}
                # use end month of matching season if not provided and adjust split season or expanded season
                if not end_month:
                    end_month = sea_end
                elif delete_scope in ["daytype", "tariff", "slot"] and start_month:
                    # extend find_month to following seasons for lower level deletion scopes and valid month range
                    find_month = sea_end + 1 if end_month > sea_end else find_month
                elif end_month > sea_end:
                    delay_month = end_month + 1
                elif end_month < sea_end:
                    # split season by copy
                    split_season = copy.deepcopy(season)
                    split_season["sea"]["start_month"] = end_month + 1
                # Adjust current season range if not low level deletion scope
                if delete_scope not in ["daytype", "tariff", "slot"]:
                    season["sea"]["start_month"] = start_month
                    season["sea"]["end_month"] = end_month

                # select dayslot for adjustments based on day types and actual same setting
                is_same = season.get("is_same")
                copy_day = None
                if delete_scope in ["daytype", "tariff", "slot"]:
                    # delete the requested daytype and make them same by copying the other daytype slots and prices
                    if is_same:
                        if delete_scope in ["tariff", "slot"]:
                            # process lower level deletion scope
                            modify_days = [SolixDayTypes.WEEKDAY.value]
                            copy_day = SolixDayTypes.WEEKEND.value
                        else:
                            # do not delete a requested daytype if they are same
                            modify_days = []
                    elif day_type == SolixDayTypes.WEEKDAY.value:
                        modify_days = [SolixDayTypes.WEEKEND.value]
                        copy_day = SolixDayTypes.WEEKDAY.value
                        is_same = True
                    elif day_type == SolixDayTypes.WEEKEND.value:
                        modify_days = [SolixDayTypes.WEEKDAY.value]
                        copy_day = SolixDayTypes.WEEKEND.value
                        is_same = True
                elif day_type in [
                    SolixDayTypes.WEEKDAY.value,
                    SolixDayTypes.WEEKEND.value,
                ]:
                    # modify only given daytype
                    modify_days = [day_type]
                    if is_same:
                        is_same = False
                elif day_type == SolixDayTypes.ALL.value:
                    # modify all daytypes
                    if is_same:
                        modify_days = [SolixDayTypes.WEEKDAY.value]
                        copy_day = SolixDayTypes.WEEKEND.value
                    else:
                        modify_days = [
                            SolixDayTypes.WEEKDAY.value,
                            SolixDayTypes.WEEKEND.value,
                        ]
                # modify active daytype
                elif is_same:
                    modify_days = [SolixDayTypes.WEEKDAY.value]
                    copy_day = SolixDayTypes.WEEKEND.value
                else:
                    modify_days = [def_day_type]
                for day in modify_days:
                    # weeday or weekend
                    slots = []
                    find_tariff = set()
                    delay_hour = None
                    day_start_hour = start_hour
                    day_end_hour = end_hour
                    day_tariff_type = tariff_type
                    # flag for allowing tarif change in slot or not
                    # Allow change in slot only if only one slot or if either start or end hour is given
                    day_tariff_change = (
                        tariff_type
                        and (
                            not (
                                tariff_price and start_hour is None and end_hour is None
                            )
                            or len(season.get(day) or []) == 1
                        )
                        and delete_scope not in ["daytype", "tariff", "slot"]
                    )
                    for slot in season.get(day) or []:
                        start = slot.get("start_time")
                        end = slot.get("end_time")
                        tariff = slot.get("type")
                        if delete_scope == "tariff" and tariff == tariff_type:
                            # delete all slots with the given tariff and ensure to adjust other slot times to avoid gaps
                            delay_hour = max(delay_hour or end, end)
                            if len(slots) > 0:
                                slots[-1]["end_time"] = delay_hour
                            continue
                        if delay_hour:
                            if len(slots) == 0 and delay_hour < 24:
                                # no previous slot after a deletion that set delay hour, expand slot to beginning and skip remaining changes
                                delay_hour = None
                                slot["start_time"] = 0
                                find_tariff.add(tariff)
                                slots.append(slot)
                                continue
                            if end > delay_hour:
                                slot["start_time"] = (
                                    0 if len(slots) == 0 else delay_hour
                                )
                                delay_hour = None
                            else:
                                # skip slot if overwritten
                                continue
                        if start <= find_hour < end:
                            if delete_scope == "slot":
                                # use start hour of found slot, deletion scope can just extend actual slot if range was defined
                                day_start_hour = start
                                day_end_hour = max(
                                    day_end_hour
                                    if not (
                                        day_start_hour is None or day_end_hour is None
                                    )
                                    else end,
                                    end,
                                )
                                delay_hour = day_end_hour
                                # adjust previous slot to fill gap of deleted slot(s)
                                if len(slots) > 0:
                                    slots[-1]["end_time"] = delay_hour
                                continue
                            # use start hour of matching slot if not provided and adjust split slot
                            if day_start_hour is None:
                                day_start_hour = start
                                # overwrite end_hour with slot end to prevent split or expand when no range was given
                                day_end_hour = end
                            elif day_start_hour > start and day_end_hour is not None:
                                # split slot by copy or merge with previous
                                if (
                                    len(slots) > 0
                                    and slots[-1]["type"] == tariff
                                    and merge_tariff_slots
                                ):
                                    # merge with previous slot if same tariff type
                                    slots[-1]["end_time"] = day_start_hour
                                else:
                                    # Copy and add slot
                                    split_slot = copy.deepcopy(slot)
                                    split_slot["end_time"] = day_start_hour
                                    find_tariff.add(tariff)
                                    slots.append(split_slot)
                                    split_slot = {}
                            # use end hour of matching slot if not provided and adjust split slot or expanded slot
                            if day_end_hour is None:
                                day_end_hour = end
                            elif day_end_hour > end:
                                delay_hour = day_end_hour
                            elif day_end_hour < end:
                                # split slot by copy if tariff is different to new tariff
                                if (
                                    day_tariff_change and tariff_type != tariff
                                ) or not merge_tariff_slots:
                                    # split slot by copy
                                    split_slot = copy.deepcopy(slot)
                                    split_slot["start_time"] = day_end_hour
                                else:
                                    day_end_hour = end
                            # Adjust current slot range
                            slot["start_time"] = day_start_hour
                            slot["end_time"] = day_end_hour
                            # make slot tariff adjustments if no price or range given
                            # Price without range is considered as change for the given tariff type only, but not for changing tariff for slots
                            if day_tariff_change:
                                tariff = tariff_type
                                slot["type"] = tariff
                            elif not day_tariff_type:
                                # set dayttype tariff of modified slot for price adjustment if no tariff defined
                                day_tariff_type = slot.get("type")
                        # Merge with previous slots if they have same tariff and merge allowed
                        if (
                            len(slots) > 0
                            and slots[-1]["type"] == tariff
                            and merge_tariff_slots
                        ):
                            # merge with previous slot if same tariff type
                            slots[-1]["end_time"] = slot.get("end_time")
                        else:
                            slots.append(slot)
                            find_tariff.add(tariff)
                        if split_slot:
                            # This split slot should have different tariff or merge is not allowed and must be appended
                            slots.append(split_slot)
                            find_tariff.add(split_slot.get("type"))
                            split_slot = {}
                    # add modified slot(s) into season
                    season[day] = slots

                    if slots:
                        prices = []
                        for price in season.get(day + "_price") or []:
                            tariff = price.get("type")
                            if clear_unused_tariff and (
                                (delete_scope == "tariff" and tariff == day_tariff_type)
                                or tariff not in find_tariff
                            ):
                                # delete unused tariff price
                                find_tariff.discard(tariff)
                                continue
                            if tariff_price and tariff == day_tariff_type:
                                # update price of tariff if specified
                                price["price"] = tariff_price
                            # remove found tariff to prevent it will be added
                            find_tariff.discard(tariff)
                            prices.append(price)
                            # adjust default price to stay in line with prices of existing tarrifs, higher types must be cheaper
                            if (
                                not tariff_price
                                and str(day_tariff_type).isdigit()
                                and str(tariff).isdigit()
                                and str(tp := price.get("price") or 0)
                                .replace(".", "", 1)
                                .isdigit()
                            ):
                                if day_tariff_type < tariff:
                                    # added tariff must be higher price
                                    def_tariff_price = str(
                                        max(float(def_tariff_price), float(tp))
                                    )
                                elif day_tariff_type > tariff:
                                    # added tariff must be lower price
                                    def_tariff_price = str(
                                        min(float(def_tariff_price), float(tp))
                                    )
                        # Ensure to append remaining tariffs to price list
                        prices.extend(
                            {
                                "price": tariff_price or def_tariff_price,
                                "type": tariff,
                            }
                            for tariff in find_tariff
                        )
                        season[day + "_price"] = prices

                        # adjust other daytype settings as modified
                        if copy_day:
                            # Copy days and tariffs
                            season[copy_day] = season.get(day)
                            season[copy_day + "_price"] = season.get(day + "_price")
                        elif (
                            not is_same
                            and len(modify_days) > 0
                            and day == modify_days[-1]
                        ):
                            # compare and activate is same if they are same after last day modification
                            other = (
                                SolixDayTypes.WEEKDAY.value
                                if day == SolixDayTypes.WEEKEND.value
                                else SolixDayTypes.WEEKEND.value
                            )
                            if (
                                season[day] == season[other]
                                and season[day + "_price"] == season[other + "_price"]
                            ):
                                is_same = True
                        season["is_same"] = is_same

                    elif not is_same:
                        # No slots left for daytype but not same, copy other daytype and make same
                        other = (
                            SolixDayTypes.WEEKDAY.value
                            if day == SolixDayTypes.WEEKEND.value
                            else SolixDayTypes.WEEKEND.value
                        )
                        is_same = True
                        season["is_same"] = is_same
                        season[day] = season.get(other)
                        season[day + "_price"] = season.get(other + "_price")
                    elif copy_day or is_same:
                        # remove season since no slot left and daytypes are same
                        season = []
                        if (
                            delete_scope in ["daytype", "tariff", "slot"]
                            and start_month
                            and end_month
                        ):
                            delay_month = sea_end + 1
                        else:
                            end_month = max(end_month or sea_end, sea_end)
                            delay_month = end_month + 1
                        # adjust previous season to fill gap of deleted season(s)
                        if len(new_ranges) > 0:
                            new_ranges[-1]["sea"]["end_month"] = delay_month - 1

            # save season(s) to new ranges
            if season:
                new_ranges.append(season)
            if split_season:
                new_ranges.append(split_season)
                split_season = {}

    schedule[rate_plan_name] = new_ranges
    # toggle usage mode in schedule back to possible mode if no use_time plan remains
    if (
        not new_ranges
        and schedule.get("mode_type") == SolarbankUsageMode.use_time.value
    ):
        # Allow automatic modes only when smart meter or smart plugs available in site
        usage_mode_options = self.solarbank_usage_mode_options(deviceSn=deviceSn)
        schedule["mode_type"] = getattr(
            SolarbankUsageMode,
            ({usage_mode_options} & {SolarbankUsageMode.smartmeter.name})
            or ({usage_mode_options} & {SolarbankUsageMode.smartplug.name})
            or SolarbankUsageMode.manual.name,
        )
    self._logger.debug(
        "Api %s schedule to be applied: %s", self.apisession.nickname, schedule
    )
    # return resulting schedule for test purposes without Api call
    if test_schedule:
        # ensure complete schedule is updated in cache for dependent fields
        await self.get_device_parm(
            siteId=siteId,
            paramType=SolixParmType.SOLARBANK_2_SCHEDULE.value,
            testSchedule=schedule,
            deviceSn=deviceSn,
        )
        return schedule
    # The applied schedule need to separate plans for AC model and common SB2 plans
    # The mode_type must always be contained
    # TODO(SB3): This may need updates once plan names for SB3 are known and modification was tested, e.g. time_slot plan
    mode_type = schedule.get("mode_type")
    new_schedule = {"mode_type": mode_type}
    if rate_plan_name in {SolarbankRatePlan.manual, SolarbankRatePlan.smartplugs}:
        new_schedule.update(
            {
                SolarbankRatePlan.manual: schedule.get(SolarbankRatePlan.manual) or [],
                SolarbankRatePlan.smartplugs: schedule.get(SolarbankRatePlan.smartplugs)
                or [],
            }
        )
    else:
        # AC unique plans to be separated for Api call
        new_schedule.update(
            {
                SolarbankRatePlan.backup: schedule.get(SolarbankRatePlan.backup) or {},
                SolarbankRatePlan.use_time: schedule.get(SolarbankRatePlan.use_time)
                or [],
            }
        )
    # Make the Api call with the schedule subset to be applied and return result, the set call will also re-read full schedule and update api dict
    resp = await self.set_device_parm(
        siteId=siteId,
        paramType=SolixParmType.SOLARBANK_2_SCHEDULE.value,
        paramData=schedule if toFile else new_schedule,
        deviceSn=deviceSn,
        toFile=toFile,
    )
    # Make also the price type change if required by usage mode change
    # The mobile App only activates use_time price automatically with use_time mode, but may not toggle back to fixed price automatically
    price_type = ((self.sites.get(siteId) or {}).get("site_details") or {}).get(
        "price_type"
    )
    new_price_type = None
    if mode_type in iter(SolarbankUsageMode) and price_type:
        if (
            mode_type in [SolarbankUsageMode.use_time.value]
            and schedule.get(SolarbankRatePlan.use_time)
            and price_type != SolixPriceTypes.USE_TIME.value
        ):
            new_price_type = SolixPriceTypes.USE_TIME.value
    if new_price_type:
        self._logger.debug(
            "Toggling api %s price type to: %s",
            self.apisession.nickname,
            new_price_type,
        )
        await self.set_site_price(
            siteId=siteId, price_type=new_price_type, toFile=toFile
        )
    return resp
