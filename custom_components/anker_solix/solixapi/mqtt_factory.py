"""Device factory for creating appropriate Anker Solix MQTT device control instances."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .apitypes import SolixDeviceType
from .mqtt_c1000x import MODELS as C1000_MODELS, SolixMqttDeviceC1000x
from .mqtt_device import SolixMqttDevice
from .mqtt_pps import MODELS as PPS_MODELS, SolixMqttDevicePps
from .mqtt_solarbank import MODELS as SB_MODELS, SolixMqttDeviceSolarbank
from .mqttmap import SOLIXMQTTMAP

if TYPE_CHECKING:
    from .api import AnkerSolixApi


class SolixMqttDeviceFactory:
    """Define the class to create the appropriate MQTT device object based on device PN."""

    def __init__(self, api_instance: AnkerSolixApi, device_sn: str) -> None:
        """Initialize.

        Args:
            api_instance: The API instance
            device_sn: The device serial number
        """
        self.api = api_instance
        self.device_sn = device_sn
        self.device_data = getattr(api_instance, "devices", {}).get(device_sn) or {}

    def create_device(self) -> SolixMqttDevice | None:
        """Create the appropriate MQTT device control instance based on device type.

        Returns:
            Appropriate MQTT device instance or None if device not found
        """
        if self.device_data and (category := self.device_data.get("type") or ""):
            pn = self.device_data.get("device_pn") or ""

            # TODO: Update factory when new device categories and criteria are implemented
            if pn in SOLIXMQTTMAP:
                if category in [SolixDeviceType.PPS.value]:
                    if pn in C1000_MODELS:
                        return SolixMqttDeviceC1000x(self.api, self.device_sn)
                    # Other PPS devices
                    if pn in PPS_MODELS:
                        return SolixMqttDevicePps(self.api, self.device_sn)

                if category in [SolixDeviceType.SOLARBANK.value] and pn in SB_MODELS:
                    return SolixMqttDeviceSolarbank(self.api, self.device_sn)

            # return default MQTT device supporting only the realtime trigger control
            return SolixMqttDevice(self.api, self.device_sn)

        return None
