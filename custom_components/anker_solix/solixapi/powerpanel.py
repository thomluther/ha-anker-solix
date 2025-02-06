"""Class for interacting with the Anker Power / Solix API Power Panel related charging_service endpoints.

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
    API_CHARGING_ENDPOINTS,
    API_FILEPREFIXES,
    ApiCategories,
    SolixDeviceCategory,
    SolixDeviceStatus,
    SolixDeviceType,
    SolixSiteType,
)
from .helpers import convertToKwh
from .session import AnkerSolixClientSession

_LOGGER: logging.Logger = logging.getLogger(__name__)


class AnkerSolixPowerpanelApi(AnkerSolixBaseApi):
    """Define the API class to handle Anker server communication via AnkerSolixClientSession for Power Panel related queries.

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

    def testDir(self, subfolder: str | None = None) -> str:
        """Get or set the subfolder for local API test files in the api session."""
        return self.apisession.testDir(subfolder)

    def logLevel(self, level: int | None = None) -> int:
        """Get or set the logger log level."""
        if level is not None and isinstance(level, int):
            self._logger.setLevel(level)
            self._logger.info("Set log level to: %s", level)
        return self._logger.getEffectiveLevel()

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
                        ]
                        and value
                    ):
                        device.update({key: str(value)})

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
        self,
        siteId: str | None = None,
        fromFile: bool = False,
        exclude: set | None = None,
        siteData: dict | None = None,
    ) -> dict:
        """Create/Update api sites cache structure.

        Implement this method to get the latest info for all power panel sites or only the provided siteId and update class cache dictionaries.
        """
        # define excluded categories to skip for queries
        if not exclude or not isinstance(exclude, set):
            exclude = set()
        if not siteData or not isinstance(siteData, dict):
            siteData = {}
        if siteId and (
            (site_info := siteData.pop("site_info", {}))
            or (self.sites.get(siteId) or {}).get("site_info")
            or {}
        ):
            # update only the provided site ID when siteInfo available/provided to avoid another site list query
            self._logger.debug("Updating Power Panel Sites data for site ID %s", siteId)
            new_sites = self.sites
            # prepare the site list dictionary for the update loop by copying the requested site from the cache
            sites: dict = {"site_list": [site_info]}
        else:
            # run normal query to get all power panel sites
            self._logger.debug("Updating Power Panel Sites data")
            new_sites = {}
            self._logger.debug("Getting site list")
            sites = await self.get_site_list(fromFile=fromFile)
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
                # check if power panel site type
                if mysite.get("site_type") == SolixDeviceType.POWERPANEL.value:
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
                    # query scene info if not provided in site Data
                    if not (scene := siteData):
                        self._logger.debug("Getting scene info for site")
                        scene = await self.get_scene_info(myid, fromFile=fromFile)
                    # add extra site data to my site
                    if scene:
                        mysite["powerpanel_list"] = scene.get("powerpanel_list") or []
                    for powerpanel in mysite.get("powerpanel_list") or []:
                        # work around for device_name which is actually the device_alias in scene info
                        if "device_name" in powerpanel:
                            # modify only a copy of the device dict to prevent changing the scene info dict
                            powerpanel = dict(powerpanel).copy()
                            powerpanel.update(
                                {"alias_name": powerpanel.pop("device_name")}
                            )
                        if sn := self._update_dev(
                            powerpanel,
                            devType=SolixDeviceType.POWERPANEL.value,
                            siteId=myid,
                            isAdmin=admin,
                        ):
                            self._site_devices.add(sn)

                    # Query 5 min avg power and soc from energy stats as work around since no current power values found for power panels in cloud server yet
                    if not (
                        {
                            SolixDeviceType.POWERPANEL.value,
                            ApiCategories.powerpanel_energy,
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
        self._logger.debug("Updating Power Panel Sites Details")
        for site_id, site in self.sites.items():
            # Fetch overall statistic totals for powerpanel site that should not be excluded since merged to overall site cache
            self._logger.debug("Getting system running totals information")
            await self.get_system_running_info(siteId=site_id, fromFile=fromFile)
            # Fetch details that work for all account types
            if {SolixDeviceType.POWERPANEL.value} - exclude:
                # Fetch details that only work for site admins
                if site.get("site_admin", False):
                    # Add extra power panel site polling that may make sense
                    pass
        return self.sites

    async def update_device_energy(
        self, fromFile: bool = False, exclude: set | None = None
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
            # Powerpanel sites have no variations for enery metrics, either all or none can be queried
            if not (
                {
                    SolixDeviceType.POWERPANEL.value,
                    ApiCategories.powerpanel_energy,
                }
                & exclude
            ):
                query_types: set = {SolixDeviceType.POWERPANEL.value}
            if query_types:
                self._logger.debug("Getting Power Panel energy details for site")
                # obtain previous energy details to check if yesterday must be queried as well
                energy = site.get("energy_details") or {}
                # delay actual time to allow the cloud server to finish update of previous day, since previous day will be queried only once
                # Cloud server energy stat updates may be delayed by 3 minutes for power panels
                time: datetime = datetime.now() - timedelta(minutes=5)
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
        self._logger.debug("Updating Power Panel Device Details")
        #
        # Implement required queries according to exclusion set
        #

        return self.devices

    async def get_system_running_info(
        self, siteId: str, fromFile: bool = False
    ) -> dict:
        """Get the site running information with tracked total stats.

        Example data:
        {"connect_infos": {"9NKBPG283YESZL5Y": true},"connected": true,"total_system_savings": 310.5,"system_savings_price_unit": "$",
        "save_carbon_footprint": 2.53,"save_carbon_unit": "t","save_carbon_c": 0.997,"total_system_power_generation": 2.54,"system_power_generation_unit": "MWh"}
        """
        data = {"siteId": siteId}
        if fromFile:
            resp = await self.apisession.loadFromFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['charging_get_system_running_info']}_{siteId}.json"
            )
        else:
            resp = await self.apisession.request(
                "post", API_CHARGING_ENDPOINTS["get_system_running_info"], json=data
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
                    "total": str(data.get("total_system_power_generation") or ""),
                    "unit": str(data.get("system_power_generation_unit") or "").lower(),
                }
            )
            # Total carbon
            stats.append(
                {
                    "type": "2",
                    "total": str(data.get("save_carbon_footprint") or ""),
                    "unit": str(data.get("save_carbon_unit") or "").lower(),
                }
            )
            # Total savings
            stats.append(
                {
                    "type": "3",
                    "total": str(data.get("total_system_savings") or ""),
                    "unit": str(data.get("system_savings_price_unit") or ""),
                }
            )
            # Add stats and connect infos to sites cache
            mysite.update(
                {
                    "statistics": stats,
                    "connect_infos": data.get("connect_infos") or {},
                },
            )
            self.sites[siteId] = mysite
        return data

    async def get_avg_power_from_energy(
        self, siteId: str, fromFile: bool = False
    ) -> dict:
        """Get the last 5 min average power from energy statistics.

        Example data:
        """
        # get existing data first from device detals to check if requery must be done
        avg_data = next(
            iter(
                [
                    (dev.get("average_power") or {})
                    for dev in self.devices.values()
                    if dev.get("type") == SolixDeviceType.POWERPANEL.value
                    and dev.get("site_id") == siteId
                ]
            ),
            {},
        )
        # verify last runtime and avoid re-query in less than 5 minutes since no new values available in energy stats
        if not (timestring := avg_data.get("last_check")) or (
            datetime.now() - datetime.strptime(timestring, "%Y-%m-%d %H:%M:%S")
        ) >= timedelta(minutes=5):
            self._logger.debug(
                "Updating Power average values from energy statistics of Panel Site ID %s",
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
                            "Checking %s data of %s",
                            source,
                            checkdate.strftime("%Y-%m-%d"),
                        )
                        if fromFile:
                            data = (
                                await self.apisession.loadFromFile(
                                    Path(self.testDir())
                                    / f"{API_FILEPREFIXES[f'charging_energy_{source}_today']}_{siteId}.json"
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
                            "Found valid %s entries until %s",
                            source,
                            validtime.strftime("%Y-%m-%d %H:%M:%S"),
                        )
                elif fromFile:
                    self._logger.debug(
                        "Reading %s data of %s",
                        source,
                        validtime.strftime("%Y-%m-%d"),
                    )
                    data = (
                        await self.apisession.loadFromFile(
                            Path(self.testDir())
                            / f"{API_FILEPREFIXES[f'charging_energy_{source}_today']}_{siteId}.json"
                        )
                    ).get("data") or {}
                else:
                    self._logger.debug(
                        "Querying %s data of %s",
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
                # Add average power to device details as work around if no other powerpanel usage data will be found in cloud
                for sn, dev in self.devices.items():
                    if (
                        dev.get("type") == SolixDeviceType.POWERPANEL.value
                        and dev.get("site_id") == siteId
                    ):
                        self.devices[sn]["average_power"] = avg_data

        return avg_data

    async def energy_statistics(
        self,
        siteId: str,
        rangeType: str | None = None,
        startDay: datetime | None = None,
        endDay: datetime | None = None,
        sourceType: str | None = None,
        isglobal: bool = False,
        productCode: str = "",
    ) -> dict:
        """Fetch Energy data for given device and optional time frame.

        siteId: site ID of device
        deviceSn: Device to fetch data # This does not really matter since system level data provided, but field is mandatory
        rangeType: "day" | "week" | "year"
        startTime: optional start Date and time
        endTime: optional end Date and time
        devType: "solar" | "hes" | "grid" | "home" | "pps" | "diesel"
        Example Data for solar_production:
        {"totalEnergy": "37.23","totalEnergyUnit": "KWh","totalImportedEnergy": "","totalImportedEnergyUnit": "","totalExportedEnergy": "37.23","totalExportedEnergyUnit": "KWh",
        "power": null,"powerUnit": "","chargeLevel": null,"energy": [
            {"value": "20.55","negValue": "0","rods": [
                {"from": "0.00","to": "20.55","sourceType": "solar"}]},
            {"value": "16.70","negValue": "0","rods": [
                {"from": "0.00","to": "16.70","sourceType": "solar"}]}],
        "energyUnit": "KWh","aggregates": [
            {"title": "Battery charging capacity","value": "26.00","unit": "KWh","type": "hes","percent": "69%","imported": false},
            {"title": "Load power consumption","value": "6.33","unit": "KWh","type": "home","percent": "17%","imported": false},
            {"title": "Sold power","value": "4.90","unit": "KWh","type": "grid","percent": "14%","imported": false}]}

        Responses for solar:
        Daily: Solar Energy, Extra Totals: PV charged, PV usage, PV to grid, 3 x percentage share solar usage
        Responses for pps:
        Daily: Discharge Energy, Extra Totals: charge
        Responses for hes:
        Daily: Discharge Energy, Extra Totals: charge
        Responses for home_usage:
        Daily: Home Usage Energy, Extra Totals: grid_to_home, battery_to_home, pv_to_home, 3 x percentage share home usage source
        Responses for grid:
        Daily: Grid import, Extra Totals: solar_to_grid, grid_to_home, grid_to_battery, 2 x percentage share how import used
        Responses for diesel:
        unknown
        """
        data = {
            "siteId": siteId,
            "sourceType": sourceType
            if sourceType in ["solar", "hes", "home", "grid", "pps", "diesel"]
            else "solar",
            "dateType": rangeType if rangeType in ["day", "week", "year"] else "day",
            "start": startDay.strftime("%Y-%m-%d")
            if startDay
            else datetime.today().strftime("%Y-%m-%d"),
            "end": endDay.strftime("%Y-%m-%d")
            if endDay
            else datetime.today().strftime("%Y-%m-%d"),
            "global": isglobal,
            "productCode": productCode,
        }
        resp = await self.apisession.request(
            "post", API_CHARGING_ENDPOINTS["energy_statistics"], json=data
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
    ) -> dict:
        """Fetch daily Energy data for given interval and provide it in a table format dictionary.

        Solar production data is always queried. Additional energy data will be queried for devtypes 'powerpanel'. The number of
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
        if SolixDeviceType.POWERPANEL.value in devTypes:
            # get first data period from file or api
            if fromFile:
                resp = (
                    await self.apisession.loadFromFile(
                        Path(self.testDir())
                        / f"{API_FILEPREFIXES['charging_energy_hes']}_{siteId}.json"
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
                            "battery_discharge": convertToKwh(
                                val=item.get("value") or None, unit=unit
                            ),
                        }
                    )
                    table.update({daystr: entry})
            # Power Panel HES has total charge energy for given interval. If requested, make daily queries for given interval
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
                            sourceType="hes",
                        )
                        # get first item from breakdown list for single day queries
                        item = next(iter(resp.get("energy") or []), {})
                        unit = resp.get("energyUnit") or ""
                        entry.update(
                            {
                                "battery_discharge": convertToKwh(
                                    val=item.get("value") or None, unit=unit
                                ),
                            }
                        )
                    entry.update(
                        {
                            "battery_charge": convertToKwh(
                                val=resp.get("totalImportedEnergy") or None,
                                unit=resp.get("totalImportedEnergyUnit"),
                            ),
                        }
                    )
                    table.update({daystr: entry})

        # Get home usage energy types
        if SolixDeviceType.POWERPANEL.value in devTypes:
            # get first data period from file or api
            if fromFile:
                resp = (
                    await self.apisession.loadFromFile(
                        Path(self.testDir())
                        / f"{API_FILEPREFIXES['charging_energy_home']}_{siteId}.json"
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

        # Add grid import, totals contain export and battery charging from grid for given interval
        if SolixDeviceType.POWERPANEL.value in devTypes:
            # get first data period from file or api
            if fromFile:
                resp = (
                    await self.apisession.loadFromFile(
                        Path(self.testDir())
                        / f"{API_FILEPREFIXES['charging_energy_grid']}_{siteId}.json"
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
            # Grid import and battery charge from grid totals for given interval. If requested, make daily queries for given interval
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
                    entry.update(
                        {
                            "solar_to_grid": convertToKwh(
                                val=resp.get("totalExportedEnergy") or None,
                                unit=resp.get("totalExportedEnergyUnit"),
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
                    table.update({daystr: entry})

        # Always Add solar production which contains percentages
        # get first data period from file or api
        if fromFile:
            resp = (
                await self.apisession.loadFromFile(
                    Path(self.testDir())
                    / f"{API_FILEPREFIXES['charging_energy_solar']}_{siteId}.json"
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
        return table
