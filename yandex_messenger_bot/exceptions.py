from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from yandex_messenger_bot.methods.base import YaBotMethod


class YaBotError(Exception):
    """Base exception for all SDK errors."""


class APIError(YaBotError):
    """Error returned by Yandex Messenger Bot API."""

    def __init__(
        self,
        message: str,
        status_code: int,
        description: str,
        method: YaBotMethod[Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.description = description
        self.method = method
        super().__init__(message)

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(status_code={self.status_code!r}, "
            f"description={self.description!r})"
        )


class BadRequestError(APIError):
    """400 Bad Request."""


class UnauthorizedError(APIError):
    """401 Unauthorized."""


class ForbiddenError(APIError):
    """403 Forbidden / Invalid token."""


class NotFoundError(APIError):
    """404 Not Found."""


class ConflictError(APIError):
    """409 Conflict."""


class PayloadTooLargeError(APIError):
    """413 Payload Too Large."""


class TooManyRequestsError(APIError):
    """429 Too Many Requests."""

    def __init__(
        self,
        message: str,
        status_code: int,
        description: str,
        retry_after: float,
        method: YaBotMethod[Any] | None = None,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(message, status_code, description, method)


class ServerError(APIError):
    """5xx Server Error."""


class NetworkError(YaBotError):
    """Connection or timeout error."""


class ClientDecodeError(YaBotError):
    """Failed to decode API response."""


class DependencyResolutionError(YaBotError):
    """A handler dependency could not be resolved."""


_STATUS_TO_ERROR: dict[int, type[APIError]] = {
    400: BadRequestError,
    401: UnauthorizedError,
    403: ForbiddenError,
    404: NotFoundError,
    409: ConflictError,
    413: PayloadTooLargeError,
    429: TooManyRequestsError,
    500: ServerError,
    502: ServerError,
    503: ServerError,
    504: ServerError,
}


def raise_for_status(
    status_code: int,
    description: str,
    method: YaBotMethod[Any] | None = None,
    retry_after: float | None = None,
) -> None:
    """Raise a typed APIError based on HTTP status code."""
    error_cls = _STATUS_TO_ERROR.get(status_code, APIError)

    if error_cls is TooManyRequestsError:
        raise TooManyRequestsError(
            message=f"API error {status_code}: {description}",
            status_code=status_code,
            description=description,
            retry_after=retry_after or 1.0,
            method=method,
        )

    raise error_cls(
        message=f"API error {status_code}: {description}",
        status_code=status_code,
        description=description,
        method=method,
    )
