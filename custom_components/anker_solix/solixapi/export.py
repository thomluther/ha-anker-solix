"""Class for exporting the power system data into json files with the provide Anker API instance.

You can specify a subfolder for the exported JSON files received as API query response, defaulting to the Api instance account nick name.
Optionally you can specify whether personalized information in the response data should be randomized in the files, like SNs, Site IDs, Trace IDs etc.
Optionally the export files will also be zipped.
They json files can be used as examples for dedicated data extraction from the Api responses.
Furthermore the API class can use the json files for debugging and testing of various system outputs.
"""

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta
from functools import partial
import json
import logging
import logging.handlers
import os
import queue
import random
import shutil
import string
from typing import Any

import aiofiles

from . import api, errors

_LOGGER: logging.Logger = logging.getLogger(__name__)


class AnkerSolixApiExport:
    """Define the class to handle json export from Anker Solix api instance."""

    def __init__(
        self,
        client: api.AnkerSolixApi,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize."""

        self.client: api.AnkerSolixApi = client
        self.export_path: str | None = None
        self.export_folder: str | None = None
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
        # Add console to logger if no handler available
        # if not self._logger.hasHandlers():
        #     # create console handler and set level to info
        #     ch = logging.StreamHandler()
        #     ch.setLevel(logging.INFO)
        #     self._logger.addHandler(ch)

    async def export_data(  # noqa: C901
        self,
        export_path: str | None = None,
        export_folder: str | None = None,
        request_delay: float | None = None,
        randomized: bool = True,
        zipped: bool = True,
    ) -> bool:
        """Run main function to export account data."""

        self.export_path = export_path
        if not self.export_path:
            # default to exports self.export_path in parent path of api library
            self.export_path = os.path.join(os.path.dirname(__file__), "..", "exports")
        self.export_folder = export_folder
        self.request_delay = (
            request_delay
            if isinstance(request_delay, int | float)
            else self.client.requestDelay()
        )
        self.randomized = randomized if isinstance(randomized, bool) else True
        self.zipped = zipped if isinstance(randomized, bool) else True
        self._randomdata = {}

        # ensure nickname is set for api client
        await self.client.async_authenticate()
        if not self.export_folder:
            if not self.client.nickname:
                return False
            # avoid filesystem problems with * in user nicknames
            self.export_folder = self.client.nickname.replace("*", "#")
        # complete path and ensure parent self.export_path for export exists
        self.export_path = os.path.abspath(
            os.path.join(self.export_path, self.export_folder)
        )
        try:
            # clear export folder if it exists already
            if os.path.exists(self.export_path):
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, shutil.rmtree, self.export_path)
                # shutil.rmtree(self.export_path)
            os.makedirs(self.export_path, exist_ok=True)
        except OSError as err:
            self._logger.error(
                "Unable clear or create export folder %s: %s", self.export_path, err
            )
            return False

        self._logger.info(
            "Exporting Anker Solix data for all account sites and devices of nickname %s.",
            self.client.nickname,
        )
        try:
            # create a queue for async file logging
            que = queue.Queue()
            # add a handler that uses the logs to queue at DEBUG level, independend of other logger handler setting
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
                    filename=os.path.join(self.export_path, "export.log"),
                ),
            )
            # create a listener for messages on the queue and log them to the file handler
            listener = logging.handlers.QueueListener(que, fh)
            # start the listener
            listener.start()

            # save existing api delay and adjust request delay for export
            if (old_delay := self.client.requestDelay()) != self.request_delay:
                self.client.requestDelay(self.request_delay)
                self._logger.debug(
                    "Saved original request delay of %s seconds and modified delay to %s seconds.",
                    old_delay,
                    self.request_delay,
                )

            # first update Api chaches if still empty
            if not (self.client.sites and self.client.devices):
                self._logger.info("")
                self._logger.info("Querying site information...")
                await self.client.update_sites()
                # Run bind devices to get also standalone devices for data export
                self._logger.info("Querying bind devices information...")
                await self.client.get_bind_devices()
            self._logger.info(
                "Found %s accessible systems (sites) and %s devices.",
                len(self.client.sites),
                len(self.client.devices),
            )

            # Query API using direct endpoints to save full response of each query in json files
            self._logger.info("")
            self._logger.info("Exporting homepage...")
            self._logger.debug(
                "%s %s --> %s",
                method := "post",
                endpoint := api.API_ENDPOINTS["homepage"],
                filename := "homepage.json",
            )
            payload = {}
            await self._export(
                os.path.join(self.export_path, filename),
                await self.client.request(
                    method,
                    endpoint,
                    json=payload,
                ),
            )
            self._logger.info("Exporting site list...")
            self._logger.debug(
                "%s %s --> %s",
                method := "post",
                endpoint := api.API_ENDPOINTS["site_list"],
                filename := "site_list.json",
            )
            payload = {}
            await self._export(
                os.path.join(self.export_path, filename),
                await self.client.request(
                    method,
                    endpoint,
                    json=payload,
                ),
            )
            self._logger.info("Exporting bind devices...")
            self._logger.debug(
                "%s %s --> %s",
                method := "post",
                endpoint := api.API_ENDPOINTS["bind_devices"],
                filename := "bind_devices.json",
            )
            payload = {}
            await self._export(
                os.path.join(self.export_path, filename),
                await self.client.request(
                    method,
                    endpoint,
                    json=payload,
                ),
            )  # shows only owner devices
            self._logger.info("Exporting user devices...")
            self._logger.debug(
                "%s %s --> %s",
                method := "post",
                endpoint := api.API_ENDPOINTS["user_devices"],
                filename := "user_devices.json",
            )
            payload = {}
            await self._export(
                os.path.join(self.export_path, filename),
                await self.client.request(
                    method,
                    endpoint,
                    json=payload,
                ),
            )  # shows only owner devices
            self._logger.info("Exporting charging devices...")
            self._logger.debug(
                "%s %s --> %s",
                method := "post",
                endpoint := api.API_ENDPOINTS["charging_devices"],
                filename := "charging_devices.json",
            )
            payload = {}
            await self._export(
                os.path.join(self.export_path, filename),
                await self.client.request(
                    method,
                    endpoint,
                    json=payload,
                ),
            )  # shows only owner devices
            self._logger.info("Exporting auto upgrade settings...")
            self._logger.debug(
                "%s %s --> %s",
                method := "post",
                endpoint := api.API_ENDPOINTS["get_auto_upgrade"],
                filename := "auto_upgrade.json",
            )
            payload = {}
            await self._export(
                os.path.join(self.export_path, filename),
                await self.client.request(
                    method,
                    endpoint,
                    json=payload,
                ),
            )  # shows only owner devices
            self._logger.info("Exporting config...")
            self._logger.debug(
                "%s %s --> %s",
                method := "post",
                endpoint := api.API_ENDPOINTS["get_config"],
                filename := "config.json",
            )
            payload = {}
            await self._export(
                os.path.join(self.export_path, filename),
                await self.client.request(
                    method,
                    endpoint,
                    json=payload,
                ),
            )
            self._logger.info("Exporting third platform list...")
            self._logger.debug(
                "%s %s --> %s",
                method := "post",
                endpoint := api.API_ENDPOINTS["third_platform_list"],
                filename := "third_platform_list.json",
            )
            payload = {}
            await self._export(
                os.path.join(self.export_path, filename),
                await self.client.request(
                    method,
                    endpoint,
                    json=payload,
                ),
            )
            self._logger.info("Get token for user account...")
            self._logger.debug(
                "%s %s --> %s",
                method := "post",
                endpoint := api.API_ENDPOINTS["get_token_by_userid"],
                filename := "None",
            )
            payload = {}
            token = (
                (
                    await self.client.request(
                        method,
                        endpoint,
                        json=payload,
                    )
                    or {}
                )
                .get("data", {})
                .get("token","")
            )
            self._logger.info("Get Shelly status with token...")
            self._logger.debug(
                "%s %s --> %s",
                method := "post",
                endpoint := api.API_ENDPOINTS["get_shelly_status"],
                filename := "shelly_status.json",
            )
            payload = {"token": token}
            await self._export(
                os.path.join(self.export_path, filename),
                await self.client.request(
                    method,
                    endpoint,
                    json=payload,
                ),
            )

            # loop through all found sites
            for siteId, site in self.client.sites.items():
                self._logger.info("")
                self._logger.info(
                    "Exporting site specific data for site %s...",
                    self._randomize(siteId, "site_id"),
                )
                self._logger.info("Exporting scene info...")
                self._logger.debug(
                    "%s %s --> %s",
                    method := "post",
                    endpoint := api.API_ENDPOINTS["scene_info"],
                    filename := f"scene_{self._randomize(siteId,'site_id')}.json",
                )
                payload = {"site_id": siteId}
                await self._export(
                    os.path.join(self.export_path, filename),
                    await self.client.request(
                        method,
                        endpoint,
                        json=payload,
                    ),
                )
                self._logger.info("Exporting site detail...")
                admin = site.get("site_admin")
                try:
                    self._logger.debug(
                        "%s %s --> %s",
                        method := "post",
                        endpoint := api.API_ENDPOINTS["site_detail"],
                        filename
                        := f"site_detail_{self._randomize(siteId,'site_id')}.json",
                    )
                    if not admin:
                        self._logger.warning(
                            "Query requires account of site owner: %s", endpoint
                        )
                    else:
                        payload = {"site_id": siteId}
                        await self._export(
                            os.path.join(self.export_path, filename),
                            await self.client.request(
                                method,
                                endpoint,
                                json=payload,
                            ),
                        )
                except errors.AnkerSolixError as err:
                    self._logger.error(
                        "Method: %s, Endpoint: %s, Payload: %s\n%s: %s",
                        str(method).upper(),
                        endpoint,
                        str(payload).replace(siteId, "<siteId>"),
                        type(err),
                        err,
                    )
                self._logger.info("Exporting wifi list...")
                try:
                    self._logger.debug(
                        "%s %s --> %s",
                        method := "post",
                        endpoint := api.API_ENDPOINTS["wifi_list"],
                        filename
                        := f"wifi_list_{self._randomize(siteId,'site_id')}.json",
                    )
                    if not admin:
                        self._logger.warning(
                            "Query requires account of site owner: %s", endpoint
                        )
                    else:
                        payload = {"site_id": siteId}
                        await self._export(
                            os.path.join(self.export_path, filename),
                            await self.client.request(
                                method,
                                endpoint,
                                json=payload,
                            ),
                        )  # works only for site owners
                except errors.AnkerSolixError as err:
                    self._logger.error(
                        "Method: %s, Endpoint: %s, Payload: %s\n%s: %s",
                        str(method).upper(),
                        endpoint,
                        str(payload).replace(siteId, "<siteId>"),
                        type(err),
                        err,
                    )
                self._logger.info("Exporting installation...")
                try:
                    self._logger.debug(
                        "%s %s --> %s",
                        method := "post",
                        endpoint := api.API_ENDPOINTS["get_installation"],
                        filename
                        := f"installation_{self._randomize(siteId,'site_id')}.json",
                    )
                    payload = {"site_id": siteId}
                    await self._export(
                        os.path.join(self.export_path, filename),
                        await self.client.request(
                            method,
                            endpoint,
                            json=payload,
                        ),
                    )
                except errors.AnkerSolixError as err:
                    self._logger.error(
                        "Method: %s, Endpoint: %s, Payload: %s\n%s: %s",
                        str(method).upper(),
                        endpoint,
                        str(payload).replace(siteId, "<siteId>"),
                        type(err),
                        err,
                    )
                self._logger.info("Exporting site price...")
                try:
                    self._logger.debug(
                        "%s %s --> %s",
                        method := "post",
                        endpoint := api.API_ENDPOINTS["get_site_price"],
                        filename := f"price_{self._randomize(siteId,'site_id')}.json",
                    )
                    if not admin:
                        self._logger.warning(
                            "Query requires account of site owner: %s", endpoint
                        )
                    else:
                        payload = {"site_id": siteId}
                        await self._export(
                            os.path.join(self.export_path, filename),
                            await self.client.request(
                                method,
                                endpoint,
                                json=payload,
                            ),
                        )  # works only for site owners
                except errors.AnkerSolixError as err:
                    self._logger.error(
                        "Method: %s, Endpoint: %s, Payload: %s\n%s: %s",
                        str(method).upper(),
                        endpoint,
                        str(payload).replace(siteId, "<siteId>"),
                        type(err),
                        err,
                    )
                self._logger.info("Exporting device parameter type 4 settings...")
                try:
                    self._logger.debug(
                        "%s %s --> %s",
                        method := "post",
                        endpoint := api.API_ENDPOINTS["get_device_parm"],
                        filename
                        := f"device_parm_4_{self._randomize(siteId,'site_id')}.json",
                    )
                    if not admin:
                        self._logger.warning(
                            "Query requires account of site owner: %s", endpoint
                        )
                    else:
                        payload = {"site_id": siteId, "param_type": "4"}
                        await self._export(
                            os.path.join(self.export_path, filename),
                            await self.client.request(
                                method,
                                endpoint,
                                json=payload,
                            ),
                        )  # works only for site owners
                except errors.AnkerSolixError as err:
                    self._logger.error(
                        "Method: %s, Endpoint: %s, Payload: %s\n%s: %s",
                        str(method).upper(),
                        endpoint,
                        str(payload).replace(siteId, "<siteId>"),
                        type(err),
                        err,
                    )
                self._logger.info("Exporting device parameter type 6 settings...")
                try:
                    self._logger.debug(
                        "%s %s --> %s",
                        method := "post",
                        endpoint := api.API_ENDPOINTS["get_device_parm"],
                        filename
                        := f"device_parm_6_{self._randomize(siteId,'site_id')}.json",
                    )
                    if not admin:
                        self._logger.warning(
                            "Query requires account of site owner: %s", endpoint
                        )
                    else:
                        payload = {"site_id": siteId, "param_type": "6"}
                        await self._export(
                            os.path.join(self.export_path, filename),
                            await self.client.request(
                                method,
                                endpoint,
                                json=payload,
                            ),
                        )  # works only for site owners
                except errors.AnkerSolixError as err:
                    self._logger.error(
                        "Method: %s, Endpoint: %s, Payload: %s\n%s: %s",
                        str(method).upper(),
                        endpoint,
                        str(payload).replace(siteId, "<siteId>"),
                        type(err),
                        err,
                    )
                self._logger.info("Exporting OTA update info...")
                try:
                    self._logger.debug(
                        "%s %s --> %s",
                        method := "post",
                        endpoint := api.API_ENDPOINTS["get_ota_update"],
                        filename := "ota_update.json",
                    )
                    if not admin:
                        self._logger.warning(
                            "Query requires account of site owner: %s", endpoint
                        )
                    else:
                        payload = {"device_sn": "", "insert_sn": ""}
                        await self._export(
                            os.path.join(self.export_path, filename),
                            await self.client.request(
                                method,
                                endpoint,
                                json=payload,
                            ),
                        )  # works only for site owners
                except errors.AnkerSolixError as err:
                    self._logger.error(
                        "Method: %s, Endpoint: %s, Payload: %s\n%s: %s",
                        str(method).upper(),
                        endpoint,
                        str(payload),
                        type(err),
                        err,
                    )
                self._logger.info("Exporting site energy data for solarbank...")
                try:
                    self._logger.debug(
                        "%s %s --> %s",
                        method := "post",
                        endpoint := api.API_ENDPOINTS["energy_analysis"],
                        filename
                        := f"energy_solarbank_{self._randomize(siteId,'site_id')}.json",
                    )
                    payload = {
                        "site_id": siteId,
                        "device_sn": "",
                        "type": "week",
                        "device_type": "solarbank",
                        "start_time": (datetime.today() - timedelta(days=1)).strftime(
                            "%Y-%m-%d"
                        ),
                        "end_time": datetime.today().strftime("%Y-%m-%d"),
                    }
                    await self._export(
                        os.path.join(self.export_path, filename),
                        await self.client.request(
                            method,
                            endpoint,
                            json=payload,
                        ),
                    )  # works also for site members
                except errors.AnkerSolixError as err:
                    self._logger.error(
                        "Method: %s, Endpoint: %s, Payload: %s\n%s: %s",
                        str(method).upper(),
                        endpoint,
                        str(payload).replace(siteId, "<siteId>"),
                        type(err),
                        err,
                    )
                self._logger.info("Exporting site energy data for solar_production...")
                try:
                    self._logger.debug(
                        "%s %s --> %s",
                        method := "post",
                        endpoint := api.API_ENDPOINTS["energy_analysis"],
                        filename
                        := f"energy_solar_production_{self._randomize(siteId,'site_id')}.json",
                    )
                    payload = {
                        "site_id": siteId,
                        "device_sn": "",
                        "type": "week",
                        "device_type": "solar_production",
                        "start_time": (datetime.today() - timedelta(days=1)).strftime(
                            "%Y-%m-%d"
                        ),
                        "end_time": datetime.today().strftime("%Y-%m-%d"),
                    }
                    await self._export(
                        os.path.join(self.export_path, filename),
                        await self.client.request(
                            method,
                            endpoint,
                            json=payload,
                        ),
                    )  # works also for site members
                except errors.AnkerSolixError as err:
                    self._logger.error(
                        "Method: %s, Endpoint: %s, Payload: %s\n%s: %s",
                        str(method).upper(),
                        endpoint,
                        str(payload).replace(siteId, "<siteId>"),
                        type(err),
                        err,
                    )
                for ch in range(1, 5):
                    self._logger.info(
                        "Exporting site energy data for solar_production PV%s...", ch
                    )
                    try:
                        self._logger.debug(
                            "%s %s --> %s",
                            method := "post",
                            endpoint := api.API_ENDPOINTS["energy_analysis"],
                            filename
                            := f"energy_solar_production_pv{ch}_{self._randomize(siteId,'site_id')}.json",
                        )
                        payload = {
                            "site_id": siteId,
                            "device_sn": "",
                            "type": "week",
                            "device_type": f"solar_production_pv{ch}",
                            "start_time": (
                                datetime.today() - timedelta(days=1)
                            ).strftime("%Y-%m-%d"),
                            "end_time": datetime.today().strftime("%Y-%m-%d"),
                        }
                        data = (
                            await self.client.request(
                                method,
                                endpoint,
                                json=payload,
                            )
                            or {}
                        )
                        if not data or not data.get("data"):
                            self._logger.warning(
                                "No solar production energy available for PV%s, skipping remaining PV channel export...",
                                ch,
                            )
                            break
                        await self._export(
                            os.path.join(self.export_path, filename),
                            data,
                        )  # works also for site members
                    except errors.AnkerSolixError as err:
                        self._logger.error(
                            "Method: %s, Endpoint: %s, Payload: %s\n%s: %s",
                            str(method).upper(),
                            endpoint,
                            str(payload).replace(siteId, "<siteId>"),
                            type(err),
                            err,
                        )
                        self._logger.warning(
                            "No solar production energy available for PV%s, skipping PV channel export...",
                            ch,
                        )
                        break
                self._logger.info("Exporting site energy data for home_usage...")
                try:
                    self._logger.debug(
                        "%s %s --> %s",
                        method := "post",
                        endpoint := api.API_ENDPOINTS["energy_analysis"],
                        filename
                        := f"energy_home_usage_{self._randomize(siteId,'site_id')}.json",
                    )
                    payload = {
                        "site_id": siteId,
                        "device_sn": "",
                        "type": "week",
                        "device_type": "home_usage",
                        "start_time": (datetime.today() - timedelta(days=1)).strftime(
                            "%Y-%m-%d"
                        ),
                        "end_time": datetime.today().strftime("%Y-%m-%d"),
                    }
                    await self._export(
                        os.path.join(self.export_path, filename),
                        await self.client.request(
                            method,
                            endpoint,
                            json=payload,
                        ),
                    )  # works also for site members
                except errors.AnkerSolixError as err:
                    self._logger.error(
                        "Method: %s, Endpoint: %s, Payload: %s\n%s: %s",
                        str(method).upper(),
                        endpoint,
                        str(payload).replace(siteId, "<siteId>"),
                        type(err),
                        err,
                    )
                self._logger.info("Exporting site energy data for grid...")
                try:
                    self._logger.debug(
                        "%s %s --> %s",
                        method := "post",
                        endpoint := api.API_ENDPOINTS["energy_analysis"],
                        filename
                        := f"energy_grid_{self._randomize(siteId,'site_id')}.json",
                    )
                    payload = {
                        "site_id": siteId,
                        "device_sn": "",
                        "type": "week",
                        "device_type": "grid",
                        "start_time": (datetime.today() - timedelta(days=1)).strftime(
                            "%Y-%m-%d"
                        ),
                        "end_time": datetime.today().strftime("%Y-%m-%d"),
                    }
                    await self._export(
                        os.path.join(self.export_path, filename),
                        await self.client.request(
                            method,
                            endpoint,
                            json=payload,
                        ),
                    )  # works also for site members
                except errors.AnkerSolixError as err:
                    self._logger.error(
                        "Method: %s, Endpoint: %s, Payload: %s\n%s: %s",
                        str(method).upper(),
                        endpoint,
                        str(payload).replace(siteId, "<siteId>"),
                        type(err),
                        err,
                    )

            # loop through all devices
            for sn, device in self.client.devices.items():
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
                    try:
                        self._logger.debug(
                            "%s %s --> %s",
                            method := "post",
                            endpoint := api.API_ENDPOINTS["solar_info"],
                            filename := f"solar_info_{self._randomize(sn,'_sn')}.json",
                        )
                        payload = {"solarbank_sn": sn}
                        await self._export(
                            os.path.join(self.export_path, filename),
                            await self.client.request(
                                method,
                                endpoint,
                                json=payload,
                            ),
                        )
                    except errors.AnkerSolixError as err:
                        self._logger.error(
                            "Method: %s, Endpoint: %s, Payload: %s\n%s: %s",
                            str(method).upper(),
                            endpoint,
                            str(payload)
                            .replace(sn, "<deviceSn>")
                            .replace(siteId, "<siteId>"),
                            type(err),
                            err,
                        )

                    self._logger.info(
                        "Exporting compatible process info for solarbank..."
                    )
                    try:
                        self._logger.debug(
                            "%s %s --> %s",
                            method := "post",
                            endpoint := api.API_ENDPOINTS["compatible_process"],
                            filename
                            := f"compatible_process_{self._randomize(sn,'_sn')}.json",
                        )
                        payload = {"solarbank_sn": sn}
                        await self._export(
                            os.path.join(self.export_path, filename),
                            await self.client.request(
                                method,
                                endpoint,
                                json=payload,
                            ),
                        )
                    except errors.AnkerSolixError as err:
                        self._logger.error(
                            "Method: %s, Endpoint: %s, Payload: %s\n%s: %s",
                            str(method).upper(),
                            endpoint,
                            str(payload)
                            .replace(sn, "<deviceSn>")
                            .replace(siteId, "<siteId>"),
                            type(err),
                            err,
                        )

                self._logger.info("Exporting power cutoff settings...")
                try:
                    self._logger.debug(
                        "%s %s --> %s",
                        method := "post",
                        endpoint := api.API_ENDPOINTS["get_cutoff"],
                        filename := f"power_cutoff_{self._randomize(sn,'_sn')}.json",
                    )
                    if not admin:
                        self._logger.warning(
                            "Query requires account of site owner: %s", endpoint
                        )
                    else:
                        payload = {"site_id": siteId, "device_sn": sn}
                        await self._export(
                            os.path.join(self.export_path, filename),
                            await self.client.request(
                                method,
                                endpoint,
                                json=payload,
                            ),
                        )  # works only for site owners
                except errors.AnkerSolixError as err:
                    self._logger.error(
                        "Method: %s, Endpoint: %s, Payload: %s\n%s: %s",
                        str(method).upper(),
                        endpoint,
                        str(payload)
                        .replace(sn, "<deviceSn>")
                        .replace(siteId, "<siteId>"),
                        type(err),
                        err,
                    )
                self._logger.info("Exporting fittings...")
                try:
                    self._logger.debug(
                        "%s %s --> %s",
                        method := "post",
                        endpoint := api.API_ENDPOINTS["get_device_fittings"],
                        filename := f"device_fittings_{self._randomize(sn,'_sn')}.json",
                    )
                    if not admin:
                        self._logger.warning(
                            "Query requires account of site owner: %s", endpoint
                        )
                    else:
                        payload = {"site_id": siteId, "device_sn": sn}
                        await self._export(
                            os.path.join(self.export_path, filename),
                            await self.client.request(
                                method,
                                endpoint,
                                json=payload,
                            ),
                        )  # works only for site owners
                except errors.AnkerSolixError as err:
                    self._logger.error(
                        "Method: %s, Endpoint: %s, Payload: %s\n%s: %s",
                        str(method).upper(),
                        endpoint,
                        str(payload)
                        .replace(sn, "<deviceSn>")
                        .replace(siteId, "<siteId>"),
                        type(err),
                        err,
                    )
                self._logger.info("Exporting load...")
                try:
                    self._logger.debug(
                        "%s %s --> %s",
                        method := "post",
                        endpoint := api.API_ENDPOINTS["get_device_load"],
                        filename := f"device_load_{self._randomize(sn,'_sn')}.json",
                    )
                    if not admin:
                        self._logger.warning(
                            "Query requires account of site owner: %s", endpoint
                        )
                    else:
                        payload = {"site_id": siteId, "device_sn": sn}
                        await self._export(
                            os.path.join(self.export_path, filename),
                            await self.client.request(
                                method,
                                endpoint,
                                json=payload,
                            ),
                        )  # works only for site owners
                except errors.AnkerSolixError as err:
                    self._logger.error(
                        "Method: %s, Endpoint: %s, Payload: %s\n%s: %s",
                        str(method).upper(),
                        endpoint,
                        str(payload)
                        .replace(sn, "<deviceSn>")
                        .replace(siteId, "<siteId>"),
                        type(err),
                        err,
                    )
                self._logger.info("Exporting OTA update info for device...")
                try:
                    self._logger.debug(
                        "%s %s --> %s",
                        method := "post",
                        endpoint := api.API_ENDPOINTS["get_ota_update"],
                        filename := f"ota_update_{self._randomize(sn,'_sn')}.json",
                    )
                    payload = {"device_sn": sn, "insert_sn": ""}
                    await self._export(
                        os.path.join(self.export_path, filename),
                        await self.client.request(
                            method,
                            endpoint,
                            json=payload,
                        ),
                    )
                except errors.AnkerSolixError as err:
                    self._logger.error(
                        "Method: %s, Endpoint: %s, Payload: %s\n%s: %s",
                        str(method).upper(),
                        endpoint,
                        str(payload)
                        .replace(sn, "<deviceSn>")
                        .replace(siteId, "<siteId>"),
                        type(err),
                        err,
                    )
                self._logger.info("Exporting upgrade record for device...")
                try:
                    self._logger.debug(
                        "%s %s --> %s",
                        method := "post",
                        endpoint := api.API_ENDPOINTS["get_upgrade_record"],
                        filename
                        := f"get_upgrade_record_{self._randomize(sn,'_sn')}.json",
                    )
                    payload = {"device_sn": sn, "type": 1}
                    await self._export(
                        os.path.join(self.export_path, filename),
                        await self.client.request(
                            method,
                            endpoint,
                            json=payload,
                        ),
                    )
                except errors.AnkerSolixError as err:
                    self._logger.error(
                        "Method: %s, Endpoint: %s, Payload: %s\n%s: %s",
                        str(method).upper(),
                        endpoint,
                        str(payload)
                        .replace(sn, "<deviceSn>")
                        .replace(siteId, "<siteId>"),
                        type(err),
                        err,
                    )

                self._logger.info("Exporting device attributes...")
                try:
                    self._logger.debug(
                        "%s %s --> %s",
                        method := "post",
                        endpoint := api.API_ENDPOINTS["get_device_attributes"],
                        filename := f"device_attrs_{self._randomize(sn,'_sn')}.json",
                    )
                    payload = {
                        "device_sn": sn,
                        "attributes": [],  # Not clear if empty attributes list will list all attributes if there are any
                    }
                    await self._export(
                        os.path.join(self.export_path, filename),
                        await self.client.request(
                            method,
                            endpoint,
                            json=payload,
                        ),
                    )
                except errors.AnkerSolixError as err:
                    self._logger.error(
                        "Method: %s, Endpoint: %s, Payload: %s\n%s: %s",
                        str(method).upper(),
                        endpoint,
                        str(payload)
                        .replace(sn, "<deviceSn>")
                        .replace(siteId, "<siteId>"),
                        type(err),
                        err,
                    )

            self._logger.info("")
            self._logger.info("Exporting site rules...")
            self._logger.debug(
                "%s %s --> %s",
                method := "post",
                endpoint := api.API_ENDPOINTS["site_rules"],
                filename := "site_rules.json",
            )
            payload = {}
            await self._export(
                os.path.join(self.export_path, filename),
                await self.client.request(method, endpoint, json=payload),
            )
            self._logger.info("Exporting message unread status...")
            self._logger.debug(
                "%s %s --> %s",
                method := "get",
                endpoint := api.API_ENDPOINTS["get_message_unread"],
                filename := "message_unread.json",
            )
            payload = {}
            await self._export(
                os.path.join(self.export_path, filename),
                await self.client.request(
                    method,
                    endpoint,
                    json=payload,
                ),
            )

            # update the api dictionaries from exported files to use randomized input data
            # this is more efficient and allows validation of randomized data in export files
            # save real client cache data first
            old_sites = deepcopy(self.client.sites)
            old_devices = deepcopy(self.client.devices)
            self.client.testDir(self.export_path)
            self._logger.debug("Saved original client cache and testfolder.")
            await self.client.update_sites(fromFile=True)
            await self.client.update_site_details(fromFile=True)
            await self.client.update_device_details(fromFile=True)
            await self.client.update_device_energy(fromFile=True)
            # avoid randomizing dictionary export twice when imported from randomized files already
            self._logger.info("")
            self._logger.info("Exporting Api sites cache from files...")
            self._logger.debug(
                "Api sites cache --> %s",
                filename := "api_sites.json",
            )
            await self._export(
                os.path.join(self.export_path, filename),
                self.client.sites,
                skip_randomize=True,
            )
            self._logger.info("Exporting Api devices cache from files...")
            self._logger.debug(
                "Api devices cache --> %s",
                filename := "api_devices.json",
            )
            await self._export(
                os.path.join(self.export_path, filename),
                self.client.devices,
                skip_randomize=True,
            )
            # restore real client cache data
            # skip restore of default test dir since it may not exist
            # self.client.testDir(old_testdir)
            self.client.sites = old_sites
            self.client.devices = old_devices
            self._logger.debug(
                "Restored original sites and devices caches for api client.",
            )
            # restore old api delay
            if old_delay != self.request_delay:
                self.client.requestDelay(old_delay)
                self._logger.debug(
                    "Restored original client request delay to %s seconds.",
                    old_delay,
                )

            # remove queue file handler again before zipping folder
            self._logger.removeHandler(qh)
            self._logger.info("")
            self._logger.info(
                "Completed export of Anker Solix system data for account %s",
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
                head_tail = os.path.split(self.export_path)
                zipname = "_".join(
                    [
                        os.path.join(head_tail[0], head_tail[1]),
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
                            root_dir=head_tail[0],
                            base_dir=head_tail[1],
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
            if "_sn" in key or key in ["sn"]:
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
            elif "wifi_name" in key:
                idx = sum(1 for s in self._randomdata.values() if "wifi-network-" in s)
                randomstr = f"wifi-network-{idx+1}"
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
                    "site_id",
                    "trace_id",
                    "bt_ble_",
                    "wifi_name",
                    "home_load_data",
                    "param_data",
                    "device_name",
                ]
            ) or k in ["sn"]:
                data[k] = self._randomize(v, k)
        return data

    async def _export(
        self,
        filename: str,
        d: dict | None = None,
        skip_randomize: bool = False,
        randomkeys: bool = False,
    ) -> None:
        """Save dict data to given file."""

        if not d:
            d = {}
        if len(d) == 0:
            self._logger.warning(
                "WARNING: File %s not saved because JSON is empty",
                filename.replace(self.export_path, self.export_folder),
            )
            return
        if self.randomized and not skip_randomize:
            d = self._check_keys(d)
            # Randomize also the (nested) keys for dictionary export if required
            if randomkeys:
                d_copy = d.copy()
                for key, val in d.items():
                    # check first nested keys in dict values
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
                    filename.replace(self.export_path, self.export_folder),
                )
        except OSError as err:
            self._logger.error(
                "ERROR: Failed to save JSON to file %s: %s",
                filename.replace(self.export_path, self.export_folder),
                err,
            )
        return

    def get_random_mapping(
        self,
    ) -> dict[str, str]:
        """Get dict of randomized data mapping."""

        return self._randomdata
