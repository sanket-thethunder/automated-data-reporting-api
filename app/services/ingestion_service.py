"""
Data Ingestion Service.

Responsible for:
- Validating and persisting uploaded files.
- Parsing CSV / JSON content into pandas DataFrames.
- Storing parsed DataFrames in an in-process registry for downstream use.
"""

from __future__ import annotations

import io
import json
import uuid
from pathlib import Path
from typing import IO

import pandas as pd
from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import (
    DataProcessingError,
    FileSizeLimitError,
    UnsupportedFileTypeError,
)
from app.core.logger import get_logger

logger = get_logger(__name__)

# In-memory registry: file_id → {"df": DataFrame, "filename": str}
_REGISTRY: dict[str, dict] = {}

SUPPORTED_CONTENT_TYPES = {
    "text/csv",
    "application/csv",
    "text/plain",
    "application/json",
    "application/vnd.ms-excel",
}

MAX_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


class DataIngestionService:
    """
    Handles file upload validation, parsing, and in-memory storage.

    All public methods are static/class-level so the service can be used
    without instantiation (stateless request handling).
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    async def ingest(cls, upload: UploadFile) -> tuple[str, pd.DataFrame]:
        """
        Validate, read, and parse an uploaded file.

        Args:
            upload: The :class:`UploadFile` object from FastAPI.

        Returns:
            A tuple of ``(file_id, dataframe)``.

        Raises:
            UnsupportedFileTypeError: If the MIME type is not supported.
            FileSizeLimitError: If the file exceeds MAX_UPLOAD_SIZE_MB.
            DataProcessingError: If parsing fails.
        """
        cls._validate_content_type(upload.content_type, upload.filename)

        raw_bytes = await upload.read()
        cls._validate_size(raw_bytes)

        df = cls._parse(raw_bytes, upload.filename or "upload")

        file_id = str(uuid.uuid4())
        _REGISTRY[file_id] = {"df": df, "filename": upload.filename or "upload"}

        logger.info(
            "Ingested file '%s' → file_id=%s  shape=%s",
            upload.filename,
            file_id,
            df.shape,
        )
        return file_id, df

    @classmethod
    def get_dataframe(cls, file_id: str) -> tuple[pd.DataFrame, str]:
        """
        Retrieve a previously ingested DataFrame.

        Args:
            file_id: The identifier returned by :meth:`ingest`.

        Returns:
            A tuple of ``(dataframe, original_filename)``.

        Raises:
            KeyError: If the file_id is not found in the registry.
        """
        entry = _REGISTRY.get(file_id)
        if entry is None:
            raise KeyError(f"No dataset found for file_id='{file_id}'.")
        return entry["df"], entry["filename"]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_content_type(content_type: str | None, filename: str | None) -> None:
        """Raise UnsupportedFileTypeError if the MIME type is not on the allow-list."""
        # Fall back to extension check when browser sends generic MIME type
        extension = Path(filename or "").suffix.lower()
        allowed_extensions = {".csv", ".json", ".txt"}

        if content_type not in SUPPORTED_CONTENT_TYPES and extension not in allowed_extensions:
            raise UnsupportedFileTypeError(
                f"File type '{content_type}' (extension '{extension}') is not supported. "
                f"Accepted types: CSV, JSON."
            )

    @staticmethod
    def _validate_size(raw_bytes: bytes) -> None:
        """Raise FileSizeLimitError if the byte payload is too large."""
        if len(raw_bytes) > MAX_BYTES:
            raise FileSizeLimitError(
                f"File size {len(raw_bytes) / 1024 / 1024:.1f} MB exceeds the "
                f"{settings.MAX_UPLOAD_SIZE_MB} MB limit."
            )

    @staticmethod
    def _parse(raw_bytes: bytes, filename: str) -> pd.DataFrame:
        """
        Parse raw bytes into a DataFrame based on file extension.

        Args:
            raw_bytes: The raw file content.
            filename: Used to determine file type via extension.

        Returns:
            Parsed :class:`pandas.DataFrame`.

        Raises:
            DataProcessingError: On any parsing failure.
        """
        ext = Path(filename).suffix.lower()
        try:
            if ext == ".json":
                return DataIngestionService._parse_json(raw_bytes)
            else:
                # Default: treat as CSV (also handles .txt, .csv)
                return DataIngestionService._parse_csv(raw_bytes)
        except Exception as exc:
            logger.exception("Failed to parse file '%s'", filename)
            raise DataProcessingError(f"Could not parse file: {exc}") from exc

    @staticmethod
    def _parse_csv(raw_bytes: bytes) -> pd.DataFrame:
        """Parse CSV bytes, trying common encodings automatically."""
        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                text = raw_bytes.decode(encoding)
                df = pd.read_csv(io.StringIO(text))
                df.columns = [str(c).strip() for c in df.columns]
                return df
            except UnicodeDecodeError:
                continue
        raise DataProcessingError("Could not decode the CSV file with supported encodings.")

    @staticmethod
    def _parse_json(raw_bytes: bytes) -> pd.DataFrame:
        """
        Parse JSON bytes.

        Supports:
        - Array of objects: ``[{"a": 1}, {"a": 2}]``
        - Dict with a "data" key: ``{"data": [...]}``
        - Pandas-style record/split orientations.
        """
        try:
            payload = json.loads(raw_bytes.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise DataProcessingError(f"Invalid JSON: {exc}") from exc

        if isinstance(payload, list):
            return pd.DataFrame(payload)
        if isinstance(payload, dict):
            # Try "data" key first, then let pandas handle the rest
            if "data" in payload:
                return pd.DataFrame(payload["data"])
            return pd.DataFrame([payload])

        raise DataProcessingError("JSON must be an array of objects or a dict.")
