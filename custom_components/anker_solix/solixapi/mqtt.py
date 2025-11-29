"""Anker Solix MQTT class to handle an MQTT server client connection session for an account."""

import asyncio
from base64 import b64decode, b64encode
from collections.abc import Callable
import contextlib
from datetime import datetime, timedelta
from functools import partial
import json
import os
from pathlib import Path
import ssl
import tempfile
from typing import Any

import aiofiles
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

from .apitypes import DeviceHexDataTypes, SolixDefaults
from .mqttcmdmap import SolixMqttCommands
from .mqtttypes import (
    DeviceHexData,
    DeviceHexDataField,
    DeviceHexDataHeader,
    MqttDataStats,
)
from .session import AnkerSolixClientSession

MessageCallback = Callable[[Any, str, Any, bytes, str, str, bool], None]


class AnkerSolixMqttSession:
    """Define the class to handle an MQTT client for Anker MQTT server connection."""

    def __init__(self, apisession: AnkerSolixClientSession) -> None:
        """Initialize."""
        self._message_callback: MessageCallback | None = None
        self._temp_cert_files: list[tempfile.NamedTemporaryFile] = []
        self._logger = apisession.logger()
        # ensure folder for certificate file caching exists
        self._auth_cache_dir = Path(__file__).parent / "authcache"
        if not os.access(self._auth_cache_dir.parent, os.W_OK):
            self._auth_cache_dir = Path(tempfile.gettempdir()) / "authcache"
        self._auth_cache_dir.mkdir(parents=True, exist_ok=True)
        self.apisession: AnkerSolixClientSession = apisession
        self.client: mqtt.Client | None = None
        self.mqtt_stats: MqttDataStats | None = None
        self.host: str | None = None
        self.port: int = 8883
        # reset class variables for saving mqtt relevant data
        # Variable to save mqtt info from connected Api client
        self.mqtt_info: dict = {}
        # Variable to save all active subscriptions
        self.subscriptions: set = set()
        # Variable to save the devices that are to be triggered for realtime data
        self.triggered_devices: set = set()
        # Cache variable to save all received and known mqtt values per device
        self.mqtt_data: dict = {}
        # Variable to exchange MID for connections
        self.mids: dict = {}
        self.testdir: str = self.apisession.testDir()

    def on_connect(
        self,
        client: mqtt.Client,
        userdata: mqtt.Any,
        flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ):
        """Define callback when the client receives a CONNACK response from the server."""
        if reason_code.is_failure:
            self._logger.error(
                "Api %s MQTT session client failed to connect to Anker Solix MQTT server: %s(%s)",
                self.apisession.nickname,
                reason_code,
                reason_code.value,
            )
        else:
            self._logger.debug(
                "Api %s MQTT session client connected successfully to Anker Solix MQTT server",
                self.apisession.nickname,
            )
            # ReInitialize statistics
            self.mqtt_stats = MqttDataStats()
            # we should always subscribe from on_connect callback to be sure
            # our subscribe is persisted across reconnection.
            for topic in self.subscriptions:
                _, mid = self.client.subscribe(topic)
                # check if mid was recorded with subscription error
                if reason_code := self.mids.pop(str(mid), None):
                    # subscription failed although connected, remove topic from subscriptions
                    self.subscriptions.discard(topic)
                    self._logger.info(
                        "Api %s MQTT session client removed topic from subscriptions: %s",
                        self.apisession.nickname,
                        topic,
                    )
                else:
                    self._logger.info(
                        "Api %s MQTT session client subscribing to topic: %s",
                        self.apisession.nickname,
                        topic,
                    )

    def on_message(
        self, client: mqtt.Client, userdata: mqtt.Any, msg: mqtt.MQTTMessage
    ):
        """Define callback when a PUBLISH message is received from the server."""
        # update mqtt stats
        self.mqtt_stats.add_bytes(count=len(msg.payload))
        # default MQTT payload decode is UTF-8
        message = json.loads(msg.payload.decode())
        # Extract timestamp field from expected dictionary in message
        timestamp = datetime.fromtimestamp(
            (message.get("head") or {}).get("timestamp")
            if isinstance(message, dict)
            else 0
        ).strftime("%Y-%m-%d %H:%M:%S")
        # extract message payload
        payload = json.loads(message.get("payload") or "")
        # Third party models not included in payload
        if not (model := payload.get("pn") if isinstance(payload, dict) else None):
            # extract model from received topic
            model = (str(msg.topic).split("/")[2:3] or [None])[0]
        if not (device_sn := payload.get("sn") if isinstance(payload, dict) else None):
            # extract sn from received topic
            device_sn = (str(msg.topic).split("/")[3:4] or [None])[0]
        data = (payload.get("data")) if isinstance(payload, dict) else None
        # Decrypt base64-encoded encrypted data field from expected dictionary in message payload
        data = b64decode(data) if isinstance(data, str) else data
        self._logger.debug(
            "Api %s MQTT session client received message dated %s: %s on topic: %s",
            self.apisession.nickname,
            timestamp,
            message,
            msg.topic,
        )
        valueupdate = False
        # Update data stats
        if isinstance(data, bytes):
            # structure hex data
            hd = DeviceHexData(model=model, hexbytes=data)
            self.mqtt_stats.add_data(device_data=hd)
            # extract described values and save them in common mqtt data cache
            if device_sn and model and (values := hd.values()):
                # get existing mqtt data for device
                device = self.mqtt_data.get(device_sn) or {}
                topics = set(device.get("topics") or [])
                topics.add(msg.topic)
                self.mqtt_data[device_sn] = (
                    device
                    | values
                    | {"last_message": timestamp, "topics": list(topics)}
                )
                valueupdate = True
        elif data:
            # no encoded data in message, print object whatever it is
            self._logger.info(
                "Api %s MQTT session client received message from device %s (%s) with non-byte data:\n%s",
                self.apisession.nickname,
                device_sn,
                model,
                str(data),
            )
        # call message callback if defined
        if callable(self._message_callback):
            self._message_callback(
                self, msg.topic, message, data, model, device_sn, valueupdate
            )

    def on_disconnect(
        self,
        client: mqtt.Client,
        userdata: mqtt.Any,
        flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties | None,
    ):
        """Define callback when the client disconnects from the server."""
        self._logger.debug(
            "Api %s MQTT session client disconnected from Anker Solix MQTT server: %s(%s)",
            self.apisession.nickname,
            reason_code,
            reason_code.value,
        )

    def on_subscribe(
        self,
        client: mqtt.Client,
        userdata: Any,
        mid: int,
        reason_code_list: list[mqtt.ReasonCode],
        properties: mqtt.Properties | None,
    ):
        """Define callback when the client subscribes to a topic."""
        # Since we subscribe only for a single channel, reason_code_list contains a single entry
        if reason_code_list[0].is_failure:
            # save the message ID as reference for subscription failures
            self.mids[str(mid)] = reason_code_list[0]
            self._logger.error(
                "Api %s MQTT session client received failure while subscribing topic: %s(%s)",
                self.apisession.nickname,
                reason_code_list[0],
                reason_code_list[0].value,
            )
        else:
            self._logger.debug(
                "Api %s MQTT session client subscribed to topic with following QoS: %s",
                self.apisession.nickname,
                reason_code_list[0].value,
            )

    def on_unsubscribe(
        self,
        client: mqtt.Client,
        userdata: Any,
        mid: int,
        reason_code_list: list[mqtt.ReasonCode],
        properties: mqtt.Properties | None,
    ):
        """Define callback when the client unsubscribes from a topic."""
        # The reason_code_list is only present in MQTTv5,in MQTTv3 it will always be empty
        if not reason_code_list or not reason_code_list[0].is_failure:
            self._logger.debug(
                "Api %s MQTT session client unsubscribed from topic",
                self.apisession.nickname,
            )
        else:
            # save the message ID as reference for unsubscription failures
            self.mids[str(mid)] = reason_code_list[0]
            self._logger.error(
                "Api %s MQTT session client received failure while unsubscribing topic: %s(%s)",
                self.apisession.nickname,
                reason_code_list[0],
                reason_code_list[0].value,
            )

    def on_publish(
        self,
        client: mqtt.Client,
        userdata: Any,
        mid: int,
        reason_code: mqtt.ReasonCode,
        properties: mqtt.Properties,
    ):
        """Define callback when the client subscribes to a topic."""
        if reason_code.is_failure:
            # save the message ID as reference for publish failures
            self.mids[str(mid)] = reason_code
            self._logger.error(
                "Api %s MQTT session client received failure while publishing topic: %s(%s)",
                self.apisession.nickname,
                reason_code,
                reason_code.value,
            )
        else:
            self._logger.debug(
                "Api %s MQTT session client published topic with following QoS: %s",
                self.apisession.nickname,
                reason_code.value,
            )

    def message_callback(
        self, func: MessageCallback | None = ""
    ) -> MessageCallback | None:
        """Get or set the message callback for this session."""
        if callable(func) or func is None:
            self._message_callback = func
        return self._message_callback

    def get_topic_prefix(self, deviceDict: dict, publish: bool = False) -> str:
        """Get the MQTT topic prefix for provided device data."""
        topic = ""
        if (
            isinstance(deviceDict, dict)
            and self.mqtt_info
            and (sn := deviceDict.get("device_sn") or "")
            and (
                pn := deviceDict.get("device_pn")
                or deviceDict.get("product_code")
                or ""
            )
        ):
            topic = f"{'cmd' if publish else 'dt'}/{self.mqtt_info.get('app_name')}/{pn}/{sn}/"
        return topic

    def get_command_data(
        self,
        command: str = SolixMqttCommands.realtime_trigger,
        parameters: dict | None = None,
    ) -> str | None:
        """Compose the hex data for MQTT publish payload to Anker Solix devices."""
        if hexdata := generate_mqtt_command(command=command, parameters=parameters):
            self._logger.debug(
                "Api %s MQTT session generated hexdata for device mqtt command '%s':\n%s",
                self.apisession.nickname,
                command,
                hexdata.hex(":"),
            )
            return hexdata.hex()
        return None

    def publish(
        self,
        deviceDict: dict,
        hexbytes: bytearray | bytes | str,
        cmd: int = 17,
        sessId: str = "1234-5678",
    ) -> tuple[str, mqtt.MQTTMessageInfo]:
        """Publish an MQTT message with provided bytes and device data.

        Returns the published message string and MQTTMessageInfo class with the publish results.
        """
        # convert parameter as required
        if isinstance(hexbytes, str):
            hexbytes = bytes.fromhex(hexbytes.replace(":", ""))
        message = {
            "head": {
                "version": "1.0.0.1",
                "client_id": f"android-{self.mqtt_info.get('app_name')}-{self.mqtt_info.get('user_id')}-{self.mqtt_info.get('certificate_id')}",
                "sess_id": sessId,  # eg "5681-3252", can this be fix, or can it be obtained from client connection?
                "msg_seq": 1,
                "seed": 1,
                "timestamp": int(datetime.now().timestamp()),
                "cmd_status": 2,
                "cmd": cmd,
                "sign_code": 1,
                "device_pn": (
                    deviceDict.get("device_pn") or deviceDict.get("product_code") or ""
                ),
                "device_sn": (sn := deviceDict.get("device_sn") or ""),
            },
            "payload": json.dumps(
                {
                    "account_id": self.mqtt_info.get("user_id"),
                    "device_sn": sn,
                    # data field in payload must be b64 encoded
                    "data": b64encode(hexbytes or b"").decode("utf-8"),
                },
                separators=(",", ":"),
            ),
        }
        # generate message string and topic
        message = json.dumps(message, separators=(",", ":"))
        topic = f"{self.get_topic_prefix(deviceDict=deviceDict, publish=True)}req"
        # update stats
        if self.mqtt_stats:
            self.mqtt_stats.add_bytes(count=len(message), sent=True)
        # publish the message and return message and response
        return (message, self.client.publish(topic=topic, payload=message))

    def subscribe(self, topic: str) -> mqtt.ReasonCode | None:
        """Add topic to subscription set and subscribe if just added and client is already connected."""
        if topic and topic not in self.subscriptions:
            # Try to subscribe topic first if client already connected
            if self.is_connected():
                _, mid = self.client.subscribe(topic)
                # check if mid was recorded with subscription error
                if reason_code := self.mids.pop(str(mid), None):
                    # subscription failed although connected
                    self._logger.error(
                        "Api %s MQTT session client failed to subscribe to topic: %s",
                        self.apisession.nickname,
                        topic,
                    )
                else:
                    self._logger.info(
                        "Api %s MQTT session client subscribed to topic: %s",
                        self.apisession.nickname,
                        topic,
                    )
                    # Add topic to subscription set to ensure it will be subscribed again on reconnects
                    self.subscriptions.add(topic)
                return reason_code
            # Add topic to subscription set to ensure it will be subscribed on (re)connects
            self.subscriptions.add(topic)
            self._logger.debug(
                "Api %s MQTT session added new topic to subscriptions: %s",
                self.apisession.nickname,
                topic,
            )
        return None

    def unsubscribe(self, topic: str) -> mqtt.ReasonCode | None:
        """Remove topic from subscription set and unsubscribe if already connected."""
        if topic and topic in self.subscriptions:
            # Try to unsubscribe topic if client already connected
            if self.is_connected():
                _, mid = self.client.unsubscribe(topic)
                # check if mid was recorded with unsubscription error
                if reason_code := self.mids.pop(str(mid), None):
                    # Unsubscription failed although connected
                    self._logger.error(
                        "Api %s MQTT session client failed to unsubscribe from topic: %s",
                        self.apisession.nickname,
                        topic,
                    )
                else:
                    self._logger.info(
                        "Api %s MQTT session client unsubscribed from topic: %s",
                        self.apisession.nickname,
                        topic,
                    )
                # Always remove topic from subscription set
                self.subscriptions.discard(topic)
                return reason_code
            # Remove topic from subscription set to ensure it will not be subscribed again on reconnects
            self.subscriptions.discard(topic)
            self._logger.debug(
                "Api %s MQTT session removed topic from subscriptions: %s",
                self.apisession.nickname,
                topic,
            )
        return None

    async def connect_client_async(self, keepalive: int = 60) -> mqtt.Client | None:
        """Connect MQTT client, it will optionally being created if none configured yet."""
        if not (self.client or await self.create_client()):
            return None
        if not self.client.is_connected():
            # Stop any previous thread before starting new one
            self.client.loop_stop()
            # Use Non blocking connect with loop_start
            self.client.connect_async(
                host=self.host, port=self.port, keepalive=keepalive
            )
            # Start the loop to process network traffic and callbacks
            self.client.loop_start()
        # Wait briefly for the client to establish the connection
        # Paho's connect_async is non-blocking; some servers are fast but we still
        # need to wait until client.is_connected() becomes True before returning.
        interval = 0.1
        waited = 0.0
        while not self.client.is_connected() and waited < self.client.connect_timeout:
            await asyncio.sleep(interval)
            waited += interval
        return self.client

    def is_connected(self) -> bool:
        """Return MQTT client connection state if client was started already."""
        # return client connection state is client started
        return bool(self.client and self.client.is_connected())

    async def create_client(self) -> mqtt.Client | None:
        """Create and configure MQTT client with SSL/TLS certificates queried from Anker Solix api session."""
        try:
            # get latest mqtt info from api session
            self.mqtt_info = await self.apisession.get_mqtt_info()
            # extract host from info
            self.host = self.mqtt_info.get("endpoint_addr") or None
            if not self.host:
                self.mqtt_info = {}
                self.host = None
                self.client = None
                return self.client
            # Create client instance
            self.client = mqtt.Client(
                callback_api_version=CallbackAPIVersion.VERSION2,
                client_id=self.mqtt_info.get("thing_name"),
                clean_session=True,
            )
            # Set userdata for client
            self.client.user_data_set(self.subscriptions)
            # self.client.connect_timeout = 10
            # Set callbacks for client
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            self.client.on_disconnect = self.on_disconnect
            self.client.on_subscribe = self.on_subscribe
            self.client.on_unsubscribe = self.on_unsubscribe
            self.client.on_publish = self.on_publish
            # create temporary cert files
            self._temp_cert_files = []
            for certname in [
                "aws_root_ca1_pem",
                "certificate_pem",
                "private_key",
            ]:
                filename = str(
                    self._auth_cache_dir
                    / f"{self.apisession.email}_mqtt_{certname}.crt"
                )
                # remove file if existing
                if Path(filename).is_file():
                    with contextlib.suppress(Exception):
                        Path(filename).unlink()
                # Cache login response in file for reuse
                async with aiofiles.open(filename, "w", encoding="utf-8") as certfile:
                    await certfile.write(self.mqtt_info.get(certname))
                    self._logger.debug(
                        "Api %s MQTT session certificate dumped to file: %s",
                        self.apisession.nickname,
                        filename,
                    )
                    self._temp_cert_files.append(filename)
            # Configure SSL/TLS using temporary files
            if len(self._temp_cert_files) == 3:
                # run this in loop executor to avoid blocking calls to files
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    None,
                    partial(
                        self.client.tls_set,
                        ca_certs=self._temp_cert_files[0],
                        certfile=self._temp_cert_files[1],
                        keyfile=self._temp_cert_files[2],
                        cert_reqs=ssl.CERT_REQUIRED,
                        tls_version=ssl.PROTOCOL_TLS,
                        ciphers=None,
                    ),
                )
            else:
                self.client = None
            # initialize statistics
            self.mqtt_stats = MqttDataStats()
        except Exception:
            # Clean up files if there was an error
            self.cleanup()
            raise
        return self.client

    def _extract_mqtt_data(
        self,
        session,
        topic: str,
        message: Any,
        data: bytes,
        model: str,
    ) -> None:
        """Extract device data from mqtt messages and add it to the mqtt data cache."""
        timestamp = ""
        if isinstance(message, dict):
            timestamp = datetime.fromtimestamp(
                (message.get("head") or {}).get("timestamp") or 0
            ).strftime("%Y-%m-%d %H:%M:%S")
        device_sn = (str(topic).split("/")[1:2] or [""])[0]
        if isinstance(data, bytes) and device_sn and model:
            # structure hex data
            hd = DeviceHexData(model=model, hexbytes=data)
            # extract described values save them in common mqtt data cache
            if values := hd.values():
                device = self.mqtt_data.get(device_sn) or {}
                topics = set(device.get("topics") or []).add(topic)
                self.mqtt_data[device_sn] = (
                    device
                    | values
                    | {"last_message": timestamp, "topics": list(topics)}
                )
        elif data:
            # no encoded data in message, dump object whatever it is
            self._logger.info(
                "Api %s received MQTT message from device %s (%s) with non-byte data: %s",
                self.apisession.nickname,
                device_sn,
                model,
                str(data),
            )

    def cleanup(self):
        """Clean up client connections and delete certificate files."""
        if self.is_connected():
            self.client.loop_stop()
            self.client.disconnect()
        self.client = None
        self.subscriptions = set()
        self.triggered_devices = set()
        self._message_callback = None
        for filename in self._temp_cert_files:
            # remove file if existing
            if Path(filename).is_file():
                with contextlib.suppress(Exception):
                    Path(filename).unlink()
                    self._logger.debug(
                        "Api %s MQTT session deleted cert file: %s",
                        self.apisession.nickname,
                        filename,
                    )
        self._temp_cert_files = []

    def realtime_trigger(
        self,
        deviceDict: dict,
        timeout: int = SolixDefaults.TRIGGER_TIMEOUT_DEF,
    ) -> mqtt.MQTTMessageInfo:
        """Trigger MQTT real time data for Anker Solix device via MQTT message."""

        return self.publish(
            deviceDict=deviceDict,
            hexbytes=self.get_command_data(
                command=SolixMqttCommands.realtime_trigger,
                parameters={"timeout": timeout},
            ),
        )[1]

    async def message_poller(
        self,
        topics: set,
        trigger_devices: set,
        msg_callback: Callable | None = None,
        timeout: int = 120,
    ) -> None:
        """Run MQTT message poller and optional device update trigger in background.

        topics must be a shared mutable object containing the topics be subscribed for MQTT message updates.
        real_time_devices must be a shared mutable object containing the device serials which should trigger real time updates.
        The update trigger will be refreshed automatically while poller is running.
        msg_callback is the function that will be called back upon received mqtt data with following parms:
        Optional timeout specifies how long devices should publish real time updates before trigger must be resent.
        topic: str, message: Any, data: bytes, model: str
        """
        try:
            # register message callback function
            if msg_callback and not self.message_callback(func=msg_callback):
                self._logger.error(
                    "Api %s MQTT session message callback is not callable: %s",
                    self.apisession.nickname,
                    msg_callback,
                )
                self.cleanup()
                return False
            client = await self.connect_client_async()
            if client and not client.is_connected():
                self._logger.error(
                    "Api %s MQTT session failed connection to Anker Solix MQTT server %s: %s",
                    self.apisession.nickname,
                    self.host,
                    self.port,
                )
                self.cleanup()
                return False
            self._logger.debug(
                "Api %s MQTT session connected successfully to Anker Solix MQTT server %s: %s",
                self.apisession.nickname,
                self.host,
                self.port,
            )
            subscribed_topics = set()
            subscribed_devices = set()
            triggered_devices = set()
            # register devices to be triggered for real time data
            self.triggered_devices = trigger_devices
            start = datetime.now() - timedelta(seconds=timeout)
            while True:
                # Update subscribed topics
                if topics != subscribed_topics:
                    subscribed_devices = set()
                    # unsubscribe removed topics
                    for topic in subscribed_topics - topics:
                        self.unsubscribe(topic)
                    # subscribe topics and track subscribed devices
                    for topic in topics.copy():
                        parts = str(topic).split("/")
                        if (pn := (parts[2:3] or [None])[0]) and (
                            sn := (parts[3:4] or [None])[0]
                        ):
                            if (resp := self.subscribe(topic)) and resp.is_failure:
                                # remove topic from shared mutable subscription tracker
                                topics.discard(topic)
                            else:
                                # add successfully subscribed device
                                subscribed_devices.add((sn, pn))
                    subscribed_topics = topics.copy()
                # check if updates must be retriggered, also upon changes in trigger devices
                if (
                    restart := int((datetime.now() - start).total_seconds()) + 5
                    >= timeout
                ) or trigger_devices - triggered_devices:
                    # republish update trigger to subscribed and yet untriggered devices
                    for sn, pn in subscribed_devices:
                        if sn in (
                            trigger_devices
                            if restart
                            else trigger_devices - triggered_devices
                        ):
                            message, response = self.publish(
                                deviceDict={
                                    "device_sn": sn,
                                    "device_pn": pn,
                                },
                                hexbytes=self.get_command_data(
                                    command=SolixMqttCommands.realtime_trigger,
                                    parameters={"timeout": timeout},
                                ),
                            )
                            self._logger.debug(
                                "Api %s MQTT session published message: %s\n%s",
                                self.apisession.nickname,
                                response,
                                message,
                            )
                    triggered_devices = trigger_devices.copy()
                    # restart timeout interval
                    if restart:
                        start = datetime.now()
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            self._logger.info(
                "Api %s MQTT session message poller was cancelled",
                self.apisession.nickname,
            )
            self.cleanup()

    async def file_poller(
        self,
        folderdict: dict,
        speed: float = 1,
        msg_callback: Callable | None = None,
    ) -> None:
        """Run MQTT message poller from files for the active folder defined in provided folder dict.

        The poller will cycle through all recorded messages of subscribed devices and call
        the msg_callback function at corresponding delays.
        The messages will repeat after the last message was used for the callback.
        The speed parameter can be used to increase or decrease the runtime through existing messages.
        To change the speed at poller runtime, specify the speed key in the referenced folder dict
        """
        if not isinstance(folderdict, dict):
            return None
        try:
            # register message callback function
            if msg_callback and not self.message_callback(func=msg_callback):
                self._logger.error(
                    "Api %s MQTT session message callback is not callable: %s",
                    self.apisession.nickname,
                    msg_callback,
                )
                return False
            # initialize MQTT statistics for file poller
            self.mqtt_stats = MqttDataStats()
            active_folder: str | None = None
            timestamps = []
            # merge initial speed options
            if (newspeed := folderdict.get("speed")) and isinstance(
                newspeed, float | int
            ):
                speed = newspeed
            else:
                folderdict["speed"] = speed
            while True:
                # Update active folder and reset msg cycle
                if active_folder != folderdict.get("folder"):
                    active_folder = None
                    active_msgs = {}
                    timestamps = []
                    time_idx = 0
                    duration = 0
                    addtime = 0
                    speedstart = 0
                    if folderdict:
                        active_folder = folderdict.get("folder")
                        # create new cache for saved messages
                        files = await self.get_mqtt_files(folder=active_folder or None)
                        for file in files:
                            for timestr, message in (
                                await self.loadFromFile(filename=file)
                            ).items():
                                if (
                                    timestamp := int(
                                        datetime.fromisoformat(timestr).timestamp()
                                    )
                                    if timestr
                                    else 0
                                ):
                                    active_msgs[timestamp] = (
                                        active_msgs.get(timestamp) or []
                                    ) + [message]
                        # sort messages
                        if timestamps := sorted(active_msgs.keys()):
                            # get messages duration, 60 seconds at least for a cycle
                            duration = max(
                                60, timestamps[len(timestamps) - 1] - timestamps[0]
                            )
                            cycleoffset = datetime.now().timestamp() - timestamps[0]
                            addtime = 0
                            speedstart = timestamps[0]
                            # write cycle progress into folderdict
                            folderdict["progress"] = 0
                            folderdict["duration"] = duration
                if timestamps:
                    cycle_now = (
                        speedstart
                        + (datetime.now().timestamp() - cycleoffset - speedstart)
                        * speed
                    )
                    while (
                        time_idx < len(timestamps) and timestamps[time_idx] <= cycle_now
                    ):
                        # write cycle progress into folderdict
                        folderdict["progress"] = round(
                            (timestamps[time_idx] - timestamps[0]) / duration * 100, 2
                        )
                        # simulate mqtt messages for timestamp
                        for message in active_msgs.get(timestamps[time_idx]) or []:
                            self._logger.debug(
                                "Api %s MQTT session loaded message from %s:\n%s",
                                self.apisession.nickname,
                                datetime.fromtimestamp(timestamps[time_idx]).strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                ),
                                message,
                            )
                            # mock timestamp in message for subsequent cycles
                            if addtime > 0 and (
                                timestamp := (message.get("head") or {}).get(
                                    "timestamp"
                                )
                            ):
                                message["head"]["timestamp"] = int(timestamp + addtime)
                            # simulate MQTT message
                            mqtt_msg = mqtt.MQTTMessage(
                                topic=message.pop("topic", "").encode()
                            )
                            mqtt_msg.payload = json.dumps(message).encode()
                            self.on_message(client=None, userdata=None, msg=mqtt_msg)
                        time_idx += 1
                    # check for cycle reset with 5 sec gap after last message
                    if (
                        time_idx >= len(timestamps)
                        and (cycle_now - timestamps[0]) >= duration + 5
                    ):
                        time_idx = 0
                        # reset cycle offset with 5 sec gap between last and first message
                        cycleoffset = datetime.now().timestamp() - timestamps[0]
                        addtime += duration + 5
                        speedstart = timestamps[0]
                    # check for speed change at runtime
                    if (newspeed := folderdict.get("speed")) and speed != newspeed:
                        # reset the offset into the cycle
                        speed = newspeed
                        speedstart = timestamps[max(0, time_idx - 1)]
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            self._logger.info(
                "Api %s MQTT session file poller was cancelled",
                self.apisession.nickname,
            )

    async def get_mqtt_files(self, folder: str | Path) -> list:
        """Get actual list of mqtt message files from provided folder."""
        if isinstance(folder, str):
            folder = Path(folder)
        if isinstance(folder, Path) and folder.is_dir():
            loop = asyncio.get_running_loop()
            contentlist = await loop.run_in_executor(None, os.scandir, folder)
            return [
                (folder / f.name).absolute()
                for f in contentlist
                if f.is_file() and f.name.startswith("mqtt_msg_")
            ]
        return []

    async def loadFromFile(
        self, filename: str | Path, starttime: str | datetime | None = None
    ) -> dict:
        """Load all or optionally the first MQTT message after starttime from given file for testing.

        It will return a dict with message timestamp and the message object itself.
        """
        filename = str(filename)
        messages = {}
        if isinstance(starttime, datetime):
            starttime = starttime.strftime("%Y-%m-%d %H:%M:%S")
        elif not isinstance(starttime, str):
            starttime = None
        try:
            if Path(filename).is_file():
                async with aiofiles.open(filename, encoding="utf-8") as file:
                    async for line in file:
                        message = json.loads(line.strip())
                        if isinstance(message, dict):
                            msgtime = str(message.pop("msg_time", ""))
                            if not starttime:
                                messages[msgtime] = message
                            elif msgtime and msgtime >= starttime:
                                messages[msgtime] = message
                                return messages
        except OSError as err:
            self._logger.error(
                "ERROR: Failed to load MQTT messages from file %s\n%s", filename, err
            )
        return messages

    async def saveToFile(
        self, filename: str | Path, data: dict | None = None, append: bool = True
    ) -> bool:
        """Save MQTT message to given file for testing."""
        filename = str(filename)
        if not isinstance(data, dict):
            data = {}
        try:
            async with aiofiles.open(
                filename, "a" if append else "w", encoding="utf-8"
            ) as file:
                # add message timestamp to data
                await file.write(
                    json.dumps(
                        {"msg_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                        | data
                    )
                    + "\n"
                )
                self._logger.debug("Saved MQTT message to file %s:", filename)
                return True
        except OSError as err:
            self._logger.error(
                "ERROR: Failed to save MQTT message to file %s\n%s", filename, err
            )
            return False


def generate_mqtt_command(  # noqa: C901
    command: str = SolixMqttCommands.realtime_trigger, parameters: dict | None = None
) -> DeviceHexData | None:
    r"""Compose the hex data for MQTT publish payload to Anker Solix devices.

    Hex command example for update trigger:
    '==================== Publish Header for update trigger ========================
    ff 09   : 2 Byte Anker Solix message marker (supposed 'ff 09')
    1f 00   : 2 Byte total message length (31) in Bytes (Little Endian format)
    03 00 0f: 3 Byte fixed message pattern (supposed `03 00 0f` for sending message)
    00 57   : 2 Byte message type pattern (varies per device model and message type)
    == Fields ==|- Value (Hex/Decode Options)=======================================
    Fld Len Typ    uIntLe/var     sIntLe
    a1  01  --  22
    └->   1 unk           34             -> fix
    a2  02  01  01
    └->   2 ui             1             -> Toggle updates on/off
    a3  05  03  2c:01:00:00
    └->   5 var                      300 -> Update timeout in sec
    fe  05  03  c8:d7:b6:68
    └->   5 var               1756813256 -> Unix Timestamp
    ==============================================================================='
    """

    hexdata = None
    if not isinstance(parameters, dict):
        parameters = {}

    # TODO: Add method to build command based on MQTT Map description

    if command == SolixMqttCommands.realtime_trigger:
        hexdata = DeviceHexData(msg_header=DeviceHexDataHeader(cmd_msg="0057"))
        hexdata.update_field(DeviceHexDataField(hexbytes="a10122"))
        hexdata.update_field(DeviceHexDataField(hexbytes="a2020101"))
        hexdata.update_field(
            DeviceHexDataField(
                f_name=bytes.fromhex("a3"),
                f_type=DeviceHexDataTypes.var.value,
                f_value=int(parameters.get("timeout") or 60).to_bytes(
                    length=4, byteorder="little"
                ),
            )
        )
        hexdata.add_timestamp_field()
    elif command == SolixMqttCommands.temp_unit_switch:
        # Temperature unit: Value 0/1 (0=Celsius, 1=Fahrenheit) (VALIDATED SB1 ✅)
        value = 1 if parameters.get("fahrenheit") else 0
        hexdata = DeviceHexData(msg_header=DeviceHexDataHeader(cmd_msg="0050"))
        hexdata.update_field(DeviceHexDataField(hexbytes="a10122"))
        hexdata.update_field(
            DeviceHexDataField(
                f_name=bytes.fromhex("a2"),
                f_type=DeviceHexDataTypes.ui.value,
                f_value=value.to_bytes(length=1, byteorder="little"),
            )
        )
        hexdata.add_timestamp_field()
    elif command == SolixMqttCommands.sb_power_cutoff_select:
        # Valid option 5 or 10 in % (VALIDATED SB1 ⚠️ Changed on device, but not in App! App needs additional change via Api)
        value = 5 if str(parameters.get("limit")) == "5" else 10
        lowpower = 4 if value == 5 else 5
        hexdata = DeviceHexData(msg_header=DeviceHexDataHeader(cmd_msg="0067"))
        hexdata.update_field(DeviceHexDataField(hexbytes="a10122"))
        # output_cutoff_data
        hexdata.update_field(
            DeviceHexDataField(
                f_name=bytes.fromhex("a2"),
                f_type=DeviceHexDataTypes.ui.value,
                f_value=value.to_bytes(length=1, byteorder="little"),
            )
        )
        # lowpower_input_data
        hexdata.update_field(
            DeviceHexDataField(
                f_name=bytes.fromhex("a3"),
                f_type=DeviceHexDataTypes.ui.value,
                f_value=lowpower.to_bytes(length=1, byteorder="little"),
            )
        )
        # input_cutoff_data
        hexdata.update_field(
            DeviceHexDataField(
                f_name=bytes.fromhex("a4"),
                f_type=DeviceHexDataTypes.ui.value,
                f_value=value.to_bytes(length=1, byteorder="little"),
            )
        )
        hexdata.add_timestamp_field()
    elif command.startswith("c1000x_"):
        # C1000X control commands using mobile app protocol patterns
        # These patterns were captured from actual mobile app MQTT traffic and validated

        if command == "c1000x_ac_output":
            # AC output control: Message type 004a (VALIDATED ✅)
            value = 1 if parameters.get("enabled", False) else 0
            hexdata = DeviceHexData(
                model="A1761", msg_header=DeviceHexDataHeader(cmd_msg="004a")
            )
            hexdata.update_field(DeviceHexDataField(hexbytes="a10122"))
            if value == 1:
                hexdata.update_field(DeviceHexDataField(hexbytes="a2020101"))
            else:
                hexdata.update_field(DeviceHexDataField(hexbytes="a2020100"))
        elif command == "c1000x_dc_output":
            # DC output control: Message type 004b (VALIDATED ✅)
            value = 1 if parameters.get("enabled", False) else 0
            hexdata = DeviceHexData(
                model="A1761", msg_header=DeviceHexDataHeader(cmd_msg="004b")
            )
            hexdata.update_field(DeviceHexDataField(hexbytes="a10122"))
            if value == 1:
                hexdata.update_field(DeviceHexDataField(hexbytes="a2020101"))
            else:
                hexdata.update_field(DeviceHexDataField(hexbytes="a2020100"))
        elif command == "c1000x_light_mode":
            # Light mode control: Message type 004f (VALIDATED ✅)
            mode = int(parameters.get("mode", 0))
            hexdata = DeviceHexData(
                model="A1761", msg_header=DeviceHexDataHeader(cmd_msg="004f")
            )
            hexdata.update_field(DeviceHexDataField(hexbytes="a10122"))
            mode_hex_map = {
                0: "a2020100",
                1: "a2020101",
                2: "a2020102",
                3: "a2020103",
                4: "a2020104",
            }
            mode_hex = mode_hex_map.get(mode, "a2020100")
            hexdata.update_field(DeviceHexDataField(hexbytes=mode_hex))
        elif command == "c1000x_display":
            # Display control: Message type 0052
            value = 1 if parameters.get("enabled", False) else 0
            hexdata = DeviceHexData(
                model="A1761", msg_header=DeviceHexDataHeader(cmd_msg="0052")
            )
            hexdata.update_field(DeviceHexDataField(hexbytes="a10122"))
            if value == 1:
                hexdata.update_field(DeviceHexDataField(hexbytes="a2020101"))
            else:
                hexdata.update_field(DeviceHexDataField(hexbytes="a2020100"))
        elif command == "c1000x_display_mode":
            # Display mode: Message type 004c (VALIDATED ✅)
            value = int(parameters.get("mode", 0))
            hexdata = DeviceHexData(
                model="A1761", msg_header=DeviceHexDataHeader(cmd_msg="004c")
            )
            hexdata.update_field(DeviceHexDataField(hexbytes="a10122"))
            mode_hex_map = {0: "a2020100", 1: "a2020101", 2: "a2020102", 3: "a2020103"}
            mode_hex = mode_hex_map.get(value, "a2020100")
            hexdata.update_field(DeviceHexDataField(hexbytes=mode_hex))
        elif command == "c1000x_temp_unit":
            # Temperature unit: Message type 0050
            value = 1 if parameters.get("fahrenheit", False) else 0
            hexdata = DeviceHexData(
                model="A1761",
                msg_header=DeviceHexDataHeader(
                    cmd_msg="0050"
                ),  # TODO: Update message type
            )
            hexdata.update_field(DeviceHexDataField(hexbytes="a10122"))
            hexdata.update_field(
                DeviceHexDataField(
                    f_name=bytes.fromhex("a2"),
                    f_type=DeviceHexDataTypes.ui.value,
                    f_value=value.to_bytes(length=1, byteorder="little"),
                )
            )
        elif command == "c1000x_dc_output_mode":
            # DC output mode: Message type 0076 (VALIDATED ✅)
            value = int(parameters.get("mode", 1))
            hexdata = DeviceHexData(
                model="A1761", msg_header=DeviceHexDataHeader(cmd_msg="0076")
            )
            hexdata.update_field(DeviceHexDataField(hexbytes="a10122"))
            if value == 1:
                hexdata.update_field(DeviceHexDataField(hexbytes="a2020101"))  # Normal
            else:
                hexdata.update_field(DeviceHexDataField(hexbytes="a2020100"))  # Smart
        elif command == "c1000x_ac_output_mode":
            # AC output mode: Message type 0077 (VALIDATED ✅)
            value = int(parameters.get("mode", 1))
            hexdata = DeviceHexData(
                model="A1761", msg_header=DeviceHexDataHeader(cmd_msg="0077")
            )
            hexdata.update_field(DeviceHexDataField(hexbytes="a10122"))
            if value == 1:
                hexdata.update_field(DeviceHexDataField(hexbytes="a2020101"))  # Normal
            else:
                hexdata.update_field(DeviceHexDataField(hexbytes="a2020100"))  # Smart
        elif command == "c1000x_max_load":
            # Max load: Message type 0044
            max_watts = int(parameters.get("max_watts", 1000))
            hexdata = DeviceHexData(
                model="A1761", msg_header=DeviceHexDataHeader(cmd_msg="0044")
            )
            hexdata.update_field(DeviceHexDataField(hexbytes="a10122"))
            hexdata.update_field(
                DeviceHexDataField(
                    f_name=bytes.fromhex("a2"),
                    f_type=DeviceHexDataTypes.sile.value,
                    f_value=max_watts.to_bytes(length=2, byteorder="little"),
                )
            )
        elif command == "c1000x_device_timeout":
            # Device timeout in minutes: Message type 0045
            timeout = int(parameters.get("timeout", 720))
            hexdata = DeviceHexData(
                model="A1761", msg_header=DeviceHexDataHeader(cmd_msg="0045")
            )
            hexdata.update_field(DeviceHexDataField(hexbytes="a10122"))
            hexdata.update_field(
                DeviceHexDataField(
                    f_name=bytes.fromhex("a2"),
                    f_type=DeviceHexDataTypes.sile.value,
                    f_value=timeout.to_bytes(length=2, byteorder="little"),
                )
            )
        elif command == "c1000x_display_timeout":
            # Device timeout in seconds: Message type 0046
            timeout = int(parameters.get("timeout", 20))
            hexdata = DeviceHexData(
                model="A1761", msg_header=DeviceHexDataHeader(cmd_msg="0046")
            )
            hexdata.update_field(DeviceHexDataField(hexbytes="a10122"))
            hexdata.update_field(
                DeviceHexDataField(
                    f_name=bytes.fromhex("a2"),
                    f_type=DeviceHexDataTypes.sile.value,
                    f_value=timeout.to_bytes(length=2, byteorder="little"),
                )
            )
        elif command == "c1000x_ultrafast_toggle":
            # UltraFast charging toggle: Message type 005e (CAPTURED FROM MOBILE APP)
            enabled = parameters.get("enabled", False)
            hexdata = DeviceHexData(
                model="A1761", msg_header=DeviceHexDataHeader(cmd_msg="005e")
            )
            hexdata.update_field(DeviceHexDataField(hexbytes="a10122"))
            # ON/OFF toggle pattern from mobile app capture
            if enabled:
                hexdata.update_field(DeviceHexDataField(hexbytes="a2020101"))  # ON
            else:
                hexdata.update_field(DeviceHexDataField(hexbytes="a2020100"))  # OFF
        # Add timestamp field for all C1000X commands
        if hexdata:
            hexdata.add_timestamp_field()

    elif command.startswith("f3800_"):
        # F3800 control commands (A1790P/A1790) - mimic C1000X logic, update model and message types if needed
        # For now, use same message types as C1000X (unless future changes are needed)
        if command == "f3800_ac_output":
            value = 1 if parameters.get("enabled", False) else 0
            hexdata = DeviceHexData(
                model="A1790P", msg_header=DeviceHexDataHeader(cmd_msg="004a")
            )
            hexdata.update_field(DeviceHexDataField(hexbytes="a10122"))
            if value == 1:
                hexdata.update_field(DeviceHexDataField(hexbytes="a2020101"))
            else:
                hexdata.update_field(DeviceHexDataField(hexbytes="a2020100"))
        elif command == "f3800_dc_output":
            value = 1 if parameters.get("enabled", False) else 0
            hexdata = DeviceHexData(
                model="A1790P", msg_header=DeviceHexDataHeader(cmd_msg="004b")
            )
            hexdata.update_field(DeviceHexDataField(hexbytes="a10122"))
            if value == 1:
                hexdata.update_field(DeviceHexDataField(hexbytes="a2020101"))
            else:
                hexdata.update_field(DeviceHexDataField(hexbytes="a2020100"))
        elif command == "f3800_light_mode":
            mode = int(parameters.get("mode", 0))
            hexdata = DeviceHexData(
                model="A1790P", msg_header=DeviceHexDataHeader(cmd_msg="004f")
            )
            hexdata.update_field(DeviceHexDataField(hexbytes="a10122"))
            mode_hex_map = {
                0: "a2020100",
                1: "a2020101",
                2: "a2020102",
                3: "a2020103",
            }
            mode_hex = mode_hex_map.get(mode, "a2020100")
            hexdata.update_field(DeviceHexDataField(hexbytes=mode_hex))
        elif command == "f3800_display":
            value = 1 if parameters.get("enabled", False) else 0
            hexdata = DeviceHexData(
                model="A1790P", msg_header=DeviceHexDataHeader(cmd_msg="0052")
            )
            hexdata.update_field(DeviceHexDataField(hexbytes="a10122"))
            if value == 1:
                hexdata.update_field(DeviceHexDataField(hexbytes="a2020101"))
            else:
                hexdata.update_field(DeviceHexDataField(hexbytes="a2020100"))
        elif command == "f3800_display_mode":
            value = int(parameters.get("mode", 0))
            hexdata = DeviceHexData(
                model="A1790P", msg_header=DeviceHexDataHeader(cmd_msg="004c")
            )
            hexdata.update_field(DeviceHexDataField(hexbytes="a10122"))
            mode_hex_map = {0: "a2020100", 1: "a2020101", 2: "a2020102", 3: "a2020103"}
            mode_hex = mode_hex_map.get(value, "a2020100")
            hexdata.update_field(DeviceHexDataField(hexbytes=mode_hex))
        elif command == "f3800_temp_unit":
            value = 1 if parameters.get("fahrenheit", False) else 0
            hexdata = DeviceHexData(
                model="A1790P", msg_header=DeviceHexDataHeader(cmd_msg="0050")
            )
            hexdata.update_field(DeviceHexDataField(hexbytes="a10122"))
            hexdata.update_field(DeviceHexDataField(hexbytes=f"a20201{value:02x}"))
        elif command == "f3800_dc_output_mode":
            value = int(parameters.get("mode", 1))
            hexdata = DeviceHexData(
                model="A1790P", msg_header=DeviceHexDataHeader(cmd_msg="0076")
            )
            hexdata.update_field(DeviceHexDataField(hexbytes="a10122"))
            if value == 1:
                hexdata.update_field(DeviceHexDataField(hexbytes="a2020101"))  # Normal
            else:
                hexdata.update_field(DeviceHexDataField(hexbytes="a2020100"))  # Off
        elif command == "f3800_ac_output_mode":
            value = int(parameters.get("mode", 1))
            hexdata = DeviceHexData(
                model="A1790P", msg_header=DeviceHexDataHeader(cmd_msg="0077")
            )
            hexdata.update_field(DeviceHexDataField(hexbytes="a10122"))
            if value == 1:
                hexdata.update_field(DeviceHexDataField(hexbytes="a2020101"))  # Normal
            else:
                hexdata.update_field(DeviceHexDataField(hexbytes="a2020100"))  # Off
        elif command == "f3800_device_timeout":
            timeout_minutes = int(parameters.get("timeout_minutes", 720))
            hexdata = DeviceHexData(
                model="A1790P", msg_header=DeviceHexDataHeader(cmd_msg="0045")
            )
            hexdata.update_field(DeviceHexDataField(hexbytes="a10122"))
            hexdata.update_field(
                DeviceHexDataField(
                    f_name=bytes.fromhex("a2"),
                    f_type=DeviceHexDataTypes.sile.value,
                    f_value=timeout_minutes.to_bytes(length=2, byteorder="little"),
                )
            )
        elif command == "f3800_max_load":
            max_watts = int(parameters.get("max_watts", 1800))
            hexdata = DeviceHexData(
                model="A1790P", msg_header=DeviceHexDataHeader(cmd_msg="0044")
            )
            hexdata.update_field(DeviceHexDataField(hexbytes="a10122"))
            hexdata.update_field(
                DeviceHexDataField(
                    f_name=bytes.fromhex("a2"),
                    f_type=DeviceHexDataTypes.sile.value,
                    f_value=max_watts.to_bytes(length=2, byteorder="little"),
                )
            )
        elif command == "f3800_port_memory":
            value = 1 if parameters.get("enabled", True) else 0
            hexdata = DeviceHexData(
                model="A1790P", msg_header=DeviceHexDataHeader(cmd_msg="0079")
            )
            hexdata.update_field(DeviceHexDataField(hexbytes="a10122"))
            hexdata.update_field(DeviceHexDataField(hexbytes=f"a20201{value:02x}"))
        # Add timestamp field for all F3800 commands
        if hexdata:
            hexdata.add_timestamp_field()

    return hexdata
