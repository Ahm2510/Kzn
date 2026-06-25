"""
Kaizen Forecasting Service — V1.0

Generates forward-looking revenue projections using linear trend extrapolation
with confidence bands. Schema-agnostic: works with any revenue-like column.

When a date column is detected, uses actual time intervals.
When no date column exists, uses row index as a proxy time axis.

Returns None gracefully on any failure — never blocks the main pipeline.
"""

from __future__ import annotations
import logging
import numpy as np
import pandas as pd
from typing import Optional, List
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Minimum data points required to produce a meaningful forecast
MIN_POINTS_FOR_FORECAST = 4


class ForecastPoint(BaseModel):
    """A single projected data point."""
    period_label: str           # Human-readable label e.g. "Month 4", "Week 12", "2024-Q2"
    projected_value: float      # Point estimate
    lower_bound: float          # 80% confidence lower bound
    upper_bound: float          # 80% confidence upper bound


class ForecastResult(BaseModel):
    """Complete forecast output."""
    forecast_horizon: int                    # Number of periods projected
    granularity: str                         # "daily" | "weekly" | "monthly" | "row_index"
    historical_points: List[ForecastPoint]   # Aggregated historical series used for fit
    projected_points: List[ForecastPoint]    # Future projections
    trend_direction: str                     # "upward" | "downward" | "flat"
    trend_slope: float                       # Revenue change per period
    r_squared: float                         # Goodness of fit (0–1)
    confidence: str                          # "high" | "medium" | "low"
    confidence_reason: str
    explanation: str                         # Plain-English explanation
    warning: Optional[str] = None
    revenue_column_used: str
    date_column_used: Optional[str] = None
    sample_size: int


def _detect_date_column(df: pd.DataFrame) -> Optional[str]:
    """Detect the most likely date column in the dataframe."""
    date_candidates = [
        "date", "order_date", "transaction_date", "created_at", "timestamp",
        "invoice_date", "purchase_date", "sale_date", "period", "month", "week",
    ]
    cols_lower = {col.lower().strip(): col for col in df.columns}
    for c in date_candidates:
        if c in cols_lower:
            return cols_lower[c]
    # Try to detect by dtype
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            return col
    # Try to parse string columns as dates
    for col in df.columns:
        if df[col].dtype == object:
            try:
                sample = df[col].dropna().head(20)
                parsed = pd.to_datetime(sample, errors="coerce", infer_datetime_format=True)
                if parsed.notna().sum() >= len(sample) * 0.8:
                    return col
            except Exception:
                continue
    return None


def _aggregate_by_period(
    df: pd.DataFrame,
    revenue_col: str,
    date_col: str,
    granularity: str,
) -> pd.DataFrame:
    """Aggregate revenue by time period. Returns DataFrame with columns: period, revenue."""
    try:
        df = df.copy()
        df["__date"] = pd.to_datetime(df[date_col], errors="coerce", infer_datetime_format=True)
        df = df.dropna(subset=["__date"])
        df["__revenue"] = pd.to_numeric(df[revenue_col], errors="coerce").fillna(0)

        if granularity == "monthly":
            df["__period"] = df["__date"].dt.to_period("M")
        elif granularity == "weekly":
            df["__period"] = df["__date"].dt.to_period("W")
        else:  # daily
            df["__period"] = df["__date"].dt.to_period("D")

        agg = df.groupby("__period")["__revenue"].sum().reset_index()
        agg.columns = ["period", "revenue"]
        agg = agg.sort_values("period").reset_index(drop=True)
        agg["period_label"] = agg["period"].astype(str)
        return agg
    except Exception as e:
        logger.debug(f"Period aggregation failed: {e}")
        return pd.DataFrame()


def _detect_granularity(df: pd.DataFrame, date_col: str) -> str:
    """Infer appropriate aggregation granularity from date spread."""
    try:
        dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
        if len(dates) < 2:
            return "monthly"
        span_days = (dates.max() - dates.min()).days
        if span_days <= 30:
            return "daily"
        elif span_days <= 180:
            return "weekly"
        else:
            return "monthly"
    except Exception:
        return "monthly"


def _fit_and_project(
    values: np.ndarray,
    n_forecast: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
    """
    Fit OLS linear regression and project forward.
    Returns: (fitted, lower, upper, slope, r_squared)
    """
    n = len(values)
    x = np.arange(n, dtype=float)
    x_forecast = np.arange(n, n + n_forecast, dtype=float)

    # OLS fit
    coeffs = np.polyfit(x, values, 1)
    slope = coeffs[0]
    intercept = coeffs[1]

    fitted = slope * x + intercept
    projected = slope * x_forecast + intercept

    # R-squared
    ss_res = np.sum((values - fitted) ** 2)
    ss_tot = np.sum((values - values.mean()) ** 2)
    r_squared = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0
    r_squared = max(0.0, min(1.0, r_squared))

    # Residual standard error for confidence bands (80% CI)
    residuals = values - fitted
    se = np.std(residuals, ddof=2) if n > 2 else np.std(residuals)
    # 1.28 = z-score for 80% CI
    margin = 1.28 * se * np.sqrt(1 + 1 / n + (x_forecast - x.mean()) ** 2 / np.sum((x - x.mean()) ** 2 + 1e-10))

    lower = projected - margin
    upper = projected + margin

    return projected, lower, upper, float(slope), r_squared


def compute_forecast(
    current_df: pd.DataFrame,
    revenue_column: str,
    forecast_horizon: int = 3,
) -> Optional[ForecastResult]:
    """
    Main entry point. Computes a revenue forecast for the next `forecast_horizon` periods.

    Args:
        current_df: Preprocessed current dataset DataFrame
        revenue_column: Detected revenue column name
        forecast_horizon: Number of future periods to project (default: 3)

    Returns:
        ForecastResult or None if insufficient data
    """
    try:
        df = current_df.copy()
        date_col = _detect_date_column(df)
        revenue_col = revenue_column

        if date_col:
            granularity = _detect_granularity(df, date_col)
            agg = _aggregate_by_period(df, revenue_col, date_col, granularity)

            if len(agg) < MIN_POINTS_FOR_FORECAST:
                # Fall back to row-index mode
                date_col = None

        if not date_col:
            # Row-index mode: chunk rows into N equal buckets
            granularity = "row_index"
            df["__revenue"] = pd.to_numeric(df[revenue_col], errors="coerce").fillna(0)
            n_chunks = min(12, max(MIN_POINTS_FOR_FORECAST, len(df) // 100))
            df["__chunk"] = pd.cut(df.index, bins=n_chunks, labels=False)
            agg = df.groupby("__chunk")["__revenue"].sum().reset_index()
            agg.columns = ["period", "revenue"]
            agg["period_label"] = [f"Period {int(i) + 1}" for i in agg["period"]]

        if len(agg) < MIN_POINTS_FOR_FORECAST:
            return None

        values = agg["revenue"].values.astype(float)
        labels = agg["period_label"].tolist()
        n = len(values)

        projected, lower, upper, slope, r_squared = _fit_and_project(values, forecast_horizon)

        # Build historical points (fitted line through actuals)
        x = np.arange(n, dtype=float)
        fitted_vals = slope * x + (values.mean() - slope * x.mean())  # same intercept
        # Use actual values for historical display, not fitted
        historical_points = [
            ForecastPoint(
                period_label=labels[i],
                projected_value=round(float(values[i]), 2),
                lower_bound=round(float(values[i]), 2),  # No uncertainty for actuals
                upper_bound=round(float(values[i]), 2),
            )
            for i in range(n)
        ]

        # Build forecast period labels
        def _next_label(last_label: str, idx: int, gran: str) -> str:
            if gran == "row_index":
                return f"Period {n + idx + 1}"
            try:
                import re
                # Try to increment period string for monthly/weekly/daily
                p = pd.Period(last_label)
                return str(p + idx + 1)
            except Exception:
                return f"Period {n + idx + 1}"

        last_label = labels[-1]
        projected_points = [
            ForecastPoint(
                period_label=_next_label(last_label, i, granularity),
                projected_value=round(float(projected[i]), 2),
                lower_bound=round(float(max(0, lower[i])), 2),
                upper_bound=round(float(upper[i]), 2),
            )
            for i in range(forecast_horizon)
        ]

        # Trend direction
        mean_rev = float(values.mean()) if values.mean() != 0 else 1.0
        slope_pct = (slope / mean_rev) * 100
        if slope_pct > 2:
            trend_direction = "upward"
        elif slope_pct < -2:
            trend_direction = "downward"
        else:
            trend_direction = "flat"

        # Confidence
        if r_squared >= 0.7 and n >= 8:
            confidence = "high"
            confidence_reason = f"Strong linear fit (R²={r_squared:.2f}) across {n} periods"
        elif r_squared >= 0.4 or n >= 5:
            confidence = "medium"
            confidence_reason = f"Moderate fit (R²={r_squared:.2f}) across {n} periods"
        else:
            confidence = "low"
            confidence_reason = f"Weak fit (R²={r_squared:.2f}) — high volatility limits projection accuracy"

        # Plain-English explanation
        direction_word = "grow" if trend_direction == "upward" else ("decline" if trend_direction == "downward" else "remain flat")
        next_val = projected_points[0].projected_value if projected_points else 0
        explanation = (
            f"Based on {n} historical {'periods' if granularity != 'row_index' else 'data segments'}, "
            f"revenue is projected to {direction_word} over the next {forecast_horizon} period(s). "
            f"The next period projects at ${next_val:,.0f} "
            f"(range: ${projected_points[0].lower_bound:,.0f}–${projected_points[0].upper_bound:,.0f})."
        ) if projected_points else "Insufficient data for projection."

        warning = None
        if r_squared < 0.3:
            warning = "Revenue is highly volatile — treat this projection as directional only, not a precise forecast."
        if granularity == "row_index":
            warning = (warning or "") + " No date column detected — projection uses row segments as a time proxy."

        return ForecastResult(
            forecast_horizon=forecast_horizon,
            granularity=granularity,
            historical_points=historical_points,
            projected_points=projected_points,
            trend_direction=trend_direction,
            trend_slope=round(slope, 2),
            r_squared=round(r_squared, 4),
            confidence=confidence,
            confidence_reason=confidence_reason,
            explanation=explanation,
            warning=warning.strip() if warning else None,
            revenue_column_used=revenue_column,
            date_column_used=date_col,
            sample_size=n,
        )

    except Exception as e:
        logger.warning(f"Forecasting failed: {e}", exc_info=True)
        return None
