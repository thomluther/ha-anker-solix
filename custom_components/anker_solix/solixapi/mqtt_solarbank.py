"""Solarbank MQTT device control methods for AnkerSolixApi.

This module contains control methods specific to the Anker Solix Solarbank device family.
These methods provide comprehensive device control via MQTT commands.
Solarbanks can also be controlled via Api, these methods cover settings only controllable via MQTT.
"""

from __future__ import annotations  # noqa: TID251

from typing import TYPE_CHECKING

from .apitypes import SolixCircuitPriority
from .helpers import get_enum_name, get_enum_value
from .mqtt_device import SolixMqttDevice
from .mqttcmdmap import SolixMqttCommands

if TYPE_CHECKING:
    from .api import AnkerSolixApi

# Define supported Models for this class
MODELS = {
    "A17C0",  # Solarbank 1 E1600
    "A17C1",  # Solarbank 2 E1600 Pro
    "A17C2",  # Solarbank 2 E1600 AC
    "A17C3",  # Solarbank 2 E1600 Plus
    "A17C5",  # Solarbank 3 E2700 Pro
    "AE100",  # Power Dock Solarbank
    "AX170",  # Power Dock Home Backup System
}
# Define possible controls per Model
# Those commands are only supported once also described for a message type in the model mapping (except realtime trigger)
# Models can be removed from a feature to block command usage even if message type is described in the mapping
FEATURES = {
    SolixMqttCommands.status_request: MODELS,
    SolixMqttCommands.realtime_trigger: MODELS,
    SolixMqttCommands.temp_unit_switch: MODELS,
    # Min SOC different since SB3
    SolixMqttCommands.sb_power_cutoff_select: {"A17C0", "A17C1", "A17C2", "A17C3"},
    SolixMqttCommands.sb_min_soc_select: {"A17C5", "AE100"},
    SolixMqttCommands.sb_soc_limits: MODELS,
    # Commands since SB2
    SolixMqttCommands.sb_ac_socket_switch: MODELS,
    SolixMqttCommands.sb_light_switch: MODELS,
    SolixMqttCommands.sb_light_mode_select: MODELS,
    SolixMqttCommands.sb_max_load: MODELS,
    SolixMqttCommands.sb_max_load_parallel: MODELS,
    # commands since SB2 AC / SB3
    SolixMqttCommands.sb_disable_grid_export_switch: MODELS,
    SolixMqttCommands.sb_device_timeout: MODELS,
    SolixMqttCommands.sb_ac_input_limit: MODELS,
    SolixMqttCommands.sb_pv_limit_select: MODELS,
    # SolixMqttCommands.sb_3rd_party_pv_switch: MODELS, # TODO: requires also Api support
    # SolixMqttCommands.sb_ev_charger_switch: {"AE100"}, # TODO: requires also Api support
    SolixMqttCommands.circuit_priority: MODELS,
}


class SolixMqttDeviceSolarbank(SolixMqttDevice):
    """Define the class to handle an Anker Solix MQTT device for controls."""

    def __init__(self, api_instance: AnkerSolixApi, device_sn: str) -> None:
        """Initialize."""
        self.models = MODELS
        self.features = FEATURES
        super().__init__(api_instance=api_instance, device_sn=device_sn)

    def update_device(
        self, device: dict, dynamic_descriptions: dict | None = None
    ) -> None:
        """Define callback for Api device updates."""
        super().update_device(device=device, dynamic_descriptions=dynamic_descriptions)
        if not dynamic_descriptions:
            return
        if dynamic_descriptions.get("circuit_setup") and (value := self._filedata.get("circuit_setup")):
            # update the grouping of mocked circuit setup
            circuit_groups = {}
            for index, circuit in value.items():
                group = f"{circuit.get("priority",0)!s}:{circuit.get("id",0)!s}"
                circuit_groups[group] = [*circuit_groups.get(group, []), index]
            self._filedata["circuit_groups"] = circuit_groups


    async def set_temp_unit(
        self,
        unit: str,
        toFile: bool = False,
    ) -> dict | None:
        """Set temperature unit via MQTT.

        Args:
            unit: "fahrenheit" | "celsius"
            toFile: If True, save mock response (for testing compatibility)

        Returns:
            dict: Mocked state if successful, False otherwise

        Example:
            await mydevice.set_temp_unit(unit="celsius")  # Celsius

        """
        # Validate command value and publish command
        return await self.run_command(
            cmd=SolixMqttCommands.temp_unit_switch,
            value=unit,
            toFile=toFile,
        )

    async def set_min_soc(
        self,
        limit: int | str,
        toFile: bool = False,
    ) -> bool | dict:
        """Set Solarbank SOC reserve via MQTT.

        NOTE: This may be insufficient for SOC reserve setting since that is controlled via Cloud Api

        Args:
            limit: SOC reserve in %
            toFile: If True, save mock response (for testing compatibility)

        Returns:
            dict: Mock response if successful, False otherwise

        Example:
            await mydevice.set_min_soc(limit=10)  # 10 %

        """
        # Validate parameters and publish command
        # Use correct command depending on which is supported by device
        # Valid option 5 or 10 in % (VALIDATED SB1 ⚠️ Changed on device, but not in App! App needs additional change via Api)
        return await self.run_command(
            cmd=SolixMqttCommands.sb_power_cutoff_select
            if SolixMqttCommands.sb_power_cutoff_select in self.controls
            else SolixMqttCommands.sb_min_soc_select,
            value=limit,
            toFile=toFile,
        )

    def update_circuit_priority(
        self,
        circuit: str | int,
        priority: str | int,
    ) -> dict | None:
        """Update the power dock circuit priority in the circuit setup structure.

        Args:
            circuit: Number of the physical circuit 1-12, e.g. "1"
            priority: Name or value of the priority, 1="must_have", 2="nice_to_have"

        Returns:
            dict: New circuit setup if successful, None otherwise

        Example:
            mydevice.update_circuit_priority(circuit=10, priority="nice_to_have")

        """
        # find circuit setup in Api cache
        status = self.get_status(fromFile=True)
        setup = status.get("circuit_setup", {})
        groups = status.get("circuit_groups", {})
        circuit = (
            f"{int(circuit):02d}"
            if (
                isinstance(circuit, int | float)
                or (isinstance(circuit, str) and circuit.isdigit())
            )
            else None
        )
        priority = (
            get_enum_value(SolixCircuitPriority,get_enum_name(SolixCircuitPriority,str(int(priority))))
            if (isinstance(circuit, int | float) or str(priority).isdigit())
            else get_enum_value(SolixCircuitPriority,priority)
            if isinstance(priority, str)
            else None
        )
        # check values and Build parameter map
        if circuit in setup and groups and priority is not None:
            # first get peers for circuit to be modified
            peers = next(iter(p for p in groups.values() if circuit in p),[])
            # cycle through setup and rebuild logical group id based on changed priority
            prio_index = {}
            for slot in [f"{i:02d}" for i in range(len(setup),0,-1)]:
                if c := setup.get(slot):
                    if slot in peers:
                        # update prio for any peer
                        prio = int(priority)
                        c["priority"] = prio
                    else:
                        prio = c.get("priority",0)
                    # increase index for prio and assign new id to any slot
                    if c.get("pair_status",0) < 2:
                        # increase prio index only if no peer slot
                        prio_index[prio] = prio_index.get(prio,0) + 1
                    # NOTE: This id assignment assumes peered slots are always adjacent slots
                    c["id"] = prio_index[prio]
            return setup
        return None
