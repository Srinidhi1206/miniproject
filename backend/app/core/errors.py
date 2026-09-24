"""User-facing error model.

Every error that reaches the client is a `SentinelError` with a stable machine
code and a friendly, non-technical message. Unexpected exceptions are logged
server-side and converted to a generic message — stack traces never leave the
server.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("sentinel.errors")


class SentinelError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, hint: str | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.hint = hint

    def to_dict(self) -> dict:
        body = {"error": {"code": self.code, "message": self.message}}
        if self.hint:
            body["error"]["hint"] = self.hint
        return body


# ---- Common, reusable errors -------------------------------------------------

def unsupported_file(accepted: str) -> SentinelError:
    return SentinelError(
        "UNSUPPORTED_FILE",
        "This file type isn't supported.",
        415,
        hint=f"Accepted formats: {accepted}.",
    )


def file_too_large(limit_mb: int) -> SentinelError:
    return SentinelError(
        "FILE_TOO_LARGE", f"That file is larger than the {limit_mb} MB limit.", 413,
        hint="Try a cropped screenshot or a compressed image.",
    )


def not_found(what: str) -> SentinelError:
    return SentinelError("NOT_FOUND", f"We couldn't find that {what}.", 404)


# ---- Handlers ----------------------------------------------------------------

def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(SentinelError)
    async def _sentinel(_: Request, exc: SentinelError):
        return JSONResponse(exc.to_dict(), status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        # Summarise pydantic errors without echoing user input back.
        # Malformed JSON reports a character offset as its location; call that "body".
        fields = sorted({
            "body" if e.get("type") == "json_invalid" else (".".join(str(p) for p in e.get("loc", [])[1:]) or "body")
            for e in exc.errors()
        })
        return JSONResponse(
            {"error": {
                "code": "INVALID_INPUT",
                "message": "Some of the submitted information is missing or invalid.",
                "fields": fields,
            }},
            status_code=422,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        message = "Not found." if exc.status_code == 404 else "The request could not be completed."
        return JSONResponse({"error": {"code": f"HTTP_{exc.status_code}", "message": message}},
                            status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        log.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            {"error": {
                "code": "INTERNAL_ERROR",
                "message": "Something went wrong on our side. Your content was not stored. Please try again.",
            }},
            status_code=500,
        )
