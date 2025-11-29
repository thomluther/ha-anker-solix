"""MQTT device control methods for Anker Solix Portable Power Stations.

This module contains control methods specific to portable power stations (PPS).
These methods provide comprehensive device control via MQTT commands.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .apitypes import SolixDefaults
from .mqtt_device import SolixMqttDevice
from .mqttcmdmap import CMD_NAME, STATE_NAME, SolixMqttCommands

if TYPE_CHECKING:
    from .api import AnkerSolixApi

# Define supported Models for this class
MODELS = {"A1761", "A1790", "A1790P"}
# Define supported and validated MQTT command controls per Model
FEATURES = {
    SolixMqttCommands.realtime_trigger: MODELS,
    SolixMqttCommands.temp_unit_switch: MODELS,
    SolixMqttCommands.device_max_load: MODELS,
    SolixMqttCommands.device_timeout_minutes: MODELS,
    SolixMqttCommands.ac_charge_switch: MODELS,
    SolixMqttCommands.ac_charge_limit: MODELS,
    SolixMqttCommands.ac_output_switch: MODELS,
    SolixMqttCommands.ac_fast_charge_switch: {"A1761"},
    SolixMqttCommands.ac_output_mode_select: MODELS,
    SolixMqttCommands.dc_output_switch: MODELS,
    SolixMqttCommands.dc_12v_output_mode_select: MODELS,
    SolixMqttCommands.display_switch: MODELS,
    SolixMqttCommands.display_mode_select: MODELS,
    SolixMqttCommands.display_timeout_seconds: MODELS,
    SolixMqttCommands.light_mode_select: MODELS,
    SolixMqttCommands.port_memory_switch: {"A1790", "A1790P"},
}


class SolixMqttDevicePps(SolixMqttDevice):
    """Define the class to handle an Anker Solix MQTT device for PPS controls."""

    def __init__(self, api_instance: AnkerSolixApi, device_sn: str) -> None:
        """Initialize."""
        self.models = MODELS
        self.features = FEATURES
        super().__init__(api_instance=api_instance, device_sn=device_sn)

    def validate_command_value(self, command_id: str, value: Any) -> bool:
        """Validate command value ranges for device controls."""
        # TODO: Enhance validation rules to extract options or ranges from command description per model
        validation_rules = {
            SolixMqttCommands.realtime_trigger: lambda v: SolixDefaults.TRIGGER_TIMEOUT_MIN
            <= v
            <= SolixDefaults.TRIGGER_TIMEOUT_MAX,
            SolixMqttCommands.ac_output_switch: lambda v: v in [0, 1],
            SolixMqttCommands.dc_output_switch: lambda v: v in [0, 1],
            SolixMqttCommands.display_switch: lambda v: v in [0, 1],
            SolixMqttCommands.ac_charge_switch: lambda v: v in [0, 1],
            SolixMqttCommands.temp_unit_switch: lambda v: v in [0, 1],
            SolixMqttCommands.port_memory_switch: lambda v: v in [0, 1],
            SolixMqttCommands.display_mode_select: lambda v: v in [0, 1, 2, 3],
            SolixMqttCommands.light_mode_select: lambda v: v in [0, 1, 2, 3, 4],
            SolixMqttCommands.dc_12v_output_mode_select: lambda v: v in [0, 1],
            SolixMqttCommands.ac_output_mode_select: lambda v: v in [0, 1],
            SolixMqttCommands.device_timeout_minutes: lambda v: v
            in [0, 30, 60, 120, 240, 360, 720, 1440],
            SolixMqttCommands.display_timeout_seconds: lambda v: v
            in [20, 30, 60, 300, 1800],
            SolixMqttCommands.device_max_load: lambda v: 100 <= v <= 2000,
            SolixMqttCommands.ac_charge_limit: lambda v: 100 <= v <= 800,
            SolixMqttCommands.ac_fast_charge_switch: lambda v: v in [0, 1],
        }
        rule = validation_rules.get(command_id)
        return rule(value) if rule else True

    async def set_ac_output(
        self,
        enabled: bool | None = None,
        mode: int | str | None = None,
        toFile: bool = False,
    ) -> bool | dict:
        """Control AC output power via MQTT.

        Args:
            enabled: True to enable AC output, False to disable
            mode: AC output mode - 1=Normal, 0=Smart
                Can also be string: "normal", "smart"
            toFile: If True, return mock response (for testing compatibility)

        Returns:
            dict: Mock response if successful, False otherwise

        Example:
            await mydevice.set_ac_output(enabled=True)
            await mydevice.set_ac_output(mode=1)  # Normal
            await mydevice.set_ac_output(mode="smart")

        """
        # response
        resp = {}
        ctrl1 = self.controls.get(SolixMqttCommands.ac_output_switch) or {}
        cmd1 = ctrl1.get(CMD_NAME, "")
        ctrl2 = self.controls.get(SolixMqttCommands.ac_output_mode_select) or {}
        cmd2 = ctrl2.get(CMD_NAME, "")
        # Validate command values
        enabled = 1 if enabled else 0 if enabled is not None else None
        if enabled is not None and not self.validate_command_value(cmd1, enabled):
            self._logger.error(
                "Device %s %s control error - Invalid AC output enabled value: %s",
                self.pn,
                self.sn,
                enabled,
            )
            return False
        # Convert string mode to int
        mode_map = {"normal": 1, "smart": 0}
        original_mode = mode
        if isinstance(mode, str):
            if (mode := mode_map.get(mode.lower())) is None:
                self._logger.error(
                    "Device %s %s control error - Invalid AC output mode string: %s",
                    self.pn,
                    self.sn,
                    original_mode,
                )
                return False
        if mode is not None and not self.validate_command_value(cmd2, mode):
            self._logger.error(
                "Device %s %s control error - Invalid AC output mode value: %s",
                self.pn,
                self.sn,
                mode,
            )
            return False
        # Send MQTT commands
        if (
            enabled is not None
            and cmd1
            and await self._send_mqtt_command(
                command=cmd1,
                parameters={"enabled": enabled},
                description=f"AC output {'enabled' if enabled else 'disabled'}",
                toFile=toFile,
            )
        ):
            if toFile and (state_name := ctrl1.get(STATE_NAME)):
                resp[state_name] = enabled
        if (
            mode is not None
            and cmd2
            and await self._send_mqtt_command(
                command=cmd2,
                parameters={"mode": mode},
                description=f"AC output mode set to {original_mode if isinstance(original_mode, str) else mode}",
                toFile=toFile,
            )
        ):
            if state_name := ctrl2.get(STATE_NAME):
                # convert smart mode 0 to state value 2
                resp[state_name] = mode or 2
        if toFile:
            self._filedata.update(resp)
        return resp or False

    async def set_dc_output(
        self,
        enabled: bool | None = None,
        mode: int | str | None = None,
        toFile: bool = False,
    ) -> bool | dict:
        """Control DC output power via MQTT.

        Args:
            enabled: True to enable DC output, False to disable
            mode: DC output mode - 1=Normal, 0=Smart
                Can also be string: "normal", "smart"
            toFile: If True, return mock response (for testing compatibility)

        Returns:
            dict: Mock response if successful, False otherwise

        Example:
            await mydevice.set_dc_output(enabled=True)
            await mydevice.set_dc_output(mode=0)  # Smart
            await mydevice.set_dc_output(mode="normal")

        """
        # response
        resp = {}
        ctrl1 = self.controls.get(SolixMqttCommands.dc_output_switch) or {}
        cmd1 = ctrl1.get(CMD_NAME, "")
        ctrl2 = self.controls.get(SolixMqttCommands.dc_12v_output_mode_select) or {}
        cmd2 = ctrl1.get(CMD_NAME, "")
        # Validate command value
        enabled = 1 if enabled else 0 if enabled is not None else None
        if enabled is not None and not self.validate_command_value(cmd1, enabled):
            self._logger.error(
                "Device %s %s control error - Invalid DC output enabled value: %s",
                self.pn,
                self.sn,
                enabled,
            )
            return False
        # Convert string mode to int
        mode_map = {"normal": 1, "smart": 0}
        original_mode = mode
        if isinstance(mode, str):
            if (mode := mode_map.get(mode.lower())) is None:
                self._logger.error(
                    "Device %s %s control error - Invalid DC output mode string: %s",
                    self.pn,
                    self.sn,
                    original_mode,
                )
                return False
        if mode is not None and not self.validate_command_value(cmd2, mode):
            self._logger.error(
                "Device %s %s control error - Invalid DC output mode value: %s",
                self.pn,
                self.sn,
                mode,
            )
            return False
        # Send MQTT commands
        if (
            enabled is not None
            and cmd1
            and await self._send_mqtt_command(
                command=cmd1,
                parameters={"enabled": enabled},
                description=f"DC output {'enabled' if enabled else 'disabled'}",
                toFile=toFile,
            )
        ):
            if state_name := ctrl1.get(STATE_NAME):
                resp[state_name] = enabled
        if (
            mode is not None
            and cmd2
            and await self._send_mqtt_command(
                command=cmd2,
                parameters={"mode": mode},
                description=f"12V DC output mode set to {original_mode if isinstance(original_mode, str) else mode}",
                toFile=toFile,
            )
        ):
            if state_name := ctrl2.get(STATE_NAME):
                # convert smart mode 0 to state value 2
                resp[state_name] = mode or 2
        if toFile:
            self._filedata.update(resp)
        return resp or False

    async def set_display(
        self,
        enabled: bool | None = None,
        mode: int | str | None = None,
        timeout_seconds: int | None = None,
        toFile: bool = False,
    ) -> bool | dict:
        """Control display settings via MQTT.

        Args:
            enabled: True to turn display on, False to turn off
            mode: Display mode - 0=Off, 1=Low, 2=Medium, 3=High
                Can also be string: "off", "low", "medium", "high"
            timeout_seconds: Seconds before display goes off again
            toFile: If True, return mock response (for testing compatibility)

        Returns:
            dict: Mock response if successful, False otherwise

        Example:
            await mydevice.set_display(enabled=True)
            await mydevice.set_display(mode=2)  # Medium
            await mydevice.set_display(mode="high")
            await mydevice.set_display(timeout_seconds=20)

        """
        # response
        resp = {}
        ctrl1 = self.controls.get(SolixMqttCommands.display_switch) or {}
        cmd1 = ctrl1.get(CMD_NAME, "")
        ctrl2 = self.controls.get(SolixMqttCommands.display_mode_select) or {}
        cmd2 = ctrl2.get(CMD_NAME, "")
        ctrl3 = self.controls.get(SolixMqttCommands.display_timeout_seconds) or {}
        cmd3 = ctrl3.get(CMD_NAME, "")
        # Validate command value
        enabled = 1 if enabled else 0 if enabled is not None else None
        if enabled is not None and not self.validate_command_value(cmd1, enabled):
            self._logger.error(
                "Device %s %s control error - Invalid display enabled value: %s",
                self.pn,
                self.sn,
                enabled,
            )
            return False
        # Convert string mode to int
        mode_map = {"off": 0, "low": 1, "medium": 2, "high": 3}
        original_mode = mode
        if isinstance(mode, str):
            if (mode := mode_map.get(mode.lower())) is None:
                self._logger.error(
                    "Device %s %s control error - Invalid display mode string: %s",
                    self.pn,
                    self.sn,
                    original_mode,
                )
                return False
        if mode is not None and not self.validate_command_value(cmd2, mode):
            self._logger.error(
                "Device %s %s control error - Invalid display mode value: %s",
                self.pn,
                self.sn,
                mode,
            )
            return False
        # Validate timeout value
        if timeout_seconds is not None and not self.validate_command_value(
            cmd3, timeout_seconds
        ):
            self._logger.error(
                "Device %s %s control error - Invalid timeout value: %s",
                self.pn,
                self.sn,
                timeout_seconds,
            )
            return False

        # Send MQTT commands
        if (
            enabled is not None
            and cmd1
            and await self._send_mqtt_command(
                command=cmd1,
                parameters={"enabled": enabled},
                description=f"display {'enabled' if enabled else 'disabled'}",
                toFile=toFile,
            )
        ):
            if state_name := ctrl1.get(STATE_NAME):
                resp[state_name] = enabled
        if (
            mode is not None
            and cmd2
            and await self._send_mqtt_command(
                command=cmd2,
                parameters={"mode": mode},
                description=f"Display mode set to {original_mode if isinstance(original_mode, str) else mode}",
                toFile=toFile,
            )
        ):
            if state_name := ctrl2.get(STATE_NAME):
                resp[state_name] = mode
        if (
            timeout_seconds is not None
            and cmd3
            and await self._send_mqtt_command(
                command=cmd3,
                parameters={"timeout": timeout_seconds},
                description=f"Display timeout set to {timeout_seconds} seconds",
                toFile=toFile,
            )
        ):
            if state_name := ctrl2.get(STATE_NAME):
                resp[state_name] = mode
        if toFile:
            self._filedata.update(resp)
        return resp or False

    async def set_backup_charge(
        self,
        enabled: bool,
        toFile: bool = False,
    ) -> bool | dict:
        """Control backup charge mode via MQTT.

        Args:
            enabled: True to enable backup charge mode, False to disable
            toFile: If True, return mock response (for testing compatibility)

        Returns:
            dict: Mock response if successful, False otherwise

        Example:
            await mydevice.set_backup_charge(enabled=True)

        """
        # response
        resp = {}
        ctrl1 = self.controls.get(SolixMqttCommands.ac_charge_switch) or {}
        cmd1 = ctrl1.get(CMD_NAME, "")
        # Validate command value
        enabled = 1 if enabled else 0 if enabled is not None else None
        if enabled is not None and not self.validate_command_value(cmd1, enabled):
            self._logger.error(
                "Device %s %s control error - Invalid backup charge enabled value: %s",
                self.pn,
                self.sn,
                enabled,
            )
            return False
        # Send MQTT commands
        if (
            enabled is not None
            and cmd1
            and await self._send_mqtt_command(
                command=cmd1,
                parameters={"enabled": enabled},
                description=f"backup charge mode {'enabled' if enabled else 'disabled'}",
                toFile=toFile,
            )
        ):
            if state_name := ctrl1.get(STATE_NAME):
                resp[state_name] = enabled
        if toFile:
            self._filedata.update(resp)
        return resp or False

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

    async def set_light(
        self,
        mode: int | str,
        toFile: bool = False,
    ) -> bool | dict:
        """Set light mode via MQTT.

        Args:
            mode: Light mode - 0=Off, 1=Low, 2=Medium, 3=High, 4=Blinking
                Can also be string: "off", "low", "medium", "high", "blinking"
            toFile: If True, return mock response (for testing compatibility)

        Returns:
            dict: Mock response if successful, False otherwise

        Example:
            await mydevice.set_light_mode(mode=3)  # High
            await mydevice.set_light_mode(mode="blinking")

        """
        # response
        resp = {}
        ctrl1 = self.controls.get(SolixMqttCommands.light_mode_select) or {}
        cmd1 = ctrl1.get(CMD_NAME, "")
        # Convert string mode to int
        mode_map = {"off": 0, "low": 1, "medium": 2, "high": 3, "blinking": 4}
        original_mode = mode
        # Validate command value
        if isinstance(mode, str):
            if (mode := mode_map.get(mode.lower())) is None:
                self._logger.error(
                    "Device %s %s control error - Invalid light mode string: %s",
                    self.pn,
                    self.sn,
                    original_mode,
                )
                return False
        if mode is not None and not self.validate_command_value(cmd1, mode):
            self._logger.error(
                "Device %s %s control error - Invalid light mode value: %s",
                self.pn,
                self.sn,
                mode,
            )
            return False
        # Send MQTT commands
        if (
            mode is not None
            and cmd1
            and await self._send_mqtt_command(
                command=cmd1,
                parameters={"mode": mode},
                description=f"light mode set to {original_mode if isinstance(original_mode, str) else mode}",
                toFile=toFile,
            )
        ):
            if state_name := ctrl1.get(STATE_NAME):
                resp[state_name] = mode
        if toFile:
            self._filedata.update(resp)
        return resp or False

    async def set_device_timeout(
        self,
        timeout_minutes: int | None = None,
        toFile: bool = False,
    ) -> dict | bool:
        """Set device auto-off timeout.

        Args:
            timeout_minutes: Timeout in minutes (30-1440)
            toFile: If True, return mock response (for testing compatibility)

        Returns:
            dict: Response with device_timeout_minutes if successful, False otherwise

        Example:
            # Set 8 hour timeout
            result = await device.set_device_timeout(timeout_minutes=480)

        """
        # response
        resp = {}
        ctrl1 = self.controls.get(SolixMqttCommands.device_timeout_minutes) or {}
        cmd1 = ctrl1.get(CMD_NAME, "")
        # Validate command value
        if timeout_minutes is not None and not self.validate_command_value(
            cmd1, timeout_minutes
        ):
            self._logger.error(
                "Device %s %s control error - Invalid timeout value: %s",
                self.pn,
                self.sn,
                timeout_minutes,
            )
            return False
        if (
            timeout_minutes is not None
            and cmd1
            and await self._send_mqtt_command(
                command=cmd1,
                parameters={"timeout": timeout_minutes},
                description=f"Device timeout set to {timeout_minutes} minutes",
                toFile=toFile,
            )
        ):
            if state_name := ctrl1.get(STATE_NAME):
                resp[state_name] = timeout_minutes
        if toFile:
            self._filedata.update(resp)
        return resp or False

    async def set_max_load(
        self,
        max_watts: int | None = None,
        toFile: bool = False,
    ) -> dict | bool:
        """Set maximum AC output load in Watt.

        Args:
            max_watts: Maximum load in watts (100-2000)
            toFile: If True, return mock response (for testing compatibility)

        Returns:
            dict: Response with max_load if successful, False otherwise

        Example:
            # Set 800W max load
            result = await device.set_max_load(max_watts=800)

        """
        # response
        resp = {}
        ctrl1 = self.controls.get(SolixMqttCommands.device_max_load) or {}
        cmd1 = ctrl1.get(CMD_NAME, "")
        # Validate command value
        if max_watts is not None and not self.validate_command_value(cmd1, max_watts):
            self._logger.error(
                "Device %s %s control error - Invalid max load value: %s",
                self.pn,
                self.sn,
                max_watts,
            )
            return False
        if (
            max_watts is not None
            and cmd1
            and await self._send_mqtt_command(
                command=cmd1,
                parameters={"max_watts": max_watts},
                description=f"Max load set to {max_watts}W",
                toFile=toFile,
            )
        ):
            if state_name := ctrl1.get(STATE_NAME):
                resp[state_name] = max_watts
        if toFile:
            self._filedata.update(resp)
        return resp or False

    async def set_charge_limit(
        self,
        max_watts: int | None = None,
        toFile: bool = False,
    ) -> dict | bool:
        """Set maximum AC charge limit in Watt.

        Args:
            max_watts: Maximum load in watts (100-800)
            toFile: If True, return mock response (for testing compatibility)

        Returns:
            dict: Response with max_load if successful, False otherwise

        Example:
            # Set 800W charge limit
            result = await device.set_max_load(max_watts=800)

        """
        # response
        resp = {}
        ctrl1 = self.controls.get(SolixMqttCommands.ac_charge_limit) or {}
        cmd1 = ctrl1.get(CMD_NAME, "")
        # Validate command value
        if max_watts is not None and not self.validate_command_value(cmd1, max_watts):
            self._logger.error(
                "Device %s %s control error - Invalid AC charge limit value: %s",
                self.pn,
                self.sn,
                max_watts,
            )
            return False
        if (
            max_watts is not None
            and cmd1
            and await self._send_mqtt_command(
                command=cmd1,
                parameters={"max_watts": max_watts},
                description=f"AC charge limit set to {max_watts}W",
                toFile=toFile,
            )
        ):
            if state_name := ctrl1.get(STATE_NAME):
                resp[state_name] = max_watts
        if toFile:
            self._filedata.update(resp)
        return resp or False

    async def set_fast_charging(
        self,
        enabled: bool,
        toFile: bool = False,
    ) -> dict | bool:
        """Set Fast charging mode (e.g. 1300W max).

        Args:
            enabled: True to enable UltraFast charging, False to disable
            toFile: If True, return mock response (for testing compatibility)

        Returns:
            dict: Response with fast_charging status if successful, False otherwise

        Example:
            # Enable UltraFast charging (1300W max)
            result = await device.set_ultrafast_charging(enabled=True)

        """
        # response
        resp = {}
        ctrl1 = self.controls.get(SolixMqttCommands.ac_fast_charge_switch) or {}
        cmd1 = ctrl1.get(CMD_NAME, "")
        # Validate command value
        if enabled is not None and not self.validate_command_value(
            cmd1, 1 if enabled else 0
        ):
            self._logger.error(
                "Device %s %s control error - Invalid ultrafast charging value: %s",
                self.pn,
                self.sn,
                enabled,
            )
            return False
        if (
            enabled is not None
            and cmd1
            and await self._send_mqtt_command(
                command=cmd1,
                parameters={"enabled": enabled},
                description=f"Fast charging {'enabled' if enabled else 'disabled'}",
                toFile=toFile,
            )
        ):
            if state_name := ctrl1.get(STATE_NAME):
                resp[state_name] = enabled
        if toFile:
            self._filedata.update(resp)
        return resp or False

    async def set_port_memory(
        self,
        enabled: bool,
        toFile: bool = False,
    ) -> dict | bool:
        """Set port memory switch.

        Args:
            enabled: True to enable port memory, False to disable
            toFile: If True, return mock response (for testing compatibility)

        Returns:
            dict: Response with port memory status if successful, False otherwise

        Example:
            # Enable port memory switch
            result = await device.set_port_memory(enabled=True)

        """
        # response
        resp = {}
        ctrl1 = self.controls.get(SolixMqttCommands.port_memory_switch) or {}
        cmd1 = ctrl1.get(CMD_NAME, "")
        # Validate command value
        if enabled is not None and not self.validate_command_value(
            cmd1, 1 if enabled else 0
        ):
            self._logger.error(
                "Device %s %s control error - Invalid port memory value: %s",
                self.pn,
                self.sn,
                enabled,
            )
            return False
        if (
            enabled is not None
            and cmd1
            and await self._send_mqtt_command(
                command=cmd1,
                parameters={"enabled": enabled},
                description=f"Port memory {'enabled' if enabled else 'disabled'}",
                toFile=toFile,
            )
        ):
            if state_name := ctrl1.get(STATE_NAME):
                resp[state_name] = enabled
        if toFile:
            self._filedata.update(resp)
        return resp or False
