"""Define mapping for MQTT messages field conversions depending on Anker Solix model."""

from .apitypes import DeviceHexDataTypes
from .mqttcmdmap import (
    CMD_AC_CHARGE_LIMIT,
    CMD_AC_FAST_CHARGE_SWITCH,
    CMD_AC_OUTPUT_MODE,
    CMD_AC_OUTPUT_SWITCH,
    CMD_DC_12V_OUTPUT_MODE,
    CMD_DC_OUTPUT_SWITCH,
    CMD_DC_OUTPUT_TIMEOUT_SEC,
    CMD_DEVICE_MAX_LOAD,
    CMD_DEVICE_TIMEOUT_MIN,
    CMD_DISPLAY_MODE,
    CMD_DISPLAY_SWITCH,
    CMD_DISPLAY_TIMEOUT_SEC,
    CMD_LIGHT_MODE,
    CMD_LIGHT_SWITCH,
    CMD_PORT_MEMORY_SWITCH,
    CMD_REALTIME_TRIGGER,
    CMD_SB_INVERTER_TYPE,
    CMD_SB_POWER_CUTOFF,
    CMD_SB_STATUS_CHECK,
    CMD_TEMP_UNIT,
)

# SOLIXMQTTMAP descriptions:
# It is a nested structure to describe value extraction from Solix MQTT messages per model.messagetype.fieldname.attributes
# Field format 0x00 is variable number of bytes, string value (Base type), no special mapping attributes
# Field format 0x01 is 1 byte fix, unsigned int (Base type), "factor" can be specified optionally for value conversion
# Field format 0x02 is 2 bytes fix, signed int LE (Base type), "factor" can be specified optionally for value conversion
# Field format 0x03 is always 4 bytes, but could be 1-4 * int, 1-2 * signed int LE or 4 Bytes signed int LE
#   The mapping must specify "values" to indicate number of values in bytes from beginning. Default is 0 for 1 value in 4 bytes
#   "factor" can be specified optionally for value conversion (applies to all values)
# Field format 0x04 is a bit mask pattern, byte number [00..len-1] reflects position, mask reflects the bit relevant for the value/toggle
#   The mapping must specify start byte string ("00"-"len-1") for fields, field description is a list, since single field can be used for various named settings
#   Each named setting must describe a "mask" integer to indicate which bit(s) are relevant for the named setting, e.g. mask 0x64 => 0100 0000
# Field format 0x05 is 4 bytes, signed float LE (Base type), "factor" can be specified optionally for value conversion
# Field format 0x06 can be many bytes, mix of Str and Byte values
#   The mapping must specify start byte string ("00"-"len-1") for fields, field description needs "type" with a DeviceHexDataTypes base type vor value conversion.
#   The "length" with int for byte count can be specified (default is 1 Byte), where Length of 0 indicates that first byte contains variable field length
#   "factor" can be specified optionally for value conversion
# "factor" usage example: e.g. int field value -123456 with factor -0.001 will convert the value to float 123.456 (maintaining factor's precision)
# Timestamp values should contain "timestamp" in name to allow decoder methods to convert value to human readable format
# Version declaration bytes should contain "sw_" or "version" in name to convert the value(s) into version string
# Names with ? are hints for fields still to be validated. Names without ? should really be validated for correctness in various situations of the device
# Duplicate names for different fields must be avoided for same device types across its various message types. If same values show up in different message types
# the field name should be the same, so they can be merged once extracting the values from the messages into a consolidated dictionary for the device.

# To simplify the defined map, smaller and re-usable mappings should be defined independently and just re-used in the overall SOLIXMQTTMAP for
# the model types that use same field mapping structure. For example various models of the same family most likely share complete or subset of message maps

PPS_VERSIONS_0830 = {
    # Various PPS device version param info
    "topic": "param_info",
    "a1": {
        "name": "hw_version",
        "type": DeviceHexDataTypes.str.value,
    },
    "a2": {
        "name": "sw_version",
        "type": DeviceHexDataTypes.str.value,
    },
}

A1722_0405 = {
    # C300 AC param info
    "topic": "param_info",
    "a4": {"name": "remaining_time_hours", "factor": 0.1},
    "a7": {"name": "usbc_1_power"},  # USB-C port 1 output power
    "a8": {"name": "usbc_2_power"},  # USB-C port 2 output power
    "a9": {"name": "usbc_3_power"},  # USB-C port 3 output power
    "aa": {"name": "usba_1_power"},  # USB-A port 1 output power
    "ac": {"name": "dc_input_power_total"},  # DC input power (solar/car charging)
    "ad": {"name": "ac_input_power_total"},  # Total AC Input in W (int)
    "ae": {"name": "ac_output_power_total"},  # Total AOutput in W (int)
    "b7": {
        "name": "ac_output_power_switch"
    },  # AC output switch: Disabled (0) or Enabled (1)
    "b8": {"name": "dc_charging_status"},  # None (0), Charging (1)
    "b9": {"name": "temperature"},  # In Celsius
    "ba": {"name": "charging_status"},  # None (0), Discharging (1), Charging (2) ???
    "bb": {"name": "battery_soc?"},  # Battery SOC
    "bc": {"name": "battery_soh?"},  # Battery Health?
    "c1": {
        "name": "dc_output_power_switch"
    },  # DC output switch: Disabled (0) or Enabled (1)
    "cf": {
        "name": "display_mode"
    },  # Display brightness: Off (0), Low (1), Medium (2), High (3)
    "fe": {"name": "msg_timestamp"},  # Message timestamp
}

A1728_0405 = {
    # C300(X) DC param info
    "topic": "param_info",
    "a3": {"name": "remaining_time_hours", "factor": 0.1},
    "a4": {"name": "usbc_1_power"},  # USB-C left output power
    "a5": {"name": "usbc_2_power"},  # USB-C center output power
    "a6": {"name": "usbc_3_power"},  # USB-C right output power
    "a7": {"name": "usbc_4_power"},  # USB-C solar output power
    "a8": {"name": "usba_1_power"},  # USB-A left output power
    "a9": {"name": "usba_2_power"},  # USB-A right output power
    "aa": {"name": "dc_input_power?"},  # DC input power 12V car charging?
    "ab": {"name": "photovoltaic_power"},  # Solar input
    "ac": {"name": "dc_input_power_total?"},  # DC input power (solar + car charging)?
    "ad": {"name": "output_power_total?"},  # Total DC output power for all ports?
    "b5": {"name": "temperature"},  # In Celsius
    "b6": {
        "name": "charging_status",  # Publishes the raw integer value (0-3): Inactive (0), Solar (1), DC Input (2), Both (3)
    },
    "b7": {"name": "battery_soc"},  # Battery SOC
    "b8": {"name": "battery_soh"},  # Battery health
    "b9": {
        "name": "usbc_1_status"
    },  # USB-C left status: Inactive (0), Discharging (1), Charging (2)
    "ba": {
        "name": "usbc_2_status"
    },  # USB-C center status: Inactive (0), Discharging (1), Charging (2)
    "bb": {
        "name": "usbc_3_status"
    },  # USB-C right status: Inactive (0), Discharging (1), Charging (2)
    "bc": {
        "name": "usbc_4_status"
    },  # USB-C solar status: Inactive (0), Discharging (1), Charging (2)
    "bd": {
        "name": "usba_1_status"
    },  # USB-A left status: Inactive (0), Discharging (1), Charging (2)
    "be": {
        "name": "usba_2_status"
    },  # USB-A right status: Inactive (0), Discharging (1), Charging (2)
    "bf": {"name": "light_switch"}, # Off (0), On (1)
    "c4": {"name": "dc_output_timeout_seconds?"}, # Timeout seconds, custom range: 0-10800???
    "c5": {
        "name": "display_timeout_seconds?"
    },  # Display timeout: 20, 30, 60, 300, 1800 seconds???
    "c8": {
        "name": "display_mode"
    },  # Brightness: Off (0), Low (1), Medium (2), High (3)
    "fe": {"name": "msg_timestamp"},  # Message timestamp
}

A1780_0405 = {
    # F2000(P) param info
    "topic": "param_info",
    "a4": {"name": "remaining_time_hours", "factor": 0.1},  # In hours
    "a5": {"name": "grid_to_battery_power"},  # AC charging power to battery
    "a6": {"name": "ac_socket_power"},  # Individual AC outlet power
    "a7": {"name": "usbc_1_power"},  # USB-C port 1 output power
    "a8": {"name": "usbc_2_power"},  # USB-C port 2 output power
    "a9": {"name": "usbc_3_power"},  # USB-C port 3 output power
    "aa": {"name": "usba_1_power"},  # USB-A port 1 output power
    "ab": {"name": "usba_2_power"},  # USB-A port 2 output power
    "ac": {"name": "dc_12v_1_power"},  # 12V port 1 output power
    "ad": {"name": "dc_12v_2_power"},  # 12V port 2 output power
    "ae": {"name": "dc_input_power"},  # DC input power (solar/car charging)
    "af": {"name": "ac_input_power"},  # AC input power (230V)
    "b0": {"name": "ac_output_power_total"},  # Total output power
    "b3": {"name": "sw_version", "values": 1},  # Main firmware version
    "b9": {"name": "sw_expansion", "values": 1},  # Expansion firmware version
    "ba": {"name": "sw_controller", "values": 1},  # Controller firmware version
    "bd": {"name": "temperature"},  # Main device temperature (°C)
    "be": {"name": "exp_1_temperature"},  # Expansion battery 1 temperature (°C)
    "c0": {"name": "expansion_packs_a?"},
    "c1": {"name": "battery_soc"},  # Main battery state of charge (%)
    "c2": {"name": "exp_1_soc"},  # Expansion battery 1 state of charge (%)
    "c3": {"name": "battery_soh"},  # Main battery state of health (%)
    "c4": {"name": "exp_1_soh"},  # Expansion battery 1 state of health (%)
    "c5": {"name": "expansion_packs_b?"},
    "d0": {"name": "device_sn"},
    "d1": {"name": "max_load"},  # Maximum load setting (W)
    "d3": {
        "name": "device_timeout_minutes"
    },  # Device auto-off timeout (minutes): 0 (Never), 30, 60, 120, 240, 360, 720, 1440
    "d4": {
        "name": "display_timeout_seconds"
    },  # Display timeout: 20, 30, 60, 300, 1800 seconds
    "d7": {"name": "ac_output_power_switch"},  # Disabled (0) or Enabled (1)
    "d8": {"name": "dc_output_power_switch"},  # Disabled (0) or Enabled (1)
    "d9": {
        "name": "display_mode"
    },  # Brightness: Off (0), Low (1), Medium (2), High (3)
    "db": {"name": "energy_saving_mode"},  # Disabled (0) or Enabled (1)
    "dc": {
        "name": "light_mode"
    },  # Off (0), Low (1), Medium (2), High (3), Blinking (4)
    "dd": {"name": "temp_unit_fahrenheit"},  # Celsius (0) or Fahrenheit (1)
    "de": {"name": "display_switch"},  # Off (0) or On (1)
    "e5": {"name": "backup_charge_switch"},  # Off (0) or On (1)
    "f8": {
        "bytes": {
            "00": {
                "name": "dc_12v_output_mode",  # Normal (1), Smart (2) - auto-off below 3W
                "type": DeviceHexDataTypes.ui.value,
            },
            "01": {
                "name": "ac_output_mode",  # Normal (1), Smart (2) - auto-off when not charging and low power
                "type": DeviceHexDataTypes.ui.value,
            },
        }
    },
    "fd": {"name": "exp_1_type"},  # Expansion battery type identifier
    "fe": {"name": "msg_timestamp"},  # Message timestamp
}

A1780_0408 = {
    # F2000(P) state info
    "topic": "state_info",
    "a3": {"name": "device_sn"},
    "a4": {"name": "local_timestamp?"},
    "a5": {"name": "utc_timestamp?"},
    "a6": {"name": "discharged_energy?", "factor": 0.001},  # in kWh
    "a7": {"name": "charged_energy?", "factor": 0.001},  # in kWh
    "ac": {"name": "battery_soc"},  # in %
}

A1790_0405 = {
    # F3800 param info
    "topic": "param_info",
    "a4": {"name": "remaining_time_hours", "factor": 0.1},  # In hours
    "a5": {"name": "ac_input_power"},
    "a6": {"name": "ac_output_power"},
    "a7": {"name": "usbc_1_power"},
    "a8": {"name": "usbc_2_power"},
    "a9": {"name": "usbc_3_power"},
    "aa": {"name": "usba_1_power?"},
    "ab": {"name": "usba_2_power?"},
    "ac": {"name": "dc_12v_output_power_switch?"},
    "ad": {"name": "battery_soc_total"},
    "ae": {"name": "photovoltaic_power"},  # Total solar input
    "af": {"name": "pv_1_power"},
    "b0": {"name": "pv_2_power"},
    "b1": {"name": "bat_charge_power"},  # Total charging (AC + Solar)
    "b2": {"name": "output_power"},
    "b4": {"name": "bat_discharge_power?"},
    "b5": {"name": "sw_version?", "values": 1},  # Main firmware version
    "ba": {"name": "sw_expansion?", "values": 1},  # Expansion firmware version
    "bc": {
        "name": "ac_output_power_switch"
    },  # AC output switch: Disabled (0) or Enabled (1)
    "bd": {
        "name": "charging_status",  # Publishes the raw integer value (0-3): Inactive (0), Solar (1), AC Input (2), Both (3)
    },
    "be": {"name": "temperature"},  # In Celsius
    "bf": {"name": "display_status"},  # Asleep (0), Manual Off (1), On (2)
    "c0": {"name": "battery_soc_total_dup?"},  # Duplicate of ad?
    "c1": {
        "name": "max_soc"
    },  # User Setting (Max SoC %) TODO: What is the command to define SOC max limit?
    # TODO: What does USB status mean, is that a toggle setting? If port is used, this should be indicated by power as well
    "c2": {"name": "usbc_1_status"},
    "c3": {"name": "usbc_2_status"},
    "c4": {"name": "usbc_3_status"},
    "c5": {"name": "usba_1_status?"},
    "c6": {"name": "usba_2_status?"},
    "c7": {
        "name": "dc_output_power_switch"
    },  # 12V DC output switch: Disabled (0) or Enabled (1)
    "cc": {"name": "device_sn"},
    "cd": {"name": "ac_input_limit"},  # User Setting (AC Charge Watts)
    "cf": {"name": "display_timeout_seconds"},  # User Setting (in seconds)
    "d3": {"name": "ac_output_power_switch_dup?"},  # Duplicate of bc?
    "d4": {"name": "dc_output_power_switch_dup?"},  # Duplicate of c7?
    "d5": {
        "name": "display_mode"
    },  # Display brightness: Off (0), Low (1), Medium (2), High (3)
    "d8": {
        "name": "temp_unit_fahrenheit"
    },  # Temperature unit: Celsius (0) or Fahrenheit (1)
    "d9": {
        "name": "light_mode"
    },  # LED light mode: Off (0), Low (1), Medium (2), High (3), Blinking (4)
    "f6": {"name": "region?"},  # Value 21333 ("US")
    "f7": {
        "name": "port_memory_switch"
    },  # Port Memory switch: Disabled (0) or Enabled (1)
    "fd": {"name": "exp_1_type"},  # Expansion battery type identifier
    "fe": {"name": "msg_timestamp"},
}

A1790_040a = {
    # F3800 param info
    "topic": "param_info",
}

A1790_0410 = {
    # F3800 param info
    "topic": "param_info",
    "a2": {
        "bytes": {
            "00": {
                "name": "power_panel_sn?",
                "length": 16,
                "type": DeviceHexDataTypes.str.value,
            },
        }
    },
    "a3": {
        "bytes": {
            "00": {
                "name": "pps_1_sn?",
                "length": 16,
                "type": DeviceHexDataTypes.str.value,
            },
        }
    },
    "a4": {
        "bytes": {
            "00": {
                "name": "pps_2_sn?",
                "length": 16,
                "type": DeviceHexDataTypes.str.value,
            },
        }
    },
    "a5": {"name": "pps_1_model?"},
    "a6": {"name": "pps_2_model?"},
    "fe": {"name": "msg_timestamp"},
}

A1790_0804 = {
    # F3800 param info
    "topic": "param_info",
}

A17C0_0407 = {
    # Solarbank network message
    "topic": "state_info",
    "a2": {"name": "device_sn"},
    "a3": {"name": "wifi_name"},
    "a4": {"name": "wifi_signal"},
    "a5": {"name": "charging_status"},
}

A17C1_0405 = {
    # Solarbank 2 param info
    "topic": "param_info",
    "a2": {"name": "device_sn"},
    "a3": {"name": "battery_soc"},
    "a5": {"name": "error_code"},
    "a6": {"name": "sw_version", "values": 4},
    "a7": {"name": "sw_controller?", "values": 4},
    "a8": {"name": "sw_expansion", "values": 4},
    "a9": {"name": "temp_unit_fahrenheit"},
    "aa": {"name": "temperature"},
    "ab": {"name": "photovoltaic_power", "factor": 0.1},
    "ac": {"name": "ac_output_power", "factor": 0.1},
    "ad": {"name": "battery_soc_total"},
    "b0": {"name": "bat_charge_power", "factor": 0.01},
    "b1": {"name": "pv_yield?", "factor": 0.0001},
    "b2": {"name": "charged_energy?", "factor": 0.00001},
    "b3": {"name": "home_consumption?", "factor": 0.0001},
    "b4": {"name": "output_cutoff_data"},
    "b5": {"name": "lowpower_input_data"},
    "b6": {"name": "input_cutoff_data"},
    "b7": {"name": "bat_discharge_power", "factor": 0.01},
    "bc": {"name": "grid_to_home_power", "factor": 0.1},
    "bd": {"name": "pv_to_grid_power", "factor": 0.1},
    "c4": {"name": "home_demand", "factor": 0.1},
    "c2": {"name": "max_load"},
    "c6": {"name": "usage_mode"},
    "c7": {"name": "home_load_preset"},
    "c8": {"name": "ac_socket_power", "factor": 0.1},
    "ca": {"name": "pv_1_power", "factor": 0.1},
    "cb": {"name": "pv_2_power", "factor": 0.1},
    "cc": {"name": "pv_3_power", "factor": 0.1},
    "cd": {"name": "pv_4_power", "factor": 0.1},
    "d3": {"name": "output_power", "factor": 0.1},
    "e0": {"name": "grid_status"},  # Grid OK (1), No grid (6), Grid connecting (3)
    "fb": {
        "bytes": {
            "00": [{"name": "grid_export_disabled", "mask": 0x01}],
        }
    },
    "fe": {"name": "msg_timestamp"},
    # "ab": {"name": "photovoltaic_power"},
    # "ac": {"name": "battery_power_signed"},
    # "ae": {"name": "ac_output_power_signed?"},
    # "b2": {"name": "discharged_energy?"},
    # "ba": {
    #     "bytes": {
    #         "00": [
    #             {"name": "light_mode", "mask": 0x40}, # Normal mode (0) or Mood mode (1)
    #             {"name": "light_off_switch", "mask": 0x20}, # Enable (0) or disable (1) LEDs
    #             {"name": "ac_socket_switch", "mask": 0x08}, # Disable (0) or enable (1) AC socket
    #             {"name": "temp_unit_fahrenheit", "mask": 0x01},  # Toggle °C(0) or F(1) unit, this does not change temperature value itself
    #         ],
    #     }
    # },
    # "bb": {"name": "heating_power"},
    # "bc": {"name": "grid_to_battery_power?"},
    # "be": {"name": "max_load_legal"},
    # "x1": {"name": "photovoltaic_power"},
    # "c4": {"name": "grid_power_signed"},
    # "c5": {"name": "home_demand"},
}

A17C1_0408 = {
    # Solarbank 2 state info
    "topic": "state_info",
    "a2": {"name": "device_sn"},
    "a3": {"name": "local_timestamp"},
    "a4": {"name": "utc_timestamp"},
    "a8": {"name": "charging_status"},
    # "af": {
    #     "bytes": {
    #         "00": [
    #             {"name": "light_mode", "mask": 0x40}, # Normal mode (0) or Mood mode (1)
    #             {"name": "light_off_switch", "mask": 0x20}, # Enable (0) or disable (1) LEDs
    #             {"name": "ac_socket_switch", "mask": 0x08},  # Disable (0) or enable (1) AC socket
    #             {"name": "temp_unit_fahrenheit", "mask": 0x01},  # Toggle °C(0) or F(1) unit, this does not change temperature value itself
    #         ],
    #     }
    # },
    "b0": {"name": "battery_soc"},
    "b6": {"name": "temperature"},
    "b7": {"name": "usage_mode?"},
    "b8": {"name": "home_load_preset"},
    "ce": {"name": "pv_1_power"},
    "cf": {"name": "pv_2_power"},
    "d0": {"name": "pv_3_power"},
    "d1": {"name": "pv_4_power"},
    # "ab": {"name": "photovoltaic_power"},
    # "ac": {"name": "pv_yield?"},
    # "b1": {"name": "unknown_power_2?"},
    # "b2": {"name": "home_consumption"},
    # "b6": {"name": "unknown_power_3?"},
    # "b7": {"name": "charged_energy?"},
    # "b8": {"name": "discharged_energy?"},
    # "be": {"name": "grid_import_energy"},
    # "bf": {"name": "unknown_energy_5?"},
    # "d3": {"name": "unknown_power_6?"},
    # "d6": {"name": "timestamp_1?"},
    # "dc": {"name": "max_load"},
    # "e0": {"name": "soc_min?"},
    # "e1": {"name": "soc_max?"},
    # "e2": {"name": "pv_power_3rd_party?"},
    # "e6": {"name": "pv_limit"},
    # "e7": {"name": "ac_input_limit"},
}

A17C1_040a = {
    # Solarbank 2 Expansion data
    "topic": "param_info",
    "a2": {"name": "expansion_packs"},
    "a3": {"name": "lowest_soc?"},
    "a4": {
        "bytes": {
            "00": {
                "name": "exp_1_controller_sn?",
                "length": 17,
                "type": DeviceHexDataTypes.str.value,
            },
            "17": {
                "name": "separator?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "18": {
                "name": "exp_1_position?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "19": {
                "name": "exp_1_temperature",
                "type": DeviceHexDataTypes.ui.value,
            },
            "20": {
                "name": "separator?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "21": {
                "name": "exp_1_soc",
                "type": DeviceHexDataTypes.ui.value,
            },
            "22": {
                "name": "exp_1_soh",
                "type": DeviceHexDataTypes.ui.value,
            },
            "27": {
                "name": "exp_1_sn",
                "length": 17,
                "type": DeviceHexDataTypes.str.value,
            },
            "44": {
                "name": "end_marker?",
                "type": DeviceHexDataTypes.ui.value,
            },
        }
    },
    "a5": {
        "bytes": {
            "00": {
                "name": "exp_2_controller_sn?",
                "length": 17,
                "type": DeviceHexDataTypes.str.value,
            },
            "17": {
                "name": "separator?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "18": {
                "name": "exp_2_position?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "19": {
                "name": "exp_2_temperature",
                "type": DeviceHexDataTypes.ui.value,
            },
            "20": {
                "name": "separator?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "21": {
                "name": "exp_2_soc",
                "type": DeviceHexDataTypes.ui.value,
            },
            "22": {
                "name": "exp_2_soh",
                "type": DeviceHexDataTypes.ui.value,
            },
            "27": {
                "name": "exp_2_sn",
                "length": 17,
                "type": DeviceHexDataTypes.str.value,
            },
            "44": {
                "name": "end_marker?",
                "type": DeviceHexDataTypes.ui.value,
            },
        }
    },
    "a6": {
        "bytes": {
            "00": {
                "name": "exp_3_controller_sn?",
                "length": 17,
                "type": DeviceHexDataTypes.str.value,
            },
            "17": {
                "name": "separator?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "18": {
                "name": "exp_3_position?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "19": {
                "name": "exp_3_temperature",
                "type": DeviceHexDataTypes.ui.value,
            },
            "20": {
                "name": "separator?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "21": {
                "name": "exp_3_soc",
                "type": DeviceHexDataTypes.ui.value,
            },
            "22": {
                "name": "exp_3_soh",
                "type": DeviceHexDataTypes.ui.value,
            },
            "27": {
                "name": "exp_3_sn",
                "length": 17,
                "type": DeviceHexDataTypes.str.value,
            },
            "44": {
                "name": "end_marker?",
                "type": DeviceHexDataTypes.ui.value,
            },
        }
    },
    "a7": {
        "bytes": {
            "00": {
                "name": "exp_4_controller_sn?",
                "length": 17,
                "type": DeviceHexDataTypes.str.value,
            },
            "17": {
                "name": "separator?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "18": {
                "name": "exp_4_position?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "19": {
                "name": "exp_4_temperature",
                "type": DeviceHexDataTypes.ui.value,
            },
            "20": {
                "name": "separator?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "21": {
                "name": "exp_4_soc",
                "type": DeviceHexDataTypes.ui.value,
            },
            "22": {
                "name": "exp_4_soh",
                "type": DeviceHexDataTypes.ui.value,
            },
            "27": {
                "name": "exp_4_sn",
                "length": 17,
                "type": DeviceHexDataTypes.str.value,
            },
            "44": {
                "name": "end_marker?",
                "type": DeviceHexDataTypes.ui.value,
            },
        }
    },
    "a8": {
        "bytes": {
            "00": {
                "name": "exp_5_controller_sn?",
                "length": 17,
                "type": DeviceHexDataTypes.str.value,
            },
            "17": {
                "name": "separator?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "18": {
                "name": "exp_5_position?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "20": {
                "name": "separator?",
                "type": DeviceHexDataTypes.ui.value,
            },
            "19": {
                "name": "exp_5_temperature",
                "type": DeviceHexDataTypes.ui.value,
            },
            "21": {
                "name": "exp_5_soc",
                "type": DeviceHexDataTypes.ui.value,
            },
            "22": {
                "name": "exp_5_soh",
                "type": DeviceHexDataTypes.ui.value,
            },
            "27": {
                "name": "exp_5_sn",
                "length": 17,
                "type": DeviceHexDataTypes.str.value,
            },
            "44": {
                "name": "end_marker?",
                "type": DeviceHexDataTypes.ui.value,
            },
        }
    },
    "fe": {"name": "msg_timestamp"},
}

A17C5_0405 = {
    # Solarbank 3 param info
    "topic": "param_info",
    "a2": {"name": "device_sn"},
    "a3": {"name": "battery_soc"},
    "a5": {"name": "temperature"},
    "a6": {"name": "battery_soc_total"},
    "a7": {"name": "sw_version", "values": 4},
    "a8": {"name": "sw_controller?", "values": 4},
    "a9": {"name": "sw_expansion", "values": 4},
    "ab": {"name": "photovoltaic_power"},
    "ac": {"name": "battery_power_signed"},
    "ad": {"name": "output_power"},
    "ae": {"name": "ac_output_power_signed"},
    "b0": {"name": "pv_yield?"},
    "b1": {"name": "charged_energy?"},
    "b2": {"name": "discharged_energy?"},
    "b3": {"name": "energy_4?"},
    "b5": {"name": "output_cutoff_controller?"},
    "b6": {"name": "output_cutoff_exp_1?"},
    "b7": {"name": "output_cutoff_exp_2?"},
    "b8": {"name": "usage_mode"},
    "b9": {"name": "home_load_preset"},
    "ba": {
        "bytes": {
            "00": [
                {
                    "name": "light_mode",
                    "mask": 0x40,
                },  # Normal mode (0) or Mood mode (1)
                {
                    "name": "light_off_switch",
                    "mask": 0x20,
                },  # Enable (0) or disable (1) LEDs
                {
                    "name": "ac_socket_switch",
                    "mask": 0x08,
                },  # Disable (0) or enable (1) AC socket
                {
                    "name": "temp_unit_fahrenheit",
                    "mask": 0x01,
                },  # Toggle °C (0) or F (1) unit, this does not change temperature value itself
            ],
        }
    },
    "bb": {"name": "heating_power"},
    "bc": {"name": "grid_to_battery_power"},
    "bd": {"name": "max_load"},
    "be": {"name": "max_load_legal"},
    "bf": {"name": "timestamp_backup_start"},
    "c0": {"name": "timestamp_backup_end"},
    "c2": {"name": "bat_charge_power?"},
    "c3": {"name": "photovoltaic_power?"},
    "c4": {"name": "grid_power_signed"},
    "c5": {"name": "home_demand"},
    "c6": {"name": "pv_1_power"},
    "c7": {"name": "pv_2_power"},
    "c8": {"name": "pv_3_power"},
    "c9": {"name": "pv_4_power"},
    "cb": {"name": "expansion_packs?"},
    "d4": {"name": "device_timeout_minutes", "factor": 30},
    "d5": {"name": "pv_limit"},
    "d6": {"name": "ac_input_limit"},
    "fb": {
        "bytes": {
            "00": [{"name": "grid_export_disabled", "mask": 0x01}],
        }
    },
    "fe": {"name": "msg_timestamp"},
}

A17C5_0408 = {
    # Solarbank 3 state info
    "topic": "state_info",
    "a2": {"name": "device_sn"},
    "a3": {"name": "local_timestamp"},
    "a4": {"name": "utc_timestamp"},
    "a7": {"name": "battery_soc"},
    "a9": {"name": "usage_mode"},
    "a8": {"name": "charging_status?"},
    "aa": {"name": "home_load_preset"},
    "ab": {"name": "photovoltaic_power"},
    "ac": {"name": "pv_yield?"},
    "ad": {"name": "pv_1_energy?"},
    "ae": {"name": "pv_2_energy?"},
    "af": {"name": "pv_3_energy?"},
    "b0": {"name": "pv_4_energy?"},
    "b1": {"name": "home_demand?"},
    "b2": {"name": "home_consumption"},
    "b6": {"name": "battery_power_signed?"},
    "b7": {"name": "charged_energy?"},
    "b8": {"name": "discharged_energy?"},
    "bd": {"name": "grid_power_signed?"},
    "be": {"name": "grid_import_energy"},
    "bf": {"name": "grid_export_energy?"},
    "c7": {"name": "pv_1_power?"},
    "c8": {"name": "pv_2_power?"},
    "c9": {"name": "pv_3_power?"},
    "ca": {"name": "pv_4_power?"},
    "d3": {"name": "ac_output_power?"},
    "d6": {"name": "timestamp_1?"},
    "dc": {"name": "max_load"},
    "dd": {"name": "ac_input_limit"},
    "e0": {"name": "soc_min?"},
    "e1": {"name": "soc_max?"},
    "e2": {"name": "pv_power_3rd_party"},
    "e6": {"name": "pv_limit"},
    "e7": {"name": "ac_input_limit"},
    "cc": {"name": "temperature"},
}

A17C5_040a = (
    A17C1_040a
    | {
        # Solarbank 3 Expansion data
    }
)

DOCK_0420 = {
    # multisystem message
    "topic": "param_info",
    "a2": {"name": "device_sn"},
    "a3": {"name": "local_timestamp"},
    "a4": {"name": "utc_timestamp"},
    "a7": {"name": "battery_soc_total"},
    "a8": {"name": "0420_unknown_1?"},
    "a9": {"name": "0420_unknown_2?"},
    "ab": {"name": "grid_power_signed"},
    "ac": {"name": "ac_output_power_signed_total"},
    "ae": {"name": "output_power_signed_total"},
    "af": {"name": "home_demand_total"},
    "b0": {"name": "pv_power_total"},
    "b1": {"name": "battery_power_signed_total"},
    "b3": {
        "bytes": {
            "00": {
                "name": "solarbank_1_sn",
                "length": 0,  # First byte is byte count for type
                "type": DeviceHexDataTypes.str.value,
            },
            "22": {
                "name": "solarbank_1_soc",
                "type": DeviceHexDataTypes.ui.value,
            },
            "43": {
                "name": "solarbank_1_exp_packs?",
                "type": DeviceHexDataTypes.ui.value,
            },
        }
    },
    "b4": {
        "bytes": {
            "00": {
                "name": "solarbank_2_sn",
                "length": 0,  # First byte is byte count for type
                "type": DeviceHexDataTypes.str.value,
            },
            "22": {
                "name": "solarbank_2_soc",
                "type": DeviceHexDataTypes.ui.value,
            },
            "43": {
                "name": "solarbank_2_exp_packs?",
                "type": DeviceHexDataTypes.ui.value,
            },
        }
    },
    "b5": {
        "bytes": {
            "00": {
                "name": "solarbank_3_sn",
                "length": 0,  # First byte is byte count for type
                "type": DeviceHexDataTypes.str.value,
            },
            "22": {
                "name": "solarbank_3_soc",
                "type": DeviceHexDataTypes.ui.value,
            },
            "43": {
                "name": "solarbank_3_exp_packs?",
                "type": DeviceHexDataTypes.ui.value,
            },
        }
    },
    "b6": {
        "bytes": {
            "00": {
                "name": "solarbank_4_sn",
                "length": 0,  # First byte is byte count for type
                "type": DeviceHexDataTypes.str.value,
            },
            "22": {
                "name": "solarbank_4_soc",
                "type": DeviceHexDataTypes.ui.value,
            },
            "43": {
                "name": "solarbank_4_exp_packs?",
                "type": DeviceHexDataTypes.ui.value,
            },
        }
    },
    "c1": {"name": "main_device_sn?"},
}

DOCK_0421 = {
    # multisystem message
    "topic": "state_info",
    "a3": {"name": "pv_limit_solarbank_4"},
    "a4": {"name": "pv_limit_solarbank_3"},
    "a5": {"name": "pv_limit_solarbank_2"},
    "a6": {"name": "pv_limit_solarbank_1"},
    "a7": {"name": "battery_soc_total"},
    "ac": {"name": "soc_max?"},
    "ad": {"name": "max_load"},
    "fc": {"name": "device_sn"},
    "fd": {"name": "local_timestamp"},
    "fe": {"name": "utc_timestamp"},
}

DOCK_0428 = {
    # multisystem message
    "topic": "state_info",
    "a2": {"name": "device_sn"},
    "a3": {"name": "local_timestamp"},
    "a4": {"name": "utc_timestamp"},
    "a5": {"name": "battery_soc_total"},
    "a6": {"name": "0428_unknown_1?"},
    "ac": {"name": "pv_power_total"},
    "b5": {"name": "battery_power_signed_total"},
    "bc": {"name": "battery_power_signed"},
    "d9": {
        "bytes": {
            "00": {
                "name": "solarbank_1_sn",
                "length": 0,  # First byte is byte count for type
                "type": DeviceHexDataTypes.str.value,
            },
        }
    },
    "da": {
        "bytes": {
            "00": {
                "name": "solarbank_2_sn",
                "length": 0,  # First byte is byte count for type
                "type": DeviceHexDataTypes.str.value,
            },
        }
    },
    "db": {
        "bytes": {
            "00": {
                "name": "solarbank_3_sn",
                "length": 0,  # First byte is byte count for type
                "type": DeviceHexDataTypes.str.value,
            },
        }
    },
    "dc": {
        "bytes": {
            "00": {
                "name": "solarbank_4_sn",
                "length": 0,  # First byte is byte count for type
                "type": DeviceHexDataTypes.str.value,
            },
        }
    },
}

DOCK_0500 = {
    # Only binary fields, format unknown
    "topic": "state_info",
}


# Following is the consolidated mapping for all device types and messages
SOLIXMQTTMAP = {
    # Power Charger C300 AC
    "A1722": {
        "004b": CMD_DC_OUTPUT_SWITCH,  # DC output switch: Disabled (0) or Enabled (1)
        "004f": CMD_LIGHT_MODE,  # LED mode: Off (0), Low (1), Medium (2), High (3)
        "0052": CMD_DISPLAY_SWITCH,  # Display switch: Disabled (0) or Enabled (1)
        "0057": CMD_REALTIME_TRIGGER,
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": A1722_0405,
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": PPS_VERSIONS_0830,
    },
    # Power Charger C300 DC
    "A1726": {
        "0043": CMD_DC_OUTPUT_TIMEOUT_SEC,  # DC output timeout: Custom Range 0-10800 seconds
        "004b": CMD_DC_OUTPUT_SWITCH,  # DC output switch: Disabled (0) or Enabled (1)
        "004f": CMD_LIGHT_MODE,  # LED mode: Off (0), Low (1), Medium (2), High (3)
        "0052": CMD_DISPLAY_SWITCH,  # Display switch: Disabled (0) or Enabled (1)
        "0057": CMD_REALTIME_TRIGGER,
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": A1728_0405,
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": PPS_VERSIONS_0830,
    },
    # Power Charger C300X DC
    "A1728": {
        "0043": CMD_DC_OUTPUT_TIMEOUT_SEC,  # DC output timeout: Custom Range 0-10800 seconds
        "004b": CMD_DC_OUTPUT_SWITCH,  # DC output switch: Disabled (0) or Enabled (1)
        "004f": CMD_LIGHT_MODE,  # LED mode: Off (0), Low (1), Medium (2), High (3)
        "0052": CMD_DISPLAY_SWITCH,  # Display switch: Disabled (0) or Enabled (1)
        "0057": CMD_REALTIME_TRIGGER,
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": A1728_0405,
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": PPS_VERSIONS_0830,
    },
    # PPS C1000(X) + B1000 Extension
    "A1761": {
        "0044": CMD_DEVICE_MAX_LOAD,  # TODO: Add supported values or options/range with steps?
        "0045": CMD_DEVICE_TIMEOUT_MIN,  # Options in minutes: 0 (Never), 30, 60, 120, 240, 360, 720, 1440
        "0046": CMD_DISPLAY_TIMEOUT_SEC,  # Options in seconds: 20, 30, 60, 300, 1800 seconds
        "004a": CMD_AC_OUTPUT_SWITCH,  # AC output switch: Disabled (0) or Enabled (1)
        "004b": CMD_DC_OUTPUT_SWITCH,  # DC output switch: Disabled (0) or Enabled (1)
        "004c": CMD_DISPLAY_MODE,  # Display brightness: Off (0), Low (1), Medium (2), High (3)
        "004f": CMD_LIGHT_MODE,  # LED mode: Off (0), Low (1), Medium (2), High (3), Blinking (4)
        "00x0": CMD_AC_CHARGE_LIMIT,  # TODO: Update correct message type, What is the range/steps/options?
        "0050": CMD_TEMP_UNIT,  # Temperature unit switch: Celsius (0) or Fahrenheit (1)
        "0052": CMD_DISPLAY_SWITCH,  # Display switch: Disabled (0) or Enabled (1)
        "0057": CMD_REALTIME_TRIGGER,
        "005e": CMD_AC_FAST_CHARGE_SWITCH,  # Ultrafast charge switch: Disabled (0) or Enabled (1)
        "0076": CMD_DC_12V_OUTPUT_MODE,  # Normal (1), Smart (0)
        "0077": CMD_AC_OUTPUT_MODE,  # Normal (1), Smart (0)
        "0405": {
            # Interval: ~3-5 seconds, but only with realtime trigger
            "topic": "param_info",
            "a4": {
                "name": "remaining_time_hours",
                "factor": 0.1,
            },  # In hours (value * factor)
            "a5": {"name": "grid_to_battery_power"},  # AC charging power to battery
            "a6": {"name": "ac_output_power"},  # Individual AC outlet power
            "a7": {"name": "usbc_1_power"},  # USB-C port 1 output power
            "a8": {"name": "usbc_2_power"},  # USB-C port 2 output power
            "a9": {"name": "usba_1_power"},  # USB-A port 1 output power
            "aa": {"name": "usba_2_power"},  # USB-A port 2 output power
            "ae": {"name": "dc_input_power"},  # DC input power (solar/car charging)
            "b0": {"name": "ac_output_power_total"},  # Total AC output power
            "b3": {"name": "sw_version", "values": 1},  # Main firmware version
            "b9": {"name": "sw_expansion", "values": 1},  # Expansion firmware version
            "ba": {"name": "sw_controller", "values": 1},  # Controller firmware version
            "bb": {"name": "ac_output_power_switch"},  # Disabled (0) or Enabled (1)
            "bd": {"name": "temperature"},  # Main device temperature (°C)
            "be": {"name": "exp_1_temperature"},  # Expansion battery 1 temperature (°C)
            "c0": {"name": "expansion_packs?"},  # Number of expansion batteries?
            "c1": {"name": "battery_soc"},  # Main battery state of charge (%)
            "c2": {"name": "exp_1_soc"},  # Expansion battery 1 state of charge (%)
            "c3": {"name": "battery_soh"},  # Main battery state of health (%)
            "c4": {"name": "exp_1_soh"},  # Expansion battery 1 state of health (%)
            "c5": {"name": "expansion_packs_b?"},
            "d0": {"name": "device_sn"},  # Device serial number
            "d1": {"name": "max_load"},  # Maximum load setting (W)
            "d2": {
                "name": "device_timeout_minutes"
            },  # Device auto-off timeout (minutes): 0 (Never), 30, 60, 120, 240, 360, 720, 1440
            "d3": {
                "name": "display_timeout_seconds"
            },  # Options: 20, 30, 60, 300, 1800 seconds
            "d8": {"name": "dc_output_power_switch"},  # Disabled (0) or Enabled (1)
            "d9": {
                "name": "display_mode"
            },  # Brightness: Off (0), Low (1), Medium (2), High (3)
            "dc": {
                "name": "light_mode"
            },  # LED light mode: Off (0), Low (1), Medium (2), High (3), Blinking (4)
            "dd": {"name": "temp_unit_fahrenheit"},  # Celsius (0) or Fahrenheit (1)
            "de": {"name": "display_switch"},  # Off (0) or On (1)
            "e5": {"name": "backup_charge_switch"},  # Off (0) or On (1)
            "f8": {
                "bytes": {
                    "00": {
                        "name": "dc_12v_output_mode",  # Normal (1), Smart (2) - auto-off below 3W
                        "type": DeviceHexDataTypes.ui.value,
                    },
                    "01": {
                        "name": "ac_output_mode",  # Normal (1), Smart (2) - auto-off when not charging and low power
                        "type": DeviceHexDataTypes.ui.value,
                    },
                }
            },
            "fd": {"name": "exp_1_type"},  # Expansion battery type identifier
            "fe": {"name": "msg_timestamp"},  # Message timestamp
        },
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": PPS_VERSIONS_0830,
    },
    # PPS F2000
    "A1780": {
        "0044": CMD_DEVICE_MAX_LOAD,  # TODO: Add supported values or options/range?
        "004a": CMD_AC_OUTPUT_SWITCH,  # AC output switch: Disabled (0) or Enabled (1)
        "004b": CMD_DC_OUTPUT_SWITCH,  # DC output switch: Disabled (0) or Enabled (1)
        "0057": CMD_REALTIME_TRIGGER,
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": A1780_0405,
        # Interval: ??
        "0408": A1780_0408,
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": PPS_VERSIONS_0830,
    },
    # PPS F2000 Plus
    "A1780P": {
        "0044": CMD_DEVICE_MAX_LOAD,  # TODO: Add supported values or options/range?
        "004a": CMD_AC_OUTPUT_SWITCH,  # AC output switch: Disabled (0) or Enabled (1)
        "004b": CMD_DC_OUTPUT_SWITCH,  # DC output switch: Disabled (0) or Enabled (1)
        "0057": CMD_REALTIME_TRIGGER,
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": A1780_0405,
        # Interval: ??
        "0408": A1780_0408,
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": PPS_VERSIONS_0830,
    },
    # PPS F3800
    "A1790": {
        "0044": CMD_DEVICE_MAX_LOAD,  # Range: 200-1800 W, Step: 100 W
        "0045": CMD_DEVICE_TIMEOUT_MIN,  # Options in minutes: 0 (Never), 30, 60, 120, 240, 360, 720, 1440
        "0046": CMD_DISPLAY_TIMEOUT_SEC,  # Options in seconds: 20, 30, 60, 300, 1800 seconds
        "004a": CMD_AC_OUTPUT_SWITCH,  # AC output switch: Disabled (0) or Enabled (1)
        "004b": CMD_DC_OUTPUT_SWITCH,  # DC output switch: Disabled (0) or Enabled (1)
        "004c": CMD_DISPLAY_MODE,  # Display brightness: Off (0), Low (1), Medium (2), High (3)
        "004f": CMD_LIGHT_MODE,  # LEF mode: Off (0), Low (1), Medium (2), High (3), Blinking (4)
        "0050": CMD_TEMP_UNIT,  # Temperature unit switch: Celsius (0) or Fahrenheit (1)
        "0052": CMD_DISPLAY_SWITCH,
        "0057": CMD_REALTIME_TRIGGER,
        "0076": CMD_DC_12V_OUTPUT_MODE,  # Normal (1), Off (0)
        "0077": CMD_AC_OUTPUT_MODE,  # Normal (1), Off (0)
        "0079": CMD_PORT_MEMORY_SWITCH,  # Port Memory switch: Disabled (0) or Enabled (1)
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": A1790_0405,
        # Interval: ??
        "040a": A1790_040a,
        # Interval: ??
        "0410": A1790_0410,
        # Interval: ??
        "0804": A1790_0804,
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": PPS_VERSIONS_0830,
        # Interval: ??
        "0840": A1790_0405,
    },
    # PPS F3800 Plus
    "A1790P": {
        "0044": CMD_DEVICE_MAX_LOAD,  # Range: 200-1800 W, Step: 100 W
        "0045": CMD_DEVICE_TIMEOUT_MIN,  # Options in minutes: 0 (Never), 30, 60, 120, 240, 360, 720, 1440
        "0046": CMD_DISPLAY_TIMEOUT_SEC,  # Options in seconds: 20, 30, 60, 300, 1800 seconds
        "004a": CMD_AC_OUTPUT_SWITCH,  # AC output switch: Disabled (0) or Enabled (1)
        "004b": CMD_DC_OUTPUT_SWITCH,  # DC output switch: Disabled (0) or Enabled (1)
        "004c": CMD_DISPLAY_MODE,  # Display brightness: Off (0), Low (1), Medium (2), High (3)
        "004f": CMD_LIGHT_MODE,  # LEF mode: Off (0), Low (1), Medium (2), High (3), Blinking (4)
        "0050": CMD_TEMP_UNIT,  # Temperature unit switch: Celsius (0) or Fahrenheit (1)
        "0052": CMD_DISPLAY_SWITCH,
        "0057": CMD_REALTIME_TRIGGER,
        "0076": CMD_DC_12V_OUTPUT_MODE,  # Normal (1), Off (0)
        "0077": CMD_AC_OUTPUT_MODE,  # Normal (1), Off (0)
        "0079": CMD_PORT_MEMORY_SWITCH,  # Enabled (1), Disabled (0)
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": A1790_0405,
        # Interval: ??
        "040a": A1790_040a,
        # Interval: ??
        "0410": A1790_0410,
        # Interval: ??
        "0804": A1790_0804,
        # Interval: Irregular, triggered on app actions, no fixed interval
        "0830": PPS_VERSIONS_0830,
        # Interval: ??
        "0840": A1790_0405,
    },
    # Solarbank 1 E1600
    "A17C0": {
        "0050": CMD_TEMP_UNIT,  # Temperature unit switch: Celsius (0) or Fahrenheit (1)
        "0056": CMD_SB_STATUS_CHECK,  # Complex command with multiple parms
        "0057": CMD_REALTIME_TRIGGER,
        "0067": CMD_SB_POWER_CUTOFF,  # Complex command with multiple parms
        "0068": CMD_SB_INVERTER_TYPE,  # Complex command with multiple parms
        "0405": {
            # Interval: ~3-5 seconds, but only with realtime trigger
            "topic": "param_info",
            "a2": {"name": "device_sn"},
            "a3": {"name": "battery_soc"},
            "a4": {"name": "405_unknown_1?"},
            "a6": {"name": "sw_version", "values": 1},
            "a7": {"name": "sw_controller", "values": 1},
            "a8": {"name": "hw_version", "values": 1},
            "a9": {"name": "temp_unit_fahrenheit"},
            "aa": {"name": "temperature"},
            "ab": {"name": "photovoltaic_power"},
            "ac": {"name": "output_power"},
            "ad": {"name": "charging_status?"},
            "ae": {
                "bytes": {
                    "12": [{"name": "allow_export_switch", "mask": 0x04}],
                    "14": {
                        "name": "charge_priority_limit",
                        "type": DeviceHexDataTypes.ui.value,
                    },
                    "15": [{"name": "priority_discharge_switch", "mask": 0x01}],
                }
            },
            "b0": {"name": "bat_charge_power"},
            "b1": {"name": "pv_yield", "factor": 0.0001},
            "b2": {"name": "charged_energy", "factor": 0.0001},
            "b3": {"name": "output_energy", "factor": 0.0001},
            "b4": {"name": "output_cutoff_data"},
            "b5": {"name": "lowpower_input_data"},
            "b6": {"name": "input_cutoff_data"},
            "b7": {"name": "inverter_brand"},
            "b8": {"name": "inverter_model"},
            "b9": {"name": "min_load"},
            "fe": {"name": "msg_timestamp"},
        },
        # Interval: varies, probably upon change
        "0407": A17C0_0407,
        "0408": {
            # Interval: ~60 seconds
            "topic": "state_info",
            "a2": {"name": "device_sn"},
            "a3": {"name": "local_timestamp"},
            "a4": {"name": "utc_timestamp"},
            "a5": {"name": "battery_soc_calc", "factor": 0.001},
            "a6": {"name": "battery_soh", "factor": 0.001},
            "a8": {"name": "charging_status"},
            "a9": {"name": "home_load_preset"},
            "aa": {"name": "photovoltaic_power"},
            "ab": {"name": "bat_charge_power"},
            "ac": {"name": "output_power"},
            "ad": {"name": "408_unknown_1?"},
            "ae": {"name": "408_unknown_2?"},
            "af": {"name": "408_unknown_3?"},
            "b0": {"name": "battery_soc"},
            "b1": {"name": "pv_yield", "factor": 0.0001},
            "b2": {"name": "charged_energy", "factor": 0.0001},
            "b3": {"name": "output_energy", "factor": 0.0001},
            "b4": {"name": "discharged_energy", "factor": 0.0001},
            "b5": {"name": "bypass_energy", "factor": 0.0001},
            "b6": {"name": "temperature"},
            "b7": {"name": "pv_1_voltage", "factor": 0.01},
            "b8": {"name": "pv_2_voltage", "factor": 0.01},
            "b9": {"name": "battery_voltage", "factor": 0.01},
        },
    },
    # Solarbank 2 E1600 Pro
    "A17C1": {
        "0057": CMD_REALTIME_TRIGGER,
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": A17C1_0405,
        # Interval: varies, probably upon change
        "0407": A17C0_0407,
        # Interval: ~300 seconds
        "0408": A17C1_0408,
        # Expansion data
        # Interval: ~3-5 seconds, but only with realtime trigger
        "040a": A17C1_040a,
    },
    # Solarbank 2 E1600 AC
    "A17C2": {
        "0057": CMD_REALTIME_TRIGGER,
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": A17C5_0405,
        # Interval: varies, probably upon change
        "0407": A17C0_0407,
        # Interval: ~300 seconds
        "0408": A17C5_0408,
        # Expansion data
        # Interval: ~3-5 seconds, but only with realtime trigger
        "040a": A17C5_040a,
    },
    # Solarbank 2 E1600 Plus
    "A17C3": {
        "0057": CMD_REALTIME_TRIGGER,
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": A17C1_0405,
        # Interval: varies, probably upon change
        "0407": A17C0_0407,
        # Interval: ~300 seconds
        "0408": A17C1_0408,
        # Expansion data
        # Interval: ~3-5 seconds, but only with realtime trigger
        "040a": A17C1_040a,
    },
    # Solarbank 3 E2700 Pro
    "A17C5": {
        "0057": CMD_REALTIME_TRIGGER,
        # Interval: ~3-5 seconds, but only with realtime trigger
        "0405": A17C5_0405,
        # Interval: varies, probably upon change
        "0407": A17C0_0407,
        # Interval: ~300 seconds
        "0408": A17C5_0408,
        # Expansion data
        # Interval: ~3-5 seconds, but only with realtime trigger
        "040a": A17C5_040a,
        # multisystem messages
        # Interval: ~3-10 seconds, but only with realtime trigger
        "0420": DOCK_0420,
        # Interval: ~300 seconds
        "0421": DOCK_0421,
        # Interval: ~300 seconds
        "0428": DOCK_0428,
        # Interval: ~300 seconds
        "0500": DOCK_0500,
    },
    # Anker Solarbank Smartmeter
    "A17X7": {
        "0057": CMD_REALTIME_TRIGGER,
        "0405": {
            # Interval: ~5 seconds, but only with realtime trigger
            "topic": "param_info",
            "a2": {"name": "device_sn"},
            "a6": {"name": "sw_version", "values": 4},
            "a7": {"name": "sw_controller", "values": 4},
            "a8": {"name": "grid_to_home_power"},
            "a9": {"name": "pv_to_grid_power"},
            "aa": {"name": "grid_import_energy", "factor": 0.01},
            "ab": {"name": "grid_export_energy", "factor": 0.01},
            # "ad": {"name": "pv_to_grid_power"},
        },
    },
    # Shello Pro 3 EM
    "SHEMP3": {
        "0057": CMD_REALTIME_TRIGGER,
        "0405": {
            # Interval: ~5 seconds, but only with realtime trigger
            "topic": "param_info",
            "a2": {"name": "device_sn"},
            "a8": {"name": "grid_to_home_power", "factor": 0.01},
            "a9": {"name": "pv_to_grid_power", "factor": 0.01},
            "aa": {"name": "grid_import_energy", "factor": 0.00001},
            "ab": {"name": "grid_export_energy", "factor": 0.00001},
            "fe": {"name": "msg_timestamp"},
        },
    },
    # Anker Power Dock
    "AE100": {
        "0057": CMD_REALTIME_TRIGGER,
        "0405": {
            # Interval: ~5 seconds, but only with realtime trigger
            "topic": "param_info",
            "a2": {"name": "device_sn"},
            "a3": {"name": "sw_version", "values": 4},
            "a5": {"name": "ac_output_power_total"},
            "a6": {"name": "battery_power_signed_total"},
            "b3": {"name": "local_timestamp"},
            "b6": {
                "bytes": {
                    "00": {
                        "name": "solarbank_1_sn",
                        "length": 0,  # First byte is byte count for type
                        "type": DeviceHexDataTypes.str.value,
                    },
                    "19": {
                        "name": "solarbank_1_soc",
                        "type": DeviceHexDataTypes.ui.value,
                    },
                }
            },
            "b7": {"name": "solarbank_1_battery_power_signed"},
            "b8": {
                "bytes": {
                    "00": {
                        "name": "solarbank_2_sn",
                        "length": 0,  # First byte is byte count for type
                        "type": DeviceHexDataTypes.str.value,
                        "19": {
                            "name": "solarbank_2_soc",
                            "type": DeviceHexDataTypes.ui.value,
                        },
                    },
                }
            },
            "b9": {"name": "solarbank_2_battery_power_signed"},
            "ba": {
                "bytes": {
                    "00": {
                        "name": "solarbank_3_sn",
                        "length": 0,  # First byte is byte count for type
                        "type": DeviceHexDataTypes.str.value,
                        "19": {
                            "name": "solarbank_3_soc",
                            "type": DeviceHexDataTypes.ui.value,
                        },
                    },
                }
            },
            "bb": {"name": "solarbank_3_battery_power_signed"},
            "bc": {
                "bytes": {
                    "00": {
                        "name": "solarbank_4_sn",
                        "length": 0,  # First byte is byte count for type
                        "type": DeviceHexDataTypes.str.value,
                    },
                    "19": {
                        "name": "solarbank_4_soc",
                        "type": DeviceHexDataTypes.ui.value,
                    },
                }
            },
            "bd": {"name": "solarbank_4_battery_power_signed"},
        },
        "0407": {
            # Interval: ~300 seconds
            # Network message
            "topic": "param_info",
            "a2": {"name": "device_sn"},
            "a3": {"name": "wifi_name"},
            "a4": {"name": "wifi_signal"},
        },
        # multisystem messages
        # Interval: ~3-10 seconds, but only with realtime trigger
        "0420": DOCK_0420,
        # Interval: ~300 seconds
        "0421": DOCK_0421,
        # Interval: ~300 seconds
        "0428": DOCK_0428,
        # Interval: ~300 seconds
        "0500": DOCK_0500,
    },
}
