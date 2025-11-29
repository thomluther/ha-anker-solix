"""F3800(P) MQTT device control methods for AnkerSolixApi.

This module contains control methods specific to the Anker F3800(P) (A1790, A1790P) portable power station.
These methods provide comprehensive device control via MQTT commands.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .mqtt_device import SolixMqttDevice
from .mqttcmdmap import SolixMqttCommands

if TYPE_CHECKING:
    from .api import AnkerSolixApi

# Define supported Models for this class
MODELS = {"A1790P", "A1790"}
# Define supported and validated controls per Model
FEATURES = {
    SolixMqttCommands.realtime_trigger: MODELS,
    SolixMqttCommands.temp_unit_switch: MODELS,
    SolixMqttCommands.device_max_load: MODELS,
    SolixMqttCommands.device_timeout_minutes: MODELS,
    SolixMqttCommands.ac_charge_switch: MODELS,
    SolixMqttCommands.ac_charge_limit: MODELS,
    SolixMqttCommands.ac_output_switch: MODELS,
    SolixMqttCommands.ac_output_mode_select: MODELS,
    SolixMqttCommands.dc_output_switch: MODELS,
    SolixMqttCommands.dc_12v_output_mode_select: MODELS,
    SolixMqttCommands.display_switch: MODELS,
    SolixMqttCommands.display_mode_select: MODELS,
    SolixMqttCommands.light_mode_select: MODELS,
    SolixMqttCommands.port_memory_switch: MODELS,
}


class SolixMqttDeviceF3800(SolixMqttDevice):
    """Define the class to handle an Anker Solix F3800 MQTT device for controls."""

    def __init__(self, api_instance: AnkerSolixApi, device_sn: str) -> None:
        """Initialize."""
        self.models = MODELS
        self.features = FEATURES
        super().__init__(api_instance=api_instance, device_sn=device_sn)

    def validate_command_value(self, command_id: str, value: Any) -> bool:
        """Validate command value ranges for device controls."""
        validation_rules = {
            "realtime_trigger": lambda v: 30 <= v <= 600,
            "ac_output_control": lambda v: v in [0, 1],
            "dc_12v_output_control": lambda v: v in [0, 1],
            "display_control": lambda v: v in [0, 1],
            "backup_charge_control": lambda v: v in [0, 1],
            "temp_unit_control": lambda v: v in [0, 1],
            "display_mode_select": lambda v: v in [0, 1, 2, 3],
            "light_mode_select": lambda v: v in [0, 1, 2, 3, 4],
            "dc_output_mode_select": lambda v: v in [1, 2],
            "ac_output_mode_select": lambda v: v in [1, 2],
            "device_timeout_minutes": lambda v: 30 <= v <= 1440,
            "max_load": lambda v: 100 <= v <= 2000,
        }
        rule = validation_rules.get(command_id)
        return rule(value) if rule else True

    async def set_ac_output(
        self,
        enabled: bool | None = None,
        mode: int | str | None = None,
        toFile: bool = False,
    ) -> bool | dict:
        """Control F3800 AC output power via MQTT.

        Args:
            enabled: True to enable AC output, False to disable
            mode: AC output mode - 1=Normal, 2=Smart
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
        # Validate command value
        enabled = 1 if enabled else 0 if enabled is not None else None
        if enabled is not None and not self.validate_command_value(
            "ac_output_control", enabled
        ):
            self._logger.error(
                "Device %s %s control error - Invalid AC output enabled value: %s",
                self.pn,
                self.sn,
                enabled,
            )
            return False
        # Convert string mode to int
        mode_map = {"normal": 1, "smart": 2}
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
        if mode is not None and not self.validate_command_value(
            "ac_output_mode_select", mode
        ):
            self._logger.error(
                "Device %s %s control error - Invalid AC output mode value: %s",
                self.pn,
                self.sn,
                mode,
            )
            return False
        # Send MQTT commands
        if enabled is not None and await self._send_mqtt_command(
            command="f3800_ac_output",
            parameters={"enabled": enabled},
            description=f"AC output {'enabled' if enabled else 'disabled'}",
            toFile=toFile,
        ):
            resp["switch_ac_output_power"] = enabled
        if mode is not None and await self._send_mqtt_command(
            command="f3800_ac_output_mode",
            parameters={"mode": mode},
            description=f"AC output mode set to {original_mode if isinstance(original_mode, str) else mode}",
            toFile=toFile,
        ):
            resp["ac_output_mode"] = mode
        if toFile:
            self._filedata.update(resp)
        return resp or False

    async def set_dc_output(
        self,
        enabled: bool | None = None,
        mode: int | str | None = None,
        toFile: bool = False,
    ) -> bool | dict:
        """Control F3800 12V DC output power via MQTT.

        Args:
            enabled: True to enable 12V DC output, False to disable
            mode: DC output mode - 1=Normal, 2=Smart
                Can also be string: "normal", "smart"
            toFile: If True, return mock response (for testing compatibility)

        Returns:
            dict: Mock response if successful, False otherwise

        Example:
            await mydevice.set_dc_output(enabled=True)
            await mydevice.set_dc_output(mode=2)  # Smart
            await mydevice.set_dc_output(mode="normal")
        """
        # response
        resp = {}
        # Validate command value
        enabled = 1 if enabled else 0 if enabled is not None else None
        if enabled is not None and not self.validate_command_value(
            "dc_12v_output_control", enabled
        ):
            self._logger.error(
                "Device %s %s control error - Invalid DC output enabled value: %s",
                self.pn,
                self.sn,
                enabled,
            )
            return False
        # Convert string mode to int
        mode_map = {"normal": 1, "smart": 2}
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
        if mode is not None and not self.validate_command_value(
            "dc_output_mode_select", mode
        ):
            self._logger.error(
                "Device %s %s control error - Invalid DC output mode value: %s",
                self.pn,
                self.sn,
                mode,
            )
            return False
        # Send MQTT commands
        if enabled is not None and await self._send_mqtt_command(
            command="f3800_dc_output",
            parameters={"enabled": enabled},
            description=f"12V DC output {'enabled' if enabled else 'disabled'}",
            toFile=toFile,
        ):
            resp["dc_output_power_switch"] = enabled
        if mode is not None and await self._send_mqtt_command(
            command="f3800_dc_output_mode",
            parameters={"mode": mode},
            description=f"12V DC output mode set to {original_mode if isinstance(original_mode, str) else mode}",
            toFile=toFile,
        ):
            resp["dc_12v_output_mode"] = mode
        if toFile:
            self._filedata.update(resp)
        return resp or False

    async def set_display(
        self,
        enabled: bool | None = None,
        mode: int | str | None = None,
        toFile: bool = False,
    ) -> bool | dict:
        """Control F3800 display settings via MQTT.

        Args:
            enabled: True to turn display on, False to turn off
            mode: Display mode - 0=Off, 1=Low, 2=Medium, 3=High
                Can also be string: "off", "low", "medium", "high"
            toFile: If True, return mock response (for testing compatibility)

        Returns:
            dict: Mock response if successful, False otherwise

        Example:
            await mydevice.set_display(enabled=True)
            await mydevice.set_display(mode=2)  # Medium
            await mydevice.set_display(mode="high")
        """
        # response
        resp = {}
        # Validate command value
        enabled = 1 if enabled else 0 if enabled is not None else None
        if enabled is not None and not self.validate_command_value(
            "display_control", enabled
        ):
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
        if mode is not None and not self.validate_command_value(
            "display_mode_select", mode
        ):
            self._logger.error(
                "Device %s %s control error - Invalid display mode value: %s",
                self.pn,
                self.sn,
                mode,
            )
            return False
        # Send MQTT commands
        if enabled is not None and await self._send_mqtt_command(
            command="f3800_display",
            parameters={"enabled": enabled},
            description=f"display {'enabled' if enabled else 'disabled'}",
            toFile=toFile,
        ):
            resp["switch_display"] = enabled
        if mode is not None and await self._send_mqtt_command(
            command="f3800_display_mode",
            parameters={"mode": mode},
            description=f"display mode set to {original_mode if isinstance(original_mode, str) else mode}",
            toFile=toFile,
        ):
            resp["display_mode"] = mode
        if toFile:
            self._filedata.update(resp)
        return resp or False

    async def set_backup_charge(
        self,
        enabled: bool,
        toFile: bool = False,
    ) -> bool | dict:
        """Control F3800 backup charge mode via MQTT.

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
        # Validate command value
        enabled = 1 if enabled else 0 if enabled is not None else None
        if enabled is not None and not self.validate_command_value(
            "backup_charge_control", enabled
        ):
            self._logger.error(
                "Device %s %s control error - Invalid backup charge enabled value: %s",
                self.pn,
                self.sn,
                enabled,
            )
            return False
        # Send MQTT commands
        if enabled is not None and await self._send_mqtt_command(
            command="f3800_backup_charge",
            parameters={"enabled": enabled},
            description=f"backup charge mode {'enabled' if enabled else 'disabled'}",
            toFile=toFile,
        ):
            resp["backup_charge_switch"] = enabled
        if toFile:
            self._filedata.update(resp)
        return resp or False

    async def set_temp_unit(
        self,
        fahrenheit: bool,
        toFile: bool = False,
    ) -> bool | dict:
        """Set F3800 temperature unit via MQTT.

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
        # Validate command value
        fahrenheit = 1 if fahrenheit else 0 if fahrenheit is not None else None
        if fahrenheit is not None and not self.validate_command_value(
            "backup_charge_control", fahrenheit
        ):
            self._logger.error(
                "Device %s %s control error - Invalid temperature unit fahrenheit value: %s",
                self.pn,
                self.sn,
                fahrenheit,
            )
            return False
        # Send MQTT commands
        if fahrenheit is not None and await self._send_mqtt_command(
            command="f3800_temp_unit",
            parameters={"fahrenheit": fahrenheit},
            description=f"temperature unit set to {'Fahrenheit' if fahrenheit else 'Celsius'}",
            toFile=toFile,
        ):
            resp["temp_unit_fahrenheit"] = fahrenheit
        if toFile:
            self._filedata.update(resp)
        return resp or False

    async def set_light(
        self,
        mode: int | str,
        toFile: bool = False,
    ) -> bool | dict:
        """Set F3800 light mode via MQTT.

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
        if mode is not None and not self.validate_command_value(
            "light_mode_select", mode
        ):
            self._logger.error(
                "Device %s %s control error - Invalid light mode value: %s",
                self.pn,
                self.sn,
                mode,
            )
            return False
        # Send MQTT commands
        if mode is not None and await self._send_mqtt_command(
            command="f3800_light_mode",
            parameters={"mode": mode},
            description=f"light mode set to {original_mode if isinstance(original_mode, str) else mode}",
            toFile=toFile,
        ):
            resp["light_mode"] = mode
        if toFile:
            self._filedata.update(resp)
        return resp or False

    async def set_display_mode(
        self,
        mode: int | str,
        toFile: bool = False,
    ) -> bool | dict:
        """Set F3800 display brightness mode via MQTT.

        Args:
            mode: Display mode - 0=Off, 1=Low, 2=Medium, 3=High
                Can also be string: "off", "low", "medium", "high"
            toFile: If True, return mock response (for testing compatibility)

        Returns:
            dict: Mock response if successful, False otherwise

        Example:
            await mydevice.set_display_mode(mode=3)  # High
            await mydevice.set_display_mode(mode="medium")
        """
        resp = {}
        # Convert string mode to int
        mode_map = {"off": 0, "low": 1, "medium": 2, "high": 3}
        original_mode = mode
        # Validate command value
        if isinstance(mode, str):
            if (mode := mode_map.get(mode.lower())) is None:
                self._logger.error(
                    "Device %s %s control error - Invalid display mode string: %s",
                    self.pn,
                    self.sn,
                    original_mode,
                )
                return False
        if mode is not None and not self.validate_command_value(
            "display_mode_select", mode
        ):
            self._logger.error(
                "Device %s %s control error - Invalid display mode value: %s",
                self.pn,
                self.sn,
                mode,
            )
            return False
        # Send MQTT command
        if mode is not None and await self._send_mqtt_command(
            command="f3800_display_mode",
            parameters={"mode": mode},
            description=f"display mode set to {original_mode if isinstance(original_mode, str) else mode}",
            toFile=toFile,
        ):
            resp["display_mode"] = mode
        if toFile:
            self._filedata.update(resp)
        return resp or False

    async def set_dc_output_mode(
        self,
        mode: int | str,
        toFile: bool = False,
    ) -> bool | dict:
        """Set F3800 DC output mode via MQTT.

        Args:
            mode: DC output mode - 1=Normal, 2=Smart
                Can also be string: "normal", "smart"
            toFile: If True, return mock response (for testing compatibility)

        Returns:
            dict: Mock response if successful, False otherwise

        Example:
            await mydevice.set_dc_output_mode(mode=2)  # Smart
            await mydevice.set_dc_output_mode(mode="normal")
        """
        resp = {}
        # Convert string mode to int
        mode_map = {"normal": 1, "smart": 2}
        original_mode = mode
        # Validate command value
        if isinstance(mode, str):
            if (mode := mode_map.get(mode.lower())) is None:
                self._logger.error(
                    "Device %s %s control error - Invalid DC output mode string: %s",
                    self.pn,
                    self.sn,
                    original_mode,
                )
                return False
        if mode is not None and not self.validate_command_value(
            "dc_output_mode_select", mode
        ):
            self._logger.error(
                "Device %s %s control error - Invalid DC output mode value: %s",
                self.pn,
                self.sn,
                mode,
            )
            return False
        # Send MQTT command
        if mode is not None and await self._send_mqtt_command(
            command="f3800_dc_output_mode",
            parameters={"mode": mode},
            description=f"DC output mode set to {original_mode if isinstance(original_mode, str) else mode}",
            toFile=toFile,
        ):
            resp["dc_output_mode"] = mode
        if toFile:
            self._filedata.update(resp)
        return resp or False

    async def set_ac_output_mode(
        self,
        mode: int | str,
        toFile: bool = False,
    ) -> bool | dict:
        """Set F3800 AC output mode via MQTT.

        Args:
            mode: AC output mode - 1=Normal, 2=Smart
                Can also be string: "normal", "smart"
            toFile: If True, return mock response (for testing compatibility)

        Returns:
            dict: Mock response if successful, False otherwise

        Example:
            await mydevice.set_ac_output_mode(mode=2)  # Smart
            await mydevice.set_ac_output_mode(mode="normal")
        """
        resp = {}
        # Convert string mode to int
        mode_map = {"normal": 1, "smart": 2}
        original_mode = mode
        # Validate command value
        if isinstance(mode, str):
            if (mode := mode_map.get(mode.lower())) is None:
                self._logger.error(
                    "Device %s %s control error - Invalid AC output mode string: %s",
                    self.pn,
                    self.sn,
                    original_mode,
                )
                return False
        if mode is not None and not self.validate_command_value(
            "ac_output_mode_select", mode
        ):
            self._logger.error(
                "Device %s %s control error - Invalid AC output mode value: %s",
                self.pn,
                self.sn,
                mode,
            )
            return False
        # Send MQTT command
        if mode is not None and await self._send_mqtt_command(
            command="f3800_ac_output_mode",
            parameters={"mode": mode},
            description=f"AC output mode set to {original_mode if isinstance(original_mode, str) else mode}",
            toFile=toFile,
        ):
            resp["ac_output_mode"] = mode
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
        resp = {}
        if timeout_minutes is not None and not self.validate_command_value(
            "device_timeout_minutes", timeout_minutes
        ):
            self._logger.error(
                "Device %s %s control error - Invalid timeout value: %s",
                self.pn,
                self.sn,
                timeout_minutes,
            )
            return False
        if timeout_minutes is not None:
            if toFile or await self._send_mqtt_command(
                command="f3800_device_timeout",
                parameters={"timeout_minutes": timeout_minutes},
                description=f"Device timeout set to {timeout_minutes} minutes",
                toFile=toFile,
            ):
                resp["device_timeout_minutes"] = timeout_minutes
                if toFile:
                    self._filedata["device_timeout_minutes"] = timeout_minutes
        return resp or False

    async def set_max_load(
        self,
        max_watts: int | None = None,
        toFile: bool = False,
    ) -> dict | bool:
        """Set maximum AC input load (current limit).

        Args:
            max_watts: Maximum load in watts (100-2000)
            toFile: If True, return mock response (for testing compatibility)

        Returns:
            dict: Response with max_load if successful, False otherwise

        Example:
            # Set 800W max load
            result = await device.set_max_load(max_watts=800)
        """
        resp = {}
        if max_watts is not None and not self.validate_command_value(
            "max_load", max_watts
        ):
            self._logger.error(
                "Device %s %s control error - Invalid max load value: %s",
                self.pn,
                self.sn,
                max_watts,
            )
            return False
        if max_watts is not None:
            if toFile or await self._send_mqtt_command(
                command="f3800_max_load",
                parameters={"max_watts": max_watts},
                description=f"Max load set to {max_watts}W",
                toFile=toFile,
            ):
                resp["max_load"] = max_watts
                if toFile:
                    self._filedata["max_load"] = max_watts
        return resp or False
