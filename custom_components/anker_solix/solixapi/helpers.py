"""Helper modules and classes for the Anker Power/Solix Cloud API."""

from datetime import datetime, timedelta

from cryptography.hazmat.primitives import hashes


class RequestCounter:
    """Counter for datetime entries in last minute and last hour."""

    def __init__(
        self,
    ) -> None:
        """Initialize."""
        self.elements: list = []

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

    def last_minute(self, details: bool = False) -> int | list:
        """Get number of timestamps or all details for last minute."""
        last_time = datetime.now() - timedelta(minutes=1)
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
        )


def md5(text: str) -> str:
    """Return MD5 hash in hex for given string."""
    h = hashes.Hash(hashes.MD5())
    h.update(text.encode("utf-8"))
    return h.finalize().hex()


def getTimezoneGMTString() -> str:
    """Construct timezone GMT string with offset, e.g. GMT+01:00."""
    tzo = datetime.now().astimezone().strftime("%z")
    return f"GMT{tzo[:3]}:{tzo[3:5]}"


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
