"""Anker Solix various MQTT device control methods for AnkerSolixApi.

This module contains control methods specific to various Anker Solix device not covered by other classes.
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
    "A17X8",  # Smartplug
}
# Define possible controls per Model
# Those commands are only supported once also described for a message type in the model mapping (except realtime trigger)
# Models can be removed from a feature to block command usage even if message type is described in the mapping
FEATURES = {
    SolixMqttCommands.status_request: MODELS,
    SolixMqttCommands.realtime_trigger: MODELS,
    SolixMqttCommands.ac_output_switch: MODELS,
    # SolixMqttCommands.plug_schedule: MODELS, # Complex command with multiple parameters
    # SolixMqttCommands.plug_delayed_toggle: MODELS, # Complex command with multiple parameters
}


class SolixMqttDeviceVarious(SolixMqttDevice):
    """Define the class to handle an Anker Solix MQTT device for controls."""

    def __init__(self, api_instance: AnkerSolixApi, device_sn: str) -> None:
        """Initialize."""
        self.models = MODELS
        self.features = FEATURES
        super().__init__(api_instance=api_instance, device_sn=device_sn)

    async def set_ac_output(
        self,
        enabled: bool | None = None,
        toFile: bool = False,
    ) -> dict | None:
        """Control AC output power via MQTT.

        Args:
            enabled: True to enable AC output, False to disable
            toFile: If True, save mock response (for testing compatibility)

        Returns:
            dict: Mocked state if successful, None otherwise

        Example:
            await mydevice.set_ac_output(enabled=True)

        """
        # response and commands
        resp = {}
        cmd1 = SolixMqttCommands.ac_output_switch
        # First validate all parameters
        if (
            enabled is not None
            and self.validate_cmd_value(cmd=cmd1, value=enabled) is None
        ):
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
        return resp or None
