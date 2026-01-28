"""Define mapping for MQTT command messages and field conversions."""

from dataclasses import asdict, dataclass
from typing import Final

from .apitypes import DeviceHexDataTypes

# common mapping keys to be used for status and command descriptions
NAME: Final[str] = "name"  # name of the data field, also used for message descriptions
TYPE: Final[str] = (
    "type"  # type the data field relevant for de/encoding, must be a byte as defined in DeviceHexDataTypes
)
TOPIC: Final[str] = "topic"  # topic suffix of the command or message
FACTOR: Final[str] = (
    "factor"  # Factor for decoding the data field value. Any command setting this state data field should use the same VALUE_DIVIDER typically
)
SIGNED: Final[str] = (
    "signed"  # Boolean flag to indicate the value decoder to use given value decoding signing (required if different than default field type signing)
)
BYTES: Final[str] = (
    "bytes"  # Key word to start nested data field break down description map for individual bytes or byte ranges
)
LENGTH: Final[str] = (
    "length"  # Define the length of a field in a bytes field breakdown. Only need to be used if length not determined by field type or first byte value
)
MASK: Final[str] = (
    "mask"  # Define a bit mask value to be used for decoding the data value. Required if a single byte may reflect multiple data fields/settings
)
COMMAND_NAME: Final[str] = (
    "command_name"  # name of the command, must be defined in dataclass SolixMqttCommands
)
COMMAND_LIST: Final[str] = (
    "command_list"  # specifies the nested commands to describe multiple commands per message type
)
STATE_NAME: Final[str] = (
    "state_name"  # extracted value name that represents the current state of the control
)
STATE_CONVERTER: Final[str] = (
    "state_converter"  # optional lambda function to convert the setting value into expected state and vice versa
)
VALUE_MIN: Final[str] = "value_min"  # min value of a range
VALUE_MAX: Final[str] = "value_max"  # max value of a range
VALUE_STEP: Final[str] = "value_step"  # step to be used within range, default is 1
VALUE_OPTIONS: Final[str] = (
    "value_options"  # Use list for value options, or dict for name:value mappings
)
VALUE_DEFAULT: Final[str] = "value_default"  # Defines a default value for the field
VALUE_FOLLOWS: Final[str] = (
    "value_follows"  # defines setting name the value depends on, the options need to define a map for the dependencies
)
VALUE_STATE: Final[str] = (
    "value_state"  # Defines a state name that should be used if found
)
VALUE_DIVIDER: Final[str] = (
    "value_divider"  # Defines a divider for the applied value, should be same as FACTOR extracting the state value data field
)


@dataclass(frozen=True)
class SolixMqttCommands:
    """Dataclass for used Anker Solix MQTT command names."""

    status_request: str = "status_request"
    realtime_trigger: str = "realtime_trigger"
    timer_request: str = "timer_request"
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
    sb_min_soc_select: str = "sb_min_soc_select"  # Does not change App station wide setting, needs Api request as well
    sb_inverter_type_select: str = "sb_inverter_type_select"
    sb_max_load: str = "sb_max_load"
    sb_max_load_parallel: str = "sb_max_load_parallel"
    sb_ac_input_limit: str = "sb_ac_input_limit"
    sb_ac_socket_switch: str = "sb_ac_socket_switch"
    sb_pv_limit_select: str = "sb_pv_limit_select"
    sb_light_switch: str = "sb_light_switch"
    sb_light_mode_select: str = "sb_light_mode_select"
    sb_disable_grid_export_switch: str = "sb_disable_grid_export_switch"
    sb_device_timeout: str = "sb_device_timeout"
    sb_usage_mode: str = "sb_usage_mode"  # Not supported, uses various field patterns per mode with same command message
    sb_3rd_party_pv_switch: str = "sb_3rd_party_pv_switch"  # Driven through cloud
    sb_ev_charger_switch: str = "sb_ev_charger_switch"  # Driven through cloud
    plug_schedule: str = "plug_schedule"
    plug_delayed_toggle: str = "plug_delayed_toggle"

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
        NAME: "msg_timestamp",
        TYPE: DeviceHexDataTypes.str.value,
    },
}

TIMESTAMP_FE = {
    # classical format using 4 bytes for timestamp value in sec
    # value will be composed automatically based on name and field
    "fe": {
        NAME: "msg_timestamp",
        TYPE: DeviceHexDataTypes.var.value,
    },
}

CMD_COMMON = {
    # Common command pattern seen in most of the commands
    TOPIC: "req",
    "a1": {NAME: "pattern_22"},  # Bytes composed automatically based on name and field
} | TIMESTAMP_FE

CMD_COMMON_V2 = {
    # Common command pattern V2 seen in most of the commands for newer devices with timestamp in ms
    TOPIC: "req",
    "a1": {NAME: "pattern_22"},  # Bytes composed automatically based on name and field
} | TIMESTAMP_FD

CMD_STATUS_REQUEST = CMD_COMMON | {
    # Command: Device status request
    COMMAND_NAME: SolixMqttCommands.status_request,
}

CMD_REALTIME_TRIGGER = CMD_COMMON | {
    # Command: Real time data message trigger
    COMMAND_NAME: SolixMqttCommands.realtime_trigger,
    "a2": {
        NAME: "set_realtime_trigger",  # Disable (0) | Enable (1)
        TYPE: DeviceHexDataTypes.ui.value,
        VALUE_OPTIONS: {"off": 0, "on": 1},
        VALUE_DEFAULT: 1,
    },
    "a3": {
        NAME: "trigger_timeout_sec",  # realtime timeout in seconds when enabled
        TYPE: DeviceHexDataTypes.var.value,
        VALUE_MIN: 60,  # real limit is unknown
        VALUE_MAX: 600,  # real limit is unknown
        VALUE_DEFAULT: 60,
    },
}

CMD_TIMER_REQUEST = CMD_COMMON | {
    # Command: Device timer request
    COMMAND_NAME: SolixMqttCommands.timer_request,
}

CMD_TEMP_UNIT = CMD_COMMON | {
    # Command: Set temperature unit
    COMMAND_NAME: SolixMqttCommands.temp_unit_switch,
    "a2": {
        NAME: "set_temp_unit_fahrenheit",  # Celsius (0) | Fahrenheit (1)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "temp_unit_fahrenheit",
        VALUE_OPTIONS: {"celsius": 0, "fahrenheit": 1},
    },
}

CMD_DEVICE_MAX_LOAD = CMD_COMMON | {
    # Command: Set device max home load in Watt
    COMMAND_NAME: SolixMqttCommands.device_max_load,
    "a2": {
        NAME: "set_device_max_load",  # supported value in Watt
        TYPE: DeviceHexDataTypes.sile.value,
        STATE_NAME: "max_load",
    },
}

CMD_DEVICE_TIMEOUT_MIN = CMD_COMMON | {
    # Command: Set device timeout in minutes
    COMMAND_NAME: SolixMqttCommands.device_timeout_minutes,
    "a2": {
        NAME: "set_device_timeout_min",  # 0 (Never), 30, 60, 120, 240, 360, 720, 1440
        TYPE: DeviceHexDataTypes.sile.value,
        STATE_NAME: "device_timeout_minutes",
        VALUE_OPTIONS: [0, 30, 60, 120, 240, 360, 720, 1440],
    },
}

CMD_AC_CHARGE_SWITCH = CMD_COMMON | {
    # Command: Enable AC backup charge
    COMMAND_NAME: SolixMqttCommands.ac_charge_switch,
    "a2": {
        NAME: "set_ac_charge_switch",  # Disable (0) | Enable (1)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "backup_charge_switch",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
}

CMD_AC_CHARGE_LIMIT = CMD_COMMON | {
    # Command: Set AC backup charge limit
    COMMAND_NAME: SolixMqttCommands.ac_charge_limit,
    "a2": {
        NAME: "set_ac_input_limit",  # supported Watt value
        TYPE: DeviceHexDataTypes.sile.value,
        STATE_NAME: "ac_input_limit",
    },
}

CMD_AC_OUTPUT_SWITCH = CMD_COMMON | {
    # Command: PPS AC output switch setting
    COMMAND_NAME: SolixMqttCommands.ac_output_switch,
    "a2": {
        NAME: "set_ac_output_switch",  # Disable (0) | Enable (1)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "ac_output_power_switch",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
}

CMD_AC_FAST_CHARGE_SWITCH = CMD_COMMON | {
    # Command: PPS AC (ultra)fast charge switch setting
    COMMAND_NAME: SolixMqttCommands.ac_fast_charge_switch,
    "a2": {
        NAME: "set_ac_fast_charge_switch",  # Disable (0) | Enable (1)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "fast_charge_switch",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
}

CMD_AC_OUTPUT_MODE = CMD_COMMON | {
    # Command: PPS AC output mode setting
    COMMAND_NAME: SolixMqttCommands.ac_output_mode_select,
    "a2": {
        NAME: "set_ac_output_mode",  # Normal (1), Smart (0)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "ac_output_mode",
        STATE_CONVERTER: lambda value, state: {0: 2, 1: 1}.get(value, 2)
        if value is not None
        else {2: 0, 1: 1}.get(state, 0),  # Smart setting represented with state 2
        VALUE_OPTIONS: {"smart": 0, "normal": 1},
    },
}

CMD_AC_OUTPUT_TIMEOUT_SEC = (
    CMD_COMMON
    | {
        # Command: PPS AC output timeout setting
        COMMAND_NAME: SolixMqttCommands.ac_output_timeout_seconds,
        "a2": {
            NAME: "set_ac_output_timeout_seconds",  # Timeout seconds, custom range: 0-86400, step 300
            TYPE: DeviceHexDataTypes.var.value,
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
        NAME: "set_dc_output_switch",  # Disable (0) | Enable (1)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "dc_output_power_switch",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
}

CMD_DC_12V_OUTPUT_MODE = CMD_COMMON | {
    # Command: PPS 12V DC output mode setting
    COMMAND_NAME: SolixMqttCommands.dc_12v_output_mode_select,
    "a2": {
        NAME: "set_dc_12v_output_mode",  # Normal (1), Smart (0)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "dc_12v_output_mode",
        STATE_CONVERTER: lambda value, state: {0: 2, 1: 1}.get(value, 2)
        if value is not None
        else {2: 0, 1: 1}.get(state, 0),  # Smart setting represented with state 2
        VALUE_OPTIONS: {"smart": 0, "normal": 1},
    },
}

CMD_DC_OUTPUT_TIMEOUT_SEC = (
    CMD_COMMON
    | {
        # Command: PPS DC output timeout setting
        COMMAND_NAME: SolixMqttCommands.dc_output_timeout_seconds,
        "a2": {
            NAME: "set_dc_output_timeout_seconds",  # Timeout seconds, custom range: 0-86400, step 300
            TYPE: DeviceHexDataTypes.var.value,
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
        NAME: "set_light_switch",  # Off (0), On (1)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "light_switch",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
}

CMD_LIGHT_MODE = CMD_COMMON | {
    # Command: PPS light mode setting
    COMMAND_NAME: SolixMqttCommands.light_mode_select,
    "a2": {
        NAME: "set_light_mode",  # Off (0), Low (1), Medium (2), High (3), Blinking (4)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "light_mode",
        VALUE_OPTIONS: {"off": 0, "low": 1, "medium": 2, "high": 3, "blinking": 4},
    },
}

CMD_DISPLAY_SWITCH = CMD_COMMON | {
    # Command: PPS display switch setting
    COMMAND_NAME: SolixMqttCommands.display_switch,
    "a2": {
        NAME: "set_display_switch",  # Off (0), On (1)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "display_switch",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
}

CMD_DISPLAY_MODE = CMD_COMMON | {
    # Command: PPS display mode setting
    COMMAND_NAME: SolixMqttCommands.display_mode_select,
    "a2": {
        NAME: "set_display_mode",  # Off (0), Low (1), Medium (2), High (3)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "display_mode",
        VALUE_OPTIONS: {"off": 0, "low": 1, "medium": 2, "high": 3},
    },
}

CMD_DISPLAY_TIMEOUT_SEC = CMD_COMMON | {
    # Command: Set display timeout in seconds
    COMMAND_NAME: SolixMqttCommands.display_timeout_seconds,
    "a2": {
        NAME: "set_display_timeout_sec",  # supported value in seconds
        TYPE: DeviceHexDataTypes.sile.value,
        STATE_NAME: "display_timeout_seconds",
        VALUE_OPTIONS: [20, 30, 60, 300, 1800],
    },
}

CMD_PORT_MEMORY_SWITCH = CMD_COMMON | {
    # Command: PPS port memory switch setting
    COMMAND_NAME: SolixMqttCommands.port_memory_switch,
    "a2": {
        NAME: "set_port_memory_switch",  # Off (0), On (1)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "port_memory_switch",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
}

CMD_SOC_LIMITS_V2 = CMD_COMMON_V2 | {
    # Command: PPS soc limit settings
    COMMAND_NAME: SolixMqttCommands.soc_limits,
    "aa": {
        NAME: "set_max_soc",  # max_soc: 80, 85, 90, 95, 100 %
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "max_soc",
        VALUE_OPTIONS: [80, 85, 90, 95, 100],
        VALUE_STATE: "max_soc",
    },
    "ab": {
        NAME: "set_min_soc",  # min_soc: 1, 5, 10, 15, 20 %
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "power_cutoff",
        VALUE_OPTIONS: [1, 5, 10, 15, 20],
        VALUE_STATE: "power_cutoff",
    },
}

CMD_SB_STATUS_CHECK = (
    CMD_COMMON
    | {
        # Command: Solarbank 1 Status check request?
        # NOTE: This command schema is incomplete and not supported yet
        COMMAND_NAME: SolixMqttCommands.sb_status_check,
        "a2": {
            NAME: "device_sn",
            TYPE: DeviceHexDataTypes.str.value,
            "length": 16,
        },
        "a3": {
            NAME: "charging_status",
            TYPE: DeviceHexDataTypes.ui.value,
        },
        "a4": {
            NAME: "set_output_preset",  # in W
            TYPE: DeviceHexDataTypes.var.value,
        },
        "a5": {
            NAME: "status_timeout_sec?",  # timeout for next status message?
            TYPE: DeviceHexDataTypes.var.value,
        },
        "a6": {
            NAME: "local_timestamp",  # used for time synchronization?
            TYPE: DeviceHexDataTypes.var.value,
        },
        "a7": {
            NAME: "next_status_timestamp",  # Requested time for next status message +56-57 seconds
            TYPE: DeviceHexDataTypes.var.value,
        },
        "a8": {
            NAME: "status_check_unknown_1?",
            TYPE: DeviceHexDataTypes.ui.value,
        },
        "a9": {
            NAME: "status_check_unknown_2?",
            TYPE: DeviceHexDataTypes.ui.value,
        },
        "aa": {
            NAME: "status_check_unknown_3?",
            TYPE: DeviceHexDataTypes.ui.value,
        },
    }
)

CMD_SB_POWER_CUTOFF = CMD_COMMON | {
    # Command: Solarbank Set Power cutoff
    COMMAND_NAME: SolixMqttCommands.sb_power_cutoff_select,
    "a2": {
        NAME: "set_output_cutoff_data",  # 10 | 5 %
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "output_cutoff_data",
        VALUE_OPTIONS: [5, 10],
    },
    "a3": {
        NAME: "set_lowpower_input_data",  # 5 | 4 %
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "lowpower_input_data",
        VALUE_FOLLOWS: "set_output_cutoff_data",
        VALUE_OPTIONS: {5: 4, 10: 5},
    },
    "a4": {
        NAME: "set_input_cutoff_data",  # 10 | 5 %
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "input_cutoff_data",
        VALUE_FOLLOWS: "set_output_cutoff_data",
        VALUE_OPTIONS: {5: 5, 10: 10},
    },
}

CMD_SB_MIN_SOC = CMD_COMMON | {
    # Command: Solarbank Set max AC input limit (AC charge)
    COMMAND_NAME: SolixMqttCommands.sb_min_soc_select,
    "a2": {
        NAME: "set_min_soc",  # 5 or 10 %
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "power_cutoff",
        VALUE_OPTIONS: [5, 10],
    },
}

CMD_SB_INVERTER_TYPE = CMD_SB_POWER_CUTOFF | {
    # Command: Solarbank 1 set Inverter Type and limits
    COMMAND_NAME: SolixMqttCommands.sb_inverter_type_select,
    # NOTE: This command schema is incomplete and not supported yet
    "a5": {
        NAME: "set_inverter_brand",  # Hex bytes of brand name, length varies
        TYPE: DeviceHexDataTypes.bin.value,
    },
    "a6": {
        NAME: "set_inverter_model",  # Hey bytes of model name, length varies
        TYPE: DeviceHexDataTypes.bin.value,
    },
    "a7": {
        NAME: "set_min_load",  # in W
        TYPE: DeviceHexDataTypes.sile.value,
    },
    "a8": {
        NAME: "set_max_load",  # in W
        TYPE: DeviceHexDataTypes.sile.value,
    },
    "a9": {
        NAME: "set_inverter_unknown_1?",  # May be 0 typically
        TYPE: DeviceHexDataTypes.ui.value,
    },
    "aa": {
        NAME: "set_ch_1_min_what?",  # 500 or other, supported values unknown
        TYPE: DeviceHexDataTypes.var.value,
    },
    "ab": {
        NAME: "set_ch_1_max_what?",  # 10000 or other, supported values unknown
        TYPE: DeviceHexDataTypes.var.value,
    },
    "ac": {
        NAME: "set_ch_2_min_what?",  # 500 or other, supported values unknown
        TYPE: DeviceHexDataTypes.var.value,
    },
    "ad": {
        NAME: "set_ch_2_max_what?",  # 10000 or other, supported values unknown
        TYPE: DeviceHexDataTypes.var.value,
    },
}

CMD_SB_AC_SOCKET_SWITCH = CMD_COMMON | {
    # Command: Solarbank switch to toggle AC socket
    COMMAND_NAME: SolixMqttCommands.sb_ac_socket_switch,
    "a2": {
        NAME: "set_ac_socket_switch",  # Off (0), On (1)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "ac_socket_switch",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
}

CMD_SB_3RD_PARTY_PV_SWITCH = CMD_COMMON | {
    # Command: Switch to enable 3rd Party PV support
    COMMAND_NAME: SolixMqttCommands.sb_3rd_party_pv_switch,
    "a2": {
        NAME: "set_3rd_party_pv_switch",  # Off (0), On (1)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "3rd_party_pv_switch",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
}

CMD_SB_EV_CHARGER_SWITCH = CMD_COMMON | {
    # Command: Switch to enable EV charger support
    COMMAND_NAME: SolixMqttCommands.sb_ev_charger_switch,
    "a2": {
        NAME: "set_ev_charger_switch",  # Off (0), On (1)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "ev_charger_switch",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
}


CMD_SB_MAX_LOAD = (
    CMD_COMMON
    | {
        # Command: Solarbank Set max load
        COMMAND_NAME: SolixMqttCommands.sb_max_load,
        "a2": {
            NAME: "set_max_load",  # AC output limit in W, various options, different per model
            TYPE: DeviceHexDataTypes.sile.value,
            STATE_NAME: "max_load",
        },
        "a3": {
            NAME: "set_max_load_type",  # single load (3), parallel load (2), individual (0)
            TYPE: DeviceHexDataTypes.sile.value,
            VALUE_DEFAULT: 0,
            VALUE_OPTIONS: {"individual": 0, "parallel": 2, "single": 3},
        },
    }
)

CMD_SB_DISABLE_GRID_EXPORT_SWITCH = CMD_COMMON | {
    # Command: Solarbank disable grid export on PV surplus
    COMMAND_NAME: SolixMqttCommands.sb_disable_grid_export_switch,
    "a5": {
        NAME: "set_disable_grid_export_a5?",  # Unknown, 0 observed
        TYPE: DeviceHexDataTypes.sile.value,
        VALUE_DEFAULT: 0,
    },
    "a6": {
        NAME: "set_disable_grid_export_switch",  # Allow export (0), disable export (1)
        TYPE: DeviceHexDataTypes.sile.value,
        STATE_NAME: "grid_export_disabled",
        VALUE_OPTIONS: {"off": 0, "on": 1},
        VALUE_STATE: "grid_export_disabled",
    },
    "a9": {
        NAME: "set_grid_export_limit",  # 0-100000, step 100
        TYPE: DeviceHexDataTypes.sile.value,
        VALUE_DEFAULT: 0,
        VALUE_STATE: "grid_export_limit",
        VALUE_MIN: 0,
        VALUE_MAX: 100000,
        VALUE_STEP: 100,
    },
}

CMD_SB_PV_LIMIT = CMD_COMMON | {
    # Command: Solarbank Set max photovoltaik input limit (MPPT limit)
    COMMAND_NAME: SolixMqttCommands.sb_pv_limit_select,
    "a7": {
        NAME: "set_sb_pv_limit_select",  # 2000 or 3600
        TYPE: DeviceHexDataTypes.sile.value,
        STATE_NAME: "pv_limit",
        VALUE_OPTIONS: [2000, 3600],
    },
}

CMD_SB_AC_INPUT_LIMIT = CMD_COMMON | {
    # Command: Solarbank Set max AC input limit (AC charge)
    COMMAND_NAME: SolixMqttCommands.sb_ac_input_limit,
    "a8": {
        NAME: "set_ac_input_limit",  # 0 - 1200 W, step: 100
        TYPE: DeviceHexDataTypes.sile.value,
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
        NAME: "set_light_mode",  # use actual state of switch
        TYPE: DeviceHexDataTypes.ui.value,
        VALUE_STATE: "light_mode",  # use this actual state as value
        STATE_NAME: "light_mode",
        VALUE_DEFAULT: 0,
    },
    "a3": {
        NAME: "set_light_off_switch",  # Light Off (1), Light On (0)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "light_off_switch",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
}

CMD_SB_LIGHT_MODE = CMD_COMMON | {
    # Command: Solarbank light mode
    COMMAND_NAME: SolixMqttCommands.sb_light_mode_select,
    "a2": {
        NAME: "set_light_mode",  # Normal (0), Mood light (1)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "light_mode",
        VALUE_OPTIONS: {"normal": 0, "mood": 1},
    },
    "a3": {
        NAME: "set_light_off_switch",  # use actual state of switch
        TYPE: DeviceHexDataTypes.ui.value,
        VALUE_STATE: "light_off_switch",  # use this actual state as value
        STATE_NAME: "light_off_switch",
        VALUE_DEFAULT: 0,
    },
}

CMD_SB_DEVICE_TIMEOUT = CMD_COMMON | {
    # Command: Solarbank device timeout
    COMMAND_NAME: SolixMqttCommands.sb_device_timeout,
    "a2": {
        NAME: "set_device_timeout_min",  # (0 - 48) * 30 min factor
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "device_timeout_minutes",
        VALUE_OPTIONS: [0, 30, 60, 120, 240, 360, 720, 1440],  # in minutes as state
        VALUE_DIVIDER: 30,
    },
}

USE_TIME_SLOT = {
    TYPE: DeviceHexDataTypes.ui.value,
    VALUE_OPTIONS: {"discharge": 1, "charge": 4, "default": 6},
    VALUE_DEFAULT: 6,
}

CMD_SB_USAGE_MODE = (
    CMD_COMMON
    | {
        # Command: Solarbank Usage mode
        # NOTE: This is driven through the cloud Api and should not be modified directly
        # ATTENTION: The type and amount of the fields varies depending on usage mode, so it cannot be described actually for proper encoding
        # The field names also vary, this command must not be enabled in the Mqtt device class for solarbanks
        COMMAND_NAME: SolixMqttCommands.sb_usage_mode,
        "a2": {
            NAME: "set_usage_mode",
            TYPE: DeviceHexDataTypes.ui.value,
            STATE_NAME: "usage_mode",
            VALUE_OPTIONS: {
                "manual": 1,  # Api scene mode is 3
                "smartmeter": 2,  # Api scene mode is 1
                "smartplugs": 3,  # Api scene mode is 2
                "backup": 4,
                "use_time": 5,
                "smart": 7,
                "time_slot": 8,
            },
        },
        "a3": {
            NAME: "set_timestamp_a3_or_0?",  # unknown timestamp as var field or ui 0
            TYPE: DeviceHexDataTypes.ui.value,
        },
        "a4": {
            NAME: "set_backup_charge_switch",  # various options depending on usage mode, eventually a bitmask is used
            TYPE: DeviceHexDataTypes.ui.value,
            STATE_NAME: "backup_charge_switch",
            VALUE_OPTIONS: {"off": 0, "on": 1},
            VALUE_DEFAULT: 0,
        },
        "a5": {
            NAME: "set_dynamic_soc_limit",  # 10-100 %, step 1 % or 0 if not used
            TYPE: DeviceHexDataTypes.ui.value,
            STATE_NAME: "dynamic_soc_limit",
            VALUE_MIN: 10,
            VALUE_MAX: 100,
            VALUE_DEFAULT: 0,
        },
        "a6": {
            NAME: "set_timestamp_backup_start",
            TYPE: DeviceHexDataTypes.var.value,
            STATE_NAME: "timestamp_backup_start",
        },
        "a6_mode_8": {
            NAME: "set_time_slot_modes",  # 48 slots, 1 byte per hour, paired today / tomorrow?,
            TYPE: DeviceHexDataTypes.bin.value,
            BYTES: {
                "00": USE_TIME_SLOT,
                "01": USE_TIME_SLOT,
                "02": USE_TIME_SLOT,
                "03": USE_TIME_SLOT,
                "04": USE_TIME_SLOT,
                "05": USE_TIME_SLOT,
                "06": USE_TIME_SLOT,
                "07": USE_TIME_SLOT,
                "08": USE_TIME_SLOT,
                "09": USE_TIME_SLOT,
                "10": USE_TIME_SLOT,
                "11": USE_TIME_SLOT,
                "12": USE_TIME_SLOT,
                "13": USE_TIME_SLOT,
                "14": USE_TIME_SLOT,
                "15": USE_TIME_SLOT,
                "16": USE_TIME_SLOT,
                "17": USE_TIME_SLOT,
                "18": USE_TIME_SLOT,
                "19": USE_TIME_SLOT,
                "20": USE_TIME_SLOT,
                "21": USE_TIME_SLOT,
                "22": USE_TIME_SLOT,
                "23": USE_TIME_SLOT,
                "24": USE_TIME_SLOT,
                "25": USE_TIME_SLOT,
                "26": USE_TIME_SLOT,
                "27": USE_TIME_SLOT,
                "28": USE_TIME_SLOT,
                "29": USE_TIME_SLOT,
                "30": USE_TIME_SLOT,
                "31": USE_TIME_SLOT,
                "32": USE_TIME_SLOT,
                "33": USE_TIME_SLOT,
                "34": USE_TIME_SLOT,
                "35": USE_TIME_SLOT,
                "36": USE_TIME_SLOT,
                "37": USE_TIME_SLOT,
                "38": USE_TIME_SLOT,
                "39": USE_TIME_SLOT,
                "40": USE_TIME_SLOT,
                "41": USE_TIME_SLOT,
                "42": USE_TIME_SLOT,
                "43": USE_TIME_SLOT,
                "44": USE_TIME_SLOT,
                "45": USE_TIME_SLOT,
                "46": USE_TIME_SLOT,
                "47": USE_TIME_SLOT,
                "48": USE_TIME_SLOT,
            },
        },
        "a7": {
            NAME: "set_timestamp_backup_end",
            TYPE: DeviceHexDataTypes.var.value,
            STATE_NAME: "timestamp_backup_end",
        },
    }
)

CMD_PLUG_SCHEDULE = (
    CMD_COMMON
    | {
        # Command: Smartplug schedule
        COMMAND_NAME: SolixMqttCommands.plug_schedule,
        "a2": {
            NAME: "set_plug_schedule_a2?",  # 1 - unknown
            TYPE: DeviceHexDataTypes.ui.value,
            VALUE_DEFAULT: 1,
        },
        "a3": {
            NAME: "set_plug_schedule_order?",  # 1 - x
            TYPE: DeviceHexDataTypes.ui.value,
            VALUE_MIN: 1,
            VALUE_MAX: 10,
        },
        "a4": {
            NAME: "set_plug_schedule_a4?",  # 1 - unknown
            TYPE: DeviceHexDataTypes.ui.value,
            VALUE_DEFAULT: 1,
        },
        "a5": {
            NAME: "set_plug_schedule_time",  # first byte = hour 0-23, second byte = minute 00-59
            TYPE: DeviceHexDataTypes.sile.value,
            VALUE_MIN: 0,
            VALUE_MAX: 15127,  # 173b hex little endian for 23:59 time
        },
        "a6": {
            NAME: "set_plug_schedule_switch",  # Off (0), On (1)
            TYPE: DeviceHexDataTypes.ui.value,
            VALUE_OPTIONS: {"off": 0, "on": 1},
        },
    }
)

CMD_PLUG_DELAYED_TOGGLE = CMD_COMMON | {
    # Command: Smartplug delayed toggle
    COMMAND_NAME: SolixMqttCommands.plug_delayed_toggle,
    "a2": {
        NAME: "set_toggle_to_switch?",  # Off (0), On (1)
        TYPE: DeviceHexDataTypes.ui.value,
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
    "a3": {
        # NAME: "set_toggle_to_delay?",  # 3 bytes: Seconds:Minutes:Hours
        TYPE: DeviceHexDataTypes.bin.value,
        BYTES: {
            "00": {
                NAME: "set_toggle_to_delay_seconds",
                TYPE: DeviceHexDataTypes.ui.value,
                VALUE_MIN: 0,
                VALUE_MAX: 59,
                VALUE_DEFAULT: 0,
            },
            "01": {
                NAME: "set_toggle_to_delay_minutes?",
                TYPE: DeviceHexDataTypes.ui.value,
                VALUE_MIN: 0,
                VALUE_MAX: 59,
                VALUE_DEFAULT: 0,
            },
            "02": {
                NAME: "set_toggle_to_delay_hours?",
                TYPE: DeviceHexDataTypes.ui.value,
                VALUE_MIN: 0,
                VALUE_MAX: 23,
                VALUE_DEFAULT: 0,
            },
        },
    },
    "a4": {
        NAME: "set_toggle_back_switch?",  # Off (0), On (1)
        TYPE: DeviceHexDataTypes.ui.value,
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
    "a5": {
        # NAME: "set_toggle_back_delay?",  # 3 bytes: Seconds:Minutes:Hours
        TYPE: DeviceHexDataTypes.bin.value,
        BYTES: {
            "00": {
                NAME: "set_toggle_back_delay_seconds?",
                TYPE: DeviceHexDataTypes.ui.value,
                VALUE_MIN: 0,
                VALUE_MAX: 59,
                VALUE_DEFAULT: 0,
            },
            "01": {
                NAME: "set_toggle_back_delay_minutes?",
                TYPE: DeviceHexDataTypes.ui.value,
                VALUE_MIN: 0,
                VALUE_MAX: 59,
                VALUE_DEFAULT: 0,
            },
            "02": {
                NAME: "set_toggle_back_delay_hours?",
                TYPE: DeviceHexDataTypes.ui.value,
                VALUE_MIN: 0,
                VALUE_MAX: 23,
                VALUE_DEFAULT: 0,
            },
        },
    },
}
