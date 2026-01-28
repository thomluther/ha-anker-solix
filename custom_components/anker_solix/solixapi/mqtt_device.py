"""MQTT basic device control methods for AnkerSolixApi.

This module contains common control methods for Anker Solix MQTT device classes.
Specific device classes should be inherited from this base class
It also provides an MQTT device factory to create correct device class instance depending on specific device
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

from .apitypes import SolixDefaults
from .helpers import round_by_factor
from .mqtt import generate_mqtt_command
from .mqttcmdmap import (
    COMMAND_LIST,
    COMMAND_NAME,
    NAME,
    STATE_CONVERTER,
    STATE_NAME,
    VALUE_DEFAULT,
    VALUE_FOLLOWS,
    VALUE_MAX,
    VALUE_MIN,
    VALUE_OPTIONS,
    VALUE_STATE,
    VALUE_STEP,
    SolixMqttCommands,
)
from .mqttmap import SOLIXMQTTMAP
from .mqtttypes import MqttCmdValidator

if TYPE_CHECKING:
    from .api import AnkerSolixApi

# Define supported Models for this class
MODELS = set()
# Define possible controls per Model
# Those commands are only supported once also described for a message type in the model mapping (except realtime trigger)
# Models can be removed from a feature to block command usage even if message type is described in the mapping
FEATURES = {
    SolixMqttCommands.realtime_trigger: MODELS,
}


class SolixMqttDevice:
    """Define the base class to handle an Anker Solix MQTT device for controls."""

    models: set = MODELS
    features: dict = FEATURES
    pn: str = ""

    def __init__(self, api_instance: AnkerSolixApi, device_sn: str) -> None:
        """Initialize."""
        self.api: AnkerSolixApi = api_instance
        self.sn: str = device_sn or ""
        self.pn: str = self.pn or ""
        self.models = self.models or MODELS
        self.features = self.features or FEATURES
        self.testdir: str = self.api.testDir()
        self.device: dict = {}
        self.mqttdata: dict = {}
        self.controls: dict = {}
        self._map: dict = {}
        self._filedata: dict = {}
        self._logger = api_instance.logger()
        # initialize device data
        self.update_device(device=self.api.devices.get(self.sn) or {})
        # register callback for Api
        self.api.register_device_callback(deviceSn=self.sn, func=self.update_device)
        # create list of supported commands and options
        self._setup_controls()

    def _setup_controls(self) -> None:
        """Extract controls, parameters and value options for the device from the mapping description.

        Example control structure:
            "realtime_trigger": {"msg_type": "0057","topic": "req","command_name": "realtime_trigger","parameters": {
                "set_realtime_trigger": {"value_options": {"off": 0,"on": 1}},
                "trigger_timeout_sec": {"value_min": 60,"value_max": 600}}}
        """
        self._map = SOLIXMQTTMAP.get(self.pn) or {}
        for cmd, pns in self.features.items():
            if not pns or self.pn in pns:
                # get defined message type for command
                msg, fields = (
                    [
                        (k, v)
                        for k, v in self._map.items()
                        if cmd
                        in [
                            v.get(COMMAND_NAME),
                            *v.get(COMMAND_LIST, []),
                        ]
                    ][:1]
                    or [("", {})]
                )[0]
                # use default message type for update trigger command if not specified
                msg = msg or (
                    "0057" if cmd == SolixMqttCommands.realtime_trigger else ""
                )
                # control only if described for a message type in the mapping
                if msg:
                    try:
                        control = {"msg_type": msg}
                        # traverse all fields, use field descriptive name as parameter name and field byte as
                        parameters = {}
                        required_options = []
                        required_number = None
                        # get nested command fields if available
                        fields = fields.get(cmd) or fields
                        for key, item in fields.items():
                            if len(key) > 2:
                                # No bytefield key, use as is
                                control[key] = item
                            elif isinstance(item, dict):
                                # extract all bytefield descriptions as parameter which have defined value keys
                                descriptors = {
                                    k: v
                                    for k, v in item.items()
                                    if k
                                    in [
                                        VALUE_MIN,
                                        VALUE_MAX,
                                        VALUE_STEP,
                                        VALUE_STATE,
                                        VALUE_OPTIONS,
                                        VALUE_DEFAULT,
                                        STATE_CONVERTER,
                                        STATE_NAME,
                                        VALUE_FOLLOWS,
                                    ]
                                }
                                # check if valid parameter for command
                                if (name := item.get(NAME)) and descriptors:
                                    # check if validator can be initialized, will throw ValueError or TypeError
                                    if (
                                        VALUE_STATE not in descriptors
                                        and VALUE_DEFAULT not in descriptors
                                        and VALUE_FOLLOWS not in descriptors
                                    ):
                                        # This is a required parameter
                                        MqttCmdValidator(
                                            min=descriptors.get(VALUE_MIN),
                                            max=descriptors.get(VALUE_MAX),
                                            step=descriptors.get(VALUE_STEP),
                                            options=descriptors.get(VALUE_OPTIONS),
                                        )
                                        required_options.append(
                                            descriptors.get(VALUE_OPTIONS)
                                        )
                                        if required_number is None:
                                            required_number = descriptors.get(
                                                VALUE_MIN, 0
                                            ) < descriptors.get(VALUE_MAX, 0)
                                        else:
                                            required_number = False
                                    # flag whether parameter is switch
                                    descriptors["is_switch"] = bool(
                                        isinstance(
                                            opt := descriptors.get(VALUE_OPTIONS), dict
                                        )
                                        and len(opt) == 2
                                        and "on" in opt
                                        and "off" in opt
                                    )
                                    # flag whether parameter is number
                                    descriptors["is_number"] = bool(
                                        descriptors.get(VALUE_MIN, 0)
                                        < descriptors.get(VALUE_MAX, 0)
                                    )
                                    # add descriptors
                                    parameters[name] = descriptors
                        control["parameters"] = parameters
                        # check if control is a switch with only "on" and "off" in single required option
                        control["is_switch"] = bool(
                            len(required_options) == 1
                            and isinstance(opt := required_options[0], dict)
                            and len(opt) == 2
                            and "on" in opt
                            and "off" in opt
                        )
                        # check if control is a single number control
                        control["is_number"] = bool(required_number)
                        self.controls[cmd] = control
                    except (ValueError, TypeError):
                        self._logger.error(
                            "MQTT device %s (%s) control setup error - Command '%s' has invalid description for parameter '%s': %s",
                            self.sn,
                            self.pn,
                            cmd or "",
                            name or "",
                            str(descriptors or {}),
                        )

    def update_device(self, device: dict) -> None:
        """Define callback for Api device updates."""
        if isinstance(device, dict) and device.get("device_sn") == self.sn:
            # Validate device type or accept any if not defined
            if (pn := device.get("device_pn")) in self.models or not self.models:
                self.pn = pn
                self.device = device
                self.mqttdata = device.get("mqtt_data", {})
            else:
                self._logger.error(
                    "Device %s (%s) is not in supported models %s for MQTT control",
                    self.sn,
                    self.pn,
                    self.models,
                )
                self.pn = ""
                self.device = {}
                self.mqttdata = {}

    def is_connected(self) -> bool:
        """Return actual MQTT connection state for device."""
        return bool(self.api.mqttsession and self.api.mqttsession.is_connected())

    def is_subscribed(self) -> bool:
        """Return actual MQTT subscription state for device."""
        return bool(
            self.is_connected()
            and {s for s in self.api.mqttsession.subscriptions if self.sn in s}
        )

    def get_cmd_parms(
        self,
        cmd: str,
        defaults: bool = False,
        state_parms: bool = False,
        follow_parms: bool = False,
        all: bool = False,
    ) -> dict:
        """Get dictionary with parameters and value descriptions for provided command.

        If defaults is True, also normal parameters with a default value will be included.
        If state_parms is True, only parameters that reuse existing state will be provided.
        If follow_parms is True, only parameters that follow another parm will be provided, otherwise those are excluded
        If all is True, all parameters will be included
        """
        if isinstance(cmd, str):
            return {
                p: desc
                for p, desc in self.controls.get(cmd, {}).get("parameters", {}).items()
                if all
                or (
                    not (state_parms or follow_parms)
                    and (VALUE_DEFAULT not in desc or defaults)
                    and VALUE_STATE not in desc
                    and VALUE_FOLLOWS not in desc
                )
                or (state_parms and VALUE_STATE in desc)
                or (follow_parms and VALUE_FOLLOWS in desc)
            }
        return {}

    def get_cmd_parm_option_map(
        self, cmd: str, parm: str | None = None, limit: int = 100
    ) -> dict:
        """Get dictionary with options mapping for first mandatory or the provided parameter. Option list or value range will be converted into dict if limit not exceeded."""
        if isinstance(cmd, str):
            # first get parameter description
            if isinstance(parm, str):
                desc = self.get_cmd_parms(cmd=cmd, all=True).get(parm, {})
            else:
                desc = next(iter(self.get_cmd_parms(cmd=cmd).values()), {})
            if not (options := desc.get(VALUE_OPTIONS, {})):
                # create value range if less than 100 options
                start = desc.get(VALUE_MIN, 0)
                stop = desc.get(VALUE_MAX, 0)
                step = desc.get(VALUE_STEP, 1)
                if (
                    start < stop
                    and len(rng := range(start, stop + step, step)) <= limit
                ):
                    options = rng
            if isinstance(options, dict):
                return options
            if isinstance(options, list | range):
                return {str(item): item for item in options}
        return {}

    def get_cmd_parm_state_option(
        self,
        cmd: str,
        parm: str | None = None,
        fromFile: bool = False,
    ) -> dict:
        """Get dictionary with command parameter state name and value converted into option string."""
        if isinstance(cmd, str):
            # first get parameter description
            if isinstance(parm, str):
                desc = self.get_cmd_parms(cmd=cmd, all=True).get(parm, {})
            else:
                desc = next(iter(self.get_cmd_parms(cmd=cmd).values()), {})
            if (
                (options := desc.get(VALUE_OPTIONS, {}))
                and isinstance(options, dict)
                and (state_name := desc.get(STATE_NAME))
                and (value := self.get_status(fromFile).get(state_name)) is not None
            ):
                # convert state to command option value
                if callable(converter := desc.get(STATE_CONVERTER)):
                    value = converter(None, value)
                return {
                    state_name: next(
                        iter(k for k, v in options.items() if v == value), value
                    )
                }
        return {}

    def cmd_is_switch(self, cmd: str, parm: str | None = None) -> bool:
        """Check whether the command is a single switch control. If parm is specified, it will check the given parameter."""
        if isinstance(cmd, str):
            if isinstance(parm, str):
                # use parameter flag
                return bool(
                    self.get_cmd_parms(cmd=cmd, all=True).get(parm, {}).get("is_switch")
                )
            # use control flag
            return bool(self.controls.get(cmd, {}).get("is_switch"))
        return False

    def cmd_is_number(self, cmd: str, parm: str | None = None) -> bool:
        """Check whether the command is a single number control. If parm is specified, it will check the given parameter."""
        if isinstance(cmd, str):
            if isinstance(parm, str):
                # use parameter flag
                return bool(
                    self.get_cmd_parms(cmd=cmd, all=True).get(parm, {}).get("is_number")
                )
            # use control flag
            return bool(self.controls.get(cmd, {}).get("is_number"))
        return False

    def validate_cmd_value(
        self, cmd: str, value: Any, parm: str | None = None
    ) -> int | float | str | bool | None:
        """Get validated command value for device control or None if anything invalid.

        parm is required if the command may have more than one parameter without default value.
        True is returned if command is valid but does not require parameter or value
        """
        if not (isinstance(cmd, str) and cmd in self.controls):
            self._logger.error(
                "MQTT device %s (%s) control error - Command not supported: '%s'",
                self.sn,
                self.pn,
                cmd,
            )
            return None
        # get all normal command parameters with or without default depending on provided value
        parms = self.get_cmd_parms(cmd=cmd, defaults=value is None)
        if not parm:
            if len(parms) > 1 or (not parms and value is not None):
                s = "'" if isinstance(value, str) else ""
                self._logger.error(
                    "MQTT device %s (%s) control error - Parameter required %s to validate command '%s' value: %s",
                    self.sn,
                    self.pn,
                    list(parms.keys()),
                    cmd,
                    s + str(value) + s,
                )
                return None
            parm, desc = next(iter(parms.items()), (None, {}))
        elif not (
            isinstance(parm, str)
            and (desc := self.get_cmd_parms(cmd=cmd, all=True).get(parm))
        ):
            self._logger.error(
                "MQTT device %s (%s) control error - Command '%s' parameter '%s' is no supported parameter: %s",
                self.sn,
                self.pn,
                cmd,
                parm,
                list(parms.keys()),
            )
            return None
        # use default if value not provided
        value = desc.get(VALUE_DEFAULT) if value is None else value
        # lookup state if default is string
        if (
            isinstance(value, str)
            and str(val := self.get_status(fromFile=True).get(value))
            .replace("-", "", 1)
            .replace(".", "", 1)
            .isdigit()
        ):
            value = float(val)
        if value is None:
            if desc:
                self._logger.error(
                    "MQTT device %s (%s) control error - Command '%s' parameter '%s' value is invalid: %s",
                    self.sn,
                    self.pn,
                    cmd,
                    parm,
                    value,
                )
                return None
            # Valid command which does not require parameter or value, return True to indicate it is valid
            return True
        try:
            # return validated parameter value or option
            return (
                MqttCmdValidator(
                    min=desc.get(VALUE_MIN),
                    max=desc.get(VALUE_MAX),
                    step=desc.get(VALUE_STEP),
                    options=desc.get(VALUE_OPTIONS),
                ).check(value)
                if value != desc.get(VALUE_DEFAULT)
                else value
            )
        except (ValueError, TypeError) as err:
            self._logger.error(
                "MQTT device %s (%s) control error - Command '%s' parameter '%s' value error: %s",
                self.sn,
                self.pn,
                cmd,
                parm,
                err,
            )
            return None

    async def _send_mqtt_command(
        self,
        command: str,
        parameters: dict | None = None,
        description: str = "",
        toFile: bool = False,
    ) -> str | None:
        """Send MQTT command to device.

        Args:
            self: The API instance
            command: Command name for get_command_data
            parameters: Command parameters
            description: Human-readable description for logging
            toFile: If True, skip publish and print decoded command (for testing compatibility)

        Returns:
            str | None: String with hex command if sent, None otherwise

        """
        # Generate command hex data
        if not (hexdata := generate_mqtt_command(command, parameters, self.pn)):
            self._logger.error(
                "MQTT device %s (%s) failed to generate hex data for command %s",
                self.sn,
                self.pn,
                command,
            )
            return None
        if toFile:
            # print the decoded command
            self._logger.info(
                "TESTMODE: MQTT device %s (%s) generated command: %s\n%s",
                self.sn,
                self.pn,
                description,
                hexdata.decode(),
            )
        else:
            try:
                # Ensure MQTT session is started and connected
                if not self.is_connected():
                    if not await self.api.startMqttSession():
                        self._logger.error(
                            "Failed to start MQTT session for device control"
                        )
                        return None
                # Publish MQTT command
                _, mqtt_info = self.api.mqttsession.publish(self.device, hexdata.hex())
                # Wait for publish completion with timeout
                with contextlib.suppress(ValueError, RuntimeError):
                    mqtt_info.wait_for_publish(timeout=5)
                if not mqtt_info.is_published():
                    self._logger.error(
                        "MQTT device %s (%s) failed to publish command: %s",
                        self.sn,
                        self.pn,
                        description,
                    )
                    return None
            except (ValueError, RuntimeError) as err:
                self._logger.error(
                    "MQTT device %s (%s) got error while sending command: %s\n%s",
                    self.sn,
                    self.pn,
                    description,
                    err,
                )
                return None
        self._logger.info("MQTT device %s (%s) %s", self.sn, self.pn, description)
        return hexdata.hex()

    async def run_command(
        self,
        cmd: str,
        value: Any = None,
        parm: str | None = None,
        parm_map: dict | None = None,
        toFile: bool = False,
    ) -> dict | None:
        """Validate and send a supported device command that requires a single parameter value at most.

        Args:
            cmd: A supported device command name
            value: Optional value for a parameter that is supported by the command
            parm: Optional Parameter for the value if command parameter description is ambiguous
            parm_map: Optional dictionary with parameter value mapping for multiple parameter commands
            toFile: If True, skip publish and print decoded command (for testing compatibility)

        Returns:
            dict: Dictionary with mock status if message was published, None otherwise

        Example:
            await mydevice.run_command(cmd=realtime_trigger, value=300, parm="trigger_timeout_sec")

        """
        resp = None
        if not isinstance(parm_map, dict):
            parm_map = {}
        # Validate command values
        if cmd:
            # merge individual parameters into parameter mapping
            if parm:
                parm_map[parm] = value
            elif not parm_map:
                parm_map[""] = value
            # get required parameters without defaults
            cmd_parms = self.get_cmd_parms(cmd=cmd)
            req_parms = set(cmd_parms.keys())
            parameters = {}
            state_fields = {}
            user_parms = {}
            for par, val in parm_map.items():
                if (
                    fieldvalue := self.validate_cmd_value(
                        cmd=cmd, value=val, parm=par or None
                    )
                ) is None and ((cmd_parms or par or val is not None) or val is None):
                    # Something is missing or invalid, error message was printed by validate method
                    return None
                # build parameter mapping for command with mock states and user description
                if par:
                    desc = self.get_cmd_parms(cmd=cmd, all=True).get(par, {})
                else:
                    # NOTE: At this point there can be max one required parameter, get the first one without defaults
                    par, desc = next(iter(cmd_parms.items()), (None, {}))
                # save fieldvalues and descriptions if parameter and value is valid for command
                if par:
                    # Validated Command parameters
                    parameters[par] = fieldvalue
                    # Mock state
                    if state_name := desc.get(STATE_NAME):
                        converter = desc.get(STATE_CONVERTER)
                        state_fields[state_name] = (
                            converter(fieldvalue, None)
                            if callable(converter)
                            else fieldvalue
                        )
                    # generate generic user description and provided string value or field value
                    user_parms[par] = val if isinstance(val, str) else fieldvalue
                    # mark required parameter as defined
                    req_parms.discard(par)
            # add command parameters that may need current state value or follow another parameter
            for par, desc in self.get_cmd_parms(
                cmd=cmd, state_parms=True, follow_parms=True
            ).items():
                if (step := desc.get(VALUE_STEP)) is None:
                    step = 1
                if follows := desc.get(VALUE_FOLLOWS):
                    # get only mock state for follow parameter if they have a state, command generator will lookup value from other parameter
                    if (
                        (state_name := desc.get(STATE_NAME))
                        and isinstance(options := desc.get(VALUE_OPTIONS), dict)
                        and (state := options.get(parameters.get(follows, "")))
                        is not None
                    ):
                        converter = desc.get(STATE_CONVERTER)
                        state_fields[state_name] = (
                            converter(state, None) if callable(converter) else state
                        )
                elif (
                    par not in parameters
                    and (
                        state := self.get_status(fromFile=True).get(
                            desc.get(VALUE_STATE, ""), desc.get(VALUE_DEFAULT)
                        )
                    )
                    is not None
                ):
                    # convert state to number format if valid number
                    if str(state).replace("-", "", 1).replace(".", "", 1).isdigit():
                        parameters[par] = round_by_factor(float(state), step)
                    else:
                        parameters[par] = state
                    # Mock state
                    if state_name := desc.get(STATE_NAME):
                        converter = desc.get(STATE_CONVERTER)
                        state_fields[state_name] = (
                            converter(parameters[par], None)
                            if callable(converter)
                            else parameters[par]
                        )
                    # mark required parameter as defined
                    req_parms.discard(par)
            # check if all required parameters are specified
            if req_parms:
                self._logger.error(
                    "MQTT device %s (%s) control error - Command '%s' is missing required parameter(s): %s",
                    self.sn,
                    self.pn,
                    cmd,
                    list(req_parms),
                )
                return None
            if not user_parms and value is not None:
                user_parms = f"'{value}'" if isinstance(value, str) else value
            # publish command with validated field values
            if await self._send_mqtt_command(
                command=cmd,
                parameters=parameters,
                description=f"sent command '{cmd}'{': ' if user_parms else ''}{user_parms}",
                toFile=toFile,
            ):
                resp = state_fields
                # add mock states for fields with depending values

                if toFile:
                    self._filedata.update(resp)
        return resp

    async def realtime_trigger(
        self,
        timeout: int = SolixDefaults.TRIGGER_TIMEOUT_DEF,
        state: bool | None = None,
        toFile: bool = False,
    ) -> dict | None:
        """Trigger device realtime data publish.

        Args:
            timeout: Seconds for realtime publish to stop
            state: Set the state of the trigger, default will be on
            toFile: If True, save mock response (for testing compatibility)

        Returns:
            dict: dict with mocked state response, None otherwise

        Example:
            await mydevice.realtime_trigger(timeout=300)

        """
        # Validate parameters and publish command
        return await self.run_command(
            cmd=SolixMqttCommands.realtime_trigger,
            value=timeout,
            parm="trigger_timeout_sec",
            parm_map={}
            if state is None
            else {"set_realtime_trigger": "on" if state else "off"},
            toFile=toFile,
        )

    async def status_request(
        self,
        toFile: bool = False,
    ) -> dict | None:
        """Send device status_request.

        Args:
            toFile: If True, save mock response (for testing compatibility)

        Returns:
            dict: dict with mocked state response, None otherwise

        Example:
            await mydevice.status_request()

        """
        # Do not check whether status request fully supported for command, it will be sent with standard message type otherwise
        if await self._send_mqtt_command(
            command=SolixMqttCommands.status_request,
            description="sent status request",
            toFile=toFile,
        ):
            return {}
        return None

    def get_combined_cache(
        self,
        mqtt_unique: bool = False,
        api_prio: bool = False,
        fromFile: bool = False,
    ) -> dict:
        """Get copy of combined values from device actual Api and MQTT cache.

        Args:
            mqtt_unique: If True, provide only MQTT values not included in Api cache
            api_prio: If True, duplicate values will have the Api cache value, default is MQTT cache value
            fromFile: If True, include mock MQTT cache while testing from files

        Returns:
            dict: Combined Api and MQTT data cache

        Example:
            mqtt_unique = mydevice.get_combined_cache(mqtt_unique=True)

        """
        mqttdata = self.mqttdata | (self._filedata if fromFile else {})
        if mqtt_unique:
            # find duplicate keys and remove them from MQTT cache copy
            dup = set(self.device.keys()) & (set(mqttdata.keys()))
            for k in dup:
                mqttdata.pop(k, None)
            return mqttdata
        if api_prio:
            data = mqttdata | self.device
        else:
            data = self.device | mqttdata
        return data

    def get_status(
        self,
        fromFile: bool = False,
    ) -> dict:
        """Get actual MQTT device cache status.

        Args:
            fromFile: If True, include mock status while testing from files

        Returns:
            dict: Device status with all extracted MQTT message fields from
                Uses MQTT data cache for real-time values

        Example:
            status = mydevice.get_status()
            print(f"AC Output: {status.get('switch_ac_output_power')}")
            print(f"Battery SOC: {status.get('battery_soc')}%")

        """
        # Return copy of accumulated MQTT data cache, handle test mode
        return self.mqttdata | (self._filedata if fromFile else {})

    def print_status(
        self,
        fromFile: bool = False,
    ) -> dict:
        """Print and return actual MQTT device status.

        Args:
            fromFile: If True, include mock status while testing from files

        Returns:
            dict: Device status with all extracted MQTT message fields from
                Uses MQTT data cache for real-time values

        Example:
            mydevice.print_status()

        """
        # Return accumulated MQTT data cache, handle test mode
        data = self.get_status(fromFile=fromFile)
        self._logger.info(
            "MQTT device %s (%s) status%s:\n%s",
            self.sn,
            self.pn,
            " with optional MQTT test control changes" if fromFile else "",
            str(data),
        )
        return data
