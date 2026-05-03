"""
Unit tests for DataIngestionService.

Tests cover CSV/JSON parsing, encoding handling, size validation,
and unsupported file type rejection — all without touching the filesystem.
"""

import io
import json

import pytest
from fastapi import UploadFile
from unittest.mock import AsyncMock, MagicMock

from app.core.exceptions import (
    DataProcessingError,
    FileSizeLimitError,
    UnsupportedFileTypeError,
)
from app.services.ingestion_service import DataIngestionService


def _make_upload(content: bytes, filename: str, content_type: str) -> UploadFile:
    """Helper: construct a mock UploadFile from raw bytes."""
    mock = MagicMock(spec=UploadFile)
    mock.filename = filename
    mock.content_type = content_type
    mock.read = AsyncMock(return_value=content)
    return mock


CSV_BYTES = b"name,age,city\nAlice,30,Mumbai\nBob,25,Delhi\n"

JSON_BYTES = json.dumps(
    [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
).encode()


class TestDataIngestionService:
    """Tests for DataIngestionService.ingest."""

    @pytest.mark.anyio
    async def test_csv_ingestion_returns_correct_shape(self):
        upload = _make_upload(CSV_BYTES, "data.csv", "text/csv")
        file_id, df = await DataIngestionService.ingest(upload)
        assert df.shape == (2, 3)
        assert "name" in df.columns

    @pytest.mark.anyio
    async def test_json_ingestion_returns_correct_shape(self):
        upload = _make_upload(JSON_BYTES, "data.json", "application/json")
        file_id, df = await DataIngestionService.ingest(upload)
        assert df.shape == (2, 2)

    @pytest.mark.anyio
    async def test_ingest_stores_in_registry(self):
        upload = _make_upload(CSV_BYTES, "reg.csv", "text/csv")
        file_id, _ = await DataIngestionService.ingest(upload)
        df2, fname = DataIngestionService.get_dataframe(file_id)
        assert fname == "reg.csv"
        assert len(df2) == 2

    @pytest.mark.anyio
    async def test_unsupported_file_type_raises(self):
        upload = _make_upload(b"<html/>", "page.html", "text/html")
        with pytest.raises(UnsupportedFileTypeError):
            await DataIngestionService.ingest(upload)

    @pytest.mark.anyio
    async def test_file_too_large_raises(self, monkeypatch):
        monkeypatch.setattr(
            "app.services.ingestion_service.MAX_BYTES", 10
        )
        upload = _make_upload(CSV_BYTES, "big.csv", "text/csv")
        with pytest.raises(FileSizeLimitError):
            await DataIngestionService.ingest(upload)

    @pytest.mark.anyio
    async def test_invalid_json_raises(self):
        upload = _make_upload(b"{not valid json", "bad.json", "application/json")
        with pytest.raises(DataProcessingError):
            await DataIngestionService.ingest(upload)

    def test_get_dataframe_missing_id_raises(self):
        with pytest.raises(KeyError):
            DataIngestionService.get_dataframe("nonexistent-id")

    @pytest.mark.anyio
    async def test_csv_with_latin1_encoding(self):
        latin1_csv = "name,city\nMüller,Berlin\nGarçon,Paris\n".encode("latin-1")
        upload = _make_upload(latin1_csv, "latin.csv", "text/csv")
        _, df = await DataIngestionService.ingest(upload)
        assert len(df) == 2

    @pytest.mark.anyio
    async def test_json_with_data_key(self):
        payload = json.dumps({"data": [{"x": 1}, {"x": 2}]}).encode()
        upload = _make_upload(payload, "nested.json", "application/json")
        _, df = await DataIngestionService.ingest(upload)
        assert list(df.columns) == ["x"]
        assert len(df) == 2
