"""Default definitions required for the Anker MQTT Cloud API."""

from dataclasses import InitVar, asdict, dataclass, field
from datetime import datetime
import struct
from typing import Any

from .apitypes import Color, SolixDeviceCategory
from .mqttmap import SOLIXMQTTMAP, DeviceHexDataTypes


@dataclass(order=True, kw_only=True)
class DeviceHexDataHeader:
    """Dataclass to structure Solix device hex data headers as received from MQTT or BT transmissions.

    Message header structure (9-10 Bytes):
    FF 09    | 2 Bytes fixed message prefix for Anker Solix message
    XX XX    | 2 Bytes message length (including prefix), little endian format
    XX XX XX | 3 Bytes pattern that seem identical across all messages (supposed `03 00/01 0f` for send/receive)
    XX XX    | 2 Bytes pattern for type of message, e.g. `84 05` on telemetry packets and `04 09` for others, depends on device model, to be figured out
    XX       | 1 optional Byte, seems increment for certain messages, fix for others or not used
    e.g. ff09 3b00 03010f 0407 xx ..data..
    """

    prefix: bytearray = b""
    msglength: int = 0
    pattern: bytearray = b""
    msgtype: bytearray = b""
    increment: bytearray = b""
    hexbytes: InitVar[bytearray | bytes | str | None] = None
    cmd_msg: InitVar[bytearray | bytes | str | None] = None

    def __post_init__(self, hexbytes, cmd_msg) -> None:
        """Init the dataclass from optional hexbytes or for new cmf_msg."""
        self.msglength = 0
        if isinstance(hexbytes, str):
            hexbytes = bytearray(bytes.fromhex(hexbytes))
        elif isinstance(hexbytes, bytes):
            hexbytes = bytearray(hexbytes)
        if isinstance(cmd_msg, str):
            cmd_msg = bytearray(bytes.fromhex(cmd_msg))
        elif isinstance(cmd_msg, bytes):
            cmd_msg = bytearray(cmd_msg)
        if isinstance(hexbytes, bytearray):
            if len(hexbytes) >= 9:
                self.prefix = hexbytes[0:2]
                self.msglength = int.from_bytes(hexbytes[2:4], byteorder="little")
                self.pattern = hexbytes[4:7]
                self.msgtype = hexbytes[7:9]
            if len(hexbytes) >= 10 and hexbytes[9:10] != bytearray.fromhex("a1"):
                self.increment = hexbytes[9:10]
            else:
                self.increment = b""
        elif isinstance(cmd_msg, bytearray):
            # Initialize for publish command with given message pattern
            self.prefix = bytearray(bytes.fromhex("ff09"))
            self.pattern = bytearray(bytes.fromhex("03000f"))
            self.msgtype = cmd_msg[0:2]
            self.increment = cmd_msg[2:3]
            self.msglength = len(self) + 2

    def __len__(self) -> int:
        """Return Bytes used for header."""
        return (
            len(self.prefix)
            + len(self.pattern)
            + len(self.msgtype)
            + len(self.increment)
            + 2 * (self.msglength > 0)
        )

    def __str__(self) -> str:
        """Print the class fields."""
        return f"prefix:{self.prefix.hex()}, msglength:{self.msglength!s}, pattern:{self.pattern.hex()}, msgtype:{self.msgtype.hex()}, increment:{self.increment.hex()}"

    def hex(self, sep: str = "") -> str:
        """Get the header as hex string."""
        b = (
            self.prefix
            + self.msglength.to_bytes(2, byteorder="little")
            + self.pattern
            + self.msgtype
            + self.increment
        )
        if sep:
            return f"{b.hex(sep=sep)}"
        return f"{b.hex()}"

    def decode(self) -> str:
        """Print the header fields representation in human readable format."""
        if len(self) > 0:
            s = f"{self.prefix.hex(' '):<8}: 2 Byte Anker Solix message marker (supposed 'ff 09')"
            s += f"\n{Color.YELLOW}{int.to_bytes(self.msglength, length=2, byteorder='little').hex(' '):<8}{Color.OFF}:"
            s += f" 2 Byte total message length ({Color.YELLOW}{self.msglength!s}{Color.OFF}) in Bytes (Little Endian format)"
            s += f"\n{self.pattern.hex(' '):<8}: 3 Byte fixed message pattern (supposed `03 00/01 0f` for send/receive)"
            s += f"\n{Color.GREEN}{self.msgtype.hex(' ')!s:<8}{Color.OFF}: 2 Byte message type pattern (varies per device model and message type)"
            s += f"\n{self.increment.hex(' '):<8}: 1 Byte optional message increment ({int.from_bytes(self.increment):>3})"
        else:
            s = ""
        return s

    def asdict(self) -> dict:
        """Return a dictionary representation of the class fields."""
        return asdict(self)


@dataclass(order=True, kw_only=True)
class DeviceHexDataField:
    """Dataclass to structure Solix device hex data field as received from MQTT or BT transmissions.

    Common data field structure:
    XX     | 1 Byte data field name (A1, A2, A3 ...), naming can be different per device model and message type
    XX     | 1 Byte data length (bytes following until end of field)
    XX ... | 1-xx Bytes data, where first Byte in data indicates the value type of the data (if data length is > 2)
    """

    f_name: bytearray = field(default_factory=bytearray)
    f_length: int = 0
    f_type: bytearray = field(default_factory=bytearray)
    f_value: bytearray = field(default_factory=bytearray)
    hexbytes: InitVar[bytearray | bytes | str | None] = None

    def __post_init__(self, hexbytes) -> None:
        """Init the dataclass from an optional hexbytes."""
        if isinstance(hexbytes, str):
            hexbytes = bytearray(bytes.fromhex(hexbytes))
        elif isinstance(hexbytes, bytes):
            hexbytes = bytearray(hexbytes)
        if isinstance(hexbytes, bytearray) and len(hexbytes) >= 2:
            self.f_name = hexbytes[0:1]
            self.f_length = int.from_bytes(hexbytes[1:2])
            if 0 < self.f_length <= len(hexbytes) - 2:
                if self.f_length > 1:
                    # field with value type
                    self.f_type = hexbytes[2:3]
                    self.f_value = hexbytes[3 : 2 + self.f_length]
                else:
                    # field with single byte value
                    self.f_type = bytearray()
                    self.f_value = hexbytes[2:3]
            else:
                self.f_type = bytearray()
                self.f_value = bytearray()
        else:
            # Update data length if initialized without hexbytes
            self.f_length = len(self.f_type) + len(self.f_value)

    def __len__(self) -> int:
        """Return Bytes used for field."""
        return (
            len(self.f_name)
            + len(self.f_type)
            + len(self.f_value)
            + 1 * (self.f_length > 0)
        )

    def __str__(self) -> str:
        """Print the class fields."""
        return f"f_name:{self.f_name.hex()}, f_length:{self.f_length!s}, f_type:{self.f_type.hex()}, f_value:{self.f_value.hex(':')}"

    def hex(self, sep: str = "") -> str:
        """Get the field as hex string."""
        b = self.f_name + self.f_length.to_bytes() + self.f_type + self.f_value
        if sep:
            return f"{b.hex(sep=sep)}"
        return f"{b.hex()}"

    def asdict(self) -> dict:
        """Return a dictionary representation of the class fields."""
        return asdict(self)

    def decode(self) -> str:
        """Return the data field representation in human readable format, including color highlighting."""
        if self.f_name:
            typ = (
                DeviceHexDataTypes(self.f_type).name
                if self.f_type in DeviceHexDataTypes
                else DeviceHexDataTypes.unk.name
            )
            tcol = (
                [
                    Color.BLUE,
                    Color.GREEN,
                    Color.CYAN,
                    Color.YELLOW,
                    Color.RED,
                    Color.MAG,
                    Color.BLUE,
                ][ti]
                if self.f_type and 0 <= (ti := int.from_bytes(self.f_type)) <= 6
                else Color.RED
            )

            if typ not in [
                DeviceHexDataTypes.str.name,
                DeviceHexDataTypes.bin.name,
                DeviceHexDataTypes.strb.name,
            ]:
                # unsigned int little endian
                uile = (
                    ";".join(
                        [
                            str(
                                int.from_bytes(
                                    self.f_value[0:2], byteorder="little", signed=True
                                )
                            ),
                            str(
                                int.from_bytes(
                                    self.f_value[2:4], byteorder="little", signed=True
                                )
                            ),
                        ]
                    )
                    if typ == DeviceHexDataTypes.var.name
                    else str(int.from_bytes(self.f_value, byteorder="little"))
                )
                # signed int little endian
                sile = str(
                    int.from_bytes(self.f_value, byteorder="little", signed=True)
                )
                # float little endian, convert via struct
                # '<f' little-endian 32-bit float (4 Bytes, single)
                fle = (
                    f"{struct.unpack('<f', self.f_value)[0]:>5.3f}"
                    if len(self.f_value) == 4
                    else ""
                )
                # double little endian, convert via struct
                # '<d' → little-endian 64-bit float (8 Bytes, double)
                dle = (
                    f"{struct.unpack('<d', self.f_value)[0]:>5.3f}"
                    if len(self.f_value) == 8
                    else ";".join(
                        [
                            str(int.from_bytes(self.f_value[i : i + 1]))
                            for i in range(len(self.f_value))
                        ]
                    )
                    if 2 <= len(self.f_value) <= 4
                    else ""
                )
            else:
                uile = str(bytes(self.f_value))
                sile = ""
                fle = ""
                dle = ""
            s = (
                f"{Color.RED}{self.f_name.hex()!s:<4}{Color.OFF} {int.to_bytes(self.f_length).hex():<3} "
                f"{tcol}{(self.f_type.hex() or '--')!s:<4}{Color.OFF}  {self.f_value.hex(':')}\n"
                f"{'└->':<3} {self.f_length!s:>3} {tcol}{typ!s:<5}{Color.OFF} "
                f"{tcol if typ in [DeviceHexDataTypes.ui.name, DeviceHexDataTypes.str.name] else ''}{uile:>15}{Color.OFF} "
                f"{tcol if typ == DeviceHexDataTypes.sile.name else ''}{sile:>15}{Color.OFF} "
                f"{tcol if typ == DeviceHexDataTypes.sfle.name else ''}{fle:>15}{Color.OFF} {dle:>15}"
            )
        else:
            s = ""
        return s

    def values(self, fieldmap: dict) -> dict:
        """Return a dictionary with extracted values based on provided field mapping."""
        return self.extract_value(
            hexdata=self.f_value, fieldtype=self.f_type, fieldmap=fieldmap
        )

    def extract_value(
        self,
        hexdata: bytearray | bytes,
        fieldtype: bytearray | bytes,
        fieldmap: dict,
        values: dict | None = None,
    ) -> dict[str, Any]:
        """Return a dictionary with extracted values based on provided hexdata, fieldtype and mapping."""
        values = values or {}
        match fieldtype:
            case DeviceHexDataTypes.str.value:
                # various number of bytes, string (Base type), use only printable part
                values[fieldmap.get("name", "")] = "".join(
                    c
                    for c in hexdata.decode(errors="ignore").strip()
                    if c.isprintable()
                )
                # use only printable part
                bytes.fromhex(
                    "41:4e:4b:45:52:00:00:00:00:00:00:00:00:00:00:00".replace(":", "")
                ).decode()
            case DeviceHexDataTypes.ui.value:
                # 1 byte fix, unsigned int (Base type)
                values[fieldmap.get("name", "")] = int(
                    int.from_bytes(hexdata) * float(fieldmap.get("factor", 1))
                )
            case DeviceHexDataTypes.sile.value:
                # 2 bytes fix, signed int LE (Base type)
                name = fieldmap.get("name", "")
                value = int(
                    int.from_bytes(hexdata, byteorder="little", signed=True)
                    * float(fieldmap.get("factor", 1))
                )
                # check if value stands for software version and convert to version number
                if "version" in name or "sw_" in name:
                    # convert int to string for version numbering
                    value = ".".join(str(value))
                values[fieldmap.get("name", "")] = value
            case DeviceHexDataTypes.var.value:
                # var is always 4 bytes, but could be 1-4 * int, 1-2 * signed int LE or 4 Byte signed int LE
                # mapping must specify "values" to indicate number of values in bytes from beginning. Default is 0 for 1 value in 4 bytes
                # If a float factor is specified, value will be rounded to factor digits
                name = fieldmap.get("name", "")
                factor = fieldmap.get("factor", 1)
                digits = str(factor)
                digits = max(
                    0,
                    int(str(digits).split("e-")[1])
                    if "e-" in digits
                    else digits[::-1].find("."),
                )
                if (count := int(fieldmap.get("values", 0))) == 1:
                    value = round(int.from_bytes(hexdata[0:1]) * factor, digits)
                elif count == 2:
                    value = round(
                        int.from_bytes(hexdata[0:2], byteorder="little", signed=True)
                        * factor,
                        digits,
                    )
                elif count == 4:
                    value = [round(int(b) * factor, digits) for b in hexdata]
                else:
                    value = round(
                        int.from_bytes(hexdata, byteorder="little", signed=True)
                        * factor,
                        digits,
                    )
                    if isinstance(factor, int):
                        value = int(value)
                if "version" in name or "sw_" in name:
                    # convert int to string for version numbering
                    if isinstance(value, list):
                        value = ".".join(str(v) for v in value)
                    else:
                        value = ".".join(str(value))
                values[name] = value
            case DeviceHexDataTypes.bin.value:
                # bin is multiple bytes, mostly bitmap patterns for settings, but can be also String or Int bytes
                # mapping must specify start byte string ("00"-"xx") for fields and field description is a list for bitmap patters, or dict for other types
                # A single bitmap field can be used for various named settings, therefore it should be a list for differentiation
                # Each named bitmap setting must describe a "mask" integer to indicate which bit(s) are relevant for the named setting, e.g. mask 0x64 => 0100 0000
                # The masked value will be shifted so that mask LSB is rightmost bit (1), therefore value of 1 is typically on, 0 is off.
                for key, bitlist in fieldmap.get("bytes", {}).items():
                    pos = int(key)
                    if isinstance(bitlist, list):
                        for bitmap in bitlist:
                            if mask := bitmap.get("mask", 0):
                                value = self.f_value[pos]
                                # shift mask and value right until LSB of mask is one, then get bit value according to mask
                                while (mask & 1) == 0:
                                    mask >>= 1
                                    value >>= 1
                                values[bitmap.get("name", "")] = value & mask
                    else:
                        # extract found dictionary description like DeviceHexDataTypes.strb
                        self.extract_value(
                            hexdata=self.f_value[pos:],
                            fieldtype=DeviceHexDataTypes.strb.value,
                            fieldmap={key: bitlist},
                        )
            case DeviceHexDataTypes.sfle.value:
                # 4 bytes, signed float LE (Base type)
                if len(hexdata) == 4:
                    values[fieldmap.get("name", "")] = struct.unpack(
                        "<f", self.f_value
                    )[0] * float(fieldmap.get("factor", 1))
            case DeviceHexDataTypes.strb.value:
                # 06 can be many bytes, mix of Str and Byte values
                # mapping must specify start byte position string ("0"-"len-1") for fields
                # field description needs "type" with a DeviceHexDataTypes base type vor value conversion.
                # The "length" with int for byte count can be specified (default is 1 Byte),
                # where Length of 0 indicates that first byte contains variable field length
                for key, bytemap in (fieldmap.get("bytes", {}) or fieldmap).items():
                    pos = int(key)
                    if (length := bytemap.get("length", 1)) == 0:
                        # first byte is length of bytes following for field
                        length = int.from_bytes(self.f_value[pos])
                        values.update(
                            self.extract_value(
                                hexdata=self.f_value[pos + 1 : pos + length + 1],
                                fieldtype=bytemap.get(
                                    "type", DeviceHexDataTypes.unk.value
                                ),
                                fieldmap=bytemap,
                            )
                        )
                    else:
                        values.update(
                            self.extract_value(
                                hexdata=self.f_value[pos : pos + length],
                                fieldtype=bytemap.get(
                                    "type", DeviceHexDataTypes.unk.value
                                ),
                                fieldmap=bytemap,
                            )
                        )
        return values


@dataclass(order=True, kw_only=True)
class DeviceHexData:
    """Dataclass to structure Solix device hex data as received from MQTT or BT transmissions.

    Messages structure:
    Header structure (9-10 Bytes):
        FF 09    | 2 Bytes fixed message prefix for Anker Solix message
        XX XX    | 2 Bytes message length (including prefix), little endian format
        XX XX XX | 3 Bytes pattern that seem identical across all messages (supposed `03 00/01 0f` for send/receive)
        XX XX    | 2 Bytes pattern for type of message, e.g. `84 05` on telemetry packets and `04 09` for others, depends on device model, to be figured out
        XX       | 1 optional Byte, seems increment for certain messages, fix for others or not used
    Starting from 10 or 11th Byte there is message data with 1 or more fields, where each field can be of variable length.
        Common data field structure:
        XX     | 1 Byte data field name (A1, A2, A3 ...), naming can be different per device model and message type
        XX     | 1 Byte data length (bytes following until end of field)
        XX ... | 1-xx Bytes data, where first Byte in data indicates the value type of the data (if data length is > 2)
    e.g. ff09 3b00 03010f 0407 | a1 01 32 | a2 11 00 415a5636....
    """

    hexbytes: bytearray = field(default_factory=bytearray)
    model: str = ""
    length: int = 0
    msg_header: DeviceHexDataHeader = field(default_factory=DeviceHexDataHeader)
    msg_fields: dict[str, DeviceHexDataField] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Post init the dataclass to decode the bytes into fields."""
        idx = 10
        if isinstance(self.hexbytes, str):
            self.hexbytes = bytearray(bytes.fromhex(self.hexbytes.replace(":", "")))
        elif isinstance(self.hexbytes, bytes):
            self.hexbytes = bytearray(self.hexbytes)
        if self.hexbytes:
            self.length = len(self.hexbytes)
            self.msg_header = DeviceHexDataHeader(hexbytes=self.hexbytes[0:idx])
            self.msg_fields = {}
            idx = len(self.msg_header)
            while 9 <= idx < self.length - 1:
                f = DeviceHexDataField(hexbytes=self.hexbytes[idx:])
                if f.f_name:
                    self.msg_fields[f.f_name.hex()] = f
                idx += int(f.f_length) + 2
        else:
            # update length and hexbytes if not initialized via hexbytes
            self._update_hexbytes()

    def __len__(self) -> int:
        """Return Byte count of hex data."""
        return self.length

    def __str__(self) -> str:
        """Print the fields and hex bytes with separator."""
        return f"model:{self.model}, header:{{{self.msg_header!s}}}, hexbytes:{self.hexbytes.hex()}"

    def _update_hexbytes(self) -> None:
        # init length and hexbytes
        self.length = len(self.msg_header)
        self.hexbytes = bytearray()
        for f in (self.msg_fields or {}).values():
            self.length += len(f)
            self.hexbytes += bytes.fromhex(f.hex())
        if self.length:
            # update message length in header
            self.msg_header.msglength = self.length
        # generate hexbytes
        self.hexbytes = bytearray(bytes.fromhex(self.msg_header.hex()) + self.hexbytes)

    def hex(self, sep: str = "") -> str:
        """Print the hex bytes with optional separator."""
        if sep:
            return self.hexbytes.hex(sep=sep)
        return self.hexbytes.hex()

    def decode(self) -> str:
        """Return the field representation in human readable format."""
        if self.length > 0:
            msgtype = self.msg_header.msgtype.hex()
            pn = (
                f" {str(getattr(SolixDeviceCategory, self.model, 'Unknown Device')).capitalize()} "
                f"/ {Color.CYAN + self.model + Color.OFF} / {Color.GREEN + msgtype + Color.OFF} /"
                if self.model
                else ""
            )
            s = f"{pn + ' Header ':-^80}\n{self.msg_header.decode()}\n{' Fields ':-^12}|{'- Value (Hex/Decode Options)':-<67}"
            if self.msg_fields:
                s += f"\n{'Fld':<3} {'Len':<3} {'Typ':<5} {'uIntLe/var':>15} {'sIntLe':>15} {'floatLe':>15} {'dblLe/4int':>15}"
                fieldmap = (
                    (SOLIXMQTTMAP.get(self.model).get(msgtype) or {})
                    if self.model in SOLIXMQTTMAP
                    else {}
                )
                for f in self.msg_fields.values():
                    name = (
                        (fld := fieldmap.get(f.f_name.hex()) or {}).get("name")
                        or (fld.get("bytes") or {})
                        or ""
                    )
                    if (
                        f.f_length == 5
                        and isinstance(name, str)
                        and "timestamp" in str(name)
                    ):
                        name = f"{name} ({datetime.fromtimestamp(int.from_bytes(f.f_value, byteorder='little', signed=True)).strftime('%Y-%m-%d %H:%M:%S')})"
                    s += f"\n{f.decode().rstrip()}{Color.CYAN + ' --> ' + str(name) + Color.OFF if name else ''}"
                s += f"\n{80 * '-'}"
        else:
            s = ""
        return s

    def asdict(self) -> dict:
        """Return a dictionary representation of the class fields."""
        return asdict(self)

    def values(self) -> dict:
        """Return a dictionary with extracted values based on defined field mappings."""
        values = {}
        fieldmap = (SOLIXMQTTMAP.get(self.model) or {}).get(
            self.msg_header.msgtype.hex()
        ) or {}
        for key, item in fieldmap.items():
            if key in self.msg_fields:
                values.update(self.msg_fields[key].values(fieldmap=item))
        return values

    def update_field(self, datafield: DeviceHexDataField) -> None:
        """Add or update the given field if header exists and ensure correct sequence of all fields."""
        if (
            self.msg_header
            and isinstance(datafield, DeviceHexDataField)
            and datafield.f_name
        ):
            self.msg_fields = self.msg_fields or {}
            self.msg_fields.update({datafield.f_name.hex(): datafield})
            # sort fields
            fieldlist = list(self.msg_fields.keys())
            fieldlist.sort()
            new_fields = {name: self.msg_fields[name] for name in fieldlist}
            self.msg_fields = new_fields
            # update length and hexbytes
            self._update_hexbytes()

    def add_timestamp_field(self, fieldname: str | bytes = "fe") -> None:
        """Add or update a timestamp field as maybe required to publish command data."""
        if isinstance(fieldname, str):
            fieldname = bytes.fromhex(fieldname)
        datafield = DeviceHexDataField(
            f_name=fieldname,
            f_type=DeviceHexDataTypes.var.value,
            f_value=int(datetime.now().timestamp()).to_bytes(4, byteorder="little"),
        )
        self.update_field(datafield=datafield)

    def pop_field(
        self, datafield: str | bytes | DeviceHexDataField
    ) -> DeviceHexDataField | None:
        """Remove the given field name and return it, or return None if not found."""
        if isinstance(datafield, bytes):
            datafield = datafield.hex()
        elif isinstance(datafield, DeviceHexDataField):
            datafield = datafield.f_name.hex()
        else:
            datafield = str(datafield)
        df = (self.msg_fields or {}).pop(datafield, None)
        # update length and hexbytes
        self._update_hexbytes()
        return df


@dataclass(kw_only=True)
class MqttDataStats:
    """Dataclass to track MQTT statistics."""

    bytes_received: int = 0
    bytes_sent: int = 0
    kb_hourly_sent: float = 0
    kb_hourly_received: float = 0
    start_time: datetime = field(default_factory=datetime.now)
    dev_messages: dict[str, dict[str, dict]] = field(default_factory=dict)
    msg_data: InitVar[DeviceHexData | None] = None

    def __post_init__(self, msg_data) -> None:
        """Init the dataclass from optional DeviceHexData for first stats."""
        if not isinstance(self.start_time, datetime):
            self.start_time = datetime.now()
        if not isinstance(self.dev_messages, dict):
            self.dev_messages = {}
        if isinstance(msg_data, DeviceHexData):
            self.add_data(device_data=msg_data)

    def __str__(self) -> str:
        """Print the class fields."""
        return (
            f"Start: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}, Received: {self.bytes_received/1024:.3f} KB ({self.kb_hourly_received:7.3f} KB/h), "
            f"Sent: {self.bytes_sent/1024:.3f} KB ({self.kb_hourly_sent:7.3f} KB/h), "
            f"Messages: {self.dev_messages.get('count', 0)} ({self.dev_messages.get('bytes', 0)/1024:.3f} KB)"
        )

    def update(self) -> None:
        """Update calculated stats."""
        elapsed = max(1, (datetime.now() - self.start_time).total_seconds()) / 3600
        self.kb_hourly_sent = self.bytes_sent / 1024 / elapsed
        self.kb_hourly_received = self.bytes_received / 1024 / elapsed

    def add_bytes(self, count: int = 0, sent: bool = False) -> None:
        """Add mqtt message and calculate stats."""
        if isinstance(count, int | float):
            if sent:
                self.bytes_sent += int(count)
            else:
                self.bytes_received += int(count)
        self.update()

    def add_data(self, device_data: DeviceHexData) -> None:
        """Add device data and calculate device messages."""
        if isinstance(device_data, DeviceHexData):
            # increate total count
            self.dev_messages["count"] = self.dev_messages.get("count", 0) + 1
            self.dev_messages["bytes"] = self.dev_messages.get("bytes", 0) + device_data.length
            # increase count and bytes per device model and message type
            msg_type = device_data.msg_header.msgtype.hex()
            device_map = self.dev_messages.get(device_data.model, {})
            messages = device_map.get(msg_type, {})
            messages["count"] = messages.get("count", 0) + 1
            messages["bytes"] = messages.get("bytes", 0) + device_data.length
            device_map[msg_type] = messages
            self.dev_messages[device_data.model] = device_map

    def asdict(self) -> dict:
        """Return a dictionary representation of the class fields."""
        return asdict(self)
