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

from .apitypes import API_ENDPOINTS, API_FILEPREFIXES, SolixDeviceType
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
        self._testdir: str = self.apisession.testDir()
        self._logger: logging.Logger = self.apisession.logger()

        # track active devices bound to any site
        self._site_devices: set = set()
        # reset class variables for saving the most recent account, site and device data (Api cache)
        self.account: dict = {}
        self.sites: dict = {}
        self.devices: dict = {}

    def testDir(self, subfolder: str | None = None) -> str:
        """Get or set the subfolder for local API test files."""
        if subfolder is not None:
            self._testdir = self.apisession.testDir(subfolder)
        return self._testdir

    def logLevel(self, level: int | None = None) -> int:
        """Get or set the logger log level."""
        if level is not None and isinstance(level, int):
            self._logger.setLevel(level)
            self._logger.info("Set log level to: %s", level)
        return self._logger.getEffectiveLevel()

    def _update_account(  # noqa: C901
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
            not (
                account_details := self.account.get(SolixDeviceType.ACCOUNT.value) or {}
            )
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
        self.account[SolixDeviceType.ACCOUNT.value] = account_details

    def _update_site(  # noqa: C901
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

    def _update_dev(  # noqa: C901
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
        """Create/Update api sites cache structure.

        Implement this method to get the latest info for all accessible sites or only the provided siteId and update class cache dictionaries.
        """
        if siteId and (self.sites.get(siteId) or {}):
            # update only the provided site ID
            self._logger.debug("Updating Sites data for site ID %s", siteId)
            new_sites = self.sites
            # prepare the site list dictionary for the update loop by copying the requested site from the cache
            sites: dict = {"site_list": [self.sites[siteId].get("site_info") or {}]}
        else:
            # run normal refresh for all sites
            self._logger.debug("Updating Sites data")
            new_sites = {}
            self._logger.debug("Getting site list")
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
                self._logger.debug("Getting scene info for site")
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
        self._logger.debug("Updating Sites Details")
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
            self._logger.debug("Getting Energy details for site")
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
        self._logger.debug("Updating Device Details")
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
                Path(self._testdir) / f"{API_FILEPREFIXES['site_rules']}.json"
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
                Path(self._testdir) / f"{API_FILEPREFIXES['site_list']}.json"
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
                Path(self._testdir) / f"{API_FILEPREFIXES['scene_info']}_{siteId}.json"
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
                Path(self._testdir) / f"{API_FILEPREFIXES['bind_devices']}.json"
            )
        else:
            resp = await self.apisession.request("post", API_ENDPOINTS["bind_devices"])
        data = resp.get("data") or {}
        active_devices = set()
        for device in data.get("data") or []:
            if sn := self._update_dev(device):
                active_devices.add(sn)
        # recycle api device list and remove devices no longer used in sites or bind devices
        rem_devices = [
            dev
            for dev in self.devices
            if dev not in (self._site_devices | active_devices)
        ]
        for dev in rem_devices:
            self.devices.pop(dev, None)
        return data

    async def get_auto_upgrade(self, fromFile: bool = False) -> dict:
        """Get auto upgrade settings and devices enabled for auto upgrade.

        Example data:
        {'main_switch': True, 'device_list': [{'device_sn': '9JVB42LJK8J0P5RY', 'device_name': 'Solarbank E1600', 'auto_upgrade': True, 'alias_name': 'Solarbank E1600',
        'icon': 'https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/e9478c2d-e665-4d84-95d7-dd4844f82055/20230719-144818.png'}]}
        """
        if fromFile:
            resp = await self.apisession.loadFromFile(
                Path(self._testdir) / f"{API_FILEPREFIXES['get_auto_upgrade']}.json"
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
                Path(self._testdir) / f"{API_FILEPREFIXES['wifi_list']}_{siteId}.json"
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
        return resp.get("data") or {}

    async def get_ota_batch(
        self, deviceSns: list | None = None, fromFile: bool = False
    ) -> dict:
        """Get the OTA info for provided list of device serials or for all owning devices in devices dict.

        Example data:
        {"update_infos": [{"device_sn": "9JVB42LJK8J0P5RY","need_update": false,"upgrade_type": 0,"lastPackage": {
                "product_code": "","product_component": "","version": "","is_forced": false,"md5": "","url": "","size": 0},
            "change_log": "","current_version": "v1.6.3","children": null}]}
        """
        # default to all admin devices in devices dict if no device serial list provided
        if not deviceSns or not isinstance(deviceSns, list):
            deviceSns = [
                s for s, device in self.devices.items() if device.get("is_admin")
            ]
        if fromFile:
            resp = await self.apisession.loadFromFile(
                Path(self._testdir) / f"{API_FILEPREFIXES['get_ota_batch']}.json"
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
                    self._update_dev(
                        {
                            "device_sn": deviceSn,
                            "is_ota_update": dev.get("need_update"),
                            "ota_version": (dev.get("lastPackage") or {}).get("version")
                            or dev.get("current_version")
                            or "",
                        }
                    )
        return resp.get("data") or {}

    async def get_message_unread(self, fromFile: bool = False) -> dict:
        """Get the unread messages for account.

        Example data:
        {"has_unread_msg": false}
        """
        if fromFile:
            resp = await self.apisession.loadFromFile(
                Path(self._testdir) / f"{API_FILEPREFIXES['get_message_unread']}.json"
            )
        else:
            resp = await self.apisession.request(
                "get", API_ENDPOINTS["get_message_unread"]
            )
        # TODO: Get rid of old method once new account dictionary was picked up by HA integration in a new Account device type
        # Old Method: save unread msg flag in each known site
        data = resp.get("data") or {}
        for siteId in self.sites:
            self._update_site(siteId, data)
        # New method: Save unread msg flag in account dictionary
        self._update_account(data)
        return data
