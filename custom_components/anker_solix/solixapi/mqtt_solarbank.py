"""Solarbank MQTT device control methods for AnkerSolixApi.

This module contains control methods specific to the Anker Solix Solarbank device family.
These methods provide comprehensive device control via MQTT commands.
Solarbanks can also be controlled via Api, these methods cover settings only controllable via MQTT.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .apitypes import SolixDefaults
from .mqtt_device import SolixMqttDevice
from .mqttcmdmap import CMD_NAME, STATE_NAME, SolixMqttCommands

if TYPE_CHECKING:
    from .api import AnkerSolixApi

# Define supported Models for this class
MODELS = {"A17C0"}
# Define supported and validated controls per Model
FEATURES = {
    SolixMqttCommands.realtime_trigger: MODELS,
    SolixMqttCommands.temp_unit_switch: MODELS,
    SolixMqttCommands.sb_power_cutoff_select: MODELS,
}


class SolixMqttDeviceSolarbank(SolixMqttDevice):
    """Define the class to handle an Anker Solix MQTT device for controls."""

    def __init__(self, api_instance: AnkerSolixApi, device_sn: str) -> None:
        """Initialize."""
        self.models = MODELS
        self.features = FEATURES
        super().__init__(api_instance=api_instance, device_sn=device_sn)

    def validate_command_value(self, command_id: str, value: Any) -> bool:
        """Validate command value ranges for controls."""
        # TODO: Enhance validation rules to extract options or ranges from command description per model
        validation_rules = {
            SolixMqttCommands.realtime_trigger: lambda v: SolixDefaults.TRIGGER_TIMEOUT_MIN
            <= v
            <= SolixDefaults.TRIGGER_TIMEOUT_MAX,
            SolixMqttCommands.temp_unit_switch: lambda v: v in [0, 1],
            SolixMqttCommands.sb_power_cutoff_select: lambda v: v in [5, 10],
        }
        rule = validation_rules.get(command_id)
        return rule(value) if rule else True

    async def set_temp_unit(
        self,
        fahrenheit: bool,
        toFile: bool = False,
    ) -> bool | dict:
        """Set temperature unit via MQTT.

        Args:
            fahrenheit: True for Fahrenheit, False for Celsius
            toFile: If True, return mock response (for testing compatibility)

        Returns:
            dict: Mock response if successful, False otherwise

        Example:
            await mydevice.set_temp_unit(fahrenheit=False)  # Celsius

        """
        # response
        resp = {}
        ctrl1 = self.controls.get(SolixMqttCommands.temp_unit_switch) or {}
        cmd1 = ctrl1.get(CMD_NAME, "")
        # Validate command value
        fahrenheit = 1 if fahrenheit else 0 if fahrenheit is not None else None
        if fahrenheit is not None and not self.validate_command_value(cmd1, fahrenheit):
            self._logger.error(
                "Device %s %s control error - Invalid temperature unit fahrenheit value: %s",
                self.pn,
                self.sn,
                fahrenheit,
            )
            return False
        # Send MQTT commands
        if (
            fahrenheit is not None
            and cmd1
            and await self._send_mqtt_command(
                command=cmd1,
                parameters={"fahrenheit": fahrenheit},
                description=f"temperature unit set to {'Fahrenheit' if fahrenheit else 'Celsius'}",
                toFile=toFile,
            )
        ):
            if state_name := ctrl1.get(STATE_NAME):
                resp[state_name] = fahrenheit
        if toFile:
            self._filedata.update(resp)
        return resp or False

    async def set_power_cutoff(
        self,
        limit: int | str,
        toFile: bool = False,
    ) -> bool | dict:
        """Set temperature unit via MQTT.

        Args:
            limit: True for Fahrenheit, False for Celsius
            toFile: If True, return mock response (for testing compatibility)

        Returns:
            dict: Mock response if successful, False otherwise

        Example:
            await mydevice.set_temp_unit(fahrenheit=False)  # Celsius

        """
        # response
        resp = {}
        ctrl1 = self.controls.get(SolixMqttCommands.sb_power_cutoff_select) or {}
        cmd1 = ctrl1.get(CMD_NAME, "")
        # Validate command value
        limit = (
            int(limit)
            if str(limit).replace("-", "", 1).replace(".", "", 1).isdigit()
            else 10
        )
        if limit is not None and not self.validate_command_value(cmd1, limit):
            self._logger.error(
                "Device %s %s control error - Invalid temperature unit fahrenheit value: %s",
                self.pn,
                self.sn,
                limit,
            )
            return False
        # Send MQTT commands
        if (
            limit is not None
            and cmd1
            and await self._send_mqtt_command(
                command=cmd1,
                parameters={"limit": limit},
                description=f"Power cutoff set to {limit!s} %",
                toFile=toFile,
            )
        ):
            if state_name := ctrl1.get(STATE_NAME):
                resp[state_name] = limit
            else:
                resp["output_cutoff_data"] = limit
                resp["lowpower_input_data"] = 4 if limit == 5 else 5
                resp["input_cutoff_data"] = limit
        if toFile:
            self._filedata.update(resp)
        return resp or False
