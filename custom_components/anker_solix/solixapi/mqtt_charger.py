"""Solix power charger MQTT device control methods for AnkerSolixApi.

This module provides control features specific to the Anker Solix Solarbank device family.
"""

from __future__ import annotations

from datetime import time
from typing import TYPE_CHECKING

from .apitypes import SolixEvChargerMode, SolixEvChargerStatus, SolixScheduleWeekendMode
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
    SolixMqttCommands.ac_1_port_switch: MODELS,
    SolixMqttCommands.ac_2_port_switch: MODELS,
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
            # Consider wait times for plug or start
            state = get_enum_name(
                SolixEvChargerStatus, str(status), SolixEvChargerStatus.unknown.name
            )
            if state == SolixEvChargerStatus.preparing.name:
                if self.mqttdata.get("plug_countdown_seconds", 0) > 0:
                    return SolixEvChargerMode.wait_plug.name
                if self.mqttdata.get("start_countdown_seconds", 0) > 0:
                    return SolixEvChargerMode.wait_start.name
                return SolixEvChargerMode.start_charge.name
            if state in [
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
            if state in [
                SolixEvChargerMode.wait_plug.name,
                SolixEvChargerMode.wait_start.name,
                SolixEvChargerMode.start_charge.name,
            ]:
                options.add(SolixEvChargerMode.stop_charge.name)
                # Allow skip option if waiting for start delay
                if state == SolixEvChargerMode.wait_start.name:
                    options.add(SolixEvChargerMode.skip_delay.name)
                elif state == SolixEvChargerMode.start_charge.name:
                    options.add(SolixEvChargerMode.boost_charge.name)
            elif state == SolixEvChargerMode.boost_charge.name:
                options.add(SolixEvChargerMode.stop_charge.name)
            # Add start option only if status indicates start capability
            elif status == SolixEvChargerStatus.standby.name:
                options.add(SolixEvChargerMode.start_charge.name)
        return list(options)

    async def set_ev_charger_schedule(
        self,
        week_start_time: str | time | None = None,
        week_end_time: str | time | None = None,
        weekend_start_time: str | time | None = None,
        weekend_end_time: str | time | None = None,
        weekend_mode: str | None = None,
        toFile: bool = False,
    ) -> dict | None:
        """Set the EV charger schedule times and weekend mode.

        Args:
            week_start_time: Weekday charge start time in "HH:MM" format
            week_end_time: Weekday charge end time in "HH:MM" format
            weekend_start_time: Weekend charge start time in "HH:MM" format
            weekend_end_time: Weekend charge end time in "HH:MM" format
            weekend_mode: Weekend mode - "same" or "different"
            toFile: If True, save mock response (for testing compatibility)

        Returns:
            dict: Mocked state if successful, None otherwise

        Example:
            await mydevice.set_ev_charger_schedule(
                week_start_time="22:00",
                week_end_time="06:00",
                weekend_mode="same"
            )

        """
        # response and commands
        resp = {}
        cmd1 = SolixMqttCommands.ev_charger_schedule_times
        # First convert parameters, ignore seconds if time objects are provided
        if isinstance(week_start_time, time):
            week_start_time = week_start_time.isoformat(timespec="minutes")
        if isinstance(week_end_time, time):
            week_end_time = week_end_time.isoformat(timespec="minutes")
        if isinstance(weekend_start_time, time):
            weekend_start_time = weekend_start_time.isoformat(timespec="minutes")
        if isinstance(weekend_end_time, time):
            weekend_end_time = weekend_end_time.isoformat(timespec="minutes")
        # Get current state
        current_week_start = self.mqttdata.get("week_start_time")
        current_week_end = self.mqttdata.get("week_end_time")
        current_weekend_mode = get_enum_name(
            SolixScheduleWeekendMode, str(self.mqttdata.get("weekend_mode"))
        )

        # make weekend times same as week times if same mode is provided
        if weekend_mode == SolixScheduleWeekendMode.same.name:
            weekend_start_time = week_start_time or current_week_start
            weekend_end_time = week_end_time or current_week_end
        # make mode different if any weekend time provided
        elif weekend_start_time is not None or weekend_end_time is not None:
            weekend_mode = SolixScheduleWeekendMode.different.name
        # make weekend times same as week times if mode is same and any week time provided
        elif week_start_time is not None or week_end_time is not None:
            if weekend_mode == SolixScheduleWeekendMode.same.name or (
                not weekend_mode
                and current_weekend_mode == SolixScheduleWeekendMode.same.name
            ):
                weekend_start_time = week_start_time or current_week_start
                weekend_end_time = week_end_time or current_week_end

        # Build parameter map for times
        parm_map = {}
        if week_start_time is not None:
            parm_map["set_week_start_time"] = str(week_start_time)
        if week_end_time is not None:
            parm_map["set_week_end_time"] = str(week_end_time)
        if weekend_start_time is not None:
            parm_map["set_weekend_start_time"] = str(weekend_start_time)
        if weekend_end_time is not None:
            parm_map["set_weekend_end_time"] = str(weekend_end_time)
        if weekend_mode is not None:
            parm_map["set_weekend_mode"] = str(weekend_mode)

        # Send command if any parameters to update
        if parm_map:
            if (
                result := await self.run_command(
                    cmd=cmd1,
                    parm_map=parm_map,
                    toFile=toFile,
                )
            ) is None:
                return None
            resp.update(result)
        return resp or None
