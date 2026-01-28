"""Class for exporting the power system data into json files with the provide Anker API instance.

You can specify a subfolder for the exported JSON files received as API query response, defaulting to the Api instance account nick name.
Optionally you can specify whether personalized information in the response data should be randomized in the files, like SNs, Site IDs, Trace IDs etc.
Optionally the export files will also be zipped.
They json files can be used as examples for dedicated data extraction from the Api responses.
Furthermore the API class can use the json files for debugging and testing of various system outputs.
"""

import asyncio
from base64 import b64encode
from collections.abc import Callable
import contextlib
from copy import deepcopy
from datetime import datetime, timedelta
from functools import partial
import json
import logging
import logging.handlers
import os
from pathlib import Path
import queue
import random
import shutil
import string
import tempfile
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
    SolixPriceProvider,
    SolixVehicle,
)
from .mqtt import AnkerSolixMqttSession
from .mqttcmdmap import COMMAND_LIST, COMMAND_NAME, SolixMqttCommands
from .mqttmap import SOLIXMQTTMAP
from .mqtttypes import DeviceHexData

_LOGGER: logging.Logger = logging.getLogger(__name__)
VERSION: str = "3.5.1.0"


class AnkerSolixApiExport:
    """Define the class to handle json export from Anker Solix api instance."""

    def __init__(
        self,
        client: api.AnkerSolixApi | api.AnkerSolixClientSession,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize."""

        # get the api client and optional mqtt session from passed object
        if isinstance(client, api.AnkerSolixApi):
            self.client = client.apisession
            mqttsession = client.mqttsession
        else:
            self.client = client
            mqttsession = None
        # create new api instance with client session
        self.api_power = api.AnkerSolixApi(apisession=self.client)
        # Add existing mqtt session to new api instance
        self.api_power.mqttsession = mqttsession
        self.export_path: str | None = None
        self.export_folder: str | None = None
        self.export_services: set | None = None
        self.randomized: bool = True
        self.mqttdata: bool = False
        self.zipped: bool = True
        self.zipfilename: str | None = None
        self.request_delay: float | None = None
        self._randomdata: dict = {}
        self._loop: asyncio.AbstractEventLoop
        self._mqtt_msg_types: set = set()
        self._old_callback: Callable | None = None

        # initialize logger for object
        if logger:
            self._logger = logger
        else:
            self._logger = _LOGGER
            self._logger.setLevel(logging.DEBUG)

    async def export_data(  # noqa: C901
        self,
        export_path: Path | str | None = None,
        export_folder: Path | str | None = None,
        export_services: set | None = None,
        request_delay: float | None = None,
        randomized: bool = True,
        mqttdata: bool = False,
        zipped: bool = True,
        toggle_cache: Callable | None = None,
    ) -> bool:
        """Run main function to export account data."""

        if not export_path:
            # default to exports self.export_path in parent path of api library
            self.export_path = (Path(__file__).parent / ".." / "exports").resolve()
            if not (
                os.access(self.export_path.parent, os.W_OK)
                or os.access(self.export_path, os.W_OK)
            ):
                self.export_path = Path(tempfile.gettempdir()) / "exports"
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
        self.mqttdata = mqttdata if isinstance(mqttdata, bool) else False
        self.zipped = zipped if isinstance(randomized, bool) else True
        toggle_cache = toggle_cache if callable(toggle_cache) else None
        self._randomdata = {}
        self._loop = asyncio.get_running_loop()

        # ensure nickname is set for api client
        await self.client.async_authenticate()
        if not self.export_folder:
            if not self.client.nickname:
                return False
            # avoid filesystem problems with * in user nicknames
            self.export_folder = self.client.nickname.replace("*", "x")
        # complete path and ensure parent self.export_path for export exists
        self.export_path: Path = (Path(self.export_path) / self.export_folder).resolve()
        try:
            # clear export folder if it exists already
            if self.export_path.exists():
                await self._loop.run_in_executor(None, shutil.rmtree, self.export_path)
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
            mqtttask: asyncio.Task | None = None
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
            fh = await self._loop.run_in_executor(
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
                "Using AnkerSolixApiExport Version: %s, Date: %s, Export Services: %s, MQTT Messages: %s",
                VERSION,
                datetime.now().strftime("%Y-%m-%d"),
                str(self.export_services),
                str(self.mqttdata),
            )
            # save existing api client delay and adjust request delay for export
            if (old_delay := self.client.requestDelay()) != self.request_delay:
                self.client.requestDelay(self.request_delay)
                self._logger.debug(
                    "Saved api %s original request delay of %s seconds and modified delay to %s seconds.",
                    self.client.nickname,
                    old_delay,
                    self.request_delay,
                )
            # Query common data for all service types to get sites and devices for account
            if await self.query_common_data():
                # start MQTT session if MQTT data requested and eligible devices exist
                if self.mqttdata:
                    mqtttask = self._loop.create_task(self.export_mqtt_data())
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
                # Wait until optional MQTT task is finished
                if self.mqttdata and mqtttask:
                    await mqtttask
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
                self._logger.info(
                    "\nExporting api %s sites cache from files...",
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
                self._logger.info(
                    "\nExporting api %s account cache...",
                    self.client.nickname,
                )
                self._logger.debug(
                    "Api %s account cache --> %s",
                    self.client.nickname,
                    filename := f"{API_FILEPREFIXES['api_account']}.json",
                )
                # update account dictionary with number of requests during export and randomized email
                self.api_power._update_account(  # noqa: SLF001
                    {"email": self._randomize(self.api_power.apisession.email, "email")}
                )
                # Skip randomizing dictionary for account data to prevent double randomizaiton of other account fields
                await self._export(
                    Path(self.export_path) / filename,
                    self.api_power.account,
                    skip_randomize=True,
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
                self._logger.info(
                    "\nCompleted export of Anker Solix systems data for api %s",
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
                    self._logger.info("\nZipping output folder to %s", self.zipfilename)
                    self._logger.info(
                        "Zipfile created: %s",
                        await self._loop.run_in_executor(
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
            return False
        else:
            return True
        finally:
            # ensure the listener is closed
            listener.stop()
            # ensure optional MQTT task is closed
            if mqtttask:
                mqtttask.cancel()
                # Wait for the tasks to finish cancellation
                with contextlib.suppress(asyncio.CancelledError):
                    await mqtttask

    async def query_common_data(self) -> bool:
        """Run functions to query sites and devices."""

        self._logger.info("\nQuerying common endpoint data...")
        # update Api caches if still empty
        if not self.api_power.sites | self.api_power.devices:
            self._logger.info("Querying site information...")
            await self.api_power.update_sites()
            # Run bind devices to get also standalone devices of admin accounts for data export
            # Do not use site_details method, which may create virtual sites
            self._logger.info("Querying bind devices information...")
            await self.api_power.get_bind_devices()
            # Get HES device specific updates for member accounts and merge them
            if self.api_power.hesApi:
                for sn, device in self.api_power.hesApi.devices.items():
                    merged_dev = self.api_power.devices.get(sn) or {}
                    merged_dev.update(device)
                    self.api_power.devices[sn] = merged_dev
        self._logger.info(
            "Found %s accessible systems (sites) and %s devices.",
            len(self.api_power.sites),
            len(self.api_power.devices),
        )
        return bool(self.api_power.sites or self.api_power.devices)

    async def export_common_data(self) -> bool:
        """Run functions to export common data."""

        try:
            # Query API using direct endpoints to save full response of each query in json files
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
            self._logger.info("Get dynamic price sites for user account...")
            await self.query(
                endpoint=API_ENDPOINTS["get_dynamic_price_sites"],
                filename=f"{API_FILEPREFIXES['get_dynamic_price_sites']}.json",
            )
            # Get supported providers for found device models supporting dynamic prices
            providers = set()
            for model in {
                dev.get("device_pn")
                for dev in self.api_power.devices.values()
                if dev.get("device_pn") in ["A17C5", "A5101", "A5102", "A5103"]
            }:
                self._logger.info(
                    "Exporting dynamic price providers for model '%s'...", model
                )
                if (
                    resp := await self.query(
                        endpoint=API_ENDPOINTS["get_dynamic_price_providers"],
                        filename=f"{API_FILEPREFIXES['get_dynamic_price_providers']}_{model}.json",
                        payload={"device_pn": model},
                    )
                ) and isinstance(resp, dict):
                    # add provider options to set
                    for country in (resp.get("data") or {}).get("country_info") or []:
                        for company in country.get("company_info") or []:
                            for area in company.get("area_info") or []:
                                providers.add(
                                    str(
                                        SolixPriceProvider(
                                            country=country.get("country"),
                                            company=company.get("company"),
                                            area=area.get("area"),
                                        )
                                    )
                                )
            # export prices for all provider options
            for provider in [SolixPriceProvider(provider=p) for p in providers]:
                self._logger.info(
                    "Exporting dynamic price details for %s...",
                    provider,
                )
                await self.query(
                    endpoint=API_ENDPOINTS["get_dynamic_price_details"],
                    filename=f"{API_FILEPREFIXES['get_dynamic_price_details']}_{str(provider).replace('/', '_')}.json",
                    payload={
                        "company": provider.company,
                        "area": provider.area,
                        "date": str(int(datetime.today().timestamp())),
                        "device_sn": "",
                    },
                )
            # Export user vehicles
            self._logger.info("Get user vehicle list...")
            response = await self.query(
                endpoint=API_ENDPOINTS["get_user_vehicles"],
                filename=f"{API_FILEPREFIXES['get_user_vehicles']}.json",
            )
            # use real vehicle_id from previous response for query
            self._logger.info("Get details for vehicle IDs...")
            vehicles = []
            for vehicleId in [
                v.get("vehicle_id")
                for v in ((response or {}).get("data") or {}).get("vehicle_list") or []
            ]:
                if (
                    v := (
                        await self.query(
                            endpoint=API_ENDPOINTS["get_user_vehicle_details"],
                            filename=f"{API_FILEPREFIXES['get_user_vehicle_details']}_{self._randomize(vehicleId, 'vehicle_id')}.json",
                            payload={"vehicle_id": vehicleId},
                            replace=[(vehicleId, "<vehicleId>")],
                        )
                        or {}
                    ).get("data")
                    or {}
                ):
                    vehicles.append(SolixVehicle(vehicle=v))  # noqa: PERF401
            # get EV brands and extract attributes of the defined models or a random model
            self._logger.info("Get EV brands and attributes of vehicle model(s)...")
            brands = (
                (
                    await self.query(
                        endpoint=API_ENDPOINTS["get_vehicle_brands"],
                        filename=f"{API_FILEPREFIXES['get_vehicle_brands']}.json",
                    )
                    or {}
                ).get("data")
                or {}
            ).get("brand_list") or []
            for vehicle in vehicles or [SolixVehicle()]:
                brand = (
                    vehicle.brand
                    if vehicle.brand in brands
                    else str(random.choice(brands or [""]))
                )
                response = await self.query(
                    endpoint=API_ENDPOINTS["get_vehicle_brand_models"],
                    filename=f"{API_FILEPREFIXES['get_vehicle_brand_models']}_{brand.replace(' ', '_')}.json",
                    payload={"brand_name": brand},
                )
                if items := ((response or {}).get("data") or {}).get("model_list"):
                    model = (
                        vehicle.model
                        if vehicle.model in items
                        else str(random.choice(items))
                    )
                    response = await self.query(
                        endpoint=API_ENDPOINTS["get_vehicle_model_years"],
                        filename=f"{API_FILEPREFIXES['get_vehicle_model_years']}_{brand.replace(' ', '_')}_{model.replace(' ', '_')}.json",
                        payload={"brand_name": brand, "model_name": model},
                    )
                    if items := ((response or {}).get("data") or {}).get("year_list"):
                        year = (
                            vehicle.productive_year
                            if vehicle.productive_year in items
                            else random.choice(items)
                        )
                        await self.query(
                            endpoint=API_ENDPOINTS["get_vehicle_year_attributes"],
                            filename=f"{API_FILEPREFIXES['get_vehicle_year_attributes']}_{brand.replace(' ', '_')}_{model.replace(' ', '_')}_{year!s}.json",
                            payload={
                                "brand_name": brand,
                                "model_name": model,
                                "productive_year": year,
                            },
                        )
            # get OCCP endpoint list
            self._logger.info("Exporting OCPP endpoints...")
            await self.query(
                endpoint=API_ENDPOINTS["get_ocpp_endpoint_list"],
                filename=f"{API_FILEPREFIXES['get_ocpp_endpoint_list']}.json",
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
                self._logger.info("Exporting CO2 ranking...")
                await self.query(
                    endpoint=API_ENDPOINTS["get_co2_ranking"],
                    filename=f"{API_FILEPREFIXES['get_co2_ranking']}_{self._randomize(siteId, 'site_id')}.json",
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

        self._logger.info("\nQuerying %s endpoint data...", ApiEndpointServices.power)
        # Query API using direct endpoints to save full response of each query in json files
        try:
            self._logger.info("\nExporting homepage...")
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
                payload={
                    "token": ((response or {}).get("data") or {}).get("token", "")
                },
            )

            # loop through all found sites
            for siteId, site in self.api_power.sites.items():
                self._logger.info(
                    "\nExporting site specific data for site %s...",
                    self._randomize(siteId, "site_id"),
                )
                admin = site.get("site_admin")
                power_site_type = site.get("power_site_type")
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
                self._logger.info("Exporting site power limit...")
                # works only for site owners
                await self.query(
                    endpoint=API_ENDPOINTS["get_site_power_limit"],
                    filename=f"{API_FILEPREFIXES['get_site_power_limit']}_{self._randomize(siteId, 'site_id')}.json",
                    payload={"site_id": siteId},
                    replace=[(siteId, "<siteId>")],
                    admin=admin,
                )
                self._logger.info("Exporting site price...")
                # works only for site owners
                await self.query(
                    endpoint=API_ENDPOINTS["get_site_price"],
                    filename=f"{API_FILEPREFIXES['get_site_price']}_{self._randomize(siteId, 'site_id')}.json",
                    payload={"site_id": siteId, "accuracy": 5},
                    replace=[(siteId, "<siteId>")],
                    admin=admin,
                )
                # Additional exports for site types support AI mode
                if power_site_type in [12]:
                    self._logger.info("Exporting site forecast schedule...")
                    await self.query(
                        endpoint=API_ENDPOINTS["get_forecast_schedule"],
                        filename=f"{API_FILEPREFIXES['get_forecast_schedule']}_{self._randomize(siteId, 'site_id')}.json",
                        payload={"site_id": siteId},
                        replace=[(siteId, "<siteId>")],
                    )
                    self._logger.info("Exporting AI EMS status...")
                    await self.query(
                        endpoint=API_ENDPOINTS["get_ai_ems_status"],
                        filename=f"{API_FILEPREFIXES['get_ai_ems_status']}_{self._randomize(siteId, 'site_id')}.json",
                        payload={"site_id": siteId},
                        replace=[(siteId, "<siteId>")],
                    )
                    # TODO: Profit types are unknown, enable export once types are known
                    # for parmtype in ["unknown_type"]:
                    #     self._logger.info("Exporting AI EMS profit for '%s'...", parmtype)
                    #     await self.query(
                    #         endpoint=API_ENDPOINTS["get_ai_ems_profit"],
                    #         filename=f"{API_FILEPREFIXES['get_ai_ems_profit']}_{self._randomize(siteId, 'site_id')}.json",
                    #         payload={"site_id": siteId, "start_time": "00:00", "end_time": "24:00", "type": parmtype},
                    #         replace=[(siteId, "<siteId>")],
                    #     )

                for parmtype in [
                    "1",
                    "2",
                    "3",
                    "4",
                    "5",
                    "6",
                    "7",
                    "12",
                    "13",
                    "16",
                    "18",
                    "20",
                    "23",
                    "26",
                ]:
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
                    # Day Totals
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
                    # Intraday
                    await self.query(
                        endpoint=API_ENDPOINTS["energy_analysis"],
                        filename=f"{API_FILEPREFIXES['energy_' + stat_type]}_today_{self._randomize(siteId, 'site_id')}.json",
                        payload={
                            "site_id": siteId,
                            "device_sn": "",
                            "type": "day",
                            "device_type": stat_type,
                            "start_time": datetime.today().strftime("%Y-%m-%d"),
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
                self._logger.info(
                    "\nExporting device specific data for device %s SN %s...",
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
                    self._logger.info("Exporting device income for solarbank...")
                    await self.query(
                        endpoint=API_ENDPOINTS["get_device_income"],
                        filename=f"{API_FILEPREFIXES['get_device_income']}_{self._randomize(sn, '_sn')}.json",
                        payload={"device_sn": sn, "start_time": "00:00"},
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
                            "pv_power_limit",
                            "legal_power_limit",
                            "power_limit_option",
                            "power_limit_option_real",
                            "switch_0w",
                        ],
                    },
                    replace=[(siteId, "<siteId>"), (sn, "<deviceSn>")],
                    admin=admin,
                )
                self._logger.info("Exporting device tamper records...")
                await self.query(
                    endpoint=API_ENDPOINTS["get_tamper_records"],
                    filename=f"{API_FILEPREFIXES['get_tamper_records']}_{self._randomize(sn, '_sn')}.json",
                    payload={
                        "device_sn": sn,
                        "page_num": 0,
                        "page_size": 10,
                    },
                    replace=[(sn, "<deviceSn>")],
                    admin=admin,
                )
                self._logger.info("Exporting device group...")
                await self.query(
                    endpoint=API_ENDPOINTS["get_device_group"],
                    filename=f"{API_FILEPREFIXES['get_device_group']}_{self._randomize(sn, '_sn')}.json",
                    payload={"device_sn": sn},
                    replace=[(sn, "<deviceSn>")],
                    admin=admin,
                )

                # export EV charger status and statistics
                if device.get("type") == api.SolixDeviceType.EV_CHARGER.value:
                    self._logger.info("Exporting EV charger RFID cards...")
                    await self.query(
                        endpoint=API_ENDPOINTS["get_device_rfid_cards"],
                        filename=f"{API_FILEPREFIXES['get_device_rfid_cards']}_{self._randomize(sn, '_sn')}.json",
                        payload={"device_sn": sn},
                        replace=[(sn, "<deviceSn>")],
                        admin=admin,
                    )
                    self._logger.info("Exporting EV charger order statistics...")
                    # TODO: Update order status types once known, may have to be limited for time range
                    for stat_type in ["week", "all"]:
                        await self.query(
                            endpoint=API_ENDPOINTS["get_device_charge_order_stats"],
                            filename=f"{API_FILEPREFIXES['get_device_charge_order_stats']}_{'today' if stat_type == 'week' else stat_type}_{self._randomize(sn, '_sn')}.json",
                            payload={
                                "device_sn": sn,
                                "date_type": stat_type,
                                "start_date": datetime.today().strftime("%Y-%m-%d")
                                if stat_type == "week"
                                else "",
                                "end_date": datetime.today().strftime("%Y-%m-%d")
                                if stat_type == "week"
                                else "",
                            },
                            replace=[(sn, "<deviceSn>")],
                        )
                    self._logger.info("Exporting EV charger order statistics list...")
                    for stat_type in [1]:
                        # TODO: Update order status types once known, may have to be limited for time range
                        await self.query(
                            endpoint=API_ENDPOINTS[
                                "get_device_charge_order_stats_list"
                            ],
                            filename=f"{API_FILEPREFIXES['get_device_charge_order_stats_list']}_{stat_type!s}_{self._randomize(sn, '_sn')}.json",
                            payload={
                                "device_sn": sn,
                                "date_type": "all",
                                "start_date": "",
                                "end_date": "",
                                "order_status": 1,
                                "page": 0,
                                "page_size": 10,
                            },
                            replace=[(sn, "<deviceSn>")],
                        )
                    self._logger.info("Exporting EV charger OCPP info...")
                    await self.query(
                        endpoint=API_ENDPOINTS["get_device_ocpp_info"],
                        filename=f"{API_FILEPREFIXES['get_device_ocpp_info']}_{self._randomize(sn, '_sn')}.json",
                        payload={"device_sn": sn},
                        replace=[(sn, "<deviceSn>")],
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

                # export data for Charger devices
                if device.get("type") == api.SolixDeviceType.CHARGER.value:
                    model = device.get("device_pn") or ""
                    self._logger.info(
                        "Exporting Power Charger specific data for device %s SN %s...",
                        device.get("name", ""),
                        self._randomize(sn, "_sn"),
                    )
                    await self.query(
                        endpoint=API_ENDPOINTS["charger_get_screensavers"],
                        filename=f"{API_FILEPREFIXES['charger_get_screensavers']}_{self._randomize(sn, '_sn')}.json",
                        payload={"device_sn": sn, "product_code": model},
                        replace=[(sn, "<deviceSn>")],
                    )
                    await self.query(
                        endpoint=API_ENDPOINTS["charger_get_charging_modes"],
                        filename=f"{API_FILEPREFIXES['charger_get_charging_modes']}_{self._randomize(sn, '_sn')}.json",
                        payload={"device_sn": sn},
                        replace=[(sn, "<deviceSn>")],
                    )
                    await self.query(
                        endpoint=API_ENDPOINTS["charger_get_triggers"],
                        filename=f"{API_FILEPREFIXES['charger_get_triggers']}_{self._randomize(sn, '_sn')}.json",
                        payload={"device_sn": sn},
                        replace=[(sn, "<deviceSn>")],
                    )
                    await self.query(
                        endpoint=API_ENDPOINTS["charger_get_device_setting"],
                        filename=f"{API_FILEPREFIXES['charger_get_device_setting']}_{self._randomize(sn, '_sn')}.json",
                        payload={"device_sn": sn},
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

        self._logger.info(
            "\nQuerying %s endpoint data...", ApiEndpointServices.charging
        )
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
                self._logger.info(
                    "\nExporting Charging specific data for site %s...",
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
                self._logger.info(
                    "\nExporting Charging specific data for device %s SN %s...",
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

        self._logger.info("\nQuerying %s endpoint data...", ApiEndpointServices.hes_svc)
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
                self._logger.info(
                    "\nExporting HES specific data for site %s...",
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
                await self.query(
                    endpoint=API_HES_SVC_ENDPOINTS["get_monetary_units"],
                    filename=f"{API_FILEPREFIXES['hes_get_monetary_units']}_{self._randomize(siteId, 'site_id')}.json",
                    payload={"siteId": siteId},
                    replace=[(siteId, "<siteId>")],
                )
                # Following will show sensitive information and addresses
                # self._logger.info("Exporting HES install info...")
                # await self.query(
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
                # get various profits of today and actual year per month
                for stat_type in ["day", "year"]:
                    self._logger.info(
                        "Exporting HES site profit data for %s...",
                        stat_type.upper(),
                    )
                    await self.query(
                        endpoint=API_HES_SVC_ENDPOINTS["get_system_profit"],
                        filename=f"{API_FILEPREFIXES['hes_get_system_profit']}_{stat_type}_{self._randomize(siteId, 'site_id')}.json",
                        payload={
                            "siteId": siteId,
                            "dateType": stat_type,
                            "start": datetime.today().strftime("%Y-%m-%d")
                            if stat_type == "day"
                            else datetime.today().strftime("%Y"),
                        },
                        replace=[(siteId, "<siteId>")],
                    )
                self._logger.info("Exporting HES device info...")
                await self.query(
                    endpoint=API_HES_SVC_ENDPOINTS["get_hes_dev_info"],
                    filename=f"{API_FILEPREFIXES['hes_get_hes_dev_info']}_{self._randomize(siteId, 'site_id')}.json",
                    payload={"siteId": siteId},
                    replace=[(siteId, "<siteId>")],
                )
                self._logger.info("Exporting HES standalone EV chargers...")
                await self.query(
                    endpoint=API_HES_SVC_ENDPOINTS["get_evcharger_standalone"],
                    filename=f"{API_FILEPREFIXES['hes_get_evcharger_standalone']}.json",
                    payload={},
                )

                # Export site infos requiring owner accounts
                self._logger.info("Exporting HES system running time...")
                await self.query(
                    endpoint=API_HES_SVC_ENDPOINTS["get_system_running_time"],
                    filename=f"{API_FILEPREFIXES['hes_get_system_running_time']}_{self._randomize(siteId, 'site_id')}.json",
                    payload={"siteId": siteId},
                    replace=[(siteId, "<siteId>")],
                    admin=admin,
                )
                # Following will show sensitive information and addresses of installer
                # self._logger.info("Exporting HES installer info...")
                # await self.query(
                #     endpoint=API_HES_SVC_ENDPOINTS["get_installer_info"],
                #     filename=f"{API_FILEPREFIXES['hes_get_installer_info']}_{self._randomize(siteId,'site_id')}.json",
                #     payload={"siteIds": [siteId], "siteId": siteId},
                #     replace=[(siteId, "<siteId>")],
                #     admin=admin,
                # )
                self._logger.info("Exporting HES MI layout...")
                await self.query(
                    endpoint=API_HES_SVC_ENDPOINTS["get_mi_layout"],
                    filename=f"{API_FILEPREFIXES['hes_get_mi_layout']}_{self._randomize(siteId, 'site_id')}.json",
                    payload={"siteId": siteId},
                    replace=[(siteId, "<siteId>")],
                    admin=admin,
                )
                self._logger.info("Exporting HES connection net tips...")
                await self.query(
                    endpoint=API_HES_SVC_ENDPOINTS["get_conn_net_tips"],
                    filename=f"{API_FILEPREFIXES['hes_get_conn_net_tips']}_{self._randomize(siteId, 'site_id')}.json",
                    payload={"siteId": siteId},
                    replace=[(siteId, "<siteId>")],
                    admin=admin,
                )
                self._logger.info("Exporting HES device data...")
                await self.query(
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
                self._logger.info(
                    "\nExporting HES specific data for device %s SN %s...",
                    device.get("name", ""),
                    self._randomize(sn, "_sn"),
                )
                siteId = device.get("site_id", "")
                admin = device.get("is_admin")

                # queries for HES devices
                if device.get("type") == api.SolixDeviceType.HES.value:
                    self._logger.info("Exporting HES device wifi info...")
                    # works only for site owners
                    await self.query(
                        endpoint=API_HES_SVC_ENDPOINTS["get_wifi_info"],
                        filename=f"{API_FILEPREFIXES['hes_get_wifi_info']}_{self._randomize(sn, '_sn')}.json",
                        payload={"sn": sn},
                        replace=[(siteId, "<siteId>"), (sn, "<deviceSn>")],
                        admin=admin,
                    )
                # queries for EV charger devices
                elif device.get("type") == api.SolixDeviceType.EV_CHARGER.value:
                    self._logger.info("Exporting HES EV charger station info...")
                    # get various feature types
                    for stat_type in [1, 2]:
                        await self.query(
                            endpoint=API_HES_SVC_ENDPOINTS[
                                "get_evcharger_station_info"
                            ],
                            filename=f"{API_FILEPREFIXES['hes_get_evcharger_station_info']}_{stat_type!s}_{self._randomize(sn, '_sn')}.json",
                            payload={"evChargerSn": sn, "featuretype": stat_type},
                            replace=[(sn, "<deviceSn>")],
                            admin=admin,
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

        if not self.randomized or not val:
            return val
        val = str(val)
        randomstr = self._randomdata.get(val, "")
        # generate new random string
        if not randomstr and val and key not in ["device_name"]:
            if "_sn" in key or "mainSn" in key or key in ["sn"]:
                randomstr = "".join(
                    random.choices(string.ascii_uppercase + string.digits, k=len(val))
                )
            elif "bt_ble_" in key or "_mac" in key:
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
            elif "_id" in key or "_password" in key:
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
                    "user_id",
                    "member_id",
                    "vehicle_id",
                    "trace_id",
                    "bt_ble_",
                    "wifi_name",
                    "ssid",
                    "home_load_data",
                    "param_data",
                    "device_name",
                    "token",
                    "email",
                    "_password",
                    "_mac",
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
                    Path(self.export_path) / filename,
                    deepcopy(response),
                    randomkeys=randomkeys,
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

    async def export_mqtt_data(self) -> None:
        """Start MQTT session and dump received messages."""

        mqttsession = None
        try:
            # get all owned devices that may support MQTT messages
            if mqttdevices := [
                dev
                for dev in self.api_power.devices.values()
                if dev.get("is_admin") and not dev.get("is_passive")
            ]:
                # reuse existing MQTT client or start new one
                if mqttsession := self.api_power.mqttsession:
                    self._logger.info(
                        "Using existing MQTT session and intercepting message callback for export..."
                    )
                    self._old_callback = mqttsession.message_callback()
                    mqttsession.message_callback(func=self.dump_device_mqtt)
                else:
                    self._logger.info("Starting MQTT session...")
                    mqttsession = await self.api_power.startMqttSession(
                        message_callback=self.dump_device_mqtt
                    )
                if mqttsession and mqttsession.is_connected():
                    self._logger.info(
                        "MQTT session connected, subscribing eligible devices and waiting 70 seconds for messages..."
                    )
                    request_devices = set()
                    for dev in mqttdevices:
                        sn = dev.get("device_sn", "")
                        pn = dev.get("device_pn", "") or dev.get("product_code", "")
                        topic = f"{self.api_power.mqttsession.get_topic_prefix(deviceDict=dev)}#"
                        resp = self.api_power.mqttsession.subscribe(topic)
                        if resp and resp.is_failure:
                            self._logger.warning(
                                "Failed subscription for topic: %s",
                                topic.replace(sn, self._randomize(sn, "device_sn")),
                            )
                        else:
                            self._logger.info(
                                "Subscribed to MQTT topic: %s",
                                topic.replace(sn, self._randomize(sn, "device_sn")),
                            )
                            # mark devices that need status requests
                            if [
                                msg
                                for msg in SOLIXMQTTMAP.get(pn, {}).values()
                                if SolixMqttCommands.status_request
                                in [
                                    msg.get(COMMAND_NAME),
                                    *msg.get(COMMAND_LIST, []),
                                ]
                            ]:
                                request_devices.add(sn)
                    # wait at least first minute for messages without trigger
                    await asyncio.sleep(70)
                    # Ensure MQTT client is still connected
                    if not mqttsession.is_connected():
                        self._logger.info(
                            "MQTT session not connected, trying reconnection..."
                        )
                        mqttsession = await self.api_power.startMqttSession(
                            message_callback=self.dump_device_mqtt
                        )
                    # Cycle through devices and publish trigger for each applicable device
                    if mqttsession.is_connected():
                        self._logger.info(
                            "Triggering MQTT Real Time data or Status Requests for 60 seconds and waiting for messages..."
                        )
                        for dev in mqttdevices:
                            sn = dev.get("device_sn")
                            if sn not in request_devices:
                                resp = mqttsession.realtime_trigger(
                                    deviceDict=dev,
                                    timeout=60,
                                    wait_for_publish=2,
                                )
                                if resp.is_published():
                                    self._logger.info(
                                        "Published MQTT Real Time trigger message for device %s",
                                        self._randomize(sn, "device_sn"),
                                    )
                                    mqttsession.triggered_devices.add(sn)
                                else:
                                    self._logger.warning(
                                        "Failed to publish Real Time trigger message for device %s",
                                        self._randomize(sn, "device_sn"),
                                    )
                                    mqttsession.triggered_devices.discard(sn)
                    # wait for the RT trigger to timeout and publish requests for required devices
                    for _ in range(12):
                        for sn in request_devices:
                            resp = mqttsession.status_request(
                                deviceDict=self.api_power.devices.get(sn, {}),
                                wait_for_publish=2,
                            )
                            if resp.is_published():
                                self._logger.info(
                                    "Published MQTT Status Request message for device %s",
                                    self._randomize(sn, "device_sn"),
                                )
                            else:
                                self._logger.warning(
                                    "Failed to publish MQTT Status Request message for device %s",
                                    self._randomize(sn, "device_sn"),
                                )
                        await asyncio.sleep(5)
                    mqttsession.triggered_devices.clear()
                    # wait another 3 minutes to get all standard messages in 5 minute interval
                    for i in range(3, 0, -1):
                        self._logger.info(
                            "Waiting %s more seconds for additional standard MQTT messages...",
                            i * 60,
                        )
                        await asyncio.sleep(60)
                else:
                    self._logger.warning(
                        "MQTT session start or connection failed, skipping MQTT data export"
                    )
            else:
                self._logger.warning(
                    "No owned devices found, skipping MQTT data export"
                )
        except (
            asyncio.CancelledError,
            ClientError,
            errors.AnkerSolixError,
        ) as err:
            if isinstance(err, ClientError | errors.AnkerSolixError):
                self._logger.warning(
                    "Aborting MQTT session due to unexpected error %s: %s",
                    type(err),
                    err,
                )
            else:
                self._logger.warning("MQTT session was cancelled.")
        finally:
            if mqttsession and self._old_callback:
                self._logger.info("MQTT message export fininished.")
                mqttsession.message_callback(func=self._old_callback)
                self._logger.info(
                    "Switched MQTT session message callback back to original."
                )
            else:
                self._logger.info("Stopping MQTT connection...")
                self.api_power.stopMqttSession()
                self._logger.info("MQTT message export fininished.")

    def dump_device_mqtt(
        self,
        session: AnkerSolixMqttSession,
        topic: str,
        message: Any,
        data: bytes,
        model: str,
        device_sn: str,
        *args,
        **kwargs,
    ) -> None:
        """Randomized known message content and save the messages to files."""

        # forward message to original message callback if existing
        if callable(self._old_callback):
            self._old_callback(
                session, topic, message, data, model, device_sn, *args, **kwargs
            )
        if isinstance(message, dict) and model and device_sn:
            # extract message type from hex data for message grouping per file
            msgtype = "other"
            randsn = self._randomize(device_sn, "device_sn")
            datastr = None
            if payload := message.get("payload"):
                payload = json.loads(payload)
            if isinstance(data, bytes):
                # structure hex data
                if not (
                    msgtype := DeviceHexData(hexbytes=data).msg_header.msgtype.hex()
                ):
                    msgtype = "other"
                # randomize potential hex serials of system device serials in hex data
                if self.randomized:
                    if siteId := (self.api_power.devices.get(device_sn) or {}).get(
                        "site_id"
                    ):
                        serials = {
                            sn
                            for sn, dev in self.api_power.devices.items()
                            if siteId == dev.get("site_id")
                        }
                    else:
                        serials = {device_sn}
                    datastr = bytes(data).hex()
                    for sn in serials:
                        snhex = sn.encode().hex()
                        randsnhex = self._randomize(sn, "device_sn").encode().hex()
                        datastr = datastr.replace(snhex, randsnhex)
            if isinstance(payload, dict):
                if datastr:
                    # replace based64 encoded string in data field of message payload
                    payload["data"] = b64encode(bytes.fromhex(datastr)).decode()
                # replace other sensitive values in payload
                payload = self._check_keys(payload)
                message["payload"] = json.dumps(payload)
            # randomize sensitive json key values in message fields
            if self.randomized:
                message = self._check_keys(message)
            # replace randomized device serial in message keys or unknown fields
            message["topic"] = topic
            msgstr = json.dumps(message).replace(device_sn, randsn)
            # save the message
            filename = f"{API_FILEPREFIXES['mqtt_message']}_{randsn}_{msgtype}.ndjson"
            # print info for first message type per device
            if filename not in self._mqtt_msg_types:
                self._mqtt_msg_types.add(filename)
                self._logger.info(
                    "Received new MQTT message type '%s' from device %s",
                    msgtype,
                    self._randomize(device_sn, "device_sn"),
                )
            # wait for the save and protect from task cancelation
            savetask = asyncio.run_coroutine_threadsafe(
                coro=self.api_power.mqttsession.saveToFile(
                    filename=Path(self.export_path) / filename, data=json.loads(msgstr)
                ),
                loop=self._loop,
            )
            if savetask.result():
                self._logger.debug(
                    "Saved MQTT message type '%s' from device %s --> %s",
                    msgtype,
                    self._randomize(device_sn, "device_sn"),
                    filename,
                )
            else:
                self._logger.warning(
                    "Failed to save MQTT message type '%s' from device %s to file %s",
                    msgtype,
                    self._randomize(device_sn, "device_sn"),
                    filename,
                )
        else:
            self._logger.debug(
                "Received unknown MQTT message type %s from device %s",
                type(message),
                self._randomize(device_sn, "device_sn") if device_sn else "Unknown",
            )
