"""Tests for exception hierarchy and raise_for_status."""

from __future__ import annotations

import pytest

from yandex_messenger_bot.exceptions import (
    APIError,
    BadRequestError,
    ClientDecodeError,
    ConflictError,
    DependencyResolutionError,
    ForbiddenError,
    NetworkError,
    NotFoundError,
    PayloadTooLargeError,
    ServerError,
    TooManyRequestsError,
    UnauthorizedError,
    YaBotError,
    raise_for_status,
)

# ---------------------------------------------------------------------------
# raise_for_status — correct exception type for each status code
# ---------------------------------------------------------------------------


class TestRaiseForStatus:
    @pytest.mark.parametrize(
        ("status_code", "expected_cls"),
        [
            (400, BadRequestError),
            (401, UnauthorizedError),
            (403, ForbiddenError),
            (404, NotFoundError),
            (409, ConflictError),
            (413, PayloadTooLargeError),
            (429, TooManyRequestsError),
            (500, ServerError),
            (502, ServerError),
            (503, ServerError),
            (504, ServerError),
        ],
    )
    def test_raises_correct_type(self, status_code: int, expected_cls: type):
        with pytest.raises(expected_cls):
            raise_for_status(status_code, description="error detail")

    def test_unknown_status_raises_base_api_error(self):
        with pytest.raises(APIError) as exc_info:
            raise_for_status(418, description="I'm a teapot")
        assert type(exc_info.value) is APIError

    def test_exception_message_contains_status_and_description(self):
        with pytest.raises(BadRequestError) as exc_info:
            raise_for_status(400, description="missing chat_id")
        msg = str(exc_info.value)
        assert "400" in msg
        assert "missing chat_id" in msg

    def test_status_code_stored_on_exception(self):
        with pytest.raises(ForbiddenError) as exc_info:
            raise_for_status(403, description="invalid token")
        assert exc_info.value.status_code == 403

    def test_description_stored_on_exception(self):
        with pytest.raises(NotFoundError) as exc_info:
            raise_for_status(404, description="chat not found")
        assert exc_info.value.description == "chat not found"

    def test_method_defaults_to_none(self):
        with pytest.raises(BadRequestError) as exc_info:
            raise_for_status(400, description="bad")
        assert exc_info.value.method is None

    def test_method_passed_through(self):
        from yandex_messenger_bot.methods.send_text import SendText

        method = SendText(chat_id="c-1", text="hi")
        with pytest.raises(BadRequestError) as exc_info:
            raise_for_status(400, description="bad", method=method)
        assert exc_info.value.method is method


# ---------------------------------------------------------------------------
# TooManyRequestsError — retry_after field
# ---------------------------------------------------------------------------


class TestTooManyRequestsError:
    def test_retry_after_passed_through(self):
        with pytest.raises(TooManyRequestsError) as exc_info:
            raise_for_status(429, description="slow down", retry_after=30.5)
        assert exc_info.value.retry_after == 30.5

    def test_retry_after_defaults_to_1_when_none(self):
        """When caller passes retry_after=None, SDK defaults to 1.0."""
        with pytest.raises(TooManyRequestsError) as exc_info:
            raise_for_status(429, description="slow down", retry_after=None)
        assert exc_info.value.retry_after == 1.0

    def test_is_subclass_of_api_error(self):
        err = TooManyRequestsError(
            message="429",
            status_code=429,
            description="rate limited",
            retry_after=5.0,
        )
        assert isinstance(err, APIError)
        assert isinstance(err, YaBotError)


# ---------------------------------------------------------------------------
# Exception repr
# ---------------------------------------------------------------------------


class TestExceptionRepr:
    def test_repr_contains_status_code(self):
        err = BadRequestError(
            message="API error 400: bad", status_code=400, description="bad request"
        )
        r = repr(err)
        assert "400" in r

    def test_repr_contains_description(self):
        err = UnauthorizedError(
            message="API error 401: no token", status_code=401, description="no token"
        )
        r = repr(err)
        assert "no token" in r

    def test_repr_contains_class_name(self):
        err = ForbiddenError(
            message="API error 403: denied", status_code=403, description="denied"
        )
        r = repr(err)
        assert "ForbiddenError" in r

    def test_server_error_repr(self):
        err = ServerError(
            message="API error 500: oops", status_code=500, description="internal error"
        )
        r = repr(err)
        assert "ServerError" in r
        assert "500" in r

    def test_too_many_requests_repr(self):
        err = TooManyRequestsError(
            message="API error 429: slow down",
            status_code=429,
            description="rate limited",
            retry_after=60.0,
        )
        r = repr(err)
        assert "TooManyRequestsError" in r
        assert "429" in r


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class TestExceptionHierarchy:
    def test_all_api_errors_inherit_ya_bot_error(self):
        for cls in (
            BadRequestError,
            UnauthorizedError,
            ForbiddenError,
            NotFoundError,
            ConflictError,
            PayloadTooLargeError,
            TooManyRequestsError,
            ServerError,
        ):
            assert issubclass(cls, YaBotError), f"{cls.__name__} must inherit YaBotError"

    def test_network_error_inherits_ya_bot_error(self):
        assert issubclass(NetworkError, YaBotError)

    def test_client_decode_error_inherits_ya_bot_error(self):
        assert issubclass(ClientDecodeError, YaBotError)

    def test_dependency_resolution_error_inherits_ya_bot_error(self):
        assert issubclass(DependencyResolutionError, YaBotError)

    def test_api_error_is_catchable_as_base(self):
        """All specific API errors should be catchable with a single 'except APIError'."""
        errors_raised = []
        for status_code in (400, 401, 403, 404, 409, 413, 500):
            try:
                raise_for_status(status_code, description="test")
            except APIError as e:
                errors_raised.append(e.status_code)
        assert errors_raised == [400, 401, 403, 404, 409, 413, 500]
