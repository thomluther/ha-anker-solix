"""MQTT device control methods for Anker Solix Portable Power Stations.

This module contains control methods specific to portable power stations (PPS).
These methods provide comprehensive device control via MQTT commands.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .mqtt_device import SolixMqttDevice
from .mqttcmdmap import SolixMqttCommands

if TYPE_CHECKING:
    from .api import AnkerSolixApi

# Define supported Models for this class
MODELS = {
    "A1722",  # SOLIX C300
    "A1723",  # SOLIX C300X
    "A1725",  #  SOLIX C200(X)
    "A1726",  # SOLIX C300 DC
    "A1727",  #  SOLIX C200 DC
    "A1728",  # SOLIX C300X DC
    "A1729",  # SOLIX C200X DC
    "A1753",  #  SOLIX C800
    "A1754",  #  SOLIX C800 Plus
    "A1755",  #  SOLIX C800X
    "A1761",  #  SOLIX C1000(X)
    "A1762",  #  Portable Power Station 1000
    "A1763",  #  SOLIX C1000 Gen 2
    "A1765",  #  SOLIX C1000X Gen 2
    "A1770",  #  F1200 (Bluetooth)
    "A1771",  #  F1200 (Bluetooth and WLAN)
    "A1772",  #  SOLIX F1500
    "A1780",  #  767 PowerHouse (SOLIX F2000)
    "A1780P",  # 767 Power House (SOLIX F2000) with WLAN
    "A1781",  #  SOLIX F2600
    "A1782",  #  SOLIX F3000
    "A1783",  #  SOLIX C2000 Gen 2
    "A1790",  #  SOLIX F3800
    "A1790P",  # SOLIX F3800 Plus
}

# Define possible controls per Model
# Those commands are only supported once also described for a message type in the model mapping (except realtime trigger)
# Models can be removed from a feature to block command usage even if message type is described in the mapping
FEATURES = {
    SolixMqttCommands.realtime_trigger: MODELS,
    SolixMqttCommands.temp_unit_switch: MODELS,
    SolixMqttCommands.device_max_load: MODELS,
    SolixMqttCommands.device_timeout_minutes: MODELS,
    SolixMqttCommands.ac_charge_switch: MODELS,
    SolixMqttCommands.ac_charge_limit: MODELS,
    SolixMqttCommands.ac_output_switch: MODELS,
    SolixMqttCommands.ac_fast_charge_switch: MODELS,
    SolixMqttCommands.ac_output_mode_select: MODELS,
    SolixMqttCommands.ac_output_timeout_seconds: MODELS,
    SolixMqttCommands.dc_output_switch: MODELS,
    SolixMqttCommands.dc_12v_output_mode_select: MODELS,
    SolixMqttCommands.dc_output_timeout_seconds: MODELS,
    SolixMqttCommands.display_switch: MODELS,
    SolixMqttCommands.display_mode_select: MODELS,
    SolixMqttCommands.display_timeout_seconds: MODELS,
    SolixMqttCommands.light_switch: MODELS,
    SolixMqttCommands.light_mode_select: MODELS,
    SolixMqttCommands.port_memory_switch: MODELS,
    SolixMqttCommands.soc_limits: MODELS,
}


class SolixMqttDevicePps(SolixMqttDevice):
    """Define the class to handle an Anker Solix MQTT device for PPS controls."""

    def __init__(self, api_instance: AnkerSolixApi, device_sn: str) -> None:
        """Initialize."""
        self.models = MODELS
        self.features = FEATURES
        super().__init__(api_instance=api_instance, device_sn=device_sn)

    async def set_ac_output(
        self,
        enabled: bool | None = None,
        mode: int | str | None = None,
        toFile: bool = False,
    ) -> dict | None:
        """Control AC output power via MQTT.

        Args:
            enabled: True to enable AC output, False to disable
            mode: AC output mode - 1=Normal, 0=Smart
                Can also be string: "normal", "smart"
            toFile: If True, save mock response (for testing compatibility)

        Returns:
            dict: Mocked state if successful, None otherwise

        Example:
            await mydevice.set_ac_output(enabled=True)
            await mydevice.set_ac_output(mode=1)  # Normal
            await mydevice.set_ac_output(mode="smart")

        """
        # response and commands
        resp = {}
        cmd1 = SolixMqttCommands.ac_output_switch
        cmd2 = SolixMqttCommands.ac_output_mode_select
        # First validate all parameters
        if (
            enabled is not None
            and self.validate_cmd_value(cmd=cmd1, value=enabled) is None
        ):
            return None
        if mode is not None and self.validate_cmd_value(cmd=cmd2, value=mode) is None:
            return None
        # Validate and run AC switch enable command
        if enabled is not None:
            if (
                result := await self.run_command(
                    cmd=cmd1,
                    value=enabled,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        # Validate and run AC output mode command
        if mode is not None:
            if (
                result := await self.run_command(
                    cmd=cmd2,
                    value=mode,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        return resp or None

    async def set_dc_output(
        self,
        enabled: bool | None = None,
        mode: int | str | None = None,
        toFile: bool = False,
    ) -> dict | None:
        """Control DC output power via MQTT.

        Args:
            enabled: True to enable DC output, False to disable
            mode: DC output mode - 1=Normal, 0=Smart
                Can also be string: "normal", "smart"
            toFile: If True, save mock response (for testing compatibility)

        Returns:
            dict: Mocked state if successful, None otherwise

        Example:
            await mydevice.set_dc_output(enabled=True)
            await mydevice.set_dc_output(mode=0)  # Smart
            await mydevice.set_dc_output(mode="normal")

        """
        # response and commands
        resp = {}
        cmd1 = SolixMqttCommands.dc_output_switch
        cmd2 = SolixMqttCommands.dc_12v_output_mode_select
        # First validate all parameters
        if (
            enabled is not None
            and self.validate_cmd_value(cmd=cmd1, value=enabled) is None
        ):
            return None
        if mode is not None and self.validate_cmd_value(cmd=cmd2, value=mode) is None:
            return None
        # Validate and run DC switch enable command
        if enabled is not None:
            if (
                result := await self.run_command(
                    cmd=cmd1,
                    value=enabled,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        # Validate and run DC output mode command
        if mode is not None:
            if (
                result := await self.run_command(
                    cmd=cmd2,
                    value=mode,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        return resp or False

    async def set_display(
        self,
        enabled: bool | None = None,
        mode: int | str | None = None,
        timeout_seconds: int | None = None,
        toFile: bool = False,
    ) -> dict | None:
        """Control display settings via MQTT.

        Args:
            enabled: True to turn display on, False to turn off
            mode: Display mode - 0=Off, 1=Low, 2=Medium, 3=High
                Can also be string: "off", "low", "medium", "high"
            timeout_seconds: Seconds before display goes off again
            toFile: If True, save mock response (for testing compatibility)

        Returns:
            dict: Mocked state if successful, None otherwise

        Example:
            await mydevice.set_display(enabled=True)
            await mydevice.set_display(mode=2)  # Medium
            await mydevice.set_display(mode="high")
            await mydevice.set_display(timeout_seconds=20)

        """
        # response
        resp = {}
        cmd1 = SolixMqttCommands.display_switch
        cmd2 = SolixMqttCommands.display_mode_select
        cmd3 = SolixMqttCommands.display_timeout_seconds
        # First validate all parameters
        if (
            enabled is not None
            and self.validate_cmd_value(cmd=cmd1, value=enabled) is None
        ):
            return None
        if mode is not None and self.validate_cmd_value(cmd=cmd2, value=mode) is None:
            return None
        if (
            timeout_seconds is not None
            and self.validate_cmd_value(cmd=cmd3, value=timeout_seconds) is None
        ):
            return None
        # Validate and run enable command
        if enabled is not None:
            if (
                result := await self.run_command(
                    cmd=cmd1,
                    value=enabled,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        # Validate and run mode command
        if mode is not None:
            if (
                result := await self.run_command(
                    cmd=cmd2,
                    value=mode,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        # Validate and run timeout command
        if timeout_seconds is not None:
            if (
                result := await self.run_command(
                    cmd=cmd3,
                    value=timeout_seconds,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        return resp or None

    async def set_backup_charge(
        self,
        enabled: bool | None = None,
        toFile: bool = False,
    ) -> dict | None:
        """Control backup charge mode via MQTT.

        Args:
            enabled: True to enable backup charge mode, False to disable
            toFile: If True, save mock response (for testing compatibility)

        Returns:
            dict: Mocked state if successful, None otherwise

        Example:
            await mydevice.set_backup_charge(enabled=True)

        """
        # response and commands
        resp = {}
        cmd1 = SolixMqttCommands.ac_charge_switch
        # Validate and run command
        if enabled is not None:
            if (
                result := await self.run_command(
                    cmd=cmd1,
                    value=enabled,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        return resp or None

    async def set_temp_unit(
        self,
        unit: str | None = None,
        toFile: bool = False,
    ) -> dict | None:
        """Set temperature unit via MQTT.

        Args:
            unit: "fahrenheit" | "celsius"
            toFile: If True, save mock response (for testing compatibility)

        Returns:
            dict: Mocked state if successful, None otherwise

        Example:
            await mydevice.set_temp_unit(unit="celsius")  # Celsius

        """
        # response and commands
        resp = {}
        cmd1 = SolixMqttCommands.temp_unit_switch
        # Validate and run command
        if unit is not None:
            if (
                result := await self.run_command(
                    cmd=cmd1,
                    value=unit,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        return resp or None

    async def set_light(
        self,
        mode: int | str | None = None,
        toFile: bool = False,
    ) -> dict | None:
        """Set light mode via MQTT.

        Args:
            mode: Light mode - 0=Off, 1=Low, 2=Medium, 3=High, 4=Blinking
                Can also be string: "off", "low", "medium", "high", "blinking"
            toFile: If True, save mock response (for testing compatibility)

        Returns:
            dict: Mocked state if successful, None otherwise

        Example:
            await mydevice.set_light_mode(mode=3)  # High
            await mydevice.set_light_mode(mode="blinking")

        """
        # response and commands
        resp = {}
        cmd1 = SolixMqttCommands.light_mode_select
        # Validate and run command
        if mode is not None:
            if (
                result := await self.run_command(
                    cmd=cmd1,
                    value=mode,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        return resp or None

    async def set_device_timeout(
        self,
        timeout_minutes: int | None = None,
        toFile: bool = False,
    ) -> dict | None:
        """Set device auto-off timeout.

        Args:
            timeout_minutes: Timeout in minutes (30-1440)
            toFile: If True, save mock response (for testing compatibility)

        Returns:
            dict: Mocked state if successful, None otherwise

        Example:
            # Set 8 hour timeout
            result = await device.set_device_timeout(timeout_minutes=480)

        """
        # response and commands
        resp = {}
        cmd1 = SolixMqttCommands.device_timeout_minutes
        # Validate and run command
        if timeout_minutes is not None:
            if (
                result := await self.run_command(
                    cmd=cmd1,
                    value=timeout_minutes,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        return resp or None

    async def set_max_load(
        self,
        max_watts: int | None = None,
        toFile: bool = False,
    ) -> dict | None:
        """Set maximum AC output load in Watt.

        Args:
            max_watts: Maximum load in watts
            toFile: If True, save mock response (for testing compatibility)

        Returns:
            dict: Mocked state if successful, None otherwise

        Example:
            # Set 800W max load
            result = await device.set_max_load(max_watts=800)

        """
        # response and commands
        resp = {}
        cmd1 = SolixMqttCommands.device_max_load
        # Validate and run command
        if max_watts is not None:
            if (
                result := await self.run_command(
                    cmd=cmd1,
                    value=max_watts,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        return resp or None

    async def set_charge_limit(
        self,
        max_watts: int | None = None,
        toFile: bool = False,
    ) -> dict | None:
        """Set maximum AC charge limit in Watt.

        Args:
            max_watts: Maximum load in watts
            toFile: If True, save mock response (for testing compatibility)

        Returns:
            dict: Mocked state if successful, None otherwise

        Example:
            # Set 800W charge limit
            result = await device.set_max_load(max_watts=800)

        """
        # response and commands
        resp = {}
        cmd1 = SolixMqttCommands.ac_charge_limit
        # Validate and run command
        if max_watts is not None:
            if (
                result := await self.run_command(
                    cmd=cmd1,
                    value=max_watts,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        return resp or None

    async def set_fast_charging(
        self,
        enabled: bool | None = None,
        toFile: bool = False,
    ) -> dict | None:
        """Set Fast charging mode (e.g. 1300W max).

        Args:
            enabled: True to enable Fast charging, False to disable
            toFile: If True, save mock response (for testing compatibility)

        Returns:
            dict: Mocked state if successful, None otherwise

        Example:
            # Enable Fast charging
            result = await device.set_fast_charging(enabled=True)

        """
        # response and commands
        resp = {}
        cmd1 = SolixMqttCommands.ac_fast_charge_switch
        # Validate and run command
        if enabled is not None:
            if (
                result := await self.run_command(
                    cmd=cmd1,
                    value=enabled,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        return resp or None

    async def set_port_memory(
        self,
        enabled: bool,
        toFile: bool = False,
    ) -> dict | None:
        """Set port memory switch.

        Args:
            enabled: True to enable port memory, False to disable
            toFile: If True, save mock response (for testing compatibility)

        Returns:
            dict: Mocked state if successful, None otherwise

        Example:
            # Enable port memory switch
            result = await device.set_port_memory(enabled=True)

        """
        # response and commands
        resp = {}
        cmd1 = SolixMqttCommands.port_memory_switch
        # Validate and run command
        if enabled is not None:
            if (
                result := await self.run_command(
                    cmd=cmd1,
                    value=enabled,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        return resp or None
