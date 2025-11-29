"""Helper modules and classes for the Anker Power/Solix Cloud API."""

from datetime import datetime, timedelta
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


def convertToKwh(val: str | float, unit: str) -> str | float | None:
    """Convert a given value to kWh depending on unit."""
    try:
        result = None
        if isinstance(val, str):
            result = float(val)
        elif isinstance(val, int | float):
            result = val
        if result is None or not isinstance(unit, str):
            return None
        if (unit := unit.lower()) == "wh":
            result = round(result / 1000, 2)
        elif unit == "mwh":
            result = round(result * 1000, 2)
        elif unit == "gwh":
            result = round(result * 1000 * 1000, 2)
        else:
            return val
        return str(result) if isinstance(val, str) else result
    except ValueError:
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
    member: Enum | None = getattr(enum_class, name, None)
    return member.value if member is not None else default


def round_by_factor(value: float, factor: float) -> int | float:
    """Round the given value by the precision of the factor."""
    # ensure precise float string, cut trailing 0 and ., reverse string and find position of ., use 0 if not found (-1)
    decimals = max(0, f"{factor:.15f}".rstrip("0").rstrip(".")[::-1].find("."))
    # ensure to round to integer if decimals is 0
    return round(value, decimals or None)
