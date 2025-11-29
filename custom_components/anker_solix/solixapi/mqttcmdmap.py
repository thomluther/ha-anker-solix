"""Define mapping for MQTT command messages and field conversions."""

from dataclasses import asdict, dataclass

from .apitypes import DeviceHexDataTypes

CMD_NAME = "cmd_name"
STATE_NAME = "state_name"
VALUE_MIN = "value_min"
VALUE_MAX = "value_max"
VALUE_STEP = "value_step"
VALUE_OPTIONS = "value_options"


@dataclass(frozen=True)
class SolixMqttCommands:
    """Dataclass for used Anker Solix MQTT command names."""

    realtime_trigger: str = "realtime_trigger"
    temp_unit_switch: str = "temp_unit_switch"
    device_max_load: str = "device_max_load"
    device_timeout_minutes: str = "device_timeout_minutes"
    ac_charge_limit: str = "ac_charge_limit"
    ac_output_switch: str = "ac_output_switch"
    ac_fast_charge_switch: str = "ac_fast_charge_switch"
    ac_output_mode_select: str = "ac_output_mode_select"
    dc_output_switch: str = "dc_output_switch"
    dc_12v_output_mode_select: str = "dc_12v_output_mode_select"
    dc_output_timeout_seconds: str = "dc_output_timeout_seconds"
    display_switch: str = "display_switch"
    display_mode_select: str = "display_mode_select"
    display_timeout_seconds: str = "display_timeout_seconds"
    light_switch: str = "light_switch"
    light_mode_select: str = "light_mode_select"
    port_memory_switch: str = "port_memory_switch"
    ac_charge_switch: str = "ac_charge_switch"
    sb_status_check: str = "sb_status_check"
    sb_power_cutoff_select: str = "sb_power_cutoff_select"
    sb_inverter_type_select: str = "sb_inverter_type_select"

    def asdict(self) -> dict:
        """Return a dictionary representation of the class fields."""
        return asdict(self)


# SOLIX MQTT COMMAND MAP descriptions:
# Each command typically uses a certain message type (2 bytes). Same command may be used by various devices
# Each command message field must be described with a name and the type. If the field does not use a type, it can be omitted
# Those command message maps should be reused in the overall mqttmap
# At a later stage, these command maps may be enhanced to compose the hex command message automatically from the description

CMD_COMMON = {
    # Common command pattern seen in most of the commands
    "topic": "req",
    "a1": {"name": "pattern_22"},
    "fe": {
        "name": "msg_timestamp",
        "type": DeviceHexDataTypes.var.value,
    },
}

CMD_REALTIME_TRIGGER = CMD_COMMON | {
    # Command: Real time data message trigger
    CMD_NAME: SolixMqttCommands.realtime_trigger,
    "a2": {
        "name": "set_realtime_trigger",  # Disable (0) | Enable (1)
        "type": DeviceHexDataTypes.ui.value,
    },
    "a3": {
        "name": "trigger_timeout_sec",  # realtime timeout in seconds when enabled
        "type": DeviceHexDataTypes.var.value,
    },
}

CMD_TEMP_UNIT = CMD_COMMON | {
    # Command: Set temperature unit
    CMD_NAME: SolixMqttCommands.temp_unit_switch,
    STATE_NAME: "temp_unit_fahrenheit",
    "a2": {
        "name": "set_temp_unit_fahrenheit",  # Celcius (0) | Fahrenheit (1)
        "type": DeviceHexDataTypes.ui.value,
    },
}

CMD_DEVICE_MAX_LOAD = CMD_COMMON | {
    # Command: Set device max home load in Watt
    CMD_NAME: SolixMqttCommands.device_max_load,
    STATE_NAME: "max_load",
    "a2": {
        "name": "set_device_max_load",  # supported value in Watt
        "type": DeviceHexDataTypes.sile.value,
    },
}

CMD_DEVICE_TIMEOUT_MIN = CMD_COMMON | {
    # Command: Set device timeout in minutes
    CMD_NAME: SolixMqttCommands.device_timeout_minutes,
    STATE_NAME: "device_timeout_minutes",
    "a2": {
        "name": "set_device_timeout_min",  # supported value in minutes
        "type": DeviceHexDataTypes.sile.value,
    },
}

CMD_AC_CHARGE_SWITCH = CMD_COMMON | {
    # Command: Enable AC backup charge
    CMD_NAME: SolixMqttCommands.ac_charge_switch,
    STATE_NAME: "backup_charge_switch",
    "a2": {
        "name": "set_ac_charge_switch",  # Disable (0) | Enable (1)
        "type": DeviceHexDataTypes.ui.value,
    },
}

CMD_AC_CHARGE_LIMIT = CMD_COMMON | {
    # Command: Set AC backup charge limit
    CMD_NAME: SolixMqttCommands.ac_charge_limit,
    STATE_NAME: "ac_charge_limit",
    "a2": {
        "name": "set_ac_charge_limit",  # supported Watt value
        "type": DeviceHexDataTypes.ui.value,
    },
}

CMD_AC_OUTPUT_SWITCH = CMD_COMMON | {
    # Command: PPS AC output switch setting
    CMD_NAME: SolixMqttCommands.ac_output_switch,
    STATE_NAME: "ac_output_power_switch",
    "a2": {
        "name": "set_ac_output_switch",  # Disable (0) | Enable (1)
        "type": DeviceHexDataTypes.ui.value,
    },
}

CMD_AC_FAST_CHARGE_SWITCH = CMD_COMMON | {
    # Command: PPS AC (ultra)fast charge switch setting
    CMD_NAME: SolixMqttCommands.ac_fast_charge_switch,
    STATE_NAME: "fast_charge_switch",
    "a2": {
        "name": "set_ac_fast_charge_switch",  # Disable (0) | Enable (1)
        "type": DeviceHexDataTypes.ui.value,
    },
}

CMD_AC_OUTPUT_MODE = CMD_COMMON | {
    # Command: PPS AC output mode setting
    CMD_NAME: SolixMqttCommands.ac_output_mode_select,
    STATE_NAME: "ac_output_mode",
    "a2": {
        "name": "set_ac_output_mode",  # Normal (1), Smart (0)
        "type": DeviceHexDataTypes.ui.value,
    },
}

CMD_DC_OUTPUT_SWITCH = CMD_COMMON | {
    # Command: PPS DC output switch setting
    CMD_NAME: SolixMqttCommands.dc_output_switch,
    STATE_NAME: "dc_output_power_switch",
    "a2": {
        "name": "set_dc_output_switch",  # Disable (0) | Enable (1)
        "type": DeviceHexDataTypes.ui.value,
    },
}

CMD_DC_12V_OUTPUT_MODE = CMD_COMMON | {
    # Command: PPS 12V DC output mode setting
    CMD_NAME: SolixMqttCommands.dc_12v_output_mode_select,
    STATE_NAME: "dc_12v_output_mode",
    "a2": {
        "name": "set_dc_12v_output_mode",  # Normal (1), Smart (0)
        "type": DeviceHexDataTypes.ui.value,
    },
}

CMD_DC_OUTPUT_TIMEOUT_SEC = CMD_COMMON | {
    # Command: PPS DC output timeout setting
    CMD_NAME: SolixMqttCommands.dc_12v_output_mode_select,
    STATE_NAME: "dc_output_timeout_seconds",
    "a2": {
        "name": "set_dc_output_timeout_seconds",  # Timeout seconds, custom range: 0-10800
        "type": DeviceHexDataTypes.var.value,
    },
}

CMD_LIGHT_SWITCH = CMD_COMMON | {
    # Command: PPS LED light switch setting
    CMD_NAME: SolixMqttCommands.light_switch,
    STATE_NAME: "light_switch",
    "a2": {
        "name": "set_light_switch",  # Off (0), On (1)
        "type": DeviceHexDataTypes.ui.value,
    },
}

CMD_LIGHT_MODE = CMD_COMMON | {
    # Command: PPS light mode setting
    CMD_NAME: SolixMqttCommands.light_mode_select,
    STATE_NAME: "light_mode",
    "a2": {
        "name": "set_light_mode",  # Off (0), Low (1), Medium (2), High (3), Blinking (4)
        "type": DeviceHexDataTypes.ui.value,
    },
}

CMD_DISPLAY_SWITCH = CMD_COMMON | {
    # Command: PPS display switch setting
    CMD_NAME: SolixMqttCommands.display_switch,
    STATE_NAME: "display_switch",
    "a2": {
        "name": "set_display_switch",  # Off (0), On (1)
        "type": DeviceHexDataTypes.ui.value,
    },
}

CMD_DISPLAY_MODE = CMD_COMMON | {
    # Command: PPS display mode setting
    CMD_NAME: SolixMqttCommands.display_mode_select,
    STATE_NAME: "display_mode",
    "a2": {
        "name": "set_display_mode",  # Off (0), Low (1), Medium (2), High (3)
        "type": DeviceHexDataTypes.ui.value,
    },
}

CMD_DISPLAY_TIMEOUT_SEC = CMD_COMMON | {
    # Command: Set display timeout in seconds
    CMD_NAME: SolixMqttCommands.display_timeout_seconds,
    STATE_NAME: "display_timeout_seconds",
    "a2": {
        "name": "set_display_timeout_sec",  # supported value in seconds
        "type": DeviceHexDataTypes.sile.value,
    },
}

CMD_PORT_MEMORY_SWITCH = CMD_COMMON | {
    # Command: PPS port memory switch setting
    CMD_NAME: SolixMqttCommands.port_memory_switch,
    STATE_NAME: "port_memory_switch",
    "a2": {
        "name": "set_port_memory_switch",  # Off (0), On (1)
        "type": DeviceHexDataTypes.ui.value,
    },
}

CMD_SB_STATUS_CHECK = (
    CMD_COMMON
    | {
        # Command: Solarbank 1 Status check request?
        CMD_NAME: SolixMqttCommands.sb_status_check,
        "a2": {
            "name": "device_sn",
            "type": DeviceHexDataTypes.str.value,
            "length": 16,
        },
        "a3": {
            "name": "charging_status",
            "type": DeviceHexDataTypes.ui.value,
        },
        "a4": {
            "name": "set_output_preset",  # in W
            "type": DeviceHexDataTypes.var.value,
        },
        "a5": {
            "name": "status_timeout_sec?",  # timeout for next status message?
            "type": DeviceHexDataTypes.var.value,
        },
        "a6": {
            "name": "local_timestamp",  # used for time synchronization?
            "type": DeviceHexDataTypes.var.value,
        },
        "a7": {
            "name": "next_status_timestamp",  # Requested time for next status message +56-57 seconds
            "type": DeviceHexDataTypes.var.value,
        },
        "a8": {
            "name": "status_check_unknown_1?",
            "type": DeviceHexDataTypes.ui.value,
        },
        "a9": {
            "name": "status_check_unknown_2?",
            "type": DeviceHexDataTypes.ui.value,
        },
        "aa": {
            "name": "status_check_unknown_3?",
            "type": DeviceHexDataTypes.ui.value,
        },
    }
)

CMD_SB_POWER_CUTOFF = CMD_COMMON | {
    # Command: Solarbank Set Power cutoff
    CMD_NAME: SolixMqttCommands.sb_power_cutoff_select,
    "a2": {
        "name": "set_output_cutoff_data",  # 10 | 5 %
        "type": DeviceHexDataTypes.ui.value,
    },
    "a3": {
        "name": "set_lowpower_input_data",  # 5 | 4 %
        "type": DeviceHexDataTypes.ui.value,
    },
    "a4": {
        "name": "set_input_cutoff_data",  # 10 | 5 %
        "type": DeviceHexDataTypes.ui.value,
    },
}

CMD_SB_INVERTER_TYPE = CMD_COMMON | {
    # Command: Solarbank 1 set Inverter Type and limits
    CMD_NAME: SolixMqttCommands.sb_inverter_type_select,
    "a2": {
        "name": "output_cutoff_data",  # 10 | 5 %
        "type": DeviceHexDataTypes.ui.value,
    },
    "a3": {
        "name": "lowpower_input_data",  # 5 | 4 %
        "type": DeviceHexDataTypes.ui.value,
    },
    "a4": {
        "name": "input_cutoff_data",  # 10 | 5 %
        "type": DeviceHexDataTypes.ui.value,
    },
    "a5": {
        "name": "set_inverter_brand",  # Hex bytes of brand name, length varies
        "type": DeviceHexDataTypes.bin.value,
    },
    "a6": {
        "name": "set_inverter_model",  # Hey bytes of model name, length varies
        "type": DeviceHexDataTypes.bin.value,
    },
    "a7": {
        "name": "set_min_load",  # in W
        "type": DeviceHexDataTypes.sile.value,
    },
    "a8": {
        "name": "set_max_load",  # in W
        "type": DeviceHexDataTypes.sile.value,
    },
    "a9": {
        "name": "set_inverter_unknown_1?",  # May be 0 typically
        "type": DeviceHexDataTypes.ui.value,
    },
    "aa": {
        "name": "ch_1_min_what?",  # 500 or other, supported values unknown
        "type": DeviceHexDataTypes.var.value,
    },
    "ab": {
        "name": "ch_1_max_what?",  # 10000 or other, supported values unknown
        "type": DeviceHexDataTypes.var.value,
    },
    "ac": {
        "name": "ch_2_min_what?",  # 500 or other, supported values unknown
        "type": DeviceHexDataTypes.var.value,
    },
    "ad": {
        "name": "ch_2_max_what?",  # 10000 or other, supported values unknown
        "type": DeviceHexDataTypes.var.value,
    },
}
