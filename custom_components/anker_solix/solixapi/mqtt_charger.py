"""Solix power charger MQTT device control methods for AnkerSolixApi.

This module provides control features specific to the Anker Solix Solarbank device family.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .apitypes import SolixEvChargerMode, SolixEvChargerStatus
from .helpers import get_enum_name
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
    "A5191",  #  V1 EV Charger
}

# Define possible controls per Model
# Those commands are only supported once also described for a message type in the model mapping (except realtime trigger)
# Models can be removed from a feature to block command usage even if message type is described in the mapping
FEATURES = {
    SolixMqttCommands.status_request: MODELS,
    SolixMqttCommands.realtime_trigger: MODELS,
    SolixMqttCommands.usbc_1_port_switch: MODELS,
    SolixMqttCommands.usbc_2_port_switch: MODELS,
    SolixMqttCommands.usbc_3_port_switch: MODELS,
    SolixMqttCommands.usbc_4_port_switch: MODELS,
    SolixMqttCommands.usba_port_switch: MODELS,
    SolixMqttCommands.plug_lock_switch: MODELS,
    SolixMqttCommands.ev_auto_start_switch: MODELS,
    SolixMqttCommands.ev_auto_charge_restart_switch: MODELS,
    SolixMqttCommands.ev_random_delay_switch: MODELS,
    SolixMqttCommands.ev_max_charge_current: MODELS,
    SolixMqttCommands.ev_load_balancing: MODELS,
    SolixMqttCommands.ev_solar_charging: MODELS,
    SolixMqttCommands.main_breaker_limit: MODELS,
    SolixMqttCommands.ev_charger_schedule_settings: MODELS,
    SolixMqttCommands.ev_charger_schedule_times: MODELS,
    SolixMqttCommands.ev_charger_mode_select: MODELS,
    SolixMqttCommands.device_power_mode: MODELS,
    SolixMqttCommands.light_brightness: MODELS,
    SolixMqttCommands.light_off_schedule: MODELS,
    SolixMqttCommands.smart_touch_mode_select: MODELS,
    SolixMqttCommands.swipe_up_mode_select: MODELS,
    SolixMqttCommands.swipe_down_mode_select: MODELS,
    SolixMqttCommands.modbus_switch: MODELS,
}


class SolixMqttDeviceCharger(SolixMqttDevice):
    """Define the class to handle an Anker Solix MQTT device for controls."""

    def __init__(self, api_instance: AnkerSolixApi, device_sn: str) -> None:
        """Initialize."""
        self.models = MODELS
        self.features = FEATURES
        super().__init__(api_instance=api_instance, device_sn=device_sn)

    def ev_charger_mode_state(self) -> str | None:
        """Get the EV charger operational mode based on its status."""
        if (status := self.mqttdata.get("ev_charger_status")) is not None:
            # First check if last command was boost
            if bool(self.mqttdata.get("boost_status")):
                return SolixEvChargerMode.boost_charge.name
            # Get last command from status
            # Standby(0), Preparing(1), Charging(2), Charger_Paused(3), Vehicle_Paused(4), Completed (5), Reserving(6), Disabled(7), Error(8)
            state = get_enum_name(
                SolixEvChargerStatus, str(status), SolixEvChargerStatus.unknown.name
            )
            if state in [
                SolixEvChargerStatus.preparing.name,
                SolixEvChargerStatus.charging.name,
                SolixEvChargerStatus.charger_paused.name,
                SolixEvChargerStatus.vehicle_paused.name,
            ]:
                return SolixEvChargerMode.start_charge.name
            return SolixEvChargerMode.stop_charge.name
        return None

    def ev_charger_mode_options(self) -> list:
        """Get the EV charger operational mode options based on its state."""
        options = set()
        status = get_enum_name(
            SolixEvChargerStatus,
            str(self.mqttdata.get("ev_charger_status")),
            SolixEvChargerStatus.unknown.name,
        )
        if state := self.ev_charger_mode_state():
            options.add(state)
            if state == SolixEvChargerMode.start_charge.name:
                options.add(SolixEvChargerMode.stop_charge.name)
                # Allow skip option if random delay enabled or wait time > 0
                if status == SolixEvChargerStatus.preparing.name and (
                    self.mqttdata.get("plug_countdown_seconds", 0) > 0
                    or self.mqttdata.get("random_delay_switch")
                ):
                    options.add(SolixEvChargerMode.skip_delay.name)
                else:
                    options.add(SolixEvChargerMode.boost_charge.name)
            elif state == SolixEvChargerMode.boost_charge.name:
                options.add(SolixEvChargerMode.stop_charge.name)
            elif status == SolixEvChargerStatus.standby.name:
                options.add(SolixEvChargerMode.start_charge.name)
        return list(options)
