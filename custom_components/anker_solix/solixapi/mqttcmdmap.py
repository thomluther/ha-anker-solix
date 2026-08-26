"""Define mapping for MQTT command messages and field conversions."""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Final

from .apitypes import DeviceHexDataTypes
from .helpers import (
    convert_circuit_setup,
    convert_port_protocols,
    convert_pps_tou_schedule,
    convert_weekdays,
)

# common mapping keys to be used for status and command descriptions
EMBEDDED: Final[str] = (
    "embedded"  # name of the json field that contains the embedded message hex data
)
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
MASK_STATE: Final[str] = (
    "mask_state"  # Define a state name to obtain initial bitmask field value
)
MASK_VALUE: Final[str] = (
    "mask_value"  # Field to save the last state found as defined with mask_state value
)
OFFSET: Final[str] = (
    "offset"  # Key word to indicate byte offset to use from beginning of field
)
COMMAND_NAME: Final[str] = (
    "command_name"  # name of the command, must be defined in dataclass SolixMqttCommands
)
COMMAND_LIST: Final[str] = (
    "command_list"  # specifies the nested commands to describe multiple commands per message type
)
COMMAND_ENCODING: Final[str] = "command_encoding"  # encoding_type for command message
STATE_NAME: Final[str] = (
    "state_name"  # extracted value name that represents the current state of the control
)
STATE_CONVERTER: Final[str] = (
    "state_converter"  # optional lambda function (value, state, cache) to convert the setting value into expected state and vice versa
)
VALUE_MIN: Final[str] = "value_min"  # min value of a range
VALUE_MAX: Final[str] = "value_max"  # max value of a range
VALUE_STEP: Final[str] = "value_step"  # step to be used within range, default is 1
VALUE_OPTIONS: Final[str] = (
    "value_options"  # Use list for value options, or dict for name:value mappings
)
VALUE_DEFAULT: Final[str] = "value_default"  # Defines a default value for the field
VALUE_FOLLOWS: Final[str] = (
    "value_follows"  # defines setting name the value depends on, the options may define a map for the dependencies or the state converter
)
VALUE_SKIP: Final[str] = (
    "value_skip"  # optional lambda function (value, cache) to skip the value if function is true
)
VALUE_STATE: Final[str] = (
    "value_state"  # Defines a state name that should be used to obtain the value if found
)
VALUE_MIN_STATE: Final[str] = (
    "value_min_state"  # Defines a state name that should be used to obtain the min value of a range if found
)
VALUE_MAX_STATE: Final[str] = (
    "value_max_state"  # Defines a state name that should be used to obtain the max value of a range if found
)
VALUE_OPTIONS_STATE: Final[str] = (
    "value_options_state"  # Defines a state name that should be used to obtain the valid options for field if found
)
VALUE_DIVIDER: Final[str] = (
    "value_divider"  # Defines a divider for the applied value, should be same as FACTOR extracting the state value data field
)


@dataclass(frozen=True)
class SolixMqttCommands:
    """Dataclass for used Anker Solix MQTT command names."""

    status_request: str = "status_request"
    theme_request: str = "theme_request"
    realtime_trigger: str = "realtime_trigger"
    timer_request: str = "timer_request"
    temp_unit_switch: str = "temp_unit_switch"
    device_max_load: str = "device_max_load"
    device_timeout_minutes: str = "device_timeout_minutes"
    ac_fast_charge_switch: str = "ac_fast_charge_switch"
    ac_charge_limit: str = "ac_charge_limit"
    ac_output_switch: str = "ac_output_switch"
    ac_output_mode_select: str = "ac_output_mode_select"
    ac_output_timeout_seconds: str = "ac_output_timeout_seconds"
    ac_output_timeout_minutes: str = "ac_output_timeout_minutes"
    ac_output_timer: str = "ac_output_timer"
    dc_output_switch: str = "dc_output_switch"
    dc_12v_output_mode_select: str = "dc_12v_output_mode_select"
    dc_output_timeout_seconds: str = "dc_output_timeout_seconds"
    energy_saving_switch: str = "energy_saving_switch"
    display_switch: str = "display_switch"
    display_mode_select: str = "display_mode_select"
    display_timeout_seconds: str = "display_timeout_seconds"
    display_timeout_mode_select: str = "display_timeout_mode_select"
    display_brightness: str = "display_brightness"
    light_switch: str = "light_switch"
    light_mode_select: str = "light_mode_select"
    port_memory_switch: str = "port_memory_switch"
    usbc_1_port_switch: str = "usbc_1_port_switch"
    usbc_2_port_switch: str = "usbc_2_port_switch"
    usbc_3_port_switch: str = "usbc_3_port_switch"
    usbc_4_port_switch: str = "usbc_4_port_switch"
    usba_port_switch: str = "usba_port_switch"
    ac_1_port_switch: str = "ac_1_port_switch"
    ac_2_port_switch: str = "ac_2_port_switch"
    usbc_1_port_timer: str = "usbc_1_port_timer"
    usbc_2_port_timer: str = "usbc_2_port_timer"
    usbc_3_port_timer: str = "usbc_3_port_timer"
    usbc_4_port_timer: str = "usbc_4_port_timer"
    usba_port_timer: str = "usba_port_timer"
    usbc_1_start_time: str = "usbc_1_start_time"
    usbc_2_start_time: str = "usbc_2_start_time"
    usbc_3_start_time: str = "usbc_3_start_time"
    usbc_4_start_time: str = "usbc_4_start_time"
    usba_start_time: str = "usba_start_time"
    usbc_1_end_time: str = "usbc_1_end_time"
    usbc_2_end_time: str = "usbc_2_end_time"
    usbc_3_end_time: str = "usbc_3_end_time"
    usbc_4_end_time: str = "usbc_4_end_time"
    usba_end_time: str = "usba_end_time"
    soc_limits: str = "soc_limits"
    backup_soc: str = "backup_soc"
    pps_usage_mode: str = "pps_usage_mode"
    pps_tou_schedule: str = "tou_schedule"
    pps_custom_schedule: str = "pps_custom_schedule"
    pps_output_schedule: str = "pps_output_schedule"
    silent_schedule: str = "silent_schedule"
    sb_status_check: str = "sb_status_check"
    sb_power_cutoff_select: str = "sb_power_cutoff_select"
    sb_min_soc_select: str = "sb_min_soc_select"  # Old command: Does not change App station wide setting, needs Api request as well
    sb_soc_limits: str = "sb_soc_limits"  # New command: Does not change App station wide setting, needs Api request as well
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
    device_switch: str = "device_switch"
    device_power_mode: str = "device_power_mode"
    plug_lock_switch: str = "plug_lock_switch"
    ev_charger_mode_select: str = "ev_charger_mode_select"
    ev_auto_start_switch: str = "ev_auto_start_switch"
    ev_auto_charge_restart_switch: str = "ev_auto_charge_restart_switch"
    smart_touch_mode_select: str = "smart_touch_mode_select"
    swipe_up_mode_select: str = "swipe_up_mode_select"
    swipe_down_mode_select: str = "swipe_down_mode_select"
    ev_charger_schedule_times: str = "ev_charger_schedule_times"
    ev_charger_schedule_settings: str = "ev_charger_schedule_settings"
    ev_max_charge_current: str = "ev_max_charge_current"
    ev_random_delay_switch: str = "ev_random_delay_switch"
    modbus_switch: str = "modbus_switch"
    light_brightness: str = "light_brightness"
    light_off_schedule: str = (
        "light_off_schedule"  # complex command with switch and schedule
    )
    main_breaker_limit: str = "main_breaker_limit"
    ev_load_balancing: str = (
        "ev_load_balancing"  # complex command with switches and schedule
    )
    ev_solar_charging: str = "ev_solar_charging"  # complex command with switches
    ac_dc_mode_select: str = "ac_dc_mode_select"
    charger_mode_select: str = "charger_mode_select"
    car_battery_type: str = "car_battery_type"
    battery_charge_limits: str = "battery_charge_limits"
    reverse_charge_limits: str = "reverse_charge_limits"
    charger_usage_mode: str = "charger_usage_mode"
    charger_custom_usage_mode: str = "charger_custom_usage_mode"
    port_priority: str = "port_priority"
    knob_mode_select: str = "knob_mode_select"
    clock_mode_select: str = "clock_mode_select"
    clock_display_schedule: str = "clock_display_schedule"
    clock_holiday_switch: str = "clock_holiday_switch"
    charger_theme: str = "charger_theme"
    charger_theme_custom: str = "charger_theme_custom"
    circuit_priority: str = "circuit_priority"
    backup_charge_plan: str = "backup_charge_plan"
    backup_charge_storm_guard: str = "backup_charge_storm_guard"
    backup_charge_timestamps: str = "backup_charge_timestamps"
    tbd_switch: str = "tbd_switch"

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

TIMESTAMP_FE_NOTYPE = {
    # classical format using 4 bytes for timestamp value in sec
    # however, no field type byte is used
    "fe": {
        NAME: "msg_timestamp",
        TYPE: DeviceHexDataTypes.unk.value,
    },
}

TIME_SILE = {
    # Time format in 2 byte value min:hour
    # 00:00 - 23:59, step 1 min, encoded as hour * 256 + minute
    TYPE: DeviceHexDataTypes.sile.value,
    VALUE_MIN: 0,
    VALUE_MAX: 5947,
    VALUE_STEP: 1,
}

TIME_VAR = {
    # Time format in 3 byte value sec:min:hour
    # 00:00:00 - 23:59:59, step 1 sec, encoded as hour * 256 * 256 + minute * 256 + second
    TYPE: DeviceHexDataTypes.var.value,
    LENGTH: 3,
    VALUE_MIN: 0,
    VALUE_MAX: 1522491,
    VALUE_STEP: 1,
}

CMD_HEADER = {
    # Common command pattern without timestamp
    TOPIC: "req",
    "a1": {NAME: "pattern_22"},  # Bytes composed automatically based on name and field
}

# Common command pattern seen in most of the commands
CMD_COMMON = CMD_HEADER | TIMESTAMP_FE

# Common command pattern V2 seen in most of the commands for newer devices with timestamp in ms
CMD_COMMON_V2 = CMD_HEADER | TIMESTAMP_FD


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
        VALUE_MIN: 30,  # real limit is unknown
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

CMD_TEMP_UNIT_V2 = CMD_COMMON_V2 | {
    # Command: Set temperature unit
    COMMAND_NAME: SolixMqttCommands.temp_unit_switch,
    "a5": {
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
        STATE_NAME: "ac_fast_charge_switch",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
}

CMD_AC_OUTPUT_MODE = CMD_COMMON | {
    # Command: PPS AC output mode setting
    COMMAND_NAME: SolixMqttCommands.ac_output_mode_select,
    "a2": {
        NAME: "set_ac_output_mode",  # Normal (0), Smart (1)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "ac_output_mode",
        STATE_CONVERTER: lambda value, state, _: (
            {1: 2, 0: 1}.get(value, 1)  # switch to state conversion for mocked state
            if value is not None
            else state  # do not convert state, since that is the provided switch value
        ),  # Convert value back for mocked state: Normal state (1), Smart state (2)
        VALUE_OPTIONS: {"smart": 1, "normal": 0},
    },
}

CMD_AC_OUTPUT_MODE_INV = CMD_COMMON | {
    # Command: PPS AC output mode setting
    COMMAND_NAME: SolixMqttCommands.ac_output_mode_select,
    "a2": {
        NAME: "set_ac_output_mode",  # Normal (1), Smart (0)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "ac_output_mode",
        STATE_CONVERTER: lambda value, state, _: (
            {0: 2, 1: 1}.get(value, 1)  # switch to state conversion for mocked state
            if value is not None
            else state  # do not convert state, since that is the provided switch value
        ),  # Convert value back for mocked state: Normal state (1), Smart state (2)
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
        NAME: "set_dc_12v_output_mode",  # Normal (0), Smart (1)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "dc_12v_output_mode",
        STATE_CONVERTER: lambda value, state, _: (
            {1: 2, 0: 1}.get(value, 1)  # switch to state conversion for mocked state
            if value is not None
            else state
        ),  # Convert value back for mocked state: Normal state (1), Smart state (2)
        VALUE_OPTIONS: {"smart": 1, "normal": 0},
    },
}

CMD_DC_12V_OUTPUT_MODE_INV = CMD_COMMON | {
    # Command: PPS 12V DC output mode setting inverted
    COMMAND_NAME: SolixMqttCommands.dc_12v_output_mode_select,
    "a2": {
        NAME: "set_dc_12v_output_mode",  # Normal (1), Smart (0)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "dc_12v_output_mode",
        STATE_CONVERTER: lambda value, state, _: (
            {0: 2, 1: 1}.get(value, 1)  # switch to state conversion for mocked state
            if value is not None
            else state
        ),  # Convert value back for mocked state: Normal state (1), Smart state (2)
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

CMD_ENERGY_SAVING_SWITCH = CMD_COMMON | {
    # Command: PPS energy/power saving mode setting
    COMMAND_NAME: SolixMqttCommands.energy_saving_switch,
    "a2": {
        NAME: "set_energy_saving_switch",  # Disable (0) | Enable (1)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "energy_saving_switch",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
}

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

CMD_USB_PORT_SWITCH = {
    port: CMD_COMMON
    | {
        # Command: Charger USB port switch setting
        # COMMAND_NAME: Must be added depending on which port is to be selected,
        "a2": {
            NAME: "set_port_switch_select",
            TYPE: DeviceHexDataTypes.ui.value,
            VALUE_OPTIONS: {
                "usbc_1": 0,
                "usbc_2": 1,
                "usbc_3": 2,
                "usbc_4": 3,
                "usba": 4,
            },
            VALUE_DEFAULT: idx,  # same pattern but different default option for port
        },
        "a3": {
            NAME: "set_port_switch",
            TYPE: DeviceHexDataTypes.ui.value,
            VALUE_OPTIONS: {"off": 0, "on": 1},
            STATE_NAME: f"{port}_switch",
        },
    }
    for idx, port in enumerate(["usbc_1", "usbc_2", "usbc_3", "usbc_4", "usba"])
}

CMD_AC_PORT_SWITCH = CMD_COMMON | {
    # Command: Charger AC port switch setting
    # COMMAND_NAME: Must be added depending on which port is to be switched,
    "a2": {
        NAME: "set_ac_port_switch_select",
        TYPE: DeviceHexDataTypes.ui.value,
        VALUE_OPTIONS: {
            "ac_1_switch": 0,
            "ac_2_switch": 1,
        },
    },
    "a3": {
        NAME: "set_ac_port_switch",
        TYPE: DeviceHexDataTypes.ui.value,
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

CMD_DEVICE_SWITCH = CMD_COMMON_V2 | {
    # Command: device power switch
    COMMAND_NAME: SolixMqttCommands.device_switch,
    "ac": {
        NAME: "set_device_switch",
        STATE_NAME: "device_switch",
        TYPE: DeviceHexDataTypes.ui.value,
        VALUE_OPTIONS: {"off": 0, "on": 1},
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
            LENGTH: 16,
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
    # Command: Solarbank Set SOC reserve for power cutoff
    COMMAND_NAME: SolixMqttCommands.sb_min_soc_select,
    "a2": {
        NAME: "set_min_soc",  # 5 or 10 %
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "power_cutoff",
        VALUE_OPTIONS: [5, 10],
    },
}

CMD_SB_SOC_LIMITS = CMD_COMMON | {
    # Command: Solarbank Set new SOC limits
    COMMAND_NAME: SolixMqttCommands.sb_soc_limits,
    "a2": {
        NAME: "set_min_soc",
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "power_cutoff",
        VALUE_MIN: 5,  # 5 % for SB2, 1 %  for SB3
        VALUE_MAX: 20,
        VALUE_STATE: "power_cutoff",
    },
    "a5": {
        NAME: "set_max_soc",
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "max_soc",
        VALUE_MIN: 80,
        VALUE_MAX: 100,
        VALUE_STATE: "max_soc",
    },
    "a6": {
        NAME: "set_backup_soc",
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "backup_soc",
        VALUE_MIN: 0,
        VALUE_MAX: 100,
        VALUE_MIN_STATE: "power_cutoff",
        VALUE_MAX_STATE: "max_soc",
        VALUE_FOLLOWS: "backup_soc",
        STATE_CONVERTER: lambda value, state, cache: (
            value
            if value is not None
            # ensure backup is min + 1 < backup < max -1
            else min(
                int(cache.get("set_max_soc", cache.get("max_soc") or 1)) - 1,
                max(
                    int(cache.get("set_min_soc", cache.get("power_cutoff") or -1)) + 1,
                    # int(cache.get("backup_soc") or 0),
                    state,
                ),
            )
            if state is not None
            else int(cache.get("backup_soc") or 0)
            # if cache.get("backup_soc") and state is None
            # else 0
            # if state is None
            # else state
        ),
    },
    "a7": {
        NAME: "set_backup_soc_switch",
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "backup_soc_switch",
        VALUE_OPTIONS: {"off": 0, "on": 1},
        VALUE_STATE: "backup_soc_switch",
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
    # Command: Solarbank Set max photovoltaic input limit (MPPT limit)
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
            SIGNED: False,
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
            SIGNED: False,
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
            NAME: "set_plug_schedule_action",  # 0=delete, 1=create, 2=modify
            TYPE: DeviceHexDataTypes.ui.value,
            VALUE_OPTIONS: {"delete": 0, "create": 1, "modify": 2},
        },
        "a3": {
            NAME: "set_plug_schedule_slot",  # schedule slot index, 1-x
            TYPE: DeviceHexDataTypes.ui.value,
            VALUE_MIN: 1,
            VALUE_MAX: 10,
        },
        "a4": {
            NAME: "set_plug_schedule_enabled",  # 0=disabled, 1=enabled
            TYPE: DeviceHexDataTypes.ui.value,
            VALUE_DEFAULT: 1,
        },
        "a5": TIME_SILE
        | {
            NAME: "set_plug_schedule_time",  # min:hour as byte pair
        },
        "a6": {
            NAME: "set_plug_schedule_switch",  # Off (0), On (1)
            TYPE: DeviceHexDataTypes.ui.value,
            VALUE_OPTIONS: {"off": 0, "on": 1},
        },
        "a7": {
            NAME: "set_plug_schedule_weekdays",  # weekday selection as day numbers (1=Mon..7=Sun), length 1-7 (one byte per day)
            TYPE: DeviceHexDataTypes.bin.value,
            VALUE_OPTIONS: {
                "monday": 1,
                "tuesday": 2,
                "wednesday": 3,
                "thursday": 4,
                "friday": 5,
                "saturday": 6,
                "sunday": 7,
            },
        },
    }
)

CMD_PLUG_DELAYED_TOGGLE = (
    CMD_COMMON
    | {
        # Command: Smartplug delayed toggle
        COMMAND_NAME: SolixMqttCommands.plug_delayed_toggle,
        "a2": {
            NAME: "set_toggle_timer_mode",  # Off (0), Start (1), Pausews (2), Running (3)
            TYPE: DeviceHexDataTypes.ui.value,
            STATE_NAME: "toggle_timer_mode",
            VALUE_OPTIONS: {"off": 0, "start": 1, "paused": 2, "running": 3},
            VALUE_STATE: "toggle_timer_mode",
        },
        "a3": {
            TYPE: DeviceHexDataTypes.bin.value,
            LENGTH: 3,
            BYTES: {
                "00": TIME_VAR
                | {
                    NAME: "set_toggle_to_delay_time",  # 3 bytes: Seconds:Minutes:Hours
                    STATE_NAME: "toggle_to_delay_time",
                    VALUE_DEFAULT: 0,
                    VALUE_STATE: "toggle_to_delay_time",
                },
            },
        },
        "a4": {
            NAME: "set_toggle_to_switch",  # State the switch will be toggled to: Off (0), On (1)
            TYPE: DeviceHexDataTypes.ui.value,
            VALUE_OPTIONS: {"off": 0, "on": 1},
            VALUE_STATE: "toggle_to_switch",
            STATE_CONVERTER: lambda value, state, cache: (
                value
                if value is not None
                else cache.get(
                    "set_toggle_to_switch",
                    cache.get(
                        "toggle_to_switch", int(not cache.get("ac_output_power_switch"))
                    ),  # default to toggle state of actual switch
                )
                if state is None
                else state
            ),
        },
        "a5": {
            TYPE: DeviceHexDataTypes.bin.value,
            LENGTH: 3,
            BYTES: {
                "00": TIME_VAR
                | {
                    NAME: "set_toggle_to_elapsed_time",  # 3 bytes: Seconds:Minutes:Hours
                    STATE_NAME: "toggle_to_elapsed_time",
                    VALUE_STATE: "toggle_to_elapsed_time",
                    STATE_CONVERTER: lambda value, state, cache: (
                        "00:00:00"
                        if cache.get(
                            "set_toggle_timer_mode",
                            cache.get("toggle_timer_mode"),
                        )
                        in [0, 1]
                        and state is None  # reset elapsed time for stop or start
                        else value
                        if value is not None
                        else (state or 0)
                    ),
                },
            },
        },
    }
)

CMD_EV_CHARGER_MODE = (
    CMD_COMMON
    | {
        # Command: EV Charger mode selection
        COMMAND_NAME: SolixMqttCommands.ev_charger_mode_select,
        COMMAND_ENCODING: 2,  # encoding_type 2 seems to be required for this command message
        # Charger Status: Standby(0), Preparing(1), Charging(2), Charger_Paused(3), Vehicle_Paused(4), Completed (5), Reserving(6), Disabled(7), Error(8)
        "a2": {
            NAME: "set_ev_charger_mode",  # Start(1), Stop(2), Skip Delay (3), Boost(4)
            TYPE: DeviceHexDataTypes.ui.value,
            VALUE_OPTIONS: {
                "start_charge": 1,
                "stop_charge": 2,
                "skip_delay": 3,
                "boost_charge": 4,
            },
            # Convert value back for mocked and different value state:
            # Standby(0), Preparing(1), Charging(2), Charger_Paused(3), Vehicle_Paused(4), Completed (5), Reserving(6), Disabled(7), Error(8)
            STATE_NAME: "ev_charger_status",
            STATE_CONVERTER: lambda value, state, _: (
                {1: 2, 2: 0, 3: 2, 4: 2}.get(
                    value, 0
                )  # switch to state conversion for mocked state. Boost uses different name and cannot be mocked
                if value is not None
                else state  # do not convert state, since that is the provided command value
            ),
        },
    }
)

CMD_DEVICE_POWER_MODE = CMD_COMMON | {
    # Command: EV Charger device power mode
    COMMAND_NAME: SolixMqttCommands.device_power_mode,
    COMMAND_ENCODING: 2,  # encoding_type 2 may be required for this command message
    "a2": {
        NAME: "set_device_power_mode",  # Restart(5)
        TYPE: DeviceHexDataTypes.ui.value,
        VALUE_OPTIONS: {"restart": 5},
        VALUE_DEFAULT: 5,
    },
}

CMD_PLUG_LOCK_SWITCH = CMD_COMMON | {
    # Command: EV Charger plug lock switch setting
    COMMAND_NAME: SolixMqttCommands.plug_lock_switch,
    "a3": {
        NAME: "set_plug_lock_switch",  # On (1), Off (2) !
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "plug_lock_switch",
        VALUE_OPTIONS: {"on": 1, "off": 2},
    },
}

CMD_EV_AUTO_START_SWITCH = CMD_COMMON | {
    # Command: EV Auto start switch setting
    COMMAND_NAME: SolixMqttCommands.ev_auto_start_switch,
    "a4": {
        NAME: "set_auto_start_switch",  # Off (0), On (1)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "auto_start_switch",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
}

CMD_EV_MAX_CHARGE_CURRENT = CMD_COMMON | {
    # Command: EV charger maximum current for charging
    COMMAND_NAME: SolixMqttCommands.ev_max_charge_current,
    "a8": {
        NAME: "set_max_evcharge_current",  # 6 - rated limit (32 A), step 1 A
        TYPE: DeviceHexDataTypes.sile.value,
        STATE_NAME: "max_evcharge_current",
        VALUE_MIN: 6,
        VALUE_MIN_STATE: "min_current_limit",
        VALUE_MAX: 16,
        VALUE_MAX_STATE: "max_current_limit",
        VALUE_STEP: 1,
        VALUE_DIVIDER: 0.1,
    },
}

CMD_EV_LIGHT_BRIGHTNESS = CMD_COMMON | {
    # Command: EV charger light brightness setting
    COMMAND_NAME: SolixMqttCommands.light_brightness,
    "aa": {
        NAME: "set_light_brightness",  # 0-100 %, step 10 %
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "light_brightness",
        VALUE_MIN: 0,
        VALUE_MAX: 100,
        VALUE_STEP: 10,
    },
}

CMD_EV_LIGHT_OFF_SCHEDULE = (
    CMD_COMMON
    | {
        COMMAND_NAME: SolixMqttCommands.light_off_schedule,
        "b4": {
            NAME: "set_light_off_schedule_switch",  # Off (0), On (1)
            TYPE: DeviceHexDataTypes.ui.value,
            STATE_NAME: "light_off_schedule_switch",
            VALUE_OPTIONS: {"off": 0, "on": 1},
            VALUE_STATE: "light_off_schedule_switch",
        },
        "b5": TIME_SILE
        | {
            NAME: "set_light_off_start_time",  # 00:00 - 23:59, step 1 min, encoded as hour * 256 + minute
            STATE_NAME: "light_off_start_time",
            VALUE_STATE: "light_off_start_time",
        },
        "b6": TIME_SILE
        | {
            NAME: "set_light_off_end_time",  # 00:00 - 23:59, step 1 min, encoded as hour * 256 + minute
            STATE_NAME: "light_off_end_time",
            VALUE_STATE: "light_off_end_time",
        },
    }
)

CMD_EV_AUTO_CHARGE_RESTART_SWITCH = CMD_COMMON | {
    # Command: EV Auto charge restart switch setting
    COMMAND_NAME: SolixMqttCommands.ev_auto_charge_restart_switch,
    "ac": {
        NAME: "set_auto_charge_restart_switch",  # Off (0), On (1)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "auto_charge_restart_switch",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
}

CMD_EV_CHARGE_RANDOM_DELAY_SWITCH = CMD_COMMON | {
    # Command: EV charge random delay switch setting
    COMMAND_NAME: SolixMqttCommands.ev_random_delay_switch,
    "ad": {
        NAME: "set_random_delay_switch",  # Off (0), On (1)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "random_delay_switch",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
}

CMD_SWIPE_UP_MODE = (
    CMD_COMMON
    | {
        COMMAND_NAME: SolixMqttCommands.swipe_up_mode_select,
        "af": {
            NAME: "set_wipe_up_mode_select",  # off (0), start charge (1), stop charge (2), boost charge (3)
            TYPE: DeviceHexDataTypes.ui.value,
            STATE_NAME: "wipe_up_mode",
            VALUE_OPTIONS: {
                "off": 0,
                "start_charge": 1,
                "stop_charge": 2,
                "boost_charge": 3,
            },
        },
    }
)

CMD_SWIPE_DOWN_MODE = (
    CMD_COMMON
    | {
        COMMAND_NAME: SolixMqttCommands.swipe_down_mode_select,
        "b0": {
            NAME: "set_wipe_down_mode_select",  # off (0), start charge (1), stop charge (2), boost charge (3)
            TYPE: DeviceHexDataTypes.ui.value,
            STATE_NAME: "wipe_down_mode",
            VALUE_OPTIONS: {
                "off": 0,
                "start_charge": 1,
                "stop_charge": 2,
                "boost_charge": 3,
            },
        },
    }
)

CMD_SMART_TOUCH_MODE = CMD_COMMON | {
    COMMAND_NAME: SolixMqttCommands.smart_touch_mode_select,
    "b2": {
        NAME: "set_smart_touch_mode_select",  # simple (0), avoid_error (1)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "smart_touch_mode",
        VALUE_OPTIONS: {"simple": 0, "anti_mistouch": 1},
    },
}

CMD_MODBUS_SWITCH = CMD_COMMON | {
    # Command: EV Charger modbus switch setting
    COMMAND_NAME: SolixMqttCommands.modbus_switch,
    "b7": {
        NAME: "set_modbus_switch",  # Off (0), On (1)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "modbus_switch",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
}

CMD_MAIN_BREAKER_LIMIT = CMD_COMMON | {
    # Command: Main breaker limit for EV charger load balancing
    COMMAND_NAME: SolixMqttCommands.main_breaker_limit,
    "a3": {
        NAME: "set_main_breaker_limit",  # 10-500 A, step 1 A
        TYPE: DeviceHexDataTypes.sile.value,
        STATE_NAME: "main_breaker_limit",
        VALUE_MIN: 10,
        VALUE_MAX: 500,
        VALUE_STEP: 1,
    },
}

CMD_EV_LOAD_BALANCING = CMD_COMMON | {
    # Command: EV Charger load balancing settings
    COMMAND_NAME: SolixMqttCommands.ev_load_balancing,
    "a2": {
        NAME: "set_load_balance_switch",  # Off (0), On (1)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "load_balance_switch",
        VALUE_STATE: "load_balance_switch",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
    "a4": {
        NAME: "set_load_balance_setting_d5",  # Off (0), On (1)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "load_balance_setting_d5",
        VALUE_STATE: "load_balance_setting_d5",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
    "a5": {
        NAME: "set_load_balance_setting_d6",  # Off (0), On (1)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "load_balance_setting_d6",
        VALUE_STATE: "load_balance_setting_d6",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
    "a6": {
        NAME: "set_load_balance_monitor_device",  # device SN
        TYPE: DeviceHexDataTypes.str.value,
        LENGTH: 16,
        STATE_NAME: "load_balance_monitor_device",
        VALUE_STATE: "load_balance_monitor_device",
    },
}

CMD_EV_SOLAR_CHARGING = (
    CMD_COMMON
    | {
        # Command: EV Charger solar charge settings
        COMMAND_NAME: SolixMqttCommands.ev_solar_charging,
        "a2": {
            NAME: "set_solar_evcharge_switch",  # Off (0), On (1)
            TYPE: DeviceHexDataTypes.ui.value,
            STATE_NAME: "solar_evcharge_switch",
            VALUE_STATE: "solar_evcharge_switch",
            VALUE_OPTIONS: {"off": 0, "on": 1},
        },
        "a3": {
            NAME: "set_solar_evcharge_mode",  # solar & grid (0), solar only (1)
            TYPE: DeviceHexDataTypes.ui.value,
            STATE_NAME: "solar_evcharge_mode",
            VALUE_STATE: "solar_evcharge_mode",
            VALUE_OPTIONS: {"solar_grid": 0, "solar_only": 1},
        },
        "a4": {
            NAME: "set_solar_evcharge_min_current",  # 6 - rated limit (32 A), step 1 A
            TYPE: DeviceHexDataTypes.sile.value,
            STATE_NAME: "solar_evcharge_min_current",
            VALUE_STATE: "solar_evcharge_min_current",
            VALUE_MIN: 6,
            VALUE_MIN_STATE: "min_current_limit",
            VALUE_MAX: 16,
            VALUE_MAX_STATE: "max_current_limit",
            VALUE_STEP: 1,
        },
        "a5": {
            NAME: "set_phase_operating_mode?",  # auto (0) / one phase(1) / 3 phase(3)- not seen yet ?
            TYPE: DeviceHexDataTypes.ui.value,
            STATE_NAME: "phase_operating_mode",
            VALUE_STATE: "phase_operating_mode",
            VALUE_OPTIONS: {"automatic": 0, "one_phase": 1},
        },
        "a6": {
            NAME: "set_solar_evcharge_monitoring_mode",
            TYPE: DeviceHexDataTypes.ui.value,
            STATE_NAME: "solar_evcharge_monitoring_mode",
            VALUE_STATE: "solar_evcharge_monitoring_mode",
            VALUE_OPTIONS: {"off": 0, "on": 1},
        },
        "a7": {
            NAME: "set_auto_phase_switch",  # Off (0), On (1)
            TYPE: DeviceHexDataTypes.ui.value,
            STATE_NAME: "auto_phase_switch",
            VALUE_STATE: "auto_phase_switch",
            VALUE_OPTIONS: {"off": 0, "on": 1},
        },
        "a8": {
            NAME: "set_solar_evcharge_monitor_device",  # device SN
            TYPE: DeviceHexDataTypes.str.value,
            LENGTH: 16,
            STATE_NAME: "solar_evcharge_monitor_device",
            VALUE_STATE: "solar_evcharge_monitor_device",
        },
    }
)

CMD_EV_CHARGER_SCHEDULE_SETTINGS = CMD_COMMON | {
    COMMAND_NAME: SolixMqttCommands.ev_charger_schedule_settings,
    "a2": {
        NAME: "set_schedule_switch",  # on (1), off (2) !!!
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "schedule_switch",
        VALUE_STATE: "schedule_switch",
        VALUE_OPTIONS: {"on": 1, "off": 2},
    },
    "a8": {
        NAME: "set_schedule_mode",  # normal (0), smart (1)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "schedule_mode",
        VALUE_STATE: "schedule_mode",
        VALUE_OPTIONS: {"normal": 0, "smart": 1},
    },
}

CMD_EV_CHARGER_SCHEDULE_TIMES = (
    CMD_COMMON
    | {
        COMMAND_NAME: SolixMqttCommands.ev_charger_schedule_times,
        "a3": TIME_SILE
        | {
            NAME: "set_week_start_time",  # 00:00 - 23:59, step 1 min, encoded as hour * 256 + minute
            STATE_NAME: "week_start_time",
            VALUE_STATE: "week_start_time",
        },
        "a4": TIME_SILE
        | {
            NAME: "set_week_end_time",  # 00:00 - 23:59, step 1 min, encoded as hour * 256 + minute
            STATE_NAME: "week_end_time",
            VALUE_STATE: "week_end_time",
        },
        "a5": TIME_SILE
        | {
            NAME: "set_weekend_start_time",  # 00:00 - 23:59, step 1 min, encoded as hour * 256 + minute
            STATE_NAME: "weekend_start_time",
            VALUE_STATE: "weekend_start_time",
        },
        "a6": TIME_SILE
        | {
            NAME: "set_weekend_end_time",  # 00:00 - 23:59, step 1 min, encoded as hour * 256 + minute
            STATE_NAME: "weekend_end_time",
            VALUE_STATE: "weekend_end_time",
        },
        "a7": {
            NAME: "set_weekend_mode",  # same (1), different (2)
            TYPE: DeviceHexDataTypes.ui.value,
            STATE_NAME: "weekend_mode",
            VALUE_STATE: "weekend_mode",
            VALUE_OPTIONS: {"same": 1, "different": 2},
        },
    }
)

CMD_AC_DC_MODE = CMD_COMMON | {
    # Command: EV charger light brightness setting
    COMMAND_NAME: SolixMqttCommands.ac_dc_mode_select,
    "a5": {
        NAME: "set_ac_dc_mode",
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "ac_dc_mode",
        VALUE_OPTIONS: {"dc": 1, "ac": 3},
    },
}

CMD_BATTERY_CHARGE_LIMITS = (
    CMD_COMMON_V2
    | {
        # Command: Alternator charger charging limits
        COMMAND_NAME: SolixMqttCommands.battery_charge_limits,
        "a5": {
            NAME: "set_charge_power_limit",  # 300-800 W, step 100W
            TYPE: DeviceHexDataTypes.sile.value,
            STATE_NAME: "charge_power_limit",
            VALUE_MIN: 500,
            VALUE_MIN_STATE: "charge_power_limit_min",
            VALUE_MAX: 800,
            VALUE_MAX_STATE: "charge_power_limit_max",
            VALUE_STEP: 100,
            VALUE_STATE: "charge_power_limit",
        },
        "b4": {
            NAME: "set_charge_voltage_limit",  # 12.0V to 13.8V in 0.1V step, depends on set type?
            TYPE: DeviceHexDataTypes.sile.value,
            STATE_NAME: "charge_voltage_limit",
            VALUE_MIN: 12.0,
            VALUE_MIN_STATE: "charge_voltage_limit_min",
            VALUE_MAX: 13.8,
            VALUE_MAX_STATE: "charge_voltage_limit_max",
            VALUE_STEP: 0.1,
            VALUE_DIVIDER: 0.1,
            VALUE_STATE: "charge_voltage_limit",
        },
    }
)

CMD_REVERSE_CHARGE_LIMITS = (
    CMD_COMMON_V2
    | {
        # Command: Alternator charger reverse charging limits
        COMMAND_NAME: SolixMqttCommands.reverse_charge_limits,
        "a6": {
            NAME: "set_reverse_power_limit",  # 100-800 W, step 100 W
            TYPE: DeviceHexDataTypes.sile.value,
            STATE_NAME: "reverse_power_limit",
            VALUE_MIN: 500,
            VALUE_MIN_STATE: "reverse_power_limit_min",
            VALUE_MAX: 800,
            VALUE_MAX_STATE: "reverse_power_limit_max",
            VALUE_STEP: 100,
            VALUE_STATE: "reverse_power_limit",
        },
        "b4": {
            NAME: "set_charge_voltage_limit",  # 12.0V to 13.8V in 0.1V step, depends on set type?
            TYPE: DeviceHexDataTypes.sile.value,
            STATE_NAME: "charge_voltage_limit",
            VALUE_MIN: 12.0,
            VALUE_MIN_STATE: "charge_voltage_limit_min",
            VALUE_MAX: 13.8,
            VALUE_MAX_STATE: "charge_voltage_limit_max",
            VALUE_STEP: 0.1,
            VALUE_DIVIDER: 0.1,
            VALUE_STATE: "charge_voltage_limit",
        },
    }
)

CMD_CAR_BATTERY_TYPE = CMD_COMMON_V2 | {
    # Command: Alternator charger battery type
    COMMAND_NAME: SolixMqttCommands.car_battery_type,
    "a3": {
        NAME: "set_car_battery_type",  # LiFePO4 (0), Lead Acid (1)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "car_battery_type",
        VALUE_OPTIONS: {"li_fe_po": 0, "lead_acid": 1},
        VALUE_STATE: "car_battery_type",
    },
    "aa": {
        NAME: "set_car_battery_voltage_type",  # 12V (0), 24V (1)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "car_battery_voltage_type",
        VALUE_OPTIONS: {"12_v": 0, "24_v": 1},
        VALUE_STATE: "car_battery_voltage_type",
    },
}

CMD_DISPLAY_BRIGHTNESS = CMD_COMMON | {
    # Command: Set display brightness 20-100 %, step 5 %
    COMMAND_NAME: SolixMqttCommands.display_brightness,
    "a2": {
        NAME: "set_display_brightness",
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "display_brightness",
        VALUE_MIN: 20,
        VALUE_MAX: 100,
        VALUE_STEP: 5,
    },
}

CMD_CHARGER_USAGE_MODE = CMD_COMMON | {
    # Command: Set charger mode: 1 (AI Power mode), 2 (Connection Prio), 3 (Dual Laptop mode), 4 (Low power mode), 5 (Custom)
    COMMAND_NAME: SolixMqttCommands.charger_usage_mode,
    "a2": {
        NAME: "set_usage_mode",
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "usage_mode",
        VALUE_OPTIONS: {
            "ai_power": 1,
            "port_priority": 2,
            "dual_laptop": 3,
            "low_power": 4,
        },
    },
}

CMD_CHARGER_CUSTOM_USAGE_MODE = CMD_CHARGER_USAGE_MODE | {
    # Command: Set charger custom usage mode: 5 with additional port settings
    COMMAND_NAME: SolixMqttCommands.charger_custom_usage_mode,
    "a2": {
        NAME: "set_usage_mode",
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "usage_mode",
        VALUE_OPTIONS: {"custom": 5},
        VALUE_DEFAULT: 5,
    },
    "a3": {
        TYPE: DeviceHexDataTypes.bin.value,
        # Byte pattern: profile_number:auto_exit:c1_pwr:c2_pwr:c3_pwr:c4_pwr:a_pwr
        # Example: 02:01:1e:1c:2c:35:18
        LENGTH: 7,
        BYTES: {
            "00": {
                NAME: "set_custom_profile_number",
                TYPE: DeviceHexDataTypes.ui.value,
                VALUE_MIN: 0,
                VALUE_MAX: 255,
                STATE_NAME: "custom_profile_number",
            },
            "01": {
                NAME: "set_auto_exit_switch",
                TYPE: DeviceHexDataTypes.ui.value,
                VALUE_OPTIONS: {"on": 1, "off": 0},
                STATE_NAME: "auto_exit_switch",
            },
            "02": {
                NAME: "set_usb_c1_power_limit",
                TYPE: DeviceHexDataTypes.ui.value,
                VALUE_MIN: 0,
                VALUE_MAX: 140,
                VALUE_DEFAULT: 0,
                STATE_NAME: "custom_usb_c1_power_limit",
            },
            "03": {
                NAME: "set_usb_c2_power_limit",
                TYPE: DeviceHexDataTypes.ui.value,
                VALUE_MIN: 0,
                VALUE_MAX: 100,
                VALUE_DEFAULT: 0,
                STATE_NAME: "custom_usb_c2_power_limit",
            },
            "04": {
                NAME: "set_usb_c3_power_limit",
                TYPE: DeviceHexDataTypes.ui.value,
                VALUE_MIN: 0,
                VALUE_MAX: 100,
                VALUE_DEFAULT: 0,
                STATE_NAME: "custom_usb_c3_power_limit",
            },
            "05": {
                NAME: "set_usb_c4_power_limit",
                TYPE: DeviceHexDataTypes.ui.value,
                VALUE_MIN: 0,
                VALUE_MAX: 100,
                VALUE_DEFAULT: 0,
                STATE_NAME: "custom_usb_c4_power_limit",
            },
            "06": {
                NAME: "set_usb_a_power_limit",
                TYPE: DeviceHexDataTypes.ui.value,
                VALUE_MIN: 0,
                VALUE_MAX: 24,
                VALUE_DEFAULT: 0,
                STATE_NAME: "custom_usb_a_power_limit",
            },
        },
    },
    "a4": {
        TYPE: DeviceHexDataTypes.bin.value,
        # USB-C Port protocols, 3 bytes each port
        # Protocol bitmask: xiaomi:huawei:pps20v:pps16v:pps11v:pd12v:ufcs:scp
        # Example: 08:00:00:0b:00:00:0b:00:00:02:00:00
        LENGTH: 12,
        BYTES: {
            f"{0 + idx * 3:02d}": {
                NAME: f"set_usb_{port}_protocols",
                TYPE: DeviceHexDataTypes.bin.value,
                LENGTH: 1,
                STATE_NAME: f"custom_usb_{port}_protocols",
                STATE_CONVERTER: lambda value, state, cache: (
                    convert_port_protocols(value)
                    if value is not None
                    else convert_port_protocols(state)
                ),
            }
            for idx, port in enumerate(["c1", "c2", "c3", "c4"])
        },
    },
}


CMD_CHARGER_CLOCK_MODE = CMD_COMMON | {
    # Command: Set charger clock mode: 0 (12h), 1 (24h)
    COMMAND_NAME: SolixMqttCommands.clock_mode_select,
    "a2": {
        NAME: "set_clock_mode",
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "clock_mode",
        VALUE_OPTIONS: {
            "12h": 0,
            "24h": 1,
        },
    },
}

CMD_CHARGER_CLOCK_DISPLAY = (
    CMD_COMMON
    | {
        # Command: Charger clock display schedule
        COMMAND_NAME: SolixMqttCommands.clock_display_schedule,
        "a2": {
            TYPE: DeviceHexDataTypes.bin.value,
            LENGTH: 5,
            BYTES: {
                "00": {
                    NAME: "set_clock_display_start_hour",  # hour
                    TYPE: DeviceHexDataTypes.ui.value,
                    VALUE_MIN: 0,
                    VALUE_MAX: 23,
                    STATE_NAME: "clock_display_start_hour",
                    VALUE_STATE: "clock_display_start_hour",
                },
                "01": {
                    NAME: "set_clock_display_start_minute",  # min
                    TYPE: DeviceHexDataTypes.ui.value,
                    VALUE_MIN: 0,
                    VALUE_MAX: 59,
                    STATE_NAME: "clock_display_start_minute",
                    VALUE_STATE: "clock_display_start_minute",
                },
                "02": {
                    NAME: "set_clock_display_end_hour",  # hour
                    TYPE: DeviceHexDataTypes.ui.value,
                    VALUE_MIN: 0,
                    VALUE_MAX: 23,
                    STATE_NAME: "clock_display_end_hour",
                    VALUE_STATE: "clock_display_end_hour",
                },
                "03": {
                    NAME: "set_clock_display_end_minute",  # min
                    TYPE: DeviceHexDataTypes.ui.value,
                    VALUE_MIN: 0,
                    VALUE_MAX: 59,
                    STATE_NAME: "clock_display_end_minute",
                    VALUE_STATE: "clock_display_end_minute",
                },
                "04": {
                    NAME: "set_clock_display_weekdays",  # Bitmask: 0:sun:sat:fri:thu:wed:tue:mon
                    TYPE: DeviceHexDataTypes.bin.value,
                    LENGTH: 1,
                    STATE_CONVERTER: lambda value, state, cache: (
                        convert_weekdays(value)
                        if value is not None
                        else convert_weekdays(state)
                    ),
                    STATE_NAME: "clock_display_weekdays",
                    VALUE_STATE: "clock_display_weekdays",
                },
            },
        },
    }
)

CMD_CHARGER_THEME = CMD_COMMON | {
    # Command: Set charger theme and display options
    "a2": {
        TYPE: DeviceHexDataTypes.ui.value,
        BYTES: {
            "00": [
                {
                    NAME: "set_clock_switch",
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                    MASK: 0x80,
                    MASK_STATE: "clock_settings",
                    STATE_NAME: "clock_switch",
                    VALUE_STATE: "clock_switch",
                },
                {
                    NAME: "set_holiday_switch",
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                    MASK: 0x40,
                    MASK_STATE: "clock_settings",
                    STATE_NAME: "holiday_switch",
                    VALUE_STATE: "holiday_switch",
                },
                {
                    NAME: "set_theme_type",
                    VALUE_OPTIONS: {"stock": 1, "custom": 2},
                    MASK: 0x06,  # Stock is bit 1, custom is bit 2
                    MASK_STATE: "clock_settings",
                    STATE_NAME: "theme_type",
                    VALUE_DEFAULT: 1,
                },
            ]
        },
    },
    "a3": {
        NAME: "set_theme_id",
        TYPE: DeviceHexDataTypes.var.value,
        SIGNED: False,
        STATE_NAME: "theme_id",
        VALUE_STATE: "theme_id",
        VALUE_MIN: 0,
        VALUE_MAX: 0xFFFFFFFF,
    },
    "a4": {
        NAME: "set_theme_hash",
        TYPE: DeviceHexDataTypes.var.value,
        SIGNED: False,
        STATE_NAME: "theme_hash",
        VALUE_STATE: "theme_hash",
        VALUE_MIN: 0,
        VALUE_MAX: 0xFFFFFFFF,
    },
    "a5": {
        NAME: "set_unknown_a5",  # only FFFFFFFF seen
        TYPE: DeviceHexDataTypes.var.value,
        SIGNED: False,
        VALUE_MIN: 0,
        VALUE_MAX: 0xFFFFFFFF,
        VALUE_DEFAULT: 0xFFFFFFFF,
    },
    "a6": {
        TYPE: DeviceHexDataTypes.bin.value,
        BYTES: {
            "00": {
                NAME: "set_theme_url",
                TYPE: DeviceHexDataTypes.str.value,
                STATE_NAME: "theme_url",
                VALUE_STATE: "theme_url",
            }
        },
    },
}

CMD_CHARGER_CLOCK_HOLIDAY = CMD_COMMON | {
    # Command: Enable / disable clock holiday switch
    COMMAND_NAME: SolixMqttCommands.clock_holiday_switch,
    "a2": {
        NAME: "set_holiday_switch",  # Disable (0) | Enable (1)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "holiday_switch",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
}

CMD_CHARGER_KNOB_MODE = CMD_COMMON | {
    # Command: Set charger know mode: 0 forward, 1 backward
    COMMAND_NAME: SolixMqttCommands.knob_mode_select,
    "a2": {
        NAME: "set_knob_mode",
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "knob_mode",
        VALUE_OPTIONS: {
            "forward": 0,
            "backward": 1,
        },
    },
}

CMD_DISPLAY_TIMEOUT_MODE = CMD_COMMON | {
    # Command: Set charger display timeout mode: 0 (Never), 1 (30 sec), 2 (60 sec), 3 (5 min), 4 (30 min)
    COMMAND_NAME: SolixMqttCommands.display_timeout_mode_select,
    "a2": {
        NAME: "set_display_timeout_mode",
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "display_timeout_mode",
        VALUE_OPTIONS: {
            "0": 0,
            "30": 1,
            "60": 2,
            "300": 3,
            "1800": 4,
        },
    },
}

CMD_PORT_TIMER = {
    port: CMD_COMMON
    | {
        # Command: USB Port Timer setting
        # COMMAND_NAME: Must be added depending on which port is to be selected,
        "a2": {
            NAME: "set_port_timer_select",
            TYPE: DeviceHexDataTypes.ui.value,
            VALUE_OPTIONS: {
                "usbc_1": 0,
                "usbc_2": 1,
                "usbc_3": 2,
                "usbc_4": 3,
                "usba": 4,
            },
            VALUE_DEFAULT: idx,  # same pattern but different default option for port
        },
        "a3": {
            TYPE: DeviceHexDataTypes.bin.value,
            LENGTH: 5,
            BYTES: {
                "00": {
                    NAME: "set_port_timer_switch",
                    TYPE: DeviceHexDataTypes.ui.value,
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                    STATE_NAME: f"{port}_timer_switch",
                    VALUE_STATE: f"{port}_timer_switch",
                },
                "01": {
                    NAME: "set_port_timer_seconds",  # Timer seconds, custom range: 0-86100, step 300
                    TYPE: DeviceHexDataTypes.var.value,
                    VALUE_MIN: 0,
                    VALUE_MAX: 86100,
                    VALUE_STEP: 300,
                    STATE_NAME: f"{port}_timer_seconds",
                    VALUE_STATE: f"{port}_timer_seconds",
                },
            },
        },
    }
    for idx, port in enumerate(["usbc_1", "usbc_2", "usbc_3", "usbc_4", "usba"])
}

CMD_PORT_SCHEDULE = CMD_COMMON | {
    # Command: USB Port start time setting
    # COMMAND_NAME: Must be added depending on which port and time type is to be selected,
    "a2": {
        NAME: "set_port_time_select",
        TYPE: DeviceHexDataTypes.ui.value,
        VALUE_OPTIONS: {
            "usbc_1": 0,
            "usbc_2": 1,
            "usbc_3": 2,
            "usbc_4": 3,
            "usba": 4,
        },
    },
    "a3": {
        NAME: "set_port_time_type_select",
        TYPE: DeviceHexDataTypes.ui.value,
        VALUE_OPTIONS: {
            "end": 0,
            "start": 1,
        },
    },
    "a4": {
        TYPE: DeviceHexDataTypes.var.value,
        BYTES: {
            "00": {
                NAME: "set_port_time_switch",
                TYPE: DeviceHexDataTypes.ui.value,
                VALUE_OPTIONS: {"off": 0, "on": 1, "undefined": 255},
            },
            "01": {
                NAME: "set_port_time_hour",  # hour
                TYPE: DeviceHexDataTypes.ui.value,
                VALUE_MIN: 0,
                VALUE_MAX: 23,
            },
            "02": {
                NAME: "set_port_time_minute",  # min
                TYPE: DeviceHexDataTypes.ui.value,
                VALUE_MIN: 0,
                VALUE_MAX: 59,
            },
            "03": {
                NAME: "set_port_time_weekdays",  # Bitmask: 0:sun:sat:fri:thu:wed:tue:mon
                TYPE: DeviceHexDataTypes.bin.value,
                LENGTH: 1,
                STATE_CONVERTER: lambda value, state, cache: (
                    convert_weekdays(value)
                    if value is not None
                    else convert_weekdays(state)
                ),
            },
        },
    },
}

CMD_PORT_START = {
    port: {
        **CMD_PORT_SCHEDULE
        | {
            "a2": {
                **CMD_PORT_SCHEDULE["a2"],
                VALUE_DEFAULT: idx,  # same pattern but different default option for port
            },
            "a3": {
                **CMD_PORT_SCHEDULE["a3"],
                VALUE_DEFAULT: 1,  # same pattern but different default option for start time
            },
            "a4": {
                **CMD_PORT_SCHEDULE["a4"],
                BYTES: {
                    **CMD_PORT_SCHEDULE["a4"][BYTES],
                    "00": {
                        **CMD_PORT_SCHEDULE["a4"][BYTES]["00"],
                        STATE_NAME: f"{port}_start_switch",
                        VALUE_STATE: f"{port}_start_switch",
                    },
                    "01": {
                        **CMD_PORT_SCHEDULE["a4"][BYTES]["01"],
                        STATE_NAME: f"{port}_start_hour",
                        VALUE_STATE: f"{port}_start_hour",
                    },
                    "02": {
                        **CMD_PORT_SCHEDULE["a4"][BYTES]["02"],
                        STATE_NAME: f"{port}_start_minute",
                        VALUE_STATE: f"{port}_start_minute",
                    },
                    "03": {
                        **CMD_PORT_SCHEDULE["a4"][BYTES]["03"],
                        STATE_NAME: f"{port}_start_weekdays",
                        VALUE_STATE: f"{port}_start_weekdays",
                    },
                },
            },
        },
    }
    for idx, port in enumerate(["usbc_1", "usbc_2", "usbc_3", "usbc_4", "usba"])
}

CMD_PORT_END = {
    port: {
        **CMD_PORT_SCHEDULE
        | {
            "a2": {
                **CMD_PORT_SCHEDULE["a2"],
                VALUE_DEFAULT: idx,  # same pattern but different default option for port
            },
            "a3": {
                **CMD_PORT_SCHEDULE["a3"],
                VALUE_DEFAULT: 0,  # same pattern but different default option for start time
            },
            "a4": {
                **CMD_PORT_SCHEDULE["a4"],
                BYTES: {
                    **CMD_PORT_SCHEDULE["a4"][BYTES],
                    "00": {
                        **CMD_PORT_SCHEDULE["a4"][BYTES]["00"],
                        STATE_NAME: f"{port}_end_switch",
                        VALUE_STATE: f"{port}_end_switch",
                    },
                    "01": {
                        **CMD_PORT_SCHEDULE["a4"][BYTES]["01"],
                        STATE_NAME: f"{port}_end_hour",
                        VALUE_STATE: f"{port}_end_hour",
                    },
                    "02": {
                        **CMD_PORT_SCHEDULE["a4"][BYTES]["02"],
                        STATE_NAME: f"{port}_end_minute",
                        VALUE_STATE: f"{port}_end_minute",
                    },
                    "03": {
                        **CMD_PORT_SCHEDULE["a4"][BYTES]["03"],
                        STATE_NAME: f"{port}_end_weekdays",
                        VALUE_STATE: f"{port}_end_weekdays",
                    },
                },
            },
        },
    }
    for idx, port in enumerate(["usbc_1", "usbc_2", "usbc_3", "usbc_4", "usba"])
}

CMD_PORT_PRIORITY = CMD_COMMON | {
    # Command: Set charger port priority 4 Bit mask
    # Bitmask 0000 1111 to activate prio (usb c1, c2, c3, c4), only 2 ports possible at a time
    COMMAND_NAME: SolixMqttCommands.port_priority,
    "a2": {
        NAME: "set_port_priority",  # 4 Bit mask
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "port_priority",
        VALUE_OPTIONS: {
            "off": 0,
            "c1": 1,
            "c2": 2,
            "c1_c2": 3,
            "c3": 4,
            "c1_c3": 5,
            "c2_c3": 6,
            "c4": 8,
            "c1_c4": 9,
            "c2_c4": 10,
            "c3_c4": 12,
        },
    },
}

CMD_CIRCUIT_PRIORITY = CMD_COMMON | {
    # Command: AX170 power dock circuit priority
    COMMAND_NAME: SolixMqttCommands.circuit_priority,
    "a2": {
        NAME: "set_low_backup_soc",
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "low_backup_soc",
        VALUE_MIN: 10,  # Range to be confirmed!
        VALUE_MAX: 99,
        VALUE_MAX_STATE: "high_backup_soc",
        VALUE_STATE: "low_backup_soc",
    },
    "a3": {
        TYPE: DeviceHexDataTypes.bin.value,
        # Circuit Priority, group ID per circuit
        # group ID must be assigned by algorithm (helper method)
        # Counting starts from last to first circuit, each priority/circuit group start counting from 1
        # Example: 01:08 01:07 01:06 01:05 01:04 01:04 02:01 01:03 01:02 01:02 01:01 01:01
        LENGTH: 24,
        NAME: "set_circuit_priority",
        STATE_CONVERTER: lambda value, state, cache: (
            convert_circuit_setup(
                value, merge=(cache or {}).get("set_circuit_priority")
            )  # provide old setup to merge mocked state
            if value is not None
            else convert_circuit_setup(state)
        ),
        STATE_NAME: "circuit_setup",
        VALUE_STATE: "circuit_setup",
    },
    "a4": {
        NAME: "set_high_backup_soc",
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "high_backup_soc",
        VALUE_MIN: 11,  # Range to be confirmed!
        VALUE_MAX: 100,
        VALUE_MIN_STATE: "low_backup_soc",
        VALUE_STATE: "high_backup_soc",
    },
}

CMD_BACKUP_CHARGE_PLAN = CMD_COMMON | {
    # Command: backup charge plan
    COMMAND_NAME: SolixMqttCommands.backup_charge_plan,
    "a2": {
        NAME: "set_plan_id",  # 4: backup_plan
        TYPE: DeviceHexDataTypes.ui.value,
        VALUE_OPTIONS: {"backup": 4},
        VALUE_DEFAULT: 4,
    },
    "a3": {
        NAME: "set_backup_option_select",
        TYPE: DeviceHexDataTypes.ui.value,
        VALUE_OPTIONS: {"backup_switch": 0, "storm_guard_switch": 1},
        # VALUE_DEFAULT must be set by corresponding command
    },
    "a4": {
        NAME: "set_backup_option_switch",
        TYPE: DeviceHexDataTypes.ui.value,
        VALUE_OPTIONS: {"off": 0, "on": 1},
        # VALUE_STATE must be set by corresponding command
    },
    "a5": {
        NAME: "set_backup_timestamps",  # Must provide a6 timestamps if enabled
        TYPE: DeviceHexDataTypes.ui.value,
        VALUE_OPTIONS: {"off": 0, "on": 1},
        VALUE_DEFAULT: 1,
    },
    "a6": {
        TYPE: DeviceHexDataTypes.bin.value,
        # backup_max_soc, backup_min_soc,start_time,end_time
        # Example: 64: 18: a8:bb:7c:6a: b8:c9:7c:6a
        LENGTH: 10,
        BYTES: {
            "00": {
                STATE_NAME: "set_target_backup_soc",
                TYPE: DeviceHexDataTypes.ui.value,
                VALUE_STATE: "high_backup_soc",
                VALUE_MIN: 80,  # Range to be confirmed!
                VALUE_MAX: 100,
            },
            "01": {
                STATE_NAME: "set_unknown_backup_soc?",
                TYPE: DeviceHexDataTypes.ui.value,
                VALUE_STATE: "unknown_backup_soc",
                VALUE_MIN: 10,  # Range to be confirmed!
                VALUE_MAX: 50,
            },
            "02": {
                NAME: "set_backup_start_timestamp",
                TYPE: DeviceHexDataTypes.var.value,
                SIGNED: False,
                VALUE_MIN: 0,
                VALUE_MAX: 0xFFFFFFFF,
                STATE_NAME: "backup_start_timestamp",
                VALUE_STATE: "backup_start_timestamp",
            },
            "06": {
                NAME: "set_backup_end_timestamp",
                TYPE: DeviceHexDataTypes.var.value,
                SIGNED: False,
                VALUE_MIN: 0,
                VALUE_MAX: 0xFFFFFFFF,
                STATE_NAME: "backup_end_timestamp",
                VALUE_DEFAULT: 0xFFFFFFFF,
            },
        },
    },
}

BACKUP_CHARGE_COMMON_V2 = CMD_COMMON_V2 | {
    # Backup charge plan common fields as used for AS220, A1785
    "a3": {
        NAME: "set_plan_id",  # is this the actual usage plan ID being modified?
        TYPE: DeviceHexDataTypes.ui.value,
        VALUE_OPTIONS: {  # 3=backup_plan
            "backup": 3,
        },
        VALUE_DEFAULT: 3,
    },
    "a4": {
        NAME: "set_backup_option_select",
        TYPE: DeviceHexDataTypes.ui.value,
        VALUE_OPTIONS: {"backup_switch": 0, "storm_guard_switch": 1},
        # VALUE_DEFAULT must be set by corresponding command
    },
    "a5": {
        NAME: "set_backup_option_switch",
        TYPE: DeviceHexDataTypes.ui.value,
        VALUE_OPTIONS: {"off": 0, "on": 1},
        # VALUE_STATE must be set by corresponding command
    },
}

CMD_BACKUP_STORM_GUARD_SWITCH_V2 = BACKUP_CHARGE_COMMON_V2 | {
    "a4": BACKUP_CHARGE_COMMON_V2["a4"]
    | {
        VALUE_DEFAULT: 1,  # Storm Guard switch option
    },
    "a5": BACKUP_CHARGE_COMMON_V2["a5"]
    | {
        STATE_NAME: "storm_guard_switch",
        VALUE_STATE: "storm_guard_switch",
    },
}

CMD_BACKUP_SWITCH_V2 = BACKUP_CHARGE_COMMON_V2 | {
    "a4": BACKUP_CHARGE_COMMON_V2["a4"]
    | {
        VALUE_DEFAULT: 0,  # backup switch option
    },
    "a5": BACKUP_CHARGE_COMMON_V2["a5"]
    | {
        STATE_NAME: "backup_switch",
        VALUE_STATE: "backup_switch",
    },
}

CMD_BACKUP_PLAN_TIMESTAMPS_V2 = CMD_BACKUP_SWITCH_V2 | {
    "a6": {
        NAME: "set_backup_timestamps",  # Must provide a7 timestamps if enabled
        TYPE: DeviceHexDataTypes.ui.value,
        VALUE_OPTIONS: {"off": 0, "on": 1},
        VALUE_DEFAULT: 1,
    },
    "a7": {
        TYPE: DeviceHexDataTypes.bin.value,
        # backup_max_soc, backup_min_soc,start_time,end_time
        # Example: 64: 18: a8:bb:7c:6a: b8:c9:7c:6a
        # NOTE: Field is skipped completely if a6 = 0
        LENGTH: 10,
        BYTES: {
            "00": {
                NAME: "set_backup_charge_soc",
                TYPE: DeviceHexDataTypes.ui.value,
                VALUE_STATE: "max_soc",
                VALUE_MIN: 80,
                VALUE_MAX: 100,
                VALUE_MAX_STATE: "max_soc",
            },
            "01": {
                NAME: "set_backup_discharge_soc",  # 00 if not changeable for device
                TYPE: DeviceHexDataTypes.ui.value,
                # VALUE_FOLLOWS: "backup_soc",
                VALUE_DEFAULT: 0,
            },
            "02": {
                NAME: "set_backup_start_timestamp",
                TYPE: DeviceHexDataTypes.var.value,
                SIGNED: False,
                VALUE_MIN: 0,
                VALUE_MAX: 0xFFFFFFFF,
                STATE_CONVERTER: lambda value, state, cache: (
                    value
                    if value is not None
                    else int(max(datetime.now().astimezone().timestamp(), state))
                    if state is not None
                    else state
                ),
                STATE_NAME: "backup_start_timestamp",
                VALUE_STATE: "backup_start_timestamp",
            },
            "06": {
                NAME: "set_backup_end_timestamp",
                TYPE: DeviceHexDataTypes.var.value,
                SIGNED: False,
                VALUE_MIN: 0,
                VALUE_MAX: 0xFFFFFFFF,
                VALUE_MIN_STATE: "backup_start_timestamp",
                STATE_CONVERTER: lambda value, state, cache: (
                    value
                    if value is not None
                    else int(
                        max(
                            (
                                cache.get("set_backup_start_timestamp")
                                or cache.get("backup_start_timestamp")
                            )
                            + 60,
                            datetime.now().astimezone().timestamp() + 60,
                            v,
                        )
                    )
                    if (v := state or cache.get("backup_end_timestamp") or 0xFFFFFFFF)
                    else state
                ),
                STATE_NAME: "backup_end_timestamp",
            },
        },
    },
}

CMD_PPS_USAGE_MODE_V2 = CMD_COMMON_V2 | {
    # PPS Usage mode and plan settings
    "a2": {  # 0=Standard, 1=Time-of-Use, 2=Self-Consumption, 3=Custom
        NAME: "set_usage_mode",
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "usage_mode",
        VALUE_OPTIONS: {
            "standard": 0,  # UPS mode
            "time_of_use": 1,
            "self_consumption": 2,
            "custom": 3,
        },
    },
}

CMD_TOU_PLAN_V2 = CMD_PPS_USAGE_MODE_V2 | {
    # TOU plan for AS220, A1785, typically sent via cloud
    "a2": CMD_PPS_USAGE_MODE_V2["a2"]
    | {
        VALUE_DEFAULT: 1,  # 0=Standard, 1=Time-of-Use, 2=Self-Consumption, 3=Custom
    },
    "a3": {
        NAME: "set_unknown_a3",  # is this the actual usage plan ID being modified?
        TYPE: DeviceHexDataTypes.ui.value,
        VALUE_DEFAULT: 0,
    },
    "a4": {
        NAME: "set_unknown_a4",
        TYPE: DeviceHexDataTypes.ui.value,
        VALUE_DEFAULT: 0,
    },
    "a6": {
        NAME: "set_unknown_a6",
        TYPE: DeviceHexDataTypes.ui.value,
        VALUE_OPTIONS: {
            "4": 4,
            "3": 3,
        },
    },
    "a7": {
        # 1st Byte is the tou schedule slot count and rest holds the TOU schedule with up to 6 slots a 3 bytes:
        # (tariff(1=Peak,2=Mid,3=Off), start_hr, end_hr) * tou_slot_count
        NAME: "set_tou_mode_schedule",
        TYPE: DeviceHexDataTypes.bin.value,
        STATE_NAME: "tou_mode_schedule",
        STATE_CONVERTER: lambda value, state, cache: (
            # Define both conversions since length of schedule is flexible within binary
            convert_pps_tou_schedule(value)
            if value is not None
            else convert_pps_tou_schedule(state)
        ),
    },
}

CMD_TBD_SWITCH = CMD_COMMON | {
    # Command: Generic switch command with unknown effect
    COMMAND_NAME: SolixMqttCommands.tbd_switch,
    "a2": {
        NAME: "set_tbd_switch",  # Disable (0) | Enable (1)
        TYPE: DeviceHexDataTypes.ui.value,
        STATE_NAME: "tbd_switch",
        VALUE_OPTIONS: {"off": 0, "on": 1},
    },
}
