"""
Integration tests for the Report Generator API.

Uses FastAPI's TestClient (synchronous) to exercise the full request
lifecycle: upload → summary → report for both PDF and Excel formats.
"""

import io
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

CSV_CONTENT = (
    "product,revenue,units,region\n"
    "Widget A,15000,300,North\n"
    "Widget B,22000,450,South\n"
    "Widget C,8000,160,North\n"
    "Widget D,31000,620,East\n"
    "Widget E,19500,390,West\n"
)

JSON_CONTENT = json.dumps(
    [
        {"product": "Alpha", "score": 88, "category": "A"},
        {"product": "Beta", "score": 76, "category": "B"},
        {"product": "Gamma", "score": 92, "category": "A"},
    ]
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _upload_csv() -> str:
    """Upload the sample CSV and return its file_id."""
    resp = client.post(
        "/upload/",
        files={"file": ("sales.csv", io.BytesIO(CSV_CONTENT.encode()), "text/csv")},
    )
    assert resp.status_code == 201
    return resp.json()["file_id"]


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_returns_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# POST /upload/
# ---------------------------------------------------------------------------

class TestUpload:
    def test_csv_upload_success(self):
        resp = client.post(
            "/upload/",
            files={"file": ("data.csv", io.BytesIO(CSV_CONTENT.encode()), "text/csv")},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "file_id" in body
        assert body["rows"] == 5
        assert "product" in body["columns"]

    def test_json_upload_success(self):
        resp = client.post(
            "/upload/",
            files={
                "file": (
                    "data.json",
                    io.BytesIO(JSON_CONTENT.encode()),
                    "application/json",
                )
            },
        )
        assert resp.status_code == 201
        assert resp.json()["rows"] == 3

    def test_unsupported_file_type_returns_415(self):
        resp = client.post(
            "/upload/",
            files={"file": ("page.html", io.BytesIO(b"<html/>"), "text/html")},
        )
        assert resp.status_code == 415

    def test_empty_csv_is_accepted(self):
        resp = client.post(
            "/upload/",
            files={
                "file": (
                    "empty.csv",
                    io.BytesIO(b"col1,col2\n"),
                    "text/csv",
                )
            },
        )
        assert resp.status_code == 201
        assert resp.json()["rows"] == 0


# ---------------------------------------------------------------------------
# GET /summary/{file_id}
# ---------------------------------------------------------------------------

class TestSummary:
    def test_summary_returns_correct_columns(self):
        file_id = _upload_csv()
        resp = client.get(f"/summary/{file_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_rows"] == 5
        assert "revenue" in body["numeric_columns"]
        assert "region" in body["categorical_columns"]

    def test_summary_column_stats_present(self):
        file_id = _upload_csv()
        resp = client.get(f"/summary/{file_id}")
        stats = {s["column"]: s for s in resp.json()["column_stats"]}
        assert "revenue" in stats
        assert stats["revenue"]["mean"] is not None

    def test_summary_unknown_file_id_returns_404(self):
        resp = client.get("/summary/does-not-exist")
        assert resp.status_code == 404

    def test_summary_missing_pct_for_no_nulls(self):
        file_id = _upload_csv()
        resp = client.get(f"/summary/{file_id}")
        stats = {s["column"]: s for s in resp.json()["column_stats"]}
        assert stats["product"]["missing_pct"] == 0.0


# ---------------------------------------------------------------------------
# POST /report/
# ---------------------------------------------------------------------------

class TestReport:
    def test_pdf_report_returns_binary(self):
        file_id = _upload_csv()
        resp = client.post(
            "/report/",
            json={"file_id": file_id, "format": "pdf", "title": "Sales Report"},
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert len(resp.content) > 1000  # non-trivial PDF

    def test_excel_report_returns_binary(self):
        file_id = _upload_csv()
        resp = client.post(
            "/report/",
            json={"file_id": file_id, "format": "excel", "title": "Sales Report"},
        )
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers["content-type"]
        assert len(resp.content) > 1000

    def test_report_with_column_subset(self):
        file_id = _upload_csv()
        resp = client.post(
            "/report/",
            json={
                "file_id": file_id,
                "format": "pdf",
                "columns": ["product", "revenue"],
            },
        )
        assert resp.status_code == 200

    def test_report_invalid_column_returns_500(self):
        file_id = _upload_csv()
        resp = client.post(
            "/report/",
            json={
                "file_id": file_id,
                "format": "pdf",
                "columns": ["nonexistent_col"],
            },
        )
        assert resp.status_code == 500

    def test_report_unknown_file_id_returns_404(self):
        resp = client.post(
            "/report/",
            json={"file_id": "ghost-id", "format": "pdf"},
        )
        assert resp.status_code == 404

    def test_report_blank_title_returns_422(self):
        file_id = _upload_csv()
        resp = client.post(
            "/report/",
            json={"file_id": file_id, "format": "pdf", "title": "   "},
        )
        assert resp.status_code == 422
