"""MQTT basic device control methods for AnkerSolixApi.

This module contains common control methods for Anker Solix MQTT device classes.
Specific device classes should be inherited from this base class
It also provides an MQTT device factory to create correct device class instance depending on specific device
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

from .apitypes import SolixDefaults
from .mqtt import generate_mqtt_command
from .mqttcmdmap import COMMAND_LIST, COMMAND_NAME, SolixMqttCommands
from .mqttmap import SOLIXMQTTMAP

if TYPE_CHECKING:
    from .api import AnkerSolixApi

# Define supported Models for this class
MODELS = set()
# Define supported and validated controls per Model
FEATURES = {
    SolixMqttCommands.realtime_trigger: MODELS,
}


class SolixMqttDevice:
    """Define the base class to handle an Anker Solix MQTT device for controls."""

    models: set = MODELS
    features: dict = FEATURES
    pn: str = ""

    def __init__(self, api_instance: AnkerSolixApi, device_sn: str) -> None:
        """Initialize."""
        self.api: AnkerSolixApi = api_instance
        self.sn: str = device_sn or ""
        self.pn: str = self.pn or ""
        self.models = self.models or MODELS
        self.features = self.features or FEATURES
        self.testdir: str = self.api.testDir()
        self.device: dict = {}
        self.mqttdata: dict = {}
        self.controls: dict = {}
        self._filedata: dict = {}
        self._logger = api_instance.logger()
        # initialize device data
        self.update_device(device=self.api.devices.get(self.sn) or {})
        # register callback for Api
        self.api.register_device_callback(deviceSn=self.sn, func=self.update_device)
        # create list of supported commands and options
        self._setup_controls()

    def _setup_controls(self) -> None:
        """Define controls and options for the device."""
        pn_map = SOLIXMQTTMAP.get(self.pn) or {}
        for cmd, pns in self.features.items():
            if not pns or self.pn in pns:
                # get defined message type for command
                msg, fields = (
                    [
                        (k, v)
                        for k, v in pn_map.items()
                        if cmd
                        in [
                            v.get(COMMAND_NAME),
                            *v.get(COMMAND_LIST, []),
                        ]
                    ][:1]
                    or [("", {})]
                )[0]
                # use default message type for update trigger command if not specified
                options = {
                    "msg_type": msg
                    or ("0057" if cmd == SolixMqttCommands.realtime_trigger else "")
                }
                # add all keys that are no byte fields
                options.update({k: v for k, v in fields.items() if len(k) > 2})
                self.controls[cmd] = options

    def update_device(self, device: dict) -> None:
        """Define callback for Api device updates."""
        if isinstance(device, dict) and device.get("device_sn") == self.sn:
            # Validate device type or accept any if not defined
            if (pn := device.get("device_pn")) in self.models or not self.models:
                self.pn = pn
                self.device = device
                self.mqttdata = device.get("mqtt_data", {})
            else:
                self._logger.error(
                    "Device %s %s is not in supported models %s for MQTT control",
                    self.pn,
                    self.sn,
                    self.models,
                )
                self.pn = ""
                self.device = {}
                self.mqttdata = {}

    def is_connected(self) -> bool:
        """Return actual MQTT connection state for device."""
        return bool(self.api.mqttsession and self.api.mqttsession.is_connected())

    def is_subscribed(self) -> bool:
        """Return actual MQTT subscription state for device."""
        return bool(
            self.is_connected()
            and {s for s in self.api.mqttsession.subscriptions if self.sn in s}
        )

    def validate_command_value(self, command_id: str, value: Any) -> bool:
        """Validate command value ranges for device controls."""
        # This has to be updated according to specific device commands and rules
        validation_rules = {
            "realtime_trigger": lambda v: SolixDefaults.TRIGGER_TIMEOUT_MIN
            <= v
            <= SolixDefaults.TRIGGER_TIMEOUT_MAX,
        }
        rule = validation_rules.get(command_id)
        return rule(value) if rule else True

    async def _send_mqtt_command(
        self,
        command: str,
        parameters: dict | None = None,
        description: str = "",
        toFile: bool = False,
    ) -> str | bool:
        """Send MQTT command to device.

        Args:
            self: The API instance
            command: Command name for get_command_data
            parameters: Command parameters
            description: Human-readable description for logging
            toFile: If true, only create command but don't send it

        Returns:
            str | bool: String with hex command if sent, False otherwise

        """
        # Generate command hex data
        if not (hexdata := generate_mqtt_command(command, parameters)):
            self._logger.error("Failed to generate MQTT command data for %s", command)
            return False
        if toFile:
            # print the decoded command
            self._logger.info(
                "TESTMODE: Generated command for MQTT device %s (%s) %s:\n%s",
                self.sn,
                self.pn,
                description,
                hexdata.decode(),
            )
        else:
            try:
                # Ensure MQTT session is started and connected
                if not self.is_connected():
                    if not await self.api.startMqttSession():
                        self._logger.error(
                            "Failed to start MQTT session for device control"
                        )
                        return False
                # Publish MQTT command
                _, mqtt_info = self.api.mqttsession.publish(self.device, hexdata.hex())
                # Wait for publish completion with timeout
                with contextlib.suppress(ValueError, RuntimeError):
                    mqtt_info.wait_for_publish(timeout=5)
                if not mqtt_info.is_published():
                    self._logger.error(
                        "Failed to publish MQTT command for device %s (%s): %s",
                        self.sn,
                        self.pn,
                        description,
                    )
                    return False
            except (ValueError, RuntimeError) as err:
                self._logger.error(
                    "Error sending MQTT command to device %s (%s): %s",
                    self.sn,
                    self.pn,
                    err,
                )
                return False
        self._logger.info("MQTT device %s (%s) %s", self.sn, self.pn, description)
        return True

    async def realtime_trigger(
        self,
        timeout: int = SolixDefaults.TRIGGER_TIMEOUT_DEF,
        toFile: bool = False,
    ) -> bool | dict:
        """Trigger device realtime data publish.

        Args:
            timeout: Seconds for realtime publish to stop
            toFile: If True, return mock response (for testing compatibility)

        Returns:
            bool: True if message was published, false otherwise

        Example:
            await mydevice.realtime_trigger(timeout=300)

        """
        # Validate command value
        if not self.validate_command_value(SolixMqttCommands.realtime_trigger, timeout):
            self._logger.error(
                "MQTT device %s (%s) control error - Invalid realtime trigger timeout: %s",
                self.sn,
                self.pn,
                timeout,
            )
            return False
        return await self._send_mqtt_command(
            command=SolixMqttCommands.realtime_trigger,
            parameters={"timeout": timeout},
            description=f"Real time trigger enabled with timeout of {timeout} seconds",
            toFile=toFile,
        )

    async def status_request(
        self,
        toFile: bool = False,
    ) -> bool | dict:
        """Send device status_request.

        Args:
            toFile: If True, return mock response (for testing compatibility)

        Returns:
            bool: True if message was published, false otherwise

        Example:
            await mydevice.status_request()

        """
        return await self._send_mqtt_command(
            command=SolixMqttCommands.status_request,
            description="status request sent",
            toFile=toFile,
        )

    def get_combined_cache(
        self,
        mqtt_unique: bool = False,
        api_prio: bool = False,
        fromFile: bool = False,
    ) -> dict:
        """Get copy of combined values from device actual Api and MQTT cache.

        Args:
            mqtt_unique: If True, provide only MQTT values not included in Api cache
            api_prio: If True, duplicate values will have the Api cache value, default is MQTT cache value
            fromFile: If True, include mock MQTT cache while testing from files

        Returns:
            dict: Combined Api and MQTT data cache

        Example:
            mqtt_unique = mydevice.get_combined_cache(mqtt_unique=True)

        """
        mqttdata = self.mqttdata | (self._filedata if fromFile else {})
        if mqtt_unique:
            # find duplicate keys and remove them from MQTT cache copy
            dup = set(self.device.keys()) & (set(mqttdata.keys()))
            for k in dup:
                mqttdata.pop(k, None)
            return mqttdata
        if api_prio:
            data = mqttdata | self.device
        else:
            data = self.device | mqttdata
        return data

    def get_status(
        self,
        fromFile: bool = False,
    ) -> dict:
        """Get actual MQTT device cache status.

        Args:
            fromFile: If True, include mock status while testing from files

        Returns:
            dict: Device status with all extracted MQTT message fields from
                Uses MQTT data cache for real-time values

        Example:
            status = mydevice.get_status()
            print(f"AC Output: {status.get('switch_ac_output_power')}")
            print(f"Battery SOC: {status.get('battery_soc')}%")

        """
        # Return copy of accumulated MQTT data cache, handle test mode
        return self.mqttdata | (self._filedata if fromFile else {})

    def print_status(
        self,
        fromFile: bool = False,
    ) -> dict:
        """Print and return actual MQTT device status.

        Args:
            fromFile: If True, include mock status while testing from files

        Returns:
            dict: Device status with all extracted MQTT message fields from
                Uses MQTT data cache for real-time values

        Example:
            mydevice.print_status()

        """
        # Return accumulated MQTT data cache, handle test mode
        data = self.get_status(fromFile=fromFile)
        self._logger.info(
            "MQTT device %s (%s) status%s:\n%s",
            self.sn,
            self.pn,
            " with optional MQTT test control changes" if fromFile else "",
            str(data),
        )
        return data
