"""
Pydantic models for request validation and response serialisation.

Separating I/O schemas from domain logic keeps the codebase clean
and makes the auto-generated Swagger docs accurate and readable.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class ReportFormat(str, Enum):
    """Supported output report formats."""
    PDF = "pdf"
    EXCEL = "excel"


class SortOrder(str, Enum):
    """Column sort direction."""
    ASC = "asc"
    DESC = "desc"


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

class UploadResponse(BaseModel):
    """Response returned after a successful file upload."""

    file_id: str = Field(..., description="Unique identifier for the uploaded dataset.")
    filename: str = Field(..., description="Original filename.")
    rows: int = Field(..., description="Number of data rows detected.")
    columns: list[str] = Field(..., description="List of column names.")
    message: str = Field(default="File uploaded and parsed successfully.")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

class ColumnStat(BaseModel):
    """Descriptive statistics for a single column."""

    column: str
    dtype: str
    count: int
    missing: int
    missing_pct: float = Field(..., description="Percentage of missing values (0–100).")
    # Numeric columns only — None for categorical
    mean: float | None = None
    median: float | None = None
    std: float | None = None
    min: float | None = None
    max: float | None = None
    # Categorical columns only
    unique: int | None = None
    top: Any | None = None
    top_freq: int | None = None


class SummaryResponse(BaseModel):
    """Aggregated summary of an uploaded dataset."""

    file_id: str
    filename: str
    total_rows: int
    total_columns: int
    numeric_columns: list[str]
    categorical_columns: list[str]
    column_stats: list[ColumnStat]


# ---------------------------------------------------------------------------
# Report request
# ---------------------------------------------------------------------------

class ReportRequest(BaseModel):
    """Body payload for the /report endpoint."""

    file_id: str = Field(..., description="file_id returned by /upload.")
    format: ReportFormat = Field(
        default=ReportFormat.PDF,
        description="Desired output format: 'pdf' or 'excel'.",
    )
    title: str = Field(
        default="Data Report",
        max_length=120,
        description="Title printed at the top of the report.",
    )
    include_charts: bool = Field(
        default=True,
        description="Embed bar/histogram charts in the report (PDF only).",
    )
    columns: list[str] | None = Field(
        default=None,
        description="Subset of columns to include. Defaults to all columns.",
    )

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title must not be blank.")
        return v.strip()
