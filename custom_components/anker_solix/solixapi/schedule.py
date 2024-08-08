"""Anker Power/Solix Cloud API class outsourced schedule related methods."""

import contextlib
import copy
from datetime import datetime
import json
import os

from .types import (
    API_ENDPOINTS,
    Solarbank2Timeslot,
    SolarbankPowerMode,
    SolarbankTimeslot,
    SolarbankUsageMode,
    SolixDefaults,
    SolixParmType,
)


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
    Attention: This method and endpoint actually returns only solarbank 1 schedule structure, which is invalid for different Solarbank 2 structures.
    While it also returns the applied home load settings, it cannot be used for Solarbank 2 due to wrong schedule data.
    """
    data = {"site_id": siteId, "device_sn": deviceSn}
    if fromFile:
        resp = await self._loadFromFile(
            os.path.join(self._testdir, f"device_load_{deviceSn}.json")
        )
    else:
        resp = await self.request("post", API_ENDPOINTS["get_device_load"], json=data)
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
    Attention: This method and endpoint actually accepts the input data, but does not change anything on the solarbank 1.
    The set_device_parm endpoint has to be used instead.
    TODO: Test if this method can be used for Solarbank 2 schedule structure?
    """
    data = {
        "site_id": siteId,
        "device_sn": deviceSn,
        "home_load_data": json.dumps(loadData),
    }
    # Make the Api call and check for return code
    code = (
        await self.request("post", API_ENDPOINTS["set_device_load"], json=data)
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
    \"blend_plan\":null,\"default_home_load\":200,\"max_load\":800,\"min_load\":0,\"step\":10}"}
    """
    data = {"site_id": siteId, "param_type": paramType}
    if fromFile:
        resp = await self._loadFromFile(
            os.path.join(self._testdir, f"device_parm_{paramType}_{siteId}.json")
        )
        # ensure backward filename compatibility without parm type in name
        if not resp and paramType == SolixParmType.SOLARBANK_SCHEDULE.value:
            resp = await self._loadFromFile(
                os.path.join(self._testdir, f"device_parm_{siteId}.json")
            )
    else:
        resp = await self.request("post", API_ENDPOINTS["get_device_parm"], json=data)
    # The home_load_data is provided as string instead of object...Convert into object for proper handling
    # It must be converted back to a string when passing this as input to set home load
    string_data = (resp.get("data", {})).get("param_data", {})
    if isinstance(string_data, str):
        resp["data"].update({"param_data": json.loads(string_data)})

    # update api device dict with latest data if optional device SN was provided, e.g. when called by set_device_parm for device details update
    data = resp.get("data") or {}
    # update schedule also for other device serials found in Solarbank 1 schedules
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
) -> bool:
    r"""Set device parameters (e.g. solarbank schedule).

    command: Must be 17 for solarbank schedule.
    paramType: was always string "4" for SB1, SB2 needs "6" and different structure
    Example paramData for type "4":
    {"param_data": '{"ranges":['
        '{"id":0,"start_time":"00:00","end_time":"08:30","turn_on":true,"appliance_loads":[{"id":0,"name":"Benutzerdefiniert","power":300,"number":1}],"charge_priority":80},'
        '{"id":0,"start_time":"08:30","end_time":"17:00","turn_on":false,"appliance_loads":[{"id":0,"name":"Benutzerdefiniert","power":100,"number":1}],"charge_priority":80},'
        '{"id":0,"start_time":"17:00","end_time":"24:00","turn_on":true,"appliance_loads":[{"id":0,"name":"Benutzerdefiniert","power":300,"number":1}],"charge_priority":0}],'
    '"min_load":100,"max_load":800,"step":0,"is_charge_priority":0,default_charge_priority":0}}'

    Example data for provided site_id with param_type 6 for SB2:
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
    code = (
        await self.request("post", API_ENDPOINTS["set_device_parm"], json=data)
    ).get("code")
    if not isinstance(code, int) or int(code) != 0:
        return False
    # update the data in api dict
    await self.get_device_parm(siteId=siteId, paramType=paramType, deviceSn=deviceSn)
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
    test_schedule: dict | None = None,  # used only for testing instead of real schedule
    test_count: int
    | None = None,  # used only for testing instead of real solarbank count
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
        schedule = (await self.get_device_load(siteId=siteId, deviceSn=deviceSn)).get(
            "home_load_data"
        ) or {}
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
    # update individual values in current slot or insert SolarbankTimeslot and adjust adjacent slots
    if not set_slot:
        now = datetime.now().time().replace(microsecond=0)
        last_time = datetime.strptime("00:00", "%H:%M").time()
        # set now to new daytime if close to end of day to determine which slot to modify
        if now >= datetime.strptime("23:59:58", "%H:%M:%S").time():
            now = datetime.strptime("00:00", "%H:%M").time()
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
                        last_time <= now < start_time
                        or (idx == len(ranges) and now >= end_time)
                    )
                ):
                    # Use daily end time if now after last slot
                    insert: dict = copy.deepcopy(slot)
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
                                                (preset - dev_preset) / (sb_count - 1)
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
            (slot.get("appliance_loads") or [{}])[0].update({"name": appliance_name})
        new_ranges.append(slot)
    self._logger.debug(
        "Ranges to apply: %s",
        new_ranges,
    )
    schedule.update({"ranges": new_ranges})
    # return resulting schedule for test purposes without Api call
    if test_count is not None or test_schedule is not None:
        return schedule
    # Make the Api call with final schedule and return result, the set call will also update api dict
    # NOTE: set_device_load does not seem to be usable yet for changing the home load, or is only usable in dual bank setups for changing the appliance load share as well?
    return await self.set_device_parm(
        siteId=siteId,
        paramData=schedule,
        deviceSn=deviceSn,
    )


async def set_sb2_home_load(  # noqa: C901
    self,
    siteId: str,
    deviceSn: str,
    preset: int | None = None,
    usage_mode: int | None = None,
    set_slot: Solarbank2Timeslot | None = None,
    insert_slot: Solarbank2Timeslot | None = None,
    test_schedule: dict | None = None,  # used only for testing instead of real schedule
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

    Example schedule for Solarbank 2 as provided via Api:
    Example data for provided site_id with param_type 6 for SB2:
    "schedule": {
        "mode_type": 3,"custom_rate_plan": [
            {"index": 0,"week": [0,6],"ranges": [
                {"start_time": "00:00","end_time": "24:00","power": 110}]},
            {"index": 1,"week": [1,2,3,4,5],"ranges": [
                {"start_time": "00:00","end_time": "08:00","power": 100},
                {"start_time": "08:00","end_time": "22:00","power": 120},
                {"start_time": "22:00","end_time": "24:00","power": 90}]}],
        "blend_plan": null,"default_home_load": 200,"max_load": 800,"min_load": 0,"step": 10}
    """
    # fast quit if nothing to change
    preset = (
        int(preset)
        if str(preset).isdigit() or isinstance(preset, int | float)
        else None
    )
    # Allow automatic mode only when smartmeter available in site
    usage_mode = (
        usage_mode
        if isinstance(usage_mode, int)
        and usage_mode in iter(SolarbankUsageMode)
        and not (
            usage_mode == SolarbankUsageMode.smartmeter.value
            and len(
                ((self.sites.get(siteId) or {}).get("grid_info") or {}).get("grid_list")
                or []
            )
            < 1
        )
        and not (
            usage_mode == SolarbankUsageMode.smartplugs.value
            and len(
                ((self.sites.get(siteId) or {}).get("smartplug_info") or {}).get(
                    "smartplug_list"
                )
                or []
            )
            < 1
        )
        else None
    )
    if (
        preset is None
        and usage_mode is None
        and set_slot is None
        and insert_slot is None
    ):
        self._logger.error("No valid schedule options provided")
        return False

    # set flag for required current parameter update
    pending_now_update = bool(set_slot is None and insert_slot is None)
    # obtain actual device schedule from internal dict or fetch via api
    if test_schedule is not None:
        schedule = test_schedule
    elif not (schedule := (self.devices.get(deviceSn) or {}).get("schedule") or {}):
        schedule = (
            await self.get_device_parm(
                siteId=siteId,
                paramType=SolixParmType.SOLARBANK_2_SCHEDULE.value,
                deviceSn=deviceSn,
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

    # update the usage mode in the overall schedule object
    if usage_mode is not None:
        schedule.update({"mode_type": usage_mode})

    rate_plan = schedule.get("custom_rate_plan") or []
    new_rate_plan = []

    # identify week days to be used, default to todays weekday or all
    days: list[str] = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]
    weekdays = (
        {int(datetime.now().strftime("%w"))}
        if rate_plan and not delete_plan
        else set(range(7))
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
                "Incomplete interval definitions for insert_slot, missing %s",
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
            "Invalid weekdays provided for schedule change: %s",
            insert_slot.weekdays or set_slot.weekdays,
        )
        return False
    # First identify a matching rate plan for provided week days
    # When weekday combination exists, re-use the same. When provided weekdays have extra days to existing, merge extra weekdays to existing
    # When existing weekdays are partial subset of provided weekdays, clone first plan with most matching days as new plan for the defined weekdays to separate them from existing plan
    matched_days = set()
    index = None
    if preset is not None or set_slot or insert_slot:
        if not delete_plan:
            for idx in rate_plan:
                if len((days := set(idx.get("week") or [])) & weekdays) > len(
                    matched_days & weekdays
                ):
                    matched_days = days.copy()
                    index = idx.get("index")
                    # re-use matching plan days if no weekdays provided
                    if match_plan:
                        weekdays = days.copy()
                    # quit loop on total match
                    if (matched_days & weekdays) == weekdays:
                        # all days defined, reuse plan
                        break
            if index is None:
                # set next index number if no matching days found
                index = len(rate_plan)
                rate_plan.append({"index": index, "week": weekdays, "ranges": []})
            elif (matched_days & weekdays) != matched_days:
                # Clone existing ranges to new plan if only partial subset of provided days
                new_ranges = list(rate_plan[index].get("ranges") or [])
                index = len(rate_plan)
                rate_plan.append(
                    {"index": index, "week": weekdays, "ranges": new_ranges}
                )
            else:
                # Merge new and existing weekdays since existing plan is for complete subset of new weekdays
                weekdays = weekdays | set(rate_plan[index].get("week") or [])
        # create new rate plan and curate existing weekdays
        removed = 0
        for idx in rate_plan:
            new_idx = copy.deepcopy(idx)
            if new_days := (
                sorted(weekdays)
                if idx.get("index") == index
                else sorted(set(idx.get("week") or []) - weekdays)
            ):
                # add merged weekdays
                new_idx.update({"index": idx.get("index") - removed, "week": new_days})
                new_rate_plan.append(new_idx)
                # adjust rate plan list index to new number
                if idx.get("index") == index:
                    index -= removed
            else:
                # skip index in new rate plan and adjust remaining
                removed += 1
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
    if preset is not None or pending_insert:
        now = datetime.now().time().replace(microsecond=0)
        last_time = datetime.strptime("00:00", "%H:%M").time()
        # set now to new daytime if close to end of day to determine which slot to modify
        if now >= datetime.strptime("23:59:58", "%H:%M:%S").time():
            now = datetime.strptime("00:00", "%H:%M").time()
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
                        last_time <= now < start_time
                        or (idx == len(ranges) and now >= end_time)
                    )
                ):
                    # Use daily end time if now after last slot
                    insert: dict = copy.deepcopy(slot)
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
                    if now < start_time:
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

                elif not insert_slot and (start_time <= now < end_time):
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
    elif not delete_plan:
        new_rate_plan: list = [
            {
                "index": 0,
                "week": list(weekdays),
                "ranges": new_ranges,
            }
        ]
    self._logger.info(
        "Rate plan to apply: %s",
        new_rate_plan,
    )
    schedule.update({"custom_rate_plan": new_rate_plan})
    # return resulting schedule for test purposes without Api call
    if test_schedule is not None:
        return schedule
    # Make the Api call with final schedule and return result, the set call will also update api dict
    return await self.set_device_parm(
        siteId=siteId,
        paramType=SolixParmType.SOLARBANK_2_SCHEDULE.value,
        paramData=schedule,
        deviceSn=deviceSn,
    )
