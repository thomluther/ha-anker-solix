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

    def add(self, request_time: datetime = datetime.now()) -> None:
        """Add new timestamp to end of counter."""
        self.elements.append(request_time)
        # limit the counter entries to 1 hour when adding new
        self.recycle()

    def recycle(
        self, last_time: datetime = datetime.now() - timedelta(hours=1)
    ) -> None:
        """Remove oldest timestamps from beginning of counter until last_time is reached, default is 1 hour ago."""
        self.elements = [x for x in self.elements if x > last_time]

    def last_minute(self) -> int:
        """Get number of timestamps for last minute."""
        last_time = datetime.now() - timedelta(minutes=1)
        return len([x for x in self.elements if x > last_time])

    def last_hour(self) -> int:
        """Get number of timestamps for last hour."""
        last_time = datetime.now() - timedelta(hours=1)
        return len([x for x in self.elements if x > last_time])


def md5(text: str) -> str:
    """Return MD5 hash in hex for given string."""
    h = hashes.Hash(hashes.MD5())
    h.update(text.encode("utf-8"))
    return h.finalize().hex()


def getTimezoneGMTString() -> str:
    """Construct timezone GMT string with offset, e.g. GMT+01:00."""
    tzo = datetime.now().astimezone().strftime("%z")
    return f"GMT{tzo[:3]}:{tzo[3:5]}"

