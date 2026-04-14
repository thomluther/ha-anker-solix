"""Anker Solix MQTT generator device control methods for AnkerSolixApi.

This module contains control methods specific to Anker Solix generator devices.
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
    "A7320",  # Smart Generator 5500
}
# Define possible controls per Model
# Those commands are only supported once also described for a message type in the model mapping (except realtime trigger)
# Models can be removed from a feature to block command usage even if message type is described in the mapping
FEATURES = {
    SolixMqttCommands.status_request: MODELS,
    SolixMqttCommands.realtime_trigger: MODELS,
    SolixMqttCommands.ac_dc_mode_select: MODELS,
}


class SolixMqttDeviceGenerator(SolixMqttDevice):
    """Define the class to handle an Anker Solix MQTT device for controls."""

    def __init__(self, api_instance: AnkerSolixApi, device_sn: str) -> None:
        """Initialize."""
        self.models = MODELS
        self.features = FEATURES
        super().__init__(api_instance=api_instance, device_sn=device_sn)

