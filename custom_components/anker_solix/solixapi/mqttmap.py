"""Define mapping for MQTT messages field conversions depending on Anker Solix model."""

from typing import Final

from .apitypes import DeviceHexDataTypes
from .mqttcmdmap import (
    BYTES,
    # CMD_AC_CHARGE_LIMIT,
    CMD_AC_FAST_CHARGE_SWITCH,
    CMD_AC_OUTPUT_MODE,
    CMD_AC_OUTPUT_SWITCH,
    CMD_COMMON_V2,
    CMD_DC_12V_OUTPUT_MODE,
    CMD_DC_OUTPUT_SWITCH,
    CMD_DC_OUTPUT_TIMEOUT_SEC,
    CMD_DEVICE_MAX_LOAD,
    CMD_DEVICE_TIMEOUT_MIN,
    CMD_DISPLAY_MODE,
    CMD_DISPLAY_SWITCH,
    CMD_DISPLAY_TIMEOUT_SEC,
    CMD_LIGHT_MODE,
    CMD_PORT_MEMORY_SWITCH,
    CMD_REALTIME_TRIGGER,
    CMD_SB_AC_INPUT_LIMIT,
    CMD_SB_AC_SOCKET_SWITCH,
    CMD_SB_DEVICE_TIMEOUT,
    CMD_SB_DISABLE_GRID_EXPORT_SWITCH,
    CMD_SB_INVERTER_TYPE,
    CMD_SB_LIGHT_MODE,
    CMD_SB_LIGHT_SWITCH,
    CMD_SB_MAX_LOAD,
    CMD_SB_MIN_SOC,
    CMD_SB_POWER_CUTOFF,
    CMD_SB_PV_LIMIT,
    CMD_SB_STATUS_CHECK,
    CMD_SOC_LIMITS_V2,
    CMD_STATUS_REQUEST,
    CMD_TEMP_UNIT,
    COMMAND_LIST,
    FACTOR,
    LENGTH,
    MASK,
    NAME,
    SIGNED,
    STATE_NAME,
    TOPIC,
    TYPE,
    VALUE_DEFAULT,
    VALUE_MAX,
    VALUE_MIN,
    VALUE_OPTIONS,
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
    "ae": {NAME: "ac_output_power_total"},  # Total AOutput in W (int)
    "b7": {
        NAME: "ac_output_power_switch"
    },  # AC output switch: Disabled (0) or Enabled (1)
    "b8": {NAME: "dc_charging_status"},  # None (0), Charging (1)
    "b9": {NAME: "temperature", SIGNED: True},  # In Celsius
    "ba": {NAME: "charging_status"},  # None (0), Discharging (1), Charging (2) ???
    "bb": {NAME: "battery_soc"},  # Battery SOC
    "bc": {NAME: "battery_soh"},  # Battery Health
    "c1": {
        NAME: "dc_output_power_switch"
    },  # DC output switch: Disabled (0) or Enabled (1)
    "c5": {NAME: "device_sn"},  # Device serial number
    "cf": {
        NAME: "display_mode"
    },  # Display brightness: Off (0), Low (1), Medium (2), High (3)
    "fe": {NAME: "msg_timestamp"},  # Message timestamp
}

_A1728_0405 = {
    # C300(X) DC param info
    TOPIC: "param_info",
    "a3": {NAME: "remaining_time_hours", FACTOR: 0.1, SIGNED: False},
    "a4": {NAME: "usbc_1_power"},  # USB-C left output power
    "a5": {NAME: "usbc_2_power"},  # USB-C center output power
    "a6": {NAME: "usbc_3_power"},  # USB-C right output power
    "a7": {NAME: "usbc_4_power"},  # USB-C solar output power
    "a8": {NAME: "usba_1_power"},  # USB-A left output power
    "a9": {NAME: "usba_2_power"},  # USB-A right output power
    "aa": {NAME: "dc_input_power?"},  # DC input power 12V car charging?
    "ab": {NAME: "photovoltaic_power"},  # Solar input
    "ac": {NAME: "dc_input_power_total?"},  # DC input power (solar + car charging)?
    "ad": {NAME: "output_power_total?"},  # Total DC output power for all ports?
    "b5": {NAME: "temperature", SIGNED: True},  # In Celsius
    "b6": {
        NAME: "charging_status",  # Publishes the raw integer value (0-3): Inactive (0), Solar (1), DC Input (2), Both (3)
    },
    "b7": {NAME: "battery_soc"},  # Battery SOC
    "b8": {NAME: "battery_soh"},  # Battery health
    "b9": {
        NAME: "usbc_1_status"
    },  # USB-C left status: Inactive (0), Discharging (1), Charging (2)
    "ba": {
        NAME: "usbc_2_status"
    },  # USB-C center status: Inactive (0), Discharging (1), Charging (2)
    "bb": {
        NAME: "usbc_3_status"
    },  # USB-C right status: Inactive (0), Discharging (1), Charging (2)
    "bc": {
        NAME: "usbc_4_status"
    },  # USB-C solar status: Inactive (0), Discharging (1), Charging (2)
    "bd": {
        NAME: "usba_1_status"
    },  # USB-A left status: Inactive (0), Discharging (1), Charging (2)
    "be": {
        NAME: "usba_2_status"
    },  # USB-A right status: Inactive (0), Discharging (1), Charging (2)
    "bf": {NAME: "light_switch"},  # Off (0), On (1)
    "c4": {
        NAME: "dc_output_timeout_seconds?"
    },  # Timeout seconds, custom range: 0-10800???
    "c5": {
        NAME: "display_timeout_seconds?"
    },  # Display timeout: 20, 30, 60, 300, 1800 seconds???
    "c8": {NAME: "display_mode"},  # Brightness: Off (0), Low (1), Medium (2), High (3)
    "fe": {NAME: "msg_timestamp"},  # Message timestamp
}

_A1761_0405 = {
    # PPS C1000(X) parm info
    TOPIC: "param_info",
    "a4": {
        NAME: "remaining_time_hours",
        FACTOR: 0.1,
        SIGNED: False,
    },  # In hours (value * factor)
    "a5": {NAME: "grid_to_battery_power"},  # AC charging power to battery
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
    "bb": {NAME: "ac_output_power_switch"},  # Disabled (0) or Enabled (1)
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
    "d0": {NAME: "device_sn"},  # Device serial number
    "d1": {NAME: "max_load"},  # Maximum load setting (W)
    "d2": {
        NAME: "device_timeout_minutes"
    },  # Device auto-off timeout (minutes): 0 (Never), 30, 60, 120, 240, 360, 720, 1440
    "d3": {NAME: "display_timeout_seconds"},  # Options: 20, 30, 60, 300, 1800 seconds
    "d8": {NAME: "dc_output_power_switch"},  # Disabled (0) or Enabled (1)
    "d9": {NAME: "display_mode"},  # Brightness: Off (0), Low (1), Medium (2), High (3)
    "dc": {
        NAME: "light_mode"
    },  # LED light mode: Off (0), Low (1), Medium (2), High (3), Blinking (4)
    "dd": {NAME: "temp_unit_fahrenheit"},  # Celsius (0) or Fahrenheit (1)
    "de": {NAME: "display_switch"},  # Off (0) or On (1)
    "e5": {NAME: "backup_charge_switch"},  # Off (0) or On (1)
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
                NAME: "ac_output_power",  # AC Ausgangsleistung
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "04": {
                NAME: "ac_input_power_a7",  # Duplicate of a6
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
    "da": {
        BYTES: {
            "12": {
                NAME: "unknown_2",
                TYPE: DeviceHexDataTypes.sile.value,
            },
            "14": {
                NAME: "unknown_3",
                TYPE: DeviceHexDataTypes.sile.value,
            },
        }
    },
    "fd": {NAME: "utc_timestamp"},
    "fe": {NAME: "msg_timestamp"},
}

_A1780_0405 = {
    # F2000(P) param info
    TOPIC: "param_info",
    "a4": {NAME: "remaining_time_hours", FACTOR: 0.1, SIGNED: False},  # In hours
    "a5": {NAME: "grid_to_battery_power"},  # AC charging power to battery
    "a6": {NAME: "ac_socket_power"},  # Individual AC outlet power
    "a7": {NAME: "usbc_1_power"},  # USB-C port 1 output power
    "a8": {NAME: "usbc_2_power"},  # USB-C port 2 output power
    "a9": {NAME: "usbc_3_power"},  # USB-C port 3 output power
    "aa": {NAME: "usba_1_power"},  # USB-A port 1 output power
    "ab": {NAME: "usba_2_power"},  # USB-A port 2 output power
    "ac": {NAME: "dc_12v_1_power"},  # 12V port 1 output power
    "ad": {NAME: "dc_12v_2_power"},  # 12V port 2 output power
    "ae": {NAME: "dc_input_power"},  # DC input power (solar/car charging)
    "af": {NAME: "ac_input_power"},  # AC input power (230V)
    "b0": {NAME: "ac_output_power_total"},  # Total output power
    "b3": {NAME: "sw_version", "values": 1},  # Main firmware version
    "b9": {NAME: "sw_expansion", "values": 1},  # Expansion firmware version
    "ba": {NAME: "sw_controller", "values": 1},  # Controller firmware version
    "bd": {NAME: "temperature", SIGNED: True},  # Main device temperature (°C)
    "be": {
        NAME: "exp_1_temperature",
        SIGNED: True,
    },  # Expansion battery 1 temperature (°C)
    "c0": {NAME: "expansion_packs_a?"},
    "c1": {NAME: "main_battery_soc"},  # Main battery state of charge (%)
    "c2": {NAME: "exp_1_soc"},  # Expansion battery 1 state of charge (%)
    "c3": {NAME: "battery_soh"},  # Main battery state of health (%)
    "c4": {NAME: "exp_1_soh"},  # Expansion battery 1 state of health (%)
    "c5": {NAME: "expansion_packs_b?"},
    "d0": {NAME: "device_sn"},
    "d1": {NAME: "max_load"},  # Maximum load setting (W)
    "d3": {
        NAME: "device_timeout_minutes"
    },  # Device auto-off timeout (minutes): 0 (Never), 30, 60, 120, 240, 360, 720, 1440
    "d4": {
        NAME: "display_timeout_seconds"
    },  # Display timeout: 20, 30, 60, 300, 1800 seconds
    "d7": {NAME: "ac_output_power_switch"},  # Disabled (0) or Enabled (1)
    "d8": {NAME: "dc_output_power_switch"},  # Disabled (0) or Enabled (1)
    "d9": {NAME: "display_mode"},  # Brightness: Off (0), Low (1), Medium (2), High (3)
    "db": {NAME: "energy_saving_mode"},  # Disabled (0) or Enabled (1)
    "dc": {NAME: "light_mode"},  # Off (0), Low (1), Medium (2), High (3), Blinking (4)
    "dd": {NAME: "temp_unit_fahrenheit"},  # Celsius (0) or Fahrenheit (1)
    "de": {NAME: "display_switch"},  # Off (0) or On (1)
    "e5": {NAME: "backup_charge_switch"},  # Off (0) or On (1)
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
    "a4": {NAME: "local_timestamp?"},
    "a5": {NAME: "utc_timestamp?"},
    "a6": {NAME: "discharged_energy?", FACTOR: 0.001},  # in kWh
    "a7": {NAME: "charged_energy?", FACTOR: 0.001},  # in kWh
    "ac": {NAME: "main_battery_soc"},  # in %
}

_A1790_0405 = {
    # F3800 param info
    TOPIC: "param_info",
    "a4": {NAME: "remaining_time_hours", FACTOR: 0.1, SIGNED: False},  # In hours
    "a5": {NAME: "ac_input_power"},
    "a6": {NAME: "ac_output_power"},
    "a7": {NAME: "usbc_1_power"},
    "a8": {NAME: "usbc_2_power"},
    "a9": {NAME: "usbc_3_power"},
    "aa": {NAME: "usba_1_power?"},
    "ab": {NAME: "usba_2_power?"},
    "ac": {NAME: "dc_12v_output_power_switch?"},
    "ad": {NAME: "main_battery_soc"},  # Main battery SOC?
    "ae": {NAME: "photovoltaic_power"},  # Total solar input
    "af": {NAME: "pv_1_power"},
    "b0": {NAME: "pv_2_power"},
    "b1": {NAME: "bat_charge_power"},  # Total charging (AC + Solar)
    "b2": {NAME: "output_power"},
    "b4": {NAME: "bat_discharge_power?"},
    "b5": {NAME: "sw_version?", "values": 1},  # Main firmware version
    "ba": {NAME: "sw_expansion?", "values": 1},  # Expansion firmware version
    "bc": {
        NAME: "ac_output_power_switch"
    },  # AC output switch: Disabled (0) or Enabled (1)
    "bd": {
        NAME: "charging_status",  # Publishes the raw integer value (0-3): Inactive (0), Solar (1), AC Input (2), Both (3)
    },
    "be": {NAME: "temperature", SIGNED: True},  # In Celsius
    "bf": {NAME: "display_status"},  # Asleep (0), Manual Off (1), On (2)
    "c0": {NAME: "battery_soc"},  # Total SOC of main + Exp batteries?
    "c1": {
        NAME: "max_soc"
    },  # User Setting (Max SoC %) TODO: What is the command to define SOC max limit?
    # TODO: What does USB status mean, is that a toggle setting? If port is used, this should be indicated by power as well
    "c2": {NAME: "usbc_1_status"},
    "c3": {NAME: "usbc_2_status"},
    "c4": {NAME: "usbc_3_status"},
    "c5": {NAME: "usba_1_status?"},
    "c6": {NAME: "usba_2_status?"},
    "c7": {
        NAME: "dc_output_power_switch"
    },  # 12V DC output switch: Disabled (0) or Enabled (1)
    "cc": {NAME: "device_sn"},
    "cd": {NAME: "ac_input_limit"},  # User Setting (AC Charge Watts)
    "cf": {NAME: "display_timeout_seconds"},  # User Setting (in seconds)
    "d3": {NAME: "ac_output_power_switch_dup?"},  # Duplicate of bc?
    "d4": {NAME: "dc_output_power_switch_dup?"},  # Duplicate of c7?
    "d5": {
        NAME: "display_mode"
    },  # Display brightness: Off (0), Low (1), Medium (2), High (3)
    "d8": {
        NAME: "temp_unit_fahrenheit"
    },  # Temperature unit: Celsius (0) or Fahrenheit (1)
    "d9": {
        NAME: "light_mode"
    },  # LED light mode: Off (0), Low (1), Medium (2), High (3), Blinking (4)
    "f6": {NAME: "region?"},  # Value 21333 ("US")
    "f7": {
        NAME: "port_memory_switch"
    },  # Port Memory switch: Disabled (0) or Enabled (1)
    "fd": {NAME: "exp_1_type"},  # Expansion battery type identifier
    "fe": {NAME: "msg_timestamp"},
}

_A1790_040a = {
    # F3800 param info
    TOPIC: "param_info",
    "a2": {NAME: "expansion_packs?"},
    "a3": {NAME: "main_battery_soc?"},  # main battery SOC
    "a4": {
        BYTES: {
            "00": {
                NAME: "exp_1_sn?",
                LENGTH: 16,
                TYPE: DeviceHexDataTypes.str.value,
            },
            "19": {
                NAME: "exp_1_temperature?",
                TYPE: DeviceHexDataTypes.ui.value,
                SIGNED: True,
            },
            "21": {
                NAME: "exp_1_soc?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "22": {
                NAME: "exp_1_soh?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "28": {
                NAME: "exp_1_type",
                LENGTH: 10,
                TYPE: DeviceHexDataTypes.str.value,
            },
        }
    },
    "a5": {
        BYTES: {
            "00": {
                NAME: "exp_2_sn?",
                LENGTH: 16,
                TYPE: DeviceHexDataTypes.str.value,
            },
            "19": {
                NAME: "exp_2_temperature?",
                TYPE: DeviceHexDataTypes.ui.value,
                SIGNED: True,
            },
            "21": {
                NAME: "exp_2_soc?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "22": {
                NAME: "exp_2_soh?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "28": {
                NAME: "exp_2_type",
                LENGTH: 10,
                TYPE: DeviceHexDataTypes.str.value,
            },
        }
    },
    "a6": {
        BYTES: {
            "00": {
                NAME: "exp_3_sn?",
                LENGTH: 16,
                TYPE: DeviceHexDataTypes.str.value,
            },
            "19": {
                NAME: "exp_3_temperature?",
                TYPE: DeviceHexDataTypes.ui.value,
                SIGNED: True,
            },
            "21": {
                NAME: "exp_3_soc?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "22": {
                NAME: "exp_3_soh?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "28": {
                NAME: "exp_3_type",
                LENGTH: 10,
                TYPE: DeviceHexDataTypes.str.value,
            },
        }
    },
    "a7": {
        BYTES: {
            "00": {
                NAME: "exp_4_sn?",
                LENGTH: 16,
                TYPE: DeviceHexDataTypes.str.value,
            },
            "19": {
                NAME: "exp_4_temperature?",
                TYPE: DeviceHexDataTypes.ui.value,
                SIGNED: True,
            },
            "21": {
                NAME: "exp_4_soc?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "22": {
                NAME: "exp_4_soh?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "28": {
                NAME: "exp_4_type",
                LENGTH: 10,
                TYPE: DeviceHexDataTypes.str.value,
            },
        }
    },
    "a8": {
        BYTES: {
            "00": {
                NAME: "exp_5_sn?",
                LENGTH: 16,
                TYPE: DeviceHexDataTypes.str.value,
            },
            "19": {
                NAME: "exp_5_temperature?",
                TYPE: DeviceHexDataTypes.ui.value,
                SIGNED: True,
            },
            "21": {
                NAME: "exp_5_soc?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "22": {
                NAME: "exp_5_soh?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "28": {
                NAME: "exp_5_type",
                LENGTH: 10,
                TYPE: DeviceHexDataTypes.str.value,
            },
        }
    },
    "a9": {
        BYTES: {
            "00": {
                NAME: "exp_6_sn?",
                LENGTH: 16,
                TYPE: DeviceHexDataTypes.str.value,
            },
            "19": {
                NAME: "exp_6_temperature?",
                TYPE: DeviceHexDataTypes.ui.value,
                SIGNED: True,
            },
            "21": {
                NAME: "exp_6_soc?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "22": {
                NAME: "exp_6_soh?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "28": {
                NAME: "exp_6_type",
                LENGTH: 10,
                TYPE: DeviceHexDataTypes.str.value,
            },
        }
    },
    "fe": {NAME: "msg_timestamp"},
}

_A1790_0410 = {
    # F3800 param info
    TOPIC: "param_info",
    "a2": {
        BYTES: {
            "00": {
                NAME: "power_panel_sn?",
                LENGTH: 16,
                TYPE: DeviceHexDataTypes.str.value,
            },
        }
    },
    "a3": {
        BYTES: {
            "00": {
                NAME: "pps_1_sn?",
                LENGTH: 16,
                TYPE: DeviceHexDataTypes.str.value,
            },
        }
    },
    "a4": {
        BYTES: {
            "00": {
                NAME: "pps_2_sn?",
                LENGTH: 16,
                TYPE: DeviceHexDataTypes.str.value,
            },
        }
    },
    "a5": {NAME: "pps_1_model?"},
    "a6": {NAME: "pps_2_model?"},
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
    "b1": {NAME: "pv_yield?", FACTOR: 0.0001},
    "b3": {NAME: "home_consumption?", FACTOR: 0.0001},
    "b2": {NAME: "charged_energy?", FACTOR: 0.00001},
    "b4": {NAME: "output_cutoff_data"},
    "b5": {NAME: "lowpower_input_data"},
    "b6": {NAME: "input_cutoff_data"},
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
    "c9": {NAME: "ac_input_power?", FACTOR: 0.1},
    "ca": {NAME: "pv_1_power", FACTOR: 0.1},
    "cb": {NAME: "pv_2_power", FACTOR: 0.1},
    "cc": {NAME: "pv_3_power", FACTOR: 0.1},
    "cd": {NAME: "pv_4_power", FACTOR: 0.1},
    "d2": {NAME: "light_mode"},  # Normal mode (0) or Mood mode (1)
    "d3": {NAME: "output_power", FACTOR: 0.1},
    "e0": {NAME: "grid_status"},  # Grid OK (1), No grid (6), Grid connecting (3)
    "e1": {NAME: "light_off_switch"},  # Light on (0), Light off (1)
    "e8": {NAME: "battery_heating"},  # Not heating (1), heating (3)
    "fb": {
        BYTES: {
            "00": [{NAME: "grid_export_disabled", MASK: 0x01}],
        }
    },
    "fe": {NAME: "msg_timestamp"},
    # "ab": {NAME: "photovoltaic_power"},
    # "ac": {NAME: "battery_power_signed"},
    # "ae": {NAME: "ac_output_power_signed?"},
    # "b2": {NAME: "discharged_energy?"},
    # "ba": {
    #     BYTES: {
    #         "00": [
    #             {NAME: "light_mode", MASK: 0x40}, # Normal mode (0) or Mood mode (1)
    #             {NAME: "light_off_switch", MASK: 0x20}, # Enable (0) or disable (1) LEDs
    #             {NAME: "ac_socket_switch", MASK: 0x08}, # Disable (0) or enable (1) AC socket
    #             {NAME: "temp_unit_fahrenheit", MASK: 0x01},  # Toggle °C(0) or F(1) unit, this does not change temperature value itself
    #         ],
    #     }
    # },
    # "bb": {NAME: "heating_power"},
    # "bc": {NAME: "grid_to_battery_power?"},
    # "be": {NAME: "max_load_legal"},
    # "x1": {NAME: "photovoltaic_power"},
    # "c4": {NAME: "grid_power_signed"},
    # "c5": {NAME: "home_demand"},
}

_A17C1_0408 = {
    # Solarbank 2 state info
    TOPIC: "state_info",
    "a2": {NAME: "device_sn"},
    "a3": {NAME: "local_timestamp"},
    "a4": {NAME: "utc_timestamp"},
    "a8": {NAME: "charging_status"},
    # "af": {
    #     BYTES: {
    #         "00": [
    #             {NAME: "light_mode", MASK: 0x40}, # Normal mode (0) or Mood mode (1)
    #             {NAME: "light_off_switch", MASK: 0x20}, # Enable (0) or disable (1) LEDs
    #             {NAME: "ac_socket_switch", MASK: 0x08},  # Disable (0) or enable (1) AC socket
    #             {NAME: "temp_unit_fahrenheit", MASK: 0x01},  # Toggle °C(0) or F(1) unit, this does not change temperature value itself
    #         ],
    #     }
    # },
    "b0": {NAME: "battery_soc"},
    "b6": {NAME: "temperature", SIGNED: True},
    "b7": {NAME: "usage_mode?"},
    "b8": {NAME: "home_load_preset"},
    "bb": {NAME: "ac_input_power?"},
    "c0": {NAME: "discharge_power?"},
    "c1": {NAME: "ac_output_power?", FACTOR: 0.1},
    "c3": {NAME: "grid_import_energy", FACTOR: 0.0001},
    "c4": {NAME: "grid_export_energy", FACTOR: 0.0001},
    "c8": {NAME: "home_demand", FACTOR: 0.1},
    "ce": {NAME: "pv_1_power"},
    "cf": {NAME: "pv_2_power"},
    "d0": {NAME: "pv_3_power"},
    "d1": {NAME: "pv_4_power"},
    # "ab": {NAME: "photovoltaic_power"},
    # "ac": {NAME: "pv_yield?"},
    # "b1": {NAME: "unknown_power_2?"},
    # "b2": {NAME: "home_consumption"},
    # "b6": {NAME: "unknown_power_3?"},
    # "b7": {NAME: "charged_energy?"},
    # "b8": {NAME: "discharged_energy?"},
    # "be": {NAME: "grid_import_energy"},
    # "bf": {NAME: "unknown_energy_5?"},
    # "d3": {NAME: "unknown_power_6?"},
    # "d6": {NAME: "timestamp_1?"},
    # "dc": {NAME: "max_load"},
    # "e0": {NAME: "soc_min?"},
    # "e1": {NAME: "soc_max?"},
    # "e2": {NAME: "pv_power_3rd_party?"},
    # "e6": {NAME: "pv_limit"},
    # "e7": {NAME: "ac_input_limit"},
}

_A17C1_040a = {
    # Solarbank 2 Expansion data
    TOPIC: "param_info",
    "a2": {NAME: "expansion_packs"},
    "a3": {NAME: "main_battery_soc"},  # main battery SOC
    "a4": {
        BYTES: {
            "00": {
                NAME: "exp_1_controller_sn?",
                LENGTH: 17,
                TYPE: DeviceHexDataTypes.str.value,
            },
            "17": {
                NAME: "separator?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "18": {
                NAME: "exp_1_position?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "19": {
                NAME: "exp_1_temperature",
                TYPE: DeviceHexDataTypes.ui.value,
                SIGNED: True,
            },
            "20": {
                NAME: "separator?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "21": {
                NAME: "exp_1_soc",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "22": {
                NAME: "exp_1_soh",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "27": {
                NAME: "exp_1_sn",
                LENGTH: 17,
                TYPE: DeviceHexDataTypes.str.value,
            },
            "44": {
                NAME: "end_marker?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
        }
    },
    "a5": {
        BYTES: {
            "00": {
                NAME: "exp_2_controller_sn?",
                LENGTH: 17,
                TYPE: DeviceHexDataTypes.str.value,
            },
            "17": {
                NAME: "separator?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "18": {
                NAME: "exp_2_position?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "19": {
                NAME: "exp_2_temperature",
                TYPE: DeviceHexDataTypes.ui.value,
                SIGNED: True,
            },
            "20": {
                NAME: "separator?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "21": {
                NAME: "exp_2_soc",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "22": {
                NAME: "exp_2_soh",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "27": {
                NAME: "exp_2_sn",
                LENGTH: 17,
                TYPE: DeviceHexDataTypes.str.value,
            },
            "44": {
                NAME: "end_marker?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
        }
    },
    "a6": {
        BYTES: {
            "00": {
                NAME: "exp_3_controller_sn?",
                LENGTH: 17,
                TYPE: DeviceHexDataTypes.str.value,
            },
            "17": {
                NAME: "separator?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "18": {
                NAME: "exp_3_position?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "19": {
                NAME: "exp_3_temperature",
                TYPE: DeviceHexDataTypes.ui.value,
                SIGNED: True,
            },
            "20": {
                NAME: "separator?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "21": {
                NAME: "exp_3_soc",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "22": {
                NAME: "exp_3_soh",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "27": {
                NAME: "exp_3_sn",
                LENGTH: 17,
                TYPE: DeviceHexDataTypes.str.value,
            },
            "44": {
                NAME: "end_marker?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
        }
    },
    "a7": {
        BYTES: {
            "00": {
                NAME: "exp_4_controller_sn?",
                LENGTH: 17,
                TYPE: DeviceHexDataTypes.str.value,
            },
            "17": {
                NAME: "separator?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "18": {
                NAME: "exp_4_position?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "19": {
                NAME: "exp_4_temperature",
                TYPE: DeviceHexDataTypes.ui.value,
                SIGNED: True,
            },
            "20": {
                NAME: "separator?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "21": {
                NAME: "exp_4_soc",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "22": {
                NAME: "exp_4_soh",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "27": {
                NAME: "exp_4_sn",
                LENGTH: 17,
                TYPE: DeviceHexDataTypes.str.value,
            },
            "44": {
                NAME: "end_marker?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
        }
    },
    "a8": {
        BYTES: {
            "00": {
                NAME: "exp_5_controller_sn?",
                LENGTH: 17,
                TYPE: DeviceHexDataTypes.str.value,
            },
            "17": {
                NAME: "separator?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "18": {
                NAME: "exp_5_position?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "20": {
                NAME: "separator?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "19": {
                NAME: "exp_5_temperature",
                TYPE: DeviceHexDataTypes.ui.value,
                SIGNED: True,
            },
            "21": {
                NAME: "exp_5_soc",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "22": {
                NAME: "exp_5_soh",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "27": {
                NAME: "exp_5_sn",
                LENGTH: 17,
                TYPE: DeviceHexDataTypes.str.value,
            },
            "44": {
                NAME: "end_marker?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
        }
    },
    "fe": {NAME: "msg_timestamp"},
}

_A17C5_0405 = {
    # Solarbank 3 param info
    TOPIC: "param_info",
    "a2": {NAME: "device_sn"},
    "a3": {NAME: "main_battery_soc"},
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
    "b3": {NAME: "grid_import_energy"},
    "b4": {NAME: "grid_export_energy"},
    "b5": {
        NAME: "soc_min"
    },  # TODO: Does this toggle with the setting? Could also be station wide SOC
    "b6": {NAME: "output_cutoff_exp_1?"},  # Could also be min SOC of Main battery?
    "b7": {
        NAME: "output_cutoff_exp_2?"
    },  # Could also be min SOC of first Expansion? But why no other expansion SOC in this message?
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
    "bf": {NAME: "timestamp_backup_start"},
    "c0": {NAME: "timestamp_backup_end"},
    "c2": {NAME: "bat_charge_power?"},
    "c3": {NAME: "photovoltaic_power?"},
    "c4": {NAME: "grid_power_signed"},
    "c5": {NAME: "home_demand"},
    "c6": {NAME: "pv_1_power"},
    "c7": {NAME: "pv_2_power"},
    "c8": {NAME: "pv_3_power"},
    "c9": {NAME: "pv_4_power"},
    "cb": {NAME: "expansion_packs?"},
    "d4": {
        NAME: "device_timeout_minutes",
        FACTOR: 30,
    },  # timeout in 30 min chunks: 0, 30, 60, 120, 240, 360, 720, 1440 minutes
    "d5": {NAME: "pv_limit"},
    "d6": {NAME: "ac_input_limit"},
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
    "a7": {NAME: "battery_soc"},
    "a9": {NAME: "usage_mode"},
    "a8": {NAME: "charging_status?"},
    "aa": {NAME: "home_load_preset"},
    "ab": {NAME: "photovoltaic_power"},
    "ac": {NAME: "pv_yield?"},
    "ad": {NAME: "pv_1_energy?"},
    "ae": {NAME: "pv_2_energy?"},
    "af": {NAME: "pv_3_energy?"},
    "b0": {NAME: "pv_4_energy?"},
    "b1": {NAME: "home_demand?"},
    "b2": {NAME: "home_consumption"},
    "b6": {NAME: "battery_power_signed?"},
    "b7": {NAME: "charged_energy?"},
    "b8": {NAME: "discharged_energy?"},
    "bd": {NAME: "grid_power_signed?"},
    "be": {NAME: "grid_import_energy"},
    "bf": {NAME: "grid_export_energy?"},
    "c7": {NAME: "pv_1_power?"},
    "c8": {NAME: "pv_2_power?"},
    "c9": {NAME: "pv_3_power?"},
    "ca": {NAME: "pv_4_power?"},
    "d3": {NAME: "ac_output_power?"},
    "d6": {NAME: "timestamp_1?"},
    "dc": {NAME: "max_load"},
    "dd": {NAME: "ac_input_limit"},
    "e0": {NAME: "soc_min?"},
    "e1": {NAME: "soc_max?"},
    "e2": {NAME: "pv_power_3rd_party"},
    "e6": {NAME: "pv_limit"},
    "e7": {NAME: "ac_input_limit"},
    "cc": {NAME: "temperature", SIGNED: True},
}

_A17C5_040a = (
    _A17C1_040a
    | {
        # Additional/different Solarbank 3 Expansion data?
    }
)

# 250W Prime Charger
_A2345_0303 = {
    TOPIC: "state_info",
    "a2": {
        BYTES: {
            "01": {
                NAME: "usbc_1_voltage",
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.001,
            },
            "03": {
                NAME: "usbc_1_current",
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.001,
            },
            "05": {
                NAME: "usbc_1_power",
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.01,
            },
        }
    },
    "a3": {
        BYTES: {
            "01": {
                NAME: "usbc_2_voltage",
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.001,
            },
            "03": {
                NAME: "usbc_2_current",
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.001,
            },
            "05": {
                NAME: "usbc_2_power",
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.01,
            },
        }
    },
    "a4": {
        BYTES: {
            "01": {
                NAME: "usbc_3_voltage",
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.001,
            },
            "03": {
                NAME: "usbc_3_current",
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.001,
            },
            "05": {
                NAME: "usbc_3_power",
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.01,
            },
        }
    },
    "a5": {
        BYTES: {
            "01": {
                NAME: "usbc_4_voltage",
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.001,
            },
            "03": {
                NAME: "usbc_4_current",
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.001,
            },
            "05": {
                NAME: "usbc_4_power",
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.01,
            },
        }
    },
    "a6": {
        BYTES: {
            "01": {
                NAME: "usba_1_voltage",
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.001,
            },
            "03": {
                NAME: "usba_1_current",
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.001,
            },
            "05": {
                NAME: "usba_1_power",
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.01,
            },
        }
    },
    "a7": {
        BYTES: {
            "01": {
                NAME: "usba_2_voltage",
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.001,
            },
            "03": {
                NAME: "usba_2_current",
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.001,
            },
            "05": {
                NAME: "usba_2_power",
                TYPE: DeviceHexDataTypes.sile.value,
                FACTOR: 0.01,
            },
        }
    },
    "fe": {NAME: "msg_timestamp"},
}


_DOCK_0420 = {
    # multisystem message
    TOPIC: "param_info",
    "a2": {NAME: "device_sn"},
    "a3": {NAME: "local_timestamp"},
    "a4": {NAME: "utc_timestamp"},
    "a7": {NAME: "battery_soc_total"},  # Average SOC of all solarbank devices in system
    "a8": {NAME: "0420_unknown_1?"},
    "a9": {NAME: "0420_unknown_2?"},
    "ab": {NAME: "grid_power_signed"},
    "ac": {NAME: "ac_output_power_signed_total"},  # Total across all devices in system
    "ae": {NAME: "output_power_signed_total"},  # Total across all devices in system
    "af": {NAME: "home_demand_total"},  # Total across all devices in system
    "b0": {NAME: "pv_power_total"},  # Total across all devices in system
    "b1": {NAME: "battery_power_signed_total"},  # Total across all devices in system
    "b3": {
        BYTES: {
            "00": {
                NAME: "solarbank_1_sn",
                TYPE: DeviceHexDataTypes.str.value,
            },
            "22": {
                NAME: "solarbank_1_soc",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "43": {
                NAME: "solarbank_1_exp_packs?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
        }
    },
    "b4": {
        BYTES: {
            "00": {
                NAME: "solarbank_2_sn",
                TYPE: DeviceHexDataTypes.str.value,
            },
            "22": {
                NAME: "solarbank_2_soc",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "43": {
                NAME: "solarbank_2_exp_packs?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
        }
    },
    "b5": {
        BYTES: {
            "00": {
                NAME: "solarbank_3_sn",
                TYPE: DeviceHexDataTypes.str.value,
            },
            "22": {
                NAME: "solarbank_3_soc",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "43": {
                NAME: "solarbank_3_exp_packs?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
        }
    },
    "b6": {
        BYTES: {
            "00": {
                NAME: "solarbank_4_sn",
                TYPE: DeviceHexDataTypes.str.value,
            },
            "22": {
                NAME: "solarbank_4_soc",
                TYPE: DeviceHexDataTypes.ui.value,
            },
            "43": {
                NAME: "solarbank_4_exp_packs?",
                TYPE: DeviceHexDataTypes.ui.value,
            },
        }
    },
    "c1": {NAME: "main_device_sn?"},
}

_DOCK_0421 = {
    # multisystem message
    TOPIC: "state_info",
    "a3": {NAME: "pv_limit_solarbank_4"},
    "a4": {NAME: "pv_limit_solarbank_3"},
    "a5": {NAME: "pv_limit_solarbank_2"},
    "a6": {NAME: "pv_limit_solarbank_1"},
    "a7": {NAME: "battery_soc_total"},  # Average SOC of all solarbank devices in system
    "ac": {NAME: "soc_max?"},
    "ad": {NAME: "max_load"},
    "fc": {NAME: "device_sn"},
    "fd": {NAME: "local_timestamp"},
    "fe": {NAME: "utc_timestamp"},
}

_DOCK_0428 = {
    # multisystem message
    TOPIC: "state_info",
    "a2": {NAME: "device_sn"},
    "a3": {NAME: "local_timestamp"},
    "a4": {NAME: "utc_timestamp"},
    "a5": {NAME: "battery_soc_total"},  # Average SOC of all solarbanks
    "a6": {NAME: "0428_unknown_1?"},
    "ac": {NAME: "pv_power_total"},
    "b5": {NAME: "battery_power_signed_total"},
    "bc": {NAME: "battery_power_signed"},
    "d9": {
        BYTES: {
            "00": {
                NAME: "solarbank_1_sn",
                TYPE: DeviceHexDataTypes.str.value,
            },
        }
    },
    "da": {
        BYTES: {
            "00": {
                NAME: "solarbank_2_sn",
                TYPE: DeviceHexDataTypes.str.value,
            },
        }
    },
    "db": {
        BYTES: {
            "00": {
                NAME: "solarbank_3_sn",
                TYPE: DeviceHexDataTypes.str.value,
            },
        }
    },
    "dc": {
        BYTES: {
            "00": {
                NAME: "solarbank_4_sn",
                TYPE: DeviceHexDataTypes.str.value,
            },
        }
    },
}

_DOCK_0500 = {
    # Only binary fields, format unknown
    TOPIC: "state_info",
}


# Following is the consolidated mapping for all device types and messages
SOLIXMQTTMAP: Final = {
    # PPS C300 AC
    "A1722": {
        "004b": CMD_DC_OUTPUT_SWITCH,  # DC output switch: Disabled (0) or Enabled (1)
        "004f": CMD_LIGHT_MODE,  # LED mode: Off (0), Low (1), Medium (2), High (3)
        "0052": CMD_DISPLAY_SWITCH,  # Display switch: Disabled (0) or Enabled (1)
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": _A1722_0405,
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": _PPS_VERSIONS_0830,
    },
    # PPS C300X AC
    "A1723": {
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": _A1722_0405,
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": _PPS_VERSIONS_0830,
    },
    # PPS C300 DC
    "A1726": {
        "0043": CMD_DC_OUTPUT_TIMEOUT_SEC,  # DC output timeout: Custom Range 0-10800 seconds
        "004b": CMD_DC_OUTPUT_SWITCH,  # DC output switch: Disabled (0) or Enabled (1)
        "004f": CMD_LIGHT_MODE,  # LED mode: Off (0), Low (1), Medium (2), High (3)
        "0052": CMD_DISPLAY_SWITCH,  # Display switch: Disabled (0) or Enabled (1)
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": _A1728_0405,
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": _PPS_VERSIONS_0830,
    },
    # PPS C300X DC
    "A1728": {
        "0043": CMD_DC_OUTPUT_TIMEOUT_SEC,  # DC output timeout: Custom Range 0-10800 seconds
        "004b": CMD_DC_OUTPUT_SWITCH,  # DC output switch: Disabled (0) or Enabled (1)
        "004f": CMD_LIGHT_MODE,  # LED mode: Off (0), Low (1), Medium (2), High (3)
        "0052": CMD_DISPLAY_SWITCH,  # Display switch: Disabled (0) or Enabled (1)
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": _A1728_0405,
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": _PPS_VERSIONS_0830,
    },
    # PPS C1000(X) + B1000 Extension
    "A1761": {
        "0044": CMD_DEVICE_MAX_LOAD  # TODO: Range to be confirmed: Range: 100-2000 W, Step: 100 W
        | {
            "a2": {
                **CMD_DEVICE_MAX_LOAD["a2"],
                VALUE_MIN: 100,
                VALUE_MAX: 2000,
                VALUE_STEP: 100,
            }
        },
        "0045": CMD_DEVICE_TIMEOUT_MIN,  # Options in minutes: 0 (Never), 30, 60, 120, 240, 360, 720, 1440
        "0046": CMD_DISPLAY_TIMEOUT_SEC,  # Options in seconds: 20, 30, 60, 300, 1800 seconds
        "004a": CMD_AC_OUTPUT_SWITCH,  # AC output switch: Disabled (0) or Enabled (1)
        "004b": CMD_DC_OUTPUT_SWITCH,  # DC output switch: Disabled (0) or Enabled (1)
        "004c": CMD_DISPLAY_MODE,  # Display brightness: Off (0), Low (1), Medium (2), High (3)
        "004f": CMD_LIGHT_MODE,  # LED mode: Off (0), Low (1), Medium (2), High (3), Blinking (4)
        # "00x0": CMD_AC_CHARGE_LIMIT,  # TODO: Update correct message type, What is the range/steps/options? 100-800 W, step 100?
        "0050": CMD_TEMP_UNIT,  # Temperature unit switch: Celsius (0) or Fahrenheit (1)
        "0052": CMD_DISPLAY_SWITCH,  # Display switch: Disabled (0) or Enabled (1)
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        "005e": CMD_AC_FAST_CHARGE_SWITCH,  # Ultrafast charge switch: Disabled (0) or Enabled (1)
        "0076": CMD_DC_12V_OUTPUT_MODE,  # Normal (1), Smart (0)
        "0077": CMD_AC_OUTPUT_MODE,  # Normal (1), Smart (0)
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
                SolixMqttCommands.ac_output_switch,
                SolixMqttCommands.ac_output_timeout_seconds,
                SolixMqttCommands.ac_charge_limit,
                SolixMqttCommands.ac_output_mode_select,
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
        },
        "0102": {
            # DC command group
            COMMAND_LIST: [
                SolixMqttCommands.dc_output_switch,
                SolixMqttCommands.dc_output_timeout_seconds,
                SolixMqttCommands.dc_12v_output_mode_select,
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
                SolixMqttCommands.display_switch,
                SolixMqttCommands.display_mode_select,
                SolixMqttCommands.display_timeout_seconds,
                SolixMqttCommands.device_timeout_minutes,
                SolixMqttCommands.port_memory_switch,
                SolixMqttCommands.soc_limits,
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
                "a4": {  # TODO: Find our correct field in message group
                    NAME: "set_display_timeout_sec",  # 0 (Never), 10, 30, 60, 300, 1800
                    TYPE: DeviceHexDataTypes.sile.value,
                    STATE_NAME: "display_timeout_seconds",
                    VALUE_OPTIONS: [0, 10, 30, 60, 300, 1800],
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
        "0405": _A1761_0405,
        # Interval: ~300 seconds
        "0889": {
            "a4": {NAME: "0889_unknown_1?"},
            "a5": {NAME: "0889_unknown_2?"},
            "a6": {NAME: "0889_unknown_3?"},
            "fd": {NAME: "0880_timestamp?"},
        },
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0421": _A1763_0421,
        # Interval: Irregular, maybe on changes or as response to App status request? Same content as 0421
        "0900": _A1763_0421,
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": _PPS_VERSIONS_0830,
    },
    # PPS F2000
    "A1780": {
        # "0044": CMD_DEVICE_MAX_LOAD,  # TODO: Add supported values or options/range?
        "004a": CMD_AC_OUTPUT_SWITCH,  # AC output switch: Disabled (0) or Enabled (1)
        "004b": CMD_DC_OUTPUT_SWITCH,  # DC output switch: Disabled (0) or Enabled (1)
        "0050": CMD_TEMP_UNIT,  # Temperature unit switch: Celsius (0) or Fahrenheit (1)
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": _A1780_0405,
        # Interval: ??
        "0408": _A1780_0408,
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": _PPS_VERSIONS_0830,
    },
    # PPS F2000 Plus
    "A1780P": {
        # "0044": CMD_DEVICE_MAX_LOAD,  # TODO: Add supported values or options/range?
        "004a": CMD_AC_OUTPUT_SWITCH,  # AC output switch: Disabled (0) or Enabled (1)
        "004b": CMD_DC_OUTPUT_SWITCH,  # DC output switch: Disabled (0) or Enabled (1)
        "0050": CMD_TEMP_UNIT,  # Temperature unit switch: Celsius (0) or Fahrenheit (1)
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": _A1780_0405,
        # Interval: ??
        "0408": _A1780_0408,
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": _PPS_VERSIONS_0830,
    },
    # PPS F3800
    "A1790": {
        "0044": CMD_DEVICE_MAX_LOAD  # Range: 200-1800 W, Step: 100 W
        | {
            "a2": {
                **CMD_DEVICE_MAX_LOAD["a2"],
                VALUE_MIN: 200,
                VALUE_MAX: 1800,
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
        "0076": CMD_DC_12V_OUTPUT_MODE,  # Normal (1), Smart (0)
        "0077": CMD_AC_OUTPUT_MODE,  # Normal (1), Smart (0)
        "0079": CMD_PORT_MEMORY_SWITCH,  # Port Memory switch: Disabled (0) or Enabled (1)
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": _A1790_0405,
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
        "0044": CMD_DEVICE_MAX_LOAD  # Range: 200-1800 W, Step: 100 W
        | {
            "a2": {
                **CMD_DEVICE_MAX_LOAD["a2"],
                VALUE_MIN: 200,
                VALUE_MAX: 1800,
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
        "0076": CMD_DC_12V_OUTPUT_MODE,  # Normal (1), Smart (0)
        "0077": CMD_AC_OUTPUT_MODE,  # Normal (1), Smart (0)
        "0079": CMD_PORT_MEMORY_SWITCH,  # Enabled (1), Disabled (0)
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": _A1790_0405,
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
            "a6": {NAME: "sw_version", "values": 1},
            "a7": {NAME: "sw_controller", "values": 1},
            "a8": {NAME: "hw_version", "values": 1},
            "a9": {NAME: "temp_unit_fahrenheit"},
            "aa": {NAME: "temperature", SIGNED: True},
            "ab": {NAME: "photovoltaic_power"},
            "ac": {NAME: "output_power"},
            "ad": {NAME: "charging_status?"},
            "ae": {
                BYTES: {
                    "12": [{NAME: "allow_export_switch", MASK: 0x04}],
                    "14": {
                        NAME: "charge_priority_limit",
                        TYPE: DeviceHexDataTypes.ui.value,
                    },
                    "15": [{NAME: "priority_discharge_switch", MASK: 0x01}],
                }
            },
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
            "b7": {NAME: "pv_1_voltage", FACTOR: 0.01},
            "b8": {NAME: "pv_2_voltage", FACTOR: 0.01},
            "b9": {NAME: "battery_voltage", FACTOR: 0.01},
        },
    },
    # Solarbank 2 E1600 Pro
    "A17C1": {
        "0050": CMD_TEMP_UNIT,  # Temperature unit switch: Celsius (0) or Fahrenheit (1)
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        # Interval: ~3-5 seconds with realtime trigger, or immediately with status request
        "0067": CMD_SB_POWER_CUTOFF,  # Complex command with multiple parms
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
                SolixMqttCommands.sb_disable_grid_export_switch,  # field a5, a6
            ],
            SolixMqttCommands.sb_max_load: CMD_SB_MAX_LOAD  # 350,600,800,1000 W, may depend on country settings
            | {
                "a2": {
                    **CMD_SB_MAX_LOAD["a2"],
                    VALUE_OPTIONS: [350, 600, 800, 1000],
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
        "0067": CMD_SB_POWER_CUTOFF,  # Complex command with multiple parms
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
                SolixMqttCommands.sb_disable_grid_export_switch,  # field a5, a6
            ],
            SolixMqttCommands.sb_max_load: CMD_SB_MAX_LOAD  # 350,600,800,1000,1200 W, may depend on country settings
            | {
                "a2": {
                    **CMD_SB_MAX_LOAD["a2"],
                    VALUE_OPTIONS: [350, 600, 800, 1000, 1200],
                }
            },
            SolixMqttCommands.sb_disable_grid_export_switch: CMD_SB_DISABLE_GRID_EXPORT_SWITCH,  # Grid export (0), Disable grid export (1)
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
        "0067": CMD_SB_POWER_CUTOFF,  # Complex command with multiple parms
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
                SolixMqttCommands.sb_disable_grid_export_switch,  # field a5, a6
            ],
            SolixMqttCommands.sb_max_load: CMD_SB_MAX_LOAD  # 350,600,800,1000 W, may depend on country settings
            | {
                "a2": {
                    **CMD_SB_MAX_LOAD["a2"],
                    VALUE_OPTIONS: [350, 600, 800, 1000],
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
        "0067": CMD_SB_MIN_SOC,  # select SOC reserve
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
                SolixMqttCommands.sb_disable_grid_export_switch,  # field a5, a6
                SolixMqttCommands.sb_pv_limit_select,  # field a7
                SolixMqttCommands.sb_ac_input_limit,  # field a8
            ],
            SolixMqttCommands.sb_max_load: CMD_SB_MAX_LOAD  # 350,600,800,1000,1200 W, may depend on country settings
            | {
                "a2": {
                    **CMD_SB_MAX_LOAD["a2"],
                    VALUE_OPTIONS: [350, 600, 800, 1000, 1200],
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
    # Anker Power Dock
    "AE100": {
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages 0405 etc
        "0405": {
            # Interval: ~5 seconds, but only with realtime trigger
            TOPIC: "param_info",
            "a2": {NAME: "device_sn"},
            "a3": {NAME: "sw_version", "values": 4},
            "a5": {NAME: "ac_output_power_total"},
            "a6": {NAME: "ac_output_power_signed_total"},
            "b3": {NAME: "utc_timestamp"},
            "b6": {
                BYTES: {
                    "00": {
                        NAME: "solarbank_1_sn",
                        TYPE: DeviceHexDataTypes.str.value,
                    },
                    "19": {
                        NAME: "solarbank_1_soc",
                        TYPE: DeviceHexDataTypes.ui.value,
                    },
                }
            },
            "b7": {NAME: "solarbank_1_ac_output_power_signed"},
            "b8": {
                BYTES: {
                    "00": {
                        NAME: "solarbank_2_sn",
                        TYPE: DeviceHexDataTypes.str.value,
                        "19": {
                            NAME: "solarbank_2_soc",
                            TYPE: DeviceHexDataTypes.ui.value,
                        },
                    },
                }
            },
            "b9": {NAME: "solarbank_2_ac_output_power_signed"},
            "ba": {
                BYTES: {
                    "00": {
                        NAME: "solarbank_3_sn",
                        TYPE: DeviceHexDataTypes.str.value,
                        "19": {
                            NAME: "solarbank_3_soc",
                            TYPE: DeviceHexDataTypes.ui.value,
                        },
                    },
                }
            },
            "bb": {NAME: "solarbank_3_ac_output_power_signed"},
            "bc": {
                BYTES: {
                    "00": {
                        NAME: "solarbank_4_sn",
                        TYPE: DeviceHexDataTypes.str.value,
                    },
                    "19": {
                        NAME: "solarbank_4_soc",
                        TYPE: DeviceHexDataTypes.ui.value,
                    },
                }
            },
            "bd": {NAME: "solarbank_4_ac_output_power_signed"},
        },
        # Interval: varies, probably upon change
        "0407": _0407,
        # multisystem messages
        # Interval: ~3-10 seconds, but only with realtime trigger
        "0420": _DOCK_0420,
        # Interval: ~300 seconds
        "0421": _DOCK_0421,
        # Interval: ~300 seconds
        "0428": _DOCK_0428,
        # Interval: ~300 seconds
        "0500": _DOCK_0500,
    },
    # Prime Charger 250W
    "A2345": {
        "0057": CMD_REALTIME_TRIGGER,  # for regular status messages
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0303": _A2345_0303,
    },
}
