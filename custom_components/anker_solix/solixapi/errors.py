"""Define Anker Solix API errors."""

from __future__ import annotations


class AnkerSolixError(Exception):
    """Define a base error."""


class AuthorizationError(AnkerSolixError):
    """Authorization error."""


class ConnectError(AnkerSolixError):
    """Connection error."""


class NetworkError(AnkerSolixError):
    """Network error."""


class ServerError(AnkerSolixError):
    """Server error."""


class RequestError(AnkerSolixError):
    """Request error."""


class ItemNotFoundError(RequestError):
    """Requested item not found error."""


class ItemExistsError(RequestError):
    """Duplicate item error."""


class ItemLimitExceededError(RequestError):
    """Item limit exceeded error."""


class BusyError(AnkerSolixError):
    """Busy error."""


class RequestLimitError(AnkerSolixError):
    """Request Limit exceeded error."""


class VerifyCodeError(AnkerSolixError):
    """Verify code error."""


class VerifyCodeExpiredError(AnkerSolixError):
    """Verification code has expired."""


class NeedVerifyCodeError(AnkerSolixError):
    """Need verification code error."""


class VerifyCodeMaxError(AnkerSolixError):
    """Maximum attempts of verifications error."""


class VerifyCodeNoneMatchError(AnkerSolixError):
    """Verify code none match error."""


class VerifyCodePasswordError(AnkerSolixError):
    """Verify code password error."""


class ClientPublicKeyError(AnkerSolixError):
    """Define an error for client public key error."""


class TokenKickedOutError(AnkerSolixError):
    """Define an error for token does not exist because it was kicked out."""


class InvalidCredentialsError(AnkerSolixError):
    """Define an error for unauthenticated accounts."""


class RetryExceeded(AnkerSolixError):
    """Define an error for exceeded retry attempts. Please try again in 24 hours."""


class NoAccessPermission(AnkerSolixError):
    """The device has no access permission."""


ERRORS: dict[int, type[AnkerSolixError]] = {
    401: AuthorizationError,
    403: AuthorizationError,
    429: RequestLimitError,
    502: ConnectError,
    504: ConnectError,
    997: ConnectError,
    998: NetworkError,
    999: ServerError,
    10000: RequestError,
    10003: RequestError,
    10004: ItemNotFoundError,
    10007: RequestError,
    21105: BusyError,
    26050: VerifyCodeError,
    26051: VerifyCodeExpiredError,
    26052: NeedVerifyCodeError,
    26053: VerifyCodeMaxError,
    26054: VerifyCodeNoneMatchError,
    26055: VerifyCodePasswordError,
    26070: ClientPublicKeyError,
    26084: TokenKickedOutError,
    26108: InvalidCredentialsError,
    26156: InvalidCredentialsError,
    26161: RequestError,
    31001: ItemExistsError,
    31003: ItemLimitExceededError,
    100053: RetryExceeded,
    160003: NoAccessPermission,
}


def raise_error(data: dict, prefix: str = "Anker Api Error") -> None:
    """Raise the appropriate Api error based upon a response code in json data."""
    if isinstance(data, dict) and "code" in data:
        # json dict, get code for server response
        code = int(data.get("code"))
    else:
        return
    if error := ERRORS.get(code) or (AnkerSolixError if code >= 10000 else None):
        raise error(f"({code}) {prefix}: {data.get('msg', 'Error msg not found')}")
