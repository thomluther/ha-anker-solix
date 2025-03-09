"""Anker Power/Solix Cloud API class energy related methods."""

from datetime import datetime, timedelta
from pathlib import Path

from .apitypes import API_ENDPOINTS, API_FILEPREFIXES, SolixDeviceType


async def energy_daily(  # noqa: C901
    self,
    siteId: str,
    deviceSn: str,
    startDay: datetime = datetime.today(),
    numDays: int = 1,
    dayTotals: bool = False,
    devTypes: set | None = None,
    fromFile: bool = False,
    showProgress: bool = False,
) -> dict:
    """Fetch daily Energy data for given interval and provide it in a table format dictionary.

    Solar production data is always queried. Additional energy data will be queried for devtypes 'solarbank' or 'smartmeter'. The number of
    queries is optimized if dayTotals is True
    Example:
    {"2023-09-29": {"date": "2023-09-29", "solar_production": "1.21", "battery_discharge": "0.47", "battery_charge": "0.56"},
     "2023-09-30": {"date": "2023-09-30", "solar_production": "3.07", "battery_discharge": "1.06", "battery_charge": "1.39"}}
    """
    table = {}
    if not devTypes or not isinstance(devTypes, set):
        devTypes = set()
    today = datetime.today()
    # check daily range and limit to 1 year max and avoid future days
    if startDay > today:
        startDay = today
        numDays = 1
    elif (startDay + timedelta(days=numDays)) > today:
        numDays = (today - startDay).days + 1
    numDays = min(366, max(1, numDays))

    # first get solarbank export
    if SolixDeviceType.SOLARBANK.value in devTypes:
        # get first data period from file or api
        justify_daytotals = bool(
            dayTotals
            and ((self.devices.get(deviceSn) or {}).get("generation") or 0) > 1
        )
        if fromFile:
            resp = (
                await self.apisession.loadFromFile(
                    Path(self.testDir())
                    / f"{API_FILEPREFIXES['energy_solarbank']}_{siteId}.json"
                )
            ).get("data", {})
        else:
            resp = await self.energy_analysis(
                siteId=siteId,
                deviceSn=deviceSn,
                rangeType="week",
                startDay=startDay,
                endDay=startDay
                if justify_daytotals
                else startDay + timedelta(days=numDays - 1),
                devType="solarbank",
            )
        fileNumDays = 0
        fileStartDay = None
        for item in resp.get("power", []):
            daystr = item.get("time", None)
            if daystr:
                if fromFile:
                    if fileStartDay is None:
                        fileStartDay = daystr
                    fileNumDays += 1
                entry = table.get(daystr, {"date": daystr})
                entry.update(
                    {
                        "date": daystr,
                        "battery_discharge": item.get("value") or None,
                    }
                )
                table.update({daystr: entry})
        # Solarbank 2 has AC socket output and battery to home related totals for given interval. If requested, make daily queries for given interval
        if justify_daytotals and table:
            if fromFile:
                daylist = [
                    datetime.strptime(fileStartDay, "%Y-%m-%d") + timedelta(days=x)
                    for x in range(fileNumDays)
                ]
            else:
                daylist = [startDay + timedelta(days=x) for x in range(numDays)]
            for day in daylist:
                daystr = day.strftime("%Y-%m-%d")
                entry = table.get(daystr, {"date": daystr})
                # update response only for real requests if not first day which was already queried
                if not fromFile and day != startDay:
                    resp = await self.energy_analysis(
                        siteId=siteId,
                        deviceSn=deviceSn,
                        rangeType="week",
                        startDay=day,
                        endDay=day,
                        devType="solarbank",
                    )
                    # get first item from breakdown list for single day queries
                    item = next(iter(resp.get("power") or []), {})
                    if daystr == item.get("time"):
                        entry.update(
                            {
                                "date": daystr,
                                "battery_discharge": item.get("value") or None,
                            }
                        )
                entry.update(
                    {
                        "date": daystr,
                        "ac_socket": resp.get("ac_out_put_total") or None,
                        "battery_to_home": resp.get("battery_to_home_total") or None,
                        "grid_to_battery": resp.get("grid_to_battery_total") or None,
                    }
                )
                table.update({daystr: entry})
                if showProgress:
                    self._logger.info(
                        "Received api %s solarbank energy for %s",
                        self.apisession.nickname,
                        daystr,
                    )
        if showProgress:
            self._logger.info(
                "Received api %s solarbank energy for period",
                self.apisession.nickname,
            )

    # Get home usage energy types if device is solarbank generation 2 or smart meter or smart plugs
    if (
        SolixDeviceType.SOLARBANK.value in devTypes
        and ((self.devices.get(deviceSn) or {}).get("generation") or 0) > 1
    ) or (
        {SolixDeviceType.SMARTMETER.value, SolixDeviceType.SMARTPLUG.value} & devTypes
    ):
        # get first data period from file or api
        justify_daytotals = bool(dayTotals)
        if fromFile:
            resp = (
                await self.apisession.loadFromFile(
                    Path(self.testDir())
                    / f"{API_FILEPREFIXES['energy_home_usage']}_{siteId}.json"
                )
            ).get("data", {})
        else:
            resp = await self.energy_analysis(
                siteId=siteId,
                deviceSn=deviceSn,
                rangeType="week",
                startDay=startDay,
                endDay=startDay
                if justify_daytotals
                else startDay + timedelta(days=numDays - 1),
                devType="home_usage",
            )
        fileNumDays = 0
        fileStartDay = None
        for item in resp.get("power", []):
            daystr = item.get("time", None)
            if daystr:
                if fromFile:
                    if fileStartDay is None:
                        fileStartDay = daystr
                    fileNumDays += 1
                entry = table.get(daystr, {"date": daystr})
                entry.update(
                    {
                        "date": daystr,
                        "home_usage": item.get("value") or None,
                    }
                )
                table.update({daystr: entry})
        # Home usage has Grid import and smart plug related totals for given interval. If requested, make daily queries for given interval
        if justify_daytotals and table:
            if fromFile:
                daylist = [
                    datetime.strptime(fileStartDay, "%Y-%m-%d") + timedelta(days=x)
                    for x in range(fileNumDays)
                ]
            else:
                daylist = [startDay + timedelta(days=x) for x in range(numDays)]
            for day in daylist:
                daystr = day.strftime("%Y-%m-%d")
                entry = table.get(daystr, {"date": daystr})
                # update response only for real requests if not first day which was already queried
                if not fromFile and day != startDay:
                    resp = await self.energy_analysis(
                        siteId=siteId,
                        deviceSn=deviceSn,
                        rangeType="week",
                        startDay=day,
                        endDay=day,
                        devType="home_usage",
                    )
                    # get first item from breakdown list for single day queries
                    item = next(iter(resp.get("power") or []), {})
                    if daystr == item.get("time"):
                        entry.update(
                            {
                                "date": daystr,
                                "home_usage": item.get("value") or None,
                            }
                        )
                entry.update(
                    {
                        "date": daystr,
                        "grid_to_home": resp.get("grid_to_home_total") or None,
                        "smartplugs_total": (resp.get("smart_plug_info") or {}).get(
                            "total_power"
                        )
                        or None,
                    }
                )
                # Add Smart Plug details if available
                if (
                    plug_list := (resp.get("smart_plug_info") or {}).get(
                        "smartplug_list"
                    )
                    or []
                ):
                    entry.update(
                        {
                            "smartplug_list": [
                                {
                                    "device_sn": plug.get("device_sn"),
                                    "alias": plug.get("device_name"),
                                    "energy": plug.get("total_power"),
                                }
                                for plug in plug_list
                            ]
                        }
                    )
                table.update({daystr: entry})
                if showProgress:
                    self._logger.info(
                        "Received api %s home_usage energy for %s",
                        self.apisession.nickname,
                        daystr,
                    )
        if showProgress:
            self._logger.info(
                "Received api %s home_usage energy for period",
                self.apisession.nickname,
            )

    # Add grid stats from smart reader only if solarbank not requested, otherwise grid data available in solarbank and solar responses
    if (
        SolixDeviceType.SMARTMETER.value in devTypes
        and SolixDeviceType.SOLARBANK.value not in devTypes
    ):
        if fromFile:
            resp = (
                await self.apisession.loadFromFile(
                    Path(self.testDir())
                    / f"{API_FILEPREFIXES['energy_grid']}_{siteId}.json"
                )
            ).get("data", {})
        else:
            resp = await self.energy_analysis(
                siteId=siteId,
                deviceSn=deviceSn,
                rangeType="week",
                startDay=startDay,
                endDay=startDay + timedelta(days=numDays - 1),
                devType="grid",
            )
        fileNumDays = 0
        fileStartDay = None
        for item in resp.get("power", []):
            daystr = item.get("time", None)
            if daystr:
                if fromFile:
                    if fileStartDay is None:
                        fileStartDay = daystr
                    fileNumDays += 1
                entry = table.get(daystr, {"date": daystr})
                entry.update(
                    {
                        "date": daystr,
                        # grid export is negative, convert to re-use as solar_to_grid value
                        "solar_to_grid": item.get("value", "").replace("-", "") or None,
                    }
                )
                table.update({daystr: entry})
        for item in resp.get("charge_trend", []):
            daystr = item.get("time", None)
            if daystr:
                entry = table.get(daystr, {"date": daystr})
                entry.update(
                    {
                        "date": daystr,
                        "grid_to_home": item.get("value") or None,
                    }
                )
                table.update({daystr: entry})
        if showProgress:
            self._logger.info(
                "Received api %s grid energy for period",
                self.apisession.nickname,
            )

    # Add solar energy per channel if supported by device, e.g. Solarbank 2 embedded inverter
    if SolixDeviceType.INVERTER.value in devTypes:
        for ch in ["pv" + str(num) for num in range(1, 5)] + ["micro_inverter"]:
            # query only if provided device SN has solar power values in cache
            if (
                f"solar_power_{ch.replace('pv', '')}"
                in (dev := self.devices.get(deviceSn) or {})
                or f"{ch}_power" in dev
            ):
                if fromFile:
                    resp = (
                        await self.apisession.loadFromFile(
                            Path(self.testDir())
                            / f"{API_FILEPREFIXES['energy_solar_production']}_{ch.replace('_', '')}_{siteId}.json"
                        )
                    ).get("data") or {}
                else:
                    resp = await self.energy_analysis(
                        siteId=siteId,
                        deviceSn=deviceSn,
                        rangeType="week",
                        startDay=startDay,
                        endDay=startDay + timedelta(days=numDays - 1),
                        devType=f"solar_production_{ch.replace('_', '')}",
                    )
                fileNumDays = 0
                fileStartDay = None
                for item in resp.get("power", []):
                    daystr = item.get("time", None)
                    if daystr:
                        if fromFile:
                            if fileStartDay is None:
                                fileStartDay = daystr
                            fileNumDays += 1
                        entry = table.get(daystr, {"date": daystr})
                        entry.update(
                            {
                                "date": daystr,
                                f"solar_production_{ch.replace('_', '')}": item.get(
                                    "value"
                                )
                                or None,
                            }
                        )
                        table.update({daystr: entry})
                if showProgress:
                    self._logger.info(
                        "Received api %s solar_production_%s energy for period",
                        self.apisession.nickname,
                        ch.replace("_", ""),
                    )

    # Always Add solar production which contains percentages
    # get first data period from file or api
    justify_daytotals = bool(dayTotals)
    if fromFile:
        resp = (
            await self.apisession.loadFromFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['energy_solar_production']}_{siteId}.json"
            )
        ).get("data", {})
    else:
        resp = await self.energy_analysis(
            siteId=siteId,
            deviceSn=deviceSn,
            rangeType="week",
            startDay=startDay,
            endDay=startDay
            if justify_daytotals
            else startDay + timedelta(days=numDays - 1),
            devType="solar_production",
        )
    fileNumDays = 0
    fileStartDay = None
    for item in resp.get("power", []):
        daystr = item.get("time", None)
        if daystr:
            if fromFile:
                if fileStartDay is None:
                    fileStartDay = daystr
                fileNumDays += 1
            entry = table.get(daystr, {"date": daystr})
            entry.update(
                {"date": daystr, "solar_production": item.get("value") or None}
            )
            table.update({daystr: entry})
    # Solarbank charge and percentages are only received as total value for given interval. If requested, make daily queries for given interval
    if justify_daytotals and table:
        if fromFile:
            daylist = [
                datetime.strptime(fileStartDay, "%Y-%m-%d") + timedelta(days=x)
                for x in range(fileNumDays)
            ]
        else:
            daylist = [startDay + timedelta(days=x) for x in range(numDays)]
        for day in daylist:
            daystr = day.strftime("%Y-%m-%d")
            entry = table.get(daystr, {"date": daystr})
            # update response only for real requests if not first day which was already queried
            if not fromFile and day != startDay:
                resp = await self.energy_analysis(
                    siteId=siteId,
                    deviceSn=deviceSn,
                    rangeType="week",
                    startDay=day,
                    endDay=day,
                    devType="solar_production",
                )
                # get first item from breakdown list for single day queries
                item = next(iter(resp.get("power") or []), {})
                if daystr == item.get("time"):
                    entry.update(
                        {
                            "date": daystr,
                            "solar_production": item.get("value") or None,
                        }
                    )
            entry.update(
                {
                    "date": daystr,
                    "battery_charge": resp.get("charge_total") or None,
                    "solar_to_grid": resp.get("solar_to_grid_total") or None,
                    "battery_percentage": resp.get("charging_pre") or None,
                    "solar_percentage": resp.get("electricity_pre") or None,
                    "other_percentage": resp.get("others_pre") or None,
                }
            )
            table.update({daystr: entry})
            if showProgress:
                self._logger.info(
                    "Received api %s solar_production energy for %s",
                    self.apisession.nickname,
                    daystr,
                )
    if showProgress:
        self._logger.info(
            "Received api %s solar_production energy for period",
            self.apisession.nickname,
        )
    return table


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
    deviceSn: Device to fetch data # This does not really matter since system level data provided, but field is mandatory
    rangeType: "day" | "week" | "year"
    startTime: optional start Date and time
    endTime: optional end Date and time
    devType: "solar_production" | "solar_production_[pv1-pv4|microinverter]" | "solarbank" | "home_usage" | "grid"
    Example Data for solar_production:
    {'power': [{'time': '2023-10-01', 'value': '3.67'}, {'time': '2023-10-02', 'value': '3.29'}, {'time': '2023-10-03', 'value': '0.55'}],
    'charge_trend': None, 'charge_level': [], 'power_unit': 'wh', 'charge_total': '3.67', 'charge_unit': 'kwh', 'discharge_total': '3.11', 'discharge_unit': 'kwh',
    'charging_pre': '0.49', 'electricity_pre': '0.51', 'others_pre': '0',
    'statistics': [{'type': '1', 'total': '7.51', 'unit': 'kwh'}, {'type': '2', 'total': '7.49', 'unit': 'kg'}, {'type': '3', 'total': '3.00', 'unit': '€'}],
    'battery_discharging_total': '', 'solar_to_grid_total': '', 'grid_to_home_total': '', 'ac_out_put_total': '', 'home_usage_total': '', 'solar_total': '17.3105',
    'trend_unit': '', 'battery_to_home_total': '', 'smart_plug_info': {'smartplug_list': [],'total_power': '0.00'}}

    Responses for solar_production:
    Daily: Solar Energy, Extra Totals: charge, discharge, overall stats (Energy, CO2, Money), 3 x percentage share, solar_to_grid
    Responses for solar_production_*:
    Daily: Solar Energy
    Responses for solarbank:
    Daily: Discharge Energy, Extra Totals: charge, discharge, ac_socket, battery_to_home, grid_to_battery
    Responses for home_usage:
    Daily: Home Usage Energy, Extra Totals: discharge, grid_to_home, battery_to_home, smart_plugs
    Responses for grid:
    Daily: solar_to_grid, grid_to_home, Extra Totals: grid_to_battery
    """
    data = {
        "site_id": siteId,
        "device_sn": deviceSn,
        "type": rangeType if rangeType in ["day", "week", "year"] else "day",
        "start_time": startDay.strftime("%Y-%m-%d")
        if startDay
        else datetime.today().strftime("%Y-%m-%d"),
        "device_type": devType
        if (
            devType in ["solar_production", "solarbank", "home_usage", "grid"]
            or "solar_production_" in devType
        )
        else "solar_production",
        "end_time": endDay.strftime("%Y-%m-%d") if endDay else "",
    }
    resp = await self.apisession.request(
        "post", API_ENDPOINTS["energy_analysis"], json=data
    )
    return resp.get("data") or {}


async def home_load_chart(self, siteId: str, deviceSn: str | None = None) -> dict:
    """Get home load chart data.

    Example data:
    {"data": []}
    """
    data = {"site_id": siteId}
    if deviceSn:
        data.update({"device_sn": deviceSn})
    resp = await self.apisession.request(
        "post", API_ENDPOINTS["home_load_chart"], json=data
    )
    return resp.get("data") or {}
