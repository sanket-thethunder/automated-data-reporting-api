"""
Analytics Service.

Computes descriptive statistics from a pandas DataFrame and returns
structured :class:`~app.models.schemas.SummaryResponse` objects.
"""

from __future__ import annotations

import math

import pandas as pd

from app.core.logger import get_logger
from app.models.schemas import ColumnStat, SummaryResponse

logger = get_logger(__name__)


class AnalyticsService:
    """
    Stateless service that computes summary statistics for a DataFrame.

    All methods are class-level — no instance state is required.
    """

    @classmethod
    def summarise(cls, file_id: str, filename: str, df: pd.DataFrame) -> SummaryResponse:
        """
        Build a full :class:`SummaryResponse` for the given DataFrame.

        Args:
            file_id: Identifier of the dataset (echoed back in the response).
            filename: Original filename (echoed back in the response).
            df: The DataFrame to analyse.

        Returns:
            A :class:`SummaryResponse` instance ready for serialisation.
        """
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        categorical_cols = [c for c in df.columns if c not in numeric_cols]

        stats = [cls._column_stat(df, col) for col in df.columns]

        logger.info(
            "Summarised file_id=%s  rows=%d  cols=%d",
            file_id,
            len(df),
            len(df.columns),
        )

        return SummaryResponse(
            file_id=file_id,
            filename=filename,
            total_rows=len(df),
            total_columns=len(df.columns),
            numeric_columns=numeric_cols,
            categorical_columns=categorical_cols,
            column_stats=stats,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @classmethod
    def _column_stat(cls, df: pd.DataFrame, col: str) -> ColumnStat:
        """
        Compute per-column statistics.

        Numeric columns receive mean/median/std/min/max.
        Categorical columns receive unique count and the most frequent value.
        """
        series = df[col]
        total = len(series)
        missing = int(series.isna().sum())

        base = dict(
            column=col,
            dtype=str(series.dtype),
            count=total - missing,
            missing=missing,
            missing_pct=round(missing / total * 100, 2) if total else 0.0,
        )

        if pd.api.types.is_numeric_dtype(series):
            desc = series.dropna().describe()
            return ColumnStat(
                **base,
                mean=cls._safe_float(desc.get("mean")),
                median=cls._safe_float(series.median()),
                std=cls._safe_float(desc.get("std")),
                min=cls._safe_float(desc.get("min")),
                max=cls._safe_float(desc.get("max")),
            )
        else:
            value_counts = series.value_counts()
            top = value_counts.index[0] if len(value_counts) else None
            top_freq = int(value_counts.iloc[0]) if len(value_counts) else None
            return ColumnStat(
                **base,
                unique=int(series.nunique()),
                top=str(top) if top is not None else None,
                top_freq=top_freq,
            )

    @staticmethod
    def _safe_float(value) -> float | None:
        """Convert a value to float, returning None for NaN / inf."""
        try:
            f = float(value)
            return None if math.isnan(f) or math.isinf(f) else round(f, 4)
        except (TypeError, ValueError):
            return None
