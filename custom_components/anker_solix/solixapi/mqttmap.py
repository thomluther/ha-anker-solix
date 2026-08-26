"""Define mapping for MQTT messages field conversions depending on Anker Solix model."""

from typing import Final

from .apitypes import DeviceHexDataTypes
from .helpers import (
    convert_circuit_setup,
    convert_port_protocols,
    convert_pps_custom_schedule,
    convert_pps_output_schedule,
    convert_pps_tou_schedule,
    convert_weekdays,
)
from .mqttcmdmap import (
    BYTES,
    CMD_AC_CHARGE_LIMIT,
    CMD_AC_DC_MODE,
    CMD_AC_FAST_CHARGE_SWITCH,
    CMD_AC_OUTPUT_MODE,
    CMD_AC_OUTPUT_MODE_INV,
    CMD_AC_OUTPUT_SWITCH,
    CMD_AC_OUTPUT_TIMEOUT_SEC,
    CMD_AC_PORT_SWITCH,
    CMD_BACKUP_CHARGE_PLAN,
    CMD_BACKUP_PLAN_TIMESTAMPS_V2,
    CMD_BACKUP_STORM_GUARD_SWITCH_V2,
    CMD_BACKUP_SWITCH_V2,
    CMD_BATTERY_CHARGE_LIMITS,
    CMD_CAR_BATTERY_TYPE,
    CMD_CHARGER_CLOCK_DISPLAY,
    CMD_CHARGER_CLOCK_HOLIDAY,
    CMD_CHARGER_CLOCK_MODE,
    CMD_CHARGER_CUSTOM_USAGE_MODE,
    CMD_CHARGER_KNOB_MODE,
    CMD_CHARGER_THEME,
    CMD_CHARGER_USAGE_MODE,
    CMD_CIRCUIT_PRIORITY,
    CMD_COMMON,
    CMD_COMMON_V2,
    CMD_DC_12V_OUTPUT_MODE,
    CMD_DC_12V_OUTPUT_MODE_INV,
    CMD_DC_OUTPUT_SWITCH,
    CMD_DC_OUTPUT_TIMEOUT_SEC,
    # CMD_DEVICE_MAX_LOAD,
    CMD_DEVICE_POWER_MODE,
    CMD_DEVICE_SWITCH,
    CMD_DEVICE_TIMEOUT_MIN,
    CMD_DISPLAY_BRIGHTNESS,
    CMD_DISPLAY_MODE,
    CMD_DISPLAY_SWITCH,
    CMD_DISPLAY_TIMEOUT_MODE,
    CMD_DISPLAY_TIMEOUT_SEC,
    CMD_ENERGY_SAVING_SWITCH,
    CMD_EV_AUTO_CHARGE_RESTART_SWITCH,
    CMD_EV_AUTO_START_SWITCH,
    CMD_EV_CHARGE_RANDOM_DELAY_SWITCH,
    CMD_EV_CHARGER_MODE,
    CMD_EV_CHARGER_SCHEDULE_SETTINGS,
    CMD_EV_CHARGER_SCHEDULE_TIMES,
    CMD_EV_LIGHT_BRIGHTNESS,
    CMD_EV_LIGHT_OFF_SCHEDULE,
    CMD_EV_LOAD_BALANCING,
    CMD_EV_MAX_CHARGE_CURRENT,
    CMD_EV_SOLAR_CHARGING,
    CMD_LIGHT_MODE,
    CMD_MAIN_BREAKER_LIMIT,
    CMD_MODBUS_SWITCH,
    CMD_PLUG_DELAYED_TOGGLE,
    CMD_PLUG_LOCK_SWITCH,
    CMD_PLUG_SCHEDULE,
    CMD_PORT_END,
    CMD_PORT_MEMORY_SWITCH,
    CMD_PORT_PRIORITY,
    CMD_PORT_START,
    CMD_PORT_TIMER,
    CMD_PPS_USAGE_MODE_V2,
    CMD_REALTIME_TRIGGER,
    CMD_REVERSE_CHARGE_LIMITS,
    CMD_SB_3RD_PARTY_PV_SWITCH,
    CMD_SB_AC_INPUT_LIMIT,
    CMD_SB_AC_SOCKET_SWITCH,
    CMD_SB_DEVICE_TIMEOUT,
    CMD_SB_DISABLE_GRID_EXPORT_SWITCH,
    CMD_SB_EV_CHARGER_SWITCH,
    CMD_SB_INVERTER_TYPE,
    CMD_SB_LIGHT_MODE,
    CMD_SB_LIGHT_SWITCH,
    CMD_SB_MAX_LOAD,
    CMD_SB_MIN_SOC,
    CMD_SB_POWER_CUTOFF,
    CMD_SB_PV_LIMIT,
    CMD_SB_SOC_LIMITS,
    CMD_SB_STATUS_CHECK,
    CMD_SB_USAGE_MODE,
    CMD_SMART_TOUCH_MODE,
    CMD_SOC_LIMITS_V2,
    CMD_STATUS_REQUEST,
    CMD_SWIPE_DOWN_MODE,
    CMD_SWIPE_UP_MODE,
    # CMD_TBD_SWITCH,
    CMD_TEMP_UNIT,
    CMD_TEMP_UNIT_V2,
    CMD_TIMER_REQUEST,
    CMD_TOU_PLAN_V2,
    CMD_USB_PORT_SWITCH,
    COMMAND_LIST,
    COMMAND_NAME,
    EMBEDDED,
    FACTOR,
    LENGTH,
    MASK,
    NAME,
    OFFSET,
    SIGNED,
    STATE_CONVERTER,
    STATE_NAME,
    # TIMESTAMP_FE_NOTYPE,
    TOPIC,
    TYPE,
    VALUE_DEFAULT,
    VALUE_FOLLOWS,
    VALUE_MAX,
    VALUE_MAX_STATE,
    VALUE_MIN,
    VALUE_MIN_STATE,
    VALUE_OPTIONS,
    VALUE_OPTIONS_STATE,
    VALUE_STATE,
    VALUE_STEP,
    SolixMqttCommands,
)

# SOLIXMQTTMAP descriptions:
# It is a nested structure to describe value extraction from Solix MQTT messages per model.messagetype.fieldname.attributes
# Field format 0x00 is variable number of bytes, string value (Base type), no special mapping attributes
# Field format 0x01 is 1 byte fix, unsigned int (Base type), FACTOR can be specified optionally for value conversion
# Field format 0x02 is 2 bytes fix, signed int LE (Base type), FACTOR can be specified optionally for value conversion
# Field format 0x03 is always 4 bytes, but could be 1-4 * int, 1-2 * signed int LE or 4 Bytes signed int LE
#   The mapping must specify "values" to indicate number of values in bytes from beginning. Default is 0 for 1 value in 4 bytes
#   FACTOR can be specified optionally for value conversion (applies to all values)
# Field format 0x04 is a bit mask pattern, byte number [00..len-1] reflects position, mask reflects the bit relevant for the value/toggle
#   The mapping must specify start byte string ("00"-"len-1") for fields, field description is a list, since single field can be used for various named settings
#   Each named setting must describe a MASK integer to indicate which bit(s) are relevant for the named setting, e.g. mask 0x64 => 0100 0000
# Field format 0x05 is 4 bytes, signed float LE (Base type), FACTOR can be specified optionally for value conversion
# Field format 0x06 can be many bytes, mix of Str and Byte values
#   The mapping must specify start byte string ("00"-"len-1") for fields, field description needs TYPE,
#   with a DeviceHexDataTypes base type for value conversion (ui=1, sile=2, sfle=4 bytes).
#   The optional LENGTH with int for byte count can be specified (default is 0 if no base type used),
#   where Length of 0 indicates that first byte contains variable field length, e.g. for str type
#   FACTOR can be specified optionally for value conversion
# FACTOR usage example: e.g. int field value -123456 with factor -0.001 will convert the value to float 123.456 (maintaining factor's precision)
# Timestamp values should contain "timestamp" in name to allow decoder methods to convert value to human readable format
# Version declaration bytes should contain "sw_" or "version" in name to convert the value(s) into version string
# Names with ? are hints for fields still to be validated. Names without ? should really be validated for correctness in various situations of the device
# Duplicate names for different fields must be avoided for same device types across its various message types. If same values show up in different message types
# the field name should be the same, so they can be merged once extracting the values from the messages into a consolidated dictionary for the device.

# To simplify the defined map, smaller and re-usable mappings should be defined independently and just re-used in the overall SOLIXMQTTMAP for
# the model types that use same field mapping structure. For example various models of the same family most likely share complete or subset of message maps

_PPS_VERSIONS_0830 = {
    # Various PPS device version param info
    TOPIC: "param_info",
    "a1": {
        NAME: "hw_version",
        TYPE: DeviceHexDataTypes.str.value,
    },
    "a2": {
        NAME: "sw_version",
        TYPE: DeviceHexDataTypes.str.value,
    },
}

_A1722_0405 = {
    # C300 AC param info
    TOPIC: "param_info",
    "a4": {NAME: "remaining_time_hours", FACTOR: 0.1, SIGNED: False},
    "a7": {NAME: "usbc_1_power"},  # USB-C port 1 output power
    "a8": {NAME: "usbc_2_power"},  # USB-C port 2 output power
    "a9": {NAME: "usbc_3_power"},  # USB-C port 3 output power
    "aa": {NAME: "usba_1_power"},  # USB-A port 1 output power
    "ac": {NAME: "dc_input_power_total"},  # DC input power (solar/car charging)
    "ad": {NAME: "ac_input_power_total"},  # Total AC Input in W (int)
    "ae": {NAME: "ac_output_power_total"},  # AC Output in W (int)
    "b7": {
        NAME: "ac_output_power_switch"
    },  # AC output switch: Disabled (0) or Enabled (1)
    "b8": {NAME: "dc_charging_status"},  # None (0), Charging (1)
    "b9": {NAME: "temperature", SIGNED: True},  # In Celsius
    "ba": {NAME: "battery_status"},  # Inactive (0), Discharging (1), Charging (2) ???
    "bb": {NAME: "battery_soc"},  # Battery SOC
    "bc": {NAME: "battery_soh"},  # Battery Health
    "c1": {
        NAME: "dc_output_power_switch"
    },  # DC output switch: Disabled (0) or Enabled (1)
    "c5": {NAME: "device_sn"},  # Device serial number
    "c6": {NAME: "ac_input_limit"},  # Recharge limit
    "cf": {
        NAME: "display_mode"
    },  # Display brightness: Off (0), Low (1), Medium (2), High (3)
    "fe": {NAME: "msg_timestamp"},  # Message timestamp
}

_A1725_0401 = {
    # C200 DC param info (A1725/A1727/A1729) - settings
    TOPIC: "param_info",
    "a1": {NAME: "device_pn"},  # Device PN identifier
    "a4": {NAME: "display_switch"},  # Off (0) or On (1)
}

_A1725_0405 = {
    # C200 DC param info (A1725/A1727)
    TOPIC: "param_info",
    "a1": {NAME: "device_pn"},  # Device PN identifier
    "a3": {
        NAME: "remaining_time_hours",
        FACTOR: 0.1,
        SIGNED: False,
    },  # Remaining runtime
    "a4": {NAME: "usbc_1_power"},  # USB-C top output power
    "a5": {NAME: "usbc_2_power"},  # USB-C middle output power
    "a6": {NAME: "usbc_3_power"},  # USB-C bottom input/output power
    "a8": {NAME: "usba_1_power"},  # USB-A top output power
    "a9": {NAME: "usba_2_power"},  # USB-A bottom output power
    "ab": {NAME: "photovoltaic_power"},  # Solar input power (W)
    "ac": {
        NAME: "dc_input_power_total"
    },  # Total input power (solar + C3 input when charging)
    "ad": {NAME: "dc_output_power_total"},  # Total USB output power
    "af": {NAME: "battery_soc_ah", FACTOR: 0.001},  # Battery SOC (Ah)
    "b5": {NAME: "temperature", SIGNED: True},  # In Celsius
    "b6": {NAME: "battery_status"},  # Battery status: 0=idle, 1=discharge, 2=charge
    "b7": {NAME: "battery_soc"},  # Battery state of charge (%)
    "b8": {NAME: "battery_soh"},  # Battery health
    "b9": {NAME: "usbc_1_status"},  # USB-C1 top status: Inactive (0), Discharging (1)
    "ba": {
        NAME: "usbc_2_status"
    },  # USB-C2 middle status: Inactive (0), Discharging (1)
    "bb": {
        NAME: "usbc_3_status"
    },  # USB-C3 bottom status: Inactive (0), Discharging (1), Charging (2)
    "bd": {NAME: "usba_1_status"},  # USB-A1 top status: Inactive (0), Discharging (1)
    "be": {
        NAME: "usba_2_status"
    },  # USB-A2 bottom status: Inactive (0), Discharging (1)
    "c3": {NAME: "device_sn"},
    "c4": {
        NAME: "device_timeout_minutes"
    },  # Device timeout: never, 30, 60, 120, 240, 360, 720, 1440 minutes
    "c5": {
        NAME: "display_timeout_seconds"
    },  # Display timeout: 20, 30, 60, 300, 1800 seconds
    "c7": {NAME: "display_mode"},  # Brightness: Low (1), Medium (2), High (3)
    "c9": {
        NAME: "temp_unit_fahrenheit"
    },  # Temperature unit: Celsius (0), Fahrenheit (1)
    "ca": {NAME: "display_switch"},  # Off (0) or On (1)
    "cd": {NAME: "pv_1_status"},  # Inactive (0), Solar (1)
    "fe": {NAME: "msg_timestamp"},  # Message timestamp
}

_A1728_0401 = {
    # C300(X) DC param info
    TOPIC: "param_info",
    "a2": {NAME: "dc_output_power_switch"},  # Disabled (0) or Enabled (1)
    "a3": {
        NAME: "light_mode"
    },  # LED light mode: Off (0), Low (1), Medium (2), High (3)
    "a4": {NAME: "display_switch"},  # Off (0) or On (1)
}

_A1728_0404 = {
    # C300(X) DC param info
    TOPIC: "param_info",
    "a2": {NAME: "dc_output_timeout_seconds"},  # Timeout seconds, custom range: 0-86100
}

_A1728_0405 = {
    # C300(X) DC param info
    TOPIC: "param_info",
    "a2": {NAME: "dc_output_timeout_seconds"},  # Timeout seconds, custom range: 0-86100
    "a3": {NAME: "remaining_time_hours", FACTOR: 0.1, SIGNED: False},
    "a4": {NAME: "usbc_1_power"},  # USB-C left output power
    "a5": {NAME: "usbc_2_power"},  # USB-C center input/output power
    "a6": {NAME: "usbc_3_power"},  # USB-C right input/output power
    "a7": {NAME: "usbc_4_power"},  # USB-C top output power
    "a8": {NAME: "usba_1_power"},  # USB-A left output power
    "a9": {NAME: "usba_2_power"},  # USB-A right output power
    "aa": {NAME: "dc_12v_1_power"},  # 12V car charger port output power
    "ab": {NAME: "photovoltaic_power"},  # Solar input power
    "ac": {NAME: "dc_input_power_total"},  # DC input power total (solar + USB-C input)
    "ad": {NAME: "dc_output_power_total"},  # Total DC output power for all ports
    "af": {NAME: "battery_soc_ah", FACTOR: 0.001},  # Battery SOC (Ah)
    "b0": {NAME: "sw_version", "values": 1},  # Main firmware version
    # "b1": {NAME: "version1?", "values": 1},  # Version?
    # "b2": {NAME: "version2?", "values": 1},  # Version?
    # "b3": {NAME: "version3?", "values": 1},  # Same as main firmware version
    # "b4": {NAME: "version4?", "values": 1},  # Same as main firmware version
    "b5": {NAME: "temperature", SIGNED: True},  # In Celsius
    "b6": {
        NAME: "battery_status",  # Battery status: Inactive (0), Discharging (1), Charging (2)
    },
    "b7": {NAME: "battery_soc"},  # Battery SOC
    "b8": {NAME: "battery_soh"},  # Battery health
    "b9": {NAME: "usbc_1_status"},  # USB-C left status: Inactive (0), Discharging (1)
    "ba": {
        NAME: "usbc_2_status"
    },  # USB-C center status: Inactive (0), Discharging (1), Charging (2)
    "bb": {NAME: "usbc_3_status"},  # USB-C right status: Inactive (0), Discharging (1)
    "bc": {NAME: "usbc_4_status"},  # USB-C top status: Inactive (0), Discharging (1)
    "bd": {NAME: "usba_1_status"},  # USB-A left status: Inactive (0), Discharging (1)
    "be": {NAME: "usba_2_status"},  # USB-A right status: Inactive (0), Discharging (1)
    # "bf": {NAME: "dc_12v_1_status"},  # DC 12V status: Inactive (0), Discharging (1)
    "bf": {NAME: "dc_output_power_switch"},  # Disabled (0) or Enabled (1)
    "c1": {
        NAME: "overload_event"
    },  # Overload event for port: None (0), USB-C1 (8), USB-C2 (9), USB-C3 (10), ...?
    "c3": {NAME: "device_sn"},
    "c4": {
        NAME: "device_timeout_minutes"
    },  # Device timeout: never, 30, 60, 120, 240, 360, 720, 1440 minutes
    "c5": {
        NAME: "display_timeout_seconds"
    },  # Display timeout: 20, 30, 60, 300, 1800 seconds
    "c7": {NAME: "display_mode"},  # Brightness: Low (1), Medium (2), High (3)
    "c8": {
        NAME: "light_mode"
    },  # LED light mode: Off (0), Low (1), Medium (2), High (3)
    "c9": {NAME: "temp_unit_fahrenheit"},  # Celsius (0) or Fahrenheit (1)
    "ca": {NAME: "display_switch"},  # Off (0) or On (1)
    "cb": {
        NAME: "light_timeout_minutes"
    },  # Light timeout: never, 30, 60, 120, 240, 360, 720, 1440 minutes
    "cd": {NAME: "pv_1_status"},  # Inactive (0), Solar (1)
    "f7": {
        NAME: "dc_12v_auto_on"
    },  # Off (0), Last state (1) - as soon as the battery is charged to 10% again
    "f8": {
        BYTES: {
            "00": {
                NAME: "dc_12v_output_mode",  # Normal (1), Smart (2) - auto-off below 3W
                TYPE: DeviceHexDataTypes.ui.value,
            },
        }
    },
    "fe": {NAME: "msg_timestamp"},  # Message timestamp
}

_A1753_0405 = {
    # PPS C800 (A1753) param info
    # Field layout matches the C1000 (_A1761_0405) as well as C800X (A1755) as well as likely C800 Plus (A1754)
    # A1754 message format still to be provided and validated
    TOPIC: "param_info",
    "a2": {
        NAME: "ac_output_timeout_seconds"
    },  # Active AC output auto-off countdown in seconds (0 = disabled); set via cmd 0042, range 0-86400, step 300
    "a3": {
        NAME: "dc_output_timeout_seconds"
    },  # Active DC output auto-off countdown in seconds (0 = disabled); verified via app timer changes
    "a4": {
        NAME: "remaining_time_hours",
        FACTOR: 0.1,
        SIGNED: False,
    },  # Remaining runtime in hours (value * factor)
    "a5": {NAME: "ac_input_power"},  # AC charging power to battery (W)
    "a6": {NAME: "ac_output_power"},  # AC outlet output power (W)
    "a7": {NAME: "usbc_1_power"},  # USB-C port 1 output power (W)
    "a8": {NAME: "usbc_2_power"},  # USB-C port 2 output power (W)
    "a9": {NAME: "usba_1_power"},  # USB-A port 1 output power (W)
    "aa": {NAME: "usba_2_power"},  # USB-A port 2 output power (W)
    "ae": {NAME: "dc_input_power"},  # DC input power (solar/car charging) (W)
    "af": {NAME: "photovoltaic_power"},  # Solar input power (W)
    "b0": {
        NAME: "output_power_total"
    },  # Combined AC + DC output power (W), includes LED lamp (1-3 W)
    "b3": {NAME: "sw_version", "values": 1},  # Main firmware version
    "b9": {NAME: "sw_expansion", "values": 1},  # Expansion firmware version
    "ba": {NAME: "sw_controller", "values": 1},  # Controller firmware version
    "bb": {
        NAME: "ac_output_status"
    },  # AC inverter: Off (0), On (1); mirrors switch state d7
    "bc": {
        NAME: "charging_status",  # Inactive (0), Solar (1), AC Input (2), Both (3)
    },
    "bd": {NAME: "temperature", SIGNED: True},  # Main device temperature (°C)
    "be": {
        NAME: "exp_1_temperature",
        SIGNED: True,
    },  # Expansion battery 1 temperature (°C)
    "bf": {NAME: "battery_status"},  # 0=standby, 1=discharge, 2=Charge
    "c1": {
        NAME: "main_battery_soc"
    },  # Main battery state of charge (%), verified on real device
    "c2": {NAME: "exp_1_soc"},  # Expansion battery 1 state of charge (%)
    "c3": {NAME: "battery_soh"},  # Main battery state of health (%), may be 0 for A1753
    "c4": {
        NAME: "exp_1_soh"
    },  # Expansion battery 1 state of health (%), may be 0 for A1753
    "c5": {NAME: "expansion_packs"},  # number of expansion batteries
    "c6": {NAME: "usbc_1_status"},  # 0:0ff, 1:On
    "c7": {NAME: "usbc_2_status"},  # 0:0ff, 1:On
    "c8": {NAME: "usba_1_status"},  # 0:0ff, 1:On
    "c9": {NAME: "usba_2_status"},  # 0:0ff, 1:On
    "cc": {
        NAME: "dc_12v_1_status"
    },  # 12V car socket: Off (0), On (1); mirrors switch state d8
    "d0": {NAME: "device_sn"},  # Device serial number
    "d1": {
        NAME: "ac_input_limit"
    },  # Max AC charge setting (W), 750/700/600/500/400/300/200
    "d2": {
        NAME: "device_timeout_minutes"
    },  # Device auto-off timeout (minutes): 0 (Never), 30, 60, 120, 240, 360, 720, 1440
    "d3": {NAME: "display_timeout_seconds"},  # Options: 20, 30, 60, 300, 1800 seconds
    "d7": {NAME: "ac_output_power_switch"},  # Disabled (0) or Enabled (1)
    "d8": {NAME: "dc_output_power_switch"},  # Disabled (0) or Enabled (1)
    "d9": {NAME: "display_mode"},  # Brightness: Off (0), Low (1), Medium (2), High (3)
    "da": {NAME: "ac_frequency"},  # AC frequency (Hz): 50 / 60
    "dc": {NAME: "light_mode"},  # LED bar: Off (0), Low (1), Medium (2), High (3)
    "de": {NAME: "display_switch"},  # Off (0) or On (1)
    "dd": {NAME: "temp_unit_fahrenheit"},  # Celsius (0) or Fahrenheit (1)
    "e5": {
        NAME: "ac_fast_charge_switch"
    },  # Ultrafast Charge switch: Disabled (0) or Enabled (1)
    "f8": {
        BYTES: {
            "00": {
                NAME: "dc_12v_output_mode",  # Normal (1), Smart (2) - auto-off below 3W
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "01": {
                NAME: "ac_output_mode",  # Normal (1), Smart (2) - auto-off when not charging and low power
                TYPE: DeviceHexDataTypes.ui.value,
            },
        }
    },
    "fd": {NAME: "exp_1_type"},  # Expansion battery type identifier
    "fe": {NAME: "msg_timestamp"},  # Message timestamp
}

_A1761_0405 = {
    # PPS C1000(X) parm info
    TOPIC: "param_info",
    "a2": {
        NAME: "ac_output_timeout_seconds"
    },  # Active AC output auto-off countdown in seconds, range 0-86400, step 300
    "a3": {
        NAME: "dc_output_timeout_seconds"
    },  # Active DC output auto-off countdown in seconds, range 0-86400, step 300
    "a4": {
        NAME: "remaining_time_hours",
        FACTOR: 0.1,
        SIGNED: False,
    },  # In hours (value * factor)
    "a5": {NAME: "ac_input_power"},  # AC charging power to battery
    "a6": {NAME: "ac_output_power"},  # Individual AC outlet power
    "a7": {NAME: "usbc_1_power"},  # USB-C port 1 output power
    "a8": {NAME: "usbc_2_power"},  # USB-C port 2 output power
    "a9": {NAME: "usba_1_power"},  # USB-A port 1 output power
    "aa": {NAME: "usba_2_power"},  # USB-A port 2 output power
    "ae": {NAME: "dc_input_power"},  # DC input power (solar/car charging)
    "af": {NAME: "photovoltaic_power"},  # Solar input
    "b0": {NAME: "output_power_total"},  # Combined AC DC output power
    "b3": {NAME: "sw_version", "values": 1},  # Main firmware version
    "b9": {NAME: "sw_expansion", "values": 1},  # Expansion firmware version
    "ba": {NAME: "sw_controller", "values": 1},  # Controller firmware version
    "bb": {
        NAME: "ac_output_status"
    },  # AC inverter: Off (0), On (1); mirrors switch state d7
    "bc": {
        NAME: "charging_status",  # Inactive (0), Solar (1), AC Input (2), Both (3)
    },
    "bd": {NAME: "temperature", SIGNED: True},  # Main device temperature (°C)
    "be": {
        NAME: "exp_1_temperature",
        SIGNED: True,
    },  # Expansion battery 1 temperature (°C)
    "c1": {NAME: "main_battery_soc"},  # Main battery state of charge (%)
    "c2": {NAME: "exp_1_soc"},  # Expansion battery 1 state of charge (%)
    "c3": {NAME: "battery_soh"},  # Main battery state of health (%)
    "c4": {NAME: "exp_1_soh"},  # Expansion battery 1 state of health (%)
    "c5": {NAME: "expansion_packs"},  # number of expansion batteries
    "c6": {NAME: "usbc_1_status"},  # 0:0ff, 1:On
    "c7": {NAME: "usbc_2_status"},  # 0:0ff, 1:On
    "c8": {NAME: "usba_1_status"},  # 0:0ff, 1:On
    "c9": {NAME: "usba_2_status"},  # 0:0ff, 1:On
    "cc": {
        NAME: "dc_12v_1_status"
    },  # 12V car socket: Off (0), On (1); mirrors switch state d8
    "d0": {NAME: "device_sn"},  # Device serial number
    "d1": {NAME: "ac_input_limit"},  # Max AC charge setting (W)
    "d2": {
        NAME: "device_timeout_minutes"
    },  # Device auto-off timeout (minutes): 0 (Never), 30, 60, 120, 240, 360, 720, 1440
    "d3": {NAME: "display_timeout_seconds"},  # Options: 20, 30, 60, 300, 1800 seconds
    "d7": {NAME: "ac_output_power_switch"},  # Disabled (0) or Enabled (1)
    "d8": {NAME: "dc_output_power_switch"},  # Disabled (0) or Enabled (1)
    "d9": {NAME: "display_mode"},  # Brightness: Off (0), Low (1), Medium (2), High (3)
    "da": {NAME: "ac_frequency"},  # 60 / 50 Hz
    "dc": {
        NAME: "light_mode"
    },  # LED light mode: Off (0), Low (1), Medium (2), High (3), Blinking (4)
    "dd": {NAME: "temp_unit_fahrenheit"},  # Celsius (0) or Fahrenheit (1)
    "de": {NAME: "display_switch"},  # Off (0) or On (1)
    "e5": {
        NAME: "ac_fast_charge_switch"
    },  # Ultrafast Charge switch: Disabled (0) or Enabled (1)
    "f8": {
        BYTES: {
            "00": {
                NAME: "dc_12v_output_mode",  # Normal (1), Smart (2) - auto-off below 3W
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "01": {
                NAME: "ac_output_mode",  # Normal (1), Smart (2) - auto-off when not charging and low power
                TYPE: DeviceHexDataTypes.ui.value,
            },
        }
    },
    "fd": {NAME: "exp_1_type"},  # Expansion battery type identifier
    "fe": {NAME: "msg_timestamp"},  # Message timestamp
}

_A1763_0421 = {
    "a2": {
        BYTES: {
            "01": {
                NAME: "device_sn",
                TYPE: DeviceHexDataTypes.str.value,
            },
            "20": {
                NAME: "device_pn",
                TYPE: DeviceHexDataTypes.str.value,
            },
        }
    },
    "a3": {
        BYTES: {
            "04": {
                NAME: "ac_input_limit_max",  # Max supported charge limit, seems fix
                TYPE: DeviceHexDataTypes.sile.value,
            },
        }
    },
    "a4": {
        BYTES: {
            "00": {
                NAME: "ac_output_timeout_seconds",  # disable (0), min:0, max: 86400, step 300
                TYPE: DeviceHexDataTypes.var.value,
                LENGTH: 4,
            },
            "04": {
                NAME: "ac_input_limit",  # AC charge limit: 100-1200 W, step: 100
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "06": {
                NAME: "ac_frequency",  # 60 / 50 Hz
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "07": {
                NAME: "ac_output_mode",  # Normal (0), Smart (1) - auto-off below 14W
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "08": {
                NAME: "dc_output_timeout_seconds",  # disable (0), min:0, max: 86400, step 300
                TYPE: DeviceHexDataTypes.var.value,
                LENGTH: 4,
            },
            "12": {
                NAME: "dc_12v_output_mode",  # Normal (0), Smart (1) - auto-off below 3W
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "13": {
                NAME: "device_timeout_minutes",  # 0 (Never), 30, 60, 120, 240, 360, 720, 1440
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "15": {
                NAME: "display_timeout_seconds",  # 0 (Never), 10, 30, 60, 300, 1800
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "17": {
                NAME: "display_mode",  # Low (1), Medium (2), High (3)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "19": {
                NAME: "temp_unit_fahrenheit",  # Celsius (0) or Fahrenheit (1)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "20": {
                NAME: "ac_fast_charge_switch",  # Ultrafast Charge switch: Disabled (0) or Enabled (1)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "21": {
                NAME: "display_switch",  # Off (0), On (1)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "22": {
                NAME: "port_memory_switch",  # Output Port Memory switch: Disabled (0) or Enabled (1)
                TYPE: DeviceHexDataTypes.ui.value,
            },
        }
    },
    "a5": {
        BYTES: {
            "00": {
                NAME: "temperature",
                SIGNED: True,
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "02": {
                NAME: "battery_soc",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "03": {
                NAME: "battery_soh",
                TYPE: DeviceHexDataTypes.ui.value,
            },
        }
    },
    "a6": {
        BYTES: {
            "00": {
                NAME: "output_power_total",  # Output power total (AC + DC)
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "02": {
                NAME: "ac_input_power_total",  # Input power total charge
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "04": {
                NAME: "dc_input_power_total",  # # DC input power (solar + car charging)
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "06": {
                NAME: "remaining_time_hours",  # hours with factor 0.1
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.1,
                SIGNED: False,
            },
            "08": {
                NAME: "main_battery_soc",  # SOC of main battery only
                TYPE: DeviceHexDataTypes.ui.value,
            },
        },
    },
    "a7": {
        BYTES: {
            "00": {
                NAME: "ac_output_power_switch",  # Off (0), On (1)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "01": {
                NAME: "ac_output_power",  # AC Output power
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "03": {
                NAME: "ac_input_power_switch",  # Off (0), On (1)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "04": {
                NAME: "ac_input_power",  # Duplicate of a6
                TYPE: DeviceHexDataTypes.sile.value,
            },
        }
    },
    "a8": {
        BYTES: {
            "00": {
                NAME: "dc_input_power_switch",  # Off (0), On (1)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "01": {
                NAME: "dc_input_power_total",  # DC input power (solar + car charging)
                TYPE: DeviceHexDataTypes.sile.value,
            },
        }
    },
    "aa": {
        BYTES: {
            "00": {
                NAME: "usbc_1_status",  # USB-C 1 status: Inactive (0), Discharging (1), Charging (2)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "01": {
                NAME: "usbc_1_power",
                TYPE: DeviceHexDataTypes.sile.value,
            },
        }
    },
    "ab": {
        BYTES: {
            "00": {
                NAME: "usbc_2_status",  # USB-C 2 status: Inactive (0), Discharging (1), Charging (2)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "01": {
                NAME: "usbc_2_power",
                TYPE: DeviceHexDataTypes.sile.value,
            },
        }
    },
    "ac": {
        BYTES: {
            "00": {
                NAME: "usbc_3_status",  # USB-C 3 status: Inactive (0), Discharging (1), Charging (2)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "01": {
                NAME: "usbc_3_power",
                TYPE: DeviceHexDataTypes.sile.value,
            },
        }
    },
    "ae": {
        BYTES: {
            "00": {
                NAME: "usba_1_status",  # USB-A 1 status: Inactive (0), Discharging (1), Charging (2)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "01": {
                NAME: "usba_1_power",
                TYPE: DeviceHexDataTypes.sile.value,
            },
        }
    },
    "b2": {
        BYTES: {
            "00": {
                NAME: "dc_output_power_switch",  # Off (0), On (1)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "01": {
                NAME: "dc_output_power_total",  # Total Watt DC
                TYPE: DeviceHexDataTypes.sile.value,
            },
        }
    },
    "c0": {
        BYTES: [
            # Field has flexible byte offsets, depending on SN length
            {
                NAME: "exp_1_sn",
                TYPE: DeviceHexDataTypes.str.value,
            },
            {
                NAME: "exp_1_temperature",
                TYPE: DeviceHexDataTypes.ui.value,
                SIGNED: True,
                OFFSET: 5,
            },
            {
                NAME: "exp_1_soc",
                TYPE: DeviceHexDataTypes.ui.value,
                OFFSET: 1,
            },
            {
                NAME: "exp_1_type",
                TYPE: DeviceHexDataTypes.str.value,
                OFFSET: 6,
            },
        ]
    },
    "d9": {
        BYTES: {
            "03": {
                NAME: "max_soc",  # max_soc: 80, 85, 90, 95, 100 %
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "04": {
                NAME: "min_soc",  # min_soc: 1, 5, 10, 15, 20 %
                TYPE: DeviceHexDataTypes.ui.value,
            },
        }
    },
    # "da": # Field used for screen schedule and theme settings, not supported on device
    "f9": {
        BYTES: {
            "00": {
                NAME: "sw_version",
                TYPE: DeviceHexDataTypes.var.value,
                "values": 4,
                "reversed": True,
            },
            "16": {
                NAME: "bms_version",
                TYPE: DeviceHexDataTypes.var.value,
                "values": 4,
                "reversed": True,
            },
            "24": {
                NAME: "hw_version",
                TYPE: DeviceHexDataTypes.var.value,
                "values": 4,
                "reversed": True,
            },
        }
    },
    "fd": {NAME: "storm_guard_timestamp", SIGNED: False},
    "fe": {NAME: "msg_timestamp"},
}

_A1783_0421 = {
    "a2": {
        BYTES: {
            "01": {
                NAME: "device_sn",
                TYPE: DeviceHexDataTypes.str.value,
            },
            "20": {
                NAME: "device_pn",
                TYPE: DeviceHexDataTypes.str.value,
            },
            "26": {
                NAME: "sw_version",
                TYPE: DeviceHexDataTypes.var.value,
                "values": 4,
                "reversed": True,
            },
        }
    },
    "a3": {
        BYTES: {
            "00": {
                NAME: "working_status",  # 0 idle / 1 discharge / 2 charge / 3 sleep / 4 shutdown / 5 ???
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "04": {
                NAME: "ac_input_limit_max",  # Max supported charge limit, seems fix
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "07": {
                NAME: "wifi_signal",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "08": {
                NAME: "mtu_size",
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "10": {
                NAME: "silent_charge_power",
                TYPE: DeviceHexDataTypes.sile.value,
            },
        }
    },
    "a4": {
        BYTES: {
            "00": {
                NAME: "ac_output_timeout_seconds",  # disabled (0), min:0, max: 86400, step 300
                TYPE: DeviceHexDataTypes.var.value,
                LENGTH: 4,
            },
            "04": {
                NAME: "ac_input_limit",  # AC charge limit: 100-1800 W, step: 100
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "06": {
                NAME: "ac_frequency",  # 60 / 50 Hz
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "07": {
                NAME: "ac_output_mode",  # Normal (0), Smart (1) - auto-off below 14W
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "08": {
                NAME: "dc_output_timeout_seconds",  # disable (0), min:0, max: 86400, step 300
                TYPE: DeviceHexDataTypes.var.value,
                LENGTH: 4,
            },
            "12": {
                NAME: "dc_12v_output_mode",  # Normal (0), Smart (1) - auto-off below 3W
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "13": {
                NAME: "device_timeout_minutes",  # 0 (Never), 30, 60, 120, 240, 360, 720, 1440
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "15": {
                NAME: "display_timeout_seconds",  # 0 (Never), 10, 30, 60, 300, 1800
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "17": {
                NAME: "display_mode",  # Low (1), Medium (2), High (3)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "19": {
                NAME: "temp_unit_fahrenheit",  # Celsius (0) or Fahrenheit (1)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "20": {
                NAME: "ac_fast_charge_switch",  # Ultrafast Charge switch: Disabled (0) or Enabled (1)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "21": {
                NAME: "display_switch",  # Off (0), On (1)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "22": {
                NAME: "port_memory_switch",  # Output Port Memory switch: Disabled (0) or Enabled (1)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "23": {
                NAME: "max_soc",  # max_soc: 80, 85, 90, 95, 100 %
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "24": {
                NAME: "min_soc",  # min_soc: 1, 5, 10, 15, 20 %
                TYPE: DeviceHexDataTypes.ui.value,
            },
        }
    },
    "a5": {
        BYTES: {
            "00": {
                NAME: "temperature",
                SIGNED: True,
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "01": {
                NAME: "battery_status",  # 0=standby, 1=discharge, 2=Charge
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "02": {
                NAME: "battery_soc",  # Total SOC of main + Exp batteries?
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "03": {  # Note: This seems to be actually 0 for A1783/85
                NAME: "battery_soh",  # Battery SOH
                TYPE: DeviceHexDataTypes.ui.value,
            },
        }
    },
    "a6": {
        BYTES: {
            "00": {
                NAME: "output_power_total",  # Output power total (AC + DC)
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "02": {
                NAME: "ac_input_power",  # Input power total charge
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "04": {
                NAME: "dc_input_power_total",  # # DC input power (solar + car charging)
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "06": {
                NAME: "remaining_time_hours",  # hours with factor 0.1
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.1,
                SIGNED: False,
            },
            "08": {
                NAME: "main_battery_soc",  # SOC of main battery only
                TYPE: DeviceHexDataTypes.ui.value,
            },
        },
    },
    "a7": {
        BYTES: {
            "00": {
                NAME: "ac_output_power_switch",  # Off (0), On (1)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "01": {
                NAME: "ac_output_power",  # AC Output power
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "03": {
                NAME: "ac_input_power_switch",  # Off (0), On (1)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "04": {
                NAME: "pv_input_power?",  # Supposed PV input, but mirrors a6.02
                TYPE: DeviceHexDataTypes.sile.value,
            },
        }
    },
    "aa": {
        BYTES: {
            "00": {
                NAME: "usbc_1_status",  # USB-C 1 status: Inactive (0), Discharging (1), Charging (2)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "01": {
                NAME: "usbc_1_power",
                TYPE: DeviceHexDataTypes.sile.value,
            },
        }
    },
    "ab": {
        BYTES: {
            "00": {
                NAME: "usbc_2_status",  # USB-C 2 status: Inactive (0), Discharging (1), Charging (2)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "01": {
                NAME: "usbc_2_power",
                TYPE: DeviceHexDataTypes.sile.value,
            },
        }
    },
    "ac": {
        BYTES: {
            "00": {
                NAME: "usbc_3_status",  # USB-C 3 status: Inactive (0), Discharging (1), Charging (2)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "01": {
                NAME: "usbc_3_power",
                TYPE: DeviceHexDataTypes.sile.value,
            },
        }
    },
    "ae": {
        BYTES: {
            "00": {
                NAME: "usba_1_status",  # USB-A 1 status: Inactive (0), Discharging (1), Charging (2)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "01": {
                NAME: "usba_1_power",
                TYPE: DeviceHexDataTypes.sile.value,
            },
        }
    },
    "b2": {
        BYTES: {
            "00": {
                NAME: "dc_output_power_switch",  # Off (0), On (1)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "01": {
                NAME: "dc_output_power_total",  # Total Watt DC
                TYPE: DeviceHexDataTypes.sile.value,
            },
        }
    },
    "c0": {
        BYTES: [
            # Field has flexible byte offsets, depending on SN length
            {
                NAME: "exp_1_sn",
                TYPE: DeviceHexDataTypes.str.value,
            },
            {
                NAME: "exp_1_temperature",
                TYPE: DeviceHexDataTypes.ui.value,
                SIGNED: True,
                OFFSET: 5,
            },
            {
                NAME: "exp_1_soc",
                TYPE: DeviceHexDataTypes.ui.value,
                OFFSET: 1,
            },
            {
                NAME: "exp_1_type",
                TYPE: DeviceHexDataTypes.str.value,
                OFFSET: 6,
            },
        ]
    },
    "ce": {
        BYTES: {
            "00": {
                NAME: "device_1_pn",
                TYPE: DeviceHexDataTypes.str.value,
            },
            "18": {
                NAME: "device_1_sn",
                TYPE: DeviceHexDataTypes.str.value,
            },
            "40": {
                NAME: "device_1_mode",  # reverse charge (1), charge (2), standby (3)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "41": {
                NAME: "device_1_output_power",
                TYPE: DeviceHexDataTypes.sile.value,
            },
        }
    },
    "d9": {
        # TOU mode selector + backup + Time-of-Use plan
        BYTES: [
            {
                NAME: "active_plan",  # TOUSystemStatus: 0=Standard/UPS, 3=Time-of-Use, 4=Self-Consumption, 5=Custom
                TYPE: DeviceHexDataTypes.ui.value,
            },
            {
                NAME: "usage_mode",  # TOUSettingSystemStatus: 0=Standard, 1=Time-of-Use, 2=Self-Consumption, 3=Custom
                TYPE: DeviceHexDataTypes.ui.value,
            },
            {
                NAME: "backup_soc",  # backup reserve % (discharge floor for tou)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            {
                NAME: "backup_charge_soc",  # changed with max_soc % (for tou and backup usage)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            {
                NAME: "backup_discharge_soc",  # changed with min_soc % (for backup discharge?)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            # Byte 5 is the tou schedule slot count and 6+ holds the TOU schedule:
            # (tariff(1=Peak,2=Mid,3=Off), start_hr, end_hr) * tou_slot_count
            # App allows max 6 slots, remainder of field has different purpose
            {
                NAME: "tou_mode_schedule",
                TYPE: DeviceHexDataTypes.bin.value,
                # Define both conversions since length of schedule is flexible within binary
                STATE_CONVERTER: lambda value, state, cache: (
                    convert_pps_tou_schedule(value)
                    if value is not None
                    else convert_pps_tou_schedule(state)
                ),
            },
            {
                NAME: "backup_status",  # 0: inactive, 1: planned charge: 2: storm guard charge
                TYPE: DeviceHexDataTypes.ui.value,
            },
            {
                NAME: "backup_switch",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            {
                NAME: "storm_guard_switch",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            {
                NAME: "backup_start_timestamp",
                TYPE: DeviceHexDataTypes.var.value,
                SIGNED: False,
            },
            {
                NAME: "backup_end_timestamp",
                TYPE: DeviceHexDataTypes.var.value,
                SIGNED: False,
            },
            {
                NAME: "auto_backup_start_timestamp",
                TYPE: DeviceHexDataTypes.var.value,
                SIGNED: False,
            },
            {
                NAME: "auto_backup_end_timestamp",
                TYPE: DeviceHexDataTypes.var.value,
                SIGNED: False,
            },
        ]
    },
    # "da" # Field used for screen schedule and theme settings
    "f9": {
        BYTES: {
            "00": {
                NAME: "sw_version",
                TYPE: DeviceHexDataTypes.var.value,
                "values": 4,
                "reversed": True,
            },
            "04": {
                NAME: "mcu_version",
                TYPE: DeviceHexDataTypes.var.value,
                "values": 4,
                "reversed": True,
            },
            "16": {
                NAME: "bms_version",
                TYPE: DeviceHexDataTypes.var.value,
                "values": 4,
                "reversed": True,
            },
            "24": {
                NAME: "hw_version",
                TYPE: DeviceHexDataTypes.var.value,
                "values": 4,
                "reversed": True,
            },
        }
    },
    "fd": {NAME: "storm_guard_timestamp", SIGNED: False},
    "fe": {NAME: "msg_timestamp"},
}

_A1780_0405 = {
    # F2000(P) param info
    TOPIC: "param_info",
    "a2": {
        NAME: "ac_output_timeout_seconds"
    },  # Active AC auto-off countdown in seconds
    "a3": {
        NAME: "dc_output_timeout_seconds"
    },  # Active DC auto-off countdown in seconds
    "a4": {NAME: "remaining_time_hours", FACTOR: 0.1, SIGNED: False},  # In hours
    "a5": {NAME: "ac_input_power"},  # AC charging power to battery
    "a6": {NAME: "ac_output_power"},  # AC outlet power
    "a7": {NAME: "usbc_1_power"},  # USB-C port 1 output power
    "a8": {NAME: "usbc_2_power"},  # USB-C port 2 output power
    "a9": {NAME: "usbc_3_power"},  # USB-C port 3 output power
    "aa": {NAME: "usba_1_power"},  # USB-A port 1 output power
    "ab": {NAME: "usba_2_power"},  # USB-A port 2 output power
    "ac": {NAME: "dc_12v_1_power"},  # 12V port 1 output power
    "ad": {NAME: "dc_12v_2_power"},  # 12V port 2 output power
    "ae": {NAME: "dc_input_power"},  # DC input power (solar/car charging)
    "af": {NAME: "photovoltaic_power"},  # Solar input
    "b0": {NAME: "output_power_total"},  # Combined AC DC output power
    "b3": {NAME: "sw_version", "values": 1},  # Main firmware version
    "b9": {NAME: "sw_expansion", "values": 1},  # Expansion firmware version
    "ba": {NAME: "sw_controller", "values": 1},  # Controller firmware version
    "bc": {
        NAME: "charging_status",  # Inactive (0), Solar (1), AC Input (2), Both (3)
    },
    "bd": {NAME: "temperature", SIGNED: True},  # Main device temperature (°C)
    "be": {
        NAME: "exp_1_temperature",
        SIGNED: True,
    },  # Expansion battery 1 temperature (°C)
    "bf": {NAME: "battery_status"},  # 0=standby, 1=discharge, 2=Charge
    "c1": {NAME: "main_battery_soc"},  # Main battery state of charge (%)
    "c2": {NAME: "exp_1_soc"},  # Expansion battery 1 state of charge (%)
    "c3": {NAME: "battery_soh"},  # Main battery state of health (%)
    "c4": {NAME: "exp_1_soh"},  # Expansion battery 1 state of health (%)
    "c5": {NAME: "expansion_packs"},
    "c6": {NAME: "usbc_1_status"},  # 0:0ff, 1:On
    "c7": {NAME: "usbc_2_status"},  # 0:0ff, 1:On
    "c8": {NAME: "usbc_3_status"},  # 0:0ff, 1:On
    "c9": {NAME: "usba_1_status"},  # 0:0ff, 1:On
    "ca": {NAME: "usba_2_status"},  # 0:0ff, 1:On
    "cb": {NAME: "dc_12v_1_status"},  # 0:0ff, 1:On
    "cc": {NAME: "dc_12v_2_status"},  # 0:0ff, 1:On
    "d0": {NAME: "device_sn"},
    "d1": {NAME: "ac_input_limit"},  # Maximum charge setting (W)
    "d2": {
        NAME: "device_timeout_minutes"
    },  # Device auto-off timeout (minutes): 0 (Never), 30, 60, 120, 240, 360, 720, 1440
    "d3": {
        NAME: "display_timeout_seconds"
    },  # Display timeout: 20, 30, 60, 300, 1800 seconds
    "d7": {NAME: "ac_output_power_switch"},  # Disabled (0) or Enabled (1)
    "d8": {NAME: "dc_output_power_switch"},  # Disabled (0) or Enabled (1)
    "d9": {NAME: "display_mode"},  # Brightness: Off (0), Low (1), Medium (2), High (3)
    "da": {NAME: "ac_frequency"},  # 60 / 50 Hz
    "db": {NAME: "energy_saving_switch"},  # Disabled (0) or Enabled (1)
    "dc": {NAME: "light_mode"},  # Off (0), Low (1), Medium (2), High (3), Blinking (4)
    "dd": {NAME: "temp_unit_fahrenheit"},  # Celsius (0) or Fahrenheit (1)
    "de": {NAME: "display_switch"},  # Off (0) or On (1)
    "e5": {NAME: "ac_fast_charge_switch"},  # Off (0) or On (1)
    "f8": {
        BYTES: {
            "00": {
                NAME: "dc_12v_output_mode",  # Normal (1), Smart (2) - auto-off below 3W
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "01": {
                NAME: "ac_output_mode",  # Normal (1), Smart (2) - auto-off when not charging and low power
                TYPE: DeviceHexDataTypes.ui.value,
            },
        }
    },
    "fd": {NAME: "exp_1_type"},  # Expansion battery type identifier
    "fe": {NAME: "msg_timestamp"},  # Message timestamp
}

_A1780_0408 = {
    # F2000(P) state info
    TOPIC: "state_info",
    "a3": {NAME: "device_sn"},
    "a4": {NAME: "local_timestamp"},
    "a5": {NAME: "utc_timestamp"},
    "a6": {NAME: "battery_voltage?", FACTOR: 0.001},
    "a7": {NAME: "pv_voltage?", FACTOR: 0.001},
    "aa": {NAME: "ac_output_power_inverted?"},
    "ab": {NAME: "battery_power_signed?", FACTOR: -1},
    "ac": {NAME: "main_battery_soc"},  # in %
}

_A1782_0421 = (
    {
        # F3000 param info
        TOPIC: "param_info",
        "a2": {
            BYTES: {
                "01": {
                    NAME: "device_sn",
                    TYPE: DeviceHexDataTypes.str.value,
                },
                "20": {
                    NAME: "device_pn",
                    TYPE: DeviceHexDataTypes.str.value,
                },
            }
        },
        "a3": {
            BYTES: {
                "04": {
                    NAME: "ac_input_limit_max",  # Max supported charge limit, seems fix
                    TYPE: DeviceHexDataTypes.sile.value,
                },
                "07": {
                    NAME: "battery_soh?",
                    TYPE: DeviceHexDataTypes.ui.value,
                },
            }
        },
        "a4": {
            BYTES: {
                "00": {
                    NAME: "ac_output_timeout_seconds",  # disable (0), min:0, max: 86400, step 300
                    TYPE: DeviceHexDataTypes.var.value,
                    LENGTH: 4,
                },
                "04": {
                    NAME: "ac_input_limit",  # AC charge limit: 200-1800 W, step: 100
                    TYPE: DeviceHexDataTypes.sile.value,
                },
                "06": {
                    NAME: "ac_frequency",  # 60 / 50 Hz
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "07": {
                    NAME: "ac_output_mode",  # Normal (0), Smart (1) - auto-off below 14W
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "08": {
                    NAME: "dc_output_timeout_seconds",  # disable (0), min:0, max: 86400, step 300
                    TYPE: DeviceHexDataTypes.var.value,
                    LENGTH: 4,
                },
                "12": {
                    NAME: "dc_12v_output_mode",  # Normal (0), Smart (1) - auto-off below 3W
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "13": {
                    NAME: "device_timeout_minutes",  # 0 (Never), 30, 60, 120, 240, 360, 720, 1440
                    TYPE: DeviceHexDataTypes.sile.value,
                },
                "15": {
                    NAME: "display_timeout_seconds",  # 0 (Never), 10, 30, 60, 300, 1800
                    TYPE: DeviceHexDataTypes.sile.value,
                },
                "17": {
                    NAME: "display_mode",  # Low (1), Medium (2), High (3)
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "18": {
                    NAME: "light_mode",  # Off (0), Low (1), Mid (2), Bright (3)
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "20": {
                    NAME: "ac_fast_charge_switch?",  # Ultrafast Charge switch: Disabled (0) or Enabled (1)
                },
                "21": {
                    NAME: "display_switch",  # Off (0), On (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "22": {
                    NAME: "port_memory_switch",  # Output Port Memory switch: Disabled (0) or Enabled (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "26": {
                    NAME: "country_code",
                    TYPE: DeviceHexDataTypes.str.value,
                    LENGTH: 2,
                },
            }
        },
        "a5": {
            BYTES: {
                "00": {
                    NAME: "temperature",
                    SIGNED: True,
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "02": {
                    NAME: "battery_soc",
                    TYPE: DeviceHexDataTypes.ui.value,
                },
            }
        },
        "a6": {
            BYTES: {
                "00": {
                    NAME: "output_power_total",  # Output power total
                    TYPE: DeviceHexDataTypes.sile.value,
                },
                "02": {
                    NAME: "ac_input_power",  # Input power total charge
                    TYPE: DeviceHexDataTypes.sile.value,
                },
            },
        },
        "a7": {
            BYTES: {
                "00": {
                    NAME: "ac_output_power_switch",  # Off (0), On (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "01": {
                    NAME: "ac_output_power",  # AC Output power
                    TYPE: DeviceHexDataTypes.sile.value,
                },
            }
        },
        "a8": {
            BYTES: {
                "00": {
                    NAME: "pv_1_status",  # Low Voltage PV: Inactive (0), Active (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "01": {
                    NAME: "pv_1_power",
                    TYPE: DeviceHexDataTypes.sile.value,
                },
            }
        },
        "a9": {
            BYTES: {
                "00": {
                    NAME: "pv_2_status",  # High Voltage PV: Inactive (0), Active (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "01": {
                    NAME: "pv_2_power",
                    TYPE: DeviceHexDataTypes.sile.value,
                },
            }
        },
        "aa": {
            BYTES: {
                "00": {
                    NAME: "usbc_1_status",  # USB-C 1 status: Inactive (0), Discharging (1), Charging (2)
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "01": {
                    NAME: "usbc_1_power",
                    TYPE: DeviceHexDataTypes.sile.value,
                },
            }
        },
        "ab": {
            BYTES: {
                "00": {
                    NAME: "usbc_2_status",  # USB-C 2 status: Inactive (0), Discharging (1), Charging (2)
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "01": {
                    NAME: "usbc_2_power",
                    TYPE: DeviceHexDataTypes.sile.value,
                },
            }
        },
        "ae": {
            BYTES: {
                "00": {
                    NAME: "usba_1_status",  # USB-A 1 status: Inactive (0), Discharging (1), Charging (2)
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "01": {
                    NAME: "usba_1_power",
                    TYPE: DeviceHexDataTypes.sile.value,
                },
            }
        },
        "af": {
            BYTES: {
                "00": {
                    NAME: "usba_2_status",  # USB-A 2 status: Inactive (0), Discharging (1), Charging (2)
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "01": {
                    NAME: "usba_2_power",
                    TYPE: DeviceHexDataTypes.sile.value,
                },
            }
        },
        "b2": {
            BYTES: {
                "00": {
                    NAME: "dc_output_power_switch",  # Car Charger Output: Off (0), On (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "01": {
                    NAME: "dc_output_power",  # DC 12V output power when enabled
                    TYPE: DeviceHexDataTypes.sile.value,
                },
            }
        },
    }
    | {
        f"c{-1 + idx}": {
            BYTES: {
                # Expansion battery 1
                "00": {
                    NAME: f"exp_{idx}_sn",
                    TYPE: DeviceHexDataTypes.str.value,
                },
                "23": {
                    NAME: f"exp_{idx}_temperature",  # Temperature in °C (signed)
                    TYPE: DeviceHexDataTypes.ui.value,
                    SIGNED: True,
                },
                "25": {
                    NAME: f"exp_{idx}_soc",  # State of charge 0-100%
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "32": {
                    NAME: f"exp_{idx}_type",  # type identifier
                    TYPE: DeviceHexDataTypes.str.value,
                },
            }
        }
        for idx in range(1, 4)
    }
    | {
        "d9": {
            BYTES: {
                "03": {
                    NAME: "max_soc",  # max_soc: 80, 85, 90, 95, 100 % ?
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "04": {
                    NAME: "min_soc",  # min_soc: 1, 5, 10, 15, 20 % ?
                    TYPE: DeviceHexDataTypes.ui.value,
                },
            }
        },
        "fd": {NAME: "unknown_fd_timestamp"},
        "fe": {NAME: "msg_timestamp"},
    }
)

_A1782_0502 = {
    # F3000 state info with aggregated energies?
    TOPIC: "state_info",
    # "a2": {
    #     BYTES: {
    #         "00": {
    #             NAME: "energy_a2_00",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "02": {
    #             NAME: "energy_a2_02",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "04": {
    #             NAME: "energy_a2_04",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "06": {
    #             NAME: "energy_a2_06",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "08": {
    #             NAME: "energy_a2_08",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "10": {
    #             NAME: "energy_a2_10",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "12": {
    #             NAME: "energy_a2_12",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "14": {
    #             NAME: "energy_a2_14",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "16": {
    #             NAME: "energy_a2_16",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "18": {
    #             NAME: "energy_a2_18",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #     }
    # },
    # "a3": {
    #     BYTES: {
    #         "00": {
    #             NAME: "energy_a3_00",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "02": {
    #             NAME: "energy_a3_02",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "04": {
    #             NAME: "energy_a3_04",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "06": {
    #             NAME: "energy_a3_06",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "08": {
    #             NAME: "energy_a3_08",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "10": {
    #             NAME: "energy_a3_10",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #     }
    # },
    # "a4": {
    #     BYTES: {
    #         "00": {
    #             NAME: "energy_a4_00",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "02": {
    #             NAME: "energy_a4_02",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "04": {
    #             NAME: "energy_a4_04",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "06": {
    #             NAME: "energy_a4_06",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "08": {
    #             NAME: "energy_a4_08",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "10": {
    #             NAME: "energy_a4_10",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "12": {
    #             NAME: "energy_a4_12",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #     }
    # },
    # "a5": {
    #     BYTES: {
    #         "00": {
    #             NAME: "energy_a5_00",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "02": {
    #             NAME: "energy_a5_02",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "04": {
    #             NAME: "energy_a5_04",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "06": {
    #             NAME: "energy_a5_06",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "08": {
    #             NAME: "energy_a5_08",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "10": {
    #             NAME: "energy_a5_10",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "12": {
    #             NAME: "energy_a5_12",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "14": {
    #             NAME: "energy_a5_14",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "16": {
    #             NAME: "energy_a5_16",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #     }
    # },
    # "a6": {
    #     BYTES: {
    #         "00": {
    #             NAME: "energy_a6_00",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "02": {
    #             NAME: "energy_a6_02",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "04": {
    #             NAME: "energy_a6_04",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "06": {
    #             NAME: "energy_a6_06",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "08": {
    #             NAME: "energy_a6_08",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "10": {
    #             NAME: "energy_a6_10",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "12": {
    #             NAME: "energy_a6_12",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "14": {
    #             NAME: "energy_a6_14",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #         "16": {
    #             NAME: "energy_a6_16",
    #             TYPE: DeviceHexDataTypes.sile.value,
    #             SIGNED: False,
    #         },
    #     }
    # },
    "fd": {NAME: "local_timestamp"},
    "fe": {NAME: "msg_timestamp"},
}

_A1790_0405 = {
    # F3800 param info
    TOPIC: "param_info",
    "a2": {
        NAME: "ac_output_timeout_seconds"
    },  # Active AC auto-off countdown in seconds
    "a3": {
        NAME: "dc_output_timeout_seconds"
    },  # Active DC auto-off countdown in seconds
    "a4": {NAME: "remaining_time_hours", FACTOR: 0.1, SIGNED: False},  # In hours
    "a5": {NAME: "ac_input_power"},
    "a6": {NAME: "ac_output_power"},
    "a7": {NAME: "usbc_1_power"},
    "a8": {NAME: "usbc_2_power"},
    "a9": {NAME: "usbc_3_power"},
    "aa": {NAME: "usba_1_power"},
    "ab": {NAME: "usba_2_power"},
    "ac": {NAME: "dc_12v_1_power"},
    "ad": {NAME: "battery_soc"},  # Total SOC of main + Exp batteries?
    "ae": {NAME: "photovoltaic_power"},  # Total solar input
    "af": {NAME: "pv_1_power"},
    "b0": {NAME: "pv_2_power"},
    "b1": {NAME: "bat_charge_power"},  # Total charging (AC + Solar)
    "b2": {NAME: "output_power_total"},  # Combined AC DC output power
    "b4": {NAME: "bat_discharge_power?"},
    "b5": {NAME: "sw_version"},  # Main firmware version
    "ba": {NAME: "sw_expansion"},  # Expansion firmware version
    "bb": {NAME: "sw_controller"},
    "bc": {
        NAME: "ac_output_power_switch"
    },  # AC output switch: Disabled (0) or Enabled (1)
    "bd": {
        NAME: "charging_status",  # Publishes the raw integer value (0-3): Inactive (0), Solar (1), AC Input (2), Both (3)
    },
    "be": {NAME: "temperature", SIGNED: True},  # In Celsius
    "bf": {NAME: "battery_status"},  # 0=standby, 1=discharge, 2=Charge
    "c0": {NAME: "main_battery_soc"},  # Main battery SOC?
    "c1": {NAME: "battery_soh"},
    "c2": {NAME: "usbc_1_status"},
    "c3": {NAME: "usbc_2_status"},
    "c4": {NAME: "usbc_3_status"},
    "c5": {NAME: "usba_1_status"},
    "c6": {NAME: "usba_2_status"},
    "c7": {NAME: "dc_12v_1_status"},
    "cc": {NAME: "device_sn"},
    "cd": {NAME: "ac_input_limit"},  # AC charge limit: 200-1800 W, step: 100
    "ce": {
        NAME: "device_timeout_minutes"
    },  # Device auto-off timeout (minutes): 0 (Never), 30, 60, 120, 240, 360, 720, 1440
    "cf": {NAME: "display_timeout_seconds"},  # User Setting (in seconds)
    "d3": {NAME: "ac_output_power_switch_dup?"},  # Duplicate of bc?
    "d4": {
        NAME: "dc_output_power_switch"
    },  # 12V DC output switch: Disabled (0) or Enabled (1)
    "d5": {
        NAME: "display_mode"
    },  # Display brightness: Off (0), Low (1), Medium (2), High (3)
    "d6": {NAME: "ac_frequency"},  # 60 / 50 Hz
    "d8": {
        NAME: "temp_unit_fahrenheit"
    },  # Temperature unit: Celsius (0) or Fahrenheit (1)
    "d9": {
        NAME: "light_mode"
    },  # LED light mode: Off (0), Low (1), Medium (2), High (3), Blinking (4)
    "e6": {NAME: "ac_input_limit_max"},  # Maximum value for control
    "f6": {
        # sile type that contains 2 chars
        BYTES: {
            "00": {
                NAME: "country_code",
                TYPE: DeviceHexDataTypes.str.value,
                LENGTH: 2,
            },  # Value 21333 ("US")
        }
    },
    "f7": {
        NAME: "port_memory_switch"
    },  # Port Memory switch: Disabled (0) or Enabled (1)
    "fd": {NAME: "exp_1_type"},  # Expansion battery type identifier
    "fe": {NAME: "msg_timestamp"},
}

_A1790_040a = (
    {
        # F3800 param info
        TOPIC: "param_info",
        "a2": {NAME: "expansion_packs"},
        "a3": {NAME: "expansion_soc"},  # total of all expansions
    }
    | {
        f"a{3 + idx}": {
            BYTES: {
                "00": {
                    NAME: f"exp_{idx}_sn",
                    LENGTH: 16,
                    TYPE: DeviceHexDataTypes.str.value,
                },
                "19": {
                    NAME: f"exp_{idx}_temperature",
                    TYPE: DeviceHexDataTypes.ui.value,
                    SIGNED: True,
                },
                "21": {
                    NAME: f"exp_{idx}_soc",
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "22": {
                    NAME: f"exp_{idx}_soh",
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "28": {
                    NAME: f"exp_{idx}_type",
                    LENGTH: 10,
                    TYPE: DeviceHexDataTypes.str.value,
                },
            }
        }
        for idx in range(1, 7)
    }
    | {
        "fe": {NAME: "msg_timestamp"},
    }
)

_A1790_0410 = {
    # F3800 param info
    TOPIC: "param_info",
    "a2": {
        BYTES: {
            "00": {
                NAME: "power_panel_sn",
                LENGTH: 16,
                TYPE: DeviceHexDataTypes.str.value,
            },
        }
    },
    "a3": {
        BYTES: {
            "00": {
                NAME: "device_1_sn",
                LENGTH: 16,
                TYPE: DeviceHexDataTypes.str.value,
            },
            "19": {
                NAME: "device_1_soc",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "20": {
                NAME: "device_1_temperature",
                SIGNED: True,
                TYPE: DeviceHexDataTypes.ui.value,
            },
        }
    },
    "a4": {
        BYTES: {
            "00": {
                NAME: "device_2_sn",
                LENGTH: 16,
                TYPE: DeviceHexDataTypes.str.value,
            },
            "19": {
                NAME: "device_2_soc",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "20": {
                NAME: "device_2_temperature",
                SIGNED: True,
                TYPE: DeviceHexDataTypes.ui.value,
            },
        }
    },
    "a5": {NAME: "device_1_pn"},
    "a6": {NAME: "device_2_pn"},
    "fe": {NAME: "msg_timestamp"},
}

_A1790_0804 = {
    # F3800 param info
    TOPIC: "param_info",
}

_0407 = {
    # Network message
    TOPIC: "state_info",
    "a2": {NAME: "device_sn"},
    "a3": {NAME: "wifi_name"},
    "a4": {NAME: "wifi_signal"},
}

_PPS_0407 = _0407 | {
    # PPS network message
    "a6": {NAME: "ac_input_limit"},
}

_A17C0_0407 = _0407 | {
    # Solarbank network message
    "a5": {NAME: "charging_status"},
}

_A17C1_0405 = {
    # Solarbank 2 param info
    TOPIC: "param_info",
    "a2": {NAME: "device_sn"},
    "a3": {NAME: "main_battery_soc"},  # controller battery only
    "a5": {NAME: "error_code"},
    "a6": {NAME: "sw_version", "values": 4},
    "a7": {NAME: "sw_controller?", "values": 4},
    "a8": {NAME: "sw_expansion", "values": 4},
    "a9": {NAME: "temp_unit_fahrenheit"},
    "aa": {NAME: "temperature", SIGNED: True},
    "ab": {NAME: "photovoltaic_power", FACTOR: 0.1},
    "ac": {NAME: "ac_output_power", FACTOR: 0.1},
    "ad": {NAME: "battery_soc"},  # controller + expansions avg
    "b0": {NAME: "bat_charge_power", FACTOR: 0.01},
    "b1": {NAME: "pv_yield", FACTOR: 0.0001},
    "b2": {NAME: "charged_energy", FACTOR: 0.00001},
    "b3": {NAME: "output_energy", FACTOR: 0.0001},
    "b4": {NAME: "min_soc"},
    "b5": {NAME: "lowpower_input_data"},
    "b6": {NAME: "active_charge_soc"},
    "b7": {NAME: "bat_discharge_power", FACTOR: 0.01},
    "bc": {NAME: "grid_to_home_power", FACTOR: 0.1},
    "bd": {NAME: "pv_to_grid_power", FACTOR: 0.1},
    "be": {NAME: "grid_import_energy", FACTOR: 0.0001},
    "bf": {NAME: "grid_export_energy", FACTOR: 0.0001},
    "c2": {NAME: "max_load"},
    "c4": {NAME: "home_demand", FACTOR: 0.1},
    "c6": {NAME: "usage_mode"},
    "c7": {NAME: "home_load_preset"},
    "c8": {NAME: "ac_socket_power", FACTOR: 0.1},
    "c9": {NAME: "consumed_energy", FACTOR: 0.0001},
    "ca": {NAME: "pv_1_power", FACTOR: 0.1},
    "cb": {NAME: "pv_2_power", FACTOR: 0.1},
    "cc": {NAME: "pv_3_power", FACTOR: 0.1},
    "cd": {NAME: "pv_4_power", FACTOR: 0.1},
    "d2": {NAME: "light_mode"},  # Normal mode (0) or Mood mode (1)
    "d3": {NAME: "output_power", FACTOR: 0.1},
    "e0": {NAME: "grid_status"},  # Grid OK (1), No grid (6), Grid connecting (3)
    "e1": {NAME: "light_off_switch"},  # Light on (0), Light off (1)
    "e8": {NAME: "battery_heating"},  # Not heating (1), heating (3)
    "eb": {NAME: "max_soc"},
    "fb": {
        BYTES: {
            "00": [{NAME: "grid_export_disabled", MASK: 0x01}],
        }
    },
    "fe": {NAME: "msg_timestamp"},
}

_A17C1_0408 = {
    # Solarbank 2 state info
    TOPIC: "state_info",
    "a2": {NAME: "device_sn"},
    "a3": {NAME: "local_timestamp"},
    "a4": {NAME: "utc_timestamp"},
    "a8": {NAME: "charging_status"},
    "ac": {NAME: "ac_output_power", FACTOR: 0.1},
    "b0": {NAME: "battery_soc"},
    "b1": {NAME: "pv_yield", FACTOR: 0.0001},
    "b2": {NAME: "charged_energy", FACTOR: 0.00001},
    "b3": {NAME: "output_energy", FACTOR: 0.0001},
    "b4": {NAME: "discharged_energy", FACTOR: 0.00001},
    "b6": {NAME: "temperature", SIGNED: True},
    "b7": {NAME: "usage_mode?"},
    "b8": {NAME: "home_load_preset"},
    "bb": {NAME: "consumed_energy", FACTOR: 0.0001},
    "bc": {NAME: "bat_discharge_power", FACTOR: 0.01},
    "c0": {NAME: "discharge_power?"},
    "c3": {NAME: "grid_import_energy", FACTOR: 0.0001},
    "c4": {NAME: "grid_export_energy", FACTOR: 0.0001},
    "c8": {NAME: "home_demand", FACTOR: 0.1},
    "ce": {NAME: "pv_1_power"},
    "cf": {NAME: "pv_2_power"},
    "d0": {NAME: "pv_3_power"},
    "d1": {NAME: "pv_4_power"},
    "e8": {NAME: "max_soc"},
    "fb": {
        BYTES: {
            "00": [{NAME: "grid_export_disabled", MASK: 0x01}],
        }
    },
}

_A17C1_040a = (
    {
        # Solarbank 2 Expansion data
        TOPIC: "param_info",
        "a2": {NAME: "expansion_packs"},
        "a3": {NAME: "main_battery_soc"},  # main battery SOC
    }
    | {
        f"a{3 + idx}": {
            BYTES: {
                "00": {
                    NAME: f"exp_{idx}_controller_sn?",
                    LENGTH: 17,
                    TYPE: DeviceHexDataTypes.str.value,
                },
                "17": {
                    NAME: "separator?",
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "18": {
                    NAME: f"exp_{idx}_position?",
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "19": {
                    NAME: f"exp_{idx}_temperature",
                    TYPE: DeviceHexDataTypes.ui.value,
                    SIGNED: True,
                },
                "20": {
                    NAME: "separator?",
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "21": {
                    NAME: f"exp_{idx}_soc",
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "22": {
                    NAME: f"exp_{idx}_soh",
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "27": {
                    NAME: f"exp_{idx}_sn",
                    LENGTH: 17,
                    TYPE: DeviceHexDataTypes.str.value,
                },
                "44": {
                    NAME: "end_marker?",
                    TYPE: DeviceHexDataTypes.ui.value,
                },
            }
        }
        for idx in range(1, 6)
    }
    | {
        "fe": {NAME: "msg_timestamp"},
    }
)

_A17C5_0405 = {
    # Solarbank 3 param info
    TOPIC: "param_info",
    "a2": {NAME: "device_sn"},
    "a3": {NAME: "main_battery_soc"},
    "a4": {NAME: "battery_status"},  # 0: Standby; ?: Discharging; 2: Charging;
    "a5": {NAME: "temperature", SIGNED: True},
    "a6": {NAME: "battery_soc"},
    "a7": {NAME: "sw_version", "values": 4},
    "a8": {NAME: "sw_controller?", "values": 4},
    "a9": {NAME: "sw_expansion", "values": 4},
    "ab": {NAME: "photovoltaic_power"},
    "ac": {NAME: "battery_power_signed"},
    "ad": {NAME: "output_power"},
    "ae": {NAME: "ac_output_power_signed"},
    "b0": {NAME: "pv_yield"},
    "b1": {NAME: "charged_energy"},
    "b2": {NAME: "discharged_energy"},
    "b3": {NAME: "output_energy"},
    "b4": {NAME: "consumed_energy"},
    "b5": {NAME: "min_soc"},
    "b7": {NAME: "active_charge_soc"},
    "b8": {NAME: "usage_mode"},
    "b9": {NAME: "home_load_preset"},
    "ba": {
        BYTES: {
            "00": [
                {
                    NAME: "light_mode",
                    MASK: 0x40,
                },  # Normal mode (0) or Mood mode (1)
                {
                    NAME: "light_off_switch",
                    MASK: 0x20,
                },  # Enable (0) or disable (1) LEDs
                {
                    NAME: "ac_socket_switch",
                    MASK: 0x08,
                },  # Disable (0) or enable (1) AC socket
                {
                    NAME: "temp_unit_fahrenheit",
                    MASK: 0x01,
                },  # Toggle °C (0) or F (1) unit, this does not change temperature value itself
            ],
        }
    },
    "bb": {NAME: "heating_power"},
    "bc": {NAME: "grid_to_battery_power"},
    "bd": {NAME: "max_load"},
    "be": {NAME: "max_load_legal"},
    "bf": {NAME: "backup_start_timestamp", SIGNED: False},
    "c0": {NAME: "backup_end_timestamp", SIGNED: False},
    "c2": {NAME: "photovoltaic_power?"},
    "c4": {NAME: "grid_power_signed"},
    "c5": {NAME: "home_demand"},
    "c6": {NAME: "pv_1_power"},
    "c7": {NAME: "pv_2_power"},
    "c8": {NAME: "pv_3_power"},
    "c9": {NAME: "pv_4_power"},
    "cb": {NAME: "expansion_packs"},
    "d4": {
        NAME: "device_timeout_minutes",
        FACTOR: 30,
    },  # timeout in 30 min chunks: 0, 30, 60, 120, 240, 360, 720, 1440 minutes
    "d5": {NAME: "pv_limit"},
    "d6": {NAME: "ac_input_limit"},
    "d8": {
        BYTES: {
            "00": {
                NAME: "max_soc",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "01": {
                NAME: "backup_soc",
                TYPE: DeviceHexDataTypes.ui.value,
            },
        },
    },
    "fb": {
        BYTES: {
            "00": [{NAME: "grid_export_disabled", MASK: 0x01}],
        }
    },
    "fe": {NAME: "msg_timestamp"},
}

_A17C5_0408 = {
    # Solarbank 3 state info
    TOPIC: "state_info",
    "a2": {NAME: "device_sn"},
    "a3": {NAME: "local_timestamp"},
    "a4": {NAME: "utc_timestamp"},
    "a5": {NAME: "battery_soc_calc", FACTOR: 0.1},
    "a6": {NAME: "battery_soh", FACTOR: 0.1},
    "a7": {NAME: "battery_soc"},
    "a9": {NAME: "usage_mode"},
    "a8": {NAME: "charging_status?"},
    "aa": {NAME: "home_load_preset"},
    "ab": {NAME: "photovoltaic_power"},
    "ac": {NAME: "pv_yield"},
    # "ad": {NAME: "pv_1_energy?"},
    # "ae": {NAME: "pv_2_energy?"},
    # "af": {NAME: "pv_3_energy?"},
    # "b0": {NAME: "pv_4_energy?"},
    "b1": {NAME: "home_demand"},
    "b2": {NAME: "home_consumption"},
    "b6": {NAME: "battery_power_signed?"},
    "b7": {NAME: "charged_energy"},
    "b8": {NAME: "discharged_energy"},
    "bd": {NAME: "grid_power_signed?"},
    "be": {NAME: "grid_import_energy"},
    "bf": {NAME: "grid_export_energy"},
    "c7": {NAME: "pv_1_power"},
    "c8": {NAME: "pv_2_power"},
    "c9": {NAME: "pv_3_power"},
    "ca": {NAME: "pv_4_power"},
    "cc": {NAME: "temperature", SIGNED: True},
    "d3": {NAME: "ac_output_power"},
    "d5": {NAME: "grid_to_home_power"},
    "d6": {NAME: "timestamp_1?"},
    "dc": {NAME: "max_load"},
    "dd": {NAME: "ac_input_limit"},
    # "de": {NAME: "output_energy"},
    "e0": {
        NAME: "active_discharge_soc"
    },  # active discharge minimum, may be backup soc level
    "e6": {NAME: "pv_limit"},
    "e7": {NAME: "ac_input_limit"},
    "e8": {NAME: "max_soc"},
}

_A17C5_040a = (
    _A17C1_040a
    | {
        # Additional/different Solarbank 3 Expansion data?
    }
)

_AE103_0404 = {
    # Solarbank 4 Expansion data
    TOPIC: "state_info",
    "a2": {NAME: "expansion_packs"},
} | {
    f"a{2 + idx}": {
        BYTES: {
            "00": {
                NAME: f"exp_{idx}_sn",
                LENGTH: 17,
                TYPE: DeviceHexDataTypes.str.value,
            },
            "17": {
                NAME: f"exp_{idx}_temperature",
                TYPE: DeviceHexDataTypes.ui.value,
                SIGNED: True,
            },
            "20": {
                NAME: f"exp_{idx}_soc",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "27": {
                NAME: f"exp_{idx}_voltage?",
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.1,
                SIGNED: False,
            },
            "29": {
                NAME: f"exp_{idx}_unknown_29?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "30": {
                NAME: f"exp_{idx}_unknown_power_30?",
                TYPE: DeviceHexDataTypes.sile.value,
            },
        }
    }
    for idx in range(1, 6)
}

_AE103_0405 = {
    # Solarbank 4 param info
    TOPIC: "param_info",
    "a2": {NAME: "device_sn"},
    "a3": {NAME: "main_battery_soc"},
    "a4": {NAME: "battery_status"},  # 0: Standby; ?: Discharging; 2: Charging;
    "a5": {NAME: "temperature", SIGNED: True},
    # "a6": {NAME: "battery_soc"},
    "a7": {NAME: "sw_version", "values": 4},
    "a8": {NAME: "sw_controller?", "values": 4},
    "a9": {NAME: "sw_expansion", "values": 4},
    "ab": {NAME: "photovoltaic_power"},
    "ac": {NAME: "battery_power_signed"},
    "ad": {NAME: "output_power"},
    "ae": {NAME: "ac_output_power_signed"},
    "b0": {NAME: "pv_yield"},
    "b1": {NAME: "charged_energy?"},
    "b2": {NAME: "discharged_energy?"},
    "b3": {NAME: "output_energy?"},
    "b4": {NAME: "grid_export_energy?"},
    "b5": {
        BYTES: {
            "00": {
                NAME: "min_soc?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "01": {
                NAME: "backup_soc?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "02": {
                NAME: "max_soc?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
        },
    },
    "b8": {NAME: "usage_mode"},
    "b9": {NAME: "home_load_preset"},
    "ba": {
        BYTES: {
            "00": [
                {
                    NAME: "light_mode",
                    MASK: 0x40,
                },  # Normal mode (0) or Mood mode (1)
                {
                    NAME: "light_off_switch",
                    MASK: 0x20,
                },  # Enable (0) or disable (1) LEDs
                {
                    NAME: "ac_socket_switch",
                    MASK: 0x08,
                },  # Disable (0) or enable (1) AC socket
                {
                    NAME: "temp_unit_fahrenheit",
                    MASK: 0x01,
                },  # Toggle °C (0) or F (1) unit, this does not change temperature value itself
            ],
        }
    },
    "bb": {NAME: "heating_power"},
    "bc": {NAME: "grid_to_battery_power"},
    "bd": {NAME: "max_load"},
    "be": {NAME: "max_load_legal"},
    "c4": {NAME: "grid_power_signed"},
    "c5": {NAME: "home_demand"},
    "c6": {NAME: "pv_1_power"},
    "c7": {NAME: "pv_2_power"},
    "c8": {NAME: "pv_3_power"},
    "c9": {NAME: "pv_4_power"},
    "cb": {NAME: "expansion_packs"},
    "f9": {
        BYTES: {
            "00": {NAME: "monitor_device", TYPE: DeviceHexDataTypes.str.value},
        },
    },
    "fb": {
        BYTES: {
            "00": [{NAME: "grid_export_disabled", MASK: 0x01}],
        }
    },
    "fe": {NAME: "msg_timestamp"},
}

_AE103_0408 = {
    # Solarbank 4 state info
    TOPIC: "state_info",
    "a2": {NAME: "device_sn"},
    "a3": {NAME: "local_timestamp"},
    "a4": {NAME: "utc_timestamp"},
    "a7": {NAME: "battery_soc"},
    "a9": {NAME: "usage_mode"},
    "a8": {NAME: "charging_status?"},
    "ab": {NAME: "photovoltaic_power"},
    "ac": {NAME: "unknown_energy_0408_ac"},
    "ad": {NAME: "unknown_energy_0408_ad"},
    "ae": {NAME: "unknown_energy_0408_ae"},
    # "ad": {NAME: "pv_1_energy?"},
    # "ae": {NAME: "pv_2_energy?"},
    # "af": {NAME: "pv_3_energy?"},
    # "b0": {NAME: "pv_4_energy?"},
    "b1": {NAME: "home_demand?"},
    "b2": {NAME: "home_consumption?"},
    "b6": {NAME: "battery_power_signed?"},
    "b7": {NAME: "charged_energy?"},
    "b8": {NAME: "discharged_energy?"},
    "bd": {NAME: "grid_power_signed"},
    "be": {NAME: "grid_import_energy?"},
    "bf": {NAME: "grid_export_energy?"},
    "c8": {NAME: "unknown_energy_0408_c8"},
    "c9": {NAME: "unknown_energy_0408_c9"},
    "cc": {NAME: "temperature", SIGNED: True},
    "ce": {NAME: "min_soc"},
    "cf": {NAME: "max_soc"},
    "d3": {NAME: "ac_output_power"},
    "d6": {NAME: "timestamp_1?"},
    "dc": {NAME: "max_load"},
    "e0": {
        NAME: "active_discharge_soc"
    },  # active discharge minimum, may be backup soc level
    "ef": {NAME: "pv_power_3rd_party"},
    "f9": {
        BYTES: {
            "00": {NAME: "monitor_device", TYPE: DeviceHexDataTypes.str.value},
        },
    },
}

_AE103_040a = (
    {
        # Solarbank 4 Expansion data
        TOPIC: "param_info",
        "a2": {NAME: "expansion_packs"},
        "a3": {NAME: "main_battery_soc"},  # main battery SOC
    }
    | {
        f"a{3 + idx}": {
            BYTES: {
                "00": {
                    NAME: f"exp_{idx}_sn",
                    LENGTH: 17,
                    TYPE: DeviceHexDataTypes.str.value,
                },
                "18": {
                    NAME: "separator?",
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "21": {
                    NAME: f"exp_{idx}_position?",
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "24": {
                    NAME: f"exp_{idx}_unknown_power_24?",
                    TYPE: DeviceHexDataTypes.sile.value,
                },
                "26": {
                    NAME: f"exp_{idx}_temperature",
                    TYPE: DeviceHexDataTypes.ui.value,
                    SIGNED: True,
                },
                "28": {
                    NAME: f"exp_{idx}_soc",
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "29": {
                    NAME: f"exp_{idx}_soh",
                    TYPE: DeviceHexDataTypes.ui.value,
                },
            }
        }
        for idx in range(1, 6)
    }
    | {
        "fe": {NAME: "msg_timestamp"},
    }
)

_A17E1_040a = (
    {
        # Home Backup System E10 Expansion data
        TOPIC: "param_info",
        "a2": {NAME: "expansion_packs"},
        "a3": {NAME: "battery_soc"},  # battery SOC
    }
    | {
        f"a{3 + idx}": {
            BYTES: {
                "00": {
                    NAME: f"exp_{idx}_sn",
                    LENGTH: 17,
                    TYPE: DeviceHexDataTypes.str.value,
                },
                "17": {
                    NAME: "separator?",
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "21": {
                    NAME: "separator?",
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "25": {
                    NAME: f"exp_{idx}_id",  # position?
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "26": {
                    NAME: f"exp_{idx}_temperature",
                    TYPE: DeviceHexDataTypes.ui.value,
                    SIGNED: True,
                },
                "27": {  # 0:idle, 1:charging, 2:discharging
                    NAME: f"exp_{idx}_battery_status",
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "28": {
                    NAME: f"exp_{idx}_soc",
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "29": {
                    NAME: f"exp_{idx}_soh",
                    TYPE: DeviceHexDataTypes.ui.value,
                },
            }
        }
        for idx in range(1, 6)
    }
    | {
        "fe": {NAME: "msg_timestamp"},
    }
)

_AX170_0405 = (
    {
        # AX170 Power dock for home backup systems A17E1
        TOPIC: "param_info",
        "a2": {NAME: "device_sn"},
        "a6": {NAME: "battery_soc_total"},  # Average SOC of all devices in system
        "a7": {NAME: "sw_version", "values": 4},
        "a8": {NAME: "sw_controller", "values": 4},
        "a9": {NAME: "hw_version", "values": 4},
        "ab": {
            NAME: "pv_power_total"
        },  # Total PV power from all devices in system? Only verified with 1 E10 Module
        "ac": {
            NAME: "battery_power_signed_total"
        },  # Power draw from battery. Negative is discharging, positive is charging.
        "b0": {NAME: "pv_yield"},
        "b1": {NAME: "charged_energy"},
        "b2": {NAME: "discharged_energy"},
        "b4": {NAME: "grid_import_energy"},
        "b5": {
            NAME: "backup_soc"
        },  # Minimum Self Consumption reserve %, Not overall reserve. Battery will stay above this level, unless grid fault.
        "b7": {
            NAME: "max_soc?"
        },  # Statix at 100, Maybe battery health, but from which device??
        "b8": {NAME: "usage_mode"},  # 2:?, 4:backup_charge, 5:?, 9:?, 10:?
        "b9": {
            NAME: "main_breaker_limit?"
        },  # Static, maybe installation setting, It's 200 on tests, so its a good chance its the 200AMP?
        "bf": {NAME: "backup_start_timestamp", SIGNED: False},
        "c0": {NAME: "backup_end_timestamp", SIGNED: False},
        "c2": {NAME: "input_power_total"},  # PV + Grid
        "c3": {
            NAME: "use_time_band?"
        },  # use_time_band: 1=peak, 2=mid-peak, 3=off-peak, 4=super-off-peak
        "c4": {NAME: "grid_power_signed"},  # positive=import, negative=export
        "c5": {NAME: "home_demand_total"},
        "cc": {
            BYTES: {
                "00": {
                    NAME: "powerdock_state_code_1?",
                    TYPE: DeviceHexDataTypes.ui.value,
                },  # Not very reliable, not sure what the setting is exactly.
                "01": {
                    NAME: "powerdock_charging_status?",
                    TYPE: DeviceHexDataTypes.ui.value,
                },  # 32 idle, 48 = charging, 64 = discharging, Is this only a upper half byte usage?
            }
        },
        "cd": {NAME: "home_demand_circuit_total"},  # Does not include other load
        "ce": {NAME: "generator_plug_status"},
        "d4": {NAME: "pv_power_3rd_party"},  # Power from external solar to home?
        "d6": {NAME: "generator_power"},  # Power from external DC generator
        "d8": {NAME: "voltage_l1l2"},  # fluctuates around 220
        "dd": {NAME: "display_timeout_seconds"},
        "de": {
            NAME: "max_load_limit_total?"
        },  # shows 4800 in monitoring. Not sure what this is.
        # for e3 decoding see https://github.com/thomluther/anker-solix-api/issues/312#issuecomment-4691257976
        "e3": {
            BYTES: {
                "00": {
                    NAME: "low_backup_soc",  # SOC when low prio circuits stop during backup discharge
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "01": {
                    NAME: "circuit_setup",
                    TYPE: DeviceHexDataTypes.bin.value,
                    LENGTH: 36,
                    STATE_CONVERTER: lambda value, state, cache: (
                        convert_circuit_setup(value) if value is not None else state
                    ),
                },
            }
        },
        "e4": {
            BYTES: {
                f"{0 + (idx - 1) * 4:02d}": {
                    NAME: f"home_demand_circuit_{idx:02d}",
                    TYPE: DeviceHexDataTypes.sfle.value,
                }
                for idx in range(1, 13)
            }
            | {
                "48": {
                    NAME: "home_demand_other",
                    TYPE: DeviceHexDataTypes.sfle.value,
                }
            }
        },
    }
    | {
        f"{0xE7 + idx:02x}": {
            BYTES: {
                "00": {
                    NAME: f"device_{idx}_pn",
                    TYPE: DeviceHexDataTypes.str.value,
                },
                "11": {
                    NAME: f"device_{idx}_sn",
                    TYPE: DeviceHexDataTypes.str.value,
                },
                "37": {
                    NAME: f"device_{idx}_temperature",
                    SIGNED: True,
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "41": {
                    NAME: f"device_{idx}_soc",
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "42": {
                    NAME: f"device_{idx}_pv_1_power",
                    TYPE: DeviceHexDataTypes.sile.value,
                },
                "46": {
                    NAME: f"device_{idx}_pv_2_power",
                    TYPE: DeviceHexDataTypes.sile.value,
                },
                "58": {
                    NAME: f"device_{idx}_battery_power",
                    TYPE: DeviceHexDataTypes.sile.value,
                },
                "66": {
                    NAME: f"device_{idx}_exp_packs",
                    TYPE: DeviceHexDataTypes.ui.value,
                },
            }
        }
        for idx in range(1, 7)
    }
    | {
        "fd": {
            NAME: "high_backup_soc"
        },  # SOC when low prio circuits start during backup discharge
        "fe": {NAME: "msg_timestamp"},
    }
)

_AX170_0408 = {
    # AX170 Power dock for home backup systems A17E1
    TOPIC: "param_info",
    "a2": {NAME: "device_sn"},
    "a3": {NAME: "local_timestamp"},
    "a4": {NAME: "utc_timestamp"},
    "a7": {NAME: "battery_soc_total"},  # Average SOC of all devices in system
    "ad": {NAME: "pv_yield_today?"},
    "df": {NAME: "pv_yield_today_df?"},
    "b1": {NAME: "tbd_power_total_b1?"},
    "b3": {NAME: "input_energy_today?"},
    "b4": {NAME: "discharged_energy_today?"},
    "b6": {
        NAME: "battery_power_signed_total"
    },  # Power draw from battery. Negative is discharging, positive is charging.
    "ba": {NAME: "discharged_energy_today_ba?"},
    "c0": {NAME: "grid_import_energy_today_c0?"},
    "d6": {NAME: "timestamp_0408_d6?"},
    "ea": {NAME: "pv_yield_today_ea?"},
    "eb": {NAME: "pv_yield_today_eb?"},
    "ee": {NAME: "pv_power_total?"},  # same as 0405 ab,c2
    "f3": {NAME: "pv_yield_today_f3?"},
    "f5": {
        BYTES: {
            f"{0 + (idx - 1) * 4:02d}": {
                NAME: f"circuit_{idx:02d}_energy_today",
                TYPE: DeviceHexDataTypes.sfle.value,
            }
            for idx in range(1, 13)
        }
        | {
            "48": {
                NAME: "other_energy_today",
                TYPE: DeviceHexDataTypes.sfle.value,
            },
        }
    },
    "f6": {
        BYTES: {
            f"{0 + (idx - 1) * 4:02d}": {
                NAME: f"home_demand_circuit_{idx:02d}",
                TYPE: DeviceHexDataTypes.sfle.value,
            }
            for idx in range(1, 13)
        }
        | {
            "48": {
                NAME: "home_demand_other",
                TYPE: DeviceHexDataTypes.sfle.value,
            },
        }
    },
} | {
    f"{0xF6 + idx:02x}": {
        BYTES: {
            "00": {
                NAME: f"device_{idx}_pn",
                TYPE: DeviceHexDataTypes.str.value,
            },
            "11": {
                NAME: f"device_{idx}_sn",
                TYPE: DeviceHexDataTypes.str.value,
            },
            "29": {
                NAME: f"device_{idx}_soc",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "34": {
                NAME: f"device_{idx}_ac_output_power_signed",
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "42": {
                NAME: f"device_{idx}_pv_power?",
                TYPE: DeviceHexDataTypes.sfle.value,
            },
        },
    }
    for idx in range(1, 5)
}

_A7320_0405 = {
    # SOLIX Smart Generator 5500 runtime message.
    TOPIC: "param_info",
    "a2": {NAME: "device_sn"},
    "a3": {NAME: "paired_device_sn"},  # paired E10 (A17E1) SN
    "a4": {NAME: "tbd_0405_a4?"},
    "a5": {
        BYTES: {
            "00": {
                NAME: "tbd_0405_a5_u16_01?",
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "02": {
                NAME: "ac_dc_mode",  # 3 = AC, 1 = DC
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "04": {
                NAME: "tbd_0405_a5_u16_03?",
                TYPE: DeviceHexDataTypes.sile.value,
            },
        }
    },
    "a7": {NAME: "sw_version?", "values": 4},
    "aa": {
        BYTES: {
            "00": {
                NAME: "tbd_0405_aa_u32_01?",
                TYPE: DeviceHexDataTypes.var.value,
            },
            "04": {
                NAME: "tbd_0405_aa_u32_02?",
                TYPE: DeviceHexDataTypes.var.value,
            },
            "08": {
                NAME: "tbd_0405_aa_u32_03?",
                TYPE: DeviceHexDataTypes.var.value,
            },
            "12": {
                NAME: "tbd_0405_aa_u32_04?",
                TYPE: DeviceHexDataTypes.var.value,
            },
            "16": {
                NAME: "tbd_0405_aa_u16_05?",
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "18": {
                NAME: "tbd_0405_aa_u16_06?",
                TYPE: DeviceHexDataTypes.sile.value,
            },
        }
    },
    "ac": {
        BYTES: {
            "40": {
                NAME: "tbd_0405_ac_u32_01?",
                TYPE: DeviceHexDataTypes.var.value,
            },
            "44": {
                NAME: "lpg_remaining_percent",
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "48": {
                NAME: "tbd_0405_ac_u32_03?",
                TYPE: DeviceHexDataTypes.var.value,
            },
            "52": {
                NAME: "lpg_remaining_lb",
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.1,  # lb
            },
            "56": {
                NAME: "lpg_full_lb",
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.1,  # 100 % lb
            },
        }
    },
    "ae": {
        BYTES: {
            "00": {
                NAME: "tbd_0405_ae_u16_01?",
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "02": {
                NAME: "tbd_0405_ae_u16_02?",
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "04": {
                NAME: "tbd_0405_ae_u16_03?",
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "06": {
                NAME: "tbd_0405_ae_u16_04?",
                TYPE: DeviceHexDataTypes.sile.value,
            },
        }
    },
    "af": {NAME: "tbd_0405_af?"},
    "b0": {NAME: "tbd_0405_b0?"},
    "b2": {NAME: "tbd_0405_b2?"},
    "b3": {NAME: "tbd_0405_b3?"},
    "b4": {NAME: "tbd_0405_b4?"},
    "b5": {NAME: "temperature?"},
    "b6": {NAME: "tbd_0405_b6?"},
    "b7": {NAME: "tbd_0405_b7?"},
    "b8": {NAME: "tbd_0405_b8?"},
    "b9": {NAME: "tbd_0405_b9?"},
    "ba": {NAME: "tbd_0405_ba?"},
    "bb": {NAME: "tbd_0405_bb?"},
    "bc": {NAME: "generator_mode"},  # 0 = quiet, 1 = eco, 2 = turbo
    "bd": {NAME: "runtime_hours?"},
    "be": {NAME: "tbd_0405_be?"},
    "bf": {NAME: "tbd_0405_bf?"},
    "c0": {NAME: "tbd_0405_c0?"},
    "c1": {NAME: "tbd_0405_c1?"},
    "c2": {NAME: "tbd_0405_c2?"},
    "c3": {NAME: "tbd_0405_c3?"},
    "c4": {NAME: "tbd_0405_c4?"},
    "c5": {NAME: "tbd_0405_c5?"},
    "c6": {NAME: "tbd_0405_c6?"},
    "ca": {NAME: "tbd_0405_ca?"},
    "cb": {NAME: "tbd_0405_cb?"},
    "fd": {NAME: "tbd_0405_fd?"},
    "fe": {NAME: "msg_timestamp"},
}

_A7320_0408 = {
    # SOLIX Smart Generator 5500 extended status message.
    TOPIC: "param_info",
    "a2": {NAME: "device_sn"},
    "a3": {NAME: "paired_device_sn"},
    "a4": {NAME: "tbd_0408_a4?"},
    "a5": {
        BYTES: {
            "00": {
                NAME: "tbd_0408_a5_u16_01?",
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "02": {
                NAME: "ac_dc_mode",  # 3 = AC, 1 = DC
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "04": {
                NAME: "tbd_0408_a5_u16_03?",
                TYPE: DeviceHexDataTypes.sile.value,
            },
        }
    },
    "ae": {
        BYTES: {
            "00": {
                NAME: "tbd_0408_ae_u16_01?",
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "02": {
                NAME: "tbd_0408_ae_u16_02?",
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "04": {
                NAME: "tbd_0408_ae_u16_03?",
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "06": {
                NAME: "tbd_0408_ae_u16_04?",
                TYPE: DeviceHexDataTypes.sile.value,
            },
        }
    },
    "af": {NAME: "tbd_0408_af?"},
    "b0": {NAME: "tbd_0408_b0?"},
    "b2": {NAME: "tbd_0408_b2?"},
    "b3": {NAME: "tbd_0408_b3?"},
    "b4": {NAME: "tbd_0408_b4?"},
    "b5": {NAME: "tbd_0408_b5?"},
    "b6": {NAME: "tbd_0408_b6?"},
    "b7": {NAME: "tbd_0408_b7?"},
    "fd": {NAME: "tbd_0408_fd?"},
    "fe": {NAME: "msg_timestamp"},
}

_A2345_0303 = (
    {
        # 250W Prime Charger
        TOPIC: "state_info",
    }
    | {
        f"{0xA2 + idx:02x}": {
            BYTES: {
                "00": {
                    NAME: f"{port}_status",
                    TYPE: DeviceHexDataTypes.ui.value,
                },  # status: Inactive (0), Active (1)
                "01": {
                    NAME: f"{port}_voltage",
                    TYPE: DeviceHexDataTypes.sile.value,
                    FACTOR: 0.001,
                },
                "03": {
                    NAME: f"{port}_current",
                    TYPE: DeviceHexDataTypes.sile.value,
                    FACTOR: 0.001,
                },
                "05": {
                    NAME: f"{port}_power",
                    TYPE: DeviceHexDataTypes.sile.value,
                    FACTOR: 0.01,
                },
            }
        }
        for idx, port in enumerate(
            ["usbc_1", "usbc_2", "usbc_3", "usbc_4", "usba_1", "usba_2"]
        )
    }
    | {
        "a8": {
            # same as 0a00 bd
            BYTES: {
                "00": {
                    NAME: "unknown_a8_00_01",
                    TYPE: DeviceHexDataTypes.sile.value,
                },
                "01": {
                    NAME: "unknown_a8_01_02",
                    TYPE: DeviceHexDataTypes.sile.value,
                },
                "02": {
                    NAME: "unknown_a8_02_03",
                    TYPE: DeviceHexDataTypes.sile.value,
                },
                "03": {
                    NAME: "unknown_a8_03",
                    TYPE: DeviceHexDataTypes.ui.value,
                },
            }
        },
        # "a9" same as 0a00 be
        "fe": {NAME: "msg_timestamp"},
    }
)

_A2345_0a00 = (
    {
        "a2": {NAME: "sw_version", "values": 4},
    }
    | {
        f"{0xA4 + idx:02x}": {
            BYTES: {
                "00": {NAME: f"{port}_status", TYPE: DeviceHexDataTypes.ui.value},
                "01": {
                    NAME: f"{port}_voltage",
                    TYPE: DeviceHexDataTypes.sile.value,
                    FACTOR: 0.001,
                },
                "03": {
                    NAME: f"{port}_current",
                    TYPE: DeviceHexDataTypes.sile.value,
                    FACTOR: 0.001,
                },
                "05": {
                    NAME: f"{port}_power",
                    TYPE: DeviceHexDataTypes.sile.value,
                    FACTOR: 0.01,
                },
            }
        }
        for idx, port in enumerate(
            ["usbc_1", "usbc_2", "usbc_3", "usbc_4", "usba_1", "usba_2"]
        )
    }
    | {
        f"{0xAA + idx:02x}": {
            BYTES: {
                "00": {
                    NAME: f"{port}_switch",
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "01": {
                    NAME: f"{port}_start_switch",  # 0 (off), 1 (on)
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "02": {
                    NAME: f"{port}_start_hour",  # hour as byte
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "03": {
                    NAME: f"{port}_start_minute",  # minute as byte
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "04": {
                    NAME: f"{port}_start_weekdays",  # Bitmask: 0:sun:sat:fri:thu:wed:tue:mon
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "05": {
                    NAME: f"{port}_end_switch",  # 0 (off), 1 (on)
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "06": {
                    NAME: f"{port}_end_hour",  # hour as byte
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "07": {
                    NAME: f"{port}_end_minute",  # minute as byte
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "08": {
                    NAME: f"{port}_end_weekdays",  # Bitmask: 0:sun:sat:fri:thu:wed:tue:mon
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "09": {NAME: f"{port}_timer_switch", TYPE: DeviceHexDataTypes.ui.value},
                "10": {
                    NAME: f"{port}_timer_seconds",
                    TYPE: DeviceHexDataTypes.var.value,
                },
                "14": {
                    NAME: f"{port}_timer_remaining_seconds",  # remaining seconds
                    TYPE: DeviceHexDataTypes.var.value,
                },
                "18": {
                    NAME: f"{port}_priority",  # 1 normal, 2 prioritized
                    TYPE: DeviceHexDataTypes.ui.value,
                },
            },
        }
        for idx, port in enumerate(["usbc_1", "usbc_2", "usbc_3", "usbc_4", "usba"])
    }
    | {
        "af": {
            BYTES: {
                "00": [
                    {NAME: "clock_settings", MASK: 0xFF},
                    {NAME: "clock_switch", MASK: 0x80},
                    {NAME: "holiday_switch", MASK: 0x40},
                    {NAME: "custom_theme_active", MASK: 0x04},
                    {NAME: "stock_theme_active", MASK: 0x02},
                ],
                "01": {
                    NAME: "theme_id",
                    TYPE: DeviceHexDataTypes.var.value,
                    SIGNED: False,
                },
            },
        },
        "b0": {
            NAME: "display_timeout_mode",  # 0 (Never), 1 (30 sec), 2 (1 min), 3 (5 min), 4 (30 min)
        },
        "b1": {
            NAME: "usage_mode",  # 1 (AI Power), 2 (Connection Prio), 3 (Dual Laptop), 4 (Low power)
        },
        "b3": {
            NAME: "display_brightness",  # Brightness in %, 20-100 % step 5 %
        },
        "b4": {
            NAME: "knob_mode",  # 0: forward, 1 backward
        },
        "b5": {
            NAME: "clock_mode",  # 0 (12h), 1 (24h)
        },
        "b6": {
            NAME: "unknown_b6",
        },
        "b8": {
            BYTES: {
                "00": {
                    NAME: "custom_profile_number",
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "01": {
                    NAME: "auto_exit_switch",
                    TYPE: DeviceHexDataTypes.ui.value,
                },
            }
            | {
                f"{2 + idx:02d}": {
                    NAME: f"custom_usb_{port}_power_limit",
                    TYPE: DeviceHexDataTypes.ui.value,
                }
                for idx, port in enumerate(["c1", "c2", "c3", "c4", "a"])
            },
        },
        "b9": {
            BYTES: {
                "00": {
                    NAME: "clock_display_start_hour",  # hour as byte
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "01": {
                    NAME: "clock_display_start_minute",  # minute as byte
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "02": {
                    NAME: "clock_display_end_hour",  # hour as byte
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "03": {
                    NAME: "clock_display_end_minute",  # minute as byte
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "04": {
                    NAME: "clock_display_weekdays",  # Bitmask: 0:sun:sat:fri:thu:wed:tue:mon
                    TYPE: DeviceHexDataTypes.ui.value,
                },
            },
        },
        "ba": {
            BYTES: {
                f"{0 + idx * 3:02d}": {
                    NAME: f"custom_usb_{port}_protocols",
                    TYPE: DeviceHexDataTypes.bin.value,
                    LENGTH: 1,
                    STATE_CONVERTER: lambda value, state, cache: (
                        convert_port_protocols(value)
                        if value is not None
                        else convert_port_protocols(state)
                    ),
                }
                for idx, port in enumerate(["c1", "c2", "c3", "c4"])
            }
        },
        # "bd" same as 0303 a8
        # "be" same as 0303 a9
        "fe": {NAME: "msg_timestamp"},
    }
)

_AS200_0421 = {
    "a2": {
        BYTES: {
            "01": {
                NAME: "device_sn",
                TYPE: DeviceHexDataTypes.str.value,
            },
            "20": {
                NAME: "device_pn",
                TYPE: DeviceHexDataTypes.str.value,
            },
        }
    },
    "a3": {
        BYTES: {
            "04": {
                NAME: "output_power",  # DC output power for each direction, allways positive
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "06": {
                NAME: "output_voltage?",
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.001,
            },
            "08": {
                NAME: "unknown_a3_08?",
                TYPE: DeviceHexDataTypes.sile.value,
            },
        }
    },
    "a4": {
        BYTES: {
            "00": {NAME: "device_switch", TYPE: DeviceHexDataTypes.ui.value},
            "01": {
                NAME: "charger_mode",  # 0=Normal, 1=Reverse
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "02": {
                NAME: "car_battery_type",  # 0=LiFePO4, 1=Lead Acid
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "03": {
                NAME: "car_battery_voltage_type",  # 0=12V, 1=24V
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "05": {
                NAME: "charge_voltage_limit",
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.1,
            },
            "07": {
                NAME: "charge_power_limit",
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "09": {
                NAME: "reverse_power_limit",
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "11": {
                NAME: "active_device_timeout_minutes",  # active device auto-off timeout (minutes): 0 (Never), 720-1440 min in 30 min steps
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "13": {
                NAME: "temp_unit_fahrenheit",
                TYPE: DeviceHexDataTypes.ui.value,
            },  # Celsius (0) or Fahrenheit (1)
            "16": {
                NAME: "device_timeout_minutes",  # Device auto-off timeout control (minutes): 720-1440 min in 30 min steps
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "18": {
                NAME: "device_timeout_switch",  # Timeout (0) or Off (1) = Never timeout
                TYPE: DeviceHexDataTypes.ui.value,
            },
        }
    },
    "a6": {
        BYTES: {
            "02": {
                NAME: "temperature",
                TYPE: DeviceHexDataTypes.ui.value,
                SIGNED: True,
            },
            "04": {
                NAME: "device_1_status",  # PPS connection via XT60i or Expansion cable: connected (1), disconnected (0), connecting (2)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "06": {
                NAME: "charge_power_limit_min",
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "08": {
                NAME: "charge_power_limit_max",
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "10": {
                NAME: "reverse_power_limit_min",
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "12": {
                NAME: "reverse_power_limit_max",
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "14": {
                NAME: "charge_voltage_limit_min",
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.1,
            },
            "16": {
                NAME: "charge_voltage_limit_max",
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.1,
            },
            "18": {
                NAME: "battery_voltage",
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.1,
            },
            "24": {
                NAME: "unknown_device_1_a6_24",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "25": {
                NAME: "device_1_output_power",  # power from connected PPS
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "27": {
                NAME: "xt60i_cable",  # XT60i cable disconnected (0), connected (1)
                TYPE: DeviceHexDataTypes.ui.value,
            },
        }
    },
    "a7": {
        BYTES: {
            "00": {
                NAME: "unknown_pps_a7_00",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "01": {
                NAME: "unknown_pps_a7_01",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "02": {
                NAME: "device_1_temperature",
                TYPE: DeviceHexDataTypes.ui.value,
                SIGNED: True,
            },
            "03": {
                NAME: "unknown_pps_a7_03",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "04": {
                NAME: "remaining_time_hours",  # PPS remaining time charge
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.1,
                SIGNED: False,
            },
            "06": {
                NAME: "reverse_remaining_time_hours",  # PPS remaining time reverse charge
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.1,
                SIGNED: False,
            },
            "08": {
                NAME: "device_1_soc",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "11": {
                NAME: "device_1_sn",
                TYPE: DeviceHexDataTypes.str.value,
            },
            "29": {
                NAME: "device_1_pn",
                TYPE: DeviceHexDataTypes.str.value,
            },
        }
    },
    "f9": {
        BYTES: {
            "24": {
                NAME: "unknown_pps_f9_24",
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "25": {
                NAME: "unknown_pps_f9_25",
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "26": {
                NAME: "unknown_pps_f9_26",
                TYPE: DeviceHexDataTypes.ui.value,
            },
        }
    },
    "fd": {
        BYTES: {
            "00": {
                NAME: "local_timestamp",
                TYPE: DeviceHexDataTypes.str.value,
                LENGTH: 13,
            },
        }
    },
    "fe": {
        BYTES: {
            "00": {
                NAME: "msg_timestamp",
                TYPE: DeviceHexDataTypes.var.value,
                SIGNED: False,
            },
        }
    },
}

# S2000 forked from _A1783_0421 (C2000 Gen 2); extra AS220-only tags TBD
_AS220_0421 = {
    "a2": {
        BYTES: {
            "01": {
                NAME: "device_sn",
                TYPE: DeviceHexDataTypes.str.value,
            },
            "20": {
                NAME: "device_pn",
                TYPE: DeviceHexDataTypes.str.value,
            },
            "26": {
                NAME: "sw_version",
                TYPE: DeviceHexDataTypes.var.value,
                "values": 4,
                "reversed": True,
            },
        }
    },
    "a3": {
        BYTES: {
            "00": {
                NAME: "working_status",  # 0 idle / 1 discharge / 2 charge / 3 sleep / 4 shutdown / 5 ???
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "04": {
                NAME: "ac_input_limit_max",  # Max supported charge limit, seems fix
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "07": {
                NAME: "wifi_signal",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "08": {
                NAME: "mtu_size",
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "10": {
                NAME: "silent_charge_power",
                TYPE: DeviceHexDataTypes.sile.value,
            },
        }
    },
    "a4": {
        BYTES: {
            "00": {
                NAME: "ac_output_timer_seconds",  # AC off timer: disabled (0), min:0, max: 86400, step 300
                TYPE: DeviceHexDataTypes.var.value,
                LENGTH: 4,
            },
            "04": {
                NAME: "ac_input_limit",  # AC charge limit: 100-2400 W, step: 100
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "06": {
                NAME: "ac_frequency",  # 60 / 50 Hz
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "13": {
                NAME: "device_timeout_minutes",  # 0 (Never), 30, 60, 120, 240, 360, 720, 1440
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "15": {
                NAME: "display_timeout_seconds",  # 0 (Never), 10, 30, 60, 300, 1800
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "17": {
                NAME: "display_mode",  # Low (1), Medium (2), High (3)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "19": {
                NAME: "temp_unit_fahrenheit",  # Celsius (0) or Fahrenheit (1)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "20": {
                NAME: "ac_fast_charge_switch",  # Ultrafast Charge switch: Disabled (0) or Enabled (1)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "21": {
                NAME: "display_switch",  # Off (0), On (1)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "22": {
                NAME: "port_memory_switch",  # Output Port Memory switch: Disabled (0) or Enabled (1)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "23": {
                NAME: "max_soc",  # max_soc %
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "24": {
                NAME: "min_soc",  # min_soc %
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "26": {NAME: "country_code", TYPE: DeviceHexDataTypes.str.value, LENGTH: 2},
            "28": {
                NAME: "ac_output_timeout_minutes",  # minutes; AS220 Smart AC output timeout (live: 240=4h, 720=12h)
                TYPE: DeviceHexDataTypes.sile.value,
            },
        }
    },
    "a5": {
        BYTES: {
            "00": {
                NAME: "temperature",
                SIGNED: True,
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "01": {
                NAME: "battery_status",  # 0=standby, 1=discharge, 2=Charge,
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "02": {
                NAME: "battery_soc",  # Battery SOC
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "03": {
                NAME: "battery_soh",  # Battery SOH
                TYPE: DeviceHexDataTypes.ui.value,
            },
        }
    },
    "a6": {
        BYTES: {
            "00": {
                NAME: "output_power_total",  # Output power total (AC + DC)
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "02": {
                NAME: "ac_input_power",  # Input power total charge
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "04": {
                NAME: "dc_input_power_total",  # # DC input power (solar + car charging)
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "06": {
                NAME: "remaining_time_hours",  # hours with factor 0.1
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.1,
                SIGNED: False,
            },
            "08": {
                NAME: "main_battery_soc",  # SOC of main battery only
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "10": {
                NAME: "ac_input_plug_status",  # 0: Disconnected, 1: connected
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "11": {
                NAME: "input_power_total",  # AC and DC input power combined
                TYPE: DeviceHexDataTypes.sile.value,
            },
        },
    },
    "a7": {
        BYTES: {
            "00": {
                NAME: "ac_output_power_switch",  # Off (0), On (1)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "01": {
                NAME: "ac_output_power",  # AC Output power
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "03": {
                NAME: "ac_input_power_switch",  # AC input / charging active (0/1) - live-confirmed: 0->1 when charging
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "04": {
                NAME: "pv_input_power?",  # Supposed PV input (dup of a6 ac_input_power) - live-confirmed = input W
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "07": {
                NAME: "ac_output_timer_remaining_seconds",
                TYPE: DeviceHexDataTypes.var.value,
            },
        }
    },
    "aa": {
        BYTES: {
            "00": {
                NAME: "usb_status",  # USB total status: Inactive (0), Discharging (1), Charging (2)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "01": {
                NAME: "usb_power",  # Total USB power
                TYPE: DeviceHexDataTypes.sile.value,
            },
        }
    },
    "d9": {
        # TOU mode selector + backup + Time-of-Use plan
        BYTES: [
            {
                NAME: "active_plan",  # TOUSystemStatus: 0=Standard/UPS, 3=Time-of-Use, 4=Self-Consumption, 5=Custom
                TYPE: DeviceHexDataTypes.ui.value,
            },
            {
                NAME: "usage_mode",  # TOUSettingSystemStatus: 0=Standard, 1=Time-of-Use, 2=Self-Consumption, 3=Custom
                TYPE: DeviceHexDataTypes.ui.value,
            },
            {
                NAME: "backup_soc",  # backup reserve % (discharge floor for tou)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            {
                NAME: "backup_charge_soc",  # changed with max_soc % (for tou and backup usage)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            {
                NAME: "backup_discharge_soc",  # changed with min_soc % (for backup discharge?)
                TYPE: DeviceHexDataTypes.ui.value,
            },
            # Byte 5 is the tou schedule slot count and 6+ holds the TOU schedule:
            # (tariff(1=Peak,2=Mid,3=Off), start_hr, end_hr) * tou_slot_count
            # App allows max 6 slots, remainder of field has different purpose
            {
                NAME: "tou_mode_schedule",
                TYPE: DeviceHexDataTypes.bin.value,
                # Define both conversions since length of schedule is flexible within binary
                STATE_CONVERTER: lambda value, state, cache: (
                    convert_pps_tou_schedule(value)
                    if value is not None
                    else convert_pps_tou_schedule(state)
                ),
            },
            {
                NAME: "backup_status",  # 0: inactive, 1: planned charge: 2: storm guard charge
                TYPE: DeviceHexDataTypes.ui.value,
            },
            {
                NAME: "backup_switch",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            {
                NAME: "storm_guard_switch",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            {
                NAME: "backup_start_timestamp",
                TYPE: DeviceHexDataTypes.var.value,
                SIGNED: False,
            },
            {
                NAME: "backup_end_timestamp",
                TYPE: DeviceHexDataTypes.var.value,
                SIGNED: False,
            },
            {
                NAME: "auto_backup_start_timestamp",
                TYPE: DeviceHexDataTypes.var.value,
                SIGNED: False,
            },
            {
                NAME: "auto_backup_end_timestamp",
                TYPE: DeviceHexDataTypes.var.value,
                SIGNED: False,
            },
        ]
    },
    "de": {
        # AC Output switch schedule (live-confirmed vs app). Flexible structure!!!
        # 0-5 time slots, each can be activated or deactivated separately
        # per slot: active:u8 (0=disabled, 1=enabled), weekdays:u8 (bit0=Mon..bit6=Sun)
        # per slot: switch:u8 (1=On, 2=Off), daytime_minutes:u16 LE
        # a3  0c 04    02: 01: 5f: 01: 1e:00:  01: 04: 00: 6e:05
        #        bin   cnt act wkd sw  00:30   act wkd sw  1390
        NAME: "ac_output_schedule",
        STATE_CONVERTER: lambda value, state, cache: (
            convert_pps_output_schedule(value)
            if value is not None
            else convert_pps_output_schedule(state)
        ),
    },
    "dd": {
        # Custom-mode charge/discharge schedule (live-confirmed vs app). Flexible structure!!!
        # groups:u8  1: weekend same, 2: weekday + weekend
        # per group: weekdays:u8 (bit0=Mon..bit6=Sun), slots:u8 + 5 slots max
        # per slot: load_mode:u8 (1=Charge, 2=Discharge), start_minutes:u16 LE, end_minutes:u16 LE
        # a2  0e 04    01: 1f: 02: 01: 00:00:68:01: 02: 68:01:d0:02
        # a2  15 04    02: 1f: 02: 01: 00:00:68:01: 02: 68:01:d0:02  :60: 01: 02: 00:00: 3c:00
        #        bin   grp wk  slt dis    00   360  ch    360   720   wk  slt chg    00     60
        NAME: "custom_mode_schedule",
        STATE_CONVERTER: lambda value, state, cache: (
            convert_pps_custom_schedule(value)
            if value is not None
            else convert_pps_custom_schedule(state)
        ),
    },
    "df": {
        # Silent-mode schedule (live-confirmed vs app)
        BYTES: {
            "00": {
                NAME: "silent_mode_switch",  # 0/1
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "01": {
                NAME: "silent_mode_weekdays",  # Bitmask: 0:sun:sat:fri:thu:wed:tue:mon
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "02": {
                NAME: "silent_mode_start_minutes",  # start, minutes of day (u16 LE)
                TYPE: DeviceHexDataTypes.sile.value,
                SIGNED: False,
            },
            "04": {
                NAME: "silent_mode_end_minutes",  # end, minutes of day (u16 LE)
                TYPE: DeviceHexDataTypes.sile.value,
                SIGNED: False,
            },
        }
    },
    "f0": {
        BYTES: {
            "00": {
                NAME: "ac_output_power_switch_f0",  # dup of ac_output_power_switch - live-confirmed via isolation test
                TYPE: DeviceHexDataTypes.ui.value,
            },
        }
    },
    # "da": # Field used for screen schedule and theme settings, not supported on device
    "f9": {
        BYTES: {
            "00": {
                NAME: "sw_version",
                TYPE: DeviceHexDataTypes.var.value,
                "values": 4,
                "reversed": True,
            },
            "24": {
                NAME: "hw_version",
                TYPE: DeviceHexDataTypes.var.value,
                "values": 4,
                "reversed": True,
            },
        }
    },
    "fd": {NAME: "storm_guard_timestamp"},
    "fe": {NAME: "msg_timestamp"},
}

_PLUG_TIMER_STATUS = {
    BYTES: {
        "00": {
            NAME: "toggle_to_delay_time",
            TYPE: DeviceHexDataTypes.var.value,  # seconds:minutes:hours
            LENGTH: 3,
        },
        "03": {
            NAME: "toggle_to_switch",  # 0 = toggle off, 1 = toggle on
            TYPE: DeviceHexDataTypes.ui.value,
        },
        "04": {
            NAME: "toggle_timer_mode",  # 3 seen while toggle_to delay running (also after start = 1), 0 inactive, 2 paused
            TYPE: DeviceHexDataTypes.ui.value,
        },
        "05": {
            NAME: "toggle_to_elapsed_time",  # seconds:minutes:hours
            TYPE: DeviceHexDataTypes.var.value,
            LENGTH: 3,
        },
    }
}

_DOCK_0405 = (
    {
        # multisystem message
        TOPIC: "param_info",
        "a2": {NAME: "device_sn"},
        "a3": {NAME: "sw_version", "values": 4},
        "a5": {NAME: "ac_output_power_signed"},
        "a6": {
            NAME: "device_output_power_signed_total",
            FACTOR: -1,
        },  # All SB outputs (negative is SB output)
        "a7": {NAME: "usage_mode"},  # SB2 usage mode
        "a8": {NAME: "unknown_0405_a8?"},
        "b3": {NAME: "utc_timestamp"},
    }
    | {
        k: v
        for idx in range(1, 5)
        for k, v in {
            f"{0xB6 + (idx - 1) * 2:02x}": {
                BYTES: [
                    # Field has flexible offset, depending on SN length
                    {
                        NAME: f"device_{idx}_sn",
                        TYPE: DeviceHexDataTypes.str.value,
                    },
                    {
                        NAME: f"device_{idx}_type",  # 01 = A17C1, 05 = A17C5 ?
                        TYPE: DeviceHexDataTypes.ui.value,
                    },
                    {
                        NAME: f"device_{idx}_soc",
                        TYPE: DeviceHexDataTypes.ui.value,
                        OFFSET: 0,  # Example for Byte offset from previous field in case of description gap
                    },
                ]
            },
            f"{0xB7 + (idx - 1) * 2:02x}": {
                NAME: f"device_{idx}_ac_output_power_signed",
                FACTOR: -1,
            },
        }.items()
    }
)

_DOCK_0420 = (
    {
        # multisystem message
        TOPIC: "param_info",
        "a2": {NAME: "device_sn"},
        "a3": {NAME: "local_timestamp"},
        "a4": {NAME: "utc_timestamp"},
        "a7": {
            NAME: "battery_soc_total"
        },  # Average SOC of all solarbank devices in system
        "a8": {NAME: "0420_unknown_1?"},
        "a9": {NAME: "usage_mode"},  # SB usage modes
        "ab": {NAME: "grid_power_signed"},
        "ac": {
            NAME: "device_output_power_signed_total"
        },  # Combined device output power
        "ae": {NAME: "ac_output_power"},  # Dock output power to home
        "af": {NAME: "home_demand_total"},  # Total across all devices in system
        "b0": {NAME: "pv_power_total"},  # Total across all devices in system
        "b1": {NAME: "battery_power_signed_total"},
    }
    | {
        f"b{2 + idx}": {
            BYTES: {
                "00": {
                    NAME: f"device_{idx}_sn",
                    TYPE: DeviceHexDataTypes.str.value,
                },
                "18": {
                    NAME: f"device_{idx}_battery_power",
                    TYPE: DeviceHexDataTypes.sfle.value,
                },
                "22": {
                    NAME: f"device_{idx}_soc",
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "23": {
                    NAME: f"device_{idx}_pv_1_power",
                    TYPE: DeviceHexDataTypes.sfle.value,
                },
                "27": {
                    NAME: f"device_{idx}_pv_2_power",
                    TYPE: DeviceHexDataTypes.sfle.value,
                },
                "31": {
                    NAME: f"device_{idx}_pv_3_power",
                    TYPE: DeviceHexDataTypes.sfle.value,
                },
                "35": {
                    NAME: f"device_{idx}_pv_4_power",
                    TYPE: DeviceHexDataTypes.sfle.value,
                },
                "39": {
                    NAME: f"device_{idx}_pv_other_power",
                    TYPE: DeviceHexDataTypes.sfle.value,
                },
                "43": {
                    NAME: f"device_{idx}_exp_packs",
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "44": {
                    NAME: f"device_{idx}_pv_power",
                    TYPE: DeviceHexDataTypes.sfle.value,
                },
            }
        }
        for idx in range(1, 5)
    }
    | {
        "c1": {NAME: "main_device_sn?"},
        "c2": {NAME: "pv_power_3rd_party"},
        "c3": {NAME: "backup_start_timestamp", SIGNED: False},
        "c4": {NAME: "backup_end_timestamp", SIGNED: False},
    }
)

_DOCK_0421 = {
    # multisystem message
    TOPIC: "state_info",
    "a4": {NAME: "max_load_total"},  # user applied max load limit across all devices
    "a5": {NAME: "ac_input_limit_total"},
    "a6": {
        NAME: "max_load_limit_total"
    },  # system defined limit based on given installation
    "a7": {NAME: "battery_soc_total"},  # Average SOC of all solarbank devices in system
    "ac": {NAME: "unknown_ac?"},
    "ae": {NAME: "usage_mode"},  # SB usage modes
    "fc": {NAME: "device_sn"},
    "fd": {NAME: "local_timestamp"},
    "fe": {NAME: "msg_timestamp"},
}

_DOCK_0428 = (
    {
        # multisystem message
        TOPIC: "state_info",
        "a2": {NAME: "device_sn"},
        "a3": {NAME: "local_timestamp"},
        "a4": {NAME: "utc_timestamp"},
        "a5": {NAME: "battery_soc_total"},  # Average SOC of all solarbanks
        "a6": {NAME: "usage_mode"},  # SB usage modes
        "a7": {NAME: "home_load_default"},  # default home load
        "ab": {NAME: "pv_power_total"},
        "ac": {NAME: "pv_power_3rd_party"},
        "b1": {NAME: "device_output_power_signed_total"},
        "b5": {NAME: "battery_power_signed_total"},
        "bc": {NAME: "grid_power_signed"},
    }
    | {
        f"{0xBE + idx:02x}": {
            BYTES: {
                "00": {
                    NAME: f"device_{idx}_sn",
                    TYPE: DeviceHexDataTypes.str.value,
                },
                "18": {
                    NAME: f"device_{idx}_soc",
                    TYPE: DeviceHexDataTypes.ui.value,
                },
                "19": {
                    NAME: f"device_{idx}_pv_power",
                    TYPE: DeviceHexDataTypes.sfle.value,
                },
                "23": {
                    NAME: f"device_{idx}_pv_1_power",
                    TYPE: DeviceHexDataTypes.sfle.value,
                },
                "27": {
                    NAME: f"device_{idx}_pv_2_power",
                    TYPE: DeviceHexDataTypes.sfle.value,
                },
                "31": {
                    NAME: f"device_{idx}_pv_3_power",
                    TYPE: DeviceHexDataTypes.sfle.value,
                },
                "35": {
                    NAME: f"device_{idx}_pv_4_power",
                    TYPE: DeviceHexDataTypes.sfle.value,
                },
            },
        }
        for idx in range(1, 5)
    }
    | {
        "c9": {NAME: "home_demand_total"},  # Total across all devices in system
    }
    | {
        f"{0xD8 + idx:02x}": {
            BYTES: {
                "00": {
                    NAME: f"device_{idx}_sn",
                    TYPE: DeviceHexDataTypes.str.value,
                },
            }
        }
        for idx in range(1, 5)
    }
)

_DOCK_0500 = {
    # Only binary fields, format unknown
    TOPIC: "state_info",
}

_EV_CHARGER_0403 = {
    # V1 status message
    TOPIC: "param_info",
    "a5": {NAME: "charging_window_seconds"},
    "a6": {
        NAME: "solar_evcharge_min_current?"
    },  # 6 - max_current_limit (32 A), step 1 A
}

_EV_CHARGER_0405 = {
    # V1 status message
    TOPIC: "param_info",
    "a2": {NAME: "unknown_limit?"},
    # "a3": {NAME: "ocpp_connect_status?"},  # disconnected(0), connecting(1), connected(2)
    "a3": {NAME: "plug_lock_switch"},  # On (1), Off (2) !
    "a4": {NAME: "auto_start_switch"},  # Off (0), On (1)
    "a8": {
        NAME: "max_evcharge_current",
        FACTOR: 0.1,
    },  # 6 - rated_current (32 A), step 1 A
    "aa": {NAME: "light_brightness"},  # 0-100 %, step 10 %
    "ac": {NAME: "auto_charge_restart_switch"},  # Off (0), On (1)
    "ad": {NAME: "random_delay_switch"},  # Off (0), On (1)
    "af": {
        NAME: "wipe_up_mode"
    },  # off (0) / start charge (1) / stop charge (2) / boost charge (3)
    "b0": {
        NAME: "wipe_down_mode"
    },  # off (0) / start charge (1) / stop charge (2) / boost charge (3)
    "b2": {NAME: "smart_touch_mode"},  # simple (0), anti_mistouch (1)
    "b4": {NAME: "light_off_schedule_switch"},  # Off (0), On (1)
    "b5": {NAME: "light_off_start_time", SIGNED: False},  # sile: hour * 256 + sec
    "b6": {NAME: "light_off_end_time", SIGNED: False},  # sile: hour * 256 + sec
    "b7": {NAME: "modbus_switch"},  # Off (0), On (1)
    "cc": {NAME: "tcp_timeout_seconds"},  # Modbus TCP timeout
    "ce": {NAME: "max_current_limit", FACTOR: 0.1},  # rated A limit for model
    "cf": {NAME: "tcp_port"},  # Modbus TCP port
    "d0": {NAME: "ip_address"},  # device IP address
    "d3": {NAME: "load_balance_switch"},  # Off (0), On (1)
    "d4": {NAME: "main_breaker_limit"},  # 10-500 A, step 1 A
    "d5": {NAME: "load_balance_setting_d5"},  # System monitoring (1)
    "d6": {NAME: "load_balance_setting_d6"},  # 1 if SM monitored?
    "d7": {NAME: "load_balance_monitor_device"},  # SN of monitoring device
    "d8": {NAME: "solar_evcharge_switch"},  # Off (0), On (1)
    "d9": {NAME: "solar_evcharge_mode"},  # solar & grid (0), solar only (1)
    "da": {NAME: "solar_evcharge_min_current"},  # 6 - rated_current (32 A), step 1 A
    "db": {NAME: "phase_operating_mode"},  # auto (0), 1 phase (1)
    "dc": {NAME: "solar_evcharge_monitoring_mode"},
    "dd": {
        NAME: "auto_phase_switch"
    },  # Off (0), On (1), only available in 3 phase models
    "de": {NAME: "solar_evcharge_monitor_device"},  # monitoring device sn
    "df": {NAME: "boost_status"},  # Off (0), On (1)
    "e0": {NAME: "cp_signal_status"},
    # A=12V(0), B1=9V(3), B2=9V(4), C1=6V(5), C2=6V(6), Error(7), D1=3V(8), D2=3V(9),  E=0V(10), F=-12(11),
    "e2": {NAME: "plug_status"},  # Disconnected (0), Connected (1)
    "e3": {NAME: "ev_charger_status"},
    # Standby(0), Preparing(1), Charging(2), Charger_Paused(3), Vehicle_Paused(4), Completed (5), Reserving(6), Disabled(7), Error(8)
    "e6": {NAME: "schedule_switch"},  # on (1), off (2) !
    "e7": {NAME: "week_start_time", SIGNED: False},  # sile: hour * 256 + sec
    "e8": {NAME: "week_end_time", SIGNED: False},  # sile: hour * 256 + sec
    "e9": {NAME: "weekend_start_time", SIGNED: False},  # sile: hour * 256 + sec
    "ea": {NAME: "weekend_end_time", SIGNED: False},  # sile: hour * 256 + sec
    "eb": {NAME: "weekend_mode"},  # 1: same, 2: different
    "ec": {NAME: "schedule_mode"},  # 0: normal, 1: smart
    "f1": {NAME: "sw_version", "values": 4},
    "f2": {NAME: "sw_controller", "values": 4},
    "f3": {NAME: "hw_version", "values": 4},
    "fe": {NAME: "min_current_limit"},  # 6 A
}

_EV_CHARGER_0410 = {
    # V1 status message
    TOPIC: "param_info",
    "a2": {NAME: "voltage_l1", "factor": 0.1},
    "a3": {NAME: "voltage_l2", "factor": 0.1},
    "a4": {NAME: "voltage_l3", "factor": 0.1},
    "a5": {NAME: "current_l1", "factor": 0.1},
    "a6": {NAME: "current_l2", "factor": 0.1},
    "a7": {NAME: "current_l3", "factor": 0.1},
    "a8": {NAME: "bat_charge_power"},
    "a9": {NAME: "charging_duration_seconds"},
    "aa": {NAME: "charging_energy", "factor": 0.001},
    "ac": {
        NAME: "charging_mode?"
    },  # off/paused (0) / grid_charge (1) ? / solar_charge (7)
    "ab": {NAME: "charging_start_timestamp", SIGNED: False},
    "ad": {NAME: "plug_countdown_seconds"},
    "ae": {NAME: "start_countdown_seconds"},
    "af": {NAME: "charging_window_seconds"},
    "b0": {NAME: "power_l1"},
    "b1": {NAME: "power_l2"},
    "b2": {NAME: "power_l3"},
    "b3": {NAME: "charging_energy_l1", "factor": 0.001},
    "b4": {NAME: "charging_energy_l2", "factor": 0.001},
    "b5": {NAME: "charging_energy_l3", "factor": 0.001},
    "b6": {NAME: "order_id?"},
    "b7": {NAME: "unknown_b7?"},  #  (0),  (1)
    "b8": {
        NAME: "ocpp_connect_status"
    },  # disconnected (0), Connecting (1), Connected (2)
    # "b9": {NAME: "cp_signal_status?"},
    # A=12V(0), B1=9V(3), B2=9V(4), C1=6V(5), C2=6V(6), Error(7), D1=3V(8), D2=3V(9),  E=0V(10), F=-12(11),
    "ba": {NAME: "phase_operating_mode"},  # auto (0), 1 phase (1)
    "bb": {NAME: "ev_charger_status"},
    # Standby(0), Preparing(1), Charging(2), Charger_Paused(3), Vehicle_Paused(4), Completed (5), Reserving(6), Disabled(7), Error(8)
}

_A17A5_0405 = {
    # SOLIX Everfrost 2 58L
    TOPIC: "param_info",
    "a2": {NAME: "device_sn"},
    "a4": {NAME: "device_pn"},
    "d0": {
        BYTES: {
            "01": {
                NAME: "unknown_sn_d0",
                TYPE: DeviceHexDataTypes.str.value,
            },
        }
    },
    "fe": {NAME: "msg_timestamp"},
}


_X1_JSON = {
    "sn": {NAME: "device_sn"},
    "subSn": {NAME: "sub_device_sn"},
    "localTime": {NAME: "local_datetime"},
    "ems_data": {
        "bs": {  # Inactive (0), Solar (1), AC Input (2), Both (3)
            NAME: "charging_status",
        },
        "gs": {NAME: "grid_status"},  # 0: OK??
        "ps": {  # 1: On-grid; 2: Off-grid 3: Standby 4: Fault
            NAME: "plant_status"
        },
        "soc": {NAME: "battery_soc"},  # 100 %
        "pp": {NAME: "photovoltaic_power"},  # 650 W
        "p2lp": {NAME: "pv_to_home_power"},  # 650 W
        "p2bp": {NAME: "pv_to_battery_power"},  # 0 W
        "p2gp": {NAME: "pv_to_grid_power"},  # 0 W
        "bp": {NAME: "battery_power_signed", FACTOR: -1},  # 0 W
        "b2lp": {NAME: "battery_to_home_power"},  # 0 W
        "b2gp": {NAME: "battery_to_grid_power"},  # 0 W
        "gp": {NAME: "grid_power_signed"},  # 0 W
        "g2bp": {NAME: "grid_to_battery_power"},  # 0 W
        "g2lp": {NAME: "grid_to_home_power"},  # 0 W
        "lp": {NAME: "ac_output_power"},  # 650 W
        "d2bp": {NAME: "generator_to_battery_power"},
        "d2lp": {NAME: "generator_to_home_power"},
        "dp": {NAME: "generator_power"},
        # daily energies in Wh?
        "pe": {NAME: "pv_yield_today", FACTOR: 0.001},  # 28629.02 Wh
        "p2le": {NAME: "pv_consumption_today", FACTOR: 0.001},  # 6348.36 Wh
        "p2be": {NAME: "pv_charge_today", FACTOR: 0.001},  # 22255.69 Wh
        "p2ge": {NAME: "pv_export_today", FACTOR: 0.001},  # 24.98 Wh
        "bdce": {NAME: "charged_energy_today", FACTOR: 0.001},  # 22255.69 Wh
        "bdde": {NAME: "discharged_energy_today", FACTOR: 0.001},  # 6879 Wh
        "b2le": {NAME: "battery_consumption_today", FACTOR: 0.001},  # 6838.9 Wh
        "b2ge": {NAME: "grid_discharged_today", FACTOR: 0.001},  # 40.09 Wh
        "g2be": {NAME: "grid_charged_today", FACTOR: 0.001},  # 0 Wh
        "g2le": {NAME: "grid_consumption_today", FACTOR: 0.001},  # 54 Wh
        "fge": {NAME: "grid_import_today", FACTOR: 0.001},
        "tge": {NAME: "grid_export_today", FACTOR: 0.001},
        "le": {NAME: "home_consumption_today", FACTOR: 0.001},  # 13241.26 Wh
        "de": {NAME: "generator_energy_today", FACTOR: 0.001},
        "d2be": {NAME: "generator_charged_today", FACTOR: 0.001},
        "d2le": {NAME: "generator_consumtion_today", FACTOR: 0.001},
        # aggregated energies in Wh?
        "pae": {NAME: "pv_yield", FACTOR: 0.001},  # 5143662.5 Wh
        "bac": {NAME: "charged_energy", FACTOR: 0.001},  # 2675350.25 Wh
        "bad": {NAME: "discharged_energy", FACTOR: 0.001},  # 2541277 Wh
    },
    "pack_data": {
        "t": {
            NAME: "exp_{x}_temperature"
        },  # List field with temps: [42.4, 41.5, 42, 41.5] °C
        "fv": {NAME: "f_voltage"},  # 53.6,
        "batv": {NAME: "battery_voltage"},  # 53.5 V
        "usoc": {NAME: "battery_soc"},  # Battery SOC
        "soh": {NAME: "battery_soh"},  # Battery Health
        "tce": {NAME: "charged_energy?", FACTOR: 0.001},  # 426497
        "tde": {NAME: "discharged_energy?", FACTOR: 0.001},  # 399819
        "dce": {NAME: "charged_energy_today", FACTOR: 0.001},  # 3522,
        "dde": {NAME: "discharged_energy_today", FACTOR: 0.001},  # 633,
        "rt": {NAME: "r_temperature?"},  # 38.1,
        "mt": {NAME: "m_temperature?"},  # 38.7,
        "ct": {NAME: "c_temperature?"},  # 41,
        "wm": {
            NAME: "usage_mode"
        },  # 0: Self-consumption; 1: TOU; 2: Backup only, 3: 3rd party control (VPP, etc) 4. User-Defined 5. Socket Aggregation
    },
}

_PP_JSON = {
    "localtime": {NAME: "local_datetime"},
    "data": {
        "sn": {NAME: "device_sn"},
        "b1sn": {NAME: "device_sn?"},
        "wf": {NAME: "wifi_name"},
        "mv": {NAME: "sw_version"},  # v1.5.7
        "mdv": {NAME: "hw_version"},  # v0.2.3.1
        "90asn": {NAME: "device_1_sn"},
        "ppsapn": {NAME: "device_1_pn"},
        "90av": {NAME: "device_1_sw_version"},  # "v3.5.6"
        "90as": {NAME: "device_1_status"},  # 2
        "90asoc": {NAME: "device_1_soc"},  # 15
        "90bsn": {NAME: "device_2_sn"},
        "ppsbpn": {NAME: "device_2_pn"},
        "90bv": {NAME: "device_2_sw_version"},  # "v3.5.6"
        "90bs": {NAME: "device_2_status"},  # 2, maybe 0: idle, 1: discharge, 2 charge
        "90bsoc": {NAME: "device_2_soc"},  # 16
        # power values
        "mcp": {NAME: "max_charge_power"},  # 8000 W
        "b2lp": {NAME: "battery_to_home_power"},  # 0 W
        "b2gp": {NAME: "battery_to_grid_power"},  # 0 W
        "bp": {NAME: "battery_power_signed", FACTOR: -1},  # -2296 W = charging
        "bcp": {NAME: "bat_charge_power", FACTOR: -1},  # -226 W = charging
        "bdcp": {NAME: "bat_discharge_power"},  # 111 W
        "pp": {NAME: "photovoltaic_power"},  # 0 W
        "p2lp": {NAME: "pv_to_home_power"},  # 0 W
        "p2bp": {NAME: "pv_to_battery_power"},  # 0 W
        "p2gp": {NAME: "pv_to_grid_power"},  # 0 W
        "gp": {NAME: "grid_power_signed"},  # 3705 W
        "g2bp": {NAME: "grid_to_battery_power"},  # 2296 W
        "g2lp": {NAME: "grid_to_home_power"},  # 1409 W
        "lp": {NAME: "ac_output_power"},  # 1409 W
        "mpp": {NAME: "micro_inverter_power"},  # 0 W
        "op": {
            NAME: "other_power"
        },  # 0 W, 3rd party PV channel, constant 0 when installation_method = 2 (none installed)
        "o2lp": {NAME: "other_to_home_power"},  # 0 W
        "o2pp": {NAME: "other_to_pv_power?"},  # 0 W
        "gmp": {NAME: "max_load_power?"},  # 4800 W
        # disaster protection (verified 2026-06 with manual backup plans and breaker test)
        "dpp": {
            NAME: "backup_plan_{x}"
        },  # list with next scheduled backup plan(s), e.g. {"start": <epoch>, "end": <epoch>, "type": 1, "soc": 100}, pushed once scheduled in App
        "dps": {
            NAME: "backup_status"
        },  # 1 while a backup plan is executing, else 0, may be 2 for auto disaster (storm guard)
        "dpct": {
            NAME: "backup_charge_time"
        },  # estimated charge time remaining, decreases with rising charge power; same value as charging_time in HTTP responses; 0 without active charge plan
        "scfg": {
            NAME: "storm_config?"
        },  # constant 7 observed; Storm Guard toggles do not change it (cloud side setting)
        # status
        "ws": {
            NAME: "working_status"
        },  # 1 = running in 0500/0505; 0502 carries Wi-Fi signal % in same key (see _PP_JSON_0502)
        "m": {
            NAME: "mode"
        },  # 2 = schedule based strategy (TOU plan), 1 = strategy without schedule (self consumption, fixed rate); verified by mode switching
        "gs": {
            NAME: "grid_status"
        },  # 0 = on-grid, 1 = grid outage (verified by breaker test)
        "bs": {  # 1: Standby; 2: Charging; 3: Discharging (verified against App); 0 never observed, deep sleep stops 0500 telemetry instead
            NAME: "battery_status"
        },
        "ps": {  # 0: Off, 1: On-grid
            NAME: "plant_status"
        },
        "soc": {NAME: "battery_soc"},  # 62 %
        "b1t": {NAME: "temperature"},  # 52 °c while device 1 was 34 °C
        "bc": {NAME: "battery_count"},  # 2
        "90s": {
            NAME: "pps_count"
        },  # 2 in 0500/0505; 0502 carries an incrementing counter in same key (see _PP_JSON_0502)
        "bds": {
            NAME: "device_{x}_data"
        },  # list with PPS data dict, eg {"sn": <pps_sn>,"soc":61,"power":-1148,"error":0}
        "cp": {
            NAME: "backup_soc"
        },  # % SOC reserved for outage (verified: follows App setting changes)
        "pu": {NAME: "power_usage_mode?"},
        "inmt": {
            NAME: "installation_method"
        },  # 3rd party PV wiring: 0 = unified circuit, 1 = separate circuit (CT at grid), 2 = no 3rd party PV (verified via App setting)
        "tv": {NAME: "sw_version_3?"},  # "v1.6.3", observed same as mv
        "acc": {NAME: "country_code"},  # "US"
        "90aacc": {NAME: "device_1_country_code"},  # "US"
        "90bacc": {NAME: "device_2_country_code"},  # "US"
        "b1e": {NAME: "err_code"},  # 0
        "tu": {NAME: "temp_unit_fahrenheit"},  # 1
        "ep": {
            NAME: "ep_unknown?"
        },  # constant 0 observed, does not change during grid outage
        "os": {
            NAME: "os_unknown?"
        },  # constant 0 observed, does not change during grid outage
        "ts": {
            NAME: "ts_unknown?"
        },  # constant 0 observed, does not change during grid outage
        "b1s": {NAME: "device_status?"},  # 0502 only, 1 observed
        "fe": {
            NAME: "fe_energy?"
        },  # 0502 only, fluctuates non-monotonic (~268000-272000), possibly alternating per PPS
        "status": {
            NAME: "event_status?"
        },  # observed 1 in event message at grid outage start
        "code": {
            NAME: "event_code?"
        },  # observed 105 in event message at grid outage start
        "mps": {NAME: "micro_power_setting?"},
        "tpp": {NAME: "pv_yield", FACTOR: 0.001},  # 3045970
        "tgp": {
            NAME: "grid_import_energy", FACTOR: 0.001
        },  # cumulative counter, increase rate proportional to grid import power, halts during outage
        "tlp": {
            NAME: "home_consumption", FACTOR: 0.001
        },  # cumulative counter, increase rate proportional to home load power
        "tsp": {NAME: "unknown_total_energy?", FACTOR: 0.001},  # 50620729
        # daily energies in Wh?
        "pe": {NAME: "pv_yield_today", FACTOR: 0.001},  # 6293 Wh
        "p2le": {NAME: "pv_consumption_today", FACTOR: 0.001},  # 4771 Wh
        "p2be": {NAME: "pv_charge_today", FACTOR: 0.001},  # 1522 Wh
        "p2ge": {NAME: "pv_export_today", FACTOR: 0.001},  # 24.98 Wh
        "bdce": {NAME: "charged_energy_today", FACTOR: 0.001},  # 2853 Wh
        "bdde": {NAME: "discharged_energy_today", FACTOR: 0.001},  # 11794 Wh
        "b2le": {NAME: "battery_consumption_today", FACTOR: 0.001},  # 11794 Wh
        "b2ge": {NAME: "grid_discharged_today", FACTOR: 0.001},  # 40.09 Wh
        "g2be": {NAME: "grid_charged_today", FACTOR: 0.001},  # 1331 Wh
        "g2le": {NAME: "grid_consumption_today", FACTOR: 0.001},  # 87889 Wh
        "fge": {NAME: "grid_import_today", FACTOR: 0.001},  # 89220 Wh
        "tge": {NAME: "grid_export_today", FACTOR: 0.001},  # 3 Wh
        "le": {NAME: "home_consumption_today", FACTOR: 0.001},  # 104452 Wh
        "de": {NAME: "generator_energy_today", FACTOR: 0.001},
        "d2be": {NAME: "generator_charged_today", FACTOR: 0.001},
        "d2le": {NAME: "generator_consumtion_today", FACTOR: 0.001},
        "o2le": {NAME: "other_consumption_today", FACTOR: 0.001},
        "o2pe": {NAME: "other_pv_yield_today", FACTOR: 0.001},
        "oe": {NAME: "other_energy_today", FACTOR: 0.001},
        # aggregated energies in Wh?
        "pae": {NAME: "pv_yield", FACTOR: 0.001},  # 3045970 Wh
        "bac": {NAME: "charged_energy", FACTOR: 0.001},  # 12286143 Wh
        "bad": {NAME: "discharged_energy", FACTOR: 0.001},  # 8033557 Wh
    },
}


# Following is the consolidated mapping for all device types and messages
SOLIXMQTTMAP: Final[dict] = {
    # PPS C300 AC
    "A1722": {
        "0044": CMD_AC_CHARGE_LIMIT  # AC Recharge Limit: 100, 200, 300, 330 W
        | {
            "a2": {
                **CMD_AC_CHARGE_LIMIT["a2"],
                VALUE_OPTIONS: [100, 200, 300, 330],
            }
        },
        "004a": CMD_AC_OUTPUT_SWITCH,  # AC output switch: Disabled (0) or Enabled (1)
        "004b": CMD_DC_OUTPUT_SWITCH,  # DC output switch: Disabled (0) or Enabled (1)
        "004f": CMD_LIGHT_MODE  # LED mode: Off (0), Low (1), Medium (2), High (3)
        | {
            "a2": {
                **CMD_LIGHT_MODE["a2"],
                VALUE_OPTIONS: {"off": 0, "low": 1, "medium": 2, "high": 3},
            },
        },
        "0052": CMD_DISPLAY_SWITCH,  # Display switch: Disabled (0) or Enabled (1)
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": _A1722_0405,
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": _PPS_VERSIONS_0830,
    },
    # PPS C300X AC
    "A1723": {
        "0044": CMD_AC_CHARGE_LIMIT  # AC Recharge Limit: 100, 200, 300, 330 W
        | {
            "a2": {
                **CMD_AC_CHARGE_LIMIT["a2"],
                VALUE_OPTIONS: [100, 200, 300, 330],
            }
        },
        "004a": CMD_AC_OUTPUT_SWITCH,  # AC output switch: Disabled (0) or Enabled (1)
        "004b": CMD_DC_OUTPUT_SWITCH,  # DC output switch: Disabled (0) or Enabled (1)
        "004f": CMD_LIGHT_MODE  # LED mode: Off (0), Low (1), Medium (2), High (3)
        | {
            "a2": {
                **CMD_LIGHT_MODE["a2"],
                VALUE_OPTIONS: {"off": 0, "low": 1, "medium": 2, "high": 3},
            },
        },
        "0052": CMD_DISPLAY_SWITCH,  # Display switch: Disabled (0) or Enabled (1)
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": _A1722_0405,
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": _PPS_VERSIONS_0830,
    },
    # SOLIX C200(X) A1725
    "A1725": {
        "0045": CMD_DEVICE_TIMEOUT_MIN,  # Device timeout: 0 (Never), 30, 60, 120, 240, 360, 720, 1440 minutes
        "0046": CMD_DISPLAY_TIMEOUT_SEC,  # Options in seconds: 20, 30, 60, 300, 1800 seconds
        "004c": CMD_DISPLAY_MODE,  # Display brightness: Low (1), Medium (2), High (3)
        "0050": CMD_TEMP_UNIT,  # Temperature unit switch: Celsius (0) or Fahrenheit (1)
        "0052": CMD_DISPLAY_SWITCH,  # Display switch: Disabled (0) or Enabled (1)
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        "0401": _A1725_0401,  # Interval: Irregular, triggered on app/device actions
        "0405": _A1725_0405,  # Interval: ~3-5 seconds, but only with realtime trigger
    },
    # PPS C300 DC
    "A1726": {
        "0043": CMD_DC_OUTPUT_TIMEOUT_SEC  # DC output timeout: Custom Range 0-86100 seconds
        | {
            "a2": {
                **CMD_DC_OUTPUT_TIMEOUT_SEC["a2"],
                VALUE_MAX: 86100,
            },
        },
        "0045": CMD_DEVICE_TIMEOUT_MIN,  # Device timeout: 0 (Never), 30, 60, 120, 240, 360, 720, 1440 minutes
        "0046": CMD_DISPLAY_TIMEOUT_SEC,  # Options in seconds: 20, 30, 60, 300, 1800 seconds
        "004c": CMD_DISPLAY_MODE,  # Display brightness: Low (1), Medium (2), High (3)
        "004b": CMD_DC_OUTPUT_SWITCH,  # DC output switch: Disabled (0) or Enabled (1)
        "004f": CMD_LIGHT_MODE  # LED mode: Off (0), Low (1), Medium (2), High (3)
        | {
            "a2": {
                **CMD_LIGHT_MODE["a2"],
                VALUE_OPTIONS: {"off": 0, "low": 1, "medium": 2, "high": 3},
            },
        },
        "0050": CMD_TEMP_UNIT,  # Temperature unit switch: Celsius (0) or Fahrenheit (1)
        "0052": CMD_DISPLAY_SWITCH,  # Display switch: Disabled (0) or Enabled (1)
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        "0401": _A1728_0401,  # Interval: Irregular, triggered on app/device actions, no fixed interval
        "0404": _A1728_0404,  # Interval: Irregular, triggered on app action, no fixed interval
        "0405": _A1728_0405,  # Interval: ~3-5 seconds, but only with realtime trigger
        "0830": _PPS_VERSIONS_0830,  # Interval: Irregular, triggered on app actions, no fixed interval
    },
    # SOLIX C200 DC A1727
    "A1727": {
        "0045": CMD_DEVICE_TIMEOUT_MIN,  # Device timeout: 0 (Never), 30, 60, 120, 240, 360, 720, 1440 minutes
        "0046": CMD_DISPLAY_TIMEOUT_SEC,  # Options in seconds: 20, 30, 60, 300, 1800 seconds
        "004c": CMD_DISPLAY_MODE,  # Display brightness: Low (1), Medium (2), High (3)
        "0050": CMD_TEMP_UNIT,  # Temperature unit switch: Celsius (0) or Fahrenheit (1)
        "0052": CMD_DISPLAY_SWITCH,  # Display switch: Disabled (0) or Enabled (1)
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        "0401": _A1725_0401,  # Interval: Irregular, triggered on app/device actions
        "0405": _A1725_0405,  # Interval: ~3-5 seconds, but only with realtime trigger
    },
    # PPS C300X DC
    "A1728": {
        "0043": CMD_DC_OUTPUT_TIMEOUT_SEC  # DC output timeout: Custom Range 0-86100 seconds
        | {
            "a2": {
                **CMD_DC_OUTPUT_TIMEOUT_SEC["a2"],
                VALUE_MAX: 86100,
            },
        },
        "0045": CMD_DEVICE_TIMEOUT_MIN,  # Device timeout: 0 (Never), 30, 60, 120, 240, 360, 720, 1440 minutes
        "0046": CMD_DISPLAY_TIMEOUT_SEC,  # Options in seconds: 20, 30, 60, 300, 1800 seconds
        "004c": CMD_DISPLAY_MODE,  # Display brightness: Low (1), Medium (2), High (3)
        "004b": CMD_DC_OUTPUT_SWITCH,  # DC output switch: Disabled (0) or Enabled (1)
        "004f": CMD_LIGHT_MODE  # LED mode: Off (0), Low (1), Medium (2), High (3)
        | {
            "a2": {
                **CMD_LIGHT_MODE["a2"],
                VALUE_OPTIONS: {"off": 0, "low": 1, "medium": 2, "high": 3},
            },
        },
        "0050": CMD_TEMP_UNIT,  # Temperature unit switch: Celsius (0) or Fahrenheit (1)
        "0052": CMD_DISPLAY_SWITCH,  # Display switch: Disabled (0) or Enabled (1)
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        "0401": _A1728_0401,  # Interval: Irregular, triggered on app/device actions, no fixed interval
        "0404": _A1728_0404,  # Interval: Irregular, triggered on app action, no fixed interval
        "0405": _A1728_0405,  # Interval: ~3-5 seconds, but only with realtime trigger
        "0830": _PPS_VERSIONS_0830,  # Interval: Irregular, triggered on app actions, no fixed interval
    },
    # SOLIX C200X DC A1729
    "A1729": {
        "0045": CMD_DEVICE_TIMEOUT_MIN,  # Device timeout: 0 (Never), 30, 60, 120, 240, 360, 720, 1440 minutes
        "0046": CMD_DISPLAY_TIMEOUT_SEC,  # Options in seconds: 20, 30, 60, 300, 1800 seconds
        "004c": CMD_DISPLAY_MODE,  # Display brightness: Low (1), Medium (2), High (3)
        "0050": CMD_TEMP_UNIT,  # Temperature unit switch: Celsius (0) or Fahrenheit (1)
        "0052": CMD_DISPLAY_SWITCH,  # Display switch: Disabled (0) or Enabled (1)
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        "0401": _A1725_0401,  # Interval: Irregular, triggered on app/device actions
        "0405": _A1725_0405,  # Interval: ~3-5 seconds, but only with realtime trigger
        "0830": _PPS_VERSIONS_0830,  # Interval: Irregular, triggered on app actions, no fixed interval
    },
    # PPS C800
    "A1753": {
        "0042": CMD_AC_OUTPUT_TIMEOUT_SEC,  # field a2, range 0-86400, step 300, 0 = disabled.
        "0043": CMD_DC_OUTPUT_TIMEOUT_SEC,  # field a2, range 0-86400, step 300, 0 = disabled.
        "0044": CMD_AC_CHARGE_LIMIT  # AC Recharge Limit options as offered by app slider
        | {
            "a2": {
                **CMD_AC_CHARGE_LIMIT["a2"],
                VALUE_OPTIONS: [200, 300, 400, 500, 600, 700, 750],
            }
        },  # status field d1 verified with app changes 750/600/300/200
        "0045": CMD_DEVICE_TIMEOUT_MIN,  # Options in minutes: 0 (Never), 30, 60, 120, 240, 360, 720, 1440
        "0046": CMD_DISPLAY_TIMEOUT_SEC,  # Options in seconds: 20, 30, 60, 300, 1800 seconds
        "004a": CMD_AC_OUTPUT_SWITCH,  # status fields bb/d7 verified
        "004b": CMD_DC_OUTPUT_SWITCH,  # status fields cc/d8 verified
        "004c": CMD_DISPLAY_MODE
        | {
            "a2": {  # Display brightness: Low (1), Medium (2), High (3), no Off option
                **CMD_DISPLAY_MODE["a2"],
                VALUE_OPTIONS: {"low": 1, "medium": 2, "high": 3},
            },
        },
        "004f": CMD_LIGHT_MODE,  # status field dc verified: Off (0) - High (3), blinking mode (4)
        "0050": CMD_TEMP_UNIT,  # Temperature unit switch: Celsius (0) or Fahrenheit (1)
        "0052": CMD_DISPLAY_SWITCH,  # status field de verified
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        "005e": CMD_AC_FAST_CHARGE_SWITCH,  # Ultrafast charge switch: Disabled (0) or Enabled (1)
        "0076": CMD_DC_12V_OUTPUT_MODE,  # Normal (0), Smart (1), Status!! Normal (1), Smart (2)
        "0077": CMD_AC_OUTPUT_MODE,  # Normal (0), Smart (1), Status!! Normal (1), Smart (2)
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": _A1753_0405,
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": _PPS_VERSIONS_0830,
    },
    # PPS C800 Plus
    "A1754": {
        "0042": CMD_AC_OUTPUT_TIMEOUT_SEC,  # field a2, range 0-86400, step 300, 0 = disabled.
        "0043": CMD_DC_OUTPUT_TIMEOUT_SEC,  # field a2, range 0-86400, step 300, 0 = disabled.
        "0044": CMD_AC_CHARGE_LIMIT  # AC Recharge Limit options per App to be validated
        | {
            "a2": {
                **CMD_AC_CHARGE_LIMIT["a2"],
                VALUE_OPTIONS: [200, 300, 400, 500, 600, 700, 750],
            }
        },
        "0045": CMD_DEVICE_TIMEOUT_MIN,  # Options in minutes: 0 (Never), 30, 60, 120, 240, 360, 720, 1440
        "0046": CMD_DISPLAY_TIMEOUT_SEC,  # Options in seconds: 20, 30, 60, 300, 1800 seconds
        "004a": CMD_AC_OUTPUT_SWITCH,  # status fields bb/d7 verified
        "004b": CMD_DC_OUTPUT_SWITCH,  # status fields cc/d8 verified
        "004c": CMD_DISPLAY_MODE
        | {
            "a2": {  # Display brightness: Low (1), Medium (2), High (3), no Off option
                **CMD_DISPLAY_MODE["a2"],
                VALUE_OPTIONS: {"low": 1, "medium": 2, "high": 3},
            },
        },
        "004f": CMD_LIGHT_MODE,  # status field dc verified: Off (0) - High (3), blinking mode (4)
        "0050": CMD_TEMP_UNIT,  # Temperature unit switch: Celsius (0) or Fahrenheit (1)
        "0052": CMD_DISPLAY_SWITCH,
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        "005e": CMD_AC_FAST_CHARGE_SWITCH,  # Ultrafast charge switch: Disabled (0) or Enabled (1)
        "0076": CMD_DC_12V_OUTPUT_MODE,  # Normal (0), Smart (1), Status!! Normal (1), Smart (2)
        "0077": CMD_AC_OUTPUT_MODE,  # Normal (0), Smart (1), Status!! Normal (1), Smart (2)
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": _A1753_0405,
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": _PPS_VERSIONS_0830,
    },
    # PPS C800X
    "A1755": {
        "0042": CMD_AC_OUTPUT_TIMEOUT_SEC,  # field a2, range 0-86400, step 300, 0 = disabled.
        "0043": CMD_DC_OUTPUT_TIMEOUT_SEC,  # field a2, range 0-86400, step 300, 0 = disabled.
        "0044": CMD_AC_CHARGE_LIMIT  # AC Recharge Limit options per App to be validated
        | {
            "a2": {
                **CMD_AC_CHARGE_LIMIT["a2"],
                VALUE_OPTIONS: [200, 300, 400, 500, 600, 700, 750],
            }
        },  # status field d1 verified with app changes 750/600/300/200
        "0045": CMD_DEVICE_TIMEOUT_MIN,  # Options in minutes: 0 (Never), 30, 60, 120, 240, 360, 720, 1440
        "0046": CMD_DISPLAY_TIMEOUT_SEC,  # Options in seconds: 20, 30, 60, 300, 1800 seconds
        "004a": CMD_AC_OUTPUT_SWITCH,
        "004b": CMD_DC_OUTPUT_SWITCH,
        "004c": CMD_DISPLAY_MODE
        | {
            "a2": {  # Display brightness: Low (1), Medium (2), High (3), no Off option
                **CMD_DISPLAY_MODE["a2"],
                VALUE_OPTIONS: {"low": 1, "medium": 2, "high": 3},
            },
        },
        "004f": CMD_LIGHT_MODE,  # status field dc verified: Off (0) - High (3), blinking mode (4)
        "0050": CMD_TEMP_UNIT,  # Temperature unit switch: Celsius (0) or Fahrenheit (1)
        "0052": CMD_DISPLAY_SWITCH,
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        "005e": CMD_AC_FAST_CHARGE_SWITCH,  # Ultrafast charge switch: Disabled (0) or Enabled (1)
        "0076": CMD_DC_12V_OUTPUT_MODE,  # Normal (0), Smart (1), Status!! Normal (1), Smart (2)
        "0077": CMD_AC_OUTPUT_MODE,  # Normal (0), Smart (1), Status!! Normal (1), Smart (2)
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": _A1753_0405,
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": _PPS_VERSIONS_0830,
    },
    # PPS C1000(X) + B1000 Extension
    "A1761": {
        "0042": CMD_AC_OUTPUT_TIMEOUT_SEC,  # field a2, range 0-86400, step 300, 0 = disabled.
        "0043": CMD_DC_OUTPUT_TIMEOUT_SEC,  # field a2, range 0-86400, step 300, 0 = disabled.
        "0044": CMD_AC_CHARGE_LIMIT
        | {
            "a2": {
                **CMD_AC_CHARGE_LIMIT["a2"],
                VALUE_MIN: 100,
                VALUE_MAX: 1000,
                VALUE_STEP: 100,
            }
        },
        "0045": CMD_DEVICE_TIMEOUT_MIN,  # Options in minutes: 0 (Never), 30, 60, 120, 240, 360, 720, 1440
        "0046": CMD_DISPLAY_TIMEOUT_SEC,  # Options in seconds: 20, 30, 60, 300, 1800 seconds
        "004a": CMD_AC_OUTPUT_SWITCH,  # AC output switch: Disabled (0) or Enabled (1)
        "004b": CMD_DC_OUTPUT_SWITCH,  # DC output switch: Disabled (0) or Enabled (1)
        "004c": CMD_DISPLAY_MODE,  # Display brightness: Off (0), Low (1), Medium (2), High (3)
        "004f": CMD_LIGHT_MODE,  # LED mode: Off (0), Low (1), Medium (2), High (3), Blinking (4)
        "0050": CMD_TEMP_UNIT,  # Temperature unit switch: Celsius (0) or Fahrenheit (1)
        "0052": CMD_DISPLAY_SWITCH,  # Display switch: Disabled (0) or Enabled (1)
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        "005e": CMD_AC_FAST_CHARGE_SWITCH,  # Ultrafast charge switch: Disabled (0) or Enabled (1)
        "0076": CMD_DC_12V_OUTPUT_MODE_INV,  # Normal (1), Smart (0)
        "0077": CMD_AC_OUTPUT_MODE_INV,  # Normal (1), Smart (0); Status!! Normal (1), Smart (2)
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": _A1761_0405,
        # Interval: varies, probably upon change
        "0407": _0407,
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": _PPS_VERSIONS_0830,
    },
    # PPS C1000 Gen 2
    "A1763": {
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        "0101": {
            # AC command group
            COMMAND_LIST: [
                SolixMqttCommands.ac_output_switch,  # field a2
                SolixMqttCommands.ac_output_timeout_seconds,  # field a3
                SolixMqttCommands.ac_charge_limit,  # field a4
                SolixMqttCommands.ac_output_mode_select,  # field a6
                SolixMqttCommands.ac_fast_charge_switch,  # field a7
            ],
            SolixMqttCommands.ac_output_switch: CMD_COMMON_V2
            | {
                "a2": {
                    NAME: "set_ac_output_switch",  # Disable (0) | Enable (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "ac_output_power_switch",
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                },
            },
            SolixMqttCommands.ac_output_timeout_seconds: CMD_COMMON_V2
            | {
                "a3": {
                    NAME: "set_ac_output_timeout_seconds",  # Timeout seconds, custom range: 0-86400, step 300
                    TYPE: DeviceHexDataTypes.var.value,
                    STATE_NAME: "ac_output_timeout_seconds",
                    VALUE_MIN: 0,
                    VALUE_MAX: 86400,
                    VALUE_STEP: 300,
                },
            },
            SolixMqttCommands.ac_charge_limit: CMD_COMMON_V2
            | {
                "a4": {
                    NAME: "set_ac_input_limit",  # in W; min: 100, max: 1200, step: 100
                    TYPE: DeviceHexDataTypes.sile.value,
                    STATE_NAME: "ac_input_limit",
                    VALUE_MIN: 100,
                    VALUE_MAX: 1200,
                    VALUE_STEP: 100,
                },
            },
            SolixMqttCommands.ac_output_mode_select: CMD_COMMON_V2
            | {
                "a6": {
                    NAME: "set_ac_output_mode",  # Normal (0), Smart (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "ac_output_mode",
                    VALUE_OPTIONS: {"normal": 0, "smart": 1},
                },
            },
            SolixMqttCommands.ac_fast_charge_switch: CMD_COMMON_V2
            | {
                "a7": {
                    NAME: "set_ac_fast_charge_switch",  # Disable (0) | Enable (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "ac_fast_charge_switch",
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                },
            },
        },
        "0102": {
            # DC command group
            COMMAND_LIST: [
                SolixMqttCommands.dc_output_switch,  # field a2
                SolixMqttCommands.dc_output_timeout_seconds,  # field a3
                SolixMqttCommands.dc_12v_output_mode_select,  # field a4
            ],
            SolixMqttCommands.dc_output_switch: CMD_COMMON_V2
            | {
                "a2": {
                    NAME: "set_dc_output_switch",  # Disable (0) | Enable (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "dc_output_power_switch",
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                },
            },
            SolixMqttCommands.dc_output_timeout_seconds: CMD_COMMON_V2
            | {
                "a3": {
                    NAME: "set_dc_output_timeout_seconds",  # Timeout seconds, custom range: 0-86400, step 300
                    TYPE: DeviceHexDataTypes.var.value,
                    STATE_NAME: "dc_output_timeout_seconds",
                    VALUE_MIN: 0,
                    VALUE_MAX: 86400,
                    VALUE_STEP: 300,
                },
            },
            SolixMqttCommands.dc_12v_output_mode_select: CMD_COMMON_V2
            | {
                "a4": {
                    NAME: "set_dc_12v_output_mode",  # Normal (0), Smart (0)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "dc_12v_output_mode",
                    VALUE_OPTIONS: {"normal": 0, "smart": 1},
                },
            },
        },
        "0103": {
            # Other command group
            COMMAND_LIST: [
                SolixMqttCommands.display_switch,  # field a2
                SolixMqttCommands.display_mode_select,  # field a3
                SolixMqttCommands.display_timeout_seconds,  # field a4
                SolixMqttCommands.temp_unit_switch,  # field a5
                SolixMqttCommands.device_timeout_minutes,  # field a6
                SolixMqttCommands.port_memory_switch,  # field a8
                SolixMqttCommands.soc_limits,  # field aa, ab
            ],
            SolixMqttCommands.display_switch: CMD_COMMON_V2
            | {
                "a2": {
                    NAME: "set_display_switch",  # Off (0), On (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "display_switch",
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                },
            },
            SolixMqttCommands.display_mode_select: CMD_COMMON_V2
            | {
                "a3": {
                    NAME: "set_display_mode",  # Low (1), Medium (2), High (3)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "display_mode",
                    VALUE_OPTIONS: {"low": 1, "medium": 2, "high": 3},
                },
            },
            SolixMqttCommands.display_timeout_seconds: CMD_COMMON_V2
            | {
                "a4": {
                    NAME: "set_display_timeout_sec",  # 0 (Never), 10, 20, 30, 60, 300, 1800
                    TYPE: DeviceHexDataTypes.sile.value,
                    STATE_NAME: "display_timeout_seconds",
                    VALUE_OPTIONS: [0, 10, 20, 30, 60, 300, 1800],
                },
            },
            SolixMqttCommands.temp_unit_switch: CMD_TEMP_UNIT_V2,  # Celsius (0) | Fahrenheit (1)
            SolixMqttCommands.device_timeout_minutes: CMD_COMMON_V2
            | {
                "a6": {
                    NAME: "set_device_timeout_min",  # 0 (Never), 30, 60, 120, 240, 360, 720, 1440
                    TYPE: DeviceHexDataTypes.sile.value,
                    STATE_NAME: "device_timeout_minutes",
                    VALUE_OPTIONS: [0, 30, 60, 120, 240, 360, 720, 1440],
                },
            },
            SolixMqttCommands.port_memory_switch: CMD_COMMON_V2
            | {
                "a8": {
                    NAME: "set_port_memory_switch",  # Off (0), On (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "port_memory_switch",
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                },
            },
            SolixMqttCommands.soc_limits: CMD_SOC_LIMITS_V2,
            # Contains fields aa ab for the limits
            # aa = max_soc: 80, 85, 90, 95, 100 %
            # ab = min_soc: 1, 5, 10, 15, 20 %
        },
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0421": _A1763_0421,
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": _PPS_VERSIONS_0830,
        # Interval: ~300 seconds
        "0889": {
            "a4": {NAME: "0889_unknown_1?"},
            "a5": {NAME: "0889_unknown_2?"},
            "a6": {NAME: "0889_unknown_3?"},
            "fd": {NAME: "0889_timestamp?"},
        },
        # Interval: Irregular, maybe on changes or as response to App status request? Same content as 0421
        "0900": _A1763_0421,
    },
    # PPS C1000X Gen 2
    "A1765": {
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        "0101": {
            # AC command group
            COMMAND_LIST: [
                SolixMqttCommands.ac_output_switch,  # field a2
                SolixMqttCommands.ac_output_timeout_seconds,  # field a3
                SolixMqttCommands.ac_charge_limit,  # field a4
                SolixMqttCommands.ac_output_mode_select,  # field a6
                SolixMqttCommands.ac_fast_charge_switch,  # field a7
            ],
            SolixMqttCommands.ac_output_switch: CMD_COMMON_V2
            | {
                "a2": {
                    NAME: "set_ac_output_switch",  # Disable (0) | Enable (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "ac_output_power_switch",
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                },
            },
            SolixMqttCommands.ac_output_timeout_seconds: CMD_COMMON_V2
            | {
                "a3": {
                    NAME: "set_ac_output_timeout_seconds",  # Timeout seconds, custom range: 0-86400, step 300
                    TYPE: DeviceHexDataTypes.var.value,
                    STATE_NAME: "ac_output_timeout_seconds",
                    VALUE_MIN: 0,
                    VALUE_MAX: 86400,
                    VALUE_STEP: 300,
                },
            },
            SolixMqttCommands.ac_charge_limit: CMD_COMMON_V2
            | {
                "a4": {
                    NAME: "set_ac_input_limit",  # in W; min: 100, max: 1200, step: 100
                    TYPE: DeviceHexDataTypes.sile.value,
                    STATE_NAME: "ac_input_limit",
                    VALUE_MIN: 100,
                    VALUE_MAX: 1200,
                    VALUE_STEP: 100,
                },
            },
            SolixMqttCommands.ac_output_mode_select: CMD_COMMON_V2
            | {
                "a6": {
                    NAME: "set_ac_output_mode",  # Normal (0), Smart (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "ac_output_mode",
                    VALUE_OPTIONS: {"normal": 0, "smart": 1},
                },
            },
            SolixMqttCommands.ac_fast_charge_switch: CMD_COMMON_V2
            | {
                "a7": {
                    NAME: "set_ac_fast_charge_switch",  # Disable (0) | Enable (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "ac_fast_charge_switch",
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                },
            },
        },
        "0102": {
            # DC command group
            COMMAND_LIST: [
                SolixMqttCommands.dc_output_switch,  # field a2
                SolixMqttCommands.dc_output_timeout_seconds,  # field a3
                SolixMqttCommands.dc_12v_output_mode_select,  # field a4
            ],
            SolixMqttCommands.dc_output_switch: CMD_COMMON_V2
            | {
                "a2": {
                    NAME: "set_dc_output_switch",  # Disable (0) | Enable (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "dc_output_power_switch",
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                },
            },
            SolixMqttCommands.dc_output_timeout_seconds: CMD_COMMON_V2
            | {
                "a3": {
                    NAME: "set_dc_output_timeout_seconds",  # Timeout seconds, custom range: 0-86400, step 300
                    TYPE: DeviceHexDataTypes.var.value,
                    STATE_NAME: "dc_output_timeout_seconds",
                    VALUE_MIN: 0,
                    VALUE_MAX: 86400,
                    VALUE_STEP: 300,
                },
            },
            SolixMqttCommands.dc_12v_output_mode_select: CMD_COMMON_V2
            | {
                "a4": {
                    NAME: "set_dc_12v_output_mode",  # Normal (0), Smart (0)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "dc_12v_output_mode",
                    VALUE_OPTIONS: {"normal": 0, "smart": 1},
                },
            },
        },
        "0103": {
            # Other command group
            COMMAND_LIST: [
                SolixMqttCommands.display_switch,  # field a2
                SolixMqttCommands.display_mode_select,  # field a3
                SolixMqttCommands.display_timeout_seconds,  # field a4
                SolixMqttCommands.temp_unit_switch,  # field a5
                SolixMqttCommands.device_timeout_minutes,  # field a6
                SolixMqttCommands.port_memory_switch,  # field a8
                SolixMqttCommands.soc_limits,  # field aa, ab
            ],
            SolixMqttCommands.display_switch: CMD_COMMON_V2
            | {
                "a2": {
                    NAME: "set_display_switch",  # Off (0), On (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "display_switch",
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                },
            },
            SolixMqttCommands.display_mode_select: CMD_COMMON_V2
            | {
                "a3": {
                    NAME: "set_display_mode",  # Low (1), Medium (2), High (3)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "display_mode",
                    VALUE_OPTIONS: {"low": 1, "medium": 2, "high": 3},
                },
            },
            SolixMqttCommands.display_timeout_seconds: CMD_COMMON_V2
            | {
                "a4": {
                    NAME: "set_display_timeout_sec",  # 0 (Never), 10, 20, 30, 60, 300, 1800
                    TYPE: DeviceHexDataTypes.sile.value,
                    STATE_NAME: "display_timeout_seconds",
                    VALUE_OPTIONS: [0, 10, 20, 30, 60, 300, 1800],
                },
            },
            SolixMqttCommands.temp_unit_switch: CMD_TEMP_UNIT_V2,  # Celsius (0) | Fahrenheit (1)
            SolixMqttCommands.device_timeout_minutes: CMD_COMMON_V2
            | {
                "a6": {
                    NAME: "set_device_timeout_min",  # 0 (Never), 30, 60, 120, 240, 360, 720, 1440
                    TYPE: DeviceHexDataTypes.sile.value,
                    STATE_NAME: "device_timeout_minutes",
                    VALUE_OPTIONS: [0, 30, 60, 120, 240, 360, 720, 1440],
                },
            },
            SolixMqttCommands.port_memory_switch: CMD_COMMON_V2
            | {
                "a8": {
                    NAME: "set_port_memory_switch",  # Off (0), On (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "port_memory_switch",
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                },
            },
            SolixMqttCommands.soc_limits: CMD_SOC_LIMITS_V2,
            # Contains fields aa ab for the limits
            # aa = max_soc: 80, 85, 90, 95, 100 %
            # ab = min_soc: 1, 5, 10, 15, 20 %
        },
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0421": _A1763_0421,
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": _PPS_VERSIONS_0830,
        # Interval: ~300 seconds
        "0889": {
            "a4": {NAME: "0889_unknown_1?"},
            "a5": {NAME: "0889_unknown_2?"},
            "a6": {NAME: "0889_unknown_3?"},
            "fd": {NAME: "0889_timestamp?"},
        },
        # Interval: Irregular, maybe on changes or as response to App status request? Same content as 0421
        "0900": _A1763_0421,
    },
    # PPS C2000 Gen 2
    "A1783": {
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0421 etc
        "005e": {
            # Backup charge plan command group
            COMMAND_LIST: [
                SolixMqttCommands.backup_charge_storm_guard,  # field a3, a4, a5
                SolixMqttCommands.backup_charge_plan,  # field a3-a5
                SolixMqttCommands.backup_charge_timestamps,  # field a6-a8
            ],
            SolixMqttCommands.backup_charge_storm_guard: CMD_BACKUP_STORM_GUARD_SWITCH_V2,
            SolixMqttCommands.backup_charge_plan: CMD_BACKUP_SWITCH_V2,
            SolixMqttCommands.backup_charge_timestamps: CMD_BACKUP_PLAN_TIMESTAMPS_V2,
        },
        "0090": {
            # TOU command group
            COMMAND_LIST: [
                SolixMqttCommands.pps_usage_mode,  # field a2
            ],
            SolixMqttCommands.pps_usage_mode: CMD_COMMON_V2
            | {
                "a2": {  # 0=Standard, 1=Time-of-Use
                    NAME: "set_usage_mode",
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "usage_mode",
                    VALUE_OPTIONS: {
                        "standard": 0,  # UPS mode
                        "time_of_use": 1,
                    },
                },
            },
        },
        "0101": {
            # AC command group
            COMMAND_LIST: [
                SolixMqttCommands.ac_output_switch,  # field a2
                SolixMqttCommands.ac_output_timeout_seconds,  # field a3
                SolixMqttCommands.ac_charge_limit,  # field a4
                SolixMqttCommands.ac_output_mode_select,  # field a6
                SolixMqttCommands.ac_fast_charge_switch,  # field a7
            ],
            SolixMqttCommands.ac_output_switch: CMD_COMMON_V2
            | {
                "a2": {
                    NAME: "set_ac_output_switch",  # Disable (0) | Enable (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "ac_output_power_switch",
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                },
            },
            SolixMqttCommands.ac_charge_limit: CMD_COMMON_V2
            | {
                "a4": {
                    NAME: "set_ac_input_limit",  # in W; min: 200, max: 1800-2400, step: 100
                    TYPE: DeviceHexDataTypes.sile.value,
                    STATE_NAME: "ac_input_limit",
                    VALUE_MIN: 200,
                    VALUE_MAX: 1800,  # lowest limit for all variants
                    VALUE_MAX_STATE: "ac_input_limit_max",  # adopt limit based on device variant
                    VALUE_STEP: 100,
                },
            },
            SolixMqttCommands.ac_output_timeout_seconds: CMD_COMMON_V2
            | {
                "a3": {
                    NAME: "set_ac_output_timeout_seconds",  # Timeout seconds, custom range: 0-86400, step 300
                    TYPE: DeviceHexDataTypes.var.value,
                    STATE_NAME: "ac_output_timeout_seconds",
                    VALUE_MIN: 0,
                    VALUE_MAX: 86400,
                    VALUE_STEP: 300,
                },
            },
            SolixMqttCommands.ac_output_mode_select: CMD_COMMON_V2
            | {
                "a6": {
                    NAME: "set_ac_output_mode",  # Normal (0), Smart (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "ac_output_mode",
                    VALUE_OPTIONS: {"normal": 0, "smart": 1},
                },
            },
            SolixMqttCommands.ac_fast_charge_switch: CMD_COMMON_V2
            | {
                "a7": {
                    NAME: "set_ac_fast_charge_switch",  # Disable (0) | Enable (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "ac_fast_charge_switch",
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                },
            },
        },
        "0102": {
            # DC command group
            COMMAND_LIST: [
                SolixMqttCommands.dc_output_switch,  # field a2
                SolixMqttCommands.dc_12v_output_mode_select,  # field a4
            ],
            SolixMqttCommands.dc_output_switch: CMD_COMMON_V2
            | {
                "a2": {
                    NAME: "set_dc_output_switch",  # Disable (0) | Enable (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "dc_output_power_switch",
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                },
            },
            SolixMqttCommands.dc_12v_output_mode_select: CMD_COMMON_V2
            | {
                "a4": {
                    NAME: "set_dc_12v_output_mode",  # Normal (0), Smart (0)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "dc_12v_output_mode",
                    VALUE_OPTIONS: {"normal": 0, "smart": 1},
                },
            },
        },
        "0103": {
            # Other command group
            COMMAND_LIST: [
                SolixMqttCommands.display_switch,  # field a2
                SolixMqttCommands.display_mode_select,  # field a3
                SolixMqttCommands.display_timeout_seconds,  # field a4
                SolixMqttCommands.temp_unit_switch,  # field a5
                SolixMqttCommands.device_timeout_minutes,  # field a6
                SolixMqttCommands.port_memory_switch,  # field a8
                SolixMqttCommands.soc_limits,  # field aa, ab
            ],
            SolixMqttCommands.display_switch: CMD_COMMON_V2
            | {
                "a2": {
                    NAME: "set_display_switch",  # Off (0), On (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "display_switch",
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                },
            },
            SolixMqttCommands.display_mode_select: CMD_COMMON_V2
            | {
                "a3": {
                    NAME: "set_display_mode",  # Low (1), Medium (2), High (3)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "display_mode",
                    VALUE_OPTIONS: {"low": 1, "medium": 2, "high": 3},
                },
            },
            SolixMqttCommands.display_timeout_seconds: CMD_COMMON_V2
            | {
                "a4": {
                    NAME: "set_display_timeout_sec",  # 0 (Never), 10, 20, 30, 60, 300, 1800
                    TYPE: DeviceHexDataTypes.sile.value,
                    STATE_NAME: "display_timeout_seconds",
                    VALUE_OPTIONS: [0, 10, 20, 30, 60, 300, 1800],
                },
            },
            SolixMqttCommands.temp_unit_switch: CMD_TEMP_UNIT_V2,  # Celsius (0) | Fahrenheit (1)
            SolixMqttCommands.device_timeout_minutes: CMD_COMMON_V2
            | {
                "a6": {
                    NAME: "set_device_timeout_min",  # 0 (Never), 30, 60, 120, 240, 360, 720, 1440
                    TYPE: DeviceHexDataTypes.sile.value,
                    STATE_NAME: "device_timeout_minutes",
                    VALUE_OPTIONS: [0, 30, 60, 120, 240, 360, 720, 1440],
                },
            },
            SolixMqttCommands.port_memory_switch: CMD_COMMON_V2
            | {
                "a8": {
                    NAME: "set_port_memory_switch",  # Off (0), On (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "port_memory_switch",
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                },
            },
            SolixMqttCommands.soc_limits: CMD_SOC_LIMITS_V2,
            # Contains fields aa ab for the limits
            # aa = max_soc: 80, 85, 90, 95, 100 %
            # ab = min_soc: 1, 5, 10, 15, 20 %
        },
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0421": _A1783_0421,
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": _PPS_VERSIONS_0830,
        # Interval: Irregular, maybe on changes or as response to App status request? Same content as 0421
        "0900": _A1783_0421,
    },
    # PPS C2000X Gen 2
    "A1785": {
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0421 etc
        "005e": {
            # Backup charge plan command group
            COMMAND_LIST: [
                SolixMqttCommands.backup_charge_storm_guard,  # field a3, a4, a5
                SolixMqttCommands.backup_charge_plan,  # field a3-a5
                SolixMqttCommands.backup_charge_timestamps,  # field a6-a8
            ],
            SolixMqttCommands.backup_charge_storm_guard: CMD_BACKUP_STORM_GUARD_SWITCH_V2,
            SolixMqttCommands.backup_charge_plan: CMD_BACKUP_SWITCH_V2,
            SolixMqttCommands.backup_charge_timestamps: CMD_BACKUP_PLAN_TIMESTAMPS_V2,
        },
        "0090": {
            # TOU command group
            COMMAND_LIST: [
                SolixMqttCommands.pps_usage_mode,  # field a2
                SolixMqttCommands.backup_soc,  # field a5
            ],
            SolixMqttCommands.pps_usage_mode: CMD_COMMON_V2
            | {
                "a2": {  # 0=Standard, 1=Time-of-Use
                    NAME: "set_usage_mode",
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "usage_mode",
                    VALUE_OPTIONS: {
                        "standard": 0,  # UPS mode
                        "time_of_use": 1,
                    },
                },
            },
            SolixMqttCommands.backup_soc: CMD_COMMON_V2
            | {
                "a5": {
                    NAME: "set_backup_soc",  # range as [min_soc + 5, max_soc], step 1%
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "backup_soc",
                    VALUE_MIN: 5,
                    VALUE_MAX: 100,
                    VALUE_STEP: 1,
                    STATE_CONVERTER: lambda value, state, cache: (
                        value
                        if value is not None
                        # ensure backup is min + 5 < backup <= max if not specified
                        else min(
                            int(cache.get("max_soc") or 80),
                            max(
                                int(cache.get("power_cutoff") or 20) + 5,
                                int(state),
                            ),
                        )
                        if state is not None
                        and str(state).replace(".", "", 1).isdigit()
                        else None
                    ),
                    VALUE_MIN_STATE: "power_cutoff",
                    VALUE_MAX_STATE: "max_soc",
                },
            },
        },
        "0101": {
            # AC command group
            COMMAND_LIST: [
                SolixMqttCommands.ac_output_switch,  # field a2
                SolixMqttCommands.ac_output_timeout_seconds,  # field a3
                SolixMqttCommands.ac_charge_limit,  # field a4
                SolixMqttCommands.ac_output_mode_select,  # field a6
                SolixMqttCommands.ac_fast_charge_switch,  # field a7
            ],
            SolixMqttCommands.ac_output_switch: CMD_COMMON_V2
            | {
                "a2": {
                    NAME: "set_ac_output_switch",  # Disable (0) | Enable (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "ac_output_power_switch",
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                },
            },
            SolixMqttCommands.ac_charge_limit: CMD_COMMON_V2
            | {
                "a4": {
                    NAME: "set_ac_input_limit",  # in W; min: 200, max: 1800-2400, step: 100
                    TYPE: DeviceHexDataTypes.sile.value,
                    STATE_NAME: "ac_input_limit",
                    VALUE_MIN: 200,
                    VALUE_MAX: 1800,  # lowest limit for all variants
                    VALUE_MAX_STATE: "ac_input_limit_max",  # adopt limit based on device variant
                    VALUE_STEP: 100,
                },
            },
            SolixMqttCommands.ac_output_timeout_seconds: CMD_COMMON_V2
            | {
                "a3": {
                    NAME: "set_ac_output_timeout_seconds",  # Timeout seconds, custom range: 0-86400, step 300
                    TYPE: DeviceHexDataTypes.var.value,
                    STATE_NAME: "ac_output_timeout_seconds",
                    VALUE_MIN: 0,
                    VALUE_MAX: 86400,
                    VALUE_STEP: 300,
                },
            },
            SolixMqttCommands.ac_output_mode_select: CMD_COMMON_V2
            | {
                "a6": {
                    NAME: "set_ac_output_mode",  # Normal (0), Smart (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "ac_output_mode",
                    VALUE_OPTIONS: {"normal": 0, "smart": 1},
                },
            },
            SolixMqttCommands.ac_fast_charge_switch: CMD_COMMON_V2
            | {
                "a7": {
                    NAME: "set_ac_fast_charge_switch",  # Disable (0) | Enable (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "ac_fast_charge_switch",
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                },
            },
        },
        "0102": {
            # DC command group
            COMMAND_LIST: [
                SolixMqttCommands.dc_output_switch,  # field a2
                SolixMqttCommands.dc_12v_output_mode_select,  # field a4
            ],
            SolixMqttCommands.dc_output_switch: CMD_COMMON_V2
            | {
                "a2": {
                    NAME: "set_dc_output_switch",  # Disable (0) | Enable (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "dc_output_power_switch",
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                },
            },
            SolixMqttCommands.dc_12v_output_mode_select: CMD_COMMON_V2
            | {
                "a4": {
                    NAME: "set_dc_12v_output_mode",  # Normal (0), Smart (0)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "dc_12v_output_mode",
                    VALUE_OPTIONS: {"normal": 0, "smart": 1},
                },
            },
        },
        "0103": {
            # Other command group
            COMMAND_LIST: [
                SolixMqttCommands.display_switch,  # field a2
                SolixMqttCommands.display_mode_select,  # field a3
                SolixMqttCommands.display_timeout_seconds,  # field a4
                SolixMqttCommands.temp_unit_switch,  # field a5
                SolixMqttCommands.device_timeout_minutes,  # field a6
                SolixMqttCommands.port_memory_switch,  # field a8
                SolixMqttCommands.soc_limits,  # field aa, ab
            ],
            SolixMqttCommands.display_switch: CMD_COMMON_V2
            | {
                "a2": {
                    NAME: "set_display_switch",  # Off (0), On (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "display_switch",
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                },
            },
            SolixMqttCommands.display_mode_select: CMD_COMMON_V2
            | {
                "a3": {
                    NAME: "set_display_mode",  # Low (1), Medium (2), High (3)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "display_mode",
                    VALUE_OPTIONS: {"low": 1, "medium": 2, "high": 3},
                },
            },
            SolixMqttCommands.display_timeout_seconds: CMD_COMMON_V2
            | {
                "a4": {
                    NAME: "set_display_timeout_sec",  # 0 (Never), 10, 20, 30, 60, 300, 1800
                    TYPE: DeviceHexDataTypes.sile.value,
                    STATE_NAME: "display_timeout_seconds",
                    VALUE_OPTIONS: [0, 10, 20, 30, 60, 300, 1800],
                },
            },
            SolixMqttCommands.temp_unit_switch: CMD_TEMP_UNIT_V2,  # Celsius (0) | Fahrenheit (1)
            SolixMqttCommands.device_timeout_minutes: CMD_COMMON_V2
            | {
                "a6": {
                    NAME: "set_device_timeout_min",  # 0 (Never), 30, 60, 120, 240, 360, 720, 1440
                    TYPE: DeviceHexDataTypes.sile.value,
                    STATE_NAME: "device_timeout_minutes",
                    VALUE_OPTIONS: [0, 30, 60, 120, 240, 360, 720, 1440],
                },
            },
            SolixMqttCommands.port_memory_switch: CMD_COMMON_V2
            | {
                "a8": {
                    NAME: "set_port_memory_switch",  # Off (0), On (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "port_memory_switch",
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                },
            },
            SolixMqttCommands.soc_limits: CMD_SOC_LIMITS_V2,
            # Contains fields aa ab for the limits
            # aa = max_soc: 80, 85, 90, 95, 100 %
            # ab = min_soc: 1, 5, 10, 15, 20 %
        },
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0421": _A1783_0421,
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": _PPS_VERSIONS_0830,
        # Interval: Irregular, maybe on changes or as response to App status request? Same content as 0421
        "0900": _A1783_0421,
    },
    # PPS S2000 - matches A1783 (C2000 Gen 2); 0101-0103 controls inherited, not yet validated
    "AS220": {
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        "005e": {
            # Backup charge plan command group
            COMMAND_LIST: [
                SolixMqttCommands.backup_charge_storm_guard,  # field a3, a4, a5
                SolixMqttCommands.backup_charge_plan,  # field a3-a5
                SolixMqttCommands.backup_charge_timestamps,  # field a6-a8
            ],
            SolixMqttCommands.backup_charge_storm_guard: CMD_BACKUP_STORM_GUARD_SWITCH_V2,
            SolixMqttCommands.backup_charge_plan: CMD_BACKUP_SWITCH_V2,
            SolixMqttCommands.backup_charge_timestamps: CMD_BACKUP_PLAN_TIMESTAMPS_V2,
        },
        "0090": {
            # TOU command group
            COMMAND_LIST: [
                SolixMqttCommands.pps_usage_mode,  # field a2
                SolixMqttCommands.pps_tou_schedule,  # field a2, a3, a4, a6, a7 => CLOUD CMD!!!
                SolixMqttCommands.backup_soc,  # field a5
            ],
            SolixMqttCommands.pps_usage_mode: CMD_PPS_USAGE_MODE_V2,  # 0=Standard, 1=Time-of-Use, 2=Self-Consumption, 3=Custom
            SolixMqttCommands.pps_tou_schedule: CMD_TOU_PLAN_V2,
            SolixMqttCommands.backup_soc: CMD_COMMON_V2
            | {
                "a5": {
                    NAME: "set_backup_soc",  # range as [min_soc + 5, max_soc], step 1%
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "backup_soc",
                    VALUE_MIN: 5,
                    VALUE_MAX: 100,
                    VALUE_STEP: 1,
                    STATE_CONVERTER: lambda value, state, cache: (
                        value
                        if value is not None
                        # ensure backup is min + 5 < backup <= max if not specified
                        else min(
                            int(cache.get("max_soc") or 80),
                            max(
                                int(cache.get("power_cutoff") or 20) + 5,
                                int(state),
                            ),
                        )
                        if state is not None
                        and str(state).replace(".", "", 1).isdigit()
                        else None
                    ),
                    VALUE_MIN_STATE: "power_cutoff",
                    VALUE_MAX_STATE: "max_soc",
                },
            },
        },
        "0093": {
            COMMAND_LIST: [
                SolixMqttCommands.pps_custom_schedule,  # field a2
                SolixMqttCommands.pps_output_schedule,  # field a3
                SolixMqttCommands.silent_schedule,  # field a4
            ],
            SolixMqttCommands.pps_custom_schedule: CMD_COMMON_V2
            | {
                "a2": {
                    NAME: "set_custom_mode_schedule",
                    TYPE: DeviceHexDataTypes.bin.value,
                    STATE_NAME: "custom_mode_schedule",
                    STATE_CONVERTER: lambda value, state, cache: (
                        convert_pps_custom_schedule(value)
                        if value is not None
                        else convert_pps_custom_schedule(state)
                    ),
                },
            },
            SolixMqttCommands.pps_output_schedule: CMD_COMMON_V2
            | {
                "a2": {
                    NAME: "set_ac_output_schedule",
                    TYPE: DeviceHexDataTypes.bin.value,
                    STATE_NAME: "ac_output_schedule",
                    STATE_CONVERTER: lambda value, state, cache: (
                        convert_pps_output_schedule(value)
                        if value is not None
                        else convert_pps_output_schedule(state)
                    ),
                },
            },
            SolixMqttCommands.silent_schedule: CMD_COMMON_V2
            | {
                "a4": {
                    TYPE: DeviceHexDataTypes.bin.value,
                    LENGTH: 6,
                    BYTES: {
                        "00": {
                            NAME: "set_silent_mode_switch",  # Disable (0) | Enable (1)
                            TYPE: DeviceHexDataTypes.ui.value,
                            STATE_NAME: "silent_mode_switch",
                            VALUE_STATE: "silent_mode_switch",
                            VALUE_OPTIONS: {"off": 0, "on": 1},
                        },
                        "01": {
                            NAME: "set_silent_mode_weekdays",  # Bitmask: 0:sun:sat:fri:thu:wed:tue:mon
                            TYPE: DeviceHexDataTypes.bin.value,
                            LENGTH: 1,
                            STATE_CONVERTER: lambda value, state, cache: (
                                convert_weekdays(value)
                                if value is not None
                                else convert_weekdays(state)
                            ),
                            STATE_NAME: "silent_mode_weekdays",
                            VALUE_STATE: "silent_mode_weekdays",
                        },
                        "02": {
                            NAME: "set_silent_mode_start_minutes",  # start, minutes of day
                            TYPE: DeviceHexDataTypes.sile.value,
                            SIGNED: False,
                            STATE_NAME: "silent_mode_start_minutes",
                            VALUE_STATE: "silent_mode_start_minutes",
                            VALUE_MIN: 0,
                            VALUE_MAX: 1339,
                        },
                        "04": {
                            NAME: "set_silent_mode_end_minutes",  # end, minutes of day
                            TYPE: DeviceHexDataTypes.sile.value,
                            SIGNED: False,
                            STATE_NAME: "silent_mode_end_minutes",
                            VALUE_STATE: "silent_mode_end_minutes",
                            VALUE_MIN: 0,
                            VALUE_MAX: 1440,
                        },
                    },
                },
            },
        },
        "0100": CMD_STATUS_REQUEST
        | {  # Device status request (one time status messages 0900)
            "a2": {
                TYPE: DeviceHexDataTypes.bin.value,
                LENGTH: 1,
                BYTES: {
                    "00": {
                        NAME: "push_status_request",  # Push (1)
                        TYPE: DeviceHexDataTypes.ui.value,
                        VALUE_DEFAULT: 1,
                    },
                },
            }
        },
        "0101": {
            # AC command group
            COMMAND_LIST: [
                SolixMqttCommands.ac_output_switch,  # field a2
                SolixMqttCommands.ac_output_timer,  # field a3
                SolixMqttCommands.ac_charge_limit,  # field a4
                SolixMqttCommands.ac_fast_charge_switch,  # field a7
                SolixMqttCommands.ac_output_timeout_minutes,  # Smart timeout field aa
            ],
            SolixMqttCommands.ac_output_switch: CMD_COMMON_V2
            | {
                "a2": {
                    NAME: "set_ac_output_switch",  # Disable (0) | Enable (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "ac_output_power_switch",
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                },
            },
            SolixMqttCommands.ac_output_timer: CMD_COMMON_V2
            | {
                "a3": {
                    NAME: "set_ac_output_timer_seconds",  # AC Out countdown seconds, custom range: 0-86400, step 300
                    TYPE: DeviceHexDataTypes.var.value,
                    STATE_NAME: "ac_output_timer_seconds",
                    VALUE_MIN: 0,
                    VALUE_MAX: 86400,
                    VALUE_STEP: 300,
                },
            },
            SolixMqttCommands.ac_charge_limit: CMD_COMMON_V2
            | {
                "a4": {
                    NAME: "set_ac_input_limit",  # in W; min: 100, max: 1200, step: 100
                    TYPE: DeviceHexDataTypes.sile.value,
                    STATE_NAME: "ac_input_limit",
                    VALUE_MIN: 100,
                    VALUE_MAX: 1200,  # lowest limit
                    VALUE_MAX_STATE: "ac_input_limit_max",  # adopt limit based on device variant
                    VALUE_STEP: 100,
                },
            },
            SolixMqttCommands.ac_fast_charge_switch: CMD_COMMON_V2
            | {
                "a7": {
                    NAME: "set_ac_fast_charge_switch",  # Disable (0) | Enable (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "ac_fast_charge_switch",
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                },
            },
            SolixMqttCommands.ac_output_timeout_minutes: CMD_COMMON_V2
            | {
                "aa": {
                    NAME: "set_ac_output_timeout_minutes",  # App Smart AC Output Mode, Timeout Never(0), 15m, 30m, 1h, 2h, 4h, 6h, 8h, 10h, 12h, 24h
                    TYPE: DeviceHexDataTypes.sile.value,
                    STATE_NAME: "ac_output_timeout_minutes",
                    VALUE_OPTIONS: [0, 15, 30, 60, 120, 240, 360, 480, 600, 720, 1440],
                },
            },
        },
        "0103": {
            # Other command group
            COMMAND_LIST: [
                SolixMqttCommands.display_switch,  # field a2
                SolixMqttCommands.display_mode_select,  # field a3
                SolixMqttCommands.display_timeout_seconds,  # field a4
                SolixMqttCommands.temp_unit_switch,  # field a5
                SolixMqttCommands.device_timeout_minutes,  # field a6
                SolixMqttCommands.port_memory_switch,  # field a8
                SolixMqttCommands.soc_limits,  # field aa, ab
            ],
            SolixMqttCommands.display_switch: CMD_COMMON_V2
            | {
                "a2": {
                    NAME: "set_display_switch",  # Off (0), On (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "display_switch",
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                },
            },
            SolixMqttCommands.display_mode_select: CMD_COMMON_V2
            | {
                "a3": {
                    NAME: "set_display_mode",  # Low (1), Medium (2), High (3)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "display_mode",
                    VALUE_OPTIONS: {"low": 1, "medium": 2, "high": 3},
                },
            },
            SolixMqttCommands.display_timeout_seconds: CMD_COMMON_V2
            | {
                "a4": {
                    NAME: "set_display_timeout_sec",  # 10, 20, 30, 60, 300, 1800
                    TYPE: DeviceHexDataTypes.sile.value,
                    STATE_NAME: "display_timeout_seconds",
                    VALUE_OPTIONS: [10, 20, 30, 60, 300, 1800],
                },
            },
            SolixMqttCommands.temp_unit_switch: CMD_TEMP_UNIT_V2,  # Celsius (0) | Fahrenheit (1)
            SolixMqttCommands.device_timeout_minutes: CMD_COMMON_V2
            | {
                "a6": {
                    NAME: "set_device_timeout_min",  # 0 (Never), 30, 60, 120, 240, 360, 720, 1440
                    TYPE: DeviceHexDataTypes.sile.value,
                    STATE_NAME: "device_timeout_minutes",
                    VALUE_OPTIONS: [0, 30, 60, 120, 240, 360, 720, 1440],
                },
            },
            SolixMqttCommands.port_memory_switch: CMD_COMMON_V2
            | {
                "a8": {
                    NAME: "set_port_memory_switch",  # Off (0), On (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "port_memory_switch",
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                },
            },
            SolixMqttCommands.soc_limits: CMD_SOC_LIMITS_V2,
            # Contains fields aa ab for the limits
            # aa = max_soc: 80, 85, 90, 95, 100 %
            # ab = min_soc: 1, 5, 10, 15, 20 %
        },
        # Interval: Irregular, triggered on app actions
        "0402": {
            "a2": {
                NAME: "device_sn",
                TYPE: DeviceHexDataTypes.str.value,
            },
            "fe": {NAME: "msg_timestamp"},
        },
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0421": _AS220_0421,
        # Interval: irregular, may only be sent once backup plan active
        "0425": {
            "a2": {
                NAME: "storm_guard_status?"
            },  # 10 and 11 seen, same value as in 0c25 cloud command
            "a3": {NAME: "backup_start_timestamp", SIGNED: False},
            "a4": {NAME: "backup_end_timestamp", SIGNED: False},
        },
        # Interval: Irregular, triggered on app actions
        "0504": {
            "a2": {
                BYTES: {
                    "00": {
                        NAME: "dc_input_power_total?",  # # DC input power (solar + car charging)
                        TYPE: DeviceHexDataTypes.sile.value,
                    },
                    "02": {
                        NAME: "remaining_time_hours?",  # hours with factor 0.1
                        TYPE: DeviceHexDataTypes.sile.value,
                        FACTOR: 0.1,
                        SIGNED: False,
                    },
                    "04": {
                        NAME: "main_battery_soc?",  # SOC of main battery only?
                        TYPE: DeviceHexDataTypes.ui.value,
                    },
                }
            },
            "fd": {NAME: "local_timestamp"},
            "fe": {NAME: "msg_timestamp"},
        },
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": _PPS_VERSIONS_0830,
        # Interval: Only as response to status request, same content as 0421
        "0900": _AS220_0421,
    },
    # PPS F2000
    "A1780": {
        "0044": CMD_AC_CHARGE_LIMIT  # in W; min: 100, max: 1440, step: 100
        | {
            "a2": {
                **CMD_AC_CHARGE_LIMIT["a2"],
                VALUE_MIN: 100,
                VALUE_MAX: 1440,
                VALUE_STEP: 100,
            }
        },
        "0045": CMD_DEVICE_TIMEOUT_MIN,  # Options in minutes: 0 (Never), 30, 60, 120, 240, 360, 720, 1440
        "0046": CMD_DISPLAY_TIMEOUT_SEC,  # Options in seconds: 20, 30, 60, 300, 1800 seconds
        "004a": CMD_AC_OUTPUT_SWITCH,  # AC output switch: Disabled (0) or Enabled (1)
        "004b": CMD_DC_OUTPUT_SWITCH,  # DC output switch: Disabled (0) or Enabled (1)
        "004c": CMD_DISPLAY_MODE,  # Display brightness: Off (0), Low (1), Medium (2), High (3)
        "004f": CMD_LIGHT_MODE,  # LED mode: Off (0), Low (1), Medium (2), High (3), Blinking (4)
        "0052": CMD_DISPLAY_SWITCH,  # Display switch: Disabled (0) or Enabled (1)
        "0050": CMD_TEMP_UNIT,  # Temperature unit switch: Celsius (0) or Fahrenheit (1)
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        "005e": CMD_AC_FAST_CHARGE_SWITCH,  # Ultrafast charge switch: Disabled (0) or Enabled (1)
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": _A1780_0405,
        # Interval: irregular, triggerd by wifi signal change?
        "0407": _PPS_0407,
        # Interval: ??
        "0408": _A1780_0408,
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": _PPS_VERSIONS_0830,
    },
    # PPS F2000 Plus
    "A1780P": {
        "0044": CMD_AC_CHARGE_LIMIT  # in W; min: 100, max: 1440, step: 100
        | {
            "a2": {
                **CMD_AC_CHARGE_LIMIT["a2"],
                VALUE_MIN: 100,
                VALUE_MAX: 1440,
                VALUE_STEP: 100,
            }
        },
        "0045": CMD_DEVICE_TIMEOUT_MIN,  # Options in minutes: 0 (Never), 30, 60, 120, 240, 360, 720, 1440
        "0046": CMD_DISPLAY_TIMEOUT_SEC,  # Options in seconds: 20, 30, 60, 300, 1800 seconds
        "004a": CMD_AC_OUTPUT_SWITCH,  # AC output switch: Disabled (0) or Enabled (1)
        "004b": CMD_DC_OUTPUT_SWITCH,  # DC output switch: Disabled (0) or Enabled (1)
        "004c": CMD_DISPLAY_MODE,  # Display brightness: Off (0), Low (1), Medium (2), High (3)
        "004f": CMD_LIGHT_MODE,  # LED mode: Off (0), Low (1), Medium (2), High (3), Blinking (4)
        "0052": CMD_DISPLAY_SWITCH,  # Display switch: Disabled (0) or Enabled (1)
        "0050": CMD_TEMP_UNIT,  # Temperature unit switch: Celsius (0) or Fahrenheit (1)
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        "005e": CMD_AC_FAST_CHARGE_SWITCH,  # Ultrafast charge switch: Disabled (0) or Enabled (1)
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": _A1780_0405,
        # Interval: irregular, triggerd by wifi signal change?
        "0407": _PPS_0407,
        # Interval: ??
        "0408": _A1780_0408,
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": _PPS_VERSIONS_0830,
    },
    # PPS F2600
    "A1781": {
        "0042": CMD_AC_OUTPUT_TIMEOUT_SEC,  # AC output timeout: 0-86400 seconds, step 300
        "0043": CMD_DC_OUTPUT_TIMEOUT_SEC,  # DC output timeout: 0-86400 seconds, step 300
        "0044": CMD_AC_CHARGE_LIMIT  # in W; min: 100, max: 1440, step: 100
        | {
            "a2": {
                **CMD_AC_CHARGE_LIMIT["a2"],
                # Note: App only supports from 200 W, but F2600 and App support 100 W as MQTT command
                VALUE_MIN: 100,
                VALUE_MAX: 1440,
                VALUE_STEP: 100,
            }
        },
        # 0045 omitted: F2600 reports d2=0 in telemetry but ignores writes
        "0046": CMD_DISPLAY_TIMEOUT_SEC,  # Options in seconds: 20, 30, 60, 300, 1800 seconds
        "004a": CMD_AC_OUTPUT_SWITCH,  # AC output switch: Disabled (0) or Enabled (1)
        "004b": CMD_DC_OUTPUT_SWITCH,  # DC output switch: Disabled (0) or Enabled (1)
        "004c": CMD_DISPLAY_MODE,  # Display brightness: Off (0), Low (1), Medium (2), High (3)
        "004e": CMD_ENERGY_SAVING_SWITCH,  # Power saving mode: Off (0) or On (1)
        "004f": CMD_LIGHT_MODE,  # LED mode: Off (0), Low (1), Medium (2), High (3), Blinking (4)
        "0052": CMD_DISPLAY_SWITCH,  # Display switch: Disabled (0) or Enabled (1)
        "0050": CMD_TEMP_UNIT,  # Temperature unit switch: Celsius (0) or Fahrenheit (1)
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        "005e": CMD_AC_FAST_CHARGE_SWITCH,  # Ultrafast charge switch: Disabled (0) or Enabled (1)
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": _A1780_0405,
        # Interval: irregular, triggered by wifi signal change?
        "0407": _PPS_0407,
        # Interval: ??
        "0408": _A1780_0408,
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": _PPS_VERSIONS_0830,
    },
    # PPS F3800
    "A1790": {
        "0044": CMD_AC_CHARGE_LIMIT  # Range: 100-1800 W, Step: 100 W
        | {
            "a2": {
                **CMD_AC_CHARGE_LIMIT["a2"],
                VALUE_MIN: 100,
                VALUE_MAX: 1800,
                VALUE_MAX_STATE: "ac_charge_limit_max",  # adopt limit based on device variant
                VALUE_STEP: 100,
            }
        },
        "0045": CMD_DEVICE_TIMEOUT_MIN,  # Options in minutes: 0 (Never), 30, 60, 120, 240, 360, 720, 1440
        "0046": CMD_DISPLAY_TIMEOUT_SEC,  # Options in seconds: 20, 30, 60, 300, 1800 seconds
        "004a": CMD_AC_OUTPUT_SWITCH,  # AC output switch: Disabled (0) or Enabled (1)
        "004b": CMD_DC_OUTPUT_SWITCH,  # DC output switch: Disabled (0) or Enabled (1)
        "004c": CMD_DISPLAY_MODE,  # Display brightness: Off (0), Low (1), Medium (2), High (3)
        "004f": CMD_LIGHT_MODE,  # LEF mode: Off (0), Low (1), Medium (2), High (3), Blinking (4)
        "0050": CMD_TEMP_UNIT,  # Temperature unit switch: Celsius (0) or Fahrenheit (1)
        "0052": CMD_DISPLAY_SWITCH,
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        "0076": CMD_DC_12V_OUTPUT_MODE_INV,  # Normal (1), Smart (0)
        "0077": CMD_AC_OUTPUT_MODE_INV,  # Normal (1), Smart (0)
        "0079": CMD_PORT_MEMORY_SWITCH,  # Port Memory switch: Disabled (0) or Enabled (1)
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": _A1790_0405,
        # Interval: irregular, triggerd by wifi signal change?
        "0407": _PPS_0407,
        # Interval: ??
        "040a": _A1790_040a,
        # Interval: ??
        "0410": _A1790_0410,
        # Interval: ??
        "0804": _A1790_0804,
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": _PPS_VERSIONS_0830,
        # Interval: ??
        "0840": _A1790_0405,
    },
    # PPS F3800 Plus
    "A1790P": {
        "0044": CMD_AC_CHARGE_LIMIT  # Range: 100-1800 W, Step: 100 W
        | {
            "a2": {
                **CMD_AC_CHARGE_LIMIT["a2"],
                VALUE_MIN: 100,
                VALUE_MAX: 1800,
                VALUE_MAX_STATE: "ac_charge_limit_max",  # adopt limit based on device variant
                VALUE_STEP: 100,
            }
        },
        "0045": CMD_DEVICE_TIMEOUT_MIN,  # Options in minutes: 0 (Never), 30, 60, 120, 240, 360, 720, 1440
        "0046": CMD_DISPLAY_TIMEOUT_SEC,  # Options in seconds: 20, 30, 60, 300, 1800 seconds
        "004a": CMD_AC_OUTPUT_SWITCH,  # AC output switch: Disabled (0) or Enabled (1)
        "004b": CMD_DC_OUTPUT_SWITCH,  # DC output switch: Disabled (0) or Enabled (1)
        "004c": CMD_DISPLAY_MODE,  # Display brightness: Off (0), Low (1), Medium (2), High (3)
        "004f": CMD_LIGHT_MODE,  # LEF mode: Off (0), Low (1), Medium (2), High (3), Blinking (4)
        "0050": CMD_TEMP_UNIT,  # Temperature unit switch: Celsius (0) or Fahrenheit (1)
        "0052": CMD_DISPLAY_SWITCH,
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        "0076": CMD_DC_12V_OUTPUT_MODE_INV,  # Normal (1), Smart (0)
        "0077": CMD_AC_OUTPUT_MODE_INV,  # Normal (1), Smart (0)
        "0079": CMD_PORT_MEMORY_SWITCH,  # Enabled (1), Disabled (0)
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": _A1790_0405,
        # Interval: irregular, triggerd by wifi signal change?
        "0407": _PPS_0407,
        # Interval: ??
        "040a": _A1790_040a,
        # Interval: ??
        "0410": _A1790_0410,
        # Interval: ??
        "0804": _A1790_0804,
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": _PPS_VERSIONS_0830,
        # Interval: ??
        "0840": _A1790_0405,
    },
    # Solarbank PPS F3000
    "A1782": {
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages
        "0101": {
            # AC command group
            COMMAND_LIST: [
                SolixMqttCommands.ac_output_switch,  # field a2
                SolixMqttCommands.ac_output_timeout_seconds,  # field a3
                SolixMqttCommands.ac_charge_limit,  # field a4
                SolixMqttCommands.ac_output_mode_select,  # field a6
            ],
            SolixMqttCommands.ac_output_switch: CMD_COMMON_V2
            | {
                "a2": {
                    NAME: "set_ac_output_switch",  # Disable (0) | Enable (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "ac_output_power_switch",
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                },
            },
            SolixMqttCommands.ac_output_timeout_seconds: CMD_COMMON_V2
            | {
                "a3": {
                    NAME: "set_ac_output_timeout_seconds",  # Timeout seconds, custom range: 0-86400, step 300
                    TYPE: DeviceHexDataTypes.var.value,
                    STATE_NAME: "ac_output_timeout_seconds",
                    VALUE_MIN: 0,
                    VALUE_MAX: 86400,
                    VALUE_STEP: 300,
                },
            },
            SolixMqttCommands.ac_charge_limit: CMD_COMMON_V2
            | {
                "a4": {
                    NAME: "set_ac_input_limit",  # in W; min: 200, max: 1800, step: 100
                    TYPE: DeviceHexDataTypes.sile.value,
                    STATE_NAME: "ac_input_limit",
                    VALUE_MIN: 200,
                    VALUE_MAX: 1800,
                    VALUE_MAX_STATE: "ac_input_limit_max",
                    VALUE_STEP: 100,
                },
            },
            SolixMqttCommands.ac_output_mode_select: CMD_COMMON_V2
            | {
                "a6": {
                    NAME: "set_ac_output_mode",  # Normal (0), Smart (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "ac_output_mode",
                    VALUE_OPTIONS: {"normal": 0, "smart": 1},
                },
            },
        },
        "0102": {
            # DC command group
            COMMAND_LIST: [
                SolixMqttCommands.dc_output_switch,  # field a2
                SolixMqttCommands.dc_output_timeout_seconds,  # field a3
                SolixMqttCommands.dc_12v_output_mode_select,  # field a4
            ],
            SolixMqttCommands.dc_output_switch: CMD_COMMON_V2
            | {
                "a2": {
                    NAME: "set_dc_output_switch",  # Disable (0) | Enable (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "dc_output_power_switch",
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                },
            },
            SolixMqttCommands.dc_output_timeout_seconds: CMD_COMMON_V2
            | {
                "a3": {
                    NAME: "set_dc_output_timeout_seconds",  # Timeout seconds, custom range: 0-86400, step 300
                    TYPE: DeviceHexDataTypes.var.value,
                    STATE_NAME: "dc_output_timeout_seconds",
                    VALUE_MIN: 0,
                    VALUE_MAX: 86400,
                    VALUE_STEP: 300,
                },
            },
            SolixMqttCommands.dc_12v_output_mode_select: CMD_COMMON_V2
            | {
                "a4": {
                    NAME: "set_dc_12v_output_mode",  # Normal (0), Smart (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "dc_12v_output_mode",
                    VALUE_OPTIONS: {"normal": 0, "smart": 1},
                },
            },
        },
        "0103": {
            # Other command group
            COMMAND_LIST: [
                SolixMqttCommands.display_switch,  # field a2
                SolixMqttCommands.display_mode_select,  # field a3
                SolixMqttCommands.display_timeout_seconds,  # field a4
                SolixMqttCommands.device_timeout_minutes,  # field a6
                SolixMqttCommands.light_mode_select,  # field a7
                SolixMqttCommands.port_memory_switch,  # field a8
                SolixMqttCommands.soc_limits,  # field aa, ab
            ],
            SolixMqttCommands.display_switch: CMD_COMMON_V2
            | {
                "a2": {
                    NAME: "set_display_switch",  # Off (0), On (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "display_switch",
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                },
            },
            SolixMqttCommands.display_mode_select: CMD_COMMON_V2
            | {
                "a3": {
                    NAME: "set_display_mode",  # Low (1), Medium (2), High (3)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "display_mode",
                    VALUE_OPTIONS: {"low": 1, "medium": 2, "high": 3},
                },
            },
            SolixMqttCommands.display_timeout_seconds: CMD_COMMON_V2
            | {
                "a4": {
                    NAME: "set_display_timeout_sec",  # 0 (Never), 10, 20, 30, 60, 300, 1800
                    TYPE: DeviceHexDataTypes.sile.value,
                    STATE_NAME: "display_timeout_seconds",
                    VALUE_OPTIONS: [0, 10, 20, 30, 60, 300, 1800],
                },
            },
            SolixMqttCommands.device_timeout_minutes: CMD_COMMON_V2
            | {
                "a6": {
                    NAME: "set_device_timeout_min",  # 0 (Never), 30, 60, 120, 240, 360, 720, 1440
                    TYPE: DeviceHexDataTypes.sile.value,
                    STATE_NAME: "device_timeout_minutes",
                    VALUE_OPTIONS: [0, 30, 60, 120, 240, 360, 720, 1440],
                },
            },
            SolixMqttCommands.light_mode_select: CMD_COMMON_V2
            | {
                "a7": {
                    NAME: "set_light_mode",  # Off (0), Low (1), Medium (2), High (3)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "light_mode",
                    VALUE_OPTIONS: {"off": 0, "low": 1, "medium": 2, "high": 3},
                },
            },
            SolixMqttCommands.port_memory_switch: CMD_COMMON_V2
            | {
                "a8": {
                    NAME: "set_port_memory_switch",  # Off (0), On (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "port_memory_switch",
                    VALUE_OPTIONS: {"off": 0, "on": 1},
                },
            },
            SolixMqttCommands.soc_limits: CMD_SOC_LIMITS_V2,
            # Contains fields aa ab for the limits
            # aa = max_soc: 80, 85, 90, 95, 100 %
            # ab = min_soc: 1, 5, 10, 15, 20 %
        },
        # Interval: irregular, triggerd by wifi signal change?
        "0407": _PPS_0407,
        "0421": _A1782_0421,
        "0502": _A1782_0502,
        # Upon request, followed by 0100 status request command
        "0900": _A1782_0421,  # Same content as 0421
    },
    # Solarbank 1 E1600
    "A17C0": {
        "0040": CMD_STATUS_REQUEST,  # Device status request, more reliable than RT (one time status messages 0405 etc)
        "0050": CMD_TEMP_UNIT,  # Temperature unit switch: Celsius (0) or Fahrenheit (1)
        "0056": CMD_SB_STATUS_CHECK,  # Complex command with multiple parms
        "0057": CMD_REALTIME_TRIGGER,  # Works only in certain states for status messages 0405 etc
        "0067": CMD_SB_POWER_CUTOFF,  # Complex command with multiple parms
        "0068": CMD_SB_INVERTER_TYPE,  # Complex command with multiple parms
        "0405": {
            # Interval: ~5 seconds with realtime trigger, or immediately with status request
            TOPIC: "param_info",
            "a2": {NAME: "device_sn"},
            "a3": {NAME: "battery_soc"},
            "a4": {NAME: "405_unknown_1?"},
            "a5": {NAME: "error_code"},
            "a6": {NAME: "sw_version", "values": 1},
            "a7": {NAME: "sw_controller", "values": 1},
            "a8": {NAME: "hw_version", "values": 1},
            "a9": {NAME: "temp_unit_fahrenheit"},
            "aa": {NAME: "temperature", SIGNED: True},
            "ab": {NAME: "photovoltaic_power"},
            "ac": {NAME: "output_power"},
            "ad": {NAME: "charging_status?"},
            # "ae": Binary structure for schedule slots, dynamic size depending on schedule
            # 2 bytes LE for start/end time in minutes, 1 byte priority limit, Export switch switch setting and discharge prio in bitmask
            # The schedule should be managed completely via Api
            "b0": {NAME: "bat_charge_power"},
            "b1": {NAME: "pv_yield", FACTOR: 0.0001},
            "b2": {NAME: "charged_energy", FACTOR: 0.0001},
            "b3": {NAME: "output_energy", FACTOR: 0.0001},
            "b4": {NAME: "output_cutoff_data"},
            "b5": {NAME: "lowpower_input_data"},
            "b6": {NAME: "input_cutoff_data"},
            "b7": {NAME: "inverter_brand"},
            "b8": {NAME: "inverter_model"},
            "b9": {NAME: "min_load"},
            "c0": {NAME: "0w_switch_sn"},
            "c1": {NAME: "0w_switch_bt_mac"},
            "fe": {NAME: "msg_timestamp"},
        },
        # Interval: varies, probably upon change
        "0407": _A17C0_0407,
        "0408": {
            # Interval: ~60 seconds
            TOPIC: "state_info",
            "a2": {NAME: "device_sn"},
            "a3": {NAME: "local_timestamp"},
            "a4": {NAME: "utc_timestamp"},
            "a5": {NAME: "battery_soc_calc", FACTOR: 0.001},
            "a6": {NAME: "battery_soh", FACTOR: 0.001},
            "a8": {NAME: "charging_status"},
            "a9": {NAME: "home_load_preset"},
            "aa": {NAME: "photovoltaic_power"},
            "ab": {NAME: "bat_charge_power"},
            "ac": {NAME: "output_power"},
            "ad": {NAME: "408_unknown_1?"},
            "ae": {NAME: "408_unknown_2?"},
            "af": {NAME: "408_unknown_3?"},
            "b0": {NAME: "battery_soc"},
            "b1": {NAME: "pv_yield", FACTOR: 0.0001},
            "b2": {NAME: "charged_energy", FACTOR: 0.0001},
            "b3": {NAME: "output_energy", FACTOR: 0.0001},
            "b4": {NAME: "discharged_energy", FACTOR: 0.0001},
            "b5": {NAME: "bypass_energy", FACTOR: 0.0001},
            "b6": {NAME: "temperature", SIGNED: True},
            "b7": {NAME: "pv_voltage", FACTOR: 0.01},
            "b8": {NAME: "output_voltage", FACTOR: 0.01},
            "b9": {NAME: "battery_voltage", FACTOR: 0.01},
        },
    },
    # Solarbank 2 E1600 Pro
    "A17C1": {
        "0050": CMD_TEMP_UNIT,  # Temperature unit switch: Celsius (0) or Fahrenheit (1)
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        "005a": CMD_SB_MAX_LOAD  # same pattern but different command for max load settings in parallel systems
        | {
            COMMAND_NAME: SolixMqttCommands.sb_max_load_parallel,
            "a2": {
                **CMD_SB_MAX_LOAD["a2"],
                VALUE_OPTIONS: [1200, 2400, 3600, 4800],
                VALUE_OPTIONS_STATE: "max_load_parallel_options",  # key to be used to provide valid options
            },
            "a3": {
                **CMD_SB_MAX_LOAD["a3"],
                VALUE_DEFAULT: 2,
            },
        },
        # Interval: ~3-5 seconds with realtime trigger, or immediately with status request
        "0067": {
            # Old and new SOC limits
            COMMAND_LIST: [
                SolixMqttCommands.sb_power_cutoff_select,  # field a2, a3, a4
                SolixMqttCommands.sb_soc_limits,  # field a2, a5, a6, a7
            ],
            SolixMqttCommands.sb_power_cutoff_select: CMD_SB_POWER_CUTOFF,  # Old: SOC reserve selection
            SolixMqttCommands.sb_soc_limits: CMD_SB_SOC_LIMITS,  # New: min, max and backup soc + switch
        },
        "0068": {
            # solarbank light command group
            COMMAND_LIST: [
                SolixMqttCommands.sb_light_mode_select,  # field a2
                SolixMqttCommands.sb_light_switch,  # field a3
            ],
            SolixMqttCommands.sb_light_mode_select: CMD_SB_LIGHT_MODE,  # Normal (0), Mood light (1)
            SolixMqttCommands.sb_light_switch: CMD_SB_LIGHT_SWITCH,  # Light Off (1), Light On (0)
        },
        "0080": {
            # solarbank command group
            COMMAND_LIST: [
                SolixMqttCommands.sb_max_load,  # field a2, a3
                SolixMqttCommands.sb_disable_grid_export_switch,  # field a5, a6, a9
            ],
            SolixMqttCommands.sb_max_load: CMD_SB_MAX_LOAD  # 350,600,800,1000 W, may depend on country settings
            | {
                "a2": {
                    **CMD_SB_MAX_LOAD["a2"],
                    VALUE_OPTIONS: [350, 600, 800, 1000],
                    VALUE_OPTIONS_STATE: "max_load_options",  # key to be used to provide valid options
                }
            },
            SolixMqttCommands.sb_disable_grid_export_switch: CMD_SB_DISABLE_GRID_EXPORT_SWITCH,  # Grid export (0), Disable grid export (1)
        },
        "0405": _A17C1_0405,
        # Interval: varies, probably upon change
        "0407": _A17C0_0407,
        # Interval: ~300 seconds
        "0408": _A17C1_0408,
        # Expansion data
        # Interval: ~3-5 seconds, but only with realtime trigger
        "040a": _A17C1_040a,
    },
    # Solarbank 2 E1600 AC
    "A17C2": {
        "0050": CMD_TEMP_UNIT,  # Temperature unit switch: Celsius (0) or Fahrenheit (1)
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        "005a": CMD_SB_MAX_LOAD  # same pattern but different command for max load settings in parallel systems
        | {
            COMMAND_NAME: SolixMqttCommands.sb_max_load_parallel,
            "a2": {
                **CMD_SB_MAX_LOAD["a2"],
                VALUE_OPTIONS: [1200, 2400, 3600, 4800],
                VALUE_OPTIONS_STATE: "max_load_parallel_options",  # key to be used to provide valid options
            },
            "a3": {
                **CMD_SB_MAX_LOAD["a3"],
                VALUE_DEFAULT: 2,
            },
        },
        "0067": {
            # Old and new SOC limits
            COMMAND_LIST: [
                SolixMqttCommands.sb_power_cutoff_select,  # field a2, a3, a4
                SolixMqttCommands.sb_soc_limits,  # field a2, a5, a6, a7
            ],
            SolixMqttCommands.sb_power_cutoff_select: CMD_SB_POWER_CUTOFF,  # Old: SOC reserve selection
            SolixMqttCommands.sb_soc_limits: CMD_SB_SOC_LIMITS,  # New: min, max and backup soc + switch
        },
        "0068": {
            # solarbank light command group
            COMMAND_LIST: [
                SolixMqttCommands.sb_light_mode_select,  # field a2
                SolixMqttCommands.sb_light_switch,  # field a3
            ],
            SolixMqttCommands.sb_light_mode_select: CMD_SB_LIGHT_MODE,  # Normal (0), Mood light (1)
            SolixMqttCommands.sb_light_switch: CMD_SB_LIGHT_SWITCH,  # Light Off (1), Light On (0)
        },
        "0080": {
            # solarbank command group
            COMMAND_LIST: [
                SolixMqttCommands.sb_max_load,  # field a2, a3
                SolixMqttCommands.sb_disable_grid_export_switch,  # field a5, a6, a9
                SolixMqttCommands.sb_ac_input_limit,  # field a8
            ],
            SolixMqttCommands.sb_max_load: CMD_SB_MAX_LOAD  # 350,600,800,1000,1200 W, may depend on country settings
            | {
                "a2": {
                    **CMD_SB_MAX_LOAD["a2"],
                    VALUE_OPTIONS: [350, 600, 800, 1000, 1200],
                    VALUE_OPTIONS_STATE: "max_load_options",  # key to be used to provide valid options
                }
            },
            SolixMqttCommands.sb_disable_grid_export_switch: CMD_SB_DISABLE_GRID_EXPORT_SWITCH,  # Grid export (0), Disable grid export (1)
            SolixMqttCommands.sb_ac_input_limit: CMD_SB_AC_INPUT_LIMIT,  # 0 - 1200 W, step: 100
        },
        # Interval: ~3-5 seconds with realtime trigger, or immediately with status request
        "0405": _A17C5_0405,
        # Interval: varies, probably upon change
        "0407": _A17C0_0407,
        # Interval: ~300 seconds
        "0408": _A17C5_0408,
        # Expansion data
        # Interval: ~3-5 seconds, but only with realtime trigger
        "040a": _A17C5_040a,
    },
    # Solarbank 2 E1600 Plus
    "A17C3": {
        "0050": CMD_TEMP_UNIT,  # Temperature unit switch: Celsius (0) or Fahrenheit (1)
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        "005a": CMD_SB_MAX_LOAD  # same pattern but different command for max load settings in parallel systems
        | {
            COMMAND_NAME: SolixMqttCommands.sb_max_load_parallel,
            "a2": {
                **CMD_SB_MAX_LOAD["a2"],
                VALUE_OPTIONS: [1200, 2400, 3600, 4800],
                VALUE_OPTIONS_STATE: "max_load_parallel_options",  # key to be used to provide valid options
            },
            "a3": {
                **CMD_SB_MAX_LOAD["a3"],
                VALUE_DEFAULT: 2,
            },
        },
        "0067": {
            # Old and new SOC limits
            COMMAND_LIST: [
                SolixMqttCommands.sb_power_cutoff_select,  # field a2, a3, a4
                SolixMqttCommands.sb_soc_limits,  # field a2, a5, a6, a7
            ],
            SolixMqttCommands.sb_power_cutoff_select: CMD_SB_POWER_CUTOFF,  # Old: SOC reserve selection
            SolixMqttCommands.sb_soc_limits: CMD_SB_SOC_LIMITS,  # New: min, max and backup soc + switch
        },
        "0068": {
            # solarbank light command group
            COMMAND_LIST: [
                SolixMqttCommands.sb_light_mode_select,  # field a2
                SolixMqttCommands.sb_light_switch,  # field a3
            ],
            SolixMqttCommands.sb_light_mode_select: CMD_SB_LIGHT_MODE,  # Normal (0), Mood light (1)
            SolixMqttCommands.sb_light_switch: CMD_SB_LIGHT_SWITCH,  # Light Off (1), Light On (0)
        },
        "0080": {
            # solarbank command group
            COMMAND_LIST: [
                SolixMqttCommands.sb_max_load,  # field a2, a3
                SolixMqttCommands.sb_disable_grid_export_switch,  # field a5, a6, a9
            ],
            SolixMqttCommands.sb_max_load: CMD_SB_MAX_LOAD  # 350,600,800,1000 W, may depend on country settings
            | {
                "a2": {
                    **CMD_SB_MAX_LOAD["a2"],
                    VALUE_OPTIONS: [350, 600, 800, 1000],
                    VALUE_OPTIONS_STATE: "max_load_options",  # key to be used to provide valid options
                },
            },
            SolixMqttCommands.sb_disable_grid_export_switch: CMD_SB_DISABLE_GRID_EXPORT_SWITCH,  # Grid export (0), Disable grid export (1)
        },
        # Interval: ~3-5 seconds with realtime trigger, or immediately with status request
        "0405": _A17C1_0405,
        # Interval: varies, probably upon change
        "0407": _A17C0_0407,
        # Interval: ~300 seconds
        "0408": _A17C1_0408,
        # Expansion data
        # Interval: ~3-5 seconds, but only with realtime trigger
        "040a": _A17C1_040a,
    },
    # Solarbank 3 E2700 Pro
    "A17C5": {
        "0050": CMD_TEMP_UNIT,  # Temperature unit switch: Celsius (0) or Fahrenheit (1)
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        "005a": CMD_SB_MAX_LOAD  # same pattern but different command for max load settings in parallel systems
        | {
            COMMAND_NAME: SolixMqttCommands.sb_max_load_parallel,
            "a2": {
                **CMD_SB_MAX_LOAD["a2"],
                VALUE_OPTIONS: [1200, 2400, 3600, 4800],
                VALUE_OPTIONS_STATE: "max_load_parallel_options",
            },
            "a3": {
                **CMD_SB_MAX_LOAD["a3"],
                VALUE_DEFAULT: 2,
            },
        },
        "005e": CMD_SB_USAGE_MODE,  # NOTE: Cmd not supported directly, but description used for msg decoding
        "0067": {
            # Old and new SOC limits
            COMMAND_LIST: [
                SolixMqttCommands.sb_min_soc_select,  # field a2
                SolixMqttCommands.sb_soc_limits,  # field a2, a5, a6, a7
            ],
            SolixMqttCommands.sb_min_soc_select: CMD_SB_MIN_SOC,  # Old: SOC reserve selection
            SolixMqttCommands.sb_soc_limits: CMD_SB_SOC_LIMITS  # New: min, max and backup soc + switch
            | {
                "a2": {
                    **CMD_SB_SOC_LIMITS["a2"],
                    VALUE_MIN: 1,  # 1 % for SB3
                },
            },
        },
        "0068": {
            # solarbank light command group
            COMMAND_LIST: [
                SolixMqttCommands.sb_light_mode_select,  # field a2
                SolixMqttCommands.sb_light_switch,  # field a3
            ],
            SolixMqttCommands.sb_light_mode_select: CMD_SB_LIGHT_MODE,  # Normal (0), Mood light (1)
            SolixMqttCommands.sb_light_switch: CMD_SB_LIGHT_SWITCH,  # Light Off (1), Light On (0)
        },
        "0073": CMD_SB_AC_SOCKET_SWITCH,  # Switch for emergency AC socket
        "0080": {
            # solarbank command group
            COMMAND_LIST: [
                SolixMqttCommands.sb_max_load,  # field a2, a3, a4
                SolixMqttCommands.sb_disable_grid_export_switch,  # field a5, a6, a9
                SolixMqttCommands.sb_pv_limit_select,  # field a7
                SolixMqttCommands.sb_ac_input_limit,  # field a8
            ],
            SolixMqttCommands.sb_max_load: CMD_SB_MAX_LOAD  # 350,600,800,1000,1200 W, may depend on country settings
            | {
                "a2": {
                    **CMD_SB_MAX_LOAD["a2"],
                    VALUE_OPTIONS: [350, 600, 800, 1000, 1200],
                    VALUE_OPTIONS_STATE: "max_load_options",  # key to be used to provide valid options
                },
                # Extra field a4 observed for SB3, which does not seem to be used for SB2?
                "a4": {
                    NAME: "set_max_load_a4?",  # Unknown, 0 observed
                    TYPE: DeviceHexDataTypes.sile.value,
                    VALUE_DEFAULT: 0,
                },
            },
            SolixMqttCommands.sb_disable_grid_export_switch: CMD_SB_DISABLE_GRID_EXPORT_SWITCH,  # Grid export (0), Disable grid export (1)
            SolixMqttCommands.sb_pv_limit_select: CMD_SB_PV_LIMIT,  # 2000 W or 3600 W
            SolixMqttCommands.sb_ac_input_limit: CMD_SB_AC_INPUT_LIMIT,  # 0 - 1200 W, step: 100
        },
        "0085": CMD_SB_3RD_PARTY_PV_SWITCH,  # 3rd Party support switch, cloud driven
        "009a": CMD_SB_DEVICE_TIMEOUT,  # timeout in 30 min chunks: 0, 30, 60, 120, 240, 360, 720, 1440 minutes
        # Interval: ~3-5 seconds with realtime trigger, or immediately with status request
        "0405": _A17C5_0405,
        # Interval: varies, probably upon change
        "0407": _A17C0_0407,
        # Interval: ~300 seconds
        "0408": _A17C5_0408,
        # Expansion data
        # Interval: ~3-5 seconds, but only with realtime trigger, NOT with status request
        "040a": _A17C5_040a,
        # multisystem messages
        # Interval: ~3-10 seconds, but only with realtime trigger, NOT with status request
        "0420": _DOCK_0420,
        # Interval: ~300 seconds
        "0421": _DOCK_0421,
        # Interval: ~300 seconds
        "0428": _DOCK_0428,
        # Interval: ~300 seconds
        "0500": _DOCK_0500,
    },
    # Solarbank 4 E5000 Pro
    "AE103": {
        # Interval: Irregular, triggered on app actions, contains device and Exp settings? Mostly empty
        "0402": {
            "fe": {NAME: "msg_timestamp"},
        },
        # Interval: ~300 seconds?
        "0404": _AE103_0404,
        # Interval: ~3-5 seconds with realtime trigger, or immediately with status request
        "0405": _AE103_0405,
        # Interval: ~300 seconds
        "0408": _AE103_0408,
        # Interval: ~3-5 seconds, but only with realtime trigger
        "040a": _AE103_040a,
        # multisystem messages
        # Interval: ~3-10 seconds, but only with realtime trigger, NOT with status request
        "0420": _DOCK_0420,
        # Interval: ~300 seconds
        "0421": _DOCK_0421,
        # Interval: ~300 seconds
        "0428": _DOCK_0428,
        # Interval: ~300 seconds
        "0500": _DOCK_0500,
    },
    # Anker SOLIX E10
    "A17E1": {
        "0057": CMD_REALTIME_TRIGGER,
        "0405": {
            # Interval: ~3-5 seconds, but only with realtime trigger
            TOPIC: "param_info",
            "a2": {NAME: "device_sn"},
            "a3": {NAME: "battery_soc"},
            "a4": {
                NAME: "charging_status"
            },  # charging_status: 0=inactive, 1=discharging, 2=charging
            "a5": {NAME: "temperature", SIGNED: True},
            "a6": {NAME: "battery_soc?"},
            "a7": {NAME: "sw_version", "values": 4},
            "a8": {NAME: "sw_controller", "values": 4},
            "a9": {NAME: "sw_expansion", "values": 4},  # Expansion firmware version
            "ab": {NAME: "photovoltaic_power"},
            "ac": {NAME: "battery_power_signed"},
            "ad": {NAME: "ac_output_power"},  # inverter AC output
            "ae": {NAME: "ac_output_power_inverted?"},  # inverter PV/Battery input?
            "b0": {NAME: "bypass_energy?"},
            "b1": {NAME: "charged_energy?"},
            "b2": {NAME: "consumed_energy?"},
            "b3": {NAME: "discharged_energy?"},
            "b4": {NAME: "pv_yield?"},
            "b8": {
                NAME: "usage_mode?"
            },  # 2=self-consume, 4=manual-backup, 5=time-of-use, 8=backup/emergency
            "bf": {NAME: "unknown_timestamp_0405_bf?"},
            "c0": {NAME: "unknown_timestamp_0405_c0?"},
            "c3": {
                NAME: "use_time_band?"
            },  # use_time_band: 1=peak, 2=mid-peak, 3=off-peak, 4=super-off-peak
            "c4": {NAME: "grid_power_signed"},  # positive=import, negative=export
            "c5": {NAME: "home_demand"},
            "c6": {NAME: "pv_1_power"},
            "c7": {NAME: "pv_2_power"},
            "af": {
                NAME: "generator_to_home_power?"
            },  # generator AC input power to home
            "ba": {
                BYTES: {
                    "02": [
                        {
                            NAME: "storm_guard_switch",  # 0=off, 1=on
                            MASK: 0x01,
                        }
                    ]
                }
            },
            "c2": {
                NAME: "ac_output_power?"
            },  # total AC output power to home from all sources in W (solar, battery, generator, grid)
            "cb": {NAME: "expansion_packs"},  # number of expansion batteries
            "d5": {
                NAME: "generator_to_battery_power?"
            },  # generator AC charging battery W
            "dc": {NAME: "grid_status"},  # 0=grid-connected, 2=off-grid/backup
            "fe": {NAME: "msg_timestamp"},
        },
        "0408": {
            # Interval: ??? seconds
            TOPIC: "param_info",
            "a2": {NAME: "device_sn"},
            "a3": {NAME: "unknown_timestamp_0408_a3?"},
            "a4": {NAME: "unknown_timestamp_0408_a4?"},
            "a7": {NAME: "battery_soc?"},
            "a8": {NAME: "expansion_packs?"},  # number of expansion batteries
            "a9": {NAME: "usage_mode?"},
            "ac": {NAME: "bypass_energy?"},  # same as 0405 b0
            "b2": {NAME: "unknown_energy_0408_b2?"},
            "b7": {NAME: "charged_energy?"},  # same as 0405 b1
            "b8": {NAME: "consumed_energy?"},  # same as 0405 b2
            "be": {NAME: "pv_yield?"},  # same as 0405 b4
            "cc": {NAME: "temperature", SIGNED: True},
        },
        # Interval: ~3-5 seconds, but only with realtime trigger
        "040a": _A17E1_040a,
    },
    # AX170 Power dock for home backup systems A17E1
    "AX170": {
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        "005e": CMD_BACKUP_CHARGE_PLAN,  # TODO: Command to be completed, fields a2,a3,a4,a5,a6,fd
        "0405": _AX170_0405,
        "0408": _AX170_0408,
        "0412": CMD_CIRCUIT_PRIORITY,  # for circuit priority and backup low/high SOC
        "0666": {
            EMBEDDED: "tlv",  # Name of field with embedded hexdata
            "a2": {NAME: "sn"},
            "a3": {NAME: "type"},
            "a4": {NAME: "tlv"},
        },
    },
    # Anker Solarbank Smartmeter
    "A17X7": {
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        "0405": {
            # Interval: ~5 seconds, but only with realtime trigger
            TOPIC: "param_info",
            "a2": {NAME: "device_sn"},
            "a6": {NAME: "sw_version", "values": 4},
            "a7": {NAME: "sw_controller", "values": 4},
            "a8": {NAME: "grid_to_home_power"},
            "a9": {NAME: "pv_to_grid_power"},
            "aa": {NAME: "grid_import_energy", FACTOR: 0.01},
            "ab": {NAME: "grid_export_energy", FACTOR: 0.01},
            # "ad": {NAME: "pv_to_grid_power"},
        },
    },
    # Anker Solarbank Smartmeter
    "A17X7US": {
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        "0405": {
            # Interval: ~5 seconds, but only with realtime trigger
            TOPIC: "param_info",
            "a2": {NAME: "device_sn"},
            "a6": {NAME: "sw_version", "values": 4},
            "a7": {NAME: "sw_controller", "values": 4},
            "b1": {NAME: "grid_power_signed_l1"},  # negative = Export
            "b2": {NAME: "grid_power_signed_l2"},  # negative = Export
            "b3": {NAME: "grid_power_signed"},  # negative = Export
            "b4": {NAME: "current_l1"},
            "b5": {NAME: "voltage_l1"},
            "b6": {NAME: "current_l2"},
            "b7": {NAME: "voltage_l2"},
            "b8": {NAME: "power_factor"},
            "b9": {NAME: "voltage_l1l2"},
            "ba": {NAME: "system_output_power_signed_l1", FACTOR: -1},
            "bb": {NAME: "system_output_power_signed_l2", FACTOR: -1},
            "bc": {NAME: "system_output_current_l1"},
            "bd": {NAME: "system_output_current_l2"},
            "be": {NAME: "voltage_l1l2_alt?"},
            "fe": {NAME: "msg_timestamp"},
        },
    },
    # Smart Meter P1
    "AE1R0": {
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0425 etc
        "0425": {
            # Interval: ~5 seconds, but only with realtime trigger
            TOPIC: "param_info",
            "a2": {NAME: "device_sn"},
            "a8": {NAME: "grid_to_home_power?"},
            "a9": {NAME: "pv_to_grid_power?"},
            "aa": {NAME: "grid_export_energy", FACTOR: 0.001},
            "ab": {NAME: "grid_import_energy", FACTOR: 0.001},
        },
        "0427": {
            # Interval: ~300 seconds
            TOPIC: "state_info",
            "a4": {
                NAME: "grid_status?"
            },  # Grid OK (1), No grid (6)?, Grid connecting (3)?
            "a5": {NAME: "device_sn"},
            "a6": {NAME: "wifi_name"},
        },
    },
    # Shello Pro 3 EM
    "SHEMP3": {
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        "0405": {
            # Interval: ~5 seconds, but only with realtime trigger
            TOPIC: "param_info",
            "a2": {NAME: "device_sn"},
            "a8": {NAME: "grid_to_home_power", FACTOR: 0.01},
            "a9": {NAME: "pv_to_grid_power", FACTOR: 0.01},
            "aa": {NAME: "grid_import_energy", FACTOR: 0.00001},
            "ab": {NAME: "grid_export_energy", FACTOR: 0.00001},
            "fe": {NAME: "msg_timestamp"},
        },
    },
    # Anker Smartplug
    "A17X8": {
        "0040": CMD_STATUS_REQUEST,  # Device status request, more reliable than RT (one time status messages 0405 etc)
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        "007a": CMD_AC_OUTPUT_SWITCH,  # AC output switch: Disabled (0) or Enabled (1)
        "007c": CMD_PLUG_SCHEDULE,  # Set a plug schedule
        "007e": CMD_PLUG_DELAYED_TOGGLE,  # Set a delayed toggle
        "007f": CMD_TIMER_REQUEST,  # Request timer status from device for delayed toggle
        "0405": {
            # Interval: ~5 seconds, but only with realtime trigger
            TOPIC: "param_info",
            "a2": {NAME: "device_sn"},
            "a4": {NAME: "ac_output_power_switch"},  # Off (0), On (1)
            "a6": {NAME: "sw_version", "values": 4},
            "a7": {NAME: "sw_controller", "values": 4},
            "a8": {NAME: "voltage", "factor": 0.1},
            "a9": {NAME: "current", "factor": 0.01},
            "aa": {NAME: "power", "factor": 0.1},
            "ab": {NAME: "output_energy", FACTOR: 0.001},
            "ad": _PLUG_TIMER_STATUS,
            "fe": {NAME: "msg_timestamp"},
        },
        "087f": {
            # Interval: upon timer request command
            TOPIC: "param_info",
            "a2": _PLUG_TIMER_STATUS,
        },
    },
    # Anker Power Dock
    "AE100": {
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        "005a": CMD_SB_MAX_LOAD  # same pattern but different command for max load settings in parallel systems
        | {
            COMMAND_NAME: SolixMqttCommands.sb_max_load_parallel,
            "a2": {
                **CMD_SB_MAX_LOAD["a2"],
                VALUE_OPTIONS: [1200, 2400, 3600, 4800],
                VALUE_OPTIONS_STATE: "max_load_parallel_options",  # key to be used to provide valid options
                STATE_NAME: "max_load_total",
            },
            "a3": {
                **CMD_SB_MAX_LOAD["a3"],
                VALUE_DEFAULT: 2,
            },
        },
        "0067": {
            # Old and new SOC limits
            COMMAND_LIST: [
                SolixMqttCommands.sb_power_cutoff_select,  # field a2, a3, a4
                SolixMqttCommands.sb_soc_limits,  # field a2, a5, a6, a7
            ],
            SolixMqttCommands.sb_power_cutoff_select: CMD_SB_POWER_CUTOFF,  # Old: SOC reserve selection, cloud driven
            SolixMqttCommands.sb_soc_limits: CMD_SB_SOC_LIMITS,  # New: min, max and backup soc + switch
        },
        "0080": CMD_SB_DISABLE_GRID_EXPORT_SWITCH,  # Grid export (0), Disable grid export (1)
        "0084": CMD_SB_EV_CHARGER_SWITCH,  # EV charger support switch, cloud driven
        "0085": CMD_SB_3RD_PARTY_PV_SWITCH,  # 3rd Party support switch, cloud driven
        # Interval: ~3-10 seconds, but only with realtime trigger
        "0405": _DOCK_0405,
        # Interval: varies, probably upon change
        "0407": _0407,
        # multisystem messages
        # Interval: ~3-10 seconds, but only with realtime trigger
        "0420": _DOCK_0420,
        # Interval: ~300 seconds
        "0421": _DOCK_0421,
        # Interval: varies, e.g. upon soc changes
        "0422": {
            "a3": {
                BYTES: {
                    "04": {
                        NAME: "max_soc",
                        TYPE: DeviceHexDataTypes.ui.value,
                    },
                    "05": {
                        NAME: "power_cutoff",
                        TYPE: DeviceHexDataTypes.ui.value,
                    },
                    "06": {
                        NAME: "backup_soc",
                        TYPE: DeviceHexDataTypes.ui.value,
                    },
                },
            },
        },
        # Interval: ~300 seconds
        "0428": _DOCK_0428,
        # Interval: ~300 seconds
        "0500": _DOCK_0500,
    },
    # Power Cooler Everfrost 2 40L
    "A17A4": {
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": _PPS_VERSIONS_0830,
        "0889": {
            "a2": {NAME: "setting_0889_a2"},
            "a3": {NAME: "setting_0889_a3"},
            "a4": {NAME: "setting_0889_a4"},
            "a5": {NAME: "setting_0889_a5"},
            "a6": {NAME: "setting_0889_a6"},
        },
    },
    # Power Cooler Everfrost 2 58L
    "A17A5": {
        # Interval: Unknown
        "0405": _A17A5_0405,
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": _PPS_VERSIONS_0830,
    },
    # Prime Charger 250W
    "A2345": {
        "0200": CMD_STATUS_REQUEST,  # Device status request for message 0a00
        "0202": CMD_COMMON | {COMMAND_NAME: SolixMqttCommands.theme_request},
        "0203": CMD_DISPLAY_TIMEOUT_MODE,  # 0 (Never), 1 (30 sec), 2 (60 sec), 3 (5 min), 4 (30 min)
        "0204": CMD_DISPLAY_BRIGHTNESS,  # Display brightness 20-100 %, step 5 %
        "0205": {  # Set Theme and clock display
            COMMAND_LIST: [
                SolixMqttCommands.charger_theme,  # fields a2-a6
                SolixMqttCommands.charger_theme_custom,  # fields a2-a5, a7 with custom url
            ],
            SolixMqttCommands.charger_theme: CMD_CHARGER_THEME,
            SolixMqttCommands.charger_theme_custom: {
                k: v for k, v in CMD_CHARGER_THEME.items() if k not in ["a2", "a6"]
            }
            | {
                "a7": {
                    TYPE: DeviceHexDataTypes.bin.value,
                    BYTES: {
                        "00": {
                            NAME: "set_theme_url",
                            TYPE: DeviceHexDataTypes.str.value,
                            STATE_NAME: "theme_url",
                            VALUE_STATE: "theme_url",
                        }
                    },
                }
            }
            | {
                "a2": {
                    TYPE: DeviceHexDataTypes.ui.value,
                    BYTES: {
                        **CMD_CHARGER_THEME["a2"][BYTES],
                        "00": [
                            {
                                **item,
                                VALUE_DEFAULT: 2,
                            }
                            if item.get(NAME) == "set_theme_type"
                            else item
                            for item in CMD_CHARGER_THEME["a2"][BYTES]["00"]
                        ],
                    },
                }
            },
        },
        "0206": {
            # USB port switch command. Same command, but selected port is a parameter
            COMMAND_LIST: [
                SolixMqttCommands.charger_usage_mode,  # field a2
                SolixMqttCommands.charger_custom_usage_mode,  # fields a2, a3, a4
            ],
            SolixMqttCommands.charger_usage_mode: CMD_CHARGER_USAGE_MODE,  # mode: 1 (AI Power mode), 2 (Connection Prio), 3 (Dual Laptop mode), 4 (Low power mode)
            SolixMqttCommands.charger_custom_usage_mode: CMD_CHARGER_CUSTOM_USAGE_MODE,  # mode: 5 (Custom) + port settings
        },
        "0207": {
            # USB port switch command. Same command, but selected port is a parameter
            COMMAND_LIST: [
                SolixMqttCommands.usbc_1_port_switch,
                SolixMqttCommands.usbc_2_port_switch,
                SolixMqttCommands.usbc_3_port_switch,
                SolixMqttCommands.usbc_4_port_switch,
                SolixMqttCommands.usba_port_switch,
            ],
            SolixMqttCommands.usbc_1_port_switch: CMD_USB_PORT_SWITCH.get("usbc_1"),
            SolixMqttCommands.usbc_2_port_switch: CMD_USB_PORT_SWITCH.get("usbc_2"),
            SolixMqttCommands.usbc_3_port_switch: CMD_USB_PORT_SWITCH.get("usbc_3"),
            SolixMqttCommands.usbc_4_port_switch: CMD_USB_PORT_SWITCH.get("usbc_4"),
            SolixMqttCommands.usba_port_switch: CMD_USB_PORT_SWITCH.get("usba"),
        },
        "0208": {
            # USB port schedule command. Same command, but selected port and time type is a parameter
            COMMAND_LIST: [
                SolixMqttCommands.usbc_1_start_time,
                SolixMqttCommands.usbc_2_start_time,
                SolixMqttCommands.usbc_3_start_time,
                SolixMqttCommands.usbc_4_start_time,
                SolixMqttCommands.usba_start_time,
                SolixMqttCommands.usbc_1_end_time,
                SolixMqttCommands.usbc_2_end_time,
                SolixMqttCommands.usbc_3_end_time,
                SolixMqttCommands.usbc_4_end_time,
                SolixMqttCommands.usba_end_time,
            ],
            SolixMqttCommands.usbc_1_start_time: CMD_PORT_START.get("usbc_1"),
            SolixMqttCommands.usbc_2_start_time: CMD_PORT_START.get("usbc_2"),
            SolixMqttCommands.usbc_3_start_time: CMD_PORT_START.get("usbc_3"),
            SolixMqttCommands.usbc_4_start_time: CMD_PORT_START.get("usbc_4"),
            SolixMqttCommands.usba_start_time: CMD_PORT_START.get("usba"),
            SolixMqttCommands.usbc_1_end_time: CMD_PORT_END.get("usbc_1"),
            SolixMqttCommands.usbc_2_end_time: CMD_PORT_END.get("usbc_2"),
            SolixMqttCommands.usbc_3_end_time: CMD_PORT_END.get("usbc_3"),
            SolixMqttCommands.usbc_4_end_time: CMD_PORT_END.get("usbc_4"),
            SolixMqttCommands.usba_end_time: CMD_PORT_END.get("usba"),
        },
        "0209": {
            # USB port timer command. Same command, but selected port is a parameter
            COMMAND_LIST: [
                SolixMqttCommands.usbc_1_port_timer,
                SolixMqttCommands.usbc_2_port_timer,
                SolixMqttCommands.usbc_3_port_timer,
                SolixMqttCommands.usbc_4_port_timer,
                SolixMqttCommands.usba_port_timer,
            ],
            SolixMqttCommands.usbc_1_port_timer: CMD_PORT_TIMER.get("usbc_1"),
            SolixMqttCommands.usbc_2_port_timer: CMD_PORT_TIMER.get("usbc_2"),
            SolixMqttCommands.usbc_3_port_timer: CMD_PORT_TIMER.get("usbc_3"),
            SolixMqttCommands.usbc_4_port_timer: CMD_PORT_TIMER.get("usbc_4"),
            SolixMqttCommands.usba_port_timer: CMD_PORT_TIMER.get("usba"),
        },
        # "020a" # unknown client command, fields a2 (country_id), a3 (account_id)
        # Special realtime trigger for this device, with 10 seconds timeout fix, sending a 0303 message per second
        "020b": {
            k: v for k, v in CMD_REALTIME_TRIGGER.items() if k not in ["a2", "a3"]
        },
        "020c": CMD_PORT_PRIORITY,  # Set the port priorities for given port bitmask
        "020e": CMD_CHARGER_KNOB_MODE,  # Set charger knob mode: 0 forward, 1 backward
        "020f": CMD_CHARGER_CLOCK_HOLIDAY,  # Set weekend mode for clock display
        "0210": CMD_CHARGER_CLOCK_MODE,  # Set charger clock mode: 0: 12h, 1: 24h
        # "0212" # unknown cloud command, fields a2-a8
        "0213": CMD_CHARGER_CLOCK_DISPLAY,  # Set charger clock display schedule
        # "0214": CMD_TBD_SWITCH,  # unknown client command, fields a2
        # "0223": CMD_TBD_SWITCH,  # unknown client command, fields a2
        "0300": {
            "a4": {NAME: "unknown_0300_a4?"},  # does not seem to be usage_mode
            "fe": {NAME: "msg_timestamp"},
        },
        # Interval: Upon change of the referred port toggle, usable by data extractor to adjust correct port state
        "0302": {
            "a2": {NAME: "set_port_switch_select"},
            "a3": {NAME: "set_port_switch"},
            "fe": {NAME: "msg_timestamp"},
        },
        # Interval: ~1 second, but only with realtime trigger. Consumption data, all data fields are also in 0a00 message
        "0303": _A2345_0303,
        # Interval: Upon change of the port timer
        "0307": {
            "a2": {NAME: "set_port_timer_select"},
            "a3": {
                BYTES: {
                    "00": {
                        NAME: "set_port_timer_switch",
                        TYPE: DeviceHexDataTypes.ui.value,
                    },  # "off": 0, "on": 1
                    "01": {
                        NAME: "port_timer_seconds",  # Timer seconds, custom range: 0-86100, step 300
                        TYPE: DeviceHexDataTypes.var.value,
                    },
                    "05": {
                        NAME: "port_timer_remaining_seconds",  # remaining seconds
                        TYPE: DeviceHexDataTypes.var.value,
                    },
                },
            },
        },
        "030f": {
            "a3": {NAME: "set_port_priority"},
            "fe": {NAME: "msg_timestamp"},
        },
        "0311": {
            "a2": {
                NAME: "theme_id",
                TYPE: DeviceHexDataTypes.var.value,
                SIGNED: False,
            },
            "a4": {
                BYTES: {
                    "00": [
                        {NAME: "theme_type", MASK: 0x06},
                    ],
                },
            },
        },
        "0312": {
            "a2": {NAME: "country_code", TYPE: DeviceHexDataTypes.str.value},  # "DE"
            "fe": {NAME: "msg_timestamp"},
        },
        # Interval: only with status request command. Contains all settings and consumption data
        "0a00": _A2345_0a00,
        "0a02": {
            "a2": {
                BYTES: {
                    "00": [
                        {NAME: "clock_settings", MASK: 0xFF},
                        {NAME: "clock_switch", MASK: 0x80},
                        {NAME: "holiday_switch", MASK: 0x40},
                        {NAME: "theme_type", MASK: 0x06},
                    ],
                },
            },
            "a3": {
                NAME: "theme_id",
                TYPE: DeviceHexDataTypes.var.value,
                SIGNED: False,
            },
            "a4": {
                NAME: "theme_url",
                TYPE: DeviceHexDataTypes.str.value,
            },
            "a6": {NAME: "unknown_0a02_a6"},
            "fe": {NAME: "msg_timestamp"},
        },
    },
    # Prime Charging Station 240W 8-in-1
    "A91B2": {
        "0200": CMD_STATUS_REQUEST,  # Device status request for message 0a00
        "0207": {
            # AC outlet switch command. Same message type as A2345 USB port switch.
            # port_select: 0=ac_1, 1=ac_2
            COMMAND_LIST: [
                SolixMqttCommands.ac_1_port_switch,
                SolixMqttCommands.ac_2_port_switch,
            ],
            SolixMqttCommands.ac_1_port_switch: CMD_AC_PORT_SWITCH
            | {
                "a2": {
                    **CMD_AC_PORT_SWITCH["a2"],
                    VALUE_DEFAULT: 0,
                },
                "a3": {
                    **CMD_AC_PORT_SWITCH["a3"],
                    STATE_NAME: "ac_1_switch",
                },
            },
            SolixMqttCommands.ac_2_port_switch: CMD_AC_PORT_SWITCH
            | {
                "a2": {
                    **CMD_AC_PORT_SWITCH["a2"],
                    VALUE_DEFAULT: 1,
                },
                "a3": {
                    **CMD_AC_PORT_SWITCH["a3"],
                    STATE_NAME: "ac_2_switch",
                },
            },
        },
        # Special realtime trigger (no a2/a3 timeout params, same as A2345)
        "020b": {
            k: v for k, v in CMD_REALTIME_TRIGGER.items() if k not in ["a2", "a3"]
        },
        # Port switch state notification (eventual broadcast by device after 0207 command)
        "0302": {
            "a2": {NAME: "set_port_switch_select"},
            "a3": {NAME: "set_port_switch"},
            "fe": {NAME: "msg_timestamp"},
        },
        # Interval: ~1 second with realtime trigger. USB port consumption data (same layout as A2345).
        "0303": _A2345_0303,
        # Full device status including AC outlet switch states, sent on status request.
        "0a00": _A2345_0a00,
    },
    # Alternator charger
    "AS200": {
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages
        "0100": CMD_STATUS_REQUEST
        | {  # Device status request (one time status messages 0900)
            "a2": {
                TYPE: DeviceHexDataTypes.bin.value,
                LENGTH: 1,
                BYTES: {
                    "00": {
                        NAME: "push_status_request",  # Push (1)
                        TYPE: DeviceHexDataTypes.ui.value,
                        VALUE_DEFAULT: 1,
                    },
                },
            }
        },
        "0103": {
            # command group
            COMMAND_LIST: [
                SolixMqttCommands.charger_mode_select,  # field a2
                SolixMqttCommands.car_battery_type,  # field a3, aa
                SolixMqttCommands.battery_charge_limits,  # field a5, b4
                SolixMqttCommands.reverse_charge_limits,  # field a6, b4
                SolixMqttCommands.device_switch,  # field ac
                SolixMqttCommands.device_timeout_minutes,  # field ae, bb, bc
                SolixMqttCommands.temp_unit_switch,  # field b2
                SolixMqttCommands.device_power_mode,  # field b8
            ],
            SolixMqttCommands.charger_mode_select: CMD_COMMON_V2
            | {
                "a2": {
                    NAME: "set_charger_mode",  # Normal charge (0), Reverse Charge (1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "charger_mode",
                    VALUE_OPTIONS: {"normal": 0, "reverse": 1},
                    VALUE_STATE: "charger_mode",
                },
            },
            SolixMqttCommands.car_battery_type: CMD_CAR_BATTERY_TYPE,
            SolixMqttCommands.battery_charge_limits: CMD_BATTERY_CHARGE_LIMITS,
            SolixMqttCommands.reverse_charge_limits: CMD_REVERSE_CHARGE_LIMITS,
            SolixMqttCommands.device_switch: CMD_DEVICE_SWITCH,  # Off (0), On (1)
            SolixMqttCommands.device_timeout_minutes: CMD_COMMON_V2
            | {
                "ae": {
                    NAME: "set_active_device_timeout_minutes",  # applied setting, 720-1440, step 30 if switch off(1), otherwise 0
                    TYPE: DeviceHexDataTypes.sile.value,
                    STATE_NAME: "active_device_timeout_minutes",
                    VALUE_FOLLOWS: "set_device_timeout_minutes",  # follow state to ensure converter cache has all dependent states
                    STATE_CONVERTER: lambda value, state, cache: (
                        (
                            0
                            if cache.get(
                                "set_device_timeout_switch",
                                cache.get("device_timeout_switch"),
                            )
                            else cache.get(
                                "set_device_timeout_minutes",
                                cache.get("device_timeout_minutes"),
                            )
                        )
                        if state is not None
                        else value
                    ),  # Smart setting represented with state 2
                    VALUE_MIN: 0,
                    VALUE_MAX: 1440,
                    VALUE_STEP: 30,
                },
                "bb": {
                    NAME: "set_device_timeout_minutes",  # control setting, 720-1440 step 30
                    TYPE: DeviceHexDataTypes.sile.value,
                    STATE_NAME: "device_timeout_minutes",
                    VALUE_STATE: "device_timeout_minutes",
                    VALUE_MIN: 720,
                    VALUE_MAX: 1440,
                    VALUE_STEP: 30,
                },
                "bc": {
                    NAME: "set_device_timeout_switch",  # on (0), off (1) = No timeout !
                    TYPE: DeviceHexDataTypes.ui.value,
                    STATE_NAME: "device_timeout_switch",
                    VALUE_OPTIONS: {"off": 1, "on": 0},
                    VALUE_STATE: "device_timeout_switch",
                },
            },
            SolixMqttCommands.temp_unit_switch: {  # field b2: Celsius (0) | Fahrenheit (1)
                k: v for k, v in CMD_TEMP_UNIT_V2.items() if k != "a5"
            }
            | {"b2": CMD_TEMP_UNIT_V2["a5"]},
            SolixMqttCommands.device_power_mode: CMD_COMMON_V2
            | {
                # Command: Device shutdown, needs physical power on button afterwards
                "b8": {
                    NAME: "set_device_power_mode",  # Shutdown(1)
                    TYPE: DeviceHexDataTypes.ui.value,
                    VALUE_OPTIONS: {"shutdown": 1},
                    VALUE_DEFAULT: 1,
                },
            },
        },
        # status message, every 3 seconds but only if realtime trigger active
        "0421": _AS200_0421,
        # Interval: ~every 5 minutes, same content as 0421
        "0900": _AS200_0421,
    },
    # Power Panel
    "A17B1": {
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages
        # Interval: unknown?
        "0500": {
            "a2": {
                "json": _PP_JSON,
            }
        },
        "0502": {
            "a2": {
                # 0502 reuses some keys of the shared PP json structure with different meaning,
                # therefore override those mappings to avoid value flapping in merged device data
                "json": _PP_JSON
                | {
                    "data": _PP_JSON["data"]
                    | {
                        "ws": {
                            NAME: "wifi_signal"
                        },  # Wi-Fi signal quality in %, e.g. 76 (verified against router), run status in 0500/0505
                        "90s": {
                            NAME: "message_count?"
                        },  # incrementing counter per 0502 message, pps_count in 0500/0505
                    },
                }
            }
        },
        "0503": {
            "a2": {
                "json": _PP_JSON,
            }
        },
        "0505": {
            "a2": {
                "json": _PP_JSON,
            }
        },
        "0601": {
            EMBEDDED: "tlv",  # Name of field with embedded hexdata
        },
    },
    # HES X1
    "A5101": {
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages
        # Interval: unknown?
        "json": _X1_JSON,
    },
    "A5102": {
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages
        # Interval: unknown?
        "json": _X1_JSON,
    },
    "A5103": {
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages
        # Interval: unknown?
        "json": _X1_JSON,
    },
    # EV Charger V1
    "A5191": {
        # "0040": CMD_STATUS_REQUEST | {  # Device status request (one time status messages 0840=0405, but no 410)
        #    **TIMESTAMP_FE_NOTYPE # App uses timestamp field without field type, Anker Bug?
        # },
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0410
        "0100": {
            # EV command group
            COMMAND_LIST: [
                SolixMqttCommands.plug_lock_switch,  # field a3
                SolixMqttCommands.ev_auto_start_switch,  # field a4
                SolixMqttCommands.ev_max_charge_current,  # field a8
                SolixMqttCommands.light_brightness,  # field aa
                SolixMqttCommands.ev_auto_charge_restart_switch,  # field ac
                SolixMqttCommands.ev_random_delay_switch,  # field ad
                SolixMqttCommands.swipe_up_mode_select,  # field af
                SolixMqttCommands.swipe_down_mode_select,  # field b0
                SolixMqttCommands.smart_touch_mode_select,  # field b2
                SolixMqttCommands.light_off_schedule,  # field b4, b5, b6
                SolixMqttCommands.modbus_switch,  # field b7
            ],
            SolixMqttCommands.plug_lock_switch: CMD_PLUG_LOCK_SWITCH,  # On (1), Off (2) !
            SolixMqttCommands.ev_auto_start_switch: CMD_EV_AUTO_START_SWITCH,  # Off (0), On (1)
            SolixMqttCommands.ev_max_charge_current: CMD_EV_MAX_CHARGE_CURRENT,  # min limit to max limit (e.g. 6-32 A, step 1 A)
            SolixMqttCommands.ev_auto_charge_restart_switch: CMD_EV_AUTO_CHARGE_RESTART_SWITCH,  # Off (0), On (1)
            SolixMqttCommands.ev_random_delay_switch: CMD_EV_CHARGE_RANDOM_DELAY_SWITCH,  # Off (0), On (1)
            SolixMqttCommands.light_brightness: CMD_EV_LIGHT_BRIGHTNESS,  # 0-100 %, step 10 %
            SolixMqttCommands.swipe_up_mode_select: CMD_SWIPE_UP_MODE,  # off (0), start charge (1), stop charge (2), boost charge (3)
            SolixMqttCommands.swipe_down_mode_select: CMD_SWIPE_DOWN_MODE,  # off (0), start charge (1), stop charge (2), boost charge (3)
            SolixMqttCommands.smart_touch_mode_select: CMD_SMART_TOUCH_MODE,  # simple (0), avoid_error (1)
            SolixMqttCommands.light_off_schedule: CMD_EV_LIGHT_OFF_SCHEDULE,  # Switch, start time, end time
            SolixMqttCommands.modbus_switch: CMD_MODBUS_SWITCH,  # Off (0), On (1)
        },
        "0105": {
            COMMAND_LIST: [
                SolixMqttCommands.ev_charger_mode_select,  # field a4
            ],
            SolixMqttCommands.ev_charger_mode_select: CMD_EV_CHARGER_MODE,  # Start(1), Stop(2), Skip Delay (3), Boost(4)
        },
        "0106": {
            COMMAND_LIST: [
                SolixMqttCommands.ev_charger_schedule_settings,  # field a2, a8
                SolixMqttCommands.ev_charger_schedule_times,  # field a3 - a7
            ],
            SolixMqttCommands.ev_charger_schedule_settings: CMD_EV_CHARGER_SCHEDULE_SETTINGS,  # Schedule switch, mode
            SolixMqttCommands.ev_charger_schedule_times: CMD_EV_CHARGER_SCHEDULE_TIMES,  # schedule times
        },
        "0108": {
            COMMAND_LIST: [
                SolixMqttCommands.device_power_mode,  # field a2
            ],
            SolixMqttCommands.device_power_mode: CMD_DEVICE_POWER_MODE,  # Restart(5)
        },
        "010c": {
            COMMAND_LIST: [
                SolixMqttCommands.main_breaker_limit,  # field a3
                SolixMqttCommands.ev_load_balancing,  # field a2, a4, a5, a6
            ],
            SolixMqttCommands.main_breaker_limit: CMD_MAIN_BREAKER_LIMIT,  # 10-500 A, step 1 A
            SolixMqttCommands.ev_load_balancing: CMD_EV_LOAD_BALANCING,  # Switch, monitoring type and device SN
        },
        "010e": {
            COMMAND_LIST: [
                SolixMqttCommands.ev_solar_charging,  # field a2-a8
            ],
            SolixMqttCommands.ev_solar_charging: CMD_EV_SOLAR_CHARGING,  # Solar charge settings
        },
        # Interval: 5 minutes regular, contains 3 unknown settings. Only regular message without trigger/request
        "0400": {
            TOPIC: "state_info",
            "a2": {NAME: "unknown_setting_400_a2"},
            "a3": {NAME: "unknown_setting_400_a3"},
            "a4": {NAME: "unknown_setting_400_a4"},
        },
        # Interval: Unknown
        "0403": _EV_CHARGER_0403,  # Few device parms for charging after 0105 command?
        # Interval: Irregular, but only after status request command?
        "0405": _EV_CHARGER_0405,  # Device parms, after command was acknowledged
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0410": _EV_CHARGER_0410,
        # Interval: once requested via status request command, same as 0405
        "0840": _EV_CHARGER_0405,
        # Interval: Control change confirmation message
        "0900": _EV_CHARGER_0405,
    },
    "A7320": {
        # SOLIX Smart Generator 5500
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        "0073": {
            COMMAND_LIST: [
                SolixMqttCommands.ac_dc_mode_select,  # field a5
            ],
            SolixMqttCommands.ac_dc_mode_select: CMD_AC_DC_MODE,  # AC/DC mode selection
        },
        "0405": _A7320_0405,
        "0408": _A7320_0408,
    },
}
