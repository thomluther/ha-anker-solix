"""Base Class for interacting with the Anker Power / Solix API.

Required Python modules:
pip install cryptography
pip install aiohttp
pip install aiofiles
"""

from __future__ import annotations

import logging
from pathlib import Path

from aiohttp import ClientSession

from .apitypes import (
    API_ENDPOINTS,
    API_FILEPREFIXES,
    API_HES_SVC_ENDPOINTS,
    SolixDeviceType,
)
from .session import AnkerSolixClientSession

_LOGGER: logging.Logger = logging.getLogger(__name__)


class AnkerSolixBaseApi:
    """Define the API base class to handle Anker server communication via AnkerSolixClientSession.

    It will also build internal cache dictionaries with information collected through the Api, those methods can be overwritten.
    It also provides some general Api queries and helpers for classes inheriting the base class
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
        self.apisession: AnkerSolixClientSession
        if apisession:
            # reuse provided client
            self.apisession = apisession
        else:
            # init new client
            self.apisession = AnkerSolixClientSession(
                email=email,
                password=password,
                countryId=countryId,
                websession=websession,
                logger=logger,
            )
        self._logger: logging.Logger = self.apisession.logger()

        # track active devices bound to any site
        self._site_devices: set = set()
        # reset class variables for saving the most recent account, site and device data (Api cache)
        self.account: dict = {}
        self.sites: dict = {}
        self.devices: dict = {}

    def testDir(self, subfolder: str | None = None) -> str:
        """Get or set the subfolder for local API test files in the api session."""
        return self.apisession.testDir(subfolder)

    def endpointLimit(self, limit: int | None = None) -> int:
        """Get or set the api request limit per endpoint per minute."""
        return self.apisession.endpointLimit(limit)

    def logLevel(self, level: int | None = None) -> int:
        """Get or set the logger log level."""
        if level is not None and isinstance(level, int):
            self._logger.setLevel(level)
            self._logger.info(
                "Set api %s log level to: %s", self.apisession.nickname, level
            )
        return self._logger.getEffectiveLevel()

    def getCaches(self) -> dict:
        """Return a merged dictionary with api cache dictionaries."""
        return self.sites | self.devices | {self.apisession.email: self.account}

    def clearCaches(self) -> None:
        """Clear the api cache dictionaries except the account cache."""
        self.sites = {}
        self.devices = {}

    def recycleDevices(
        self, extraDevices: set | None = None, activeDevices: set | None = None
    ) -> None:
        """Recycle api device list and remove devices no longer used in sites cache or extra devices."""
        if not extraDevices or not isinstance(extraDevices, set):
            extraDevices = set()
        if not activeDevices or not isinstance(activeDevices, set):
            activeDevices = set()
        # first clear internal site devices cache if active devices are provided
        if activeDevices:
            rem_devices = [
                dev
                for dev in self._site_devices
                if dev not in (activeDevices | extraDevices)
            ]
            for dev in rem_devices:
                self._site_devices.discard(dev)
        # Clear device cache to maintain only active and extra devices
        rem_devices = [
            dev
            for dev in self.devices
            if dev not in (self._site_devices | extraDevices)
        ]
        for dev in rem_devices:
            self.devices.pop(dev, None)

    def recycleSites(self, activeSites: set | None = None) -> None:
        """Recycle api site cache and remove sites no longer active according provided activeSites."""
        if activeSites and isinstance(activeSites, set):
            rem_sites = [site for site in self.sites if site not in activeSites]
            for site in rem_sites:
                self.sites.pop(site, None)

    def _update_account(
        self,
        details: dict | None = None,
    ) -> None:
        """Update the internal account dictionary with data provided in details dictionary.

        This method is used to consolidate acount related details from various less frequent requests that are not covered with the update_sites method.
        """
        if not details or not isinstance(details, dict):
            details = {}
        # lookup old account details if any or update account info if nickname is different (e.g. after authentication)
        if (
            not (account_details := self.account or {})
            or account_details.get("nickname") != self.apisession.nickname
        ):
            # init or update the account details
            account_details.update(
                {
                    "type": SolixDeviceType.ACCOUNT.value,
                    "email": self.apisession.email,
                    "nickname": self.apisession.nickname,
                    "country": self.apisession.countryId,
                    "server": self.apisession.server,
                }
            )
        # update extra details and always request counts
        account_details.update(
            details
            | {
                "requests_last_min": self.apisession.request_count.last_minute(),
                "requests_last_hour": self.apisession.request_count.last_hour(),
            }
        )
        self.account = account_details

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
                    #
                    # Implement device update code with key filtering, conversion, consolidation, calculation or dependency updates
                    #
                    if key in ["device_sw_version"] and value:
                        # Example for key name conversion when value is given
                        device.update({"sw_version": str(value)})
                    elif key in [
                        # Examples for boolean key values
                        "wifi_online",
                        "auto_upgrade",
                        "is_ota_update",
                    ]:
                        device.update({key: bool(value)})
                    elif key in [
                        # Example for key with string values
                        "wireless_type",
                        "ota_version",
                    ] or (
                        key
                        in [
                            # Example for key with string values that should only be updated if value returned
                            "wifi_name",
                        ]
                        and value
                    ):
                        device.update({key: str(value)})
                    else:
                        # Example for all other keys not filtered or converted
                        device.update({key: value})

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
    ) -> dict:
        """Create/Update api sites cache structure.

        Implement this method to get the latest info for all accessible sites or only the provided siteId and update class cache dictionaries.
        """
        # define excluded categories to skip for queries
        if not exclude or not isinstance(exclude, set):
            exclude = set()
        if siteId and (self.sites.get(siteId) or {}):
            # update only the provided site ID
            self._logger.debug(
                "Updating api %s sites data for site ID %s",
                self.apisession.nickname,
                siteId,
            )
            new_sites = self.sites
            # prepare the site list dictionary for the update loop by copying the requested site from the cache
            sites: dict = {"site_list": [self.sites[siteId].get("site_info") or {}]}
        else:
            # run normal refresh for all sites
            self._logger.debug(
                "Updating api %s sites data",
                self.apisession.nickname,
            )
            new_sites = {}
            self._logger.debug(
                "Getting api %s site list",
                self.apisession.nickname,
            )
            sites = await self.get_site_list(fromFile=fromFile)
            self._site_devices = set()
        for site in sites.get("site_list", []):
            if myid := site.get("site_id"):
                # Update site info
                mysite: dict = self.sites.get(myid, {})
                siteInfo: dict = mysite.get("site_info", {})
                siteInfo.update(site)
                mysite.update(
                    {"type": SolixDeviceType.SYSTEM.value, "site_info": siteInfo}
                )
                admin = (
                    siteInfo.get("ms_type", 0) in [0, 1]
                )  # add boolean key to indicate whether user is site admin (ms_type 1 or not known) and can query device details
                mysite.update({"site_admin": admin})
                # Update scene info for site
                self._logger.debug(
                    "Getting api %s scene info for site",
                    self.apisession.nickname,
                )
                scene = await self.get_scene_info(myid, fromFile=fromFile)
                mysite.update(scene)
                new_sites.update({myid: mysite})
                #
                # Implement site dependent device update code as needed for various device types
                # For each SN found in the site structures, update the internal site_devices set
                # The update device details routine may also find standalone devices and need to merge all active
                # devices for cleanup/removal of extra/obsolete devices in the cache structure
                self._site_devices.add("found_sn")

        # Write back the updated sites
        self.sites = new_sites
        # update account dictionary with number of requests
        self._update_account({"use_files": fromFile})
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
            "Updating api %s sites details",
            self.apisession.nickname,
        )
        #
        # Implement required queries according to exclusion set
        #

        # update account dictionary with number of requests
        self._update_account({"use_files": fromFile})
        return self.sites

    async def update_device_energy(
        self, fromFile: bool = False, exclude: set | None = None
    ) -> dict:
        """Get the site energy statistics for given device types from today and yesterday.

        Implement this method for the required energy query methods to obtain energy data for today and yesterday.
        It was found that energy data is tracked only per site, but not individual devices even if a device SN parameter may be mandatory in the Api request.
        """
        # check exclusion list, default to all energy data
        if not exclude or not isinstance(exclude, set):
            exclude = set()
        for site_id, site in self.sites.items():
            self._logger.debug(
                "Getting api %s energy details for site",
                self.apisession.nickname,
            )
            #
            # Implement required queries according to exclusion set
            #
            # save energy stats with sites dictionary
            site["energy_details"] = {"energy_key": "energy_value"}
            self.sites[site_id] = site

        # update account dictionary with number of requests
        self._update_account({"use_files": fromFile})
        return self.devices

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
            "Updating api %s device details",
            self.apisession.nickname,
        )
        #
        # Implement required queries according to exclusion set
        #

        # update account dictionary with number of requests
        self._update_account({"use_files": fromFile})
        return self.devices

    async def get_site_rules(self, fromFile: bool = False) -> dict:
        """Get the site rules supported by the api.

        Example data:
        {'rule_list': [
            {'power_site_type': 1, 'main_device_models': ['A5143'], 'device_models': ['A5143', 'A1771'], 'can_empty_site': False,
                'quantity_min_limit_map': {'A1771': 1, 'A5143': 1},'quantity_max_limit_map': {'A1771': 2, 'A5143': 1}},
            {'power_site_type': 2, 'main_device_models': ['A17C0'], 'device_models': ['A17C0', 'A5143', 'A1771'], 'can_empty_site': False,
                'quantity_min_limit_map': {'A17C0': 1}, 'quantity_max_limit_map': {'A1771': 2, 'A17C0': 2, 'A5143': 1}},
            {'power_site_type': 4, 'main_device_models': ['A17B1'], 'device_models': ['A17B1'], 'can_empty_site': True,
                'quantity_min_limit_map': None, 'quantity_max_limit_map': {'A17B1': 1}},
            {'power_site_type': 5, 'main_device_models': ['A17C1'], 'device_models': ['A17C1', 'A17X7'], 'can_empty_site': True,
                'quantity_min_limit_map': None, 'quantity_max_limit_map': {'A17C1': 1}},
            {'power_site_type': 6, 'main_device_models': ['A5341'], 'device_models': ['A5341', 'A5101', 'A5220'], 'can_empty_site': False,
                'quantity_min_limit_map': {'A5341': 1}, 'quantity_max_limit_map': {'A5341': 1}},
            {'power_site_type': 7, 'main_device_models': ['A5101'], 'device_models': ['A5101', 'A5220'], 'can_empty_site': False,
                'quantity_min_limit_map': {'A5101': 1}, 'quantity_max_limit_map': {'A5101': 6}},
            {'power_site_type': 8, 'main_device_models': ['A5102'], 'device_models': ['A5102', 'A5220'], 'can_empty_site': False,
                'quantity_min_limit_map': {'A5102': 1}, 'quantity_max_limit_map': {'A5102': 6}},
            {'power_site_type': 9, 'main_device_models': ['A5103'], 'device_models': ['A5103', 'A5220'], 'can_empty_site': False,
                'quantity_min_limit_map': {'A5103': 1}, 'quantity_max_limit_map': {'A5103': 6}}]}
        """
        if fromFile:
            resp = await self.apisession.loadFromFile(
                Path(self.testDir()) / f"{API_FILEPREFIXES['site_rules']}.json"
            )
        else:
            resp = await self.apisession.request("post", API_ENDPOINTS["site_rules"])
        return resp.get("data") or {}

    async def get_site_list(self, fromFile: bool = False) -> dict:
        """Get the site list for the used account.

        Example data:
        {'site_list': [{'site_id': 'efaca6b5-f4a0-e82e-3b2e-6b9cf90ded8c', 'site_name': 'BKW', 'site_img': '', 'device_type_list': [3], 'ms_type': 2, 'power_site_type': 2, 'is_allow_delete': True}]}
        """
        if fromFile:
            resp = await self.apisession.loadFromFile(
                Path(self.testDir()) / f"{API_FILEPREFIXES['site_list']}.json"
            )
        else:
            resp = await self.apisession.request("post", API_ENDPOINTS["site_list"])
        return resp.get("data") or {}

    async def get_scene_info(self, siteId: str, fromFile: bool = False) -> dict:
        """Get scene info. It reflects mostly data visible in the Anker App home page for the site. It also works for shared accounts.

        Example data for provided site_id:
        {"home_info":{"home_name":"Home","home_img":"","charging_power":"0.00","power_unit":"W"},
        "solar_list":[],
        "pps_info":{"pps_list":[],"total_charging_power":"0.00","power_unit":"W","total_battery_power":"0.00","updated_time":"","pps_status":0},
        "statistics":[{"type":"1","total":"89.75","unit":"kwh"},{"type":"2","total":"89.48","unit":"kg"},{"type":"3","total":"35.90","unit":"€"}],
        "topology_type":"1","solarbank_info":{"solarbank_list":
            [{"device_pn":"A17C0","device_sn":"9JVB42LJK8J0P5RY","device_name":"Solarbank E1600",
                "device_img":"https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/e9478c2d-e665-4d84-95d7-dd4844f82055/20230719-144818.png",
                "battery_power":"75","bind_site_status":"","charging_power":"0","power_unit":"W","charging_status":"2","status":"0","wireless_type":"1","main_version":"","photovoltaic_power":"0",
                "output_power":"0","create_time":1695392386}],
            "total_charging_power":"0","power_unit":"W","charging_status":"0","total_battery_power":"0.00","updated_time":"2023-12-28 18:53:27","total_photovoltaic_power":"0","total_output_power":"0.00"},
        "retain_load":"0W","updated_time":"01-01-0001 00:00:00","power_site_type":2,"site_id":"efaca6b5-f4a0-e82e-3b2e-6b9cf90ded8c"}
        """
        data = {"site_id": siteId}
        if fromFile:
            resp = await self.apisession.loadFromFile(
                Path(self.testDir()) / f"{API_FILEPREFIXES['scene_info']}_{siteId}.json"
            )
        else:
            resp = await self.apisession.request(
                "post", API_ENDPOINTS["scene_info"], json=data
            )
        return resp.get("data") or {}

    async def get_bind_devices(self, fromFile: bool = False) -> dict:
        """Get the bind device information, which will list all devices the account has admin rights for. It also contains firmware level of devices.

        Example data:
        {"data": [{"device_sn":"9JVB42LJK8J0P5RY","product_code":"A17C0","bt_ble_id":"BC:A2:AF:C7:55:F9","bt_ble_mac":"BCA2AFC755F9","device_name":"Solarbank E1600","alias_name":"Solarbank E1600",
        "img_url":"https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/e9478c2d-e665-4d84-95d7-dd4844f82055/20230719-144818.png",
        "link_time":1695392302068,"wifi_online":false,"wifi_name":"","relate_type":["ble","wifi"],"charge":false,"bws_surplus":0,"device_sw_version":"v1.4.4","has_manual":false}]}
        """
        if fromFile:
            resp = await self.apisession.loadFromFile(
                Path(self.testDir()) / f"{API_FILEPREFIXES['bind_devices']}.json"
            )
        else:
            resp = await self.apisession.request("post", API_ENDPOINTS["bind_devices"])
        data = resp.get("data") or {}
        active_devices = set()
        for device in data.get("data") or []:
            # ensure to get product list once if needed if no device name in response
            if not device.get("device_name") and "products" not in self.account:
                self._update_account(
                    {"products": await self.get_products(fromFile=fromFile)}
                )
            if sn := self._update_dev(device):
                active_devices.add(sn)
        # recycle api device list and remove devices no longer used in sites or bind devices
        self.recycleDevices(extraDevices=active_devices)
        return data

    async def get_auto_upgrade(self, fromFile: bool = False) -> dict:
        """Get auto upgrade settings and devices enabled for auto upgrade.

        Example data:
        {'main_switch': True, 'device_list': [{'device_sn': '9JVB42LJK8J0P5RY', 'device_name': 'Solarbank E1600', 'auto_upgrade': True, 'alias_name': 'Solarbank E1600',
        'icon': 'https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/e9478c2d-e665-4d84-95d7-dd4844f82055/20230719-144818.png'}]}
        """
        if fromFile:
            resp = await self.apisession.loadFromFile(
                Path(self.testDir()) / f"{API_FILEPREFIXES['get_auto_upgrade']}.json"
            )
        else:
            resp = await self.apisession.request(
                "post", API_ENDPOINTS["get_auto_upgrade"]
            )
        data = resp.get("data") or {}
        main = data.get("main_switch")
        devicelist = data.get("device_list", [])  # could be null for non owning account
        if not devicelist:
            devicelist = []
        for device in devicelist:
            dev_ota = device.get("auto_upgrade")
            if isinstance(dev_ota, bool):
                # update device setting based on main setting if available
                if isinstance(main, bool):
                    device.update({"auto_upgrade": main and dev_ota})
                self._update_dev(device)
        return data

    async def set_auto_upgrade(self, devices: dict[str, bool]) -> bool:
        """Set auto upgrade switches for given device dictionary.

        Example input:
        devices = {'9JVB42LJK8J0P5RY': True}
        The main switch must be set True if any device switch is set True. The main switch does not need to be changed to False if no device is True.
        But if main switch is set to False, all devices will automatically be set to False and individual setting is ignored by Api.
        """
        # get actual settings
        settings = await self.get_auto_upgrade()
        if (main_switch := settings.get("main_switch")) is None:
            return False
        dev_switches = {}
        main = None
        change_list = []
        for dev_setting in settings.get("device_list") or []:
            if (
                isinstance(dev_setting, dict)
                and (device_sn := dev_setting.get("device_sn"))
                and (dev_upgrade := dev_setting.get("auto_upgrade")) is not None
            ):
                dev_switches[device_sn] = dev_upgrade
        # Loop through provided device list and compose the request data device list that needs to be send
        for sn, upgrade in devices.items():
            if sn in dev_switches:
                if upgrade != dev_switches[sn]:
                    change_list.append({"device_sn": sn, "auto_upgrade": upgrade})
                    if upgrade:
                        main = True

        if change_list:
            # json example for endpoint
            # {"main_switch": False, "device_list": [{"device_sn": "9JVB42LJK8J0P5RY","auto_upgrade": True}]}
            data = {
                "main_switch": main if main is not None else main_switch,
                "device_list": change_list,
            }
            # Make the Api call and check for return code
            code = (
                await self.apisession.request(
                    "post", API_ENDPOINTS["set_auto_upgrade"], json=data
                )
            ).get("code")
            if not isinstance(code, int) or int(code) != 0:
                return False
            # update the data in api dict
            await self.get_auto_upgrade()

        return True

    async def get_wifi_list(self, siteId: str, fromFile: bool = False) -> dict:
        """Get the wifi list.

        Example data:
        {'wifi_info_list': [{"wifi_name": "wifi-network-1","wifi_signal": "48","device_sn": "7SKIVRGPK8XC2ROB","rssi": "","offline": false}]}
        """
        data = {"site_id": siteId}
        if fromFile:
            resp = await self.apisession.loadFromFile(
                Path(self.testDir()) / f"{API_FILEPREFIXES['wifi_list']}_{siteId}.json"
            )
        else:
            resp = await self.apisession.request(
                "post", API_ENDPOINTS["wifi_list"], json=data
            )
        # update device data if device_sn found in wifi list
        if data := resp.get("data") or {}:
            for wifi_info in data.get("wifi_info_list") or []:
                if wifi_info.get("device_sn"):
                    self._update_dev(wifi_info)
        return data

    async def get_ota_batch(
        self, deviceSns: list | None = None, fromFile: bool = False
    ) -> dict:
        """Get the OTA info for provided list of device serials or for all owning devices in devices dict.

        Example data:
        {"update_infos": [{"device_sn": "9JVB42LJK8J0P5RY","need_update": false,"upgrade_type": 0,"lastPackage": {
                "product_code": "","product_component": "","version": "","is_forced": false,"md5": "","url": "","size": 0},
        "change_log": "","current_version": "v1.6.3","children": [
            {"needUpdate": false,"device_type": "A17C1_esp32","rom_version_name": "v0.1.5.1","force_upgrade": false,"full_package": {
                "file_path": "https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/ota/2024/09/06/iot-admin/J7lALfvEQZIiqHyD/A17C1-A17C3_EUOTAWIFI_V0.1.5.1_20240828.bin",
                "file_size": 1270256,"file_md5": "578ac26febb55ee55ffe9dc6819b6c4a"},
            "change_log": "","sub_current_version": ""},
            {"needUpdate": false,"device_type": "A17C1_mcu","rom_version_name": "v1.0.5.16","force_upgrade": false,"full_package": {
                "file_path": "https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/ota/2024/09/06/iot-admin/w3ofT0NcpGF3IUcC/A17C1-A17C3_EUOTA_V1.0.5.16_20240904.bin",
                "file_size": 694272,"file_md5": "40913018b3e542c0350e8815951e4a9c"},
            "change_log": "","sub_current_version": ""},
            {"needUpdate": false,"device_type": "A17C1_100Ah","rom_version_name": "v0.1.9.1","force_upgrade": false,"full_package": {
                "file_path": "https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/ota/2024/09/06/iot-admin/mmCg3IkHt2YpF8TR/A17C1-A17C3_EUOTA_V0.1.9.1_20240904.bin",
                "file_size": 694272,"file_md5": "40913018b3e542c0350e8815951e4a9c"},
            "change_log": "","sub_current_version": ""}]]}]}
        """
        # default to all admin devices in devices dict if no device serial list provided
        if not deviceSns or not isinstance(deviceSns, list):
            deviceSns = [
                s for s, device in self.devices.items() if device.get("is_admin")
            ]
        if not deviceSns:
            resp = {}
        elif fromFile:
            resp = await self.apisession.loadFromFile(
                Path(self.testDir()) / f"{API_FILEPREFIXES['get_ota_batch']}.json"
            )
        else:
            data = {
                "device_list": [
                    {"device_sn": serial, "version": ""} for serial in deviceSns
                ]
            }
            resp = await self.apisession.request(
                "post", API_ENDPOINTS["get_ota_batch"], json=data
            )
        # update device details only if valid response
        if (data := resp.get("data") or {}) and deviceSns:
            # update devices dict with new ota data
            for dev in data.get("update_infos") or []:
                if deviceSn := dev.get("device_sn"):
                    need_update = bool(dev.get("need_update"))
                    is_forced = bool(dev.get("is_forced"))
                    children: list = []
                    for child in dev.get("children") or []:
                        need_update = need_update or bool(child.get("needUpdate"))
                        is_forced = is_forced or bool(child.get("needUpdate"))
                        children.append(
                            {
                                "device_type": child.get("device_type"),
                                "need_update": bool(child.get("needUpdate")),
                                "force_upgrade": bool(child.get("force_upgrade")),
                                "rom_version_name": child.get("rom_version_name"),
                            }
                        )
                    self._update_dev(
                        {
                            "device_sn": deviceSn,
                            "is_ota_update": need_update,
                            "ota_forced": need_update,
                            "ota_version": (dev.get("lastPackage") or {}).get("version")
                            or dev.get("current_version")
                            or "",
                            "ota_children": children,
                        }
                    )
        return data

    async def get_message_unread(self, fromFile: bool = False) -> dict:
        """Get the unread messages for account.

        Example data:
        {"has_unread_msg": false}
        """
        if fromFile:
            resp = await self.apisession.loadFromFile(
                Path(self.testDir()) / f"{API_FILEPREFIXES['get_message_unread']}.json"
            )
        else:
            resp = await self.apisession.request(
                "get", API_ENDPOINTS["get_message_unread"]
            )
        data = resp.get("data") or {}
        # New method: Save unread msg flag in account dictionary
        self._update_account(data)
        return data

    async def get_product_platforms_list(self, fromFile: bool = False) -> list:
        r"""Get the product list. The response fields will show all supported Anker devices including model type, device name and image url.

        Example data:
        [{"name": "Balcony Solar Power System","img_url": "https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/29f0b6a3-6ba5-40cb-b1b8-94cf39784433/20230731-103020.jpeg",
          "index": 2,"products": [
          {"name": "MI60 Microinverter","img_url": "https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/2e60fc1a-f1c2-4574-8e00-a50689c87f72/picl_A5140_normal.png",
            "index": 1,"product_code": "A5140","net_img_url": "https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/e75905fc-4cce-4533-bece-8bd7f9464e6f/A5140_guide.png",
            "net_guideline": "<div style=\"margin-bottom:12px;\"><font face=\"DingNextLTProRegular\" style=\"font-size: 16px\";>The Schuko cable should not be connected to your home grid yet!</font></div><br>\n\n<div style=\"margin-bottom:12px;\"><font face=\"DingNextLTProRegular\" style=\"font-size: 16px\";>Step 1: Please make sure the DC power supply (cable solar panel to inverter) is connected.</font></div><br>\n\n<div style=\"margin-bottom:12px;\"><font face=\"DingNextLTProRegular\" style=\"font-size: 16px\";>Step 2: Wait 90 seconds when the indicator light of the inverter</font><font face=\"DingNextLTProRegular\" color=\"#00A9E0\" style=\"font-size: 16px\"> blink red</font>.</div><br>\n\n<div style=\"margin-bottom:12px;\"><font face=\"DingNextLTProRegular\" style=\"font-size: 16px\";>Step 3: Connect your phone to the Wi-Fi of the Microinverter</font><font face=\"DingNextLTProRegular\" color=\"#00A9E0\" style=\"font-size: 16px\"> MI-XXXXXXXX</font><font face=\"DingNextLTProRegular\" style=\"font-size: 16px\";> and return to the Anker App.</font></div><br>\n\n<div style=\"margin-bottom:12px;\"><font face=\"DingNextLTProRegular\" style=\"font-size: 16px\";>Password:</font><font face=\"DingNextLTProRegular\" color=\"#00A9E0\" style=\"font-size: 16px\">12345678</font></div>",
            "p_codes": []},
          {"name": "Solarbank 2 E1600 Pro","img_url": "https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/2024/05/24/iot-admin/5iJoq1dk63i47HuR/picl_A17C1_normal%281%29.png",
            "index": 1,"product_code": "A17C1","net_img_url": "https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/2024/05/24/iot-admin/xCw8DYNcDGk35wxs/A17C1_guide.gif",
            "net_guideline": "Press the IoT button for 2 seconds until the IoT button starts flashing.","p_codes": [
              {"p_code": "A17C13Z1","img_url": "https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/banner/2024/05/24/iot-admin/SC9Wa8mzqhkLFMjt/picl_A17C1_normal.png"},
              {"p_code": "A17C1IZ1","img_url": "https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/banner/2024/05/24/iot-admin/SC9Wa8mzqhkLFMjt/picl_A17C1_normal.png"}]},
          {"name": "Solarbank E1600","img_url": "https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/e9478c2d-e665-4d84-95d7-dd4844f82055/20230719-144818.png",
            "index": 2,"product_code": "A17C0","net_img_url": "https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/a901a1c3-a2ba-46ec-8eb6-f644eb29489b/A17C0_guide_generic.gif",
            "net_guideline": "Press the button and the IoT button is blinking green light.","p_codes": [
              {"p_code": "6Y6","img_url": "https://public-aiot-fra-prod.s3.eu-central-1.amazonaws.com/anker-power/public/banner/2023/08/21/iot-admin/2ZacNVApQvHbpyFe/picl_A17C0_normal.png"},
              {"p_code": "V6Y","img_url": "https://public-aiot-fra-prod.s3.eu-central-1.amazonaws.com/anker-power/public/banner/2023/08/21/iot-admin/2ZacNVApQvHbpyFe/picl_A17C0_normal.png"},
              {"p_code": "T90","img_url": "https://public-aiot-fra-prod.s3.eu-central-1.amazonaws.com/anker-power/public/banner/2023/08/21/iot-admin/2ZacNVApQvHbpyFe/picl_A17C0_normal.png"}]}]
        """
        if fromFile:
            resp = await self.apisession.loadFromFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['get_product_categories']}.json"
            )
        else:
            resp = await self.apisession.request(
                "get", API_ENDPOINTS["get_product_categories"]
            )
        return resp.get("data") or []

    async def get_third_platforms_list(self, fromFile: bool = False) -> list:
        r"""Get the 3rd party platform list. The response fields will show all supported 3rd party platforms with their products, including model type, device name and image url.

        Example data:
        {"data":[{"index": 0,"name": "Shelly",
          "content": "Shelly\u662f\u4e00\u5bb6\u4e13\u6ce8\u4e8e\u667a\u80fd\u5bb6\u5c45\u8bbe\u5907\u7684\u516c\u53f8\uff0c\u63d0\u4f9b\u9ad8\u6027\u80fd\u3001\u6613\u7528\u7684\u667a\u80fd\u5f00\u5173\u3001\u63d2\u5ea7\u3001\u4f20\u611f\u5668\u548c\u63a7\u5236\u5668\uff0c\u517c\u5bb9\u5176\u4ed6\u667a\u80fd\u5bb6\u5c45\u7cfb\u7edf\uff0c\u63d0\u5347\u7528\u6237\u4f53\u9a8c\u3002",
          "logo": "https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/banner/2024/08/29/iot-admin/isCjeqQviU5L4O7D/20240829-102526.jpg",
          "tag": "shelly","url": "https://my.shelly.cloud/integrator.html","callback_url": "https://ankerpower-api-eu.anker.com/cloud/powerservice/shelly_callback","tag_code": "ITG_AIN2",
          "products": [
            {"name": "3EM","img_url": "https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/banner/2024/08/29/iot-admin/5lyJ9NmYG5pD7NIA/3em.png",
            "index": 0,"product_code": "SHEM3","net_img_url": "","net_guideline": "","p_codes": null},
            {"name": "Pro 3EM","img_url": "https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/banner/2024/09/02/iot-admin/I8dV8ONUfEm4iXSc/3em%20pro.png",
            "index": 0,"product_code": "SHEMP3","net_img_url": "","net_guideline": "","p_codes": null}],
          "countries": "DE,AT,FR,IT"}]}
        """
        if fromFile:
            resp = await self.apisession.loadFromFile(
                Path(self.testDir()) / f"{API_FILEPREFIXES['get_third_platforms']}.json"
            )
        else:
            resp = await self.apisession.request(
                "post", API_ENDPOINTS["get_third_platforms"]
            )
        return (resp.get("data") or {}).get("data") or []

    async def get_hes_platforms_list(self, fromFile: bool = False) -> list:
        r"""Get the hes platform list. The response fields will show supported platforms categories with their products, some redundant but also some unique to product platform list.

        Example data:
        "data": {"productsInfo": [
            {"category": "Balcony Solar Power System","code": "A5140","name": "MI60 Microinverter",
            "imgUrl": "https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/2e60fc1a-f1c2-4574-8e00-a50689c87f72/picl_A5140_normal.png"},
            {"category": "Balcony Solar Power System","code": "A17C1","name": "Solarbank 2 E1600 Pro",
            "imgUrl": "https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/2024/05/24/iot-admin/5iJoq1dk63i47HuR/picl_A17C1_normal%281%29.png"},
            {"category": "Residential Storage System","code": "A5101","name": "X1-P6K-US/S",
            "imgUrl": "https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/2024/03/27/iot-admin/KEwdxNejZq2tDXCX/picl_A5101_normal.png"},
            {"category": "Residential Storage System","code": "A5150","name": "Microinverter",
            "imgUrl": "https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/2024/07/29/iot-admin/1VUzMEfFhzv4gopz/%E5%BE%AE%E9%80%86.png"},
            {"category": "Residential Storage System","code": "A5341","name": "Backup Controller",
            "imgUrl": "https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/2024/09/24/iot-admin/ANJzf3AX8isPzNMI/picl_A5341_normal.png"},
            {"category": "Residential Storage System","code": "A5450","name": "Zigbee Dongle",
            "imgUrl": "https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/2024/07/29/iot-admin/mp7s3FzbBXjRqIxV/ECU.png"},
            {"category": "Residential Storage System","code": "A5102","name": "X1-H(3.68~6)K-S\t",
            "imgUrl": "https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/2024/03/27/iot-admin/BT8pMS9hrhg8IEob/picl_A5101_normal.png"},
            {"category": "Residential Storage System","code": "A5103","name": "X1-H (5~12)K-T",
            "imgUrl": "https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/2024/03/27/iot-admin/NLxTngSOzIY49fX2/picl_A5101_normal.png"},
            {"category": "Residential Storage System","code": "A5220","name": "Battery Module",
            "imgUrl": "https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/2024/03/27/iot-admin/QgLuazcQypTsCzvv/picl_A5220_normal.png"}]}
        """
        if fromFile:
            resp = await self.apisession.loadFromFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['hes_get_product_info']}.json"
            )
        else:
            resp = await self.apisession.request(
                "post", API_HES_SVC_ENDPOINTS["get_product_info"]
            )
        return (resp.get("data") or {}).get("productsInfo") or []

    async def get_products(self, fromFile: bool = False) -> dict:
        """Compose the supported Anker and third platform products into a condensed dictionary."""

        products = {}
        self._logger.debug(
            "Getting api %s Anker platform list",
            self.apisession.nickname,
        )
        for platform in await self.get_product_platforms_list(fromFile=fromFile):
            plat_name = platform.get("name") or ""
            for prod in platform.get("products") or []:
                products[prod.get("product_code") or ""] = {
                    "name": str(prod.get("name") or "").strip(),
                    "platform": str(plat_name).strip(),
                    # "img_url": prod.get("img_url"),
                }
        self._logger.debug(
            "Getting api %s HES product list",
            self.apisession.nickname,
        )
        for platform in await self.get_hes_platforms_list(fromFile=fromFile):
            if (pn := platform.get("code") or "") and pn not in products:
                products[pn] = {
                    "name": str(platform.get("name") or "").strip(),
                    "platform": str(platform.get("category") or "").strip(),
                    # "img_url": platform.get("imgUrl"),
                }
        # get_third_platforms_list does no longer show 3rd platform products, skip query until data provided again
        # see https://github.com/thomluther/anker-solix-api/issues/172
        # self._logger.debug(
        #     "Getting api %s 3rd party platform list",
        #     self.apisession.nickname,
        # )
        # for platform in await self.get_third_platforms_list(fromFile=fromFile):
        #     plat_name = platform.get("name") or ""
        #     countries = platform.get("countries") or ""
        #     for prod in platform.get("products") or []:
        #         products[prod.get("product_code") or ""] = {
        #             "name": " ".join([plat_name, prod.get("name")]),
        #             "platform": plat_name,
        #             "countries": countries,
        #             # "img_url": prod.get("img_url"),
        #         }
        return products

    async def get_currency_list(self, fromFile: bool = False) -> dict:
        r"""Get the currency list for the power sites.

        Example data:
        "data": {"currency_list": [
            {"symbol": "$","name": "USD"},
            {"symbol": "\u20ac","name": "EUR"},
            {"symbol": "z\u0142","name": "PLN"}],
            "default_currency": {"symbol": "\u20ac","name": "EUR"}}
        """
        if fromFile:
            resp = await self.apisession.loadFromFile(
                Path(self.testDir()) / f"{API_FILEPREFIXES['get_currency_list']}.json"
            )
        else:
            resp = await self.apisession.request(
                "post", API_ENDPOINTS["get_currency_list"]
            )
        return resp.get("data") or {}
