"""Class for exporting the power system data into json files with the provide Anker API instance.

You can specify a subfolder for the exported JSON files received as API query response, defaulting to the Api instance account nick name.
Optionally you can specify whether personalized information in the response data should be randomized in the files, like SNs, Site IDs, Trace IDs etc.
Optionally the export files will also be zipped.
They json files can be used as examples for dedicated data extraction from the Api responses.
Furthermore the API class can use the json files for debugging and testing of various system outputs.
"""

import asyncio
from collections.abc import Callable
from copy import deepcopy
from datetime import datetime, timedelta
from functools import partial
import json
import logging
import logging.handlers
from pathlib import Path
import queue
import random
import shutil
import string
from typing import Any

import aiofiles
from aiohttp.client_exceptions import ClientError

from . import api, errors
from .apitypes import (
    API_CHARGING_ENDPOINTS,
    API_ENDPOINTS,
    API_FILEPREFIXES,
    API_HES_SVC_ENDPOINTS,
    ApiEndpointServices,
)

_LOGGER: logging.Logger = logging.getLogger(__name__)
VERSION: str = "2.7.0.0"


class AnkerSolixApiExport:
    """Define the class to handle json export from Anker Solix api instance."""

    def __init__(
        self,
        client: api.AnkerSolixApi | api.AnkerSolixClientSession,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize."""

        # get the api client session from passed object
        if isinstance(client, api.AnkerSolixApi):
            self.client = client.apisession
        else:
            self.client = client
        # create new api instance with client session
        self.api_power = api.AnkerSolixApi(apisession=self.client)
        self.export_path: str | None = None
        self.export_folder: str | None = None
        self.export_services: set | None = None
        self.randomized: bool = True
        self.zipped: bool = True
        self.zipfilename: str | None = None
        self.request_delay: float | None = None
        self._randomdata: dict = {}

        # initialize logger for object
        if logger:
            self._logger = logger
        else:
            self._logger = _LOGGER
            self._logger.setLevel(logging.DEBUG)

    async def export_data(
        self,
        export_path: Path | str | None = None,
        export_folder: Path | str | None = None,
        export_services: set | None = None,
        request_delay: float | None = None,
        randomized: bool = True,
        zipped: bool = True,
        toggle_cache: Callable | None = None,
    ) -> bool:
        """Run main function to export account data."""

        if not export_path:
            # default to exports self.export_path in parent path of api library
            self.export_path = Path(__file__).parent / ".." / "exports"
        else:
            self.export_path = Path(export_path)
        if not export_folder:
            self.export_folder = None
        else:
            self.export_folder = Path(export_folder)
        if export_services and isinstance(export_services, set):
            self.export_services = export_services
        else:
            # use empty set to export only endpoint services depending on discovered site types
            self.export_services: set = set()
            # self.export_services: set = set(asdict(ApiEndpointServices()).values())
        self.request_delay = (
            request_delay
            if isinstance(request_delay, int | float)
            else self.client.requestDelay()
        )
        self.randomized = randomized if isinstance(randomized, bool) else True
        self.zipped = zipped if isinstance(randomized, bool) else True
        toggle_cache = toggle_cache if callable(toggle_cache) else None
        self._randomdata = {}

        # ensure nickname is set for api client
        await self.client.async_authenticate()
        if not self.export_folder:
            if not self.client.nickname:
                return False
            # avoid filesystem problems with * in user nicknames
            self.export_folder = self.client.nickname.replace("*", "x")
        # complete path and ensure parent self.export_path for export exists
        self.export_path: Path = Path.resolve(
            Path(self.export_path) / self.export_folder
        )
        try:
            # clear export folder if it exists already
            if self.export_path.exists():
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, shutil.rmtree, self.export_path)
                # shutil.rmtree(self.export_path)
            Path(self.export_path).mkdir(parents=True, exist_ok=True)
        except OSError as err:
            self._logger.error(
                "Unable to clear or create export folder %s: %s", self.export_path, err
            )
            return False

        self._logger.info(
            "Exporting Anker Solix data for all account sites and devices of api nickname %s",
            self.client.nickname,
        )
        try:
            # create a queue for async file logging
            que = queue.Queue()
            # add a handler that uses the logs to queue at DEBUG level, independent of other logger handler setting
            qh = logging.handlers.QueueHandler(que)
            qh.setFormatter(
                logging.Formatter(
                    fmt="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
                    datefmt="%H:%M:%S",
                )
            )
            qh.setLevel(logging.DEBUG)
            # add queue handler to logger
            self._logger.addHandler(qh)
            # create file handler for async file logging from the queue
            loop = asyncio.get_running_loop()
            fh = await loop.run_in_executor(
                None,
                partial(
                    logging.FileHandler,
                    filename=Path(self.export_path) / "export.log",
                ),
            )
            # create a listener for messages on the queue and log them to the file handler
            listener = logging.handlers.QueueListener(que, fh)
            # start the listener
            listener.start()

            self._logger.info(
                "Using AnkerSolixApiExport Version: %s, Date: %s, Export Services: %s",
                VERSION,
                datetime.now().strftime("%Y-%m-%d"),
                str(self.export_services),
            )

            # save existing api delay and adjust request delay for export
            if (old_delay := self.client.requestDelay()) != self.request_delay:
                self.client.requestDelay(self.request_delay)
                self._logger.debug(
                    "Saved api %s original request delay of %s seconds and modified delay to %s seconds.",
                    self.client.nickname,
                    old_delay,
                    self.request_delay,
                )

            # Export common data for all service types and skip rest on error
            if await self.export_common_data():
                # Export power_service endpoint data
                if {
                    ApiEndpointServices.power
                } & self.export_services or not self.export_services:
                    await self.export_power_service_data()

                # Export charging_energy_service endpoint data
                if {
                    ApiEndpointServices.charging
                } & self.export_services or not self.export_services:
                    await self.export_charging_energy_service_data()

                # Export charging_hes_svc endpoint data
                if {
                    ApiEndpointServices.hes_svc
                } & self.export_services or not self.export_services:
                    await self.export_charging_hes_svc_data()

                # update api dictionaries from exported files to use randomized input data
                # this is more efficient and allows validation of randomized data in export files
                # save real api cache data first
                old_account = deepcopy(self.api_power.account)
                old_sites = deepcopy(self.api_power.sites)
                old_devices = deepcopy(self.api_power.devices)
                old_testdir = self.api_power.testDir()
                # Notify optional callable that cache is toggled invalid
                if toggle_cache:
                    toggle_cache(False)
                self.api_power.testDir(self.export_path)
                self._logger.debug(
                    "Saved api %s original testfolder",
                    self.client.nickname,
                )
                await self.api_power.update_sites(fromFile=True)
                await self.api_power.update_device_details(fromFile=True)
                await self.api_power.update_site_details(fromFile=True)
                await self.api_power.update_device_energy(fromFile=True)
                self._logger.info("")
                self._logger.info(
                    "Exporting api %s sites cache from files...",
                    self.client.nickname,
                )
                self._logger.debug(
                    "Api %s sites cache --> %s",
                    self.client.nickname,
                    filename := f"{API_FILEPREFIXES['api_sites']}.json",
                )
                # avoid randomizing dictionary export twice when imported from randomized files already
                await self._export(
                    Path(self.export_path) / filename,
                    self.api_power.sites,
                    skip_randomize=True,
                )
                self._logger.info(
                    "Exporting api %s devices cache from files...",
                    self.client.nickname,
                )
                self._logger.debug(
                    "Api %s devices cache --> %s",
                    self.client.nickname,
                    filename := f"{API_FILEPREFIXES['api_devices']}.json",
                )
                # avoid randomizing dictionary export twice when imported from randomized files already
                await self._export(
                    Path(self.export_path) / filename,
                    self.api_power.devices,
                    skip_randomize=True,
                )
                # Always export account dictionary
                self._logger.info("")
                self._logger.info(
                    "Exporting api %s account cache...",
                    self.client.nickname,
                )
                self._logger.debug(
                    "Api %s account cache --> %s",
                    self.client.nickname,
                    filename := f"{API_FILEPREFIXES['api_account']}.json",
                )
                # update account dictionary with number of requests during export
                self.api_power._update_account()  # noqa: SLF001
                # Randomizing dictionary for account data
                await self._export(
                    Path(self.export_path) / filename,
                    self.api_power.account,
                )
                # Print stats
                self._logger.info(
                    "Api %s request stats: %s",
                    self.client.nickname,
                    self.client.request_count,
                )

                # restore real client cache data for re-use of sites and devices in other Api services
                self.api_power.account = old_account
                self.api_power.sites = old_sites
                self.api_power.devices = old_devices
                # skip restore of default test dir in client session since it may not exist
                if Path(old_testdir).is_dir() and old_testdir != self.export_path:
                    self.api_power.testDir(old_testdir)
                    self._logger.debug(
                        "Restored original test folder for api %s client session.",
                        self.client.nickname,
                    )
                # restore old api session delay
                if old_delay != self.request_delay:
                    self.client.requestDelay(old_delay)
                    self._logger.debug(
                        "Restored api %s original client request delay to %s seconds.",
                        self.client.nickname,
                        old_delay,
                    )
                # Notify optional callable that cache was restored
                if toggle_cache:
                    toggle_cache(True)

                # remove queue file handler again before zipping folder
                self._logger.removeHandler(qh)
                self._logger.info("")
                self._logger.info(
                    "Completed export of Anker Solix systems data for api %s",
                    self.client.nickname,
                )
                if self.randomized:
                    self._logger.info(
                        "Folder %s contains the randomized JSON files. Pls check and update fields that may contain unrecognized personalized data.",
                        self.export_path,
                    )
                else:
                    self._logger.warning(
                        "Folder %s contains the JSON files with personalized data.",
                        self.export_path,
                    )

                # Optionally zip the output
                if self.zipped:
                    zipname = "_".join(
                        [
                            str(self.export_path),
                            datetime.now().strftime("%Y-%m-%d_%H%M"),
                        ]
                    )
                    self.zipfilename = zipname + ".zip"
                    self._logger.info("")
                    self._logger.info("Zipping output folder to %s", self.zipfilename)
                    loop = asyncio.get_running_loop()

                    self._logger.info(
                        "Zipfile created: %s",
                        await loop.run_in_executor(
                            None,
                            partial(
                                shutil.make_archive,
                                base_name=zipname,
                                format="zip",
                                root_dir=Path(self.export_path).parent,
                                base_dir=Path(self.export_path).name,
                            ),
                        ),
                    )
                else:
                    self.zipfilename = None

        except errors.AnkerSolixError as err:
            self._logger.error("%s: %s", type(err), err)
            # ensure the listener is closed
            listener.stop()
            return False
        else:
            # ensure the listener is closed
            listener.stop()
            return True

    async def export_common_data(self) -> bool:
        """Run functions to export common data."""

        self._logger.info("")
        self._logger.info("Querying common endpoint data...")
        # first update Api caches if still empty
        if not self.api_power.sites | self.api_power.devices:
            self._logger.info("Querying site information...")
            await self.api_power.update_sites()
            # Run bind devices to get also standalone devices for data export
            self._logger.info("Querying bind devices information...")
            await self.api_power.get_bind_devices()
        self._logger.info(
            "Found %s accessible systems (sites) and %s devices.",
            len(self.api_power.sites),
            len(self.api_power.devices),
        )

        # Query API using direct endpoints to save full response of each query in json files
        try:
            self._logger.info("Exporting site list...")
            await self.query(
                endpoint=API_ENDPOINTS["site_list"],
                filename=f"{API_FILEPREFIXES['site_list']}.json",
                catch=False,
            )
            self._logger.info("Exporting bind devices...")
            # shows only owner devices
            await self.query(
                endpoint=API_ENDPOINTS["bind_devices"],
                filename=f"{API_FILEPREFIXES['bind_devices']}.json",
                catch=False,
            )
            # Single OTA batch query for all devices, provides responses for owning devices only
            self._logger.info("Exporting OTA batch info for all devices...")
            await self.query(
                endpoint=API_ENDPOINTS["get_ota_batch"],
                filename=f"{API_FILEPREFIXES['get_ota_batch']}.json",
                payload={
                    "device_list": [
                        {"device_sn": serial, "version": ""}
                        for serial in self.api_power.devices
                    ]
                },
                replace=[
                    (serial, f"<deviceSn{idx + 1}>")
                    for idx, serial in enumerate(self.api_power.devices.keys())
                ],
                catch=False,
            )
            self._logger.info("Exporting message unread status...")
            await self.query(
                method="get",
                endpoint=API_ENDPOINTS["get_message_unread"],
                filename=f"{API_FILEPREFIXES['get_message_unread']}.json",
            )
            self._logger.info("Exporting currency list...")
            await self.query(
                method="post",
                endpoint=API_ENDPOINTS["get_currency_list"],
                filename=f"{API_FILEPREFIXES['get_currency_list']}.json",
            )
            self._logger.info("Exporting supported sites, devices and accessories...")
            await self.query(
                endpoint=API_ENDPOINTS["site_rules"],
                filename=f"{API_FILEPREFIXES['site_rules']}.json",
            )
            await self.query(
                method="get",
                endpoint=API_ENDPOINTS["get_product_categories"],
                filename=f"{API_FILEPREFIXES['get_product_categories']}.json",
            )
            await self.query(
                method="get",
                endpoint=API_ENDPOINTS["get_product_accessories"],
                filename=f"{API_FILEPREFIXES['get_product_accessories']}.json",
            )
            await self.query(
                endpoint=API_ENDPOINTS["get_third_platforms"],
                filename=f"{API_FILEPREFIXES['get_third_platforms']}.json",
            )
            # loop through all found sites
            for siteId in self.api_power.sites:
                self._logger.info("Exporting scene info...")
                await self.query(
                    endpoint=API_ENDPOINTS["scene_info"],
                    filename=f"{API_FILEPREFIXES['scene_info']}_{self._randomize(siteId, 'site_id')}.json",
                    payload={"site_id": siteId},
                    replace=[(siteId, "<siteId>")],
                )

        except (errors.AnkerSolixError, ClientError) as err:
            if isinstance(err, ClientError):
                self._logger.warning(
                    "Connection problems or common endpoint data queries may not be supported on used server: %s",
                    err,
                )
            else:
                self._logger.error("%s: %s", type(err), err)
            self._logger.warning(
                "Skipping remaining data queries.",
            )
            return False
        return True

    async def export_power_service_data(self) -> bool:
        """Run functions to export power_service endpoint data."""

        self._logger.info("")
        self._logger.info("Querying %s endpoint data...", ApiEndpointServices.power)
        # Query API using direct endpoints to save full response of each query in json files
        try:
            self._logger.info("")
            self._logger.info("Exporting homepage...")
            await self.query(
                endpoint=API_ENDPOINTS["homepage"],
                filename=f"{API_FILEPREFIXES['homepage']}.json",
                catch=False,
            )
            self._logger.info("Exporting user devices...")
            # shows only owner devices
            await self.query(
                endpoint=API_ENDPOINTS["user_devices"],
                filename=f"{API_FILEPREFIXES['user_devices']}.json",
            )
            self._logger.info("Exporting charging devices...")
            # shows only owner devices
            await self.query(
                endpoint=API_ENDPOINTS["charging_devices"],
                filename=f"{API_FILEPREFIXES['charging_devices']}.json",
            )
            self._logger.info("Exporting auto upgrade settings...")
            # shows only owner devices
            await self.query(
                endpoint=API_ENDPOINTS["get_auto_upgrade"],
                filename=f"{API_FILEPREFIXES['get_auto_upgrade']}.json",
            )
            self._logger.info("Exporting config...")
            await self.query(
                endpoint=API_ENDPOINTS["get_config"],
                filename=f"{API_FILEPREFIXES['get_config']}.json",
            )
            self._logger.info("Get token for user account...")
            response = await self.query(
                endpoint=API_ENDPOINTS["get_token_by_userid"],
                filename=f"{API_FILEPREFIXES['get_token_by_userid']}.json",
            )
            self._logger.info("Get Shelly status with token...")
            await self.query(
                endpoint=API_ENDPOINTS["get_shelly_status"],
                filename=f"{API_FILEPREFIXES['get_shelly_status']}.json",
                # use real token from previous response for query
                payload={"token": (response or {}).get("data", {}).get("token", "")},
            )

            # loop through all found sites
            for siteId, site in self.api_power.sites.items():
                self._logger.info("")
                self._logger.info(
                    "Exporting site specific data for site %s...",
                    self._randomize(siteId, "site_id"),
                )
                admin = site.get("site_admin")
                self._logger.info("Exporting site detail...")
                # works only for site owners
                await self.query(
                    endpoint=API_ENDPOINTS["site_detail"],
                    filename=f"{API_FILEPREFIXES['site_detail']}_{self._randomize(siteId, 'site_id')}.json",
                    payload={"site_id": siteId},
                    replace=[(siteId, "<siteId>")],
                    admin=admin,
                )
                self._logger.info("Exporting wifi list...")
                # works only for site owners
                await self.query(
                    endpoint=API_ENDPOINTS["wifi_list"],
                    filename=f"{API_FILEPREFIXES['wifi_list']}_{self._randomize(siteId, 'site_id')}.json",
                    payload={"site_id": siteId},
                    replace=[(siteId, "<siteId>")],
                    admin=admin,
                )
                self._logger.info("Exporting installation...")
                await self.query(
                    endpoint=API_ENDPOINTS["get_installation"],
                    filename=f"{API_FILEPREFIXES['get_installation']}_{self._randomize(siteId, 'site_id')}.json",
                    payload={"site_id": siteId},
                    replace=[(siteId, "<siteId>")],
                )
                self._logger.info("Exporting site price...")
                # works only for site owners
                await self.query(
                    endpoint=API_ENDPOINTS["get_site_price"],
                    filename=f"{API_FILEPREFIXES['get_site_price']}_{self._randomize(siteId, 'site_id')}.json",
                    payload={"site_id": siteId},
                    replace=[(siteId, "<siteId>")],
                    admin=admin,
                )

                for parmtype in ["4", "6", "9", "12", "13"]:
                    self._logger.info(
                        "Exporting device parameter type %s settings...", parmtype
                    )
                    # works only for site owners
                    await self.query(
                        endpoint=API_ENDPOINTS["get_device_parm"],
                        filename=f"{API_FILEPREFIXES['get_device_parm']}_{parmtype}_{self._randomize(siteId, 'site_id')}.json",
                        payload={"site_id": siteId, "param_type": parmtype},
                        replace=[(siteId, "<siteId>")],
                        admin=admin,
                    )
                # exporting various energy stats for power sites
                for stat_type in [
                    "solarbank",
                    "solar_production",
                    "home_usage",
                    "grid",
                ]:
                    self._logger.info(
                        "Exporting site energy data for %s...",
                        stat_type.upper(),
                    )
                    await self.query(
                        endpoint=API_ENDPOINTS["energy_analysis"],
                        filename=f"{API_FILEPREFIXES['energy_' + stat_type]}_{self._randomize(siteId, 'site_id')}.json",
                        payload={
                            "site_id": siteId,
                            "device_sn": "",
                            "type": "week",
                            "device_type": stat_type,
                            "start_time": (
                                datetime.today() - timedelta(days=1)
                            ).strftime("%Y-%m-%d"),
                            "end_time": datetime.today().strftime("%Y-%m-%d"),
                        },
                        replace=[(siteId, "<siteId>")],
                    )
                for ch in ["pv" + str(num) for num in range(1, 5)] + ["microinverter"]:
                    self._logger.info(
                        "Exporting site energy data for solar production channel %s...",
                        ch.upper(),
                    )
                    response = await self.query(
                        endpoint=API_ENDPOINTS["energy_analysis"],
                        filename=f"{API_FILEPREFIXES['energy_solar_production']}_{ch}_{self._randomize(siteId, 'site_id')}.json",
                        payload={
                            "site_id": siteId,
                            "device_sn": "",
                            "type": "week",
                            "device_type": f"solar_production_{ch}",
                            "start_time": (
                                datetime.today() - timedelta(days=1)
                            ).strftime("%Y-%m-%d"),
                            "end_time": datetime.today().strftime("%Y-%m-%d"),
                        },
                        replace=[(siteId, "<siteId>")],
                    )
                    if not isinstance(response, dict) or not response.get("data"):
                        self._logger.warning(
                            "No solar production energy available for channel %s, skipping remaining solar channel export...",
                            ch.upper(),
                        )
                        break

            # loop through all devices for other queries
            for sn, device in self.api_power.devices.items():
                self._logger.info("")
                self._logger.info(
                    "Exporting device specific data for device %s SN %s...",
                    device.get("name", ""),
                    self._randomize(sn, "_sn"),
                )
                siteId = device.get("site_id", "")
                admin = device.get("is_admin")

                if device.get("type") == api.SolixDeviceType.SOLARBANK.value:
                    self._logger.info("Exporting solar info settings for solarbank...")
                    await self.query(
                        endpoint=API_ENDPOINTS["solar_info"],
                        filename=f"{API_FILEPREFIXES['solar_info']}_{self._randomize(sn, '_sn')}.json",
                        payload={"solarbank_sn": sn},
                        replace=[(siteId, "<siteId>"), (sn, "<deviceSn>")],
                    )
                    self._logger.info(
                        "Exporting compatible process info for solarbank..."
                    )
                    await self.query(
                        endpoint=API_ENDPOINTS["compatible_process"],
                        filename=f"{API_FILEPREFIXES['compatible_process']}_{self._randomize(sn, '_sn')}.json",
                        payload={"solarbank_sn": sn},
                        replace=[(siteId, "<siteId>"), (sn, "<deviceSn>")],
                    )

                self._logger.info("Exporting power cutoff settings...")
                # works only for site owners
                await self.query(
                    endpoint=API_ENDPOINTS["get_cutoff"],
                    filename=f"{API_FILEPREFIXES['get_cutoff']}_{self._randomize(sn, '_sn')}.json",
                    payload={"site_id": siteId, "device_sn": sn},
                    replace=[(siteId, "<siteId>"), (sn, "<deviceSn>")],
                    admin=admin,
                )
                self._logger.info("Exporting fittings...")
                # works only for site owners
                await self.query(
                    endpoint=API_ENDPOINTS["get_device_fittings"],
                    filename=f"{API_FILEPREFIXES['get_device_fittings']}_{self._randomize(sn, '_sn')}.json",
                    payload={"site_id": siteId, "device_sn": sn},
                    replace=[(siteId, "<siteId>"), (sn, "<deviceSn>")],
                    admin=admin,
                )
                self._logger.info("Exporting load...")
                # works only for site owners
                await self.query(
                    endpoint=API_ENDPOINTS["get_device_load"],
                    filename=f"{API_FILEPREFIXES['get_device_load']}_{self._randomize(sn, '_sn')}.json",
                    payload={"site_id": siteId, "device_sn": sn},
                    replace=[(siteId, "<siteId>"), (sn, "<deviceSn>")],
                    admin=admin,
                )
                # This query does not work for most devices, device firmware data is covered with a single ota_batch query
                # self._logger.info("Exporting OTA update info for device...")
                # await self.query(
                #     endpoint=API_ENDPOINTS["get_ota_update"],
                #     filename=f"{API_FILEPREFIXES['get_ota_update']}_{self._randomize(sn,'_sn')}.json",
                #     payload={"device_sn": sn, "insert_sn": ""},
                #     replace=[(siteId, "<siteId>"), (sn, "<deviceSn>")],
                #     admin=admin,
                # )
                self._logger.info("Exporting upgrade record for device...")
                await self.query(
                    endpoint=API_ENDPOINTS["get_upgrade_record"],
                    filename=f"{API_FILEPREFIXES['get_upgrade_record']}_1_{self._randomize(sn, '_sn')}.json",
                    payload={"device_sn": sn, "type": 1},
                    replace=[(siteId, "<siteId>"), (sn, "<deviceSn>")],
                )
                self._logger.info("Exporting device attributes...")
                await self.query(
                    endpoint=API_ENDPOINTS["get_device_attributes"],
                    filename=f"{API_FILEPREFIXES['get_device_attributes']}_{self._randomize(sn, '_sn')}.json",
                    # TODO: Empty attributes list will not list any attributes, possible attributes and devices are unknown yet
                    # Only rssi delivered response value so far, test further possible attributes on queries with various devices
                    payload={
                        "device_sn": sn,
                        "attributes": [
                            "rssi",
                            "temperature",
                            "battery_cycles",
                            "state_of_health",
                            "status",
                            "wifi_signal",
                            "switch",
                            "ssid",
                            "led",
                            "micro_inverter_power_limit",
                        ],
                    },
                    replace=[(siteId, "<siteId>"), (sn, "<deviceSn>")],
                    admin=admin,
                )

                # export device pv status and statistics for inverters
                if device.get("type") == api.SolixDeviceType.INVERTER.value:
                    self._logger.info(
                        "Exporting inverter specific data for device %s SN %s...",
                        device.get("name", ""),
                        self._randomize(sn, "_sn"),
                    )
                    await self.query(
                        endpoint=API_ENDPOINTS["get_device_pv_status"],
                        filename=f"{API_FILEPREFIXES['get_device_pv_status']}_{self._randomize(sn, '_sn')}.json",
                        payload={"sns": sn},
                        replace=[(sn, "<deviceSn>")],
                    )
                    await self.query(
                        endpoint=API_ENDPOINTS["get_device_pv_total_statistics"],
                        filename=f"{API_FILEPREFIXES['get_device_pv_total_statistics']}_{self._randomize(sn, '_sn')}.json",
                        payload={"sn": sn},
                        replace=[(sn, "<deviceSn>")],
                    )
                    await self.query(
                        endpoint=API_ENDPOINTS["get_device_pv_price"],
                        filename=f"{API_FILEPREFIXES['get_device_pv_price']}_{self._randomize(sn, '_sn')}.json",
                        payload={"sn": sn},
                        replace=[(sn, "<deviceSn>")],
                    )
                    self._logger.info(
                        "Exporting inverter energy data for device %s SN %s...",
                        device.get("name", ""),
                        self._randomize(sn, "_sn"),
                    )
                    # inverter energy statistic
                    await self.query(
                        endpoint=API_ENDPOINTS["get_device_pv_statistics"],
                        filename=f"{API_FILEPREFIXES['get_device_pv_statistics']}_today_{self._randomize(sn, '_sn')}.json",
                        payload={
                            "sn": sn,
                            "type": "day",
                            "start": datetime.today().strftime("%Y-%m-%d"),
                            "end": "",
                            "version": "1",
                        },
                        replace=[(sn, "<deviceSn>")],
                    )
                    await self.query(
                        endpoint=API_ENDPOINTS["get_device_pv_statistics"],
                        filename=f"{API_FILEPREFIXES['get_device_pv_statistics']}_{self._randomize(sn, '_sn')}.json",
                        payload={
                            "sn": sn,
                            "type": "week",
                            "start": (datetime.today() - timedelta(days=1)).strftime(
                                "%Y-%m-%d"
                            ),
                            "end": datetime.today().strftime("%Y-%m-%d"),
                            "version": "1",
                        },
                        replace=[(sn, "<deviceSn>")],
                    )

        except (errors.AnkerSolixError, ClientError) as err:
            if isinstance(err, ClientError):
                self._logger.warning(
                    "%s endpoint data queries may not be supported on used server: %s",
                    ApiEndpointServices.power,
                    err,
                )
            else:
                self._logger.error("%s: %s", type(err), err)
            self._logger.warning(
                "Skipping remaining %s endpoint data queries.",
                ApiEndpointServices.power,
            )
            return False
        return True

    async def export_charging_energy_service_data(self) -> bool:
        """Run functions to export charging_energy_service endpoint data."""

        self._logger.info("")
        self._logger.info("Querying %s endpoint data...", ApiEndpointServices.charging)
        # Query API using direct endpoints to save full response of each query in json files
        try:
            # Use simple first query without parms to check if service endpoints usable
            self._logger.info("Exporting Charging error info...")
            await self.query(
                endpoint=API_CHARGING_ENDPOINTS["get_error_info"],
                filename=f"{API_FILEPREFIXES['charging_get_error_info']}.json",
                catch=False,
            )

            has_charging = False
            # loop through all found sites
            for siteId, site in self.api_power.sites.items():
                admin = site.get("site_admin")
                self._logger.info("")
                self._logger.info(
                    "Exporting Charging specific data for site %s...",
                    self._randomize(siteId, "site_id"),
                )

                self._logger.info("Exporting Charging system running info...")
                await self.query(
                    endpoint=API_CHARGING_ENDPOINTS["get_system_running_info"],
                    filename=f"{API_FILEPREFIXES['charging_get_system_running_info']}_{self._randomize(siteId, 'site_id')}.json",
                    payload={"siteId": siteId},
                    replace=[(siteId, "<siteId>")],
                    randomkeys=True,
                )
                # check if valid charging data available for site and skip if not enforced
                if not (
                    is_charging := len(site.get("powerpanel_list") or []) > 0
                ) and not self.export_services & {ApiEndpointServices.charging}:
                    self._logger.info(
                        "No system for %s endpoint data found, skipping remaining site queries...",
                        ApiEndpointServices.charging,
                    )
                    continue

                if is_charging:
                    has_charging = True

                # get various daily energies since yesterday
                for stat_type in ["solar", "hes", "pps", "home", "grid", "diesel"]:
                    self._logger.info(
                        "Exporting Charging site energy data for %s...",
                        stat_type.upper(),
                    )
                    await self.query(
                        endpoint=API_CHARGING_ENDPOINTS["energy_statistics"],
                        filename=f"{API_FILEPREFIXES['charging_energy_' + stat_type]}_{self._randomize(siteId, 'site_id')}.json",
                        payload={
                            "siteId": siteId,
                            "sourceType": stat_type,
                            "dateType": "week",
                            "start": (datetime.today() - timedelta(days=1)).strftime(
                                "%Y-%m-%d"
                            ),
                            "end": datetime.today().strftime("%Y-%m-%d"),
                            "global": False,
                            "productCode": "",
                        },
                        replace=[(siteId, "<siteId>")],
                    )

                # get various energies of today for last 5 min average values
                for stat_type in ["solar", "hes", "home", "grid", "diesel"]:
                    self._logger.info(
                        "Exporting Charging site energy data of today for %s...",
                        stat_type.upper(),
                    )
                    await self.query(
                        endpoint=API_CHARGING_ENDPOINTS["energy_statistics"],
                        filename=f"{API_FILEPREFIXES['charging_energy_' + stat_type + '_today']}_{self._randomize(siteId, 'site_id')}.json",
                        payload={
                            "siteId": siteId,
                            "sourceType": stat_type,
                            "dateType": "day",
                            "start": datetime.today().strftime("%Y-%m-%d"),
                            "end": datetime.today().strftime("%Y-%m-%d"),
                            "global": False,
                            "productCode": "",
                        },
                        replace=[(siteId, "<siteId>")],
                    )

                self._logger.info("Exporting Charging site device data report...")
                # check all control options
                for ctrol in [0, 1]:
                    await self.query(
                        endpoint=API_CHARGING_ENDPOINTS["report_device_data"],
                        filename=f"{API_FILEPREFIXES['charging_report_device_data']}_{ctrol}_{self._randomize(siteId, 'site_id')}.json",
                        payload={"siteIds": [siteId], "ctrol": ctrol, "duration": 300},
                        replace=[(siteId, "<siteId>")],
                    )

            # skip device queries if no charging system found and charging not enforced
            if not has_charging and not self.export_services & {
                ApiEndpointServices.charging
            }:
                self._logger.info(
                    "No system for %s endpoint data found, skipping device queries...",
                    ApiEndpointServices.charging,
                )
                return True

            # loop through all devices
            for sn, device in self.api_power.devices.items():
                self._logger.info("")
                self._logger.info(
                    "Exporting Charging specific data for device %s SN %s...",
                    device.get("name", ""),
                    self._randomize(sn, "_sn"),
                )
                siteId = device.get("site_id", "")
                admin = device.get("is_admin")

                # run only for main power panel devices for site owner
                if (
                    dev_type := device.get("type")
                ) == api.SolixDeviceType.POWERPANEL.value:
                    self._logger.info("Exporting %s monetary units...", dev_type)
                    # works only for site owners
                    await self.query(
                        endpoint=API_CHARGING_ENDPOINTS["get_monetary_units"],
                        filename=f"{API_FILEPREFIXES['charging_get_monetary_units']}_{self._randomize(sn, '_sn')}.json",
                        payload={"siteId": siteId, "sn": sn},
                        replace=[(siteId, "<siteId>"), (sn, "<deviceSn>")],
                        admin=admin,
                    )
                    self._logger.info("Exporting %s configs...", dev_type)
                    # works only for site owners
                    await self.query(
                        endpoint=API_CHARGING_ENDPOINTS["get_configs"],
                        filename=f"{API_FILEPREFIXES['charging_get_configs']}_{self._randomize(sn, '_sn')}.json",
                        payload={
                            "siteId": siteId,
                            "sn": sn,
                            "param_types": ["hes", "home", "grid"],
                        },  # TODO: supported types unknown
                        replace=[(siteId, "<siteId>"), (sn, "<deviceSn>")],
                        admin=admin,
                    )
                    self._logger.info("Exporting %s utility rate plan...", dev_type)
                    # works only for site owners
                    await self.query(
                        endpoint=API_CHARGING_ENDPOINTS["get_utility_rate_plan"],
                        filename=f"{API_FILEPREFIXES['charging_get_utility_rate_plan']}_{self._randomize(sn, '_sn')}.json",
                        payload={
                            "siteId": siteId,
                            "sn": sn,
                        },  # TODO: required parameters unknown
                        replace=[(siteId, "<siteId>"), (sn, "<deviceSn>")],
                        admin=admin,
                    )
                    self._logger.info("Exporting %s info...", dev_type)
                    # works only for site owners
                    await self.query(
                        endpoint=API_CHARGING_ENDPOINTS["get_device_info"],
                        filename=f"{API_FILEPREFIXES['charging_get_device_info']}_{self._randomize(sn, '_sn')}.json",
                        payload={"siteId": siteId, "sns": [sn]},
                        replace=[(siteId, "<siteId>"), (sn, "<deviceSn>")],
                        admin=admin,
                    )

                # run for power panel or pps devices for site owner
                if dev_type in [
                    api.SolixDeviceType.POWERPANEL.value,
                    api.SolixDeviceType.PPS.value,
                ]:
                    self._logger.info("Exporting %s wifi info...", dev_type)
                    # works only for site owners
                    await self.query(
                        endpoint=API_CHARGING_ENDPOINTS["get_wifi_info"],
                        filename=f"{API_FILEPREFIXES['charging_get_wifi_info']}_{self._randomize(sn, '_sn')}.json",
                        payload={"sn": sn},
                        replace=[(siteId, "<siteId>"), (sn, "<deviceSn>")],
                        admin=admin,
                    )
                    self._logger.info(
                        "Exporting %s installation inspection...", dev_type
                    )
                    # works only for site owners
                    await self.query(
                        endpoint=API_CHARGING_ENDPOINTS["get_installation_inspection"],
                        filename=f"{API_FILEPREFIXES['charging_get_installation_inspection']}_{self._randomize(sn, '_sn')}.json",
                        payload={"sn": sn},
                        replace=[(siteId, "<siteId>"), (sn, "<deviceSn>")],
                        admin=admin,
                    )

        except (errors.AnkerSolixError, ClientError) as err:
            if isinstance(err, ClientError):
                self._logger.warning(
                    "%s endpoint data queries may not be supported on used server: %s",
                    ApiEndpointServices.charging,
                    err,
                )
            else:
                self._logger.error("%s: %s", type(err), err)
            self._logger.warning(
                "Skipping remaining %s endpoint data queries.",
                ApiEndpointServices.charging,
            )
            return False
        return True

    async def export_charging_hes_svc_data(self) -> bool:
        """Run functions to export charging_hes_svc endpoint data."""

        self._logger.info("")
        self._logger.info("Querying %s endpoint data...", ApiEndpointServices.hes_svc)
        # Query API using direct endpoints to save full response of each query in json files
        try:
            # Use simple first query without parms to check if service endpoints usable
            self._logger.info("Exporting HES product info...")
            await self.query(
                endpoint=API_HES_SVC_ENDPOINTS["get_product_info"],
                filename=f"{API_FILEPREFIXES['hes_get_product_info']}.json",
                catch=False,
            )

            # loop through all found sites and check if hes site types available
            has_hes = False
            for siteId, site in self.api_power.sites.items():
                admin = site.get("site_admin")
                self._logger.info("")
                self._logger.info(
                    "Exporting HES specific data for site %s...",
                    self._randomize(siteId, "site_id"),
                )

                self._logger.info("Exporting HES system running info...")
                response = await self.query(
                    endpoint=API_HES_SVC_ENDPOINTS["get_system_running_info"],
                    filename=f"{API_FILEPREFIXES['hes_get_system_running_info']}_{self._randomize(siteId, 'site_id')}.json",
                    payload={"siteId": siteId},
                    replace=[(siteId, "<siteId>")],
                )
                # check if valid HES data available for site and skip if not enforced
                if not (
                    is_hes := isinstance(response, dict)
                    and ((response.get("data") or {}).get("mainSn") or None)
                ) and not self.export_services & {ApiEndpointServices.hes_svc}:
                    self._logger.info(
                        "No system for %s endpoint data found, skipping remaining site queries...",
                        ApiEndpointServices.hes_svc,
                    )
                    continue

                if is_hes:
                    has_hes = True
                self._logger.info("Exporting HES monetary units...")
                response = await self.query(
                    endpoint=API_HES_SVC_ENDPOINTS["get_monetary_units"],
                    filename=f"{API_FILEPREFIXES['hes_get_monetary_units']}_{self._randomize(siteId, 'site_id')}.json",
                    payload={"siteId": siteId},
                    replace=[(siteId, "<siteId>")],
                )
                # Following will show sensitive information and addresses
                # self._logger.info("Exporting HES install info...")
                # response = await self.query(
                #     endpoint=API_HES_SVC_ENDPOINTS["get_install_info"],
                #     filename=f"{API_FILEPREFIXES['hes_get_install_info']}_{self._randomize(siteId,'site_id')}.json",
                #     payload={"siteId": siteId},
                #     replace=[(siteId, "<siteId>")],
                # )

                # get various daily energies since yesterday
                for stat_type in ["solar", "hes", "home", "grid"]:
                    self._logger.info(
                        "Exporting HES site energy data for %s...",
                        stat_type.upper(),
                    )
                    await self.query(
                        endpoint=API_HES_SVC_ENDPOINTS["energy_statistics"],
                        filename=f"{API_FILEPREFIXES['hes_energy_' + stat_type]}_{self._randomize(siteId, 'site_id')}.json",
                        payload={
                            "siteId": siteId,
                            "sourceType": stat_type,
                            "dateType": "week",
                            "start": (datetime.today() - timedelta(days=1)).strftime(
                                "%Y-%m-%d"
                            ),
                            "end": datetime.today().strftime("%Y-%m-%d"),
                        },
                        replace=[(siteId, "<siteId>")],
                    )

                # get various energies of today for last 5 min average values
                for stat_type in ["solar", "hes", "home", "grid"]:
                    self._logger.info(
                        "Exporting HES site energy data of today for %s...",
                        stat_type.upper(),
                    )
                    await self.query(
                        endpoint=API_HES_SVC_ENDPOINTS["energy_statistics"],
                        filename=f"{API_FILEPREFIXES['hes_energy_' + stat_type + '_today']}_{self._randomize(siteId, 'site_id')}.json",
                        payload={
                            "siteId": siteId,
                            "sourceType": stat_type,
                            "dateType": "day",
                            "start": datetime.today().strftime("%Y-%m-%d"),
                            "end": datetime.today().strftime("%Y-%m-%d"),
                        },
                        replace=[(siteId, "<siteId>")],
                    )
                self._logger.info("Exporting HES device info...")
                response = await self.query(
                    endpoint=API_HES_SVC_ENDPOINTS["get_hes_dev_info"],
                    filename=f"{API_FILEPREFIXES['hes_get_hes_dev_info']}_{self._randomize(siteId, 'site_id')}.json",
                    payload={"siteId": siteId},
                    replace=[(siteId, "<siteId>")],
                )

                # Export site infos requiring owner accounts
                # Following will show sensitive information and addresses of installer
                # self._logger.info("Exporting HES installer info...")
                # response = await self.query(
                #     endpoint=API_HES_SVC_ENDPOINTS["get_installer_info"],
                #     filename=f"{API_FILEPREFIXES['hes_get_installer_info']}_{self._randomize(siteId,'site_id')}.json",
                #     payload={"siteIds": [siteId], "siteId": siteId},
                #     replace=[(siteId, "<siteId>")],
                #     admin=admin,
                # )
                self._logger.info("Exporting HES system running time...")
                response = await self.query(
                    endpoint=API_HES_SVC_ENDPOINTS["get_system_running_time"],
                    filename=f"{API_FILEPREFIXES['hes_get_system_running_time']}_{self._randomize(siteId, 'site_id')}.json",
                    payload={"siteId": siteId},
                    replace=[(siteId, "<siteId>")],
                    admin=admin,
                )
                self._logger.info("Exporting HES MI layout...")
                response = await self.query(
                    endpoint=API_HES_SVC_ENDPOINTS["get_mi_layout"],
                    filename=f"{API_FILEPREFIXES['hes_get_mi_layout']}_{self._randomize(siteId, 'site_id')}.json",
                    payload={"siteId": siteId},
                    replace=[(siteId, "<siteId>")],
                    admin=admin,
                )
                self._logger.info("Exporting HES connection net tips...")
                response = await self.query(
                    endpoint=API_HES_SVC_ENDPOINTS["get_conn_net_tips"],
                    filename=f"{API_FILEPREFIXES['hes_get_conn_net_tips']}_{self._randomize(siteId, 'site_id')}.json",
                    payload={"siteId": siteId},
                    replace=[(siteId, "<siteId>")],
                    admin=admin,
                )
                self._logger.info("Exporting HES device data...")
                response = await self.query(
                    endpoint=API_HES_SVC_ENDPOINTS["report_device_data"],
                    filename=f"{API_FILEPREFIXES['hes_report_device_data']}_{self._randomize(siteId, 'site_id')}.json",
                    payload={"siteIds": [siteId]},
                    replace=[(siteId, "<siteId>")],
                    admin=admin,
                )

            # skip remaining queries if no hes system found and hes not enforced
            if not has_hes and not self.export_services & {ApiEndpointServices.hes_svc}:
                self._logger.info(
                    "No system for %s endpoint data found, skipping remaining queries...",
                    ApiEndpointServices.hes_svc,
                )
                return True

            self._logger.info("Exporting HES heat pump plan...")
            await self.query(
                endpoint=API_HES_SVC_ENDPOINTS["get_heat_pump_plan"],
                filename=f"{API_FILEPREFIXES['hes_get_heat_pump_plan']}.json",
            )
            # TODO: Export electrical plan as example once a valid country and state was found
            country = "de"
            state_code = "nw"
            self._logger.info(
                "Exporting HES electric utility and plan list (exemplary for country '%s' and state '%s')...",
                country,
                state_code,
            )
            await self.query(
                endpoint=API_HES_SVC_ENDPOINTS["get_electric_plan_list"],
                filename=f"{API_FILEPREFIXES['hes_get_electric_plan_list']}_{country}_{state_code}.json",
                payload={"country": country, "state_code": state_code},
            )

            # loop through all devices
            for sn, device in self.api_power.devices.items():
                self._logger.info("")
                self._logger.info(
                    "Exporting HES specific data for device %s SN %s...",
                    device.get("name", ""),
                    self._randomize(sn, "_sn"),
                )
                siteId = device.get("site_id", "")
                admin = device.get("is_admin")

                # run only for hes devices for site owner
                if device.get("type") == api.SolixDeviceType.HES.value:
                    self._logger.info("Exporting HES device wifi info...")
                    await self.query(
                        endpoint=API_HES_SVC_ENDPOINTS["get_wifi_info"],
                        filename=f"{API_FILEPREFIXES['hes_get_wifi_info']}_{self._randomize(sn, '_sn')}.json",
                        payload={"sn": sn},
                        replace=[(siteId, "<siteId>"), (sn, "<deviceSn>")],
                    )

        except (errors.AnkerSolixError, ClientError) as err:
            if isinstance(err, ClientError):
                self._logger.warning(
                    "%s endpoint data queries may not be supported on used server: %s",
                    ApiEndpointServices.hes_svc,
                    err,
                )
            else:
                self._logger.error("%s: %s", type(err), err)
            self._logger.warning(
                "Skipping remaining %s endpoint data queries.",
                ApiEndpointServices.hes_svc,
            )
            return False

        return True

    def _randomize(self, val: str, key: str = "") -> str:
        """Randomize a given string while maintaining its format if format is known for given key name.

        Reuse same randomization if value was already randomized
        """

        val = str(val)
        if not self.randomized:
            return val
        randomstr = self._randomdata.get(val, "")
        # generate new random string
        if not randomstr and val and key not in ["device_name"]:
            if "_sn" in key or "mainSn" in key or key in ["sn"]:
                randomstr = "".join(
                    random.choices(string.ascii_uppercase + string.digits, k=len(val))
                )
            elif "bt_ble_" in key:
                # Handle values with and without ':'
                temp = val.replace(":", "")
                randomstr = self._randomdata.get(
                    temp
                )  # retry existing randomized value without :
                if not randomstr:
                    randomstr = "".join(
                        random.choices(string.hexdigits.upper(), k=len(temp))
                    )
                if ":" in val:
                    # save also key value without ':'
                    self._randomdata.update({temp: randomstr})
                    randomstr = ":".join(
                        a + b
                        for a, b in zip(randomstr[::2], randomstr[1::2], strict=False)
                    )
            elif "_id" in key:
                for part in val.split("-"):
                    if randomstr:
                        randomstr = "-".join(
                            [
                                randomstr,
                                "".join(
                                    random.choices(
                                        string.hexdigits.lower(), k=len(part)
                                    )
                                ),
                            ]
                        )
                    else:
                        randomstr = "".join(
                            random.choices(string.hexdigits.lower(), k=len(part))
                        )
            elif "wifi_name" in key or "ssid" in key:
                idx = sum(1 for s in self._randomdata.values() if "wifi-network-" in s)
                randomstr = f"wifi-network-{idx + 1}"
            elif "email" in key:
                idx = sum(1 for s in self._randomdata.values() if "anonymous-" in s)
                randomstr = f"anonymous-{idx + 1}@domain.com"
            elif key in ["home_load_data", "param_data"]:
                # these keys may contain schedule dict encoded as string, ensure contained serials are replaced in string
                # replace all mappings from self._randomdata, but skip trace ids
                randomstr = val
                for k, v in (
                    (old, new)
                    for old, new in self._randomdata.items()
                    if len(old) != 32
                ):
                    randomstr = randomstr.replace(k, v)
                # leave without saving randomized string in self._randomdata
                return randomstr
            else:
                # default randomize format
                randomstr = "".join(random.choices(string.ascii_letters, k=len(val)))
            self._randomdata.update({val: randomstr})
        return randomstr or str(val)

    def _check_keys(self, data: Any):
        """Recursive traversal of complex nested objects to randomize value for certain keys."""

        if isinstance(data, int | float | str):
            return data
        for k, v in data.copy().items():
            if isinstance(v, dict):
                v = self._check_keys(v)
            if isinstance(v, list):
                v = [self._check_keys(i) for i in v]
            # Randomize value for certain keys
            if any(
                x in k
                for x in [
                    "_sn",
                    "mainSn",
                    "site_id",
                    "station_id",
                    "trace_id",
                    "bt_ble_",
                    "wifi_name",
                    "ssid",
                    "home_load_data",
                    "param_data",
                    "device_name",
                    "token",
                    "email",
                ]
            ) or k in ["sn"]:
                data[k] = self._randomize(v, k)
        return data

    async def _export(
        self,
        filename: Path | str,
        d: dict | None = None,
        skip_randomize: bool = False,
        randomkeys: bool = False,
    ) -> None:
        """Save dict data to given file."""

        if not d:
            d = {}
        filename = str(filename)
        if len(d) == 0:
            self._logger.warning(
                "WARNING: File %s not saved because JSON is empty",
                filename.replace(str(self.export_path), str(self.export_folder)),
            )
            return
        if self.randomized and not skip_randomize:
            d = self._check_keys(d)
            # Randomize also the (nested) keys for dictionary export if required
            if randomkeys:
                d_copy = deepcopy(d)
                for key, val in d.items():
                    # check first nested keys in dict values
                    if isinstance(val, dict):
                        for nested_key, nested_val in dict(val).items():
                            if isinstance(nested_val, dict):
                                for k in [
                                    text for text in nested_val if isinstance(text, str)
                                ]:
                                    # check nested dict keys
                                    if k in self._randomdata:
                                        d_copy[key][nested_key][self._randomdata[k]] = (
                                            d_copy[key][nested_key].pop(k)
                                        )
                    # check root keys
                    if key in self._randomdata:
                        d_copy[self._randomdata[key]] = d_copy.pop(key)
                d = d_copy

        try:
            async with aiofiles.open(filename, "w", encoding="utf-8") as file:
                await file.write(json.dumps(d, indent=2))
                self._logger.info(
                    "Saved JSON to file %s",
                    filename.replace(str(self.export_path), str(self.export_folder)),
                )
        except OSError as err:
            self._logger.error(
                "ERROR: Failed to save JSON to file %s: %s",
                filename.replace(str(self.export_path), str(self.export_folder)),
                err,
            )
        return

    def get_random_mapping(
        self,
    ) -> dict[str, str]:
        """Get dict of randomized data mapping."""

        return self._randomdata

    async def query(
        self,
        method: str = "post",
        endpoint: str = "",
        filename: str = "",
        payload: dict[str, any] | None = None,
        admin: bool = True,
        catch: bool = True,
        randomkeys: bool = False,
        replace: list[(str, str)] | None = None,
    ) -> dict[str, any] | None:
        """Run the query and catch exception if required."""

        response = None
        if not payload:
            payload = {}
        if not replace:
            replace = []
        try:
            self._logger.debug("%s %s --> %s", method, endpoint, filename)
            if not admin:
                self._logger.warning(
                    "Api %s query requires account of site owner: %s",
                    self.client.nickname,
                    endpoint,
                )
            else:
                # return real response data without randomization if needed
                response = await self.client.request(method, endpoint, json=payload)
                await self._export(
                    Path(self.export_path) / filename, response, randomkeys=randomkeys
                )
        except (errors.AnkerSolixError, ClientError) as err:
            ignore_client_error = True
            if isinstance(err, ClientError):
                # client errors never to be caught
                # Error: 503, message='Service Temporarily Unavailable'
                ignore_client_error = "Error: 503," not in str(err)
            if catch and ignore_client_error:
                for secret, public in replace:
                    payload = (str(payload).replace(secret, public),)
                self._logger.error(
                    "Api: %s, Method: %s, Endpoint: %s, Payload: %s\n%s: %s",
                    self.client.nickname,
                    str(method).upper(),
                    endpoint,
                    str(payload),
                    type(err),
                    err,
                )
            else:
                raise
        return response
