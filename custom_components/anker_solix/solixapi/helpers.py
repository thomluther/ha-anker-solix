"""Helper modules and classes for the Anker Power/Solix Cloud API."""

import contextlib
from datetime import datetime, time, timedelta
from enum import Enum
import hashlib
from typing import Any


class RequestCounter:
    """Counter for datetime entries in last minute and last hour."""

    def __init__(
        self,
    ) -> None:
        """Initialize."""
        self.elements: list = []
        self.throttled: set = set()

    def __str__(self) -> str:
        """Print the counters."""
        return f"{self.last_hour()} last hour, {self.last_minute()} last minute"

    def add(self, request_time: datetime | None = None, request_info: str = "") -> None:
        """Add new tuple with timestamp and optional request info to end of counter."""
        self.elements.append((request_time or datetime.now(), request_info))
        # limit the counter entries to 1 hour when adding new
        self.recycle()

    def recycle(
        self, last_time: datetime = datetime.now() - timedelta(hours=1)
    ) -> None:
        """Remove oldest timestamps from beginning of counter until last_time is reached, default is 1 hour ago."""
        self.elements = [x for x in self.elements if x[0] > last_time]

    def add_throttle(self, endpoint: str) -> None:
        """Add and endpoint to the throttled endpoint set."""
        if endpoint and isinstance(endpoint, str):
            self.throttled.add(endpoint)

    def last_minute(self, details: bool = False) -> int | list:
        """Get number of timestamps or all details for last minute."""
        last_time = datetime.now() - timedelta(minutes=1, seconds=2)
        requests = [x for x in self.elements if x[0] > last_time]
        return requests if details else len(requests)

    def last_hour(self, details: bool = False) -> int | list:
        """Get number of timestamps or details for last hour."""
        last_time = datetime.now() - timedelta(hours=1)
        requests = [x for x in self.elements if x[0] > last_time]
        return requests if details else len(requests)

    def get_details(self, last_hour: bool = False) -> str:
        """Get string with details of selected interval."""
        return "\n".join(
            [
                (item[0]).strftime("%H:%M:%S.")
                + str((item[0]).microsecond)[0:3]
                + " --> "
                + str(item[1])
                for item in (
                    self.last_hour(details=True)
                    if last_hour
                    else self.last_minute(details=True)
                )
            ]
            + ["Throttled Endpoints:"]
            + (list(self.throttled) or ["None"])
        )


def md5(data: str | bytes) -> str:
    """Return MD5 hash in hex for given string or bytes."""
    return hashlib.md5(data.encode() if isinstance(data, str) else data).hexdigest()


def getTimezoneGMTString() -> str:
    """Construct timezone GMT string with offset, e.g. GMT+01:00."""
    tzo = datetime.now().astimezone().strftime("%z")
    return f"GMT{tzo[:3]}:{tzo[3:5]}"


def generateTimestamp(in_ms: bool = False) -> str:
    """Generate unix epoche timestamp from local time in seconds or milliseconds."""
    return str(int(datetime.now().timestamp() * (1000 if in_ms else 1)))


def convertToKwh(val: str | float, unit: str, decimals: int = 2) -> str | float | None:
    """Convert a given value to kWh depending on unit, rounded to decimals."""
    try:
        result = None
        if isinstance(val, str):
            result = float(val)
        elif isinstance(val, int | float):
            result = val
        if result is None or not isinstance(unit, str):
            return None
        if (unit := unit.lower()) == "wh":
            result = round(result / 1000, decimals)
        elif unit == "mwh":
            result = round(result * 1000, decimals)
        elif unit == "gwh":
            result = round(result * 1000 * 1000, decimals)
        else:
            result = round(result, decimals)
        return f"{result:.{decimals}f}" if isinstance(val, str) else result
    except ValueError:
        return None


def convert_time_seconds(val: str | float | time) -> int | time | None:
    """Convert the given time or seconds value into the opposite. A string will be intepreted as time string."""
    # first convert into any of the 2 expected formats
    if isinstance(val, str):
        try:
            val = time.fromisoformat(val)
        except ValueError:
            val = None
    elif isinstance(val, float | int):
        val = int(val % (24 * 3600))  # Restricting to a 24-hour format
    if isinstance(val, time):
        return val.hour * 3600 + val.minute * 60 + val.second
    if isinstance(val, int):
        hours, remainder = divmod(val, 3600)
        minutes, seconds = divmod(remainder, 60)
        return time(hours, minutes, seconds)
    return None


def convert_time_minutes(val: str | float | time) -> int | time | None:
    """Convert the given time or minutes value into the opposite. A string will be intepreted as time string."""
    # first convert into any of the 2 expected formats
    if isinstance(val, str):
        try:
            val = time.fromisoformat(val)
        except ValueError:
            val = None
    elif isinstance(val, float | int):
        val = int(val % (24 * 60))  # Restricting to a 24-hour format
    if isinstance(val, time):
        return val.hour * 60 + val.minute
    if isinstance(val, int):
        hours, minutes = divmod(val, 60)
        return time(hours, minutes)
    return None


def get_enum_name(
    enum_class: Enum, value: Any, default: Any | None = None
) -> Any | None:
    """Get the name for an enum value safely with optional default or None."""
    return enum_class(value).name if value in iter(enum_class) else default


def get_enum_value(
    enum_class: Enum, name: str, default: Any | None = None
) -> Any | None:
    """Get the value for an enum name safely with optional default or None."""
    member: Enum | None = getattr(enum_class, str(name), None)
    return member.value if member is not None else default


def round_by_factor(value: float, factor: float) -> int | float:
    """Round the given value by the precision of the factor."""
    # ensure precise float string, cut trailing 0 and ., reverse string and find position of ., use 0 if not found (-1)
    decimals = max(0, f"{factor:.15f}".rstrip("0").rstrip(".")[::-1].find("."))
    # ensure to round to integer if decimals is 0, avoid sign for 0 float
    value = round(value, decimals or None)
    return value if value != 0 else 0


def get_solix_product_code(sn: str) -> str:
    """Extract Anker Solix product code from serial number string.

    Rules:
    - 16-digit SN: characters 4-6 (index 3-5, 3 characters)
    - 17-digit SN: characters 4-7 (index 3-6, 4 characters)
    """
    if isinstance(sn, str):
        sn = sn.strip()
        if 16 <= len(sn) <= 17:
            # 16-digit SN: extract characters 4-6 (index 3-5)
            # 17-digit SN: extract characters 4-7 (index 3-6)
            return sn[3 : len(sn) - 10]
    return ""


# Definition of generic converters to convert Anker Solix MQTT field bytes into consumable values and vice versa
# They can be re-used in MQTT message decoding, value extraction and value encoding routines


def convert_timestamp(
    value: float | bytes | bytearray, ms: bool = False
) -> float | bytes | None:
    """Convert the input value between bytes and float value according to the formats used in MQTT messages."""
    # traditional timestamp format with field type var with 4 bytes little endian representing the timestamp in seconds
    # new format is timestamp in milliseconds as string formatted field
    if isinstance(value, float | int):
        # convert to bytes
        if ms:
            # convert timestamp to ms and strin prior encoding
            return str(int(value * 1000)).encode()
        # encode timestamp as little endian integer
        return int(value).to_bytes(4, byteorder="little")
    if isinstance(value, bytes | bytearray):
        # convert to float timestamp in seconds
        if ms or len(value) > 4:
            msec = "".join(
                c
                for c in value.decode(errors="ignore").strip()
                if (c.isdigit() or c == ".")
            )
            if msec.replace(".", "", 1).isdigit():
                return float(msec) / 1000
        else:
            return float(int.from_bytes(value, byteorder="little", signed=True))
    return None


def convert_time(value: bytes | bytearray | str) -> bytes | str | None:
    """Convert time between bytes used in MQTT messages and string formats.

    Automatically detects input value type and converts accordingly.

    Args:
        value: Time data in bytes format (2-3 bytes in little endian: ([seconds,] minutes, hours))
              or string format (HH:MM or HH:MM:SS).

    Returns:
        String in HH:MM[:SS] format if input is bytes/bytearray.
        2-3 Bytes ([seconds,] minutes, hours) if input is string.
        None if input is invalid or unsupported type.

    """
    if isinstance(value, bytes | bytearray) and (2 <= len(value) <= 3):
        # Convert bytes to string
        parts = [f"{x:02d}" for x in value]
        parts.reverse()  # reverse to little endian
        return ":".join(parts)
    if (
        isinstance(value, str)
        and (parts := value.split(":"))
        and (2 <= len(parts) <= 3)
    ):
        # Convert string to bytes
        if (
            (parts[0].isdigit() and 0 <= int(parts[0]) <= 23)
            and (parts[1].isdigit() and 0 <= int(parts[1]) <= 59)
            and (len(parts) < 3 or (parts[2].isdigit() and 0 <= int(parts[2]) <= 59))
        ):
            return bytes(
                ([int(parts[2])] if len(parts) > 2 else [])
                + [int(parts[1]), int(parts[0])]
            )
    return None


def convert_weekdays(
    value: bytes | bytearray | list | set, lsb_day: str = "mon"
) -> bytes | list | None:
    """Convert list of weekdays between bitmask used in MQTT messages and list formats.

    Automatically detects input value type and converts accordingly. The typical Bitmask is:
    0:sun:sat:fri:thu:wed:tue:mon
    with mon as lsb_day

    Args:
        value: Weekday data in a byte bitmask (1 byte, 0-0x7f)
              or list|set with 3 char weekdays or "all", format ["tue", "sat"] or ["all"].
        lsb_day: least significant day of week = bit 0

    Returns:
        List with weekdays if input is bytes/bytearray.
        1 Byte with the bitmask (0-0x7f) if input is list.
        None if input is invalid or unsupported type.

    """
    weekdays = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    if isinstance(lsb_day, str) and lsb_day.lower() in weekdays:
        idx = weekdays.index(lsb_day.lower())
        weekdays = weekdays[idx:] + weekdays[:idx]
    if isinstance(value, bytes | bytearray) and len(value) == 1:
        # Convert bitmask to list
        return [
            name
            for idx, name in enumerate(weekdays)
            if int.from_bytes(value) & (1 << idx)
        ]
    if isinstance(value, list | set) and (0 <= len(set(value)) <= 10):
        # convert elements to lower case string and "all" to weekdays
        value = set(map(str.lower, map(str, value)))
        if "all" in value:
            value = (value - {"all"}) | set(weekdays)
        # Convert valid weekdays into bitmask byte
        return sum(
            1 << weekdays.index(day.lower())
            for day in value
            if isinstance(day, str) and day in weekdays
        ).to_bytes()
    return None


def convert_port_protocols(
    value: bytes | bytearray | list | set,
) -> bytes | list | None:
    """Convert list with eligible USB-C port protocols between bitmask used in MQTT messages and list formats.

    Automatically detects input value type and converts accordingly. The typical Bitmask is:
    xiaomi:huawei:pps20v:pps16v:pps11v:pd12v:ufcs:scp

    Args:
        value: Protocols in a byte bitmask (1 byte, 0-0xff)
              or list|set with port protocols or "all", format ["pps16v", "ufcs"] or ["all"].
              Note: Restrictions may apply and all protocols together may not be supported.

    Returns:
        List with protocols if input is bytes/bytearray.
        1 Byte with the bitmask (0-0xff) if input is list or set.
        None if input is invalid or unsupported type.

    """
    protocols = [
        "scp",
        "ufcs",
        "pd12v",
        "pps11v",
        "pps16v",
        "pps20v",
        "huawei",
        "xiaomi",
    ]
    if isinstance(value, bytes | bytearray) and len(value) == 1:
        # Convert bitmask to list
        return [
            name
            for idx, name in enumerate(protocols)
            if int.from_bytes(value) & (1 << idx)
        ]
    if isinstance(value, list | set) and (0 <= len(set(value)) <= 10):
        # convert elements to lower case string and "all" to weekdays
        value = set(map(str.lower, map(str, value)))
        if "all" in value:
            value = (value - {"all"}) | set(protocols)
        # Convert valid weekdays into bitmask byte
        return sum(
            1 << protocols.index(day.lower())
            for day in value
            if isinstance(day, str) and day in protocols
        ).to_bytes()
    return None


def convert_pps_custom_schedule(
    value: bytes | bytearray | dict,
) -> bytearray | dict | None:
    """Convert between PPS custom schedule dictionary and binary field as used in MQTT messages.

    Automatically detects input value type and converts accordingly. The dictionary structure:
    groups:u8  1: e.g. weekdays, 2: e.g. weekend
    per group: weekdays:u8 (bit0=Mon..bit6=Sun), slots:u8 + 5 slots max
    per slot: load_mode:u8 (1=Charge, 2=Discharge), start_minutes:u16 LE, end_minutes:u16 LE
    01:  1f:  02:  01: 00:00: 68:01:  02: 68:01: d0:02
    02:  1f:  02:  01: 00:00: 68:01:  02: 68:01: d0:02  :60:  01:  02: 00:00: 3c:00
    grp  wk   slt  dis    00    360   chrg  360    720   wk   slt  chg    00     60

    Args:
        value: dictionary or binary with schedule structure

    Returns:
        Dictionary with schedule if input is bytes/bytearray.
        Bytearray with schedule data if input is valid dictionary structure.
        None if conversion failed

    """
    if isinstance(value, bytes | bytearray):
        # Convert binary to dict
        with contextlib.suppress(ValueError, TypeError):
            pos = 0
            schedule = {}
            if groups := int.from_bytes(value[:1]):
                schedule["groups"] = []
                pos += 1
            for grp in range(groups):
                group = {
                    "index": grp,
                    "weekdays": convert_weekdays(value[pos : pos + 1]),
                    "ranges": [],
                }
                pos += 1
                if slots := int.from_bytes(value[pos : pos + 1]):
                    pos += 1
                    for _ in range(slots):
                        start = int.from_bytes(
                            value[pos + 1 : pos + 3], byteorder="little"
                        )
                        end = int.from_bytes(
                            value[pos + 3 : pos + 5], byteorder="little"
                        )
                        slot = {
                            "load_mode": int.from_bytes(
                                value[pos : pos + 1], byteorder="little"
                            ),
                            "start_time": f"{start // 60:02d}:{start % 60:02d}",
                            "end_time": f"{end // 60:02d}:{end % 60:02d}",
                        }
                        group["ranges"].append(slot)
                        pos += 5
                schedule["groups"].append(group)
            return schedule
    if isinstance(value, dict):
        # convert elements to binary structure
        with contextlib.suppress(ValueError, TypeError):
            hexvalue = bytearray()
            groups = value.get("groups", [])
            hexvalue.extend(len(groups).to_bytes(byteorder="little"))
            for group in groups:
                hexvalue.extend(convert_weekdays(group.get("weekdays", [])))
                slots = group.get("ranges", [])
                hexvalue.extend(len(slots).to_bytes(byteorder="little"))
                for slot in slots:
                    hexvalue.extend(
                        int(slot.get("load_mode", 0)).to_bytes(byteorder="little")
                    )
                    start = slot.get("start_time", "").split(":")
                    end = slot.get("end_time", "").split(":")
                    hexvalue.extend(
                        int(
                            int((start[:1] or [0])[0]) * 60
                            + int((start[1:2] or [])[0] or 0)
                        ).to_bytes(length=2, byteorder="little")
                    )
                    hexvalue.extend(
                        int(
                            int((end[:1] or [])[0] or 0) * 60
                            + int((end[1:2] or [0])[0])
                        ).to_bytes(length=2, byteorder="little")
                    )
            return hexvalue
    return None


def convert_pps_tou_schedule(
    value: bytes | bytearray | dict, min_slots: int = 0, max_slots: int = 6
) -> bytearray | dict | None:
    """Convert between PPS time of use schedule dictionary and binary field as used in MQTT messages.

    Automatically detects input value type and converts accordingly. The dictionary structure:
    Byte with slot count
    Each slot has 3 bytes: tariff: (1=Peak,2=Mid,3=Off), start_hr, end_hr
    max 6 slots are allowed in the app, the field may have max 7 slots
    The price per tariff is not part of the structure, this may be maintained by App/Cloud only

    Args:
        value: dictionary or binary with schedule structure
        min_slots: Trailing bytes will be added if min slots > found slots (ignored for dictionary extract)
        max_slots: Max bytes slots to be extracted, None returned if dictionary exceeds max

    Returns:
        Dictionary with schedule if input is bytes/bytearray.
        Bytearray with schedule data if input is valid dictionary structure.
        None if conversion failed

    """
    if isinstance(value, bytes | bytearray):
        # Convert binary to dict
        with contextlib.suppress(ValueError, TypeError):
            pos = 0
            schedule = {}
            if slots := int.from_bytes(value[:1]):
                schedule["ranges"] = []
                pos += 1
            for _ in range(slots):
                start = int.from_bytes(value[pos + 1 : pos + 2], byteorder="little")
                end = int.from_bytes(value[pos + 2 : pos + 3], byteorder="little")
                slot = {
                    "tariff": int.from_bytes(value[pos : pos + 1], byteorder="little"),
                    "start_time": f"{start:02d}:00",
                    "end_time": f"{end:02d}:00",
                }
                schedule["ranges"].append(slot)
                pos += 3
            return schedule
    if isinstance(value, dict):
        # convert elements to binary structure
        with contextlib.suppress(ValueError, TypeError):
            hexvalue = bytearray()
            slots = value.get("ranges", [])
            # limit count to max converted slots
            hexvalue.extend(min(len(slots), max_slots).to_bytes(byteorder="little"))
            # adopt slot list according to limits
            if len(slots) < min_slots:
                slots.extend({} for _ in range(min_slots - len(slots)))
            slots = slots[:max_slots]
            for slot in slots:
                hexvalue.extend(int(slot.get("tariff", 0)).to_bytes(byteorder="little"))
                start = slot.get("start_time", "").split(":")
                end = slot.get("end_time", "").split(":")
                hexvalue.extend(
                    int((start[:1] or [])[0] or 0).to_bytes(byteorder="little")
                )
                hexvalue.extend(
                    int((end[:1] or [])[0] or 0).to_bytes(byteorder="little")
                )
            return hexvalue
    return None
