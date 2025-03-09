"""Class for interacting with the Anker Power / Solix API HES related charging_service endpoints.

Required Python modules:
pip install cryptography
pip install aiohttp
pip install aiofiles
"""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from pathlib import Path

from aiohttp import ClientSession

from .apibase import AnkerSolixBaseApi
from .apitypes import (
    API_FILEPREFIXES,
    API_HES_SVC_ENDPOINTS,
    ApiCategories,
    SolixDeviceCategory,
    SolixDeviceStatus,
    SolixDeviceType,
    SolixSiteType,
)
from .helpers import convertToKwh
from .session import AnkerSolixClientSession

_LOGGER: logging.Logger = logging.getLogger(__name__)


class AnkerSolixHesApi(AnkerSolixBaseApi):
    """Define the API class to handle Anker server communication via AnkerSolixClientSession for HES related queries.

    It will also build internal cache dictionaries with information collected through the Api.
    """

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

    def _update_site(
        self,
        siteId: str,
        details: dict,
    ) -> None:
        """Update the internal sites dictionary with data provided for the nested site details dictionary.

        This method is used to consolidate site details from various less frequent requests that are not covered with the update_sites poller method.
        """
        # lookup old site details if any
        if siteId in self.sites:
            site_details = (self.sites[siteId]).get("site_details") or {}
            site_details.update(details)
        else:
            site_details = details
            self.sites[siteId] = {}
        self.sites[siteId]["site_details"] = site_details

    def _update_dev(
        self,
        devData: dict,
        devType: str | None = None,
        siteId: str | None = None,
        isAdmin: bool | None = None,
    ) -> str | None:
        """Update the internal device details dictionary with the given data. The device_sn key must be set in the data dict for the update to be applied.

        This method should be implemented to consolidate various device related key values from various requests under a common set of device keys.
        The device SN should be returned if found in devData and an update was done
        """

        if sn := devData.get("device_sn"):
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
            for key, value in devData.items():
                try:
                    # Implement device update code with key filtering, conversion, consolidation, calculation or dependency updates
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
                    elif key in ["alias_name"] and value:
                        device.update({"alias": str(value)})
                    elif key in ["status"]:
                        device.update({"status": str(value)})
                        # decode the status into a description
                        description = SolixDeviceStatus.unknown.name
                        for status in SolixDeviceStatus:
                            if str(value) == status.value:
                                description = status.name
                                break
                        device.update({"status_desc": description})
                    elif key in [
                        # Examples for boolean key values
                        "auto_upgrade",
                        "is_subdevice",
                    ]:
                        device.update({key: bool(value)})
                    elif key in [
                        # key with string values
                        "wireless_type",
                    ] or (
                        key
                        in [
                            # Example for key with string values that should only be updated if value returned
                            "wifi_name",
                            "main_sn",
                        ]
                        and value
                    ):
                        device.update({key: str(value)})

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

    async def update_sites(
        self,
        siteId: str | None = None,
        fromFile: bool = False,
        exclude: set | None = None,
        siteData: dict | None = None,
    ) -> dict:
        """Create/Update api sites cache structure.

        Implement this method to get the latest info for all hes sites or only the provided siteId and update class cache dictionaries.
        """
        # define excluded categories to skip for queries
        if not exclude or not isinstance(exclude, set):
            exclude = set()
        if not siteData or not isinstance(siteData, dict):
            siteData = {}
        if siteId and (
            site_info := siteData.pop("site_info", {})
            or (self.sites.get(siteId) or {}).get("site_info")
            or {}
        ):
            # update only the provided site ID when siteInfo available/provided to avoid another site list query
            self._logger.debug(
                "Updating api %s HES sites data for site ID %s",
                self.apisession.nickname,
                siteId,
            )
            new_sites = self.sites
            # prepare the site list dictionary for the update loop by copying the requested site from the cache
            sites: dict = {"site_list": [site_info]}
        else:
            # run normal refresh for given or all sites
            self._logger.debug(
                "Updating api %s HES Sites data%s",
                self.apisession.nickname,
                " for site ID " + siteId if siteId else "",
            )
            new_sites = {}
            self._logger.debug(
                "Getting api %s site list",
                self.apisession.nickname,
            )
            sites: dict = {
                "site_list": [
                    s
                    for s in (await self.get_site_list(fromFile=fromFile)).get(
                        "site_list"
                    )
                    or []
                    if not siteId or s.get("site_id") == siteId
                ]
            }
            # rebuild device list found in any site
            if not siteId:
                self._site_devices = set()
        for site in sites.get("site_list", []):
            if myid := site.get("site_id"):
                # Update site info
                mysite: dict = self.sites.get(myid, {})
                site_info: dict = mysite.get("site_info", {})
                site_info.update(site)
                if hasattr(
                    SolixSiteType,
                    item := "t_" + str(site_info.get("power_site_type") or ""),
                ):
                    mysite["site_type"] = getattr(SolixSiteType, item)
                # check if hes site type
                if mysite.get("site_type") == SolixDeviceType.HES.value:
                    mysite.update(
                        {
                            "site_id": myid,
                            "type": SolixDeviceType.SYSTEM.value,
                            "site_info": site_info,
                        }
                    )
                    # add boolean key to indicate whether user is site admin (ms_type 1 or not known) and can query device details
                    admin = site_info.get("ms_type", 0) in [0, 1]
                    mysite["site_admin"] = admin
                    # query site device info if not provided in site Data
                    if not (hes_list := siteData.get("hes_list")):
                        self._logger.debug(
                            "Getting api %s device info for HES site",
                            self.apisession.nickname,
                        )
                        hes_list = (
                            await self.get_dev_info(siteId=myid, fromFile=fromFile)
                        ).get("results") or []

                    # add extra site data to my site
                    mysite["hes_list"] = hes_list
                    for hes in hes_list or []:
                        main_sn = hes.get("sn") or ""
                        if sn := self._update_dev(
                            {
                                "device_sn": hes.get("sn") or "",
                                "main_sn": main_sn,
                                "device_pn": hes.get("pn") or "",
                            },
                            devType=SolixDeviceType.HES.value,
                            siteId=myid,
                            isAdmin=admin,
                        ):
                            self._site_devices.add(sn)
                        for subdev in [
                            dev
                            for dev in (hes.get("subDevInfo") or [])
                            if dev.get("sn") != main_sn
                        ]:
                            if sn := self._update_dev(
                                {
                                    "device_sn": subdev.get("sn") or "",
                                    "main_sn": main_sn,
                                    "is_subdevice": True,
                                    "device_pn": subdev.get("pn") or "",
                                },
                                devType=SolixDeviceType.HES.value,
                                siteId=myid,
                                isAdmin=admin,
                            ):
                                self._site_devices.add(sn)

                    # Query 5 min avg power and soc from energy stats as work around since no current power values found for hes in cloud server yet
                    if not (
                        {
                            SolixDeviceType.HES.value,
                            ApiCategories.hes_energy,
                        }
                        & exclude
                    ):
                        await self.get_avg_power_from_energy(
                            siteId=myid, fromFile=fromFile
                        )
                    new_sites.update({myid: mysite})

        # Write back the updated sites
        self.sites = new_sites
        return self.sites

    async def update_site_details(
        self, fromFile: bool = False, exclude: set | None = None
    ) -> dict:
        """Get the latest updates for additional account or site related details updated less frequently.

        Implement this method for site related queries that should be used less frequently.
        Most of theses requests return data only when user has admin rights for sites owning the devices.
        To limit API requests, this update site details method should be called less frequently than update site method,
        and it updates just the nested site_details dictionary in the sites dictionary as well as the account dictionary
        """
        # define excluded categories to skip for queries
        if not exclude or not isinstance(exclude, set):
            exclude = set()
        self._logger.debug(
            "Updating api %s HES Sites details",
            self.apisession.nickname,
        )
        for site_id, site in self.sites.items():
            # Fetch overall statistic totals for hes site that should not be excluded since merged to overall site cache
            self._logger.debug(
                "Getting api %s system running totals information",
                self.apisession.nickname,
            )
            await self.get_system_running_info(siteId=site_id, fromFile=fromFile)
            # Fetch details that work for all account types
            if {SolixDeviceType.HES.value} - exclude:
                # Fetch details that only work for site admins
                if site.get("site_admin", False):
                    # Add extra hes site polling that may make sense
                    pass
        return self.sites

    async def update_device_energy(
        self,
        fromFile: bool = False,
        exclude: set | None = None,
    ) -> dict:
        """Get the site energy statistics for given site.

        Implement this method for the required energy query methods to obtain energy data for today and yesterday.
        It was found that energy data is tracked only per site, but not individual devices even if a device SN parameter may be mandatory in the Api request.
        """
        # check exclusion list, default to all energy data
        if not exclude or not isinstance(exclude, set):
            exclude = set()
        for site_id, site in self.sites.items():
            query_types: set = set()
            # build device types set for daily energy query, depending on device types found for site
            # HES sites have no variations for energy metrics, either all or none can be queried
            if not (
                {
                    SolixDeviceType.HES.value,
                    ApiCategories.hes_energy,
                }
                & exclude
            ):
                query_types: set = {SolixDeviceType.HES.value}
            if query_types:
                self._logger.debug(
                    "Getting api %s HES energy details for site",
                    self.apisession.nickname,
                )
                # obtain previous energy details to check if yesterday must be queried as well
                energy = site.get("energy_details") or {}
                # delay actual time to allow the cloud server to finish update of previous day, since previous day will be queried only once
                # Cloud server energy stat updates may be delayed by 3 minutes for HES
                # min Offset in seconds to last valid record, reduce by 5 minutes to ensure last record is made
                energy_offset = (site.get("energy_offset_seconds") or 0) - 300
                time: datetime = datetime.now() + timedelta(seconds=energy_offset)
                today = time.strftime("%Y-%m-%d")
                yesterday = (time - timedelta(days=1)).strftime("%Y-%m-%d")
                # Fetch energy from today or both days
                data: dict = {}
                if yesterday != (energy.get("last_period") or {}).get("date"):
                    data.update(
                        await self.energy_daily(
                            siteId=site_id,
                            startDay=datetime.fromisoformat(yesterday),
                            numDays=2,
                            dayTotals=True,
                            devTypes=query_types,
                            fromFile=fromFile,
                        )
                    )
                else:
                    data.update(
                        await self.energy_daily(
                            siteId=site_id,
                            startDay=datetime.fromisoformat(today),
                            numDays=1,
                            dayTotals=True,
                            devTypes=query_types,
                            fromFile=fromFile,
                        )
                    )
                if fromFile:
                    # get last date entries from file and replace date with yesterday and today for testing
                    days = len(data)
                    if len(data) > 1:
                        entry: dict = list(data.values())[days - 2]
                        entry.update({"date": yesterday})
                        energy["last_period"] = entry
                    if len(data) > 0:
                        entry: dict = list(data.values())[days - 1]
                        entry.update({"date": today})
                        energy["today"] = entry
                else:
                    energy["today"] = data.get(today) or {}
                    if data.get(yesterday):
                        energy["last_period"] = data.get(yesterday) or {}
                # save energy stats with sites dictionary
                site["energy_details"] = energy
                self.sites[site_id] = site
        return self.sites

    async def update_device_details(
        self, fromFile: bool = False, exclude: set | None = None
    ) -> dict:
        """Get the latest updates for additional device info updated less frequently.

        Implement this method for the required query methods to fetch device related data and update the device cache accordingly.
        To limit API requests, this update device details method should be called less frequently than update site method,
        which will also update most device details as found in the site data response.
        """
        # define excluded device types or categories to skip for queries
        if not exclude or not isinstance(exclude, set):
            exclude = set()
        self._logger.debug(
            "Updating api %s HES Device details",
            self.apisession.nickname,
        )
        #
        # Implement required queries according to exclusion set
        #

        return self.devices

    async def get_system_running_info(
        self, siteId: str, fromFile: bool = False
    ) -> dict:
        """Get the site running information with tracked total stats.

        Example data:
        {"mainSn": "SFW0EKTKW7IA043U","pcsSns": ["ATHRE00E22200039"],"mainDeviceModel": "A5103","connected": true,"totalSystemSavings": 134.7,"systemSavingsPriceUnit": "\u20ac",
        "saveCarbonFootprint": 304,"saveCarbonUnit": "kg","saveCarbonC": 0.997,"totalSystemPowerGeneration": 304.42,"systemPowerGenerationUnit": "KWh","numberOfParallelDevice": 1,
        "batCount": 3,"rePostTime": 5,"supportDiesel": false,"net": 2,"isAddHeatPump": false,"realNet": 1,"systemCode": "DE202411140001"}
        """
        data = {"siteId": siteId}
        if fromFile:
            resp = await self.apisession.loadFromFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['hes_get_system_running_info']}_{siteId}.json"
            )
        else:
            resp = await self.apisession.request(
                "post", API_HES_SVC_ENDPOINTS["get_system_running_info"], json=data
            )
        data = resp.get("data") or {}
        # update sites dict with relevant info and with required structure
        stats = []
        if data and (mysite := self.sites.get(siteId)):
            # create statistics dictionary as used in scene_info for other sites to allow direct replacement
            # Total Energy
            stats.append(
                {
                    "type": "1",
                    "total": str(data.get("totalSystemPowerGeneration") or ""),
                    "unit": str(data.get("systemPowerGenerationUnit") or "").lower(),
                }
            )
            # Total carbon
            stats.append(
                {
                    "type": "2",
                    "total": str(data.get("saveCarbonFootprint") or ""),
                    "unit": str(data.get("saveCarbonUnit") or "").lower(),
                }
            )
            # Total savings
            stats.append(
                {
                    "type": "3",
                    "total": str(data.get("totalSystemSavings") or ""),
                    "unit": str(data.get("systemSavingsPriceUnit") or ""),
                }
            )
            # Add stats and other system infos to sites cache
            mysite.update(
                {
                    "statistics": stats,
                    "hes_info": {
                        "hes_list": [
                            {
                                "device_sn": data.get("mainSn") or "",
                                "main_sn": True,
                                "device_pn": data.get("mainDeviceModel") or "",
                            }
                        ]
                        + [
                            {"device_sn": sn, "main_sn": False}
                            for sn in data.get("pcsSns") or []
                        ],
                        "total_charging_power": "0",
                    },
                    "connected": data.get("connected"),
                    "numberOfParallelDevice": data.get("numberOfParallelDevice"),
                    "batCount": data.get("batCount"),
                    "rePostTime": data.get("rePostTime"),
                    "net": data.get("net"),
                    "realNet": data.get("realNet"),
                    "supportDiesel": data.get("supportDiesel"),
                    "isAddHeatPump": data.get("isAddHeatPump"),
                    "systemCode": data.get("systemCode"),
                }
            )
            self.sites[siteId] = mysite
        return data

    async def get_avg_power_from_energy(
        self, siteId: str, fromFile: bool = False
    ) -> dict:
        """Get the last 5 min average power from energy statistics.

        Example data:
        """
        # get existing data first from site details to check if requery must be done
        avg_data = (self.sites.get(siteId) or {}).get("average_power") or {}
        # verify last runtime and avoid re-query in less than 5 minutes since no new values available in energy stats
        if not (timestring := avg_data.get("last_check")) or (
            datetime.now() - datetime.strptime(timestring, "%Y-%m-%d %H:%M:%S")
        ) >= timedelta(minutes=5):
            self._logger.debug(
                "Updating api %s power average values from energy statistics of HES site ID %s",
                self.apisession.nickname,
                siteId,
            )
            offset = timedelta(seconds=avg_data.get("offset_seconds") or 0)
            validtime = datetime.now() + offset
            validdata = {}
            for source in ["hes", "solar", "home", "grid"]:
                # check for initial or updated min offset, using SOC value in hes data because that should never be 0 for a valid timestamp
                if source == "hes":
                    future = ""
                    for diff in (
                        [1, 0, -1]
                        if offset.total_seconds() == 0 and not fromFile
                        else [0]
                    ):
                        # check +/- 1 day to find last valid SOC timestamp in real data before invalid SOC entry of 0 %
                        checkdate = validtime + timedelta(days=diff)
                        self._logger.debug(
                            "Checking api %s %s data of %s",
                            self.apisession.nickname,
                            source,
                            checkdate.strftime("%Y-%m-%d"),
                        )
                        if fromFile:
                            data = (
                                await self.apisession.loadFromFile(
                                    Path(self.testDir())
                                    / f"{API_FILEPREFIXES[f'hes_energy_{source}_today']}_{siteId}.json"
                                )
                            ).get("data") or {}
                        else:
                            data = await self.energy_statistics(
                                siteId=siteId,
                                rangeType="day",
                                sourceType=source,
                                startDay=checkdate,
                                endDay=checkdate,
                            )
                        # generate list of SOC timestamps different from 0 and pick last one
                        if soclist := [
                            item
                            for item in (data.get("chargeLevel") or [])
                            if (item.get("value") or "0") != "0"
                        ]:
                            if soclist[-1].get("time"):
                                last = datetime.strptime(
                                    checkdate.strftime("%Y-%m-%d")
                                    + soclist[-1].get("time"),
                                    "%Y-%m-%d%H:%M",
                                )
                                future: datetime = last + timedelta(minutes=5)
                                validdata = data
                                break
                    # get min offset to first invalid timestamp to find best check time (smallest delay after new statue value from cloud)
                    if future:
                        offset = min(
                            # use default offset 2 days for first calculation
                            timedelta(days=2)
                            if offset.total_seconds() == 0
                            # reset offset if significantly higher, when previous last valid entry was not really the last one due to 0 value SOC entries
                            or future - datetime.now() > offset + timedelta(minutes=6)
                            else offset,
                            # set offset few seconds before future invalid time if smaller than previous offset
                            future - datetime.now() - timedelta(seconds=2),
                        )
                        validtime = datetime.now() + offset
                        # reuse last valid data from timestamp check to get values
                        data = validdata
                        self._logger.debug(
                            "Found valid api %s %s entries until %s",
                            self.apisession.nickname,
                            source,
                            validtime.strftime("%Y-%m-%d %H:%M:%S"),
                        )
                elif fromFile:
                    self._logger.debug(
                        "Reading api %s %s data of %s",
                        self.apisession.nickname,
                        source,
                        validtime.strftime("%Y-%m-%d"),
                    )
                    data = (
                        await self.apisession.loadFromFile(
                            Path(self.testDir())
                            / f"{API_FILEPREFIXES[f'hes_energy_{source}_today']}_{siteId}.json"
                        )
                    ).get("data") or {}
                else:
                    self._logger.debug(
                        "Querying api %s %s data of %s",
                        self.apisession.nickname,
                        source,
                        validtime.strftime("%Y-%m-%d"),
                    )
                    data = await self.energy_statistics(
                        siteId=siteId,
                        rangeType="day",
                        sourceType=source,
                        startDay=validtime,
                    )
                # set last check time more into past to ensure each run verifies until offset no longer increases
                if (
                    future
                    and not fromFile
                    and (
                        future - datetime.now() - timedelta(seconds=2) < offset
                        or offset.total_seconds == 0
                    )
                ):
                    avg_data["last_check"] = (
                        datetime.now() - timedelta(minutes=5)
                    ).strftime("%Y-%m-%d %H:%M:%S")
                else:
                    avg_data["last_check"] = datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                avg_data["valid_time"] = validtime.strftime("%Y-%m-%d %H:%M:%S")
                avg_data["offset_seconds"] = round(offset.total_seconds())
                avg_data["power_unit"] = data.get("powerUnit")
                # extract power values only if offset to last valid SOC entry was found
                if offset.total_seconds() != 0 and (
                    powerlist := [
                        item
                        for item in (data.get("power") or [])
                        if (item.get("time") or "24:00") <= validtime.strftime("%H:%M")
                    ]
                ):
                    if source == "hes":
                        for idx, power in enumerate(
                            powerlist[-1].get("powerInfos") or [], start=1
                        ):
                            if idx == 1:
                                avg_data["charge_power_avg"] = str(
                                    power.get("value") or ""
                                ).replace("-", "")
                            else:
                                avg_data["discharge_power_avg"] = str(
                                    power.get("value") or ""
                                ).replace("-", "")
                        if soclist := [
                            item
                            for item in (data.get("chargeLevel") or [])
                            if (item.get("time") or "24:00")
                            <= validtime.strftime("%H:%M")
                        ]:
                            avg_data["state_of_charge"] = soclist[-1].get("value") or ""
                    elif source == "solar":
                        avg_data["solar_power_avg"] = (
                            next(
                                iter(powerlist[-1].get("powerInfos") or []),
                                {},
                            ).get("value")
                            or ""
                        )
                    elif source == "home":
                        avg_data["home_usage_avg"] = (
                            next(
                                iter(powerlist[-1].get("powerInfos") or []),
                                {},
                            ).get("value")
                            or ""
                        )
                    elif source == "grid":
                        avg_data["grid_import_avg"] = (
                            next(
                                iter(powerlist[-1].get("powerInfos") or []),
                                {},
                            ).get("value")
                            or ""
                        )
            # update device dict with relevant info and with required structure
            if avg_data:
                # Add average power to site details as work around if no other hes usage data will be found in cloud for main devices
                # Add energy offset info to site cache
                site = self.sites.get(siteId) or {}
                site.update(
                    {
                        "average_power": avg_data,
                        "energy_offset_seconds": avg_data.get("offset_seconds"),
                        "energy_offset_check": avg_data.get("last_check"),
                    }
                )
                self.sites[siteId] = site
        return avg_data

    async def energy_statistics(
        self,
        siteId: str,
        rangeType: str | None = None,
        startDay: datetime | None = None,
        endDay: datetime | None = None,
        sourceType: str | None = None,
    ) -> dict:
        """Fetch Energy data for given device and optional time frame.

        siteId: site ID of device
        deviceSn: Device to fetch data # This does not really matter since system level data provided, but field is mandatory
        rangeType: "day" | "week" | "year"
        startTime: optional start Date and time
        endTime: optional end Date and time
        devType: "solar" | "hes" | "grid" | "home"
        Example Data for solar_production:
        {"power": [{"time": "2025-02-01","value": "0"},{"time": "2025-02-02","value": "0"}],
        "charge_trend": null,"charge_level": [],"power_unit": "wh","charge_total": "0.00","charge_unit": "kwh","discharge_total": "0.00","discharge_unit": "kwh",
        "charging_pre": "0","electricity_pre": "0","others_pre": "0","statistics": [
            {"type": "1","total": "0.00","unit": "kwh"},
            {"type": "2","total": "0.00","unit": "kg"},
            {"type": "3","total": "0.00","unit": "\u20ac"}],
        "battery_discharging_total":"","solar_to_grid_total":"","grid_to_home_total":"","ac_out_put_total":"","home_usage_total":"","solar_total":"0.0000","trend_unit":"",
        "battery_to_home_total":"","smart_plug_info":null,"local_time":"","grid_to_battery_total":"","grid_imported_total":"","solar_to_battery_total":"","solar_to_home_total":""}

        Responses for solar:
        Daily: Solar Energy, Extra Totals: PV charged, PV usage, PV to grid, 3 x percentage share solar usage
        Responses for hes:
        Daily: Discharge Energy, Extra Totals: battery_to_home, battery_to_grid
        Responses for home_usage:
        Daily: Home Usage Energy, Extra Totals: grid_to_home, battery_to_home, solar_to_home, 3 x percentage share home usage source
        Responses for grid:
        Daily: Grid import, Extra Totals: solar_to_grid, battery_to_grid, grid_to_home, grid_to_battery, 2 x percentage share how import used and 2 x export share
        """
        data = {
            "siteId": siteId,
            "sourceType": sourceType
            if sourceType in ["solar", "hes", "home", "grid"]
            else "solar",
            "dateType": rangeType if rangeType in ["day", "week", "year"] else "day",
            "start": startDay.strftime("%Y-%m-%d")
            if startDay
            else datetime.today().strftime("%Y-%m-%d"),
            "end": endDay.strftime("%Y-%m-%d")
            if endDay
            else datetime.today().strftime("%Y-%m-%d"),
        }
        resp = await self.apisession.request(
            "post", API_HES_SVC_ENDPOINTS["energy_statistics"], json=data
        )
        return resp.get("data") or {}

    async def energy_daily(  # noqa: C901
        self,
        siteId: str,
        startDay: datetime = datetime.today(),
        numDays: int = 1,
        dayTotals: bool = False,
        devTypes: set | None = None,
        fromFile: bool = False,
        showProgress: bool = False,
    ) -> dict:
        """Fetch daily Energy data for given interval and provide it in a table format dictionary.

        Solar production data is always queried. Additional energy data will be queried for devtypes 'hes'. The number of
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

        # first get HES export
        if SolixDeviceType.HES.value in devTypes:
            # get first data period from file or api
            if fromFile:
                resp = (
                    await self.apisession.loadFromFile(
                        Path(self.testDir())
                        / f"{API_FILEPREFIXES['hes_energy_hes']}_{siteId}.json"
                    )
                ).get("data", {})
            else:
                resp = await self.energy_statistics(
                    siteId=siteId,
                    rangeType="week",
                    startDay=startDay,
                    # query only 1 day if daytotals requested
                    endDay=startDay
                    if dayTotals
                    else startDay + timedelta(days=numDays - 1),
                    sourceType="hes",
                )
            fileNumDays = 0
            fileStartDay = None
            unit = resp.get("energyUnit") or ""
            for item in resp.get("energy") or []:
                # No daystring in response, count the index for proper date
                if daystr := (startDay + timedelta(days=fileNumDays)).strftime(
                    "%Y-%m-%d"
                ):
                    if fromFile and fileStartDay is None:
                        fileStartDay = daystr
                    fileNumDays += 1
                    entry = table.get(daystr, {"date": daystr})
                    entry.update(
                        {
                            "battery_discharge": convertToKwh(
                                val=item.get("value") or None, unit=unit
                            ),
                        }
                    )
                    table.update({daystr: entry})
            # TODO: HES has currently no total discharge energy or other extra totals for interval. Check if discharge is available in PPS data to replace HES with PPS
            # If requested, make daily queries for given interval
            # if dayTotals and table:
            #     if fromFile:
            #         daylist = [
            #             datetime.strptime(fileStartDay, "%Y-%m-%d") + timedelta(days=x)
            #             for x in range(fileNumDays)
            #         ]
            #     else:
            #         daylist = [startDay + timedelta(days=x) for x in range(numDays)]
            #     for day in daylist:
            #         daystr = day.strftime("%Y-%m-%d")
            #         entry = table.get(daystr, {"date": daystr})
            #         # update response only for real requests if not first day which was already queried
            #         if not fromFile and day != startDay:
            #             resp = await self.energy_statistics(
            #                 siteId=siteId,
            #                 rangeType="week",
            #                 startDay=day,
            #                 endDay=day,
            #                 sourceType="hes",
            #             )
            #             # get first item from breakdown list for single day queries
            #             item = next(iter(resp.get("energy") or []), {})
            #             unit = resp.get("energyUnit") or ""
            #             entry.update(
            #                 {
            #                     "battery_discharge": convertToKwh(
            #                         val=item.get("value") or None, unit=unit
            #                     ),
            #                 }
            #             )
            #         # Discharge currently not provided with HES data
            #         # entry.update(
            #         #     {
            #         #         "battery_charge": convertToKwh(
            #         #             val=resp.get("totalImportedEnergy") or None,
            #         #             unit=resp.get("totalImportedEnergyUnit"),
            #         #         ),
            #         #     }
            #         # )
            #         # table.update({daystr: entry})
            #         # if showProgress:
            #         #     self._logger.info("Received api %s hes energy for %s", self.apisession.nickname, daystr)
            if showProgress:
                self._logger.info(
                    "Received api %s hes energy for period",
                    self.apisession.nickname,
                )

        # Get home usage energy types
        if SolixDeviceType.HES.value in devTypes:
            # get first data period from file or api
            if fromFile:
                resp = (
                    await self.apisession.loadFromFile(
                        Path(self.testDir())
                        / f"{API_FILEPREFIXES['hes_energy_home']}_{siteId}.json"
                    )
                ).get("data", {})
            else:
                resp = await self.energy_statistics(
                    siteId=siteId,
                    rangeType="week",
                    startDay=startDay,
                    # query only 1 day if daytotals requested
                    endDay=startDay
                    if dayTotals
                    else startDay + timedelta(days=numDays - 1),
                    sourceType="home",
                )
            fileNumDays = 0
            fileStartDay = None
            unit = resp.get("energyUnit") or ""
            for item in resp.get("energy") or []:
                # No daystring in response, count the index for proper date
                # daystr = item.get("time", None)
                if daystr := (startDay + timedelta(days=fileNumDays)).strftime(
                    "%Y-%m-%d"
                ):
                    if fromFile and fileStartDay is None:
                        fileStartDay = daystr
                    fileNumDays += 1
                    entry = table.get(daystr, {"date": daystr})
                    entry.update(
                        {
                            "home_usage": convertToKwh(
                                val=item.get("value") or None, unit=unit
                            ),
                        }
                    )
                    table.update({daystr: entry})
            # Home has consumption breakdown and shares for given interval. If requested, make daily queries for given interval
            if dayTotals and table:
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
                        resp = await self.energy_statistics(
                            siteId=siteId,
                            rangeType="week",
                            startDay=day,
                            endDay=day,
                            sourceType="home",
                        )
                        # get first item from breakdown list for single day queries
                        item = next(iter(resp.get("energy") or []), {})
                        unit = resp.get("energyUnit") or ""
                        entry.update(
                            {
                                "home_usage": convertToKwh(
                                    val=item.get("value") or None, unit=unit
                                ),
                            }
                        )
                    for item in resp.get("aggregates") or []:
                        itemtype = str(item.get("type") or "").lower()
                        if itemtype == "hes":
                            if (
                                percent := str(item.get("percent") or "").replace(
                                    "%", ""
                                )
                            ) and percent.isdigit():
                                percent = str(float(percent) / 100)
                            entry.update(
                                {
                                    "battery_to_home": convertToKwh(
                                        val=item.get("value") or None,
                                        unit=item.get("unit"),
                                    ),
                                    "battery_percentage": percent,
                                }
                            )
                        elif itemtype == "solar":
                            if (
                                percent := str(item.get("percent") or "").replace(
                                    "%", ""
                                )
                            ) and percent.isdigit():
                                percent = str(float(percent) / 100)
                            entry.update(
                                {
                                    "solar_to_home": convertToKwh(
                                        val=item.get("value") or None,
                                        unit=item.get("unit"),
                                    ),
                                    "solar_percentage": percent,
                                }
                            )
                        elif itemtype == "grid":
                            if (
                                percent := str(item.get("percent") or "").replace(
                                    "%", ""
                                )
                            ) and percent.isdigit():
                                percent = str(float(percent) / 100)
                            entry.update(
                                {
                                    "grid_to_home": convertToKwh(
                                        val=item.get("value") or None,
                                        unit=item.get("unit"),
                                    ),
                                    "other_percentage": percent,
                                }
                            )
                    table.update({daystr: entry})
                    if showProgress:
                        self._logger.info(
                            "Received api %s home energy for %s",
                            self.apisession.nickname,
                            daystr,
                        )
            if showProgress:
                self._logger.info(
                    "Received api %s home energy for period",
                    self.apisession.nickname,
                )

        # Add grid import, totals contain export and battery charging from grid for given interval
        if SolixDeviceType.HES.value in devTypes:
            # get first data period from file or api
            if fromFile:
                resp = (
                    await self.apisession.loadFromFile(
                        Path(self.testDir())
                        / f"{API_FILEPREFIXES['hes_energy_grid']}_{siteId}.json"
                    )
                ).get("data", {})
            else:
                resp = await self.energy_statistics(
                    siteId=siteId,
                    rangeType="week",
                    startDay=startDay,
                    # query only 1 day if daytotals requested
                    endDay=startDay
                    if dayTotals
                    else startDay + timedelta(days=numDays - 1),
                    sourceType="grid",
                )
            fileNumDays = 0
            fileStartDay = None
            unit = resp.get("energyUnit") or ""
            for item in resp.get("energy") or []:
                # No daystring in response, count the index for proper date
                # daystr = item.get("time", None)
                if daystr := (startDay + timedelta(days=fileNumDays)).strftime(
                    "%Y-%m-%d"
                ):
                    if fromFile and fileStartDay is None:
                        fileStartDay = daystr
                    fileNumDays += 1
                    entry = table.get(daystr, {"date": daystr})
                    entry.update(
                        {
                            "grid_import": convertToKwh(
                                val=item.get("value") or None, unit=unit
                            ),
                        }
                    )
                    table.update({daystr: entry})
            # Grid import, grid charge and solar export from grid totals for given interval. If requested, make daily queries for given interval
            if dayTotals and table:
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
                        resp = await self.energy_statistics(
                            siteId=siteId,
                            rangeType="week",
                            startDay=day,
                            endDay=day,
                            sourceType="grid",
                        )
                        # get first item from breakdown list for single day queries
                        item = next(iter(resp.get("energy") or []), {})
                        unit = resp.get("energyUnit") or ""
                        entry.update(
                            {
                                "grid_import": convertToKwh(
                                    val=item.get("value") or None, unit=unit
                                ),
                            }
                        )
                    for item in resp.get("aggregates") or []:
                        itemtype = str(item.get("type") or "").lower()
                        if itemtype == "hes":
                            entry.update(
                                {
                                    "grid_to_battery": convertToKwh(
                                        val=item.get("value") or None,
                                        unit=item.get("unit"),
                                    ),
                                }
                            )
                        elif itemtype == "solar":
                            entry.update(
                                {
                                    "solar_to_grid": convertToKwh(
                                        val=item.get("value") or None,
                                        unit=item.get("unit"),
                                    ),
                                }
                            )
                    table.update({daystr: entry})
                    if showProgress:
                        self._logger.info(
                            "Received api %s grid energy for %s",
                            self.apisession.nickname,
                            daystr,
                        )
            if showProgress:
                self._logger.info(
                    "Received api %s grid energy for period",
                    self.apisession.nickname,
                )

        # Always Add solar production
        # get first data period from file or api
        if fromFile:
            resp = (
                await self.apisession.loadFromFile(
                    Path(self.testDir())
                    / f"{API_FILEPREFIXES['hes_energy_solar']}_{siteId}.json"
                )
            ).get("data", {})
        else:
            resp = await self.energy_statistics(
                siteId=siteId,
                rangeType="week",
                startDay=startDay,
                # query only 1 day if daytotals requested
                endDay=startDay
                if dayTotals
                else startDay + timedelta(days=numDays - 1),
                sourceType="solar",
            )
        fileNumDays = 0
        fileStartDay = None
        unit = resp.get("energyUnit") or ""
        for item in resp.get("energy") or []:
            # No daystring in response, count the index for proper date
            # daystr = item.get("time", None)
            if daystr := (startDay + timedelta(days=fileNumDays)).strftime("%Y-%m-%d"):
                if fromFile and fileStartDay is None:
                    fileStartDay = daystr
                fileNumDays += 1
                entry = table.get(daystr, {"date": daystr})
                entry.update(
                    {
                        "solar_production": convertToKwh(
                            val=item.get("value") or None, unit=unit
                        ),
                    }
                )
                table.update({daystr: entry})
        # Solar charge and is only received as total value for given interval. If requested, make daily queries for given interval
        if dayTotals and table:
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
                    resp = await self.energy_statistics(
                        siteId=siteId,
                        rangeType="week",
                        startDay=day,
                        endDay=day,
                        sourceType="solar",
                    )
                    # get first item from breakdown list for single day queries
                    item = next(iter(resp.get("energy") or []), {})
                    unit = resp.get("energyUnit") or ""
                    entry.update(
                        {
                            "solar_production": convertToKwh(
                                val=item.get("value") or None, unit=unit
                            ),
                        }
                    )
                for item in resp.get("aggregates") or []:
                    itemtype = str(item.get("type") or "").lower()
                    if itemtype == "hes":
                        entry.update(
                            {
                                "solar_to_battery": convertToKwh(
                                    val=item.get("value") or None,
                                    unit=item.get("unit"),
                                ),
                            }
                        )
                table.update({daystr: entry})
                if showProgress:
                    self._logger.info(
                        "Received api %s solar energy for %s",
                        self.apisession.nickname,
                        daystr,
                    )
        if showProgress:
            self._logger.info(
                "Received api %s solar energy for period",
                self.apisession.nickname,
            )
        return table

    async def get_dev_info(self, siteId: str, fromFile: bool = False) -> dict:
        """Get the HES device info for site.

        This contains the complete hes device structure for a given site and can be used to find all device SN per site
        Example data:
        {"ats": {"sn": "","pn": "","type": "ats","img": "","name": "","aliasName": ""},
        "results": [{"sn": "SFW0EKTKW7IA043U","pn": "A5103","type": "pcs","img": "","name": "A5103_ARM","aliasName": "","subDevInfo": [
            {"sn": "SFW0EKTKW7IA043U","pn": "A5103","type": "ems","img": "","name": "A5103_ARM","aliasName": ""},
            {"sn": "SFW0EKTKW7IA043U","pn": "A5103","type": "pcs","img": "","name": "A5103_ARM","aliasName": ""},
            {"sn": "LVB4J2MJIBDYSFIY","pn": "A5220","type": "pack","img": "","name": "A5220_BMS","aliasName": ""},
            {"sn": "L1D6NQGANH5ODNPC","pn": "A5220","type": "pack","img": "","name": "A5220_BMS","aliasName": ""},
            {"sn": "2RXWQNI8QLAYW0LX","pn": "A5220","type": "pack","img": "","name": "A5220_BMS","aliasName": ""}]}],
        "ecuDevices": null},
        """
        data = {"siteId": siteId}
        if fromFile:
            resp = await self.apisession.loadFromFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['hes_get_hes_dev_info']}_{siteId}.json"
            )
        else:
            resp = await self.apisession.request(
                "post", API_HES_SVC_ENDPOINTS["get_hes_dev_info"], json=data
            )
        return resp.get("data") or {}
