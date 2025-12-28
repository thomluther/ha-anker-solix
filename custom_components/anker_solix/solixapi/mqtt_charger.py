"""Solix power charger MQTT device control methods for AnkerSolixApi.

This module provides control features specific to the Anker Solix Solarbank device family.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .mqtt_device import SolixMqttDevice
from .mqttcmdmap import SolixMqttCommands

if TYPE_CHECKING:
    from .api import AnkerSolixApi

# Define supported Models for this class
MODELS = {
    "A1903",  #  150W Charging Base
    "A2345",  #  250W Prime Charger
    "A25X7",  #  Prime Wireless Charger
    "A2687",  #  160W Prime Charger
    "A91B2",  #  240W Charging Station
}

# Define possible controls per Model
# Those commands are only supported once also described for a message type in the model mapping (except realtime trigger)
# Models can be removed from a feature to block command usage even if message type is described in the mapping
FEATURES = {
    SolixMqttCommands.status_request: MODELS,
    SolixMqttCommands.realtime_trigger: MODELS,
}


class SolixMqttDeviceCharger(SolixMqttDevice):
    """Define the class to handle an Anker Solix MQTT device for controls."""

    def __init__(self, api_instance: AnkerSolixApi, device_sn: str) -> None:
        """Initialize."""
        self.models = MODELS
        self.features = FEATURES
        super().__init__(api_instance=api_instance, device_sn=device_sn)
