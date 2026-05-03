"""
Custom exceptions and FastAPI exception handlers.

Having a dedicated exception hierarchy makes it easy to return
consistent, machine-readable error responses.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


# ---------------------------------------------------------------------------
# Exception classes
# ---------------------------------------------------------------------------

class ReportGeneratorError(Exception):
    """Base class for all application-specific exceptions."""

    status_code: int = 500
    detail: str = "An unexpected error occurred."

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)


class ValidationError(ReportGeneratorError):
    """Raised when incoming data fails business-level validation."""
    status_code = 422
    detail = "Data validation failed."


class UnsupportedFileTypeError(ReportGeneratorError):
    """Raised when the uploaded file type is not supported."""
    status_code = 415
    detail = "Unsupported file type."


class DataProcessingError(ReportGeneratorError):
    """Raised when pandas / data processing encounters an error."""
    status_code = 422
    detail = "Failed to process the uploaded data."


class ReportGenerationError(ReportGeneratorError):
    """Raised when report rendering fails."""
    status_code = 500
    detail = "Failed to generate the report."


class FileSizeLimitError(ReportGeneratorError):
    """Raised when an uploaded file exceeds the maximum allowed size."""
    status_code = 413
    detail = "Uploaded file exceeds the maximum allowed size."


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

def register_exception_handlers(app: FastAPI) -> None:
    """Attach global exception handlers to a FastAPI application instance."""

    @app.exception_handler(ReportGeneratorError)
    async def report_generator_error_handler(
        request: Request, exc: ReportGeneratorError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.__class__.__name__, "detail": exc.detail},
        )
