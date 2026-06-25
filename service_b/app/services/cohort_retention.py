"""
Kaizen Cohort Retention Analysis — V1.0

Computes customer retention cohorts. Requires customer_id and date columns.
Returns None silently when prerequisites are missing.
Never blocks the main pipeline.
"""

from __future__ import annotations
import logging
import pandas as pd
import numpy as np
from typing import Optional, List, Dict
from pydantic import BaseModel

logger = logging.getLogger(__name__)

MIN_CUSTOMERS_FOR_COHORT = 20
MIN_PERIODS_FOR_COHORT = 2


class CohortRow(BaseModel):
    cohort_label: str           # e.g. "2024-01"
    cohort_size: int            # Customers acquired in this cohort
    periods: List[float]        # Retention % per subsequent period (index 0 = acquisition period = 100)
    period_labels: List[str]    # e.g. ["Month 0", "Month 1", "Month 2"]


class RetentionSummary(BaseModel):
    overall_retention_rate: float       # % of customers who made repeat purchase
    avg_orders_per_customer: float
    single_purchase_customers_pct: float
    repeat_purchase_rate: float         # % of customers with 2+ orders
    best_cohort: Optional[str] = None
    worst_cohort: Optional[str] = None
    cohort_trend: str                   # "improving" | "stable" | "declining"
    at_risk_cohorts: List[str]          # Cohorts with retention < 20% by month 2


class CohortRetentionResult(BaseModel):
    cohort_table: List[CohortRow]
    summary: RetentionSummary
    customer_column_used: str
    date_column_used: str
    revenue_column_used: str
    total_customers: int
    total_cohorts: int
    analysis_granularity: str           # "monthly" | "weekly"
    confidence: str
    confidence_reason: str
    explanation: str
    warning: Optional[str] = None
    has_sufficient_history: bool
    sample_size: int


def _detect_customer_column(df: pd.DataFrame) -> Optional[str]:
    candidates = [
        "customer_id", "customer", "client_id", "user_id", "account_id",
        "buyer_id", "shopper_id", "member_id", "contact_id",
    ]
    cols_lower = {col.lower().strip(): col for col in df.columns}
    for c in candidates:
        if c in cols_lower:
            return cols_lower[c]
    return None


def _detect_date_col(df: pd.DataFrame) -> Optional[str]:
    candidates = [
        "date", "order_date", "transaction_date", "created_at", "timestamp",
        "invoice_date", "purchase_date", "sale_date",
    ]
    cols_lower = {col.lower().strip(): col for col in df.columns}
    for c in candidates:
        if c in cols_lower:
            return cols_lower[c]
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            return col
    return None


def compute_cohort_retention(
    current_df: pd.DataFrame,
    revenue_column: str,
) -> Optional[CohortRetentionResult]:
    """
    Main entry point. Returns None if customer_id or date column not found.
    """
    try:
        customer_col = _detect_customer_column(current_df)
        date_col = _detect_date_col(current_df)

        if customer_col is None or date_col is None:
            return None

        df = current_df[[customer_col, date_col, revenue_column]].copy()
        df["__customer"] = df[customer_col].astype(str)
        df["__date"] = pd.to_datetime(df[date_col], errors="coerce", infer_datetime_format=True)
        df["__revenue"] = pd.to_numeric(df[revenue_column], errors="coerce")
        df = df.dropna(subset=["__customer", "__date"])
        df = df[df["__customer"].str.strip() != ""]

        total_customers = df["__customer"].nunique()

        if total_customers < MIN_CUSTOMERS_FOR_COHORT:
            return None

        # Determine granularity
        span_days = (df["__date"].max() - df["__date"].min()).days
        granularity = "weekly" if span_days <= 60 else "monthly"
        freq = "M" if granularity == "monthly" else "W"

        # Assign cohort (acquisition period = first purchase period)
        df["__period"] = df["__date"].dt.to_period(freq)
        first_purchase = df.groupby("__customer")["__period"].min().reset_index()
        first_purchase.columns = ["__customer", "__cohort"]
        df = df.merge(first_purchase, on="__customer")

        df["__period_num"] = (df["__period"] - df["__cohort"]).apply(lambda x: x.n if hasattr(x, 'n') else int(x))
        df = df[df["__period_num"] >= 0]

        periods_available = sorted(df["__period_num"].unique())
        if len(periods_available) < MIN_PERIODS_FOR_COHORT:
            return None

        max_period = min(int(df["__period_num"].max()), 6)  # Cap at 6 periods to keep table readable

        # Build cohort table
        cohorts = sorted(df["__cohort"].unique())
        cohort_rows = []

        retention_by_cohort: Dict[str, List[float]] = {}

        for cohort in cohorts:
            cohort_df = df[df["__cohort"] == cohort]
            acquired = cohort_df["__customer"].nunique()

            if acquired < 5:
                continue

            period_labels = [f"Period {i}" for i in range(max_period + 1)]
            retention_pcts = []
            for p in range(max_period + 1):
                retained = cohort_df[cohort_df["__period_num"] == p]["__customer"].nunique()
                pct = round((retained / acquired) * 100, 1)
                retention_pcts.append(pct)

            cohort_label = str(cohort)
            cohort_rows.append(CohortRow(
                cohort_label=cohort_label,
                cohort_size=acquired,
                periods=retention_pcts,
                period_labels=period_labels,
            ))
            retention_by_cohort[cohort_label] = retention_pcts

        if not cohort_rows:
            return None

        # Summary stats
        orders_per_customer = df.groupby("__customer")["__period"].count()
        repeat_customers = int((orders_per_customer >= 2).sum())
        repeat_purchase_rate = round((repeat_customers / total_customers) * 100, 1)
        avg_orders = round(float(orders_per_customer.mean()), 2)
        single_pct = round(((orders_per_customer == 1).sum() / total_customers) * 100, 1)

        # Period-1 retention rate (month 1 retention) across all cohorts
        p1_rates = [row.periods[1] for row in cohort_rows if len(row.periods) > 1]
        overall_retention = round(float(np.mean(p1_rates)), 1) if p1_rates else 0.0

        # Best/worst cohort by period-1 retention
        if p1_rates:
            p1_by_cohort = {row.cohort_label: row.periods[1] for row in cohort_rows if len(row.periods) > 1}
            best_cohort = max(p1_by_cohort, key=lambda k: p1_by_cohort[k]) if p1_by_cohort else None
            worst_cohort = min(p1_by_cohort, key=lambda k: p1_by_cohort[k]) if p1_by_cohort else None
        else:
            best_cohort = worst_cohort = None

        # At-risk cohorts: period-1 retention < 20%
        at_risk = [
            row.cohort_label for row in cohort_rows
            if len(row.periods) > 1 and row.periods[1] < 20
        ]

        # Cohort trend: compare first half vs second half of cohorts
        mid = len(p1_rates) // 2
        if mid > 0 and len(p1_rates) >= 4:
            first_half_avg = np.mean(p1_rates[:mid])
            second_half_avg = np.mean(p1_rates[mid:])
            diff = second_half_avg - first_half_avg
            cohort_trend = "improving" if diff > 3 else ("declining" if diff < -3 else "stable")
        else:
            cohort_trend = "stable"

        # Confidence
        n_cohorts = len(cohort_rows)
        if n_cohorts >= 4 and total_customers >= 100:
            confidence = "high"
            confidence_reason = f"{n_cohorts} cohorts · {total_customers:,} customers"
        elif n_cohorts >= 2:
            confidence = "medium"
            confidence_reason = f"{n_cohorts} cohorts — more history improves accuracy"
        else:
            confidence = "low"
            confidence_reason = "Limited cohort data"

        # Explanation
        explanation = (
            f"Analyzed {total_customers:,} customers across {n_cohorts} cohorts. "
            f"Repeat purchase rate: {repeat_purchase_rate}%. "
            f"Average period-1 retention: {overall_retention}%. "
        )
        if cohort_trend == "improving":
            explanation += "Retention is trending upward — recent cohorts retain customers better."
        elif cohort_trend == "declining":
            explanation += "Retention is declining — recent cohorts are not returning at the same rate as earlier ones."
        else:
            explanation += "Retention is broadly stable across cohorts."

        has_sufficient_history = len(cohort_rows) >= 3 and max_period >= 2

        warning = None
        if repeat_purchase_rate < 20:
            warning = f"Only {repeat_purchase_rate}% of customers made a repeat purchase — strong acquisition is not translating to retention."
        if at_risk and len(at_risk) > 0:
            w2 = f"{len(at_risk)} cohort(s) show <20% period-1 retention."
            warning = (warning + " " + w2) if warning else w2

        summary = RetentionSummary(
            overall_retention_rate=overall_retention,
            avg_orders_per_customer=avg_orders,
            single_purchase_customers_pct=single_pct,
            repeat_purchase_rate=repeat_purchase_rate,
            best_cohort=best_cohort,
            worst_cohort=worst_cohort,
            cohort_trend=cohort_trend,
            at_risk_cohorts=at_risk,
        )

        return CohortRetentionResult(
            cohort_table=cohort_rows,
            summary=summary,
            customer_column_used=customer_col,
            date_column_used=date_col,
            revenue_column_used=revenue_column,
            total_customers=total_customers,
            total_cohorts=n_cohorts,
            analysis_granularity=granularity,
            confidence=confidence,
            confidence_reason=confidence_reason,
            explanation=explanation,
            warning=warning,
            has_sufficient_history=has_sufficient_history,
            sample_size=len(df),
        )

    except Exception as e:
        logger.warning(f"Cohort retention failed: {e}", exc_info=True)
        return None
