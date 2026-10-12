from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppException(Exception):
    status_code: int = 500
    code: str = "internal_error"
    message: str = "Something went wrong."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.message
        self.details = details
        super().__init__(self.message)


class NotFoundError(AppException):
    status_code = 404
    code = "not_found"
    message = "Resource not found."


class UnauthorizedError(AppException):
    status_code = 401
    code = "unauthorized"
    message = "Authentication required."


class ConflictError(AppException):
    status_code = 409
    code = "conflict"
    message = "Resource already exists."


class ValidationAppError(AppException):
    status_code = 422
    code = "validation_error"
    message = "Invalid input."


class BookingRejectedError(AppException):
    """A booking request broke a rule or nothing was free. `details["reason"]` says which."""

    status_code = 409
    code = "booking_rejected"
    message = "The booking can't be made."

    def __init__(self, reason: str, message: str | None = None) -> None:
        super().__init__(message, details={"reason": reason})
        self.reason = reason


async def _app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "details": exc.details},
    )


async def _request_validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Give FastAPI's own 422s (bad query params, bodies) the same shape as AppException."""
    errors = [
        {"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "code": ValidationAppError.code,
            "message": ValidationAppError.message,
            "details": {"errors": errors},
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppException, _app_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _request_validation_handler)  # type: ignore[arg-type]
