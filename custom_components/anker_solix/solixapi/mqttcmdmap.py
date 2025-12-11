"""Define mapping for MQTT command messages and field conversions."""

from dataclasses import asdict, dataclass

from .apitypes import DeviceHexDataTypes

# common command descriptions to be used
COMMAND_NAME = "command_name"  # name of the command, must be defined in dataclass SolixMqttCommands
COMMAND_LIST = "command_list"  # specifies the nested commands to describe multiple commands per message type
STATE_NAME = "state_name"  # extracted value name that represents the current state of the control
VALUE_MIN = "value_min"  # min value of a range
VALUE_MAX = "value_max"  # max value of a range
VALUE_STEP = "value_step"  # step to be used within range, default is 1
VALUE_OPTIONS = (
    "value_options"  # Use list for value options, or dict for name:value mappings
)
VALUE_DEFAULT = "value_default"  # Defines a default value for the field
VALUE_FOLLOWS = "value_follows"  # defines setting name the value depends on, the options need to define a map for the dependencies
VALUE_STATE = "value_state"  # Defines a state name that should be used if found
VALUE_DIVIDER = "value_divider"  # Defines a divider for the applied value, should be same as factor extracting the state value


@dataclass(frozen=True)
class SolixMqttCommands:
    """Dataclass for used Anker Solix MQTT command names."""

    status_request: str = "status_request"
    realtime_trigger: str = "realtime_trigger"
    temp_unit_switch: str = "temp_unit_switch"
    device_max_load: str = "device_max_load"
    device_timeout_minutes: str = "device_timeout_minutes"
    ac_charge_switch: str = "ac_charge_switch"
    ac_fast_charge_switch: str = "ac_fast_charge_switch"
    ac_charge_limit: str = "ac_charge_limit"
    ac_output_switch: str = "ac_output_switch"
    ac_output_mode_select: str = "ac_output_mode_select"
    ac_output_timeout_seconds: str = "ac_output_timeout_seconds"
    dc_output_switch: str = "dc_output_switch"
    dc_12v_output_mode_select: str = "dc_12v_output_mode_select"
    dc_output_timeout_seconds: str = "dc_output_timeout_seconds"
    display_switch: str = "display_switch"
    display_mode_select: str = "display_mode_select"
    display_timeout_seconds: str = "display_timeout_seconds"
    light_switch: str = "light_switch"
    light_mode_select: str = "light_mode_select"
    port_memory_switch: str = "port_memory_switch"
    soc_limits: str = "soc_limits"
    sb_status_check: str = "sb_status_check"
    sb_power_cutoff_select: str = "sb_power_cutoff_select"
    sb_min_soc_select: str = "sb_min_soc_select"
    sb_inverter_type_select: str = "sb_inverter_type_select"
    sb_max_load: str = "sb_max_load"
    sb_ac_input_limit: str = "sb_ac_input_limit"
    sb_ac_socket_switch: str = "sb_ac_socket_switch"
    sb_pv_limit_select: str = "sb_pv_limit_select"
    sb_light_switch: str = "sb_light_switch"
    sb_light_mode_select: str = "sb_light_mode_select"
    sb_disable_grid_export_switch: str = "sb_disable_grid_export_switch"
    sb_device_timeout: str = "sb_device_timeout"

    def asdict(self) -> dict:
        """Return a dictionary representation of the class fields."""
        return asdict(self)


# SOLIX MQTT COMMAND MAP descriptions:
# Each command typically uses a certain message type (2 bytes). Same command may be used by various devices
# Each command message field must be described with a name and the type. If the field does not use a type, it can be omitted
# Those command message maps should be reused in the overall mqttmap
# At a later stage, these command maps may be enhanced to compose the hex command message automatically from the description

TIMESTAMP_FD = {
    # newer format using str type for timestamp value in ms
    # value will be composed automatically based on name and field
    "fd": {
        "name": "msg_timestamp",
        "type": DeviceHexDataTypes.str.value,
    },
}

TIMESTAMP_FE = {
    # classical format using 4 bytes for timestamp value in sec
    # value will be composed automatically based on name and field
    "fe": {
        "name": "msg_timestamp",
        "type": DeviceHexDataTypes.var.value,
    },
}

CMD_COMMON = {
    # Common command pattern seen in most of the commands
    # TODO: Compare across all described commands if used only for cmd message types 00xx
    "topic": "req",
    "a1": {
        "name": "pattern_22"
    },  # Bytes composed automatically based on name and field
} | TIMESTAMP_FE

CMD_COMMON_V2 = {
    # Common command pattern V2 seen in most of the commands for newer devices with timestamp in ms
    # TODO: Compare across all described commands if used only for cmd message types 01xx
    "topic": "req",
    "a1": {
        "name": "pattern_22"
    },  # Bytes composed automatically based on name and field
} | TIMESTAMP_FD

CMD_STATUS_REQUEST = CMD_COMMON | {
    # Command: Device status request
    COMMAND_NAME: SolixMqttCommands.status_request,
}

CMD_REALTIME_TRIGGER = CMD_COMMON | {
    # Command: Real time data message trigger
    COMMAND_NAME: SolixMqttCommands.realtime_trigger,
    "a2": {
        "name": "set_realtime_trigger",  # Disable (0) | Enable (1)
        "type": DeviceHexDataTypes.ui.value,
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
    "a3": {
        "name": "trigger_timeout_sec",  # realtime timeout in seconds when enabled
        "type": DeviceHexDataTypes.var.value,
        VALUE_MIN: 60,  # real limit is unknown
        VALUE_MAX: 600,  # real limit is unknown
    },
}

CMD_TEMP_UNIT = CMD_COMMON | {
    # Command: Set temperature unit
    COMMAND_NAME: SolixMqttCommands.temp_unit_switch,
    "a2": {
        "name": "set_temp_unit_fahrenheit",  # Celcius (0) | Fahrenheit (1)
        "type": DeviceHexDataTypes.ui.value,
        STATE_NAME: "temp_unit_fahrenheit",
        VALUE_OPTIONS: {"celcius": 0, "fahrenheit": 1},
    },
}

CMD_DEVICE_MAX_LOAD = CMD_COMMON | {
    # Command: Set device max home load in Watt
    COMMAND_NAME: SolixMqttCommands.device_max_load,
    "a2": {
        "name": "set_device_max_load",  # supported value in Watt
        "type": DeviceHexDataTypes.sile.value,
        STATE_NAME: "max_load",
    },
}

CMD_DEVICE_TIMEOUT_MIN = CMD_COMMON | {
    # Command: Set device timeout in minutes
    COMMAND_NAME: SolixMqttCommands.device_timeout_minutes,
    "a2": {
        "name": "set_device_timeout_min",  # 0 (Never), 30, 60, 120, 240, 360, 720, 1440
        "type": DeviceHexDataTypes.sile.value,
        STATE_NAME: "device_timeout_minutes",
        VALUE_OPTIONS: [0, 30, 60, 120, 240, 360, 720, 1440],
    },
}

CMD_AC_CHARGE_SWITCH = CMD_COMMON | {
    # Command: Enable AC backup charge
    COMMAND_NAME: SolixMqttCommands.ac_charge_switch,
    "a2": {
        "name": "set_ac_charge_switch",  # Disable (0) | Enable (1)
        "type": DeviceHexDataTypes.ui.value,
        STATE_NAME: "backup_charge_switch",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
}

CMD_AC_CHARGE_LIMIT = CMD_COMMON | {
    # Command: Set AC backup charge limit
    COMMAND_NAME: SolixMqttCommands.ac_charge_limit,
    "a2": {
        "name": "set_ac_input_limit",  # supported Watt value
        "type": DeviceHexDataTypes.sile.value,
        STATE_NAME: "ac_input_limit",
    },
}

CMD_AC_OUTPUT_SWITCH = CMD_COMMON | {
    # Command: PPS AC output switch setting
    COMMAND_NAME: SolixMqttCommands.ac_output_switch,
    "a2": {
        "name": "set_ac_output_switch",  # Disable (0) | Enable (1)
        "type": DeviceHexDataTypes.ui.value,
        STATE_NAME: "ac_output_power_switch",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
}

CMD_AC_FAST_CHARGE_SWITCH = CMD_COMMON | {
    # Command: PPS AC (ultra)fast charge switch setting
    COMMAND_NAME: SolixMqttCommands.ac_fast_charge_switch,
    "a2": {
        "name": "set_ac_fast_charge_switch",  # Disable (0) | Enable (1)
        "type": DeviceHexDataTypes.ui.value,
        STATE_NAME: "fast_charge_switch",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
}

CMD_AC_OUTPUT_MODE = CMD_COMMON | {
    # Command: PPS AC output mode setting
    COMMAND_NAME: SolixMqttCommands.ac_output_mode_select,
    "a2": {
        "name": "set_ac_output_mode",  # Normal (1), Smart (0)
        "type": DeviceHexDataTypes.ui.value,
        STATE_NAME: "ac_output_mode",
        VALUE_OPTIONS: {"smart": 0, "normal": 1},
    },
}

CMD_AC_OUTPUT_TIMEOUT_SEC = (
    CMD_COMMON
    | {
        # Command: PPS DC output timeout setting
        COMMAND_NAME: SolixMqttCommands.ac_output_timeout_seconds,
        "a2": {
            "name": "set_ac_output_timeout_seconds",  # Timeout seconds, custom range: 0-86400, step 300
            "type": DeviceHexDataTypes.var.value,
            STATE_NAME: "ac_output_timeout_seconds",
            VALUE_MIN: 0,
            VALUE_MAX: 86400,
            VALUE_STEP: 300,
        },
    }
)

CMD_DC_OUTPUT_SWITCH = CMD_COMMON | {
    # Command: PPS DC output switch setting
    COMMAND_NAME: SolixMqttCommands.dc_output_switch,
    "a2": {
        "name": "set_dc_output_switch",  # Disable (0) | Enable (1)
        "type": DeviceHexDataTypes.ui.value,
        STATE_NAME: "dc_output_power_switch",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
}

CMD_DC_12V_OUTPUT_MODE = CMD_COMMON | {
    # Command: PPS 12V DC output mode setting
    COMMAND_NAME: SolixMqttCommands.dc_12v_output_mode_select,
    "a2": {
        "name": "set_dc_12v_output_mode",  # Normal (1), Smart (0)
        "type": DeviceHexDataTypes.ui.value,
        STATE_NAME: "dc_12v_output_mode",
        VALUE_OPTIONS: {"smart": 0, "normal": 1},
    },
}

CMD_DC_OUTPUT_TIMEOUT_SEC = (
    CMD_COMMON
    | {
        # Command: PPS DC output timeout setting
        COMMAND_NAME: SolixMqttCommands.dc_output_timeout_seconds,
        "a2": {
            "name": "set_dc_output_timeout_seconds",  # Timeout seconds, custom range: 0-86400, step 300
            "type": DeviceHexDataTypes.var.value,
            STATE_NAME: "dc_output_timeout_seconds",
            VALUE_MIN: 0,
            VALUE_MAX: 86400,
            VALUE_STEP: 300,
        },
    }
)

CMD_LIGHT_SWITCH = CMD_COMMON | {
    # Command: PPS LED light switch setting
    COMMAND_NAME: SolixMqttCommands.light_switch,
    "a2": {
        "name": "set_light_switch",  # Off (0), On (1)
        "type": DeviceHexDataTypes.ui.value,
        STATE_NAME: "light_switch",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
}

CMD_LIGHT_MODE = CMD_COMMON | {
    # Command: PPS light mode setting
    COMMAND_NAME: SolixMqttCommands.light_mode_select,
    "a2": {
        "name": "set_light_mode",  # Off (0), Low (1), Medium (2), High (3), Blinking (4)
        "type": DeviceHexDataTypes.ui.value,
        STATE_NAME: "light_mode",
        VALUE_OPTIONS: {"off": 0, "low": 1, "medium": 2, "high": 3, "blinking": 4},
    },
}

CMD_DISPLAY_SWITCH = CMD_COMMON | {
    # Command: PPS display switch setting
    COMMAND_NAME: SolixMqttCommands.display_switch,
    "a2": {
        "name": "set_display_switch",  # Off (0), On (1)
        "type": DeviceHexDataTypes.ui.value,
        STATE_NAME: "display_switch",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
}

CMD_DISPLAY_MODE = CMD_COMMON | {
    # Command: PPS display mode setting
    COMMAND_NAME: SolixMqttCommands.display_mode_select,
    "a2": {
        "name": "set_display_mode",  # Off (0), Low (1), Medium (2), High (3)
        "type": DeviceHexDataTypes.ui.value,
        STATE_NAME: "display_mode",
        VALUE_OPTIONS: {"off": 0, "low": 1, "medium": 2, "high": 3},
    },
}

CMD_DISPLAY_TIMEOUT_SEC = CMD_COMMON | {
    # Command: Set display timeout in seconds
    COMMAND_NAME: SolixMqttCommands.display_timeout_seconds,
    "a2": {
        "name": "set_display_timeout_sec",  # supported value in seconds
        "type": DeviceHexDataTypes.sile.value,
        STATE_NAME: "display_timeout_seconds",
        VALUE_OPTIONS: [20, 30, 60, 300, 1800],
    },
}

CMD_PORT_MEMORY_SWITCH = CMD_COMMON | {
    # Command: PPS port memory switch setting
    COMMAND_NAME: SolixMqttCommands.port_memory_switch,
    "a2": {
        "name": "set_port_memory_switch",  # Off (0), On (1)
        "type": DeviceHexDataTypes.ui.value,
        STATE_NAME: "port_memory_switch",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
}

CMD_SOC_LIMITS_V2 = CMD_COMMON_V2 | {
    # Command: PPS soc limit settings
    COMMAND_NAME: SolixMqttCommands.soc_limits,
    "aa": {
        "name": "set_max_soc",  # max_soc: 80, 85, 90, 95, 100 %
        "type": DeviceHexDataTypes.ui.value,
        STATE_NAME: "max_soc",
        VALUE_OPTIONS: [80, 85, 90, 95, 100],
    },
    "ab": {
        "name": "set_min_soc",  # min_soc: 1, 5, 10, 15, 20 %
        "type": DeviceHexDataTypes.ui.value,
        STATE_NAME: "min_soc",
        VALUE_OPTIONS: [1, 5, 10, 15, 20],
    },
}

CMD_SB_STATUS_CHECK = (
    CMD_COMMON
    | {
        # Command: Solarbank 1 Status check request?
        # NOTE: This command schema is incomplete and not supported yet
        COMMAND_NAME: SolixMqttCommands.sb_status_check,
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
    COMMAND_NAME: SolixMqttCommands.sb_power_cutoff_select,
    "a2": {
        "name": "set_output_cutoff_data",  # 10 | 5 %
        "type": DeviceHexDataTypes.ui.value,
        STATE_NAME: "output_cutoff_data",
        VALUE_OPTIONS: [5, 10],
    },
    "a3": {
        "name": "set_lowpower_input_data",  # 5 | 4 %
        "type": DeviceHexDataTypes.ui.value,
        STATE_NAME: "lowpower_input_data",
        VALUE_FOLLOWS: "set_output_cutoff_data",
        VALUE_OPTIONS: {5: 4, 10: 5},
    },
    "a4": {
        "name": "set_input_cutoff_data",  # 10 | 5 %
        "type": DeviceHexDataTypes.ui.value,
        STATE_NAME: "input_cutoff_data",
        VALUE_FOLLOWS: "set_output_cutoff_data",
        VALUE_OPTIONS: {5: 5, 10: 10},
    },
}

CMD_SB_MIN_SOC = CMD_COMMON | {
    # Command: Solarbank Set max AC input limit (AC charge)
    COMMAND_NAME: SolixMqttCommands.sb_min_soc_select,
    "a2": {
        "name": "set_min_soc",  # 5 or 10 %
        "type": DeviceHexDataTypes.ui.value,
        STATE_NAME: "min_soc",
        VALUE_OPTIONS: [5, 10],
    },
}

CMD_SB_INVERTER_TYPE = CMD_SB_POWER_CUTOFF | {
    # Command: Solarbank 1 set Inverter Type and limits
    COMMAND_NAME: SolixMqttCommands.sb_inverter_type_select,
    # NOTE: This command schema is incomplete and not supported yet
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
        "name": "set_ch_1_min_what?",  # 500 or other, supported values unknown
        "type": DeviceHexDataTypes.var.value,
    },
    "ab": {
        "name": "set_ch_1_max_what?",  # 10000 or other, supported values unknown
        "type": DeviceHexDataTypes.var.value,
    },
    "ac": {
        "name": "set_ch_2_min_what?",  # 500 or other, supported values unknown
        "type": DeviceHexDataTypes.var.value,
    },
    "ad": {
        "name": "set_ch_2_max_what?",  # 10000 or other, supported values unknown
        "type": DeviceHexDataTypes.var.value,
    },
}

CMD_SB_AC_SOCKET_SWITCH = CMD_COMMON | {
    # Command: Solarbank switch to toggle AC socket
    COMMAND_NAME: SolixMqttCommands.sb_ac_socket_switch,
    "a2": {
        "name": "set_ac_socket_switch",  # Off (0), On (1)
        "type": DeviceHexDataTypes.ui.value,
        STATE_NAME: "ac_socket_switch",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
}

CMD_SB_MAX_LOAD = (
    CMD_COMMON
    | {
        # Command: Solarbank Set max load
        COMMAND_NAME: SolixMqttCommands.sb_max_load,
        "a2": {
            "name": "set_max_load",  # AC output limit in W, various options, different per model
            "type": DeviceHexDataTypes.sile.value,
            STATE_NAME: "max_load",
        },
        "a3": {
            "name": "set_max_load_a3?",  # Unknown, 0 observed
            "type": DeviceHexDataTypes.sile.value,
            VALUE_DEFAULT: 0,
        },
        "a4": {
            "name": "set_max_load_a4?",  # Unknown, 0 observed
            "type": DeviceHexDataTypes.sile.value,
            VALUE_DEFAULT: 0,
        },
    }
)

CMD_SB_DISABLE_GRID_EXPORT_SWITCH = CMD_COMMON | {
    # Command: Solarbank disable grid export on PV surplus
    COMMAND_NAME: SolixMqttCommands.sb_disable_grid_export_switch,
    "a5": {
        "name": "set_disable_grid_export_a5?",  # Unknown, 0 observed
        "type": DeviceHexDataTypes.sile.value,
        VALUE_DEFAULT: 0,
    },
    "a6": {
        "name": "set_disable_grid_export_switch",  # Allow export (0), disable export (1)
        "type": DeviceHexDataTypes.sile.value,
        STATE_NAME: "grid_export_disabled",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
}

CMD_SB_PV_LIMIT = CMD_COMMON | {
    # Command: Solarbank Set max photovoltaik input limit (MPPT limit)
    COMMAND_NAME: SolixMqttCommands.sb_pv_limit_select,
    "a7": {
        "name": "set_sb_pv_limit_select",  # 2000 or 3600
        "type": DeviceHexDataTypes.sile.value,
        STATE_NAME: "pv_limit",
        VALUE_OPTIONS: [2000, 3600],
    },
}
CMD_SB_AC_INPUT_LIMIT = CMD_COMMON | {
    # Command: Solarbank Set max AC input limit (AC charge)
    COMMAND_NAME: SolixMqttCommands.sb_ac_input_limit,
    "a8": {
        "name": "set_ac_input_limit",  # 0 - 1200 W, step: 100
        "type": DeviceHexDataTypes.sile.value,
        STATE_NAME: "ac_input_limit",
        VALUE_MIN: 0,
        VALUE_MAX: 1200,
        VALUE_STEP: 100,
    },
}

CMD_SB_LIGHT_SWITCH = CMD_COMMON | {
    # Command: Solarbank light switch
    COMMAND_NAME: SolixMqttCommands.sb_light_switch,
    "a2": {
        "name": "set_light_off_switch",  # Light Off (1), Light On (0)
        "type": DeviceHexDataTypes.ui.value,
        STATE_NAME: "light_off_switch",
        VALUE_OPTIONS: {"off": 1, "on": 0},
    },
    "a3": {
        "name": "set_light_mode",  # use actual state of switch
        "type": DeviceHexDataTypes.ui.value,
        VALUE_STATE: "light_mode",  # use this actual state as value
        VALUE_DEFAULT: 0,
    },
}

CMD_SB_LIGHT_MODE = CMD_COMMON | {
    # Command: Solarbank light mode
    COMMAND_NAME: SolixMqttCommands.sb_light_mode_select,
    "a2": {
        "name": "set_light_off_switch",  # use actual state of switch
        "type": DeviceHexDataTypes.ui.value,
        VALUE_STATE: "light_off_switch",  # use this actual state as value
        VALUE_DEFAULT: 0,
    },
    "a3": {
        "name": "set_light_mode",  # Normal (0), Mood light (1)
        "type": DeviceHexDataTypes.ui.value,
        STATE_NAME: "light_mode",
        VALUE_OPTIONS: {"normal": 0, "mood": 1},
    },
}

CMD_SB_DEVICE_TIMEOUT = CMD_COMMON | {
    # Command: Solarbank device timeout
    COMMAND_NAME: SolixMqttCommands.sb_device_timeout,
    "a2": {
        "name": "set_device_timeout_30min",  # (0 - 48) * 30 min
        "type": DeviceHexDataTypes.ui.value,
        STATE_NAME: "device_timeout_minutes",
        VALUE_OPTIONS: [0, 30, 60, 120, 240, 360, 720, 1440],  # in minutes as state
        VALUE_DIVIDER: 30,
    },
}
