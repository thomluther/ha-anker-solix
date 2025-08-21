"""Anker Power/Solix Cloud API class energy related methods."""

from datetime import datetime, time, timedelta
from pathlib import Path
from statistics import mean

from .apitypes import (
    API_ENDPOINTS,
    API_FILEPREFIXES,
    SolarbankUsageMode,
    SolixDeviceType,
)


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
    future = datetime.today() + timedelta(days=7)
    # check daily range and limit to 1 year max and avoid future days in more than 1 week
    if startDay > future:
        startDay = future
        numDays = 1
    elif (startDay + timedelta(days=numDays)) > future:
        numDays = (future - startDay).days + 1
    numDays = min(366, max(1, numDays))

    # first get solarbank export
    if SolixDeviceType.SOLARBANK.value in devTypes:
        # get first data period from file or api
        justify_daytotals = bool(
            dayTotals
            and ((self.devices.get(deviceSn) or {}).get("generation") or 0) >= 2
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
        items = resp.get("power") or []
        # for file usage ensure that last item is used if today is included
        start = (
            len(items) - 1
            if fromFile and datetime.now().date() == startDay.date()
            else 0
        )
        for idx, item in enumerate(items[start : start + numDays]):
            if fromFile:
                daystr = (startDay + timedelta(days=idx)).strftime("%Y-%m-%d")
            else:
                daystr = item.get("time")
            if daystr:
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
            for day in [
                startDay + timedelta(days=x)
                for x in range(min(len(items), numDays) if fromFile else numDays)
            ]:
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
        and ((self.devices.get(deviceSn) or {}).get("generation") or 0) >= 2
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
        items = resp.get("power") or []
        # for file usage ensure that last item is used if today is included
        start = (
            len(items) - 1
            if fromFile and datetime.now().date() == startDay.date()
            else 0
        )
        for idx, item in enumerate(items[start : start + numDays]):
            if fromFile:
                daystr = (startDay + timedelta(days=idx)).strftime("%Y-%m-%d")
            else:
                daystr = item.get("time")
            if daystr:
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
            for day in [
                startDay + timedelta(days=x)
                for x in range(min(len(items), numDays) if fromFile else numDays)
            ]:
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
        items = resp.get("power") or []
        # for file usage ensure that last item is used if today is included
        start = (
            len(items) - 1
            if fromFile and datetime.now().date() == startDay.date()
            else 0
        )
        for idx, item in enumerate(items[start : start + numDays]):
            if fromFile:
                daystr = (startDay + timedelta(days=idx)).strftime("%Y-%m-%d")
            else:
                daystr = item.get("time")
            if daystr:
                entry = table.get(daystr, {"date": daystr})
                entry.update(
                    {
                        "date": daystr,
                        # grid export is negative, convert to re-use as solar_to_grid value
                        "solar_to_grid": item.get("value", "").replace("-", "",1) or None,
                    }
                )
                table.update({daystr: entry})
        items = resp.get("charge_trend") or []
        # for file usage ensure that last item is used if today is included
        start = (
            len(items) - 1
            if fromFile and datetime.now().date() == startDay.date()
            else 0
        )
        for idx, item in enumerate(items[start : start + numDays]):
            if fromFile:
                daystr = (startDay + timedelta(days=idx)).strftime("%Y-%m-%d")
            else:
                daystr = item.get("time")
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
                items = resp.get("power") or []
                # for file usage ensure that last item is used if today is included
                start = (
                    len(items) - 1
                    if fromFile and datetime.now().date() == startDay.date()
                    else 0
                )
                for idx, item in enumerate(items[start : start + numDays]):
                    if fromFile:
                        daystr = (startDay + timedelta(days=idx)).strftime("%Y-%m-%d")
                    else:
                        daystr = item.get("time")
                    if daystr:
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
    items = resp.get("power") or []
    # for file usage ensure that last item is used if today is included
    start = (
        len(items) - 1 if fromFile and datetime.now().date() == startDay.date() else 0
    )
    for idx, item in enumerate(items[start : start + numDays]):
        if fromFile:
            daystr = (startDay + timedelta(days=idx)).strftime("%Y-%m-%d")
        else:
            daystr = item.get("time")
        if daystr:
            entry = table.get(daystr, {"date": daystr})
            entry.update(
                {"date": daystr, "solar_production": item.get("value") or None}
            )
            table.update({daystr: entry})
    # Solarbank charge and percentages are only received as total value for given interval. If requested, make daily queries for given interval
    if justify_daytotals and table:
        for day in [
            startDay + timedelta(days=x)
            for x in range(min(len(items), numDays) if fromFile else numDays)
        ]:
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
                    "solar_to_battery": resp.get("solar_to_battery_total") or None,
                    "solar_to_home": resp.get("solar_to_home_total") or None,
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
    'forecast_total': "4.49",'trend_unit': 'w', 'battery_to_home_total': '', 'smart_plug_info': {'smartplug_list': [],'total_power': '0.00'},
    'forecast_trend': [{'time': '02:00','value': '0.00','rods': null},{'time': '03:00','value': '0.00','rods': null}]}
    Responses for solar_production:
    Daily: Solar Energy, Extra Totals: charge, discharge, overall stats (Energy, CO2, Money), 3 x percentage share, solar_to_grid, solar_to_home, solar_to_battery
    Responses for solar_production_*:
    Daily: Solar Energy
    Responses for solarbank:
    Daily: Discharge Energy, Extra Totals: charge, discharge, ac_socket, battery_to_home, grid_to_battery
    Responses for home_usage:
    Daily: Home Usage Energy, Extra Totals: discharge, grid_to_home, battery_to_home, smart_plugs, solar_to_home
    Responses for grid:
    Daily: solar_to_grid, grid_to_home, Extra Totals: grid_to_battery, grid_imported
    """
    data = {
        "site_id": siteId,
        "device_sn": deviceSn,
        "type": rangeType if rangeType in ["day", "week", "year"] else "day",
        "start_time": startDay.strftime("%Y-%m-%d")
        if isinstance(startDay, datetime)
        else datetime.today().strftime("%Y-%m-%d"),
        "device_type": devType
        if (
            devType in ["solar_production", "solarbank", "home_usage", "grid"]
            or "solar_production_" in devType
        )
        else "solar_production",
        "end_time": endDay.strftime("%Y-%m-%d") if isinstance(endDay, datetime) else "",
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


async def refresh_pv_forecast(
    self,
    siteId: str,
    fromFile: bool = False,
) -> None:
    """Refresh the solar forecast data, max once per hour. It will only be done if energy details polled previously."""
    if not (site := self.sites.get(siteId) or {} if isinstance(siteId, str) else {}):
        return
    if not (energy := site.get("energy_details") or {}):
        return
    # Check if smart mode is active, use site info but also schedule info in devices if just enabled before it is reflected in site info
    smartmode = site.get("user_scene_mode") == SolarbankUsageMode.smart.value or [
        d
        for d in self.devices.values()
        if d.get("site_id") == siteId
        and (d.get("schedule") or {}).get("mode_type") == SolarbankUsageMode.smart.value
    ]
    # consider different timezone if recognized in energy data
    now = datetime.now() + timedelta(seconds=site.get("energy_offset_tz") or 0)
    # get existing forecast information
    fcdetails = energy.get("pv_forecast_details") or {}
    # get last poll time or initialize with old date for first poll
    lastpoll = fcdetails.get("poll_time") or (now - timedelta(days=2)).strftime(
        "%Y-%m-%d %H:%M"
    )
    lastpoll = datetime.fromisoformat(lastpoll)
    trend = fcdetails.get("trend") or []
    new_trend = []
    energy_today = energy.get("today") or {}
    # set the default produced solar fields depending on time and previous intraday polls
    produced = fcdetails.get("produced_hourly") or []
    produced_today = ""
    # fetch new forecast max once per hour or if missing, but only if smartmode active
    if smartmode and (
        lastpoll.date() != now.date() or lastpoll.hour != now.hour or not trend
    ):
        self._logger.debug("Getting api %s solar forecast", self.apisession.nickname)
        # new trend query will provide only up to 24 hours in advance, first entry is next full hour with forecast of current hour
        # queries provide also 00:00 at end of day, which is duplicate of first slot next day
        # total forecast is summary of all 24 future hours, not split per queried day
        trend_unit = ""
        for day in range(2 if now.hour > 0 else 1):
            checkdate = now + timedelta(days=day)
            if fromFile:
                # use the same file twice for testing
                data = (
                    await self.apisession.loadFromFile(
                        Path(self.testDir())
                        / f"{API_FILEPREFIXES['energy_solar_production']}_today_{siteId}.json"
                    )
                ).get("data") or {}
            else:
                data = await self.energy_analysis(
                    siteId=siteId,
                    deviceSn="",
                    rangeType="day",
                    devType="solar_production",
                    startDay=checkdate,
                    endDay=checkdate,
                )
            trend_unit = data.get("trend_unit") or ""
            trend_unit = str(trend_unit).lower()
            decimals = 2 if "k" in trend_unit else 0
            if day == 0:
                # refresh todays production data
                produced_today = data.get("solar_total") or ""
                # init hourly data with 0
                produced = [
                    {
                        "timestamp": f"{checkdate.strftime('%Y-%m-%d')} 00:00",
                        "power": f"{0:.{decimals}f}",
                    }
                ]
                # extract and accumulate hourly production values for today
                unit = data.get("power_unit") or ""
                unit = str(unit).lower()
                for h in range(now.hour + 1):
                    # summarize and normalize hourly production to trend unit
                    starttime = time(hour=h, minute=1).strftime("%H:%M")
                    endtime = time(hour=h + 1).strftime("%H:%M") if h < 23 else "24:00"
                    # Add empty power for hours that have no values, future hours will be skipped by loop
                    if values := [
                        float(slot.get("value"))
                        for slot in data.get("power") or []
                        if starttime < (slot.get("time") or "") <= endtime
                        and str(slot.get("value")).replace(".", "", 1).isdigit()
                    ]:
                        hourly = mean(values) * (
                            1000
                            if "k" in unit and "k" not in trend_unit
                            else 0.001
                            if "k" in trend_unit and "k" not in unit
                            else 1
                        )
                    else:
                        hourly = None
                    produced.append(
                        {
                            "timestamp": " ".join(
                                [
                                    (
                                        checkdate
                                        if h < 23
                                        else checkdate + timedelta(days=1)
                                    ).strftime("%Y-%m-%d"),
                                    endtime if h < 23 else "00:00",
                                ]
                            ),
                            "power": "" if hourly is None else f"{hourly:.{decimals}f}",
                        }
                    )
            new_trend += [
                {
                    "timestamp": " ".join(
                        [checkdate.strftime("%Y-%m-%d"), slot.get("time") or ""]
                    ),
                    "power": f"{float(slot.get('value')):.{decimals}f}"
                    if str(slot.get("value")).replace(".", "", 1).isdigit()
                    else "",
                }
                for slot in data.get("forecast_trend") or []
            ]
            fcdetails["forecast_24h"] = data.get("forecast_total") or ""
            # remove last timestamp of 00:00 if smaller than previous to avoid duplicates with next day
            if ((new_trend[-1:] or [{}])[0].get("timestamp") or "") < (
                (new_trend[-2:-1] or [{}])[0].get("timestamp") or ""
            ) or len(new_trend) == 1:
                new_trend = new_trend[:-1]
        # update fields that may change from new fetch
        fcdetails["trend_unit"] = trend_unit.upper()
        fcdetails["local_time"] = data.get("local_time") or ""
        fcdetails["poll_time"] = now.strftime("%Y-%m-%d %H:%M")
        lastpoll = now
        # clear timestamp for this hour trend to force update of extracted values after new fetch
        fcdetails.pop("time_this_hour", None)
    # keep old trend of today and update only the provided trend slots
    old_trend = fcdetails.get("trend") or []
    checkdate = now.replace(hour=0, minute=0).strftime("%Y-%m-%d %H:%M")
    new_start = (new_trend[:1] or [{}])[0].get("timestamp") or ""
    unit = fcdetails.get("trend_unit") or ""
    decimals = 2 if "k" in unit.lower() else 0
    trend = [
        slot
        for slot in old_trend
        if (ot := slot.get("timestamp") or "") >= checkdate
        and (not new_start or ot < new_start)
    ]
    trend += new_trend
    fcdetails["trend"] = trend
    # extract remaining energy for today, use full hours and fraction of current hour from trend
    fullhour = (now + timedelta(hours=2)).replace(minute=0).strftime("%Y-%m-%d %H:%M")
    endtime = (
        (now + timedelta(days=1)).replace(hour=0, minute=0).strftime("%Y-%m-%d %H:%M")
    )
    remain_kwh = sum(
        [
            float(slot.get("power"))
            for slot in trend
            if fullhour <= str(slot.get("timestamp")) <= endtime
            and str(slot.get("power")).replace(".", "", 1).isdigit()
        ]
    ) / (1 if "k" in str(unit).lower() else 1000)
    # assume fraction of actual hour for remaing calculation
    actual_kwh = (
        sum(
            [
                float(slot.get("power"))
                for slot in trend
                if (now + timedelta(hours=1))
                .replace(minute=0)
                .strftime("%Y-%m-%d %H:%M")
                == str(slot.get("timestamp"))
                and str(slot.get("power")).replace(".", "", 1).isdigit()
            ]
        )
    ) / (1 if "k" in str(unit).lower() else 1000)
    fcdetails["remaining_today"] = (
        (f"{remain_kwh + (actual_kwh * (60 - now.minute) / 60):.2f}") if trend else ""
    )
    # set actual production for today depending on previous polls
    if not produced_today:
        # reset actual energy data if last poll was yesterday, otherwise use previous data
        if lastpoll.strftime("%Y-%m-%d") < now.strftime("%Y-%m-%d"):
            produced_today = "0"
        else:
            # initialize production with previous value to calculate difference
            produced_today = fcdetails.get("produced_today") or ""
    # update solar production data from more frequent daily energy data if higher
    if (
        produced_today.replace(".", "", 1).isdigit()
        and energy_today.get("date") <= now.strftime("%Y-%m-%d")
        and str(solar_prod := energy_today.get("solar_production") or "")
        .replace(".", "", 1)
        .isdigit()
        and float(solar_prod) >= float(produced_today)
    ):
        thishour = (
            (now + timedelta(hours=1)).replace(minute=0).strftime("%Y-%m-%d %H:%M")
        )
        # get slot of actual hour and add missing energy or new slot while hour within existing trend range
        if slot := (
            [
                s
                for s in produced
                if thishour == str(s.get("timestamp"))
                and str(s.get("power")).replace(".", "", 1).isdigit()
            ][-1:]
            or [{}]
        )[0]:
            # do inplace update with normalized unit conversion
            value = (
                (float(solar_prod) - float(produced_today))
                if energy_today.get("date") == now.strftime("%Y-%m-%d")
                else float(produced_today)
            )
            slot["power"] = (
                f"{float(slot['power']) + value * (1 if 'k' in unit.lower() else 1000):.{decimals}f}"
            )
        # add new production slot while within trend range if smart mode disabled temporarily without new hourly queries
        elif produced and (
            (produced[-1:] or [{}])[0].get("timestamp") or ""
        ) < thishour <= ((trend[-1:] or [{}])[0].get("timestamp") or ""):
            produced.append(
                {
                    "timestamp": thishour,
                    "power": (
                        f"{(float(solar_prod) - float(produced_today)) * (1 if 'k' in unit.lower() else 1000):.{decimals}f}"
                    ),
                }
            )
            # sanitize produced hourly data for today only
            produced = [
                slot
                for slot in produced
                if slot.get("timestamp")
                >= now.replace(hour=0, minute=0).strftime("%Y-%m-%d %H:%M")
            ]
        # update last production value for next refresh
        produced_today = solar_prod
    fcdetails["produced_hourly"] = produced
    fcdetails["produced_today"] = produced_today
    # set initial production prior first trend value for better completion of total forecast for today
    # otherwise forecast for today is only calculated from trend values
    fcdetails["produced_initially"] = (
        "0"
        if "00:00" in (ts := (trend[:1] or [{}])[0].get("timestamp") or "")
        else f"{
            sum(
                [
                    float(slot.get('power'))
                    for slot in produced
                    if str(slot.get('timestamp')) < ts
                    and str(slot.get('power')).replace('.', '', 1).isdigit()
                ]
            )
            / (1 if 'k' in unit.lower() else 1000):.2f}"
    )
    # calculate total forecast of today
    daily_kwh = sum(
        [
            float(slot.get("power"))
            for slot in trend
            if now.replace(hour=0, minute=0).strftime("%Y-%m-%d %H:%M")
            < str(slot.get("timestamp"))
            <= (now + timedelta(days=1))
            .replace(hour=0, minute=0)
            .strftime("%Y-%m-%d %H:%M")
            and str(slot.get("power")).replace(".", "", 1).isdigit()
        ]
    ) / (1 if "k" in unit.lower() else 1000)
    fcdetails["forecast_today"] = (
        (f"{daily_kwh + float(fcdetails.get('produced_initially')):.2f}")
        if trend
        else ""
    )
    # calculate available forecast of tomorrow (incomplete most of the time)
    daily_kwh = sum(
        [
            float(slot.get("power"))
            for slot in trend
            if (now + timedelta(days=1))
            .replace(hour=0, minute=0)
            .strftime("%Y-%m-%d %H:%M")
            < str(slot.get("timestamp"))
            <= (now + timedelta(days=2))
            .replace(hour=0, minute=0)
            .strftime("%Y-%m-%d %H:%M")
            and str(slot.get("power")).replace(".", "", 1).isdigit()
        ]
    ) / (1 if "k" in unit.lower() else 1000)
    fcdetails["forecast_tomorrow"] = f"{daily_kwh:.2f}" if trend else ""
    # update data in site energy details
    energy["pv_forecast_details"] = fcdetails
    site["energy_details"] = energy
    # extract the actual forecast for site
    self.extractSolarForecast(siteId=siteId)


async def device_pv_energy_daily(
    self,
    deviceSn: str,
    startDay: datetime = datetime.today(),
    numDays: int = 1,
    fromFile: bool = False,
    showProgress: bool = False,
) -> dict:
    """Fetch daily Energy data for given interval and provide it in a table format dictionary.

    Example data:
    {"2023-09-29": {"date": "2023-09-29", "solar_production": "1.21"},
    "2023-09-30": {"date": "2023-09-30", "solar_production": "3.07"}}
    """
    table = {}
    future = datetime.today() + timedelta(days=7)
    # check daily range and limit to 1 year max and avoid future days in more than 1 week
    if startDay > future:
        startDay = future
        numDays = 1
    elif (startDay + timedelta(days=numDays)) > future:
        numDays = (future - startDay).days + 1
    numDays = min(366, max(1, numDays))

    # get first data period from file or api
    if fromFile:
        resp = (
            await self.apisession.loadFromFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['get_device_pv_statistics']}_{deviceSn}.json"
            )
        ).get("data", {})
    else:
        resp = await self.get_device_pv_statistics(
            deviceSn=deviceSn,
            rangeType="week",
            startDay=startDay,
            endDay=startDay + timedelta(days=numDays - 1),
        )
    for idx, item in enumerate(resp.get("energy", [])):
        daystr = (startDay + timedelta(days=idx)).strftime("%Y-%m-%d")
        entry = table.get(daystr, {"date": daystr})
        entry.update(
            {
                "date": daystr,
                "solar_production": None
                if item.get("energy") is None
                else str(item.get("energy")),
            }
        )
        table.update({daystr: entry})
    if showProgress:
        self._logger.info(
            "Received api %s device PV energy for period",
            self.apisession.nickname,
        )
    return table


async def get_device_pv_statistics(
    self,
    deviceSn: str,
    rangeType: str | None = None,
    startDay: datetime | None = None,
    endDay: datetime | None = None,
    version: str = "1",
) -> dict:
    """Get pv statistics data for an inverter device on a daily, weekly, monthly or yearly basis.

    - type is either day, week, month or year
    - start is the day (YYYY-MM-DD), month (YYYY-MM) or year (YYYY) in question
    - end is the last day of a week (YYYY-MM-DD), if the type is week
    - version seems to be always '1'

    Example data (type year):
    {'curve': [], 'energy':[
        {'money': 0, 'energy': 0, 'index': 1}, {'money': 0, 'energy': 0, 'index': 2},
        {'money': 0, 'energy': 15.35, 'index': 3}, {'money': 0, 'energy': 50.81, 'index': 4},
        {'money': 0, 'energy': 0, 'index': 5}, {'money': 0, 'energy': 0, 'index': 6},
        {'money': 0, 'energy': 0, 'index': 7}, {'money': 0, 'energy': 0, 'index': 8},
        {'money': 0, 'energy': 0, 'index': 9}, {'money': 0, 'energy': 0, 'index': 10},
        {'money': 0, 'energy': 0, 'index': 11}, {'money': 0, 'energy': 0, 'index': 12}],
    'energyUnit': 'kWh', 'solarGeneraion': 66.15, 'money': 0, 'moneyUnit': '', 'loadPercent': '',
    'ppsPercent': '', 'generationTime': 0, 'maxPower': 0}
    """

    rangeType = rangeType if rangeType in ["week", "month", "year"] else "day"
    startDay = startDay if isinstance(startDay, datetime) else datetime.today()
    endDay = endDay if isinstance(endDay, datetime) else startDay
    data = {
        "sn": deviceSn,
        "type": rangeType,
        "start": startDay.strftime(
            "%Y-%m"
            if rangeType in ["month"]
            else "%Y"
            if rangeType in ["year"]
            else "%Y-%m-%d"
        ),
        "end": ""
        if not endDay
        else endDay.strftime(
            "%Y-%m"
            if rangeType in ["month"]
            else "%Y"
            if rangeType in ["year"]
            else "%Y-%m-%d"
        ),
        "version": version,
    }
    resp = await self.apisession.request(
        "post", API_ENDPOINTS["get_device_pv_statistics"], json=data
    )
    return resp.get("data") or {}


async def get_device_charge_order_stats(
    self,
    deviceSn: str,
    rangeType: str | None = None,
    startDay: datetime | None = None,
    endDay: datetime | None = None,
) -> dict:
    """Get EV charger order statistics on a weekly, monthly, yearly or total basis.

    - rangeType is either week, month, year or all
    - startDay is the day (YYYY-MM-DD) in question
    - endDay is to limit period, default is requested range type

    Example data:
    {"total_stats": {"charge_unit": "","charge_total": 0,"charge_time": 0,"charge_count": 0,"cost": 0,"cost_unit": "\u20ac","cost_saving": 0,
    "co2_saving": 0,"co2_saveing_unit": "","mile_age": 0},"date_list": []}
    """
    # TODO: Update example once range break down is available, will field name typo still be corrected?
    rangeType = rangeType if rangeType in ["week", "month", "year"] else "all"
    startDay = startDay if isinstance(startDay, datetime) else datetime.now()
    endDay = endDay if isinstance(endDay, datetime) else startDay
    data = {
        "device_sn": deviceSn,
        "date_type": rangeType,
        "start_date": ""
        if not startDay or rangeType in ["all"]
        else startDay.strftime("%Y-%m-%d"),
        "end_date": ""
        if not endDay or rangeType in ["all"]
        else endDay.strftime("%Y-%m-%d"),
    }
    resp = await self.apisession.request(
        "post", API_ENDPOINTS["get_device_charge_order_stats"], json=data
    )
    return resp.get("data") or {}
