"""
Unit tests for AnalyticsService.

These tests exercise the summarise() method with controlled DataFrames
and verify that statistics are computed correctly.
"""

import math

import pandas as pd
import pytest

from app.services.analytics_service import AnalyticsService


@pytest.fixture()
def simple_df() -> pd.DataFrame:
    """A small DataFrame with one numeric and one categorical column."""
    return pd.DataFrame(
        {
            "age": [25, 30, 35, 40, None],
            "city": ["Mumbai", "Delhi", "Mumbai", "Chennai", "Mumbai"],
        }
    )


class TestAnalyticsService:
    """Tests for AnalyticsService.summarise."""

    def test_returns_correct_row_count(self, simple_df):
        result = AnalyticsService.summarise("id-1", "test.csv", simple_df)
        assert result.total_rows == 5

    def test_returns_correct_column_count(self, simple_df):
        result = AnalyticsService.summarise("id-1", "test.csv", simple_df)
        assert result.total_columns == 2

    def test_numeric_and_categorical_split(self, simple_df):
        result = AnalyticsService.summarise("id-1", "test.csv", simple_df)
        assert "age" in result.numeric_columns
        assert "city" in result.categorical_columns

    def test_numeric_stat_mean(self, simple_df):
        result = AnalyticsService.summarise("id-1", "test.csv", simple_df)
        age_stat = next(s for s in result.column_stats if s.column == "age")
        # Mean of [25, 30, 35, 40] = 32.5
        assert age_stat.mean == pytest.approx(32.5, rel=1e-3)

    def test_numeric_stat_missing(self, simple_df):
        result = AnalyticsService.summarise("id-1", "test.csv", simple_df)
        age_stat = next(s for s in result.column_stats if s.column == "age")
        assert age_stat.missing == 1
        assert age_stat.missing_pct == pytest.approx(20.0, rel=1e-3)

    def test_categorical_top_value(self, simple_df):
        result = AnalyticsService.summarise("id-1", "test.csv", simple_df)
        city_stat = next(s for s in result.column_stats if s.column == "city")
        assert city_stat.top == "Mumbai"
        assert city_stat.top_freq == 3

    def test_all_missing_column(self):
        df = pd.DataFrame({"x": [None, None, None]})
        result = AnalyticsService.summarise("id-2", "empty.csv", df)
        x_stat = result.column_stats[0]
        assert x_stat.missing == 3
        assert x_stat.missing_pct == 100.0

    def test_empty_dataframe(self):
        df = pd.DataFrame({"a": pd.Series([], dtype=float)})
        result = AnalyticsService.summarise("id-3", "empty.csv", df)
        assert result.total_rows == 0

    def test_safe_float_returns_none_for_nan(self):
        assert AnalyticsService._safe_float(float("nan")) is None

    def test_safe_float_returns_none_for_inf(self):
        assert AnalyticsService._safe_float(float("inf")) is None

    def test_safe_float_rounds_to_4_decimals(self):
        assert AnalyticsService._safe_float(3.141592653) == 3.1416
