"""
Outstanding Payments / Receivables Risk (V1 — Additive, distribution niche)

Distributors live and die by collections: capital is locked up in credit
extended to hundreds of retail shops. This dimension does not exist anywhere
else in the engine, so this is a new, self-contained module.

It mirrors the conventions of the other additive analytics modules
(``customer_segments.py``, ``concentration_risk.py``): a pydantic result model
and a ``compute_*`` entry point that returns ``Optional[...]`` and never raises.

Graceful degradation is mandatory: if no outstanding / receivable column is
detected, the module returns ``None`` (a no-op) — the caller omits the section
and the missing column is surfaced via ``schema_warnings`` upstream.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd
from pydantic import BaseModel

from app.services.insight_engine.entity_detector import (
    detect_customer_column,
    detect_date_column,
    detect_outstanding_column,
    format_inr,
    format_inr_lakh,
)


# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────

class ReceivableCustomer(BaseModel):
    customer: str
    outstanding: float
    share_pct: float
    aging_bucket: Optional[str] = None     # "0-45" | "45-60" | "60-90" | "90+"
    oldest_unpaid_days: Optional[int] = None
    explanation: Optional[str] = None


class ReceivablesRiskResult(BaseModel):
    customers: List[ReceivableCustomer] = []   # ranked by outstanding desc
    total_outstanding: float = 0.0
    customer_count: int = 0
    aging_available: bool = False
    over_45_amount: float = 0.0
    over_60_amount: float = 0.0
    over_90_amount: float = 0.0
    over_45_customer_count: int = 0
    confidence: str = "medium"
    warning: Optional[str] = None
    headline_action: Optional[str] = None      # imperative one-liner for the action list


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _resolve_columns(
    df: pd.DataFrame,
    schema: Optional[Dict[str, Optional[str]]],
) -> Dict[str, Optional[str]]:
    out_col = schema.get("outstanding_col") if schema else None
    cust_col = schema.get("customer_col") if schema else None
    date_col = schema.get("date_col") if schema else None
    if not out_col:
        out_col, _c, _m = detect_outstanding_column(df)
    if not cust_col:
        cust_col, _c, _m = detect_customer_column(df)
    if not date_col:
        date_col, _c, _m = detect_date_column(df)
    return {"outstanding_col": out_col, "customer_col": cust_col, "date_col": date_col}


def _confidence(customer_count: int, row_count: int) -> str:
    if customer_count >= 20 and row_count >= 100:
        return "high"
    if customer_count >= 8 or row_count >= 50:
        return "medium"
    return "low"


def _bucket(days: Optional[int]) -> Optional[str]:
    if days is None:
        return None
    if days >= 90:
        return "90+"
    if days >= 60:
        return "60-90"
    if days >= 45:
        return "45-60"
    return "0-45"


TOP_N = 10


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

def compute_receivables_risk(
    current_df: pd.DataFrame,
    schema: Optional[Dict[str, Optional[str]]] = None,
) -> Optional[ReceivablesRiskResult]:
    """
    Summarize outstanding receivables and aging risk.

    Returns ``None`` (graceful no-op) when no outstanding/receivable column is
    present — the section is simply omitted and flagged in ``schema_warnings``.
    Never raises.
    """
    try:
        cols = _resolve_columns(current_df, schema)
        out_col = cols["outstanding_col"]
        cust_col = cols["customer_col"]
        date_col = cols["date_col"]

        if not out_col:
            # No receivables dimension in this dataset — omit silently.
            return None

        if not cust_col:
            return ReceivablesRiskResult(
                warning="Outstanding amounts found but no customer column; cannot attribute receivables.",
                confidence="low",
            )

        df = current_df[[c for c in {cust_col, out_col, date_col} if c]].copy()
        df[out_col] = pd.to_numeric(df[out_col], errors="coerce")
        df = df.dropna(subset=[cust_col, out_col])
        # Only positive balances represent money owed to the distributor.
        df = df[df[out_col] > 0]
        if df.empty:
            return ReceivablesRiskResult(
                warning="No positive outstanding balances detected.",
                confidence="low",
            )

        df[cust_col] = df[cust_col].astype(str)

        # Aging: if a date column exists, treat each unpaid row's age relative to
        # the dataset's latest date as the proxy for how long the balance is overdue.
        aging_available = False
        row_age_days: Optional[pd.Series] = None
        if date_col and date_col in df.columns:
            parsed = pd.to_datetime(df[date_col], errors="coerce")
            if parsed.notna().sum() > 0:
                ref = parsed.max()
                row_age_days = (ref - parsed).dt.days
                aging_available = True

        per_cust = df.groupby(cust_col)[out_col].sum().sort_values(ascending=False)
        total_outstanding = float(per_cust.sum())
        customer_count = int(per_cust.shape[0])

        # Per-customer oldest unpaid age, for bucket labelling.
        oldest_age: Dict[str, Optional[int]] = {}
        if aging_available and row_age_days is not None:
            age_df = df.assign(__age=row_age_days)
            grouped_age = age_df.groupby(cust_col)["__age"].max()
            for cust, age in grouped_age.items():
                oldest_age[cust] = int(age) if pd.notna(age) else None

        # Aging rollups (amount that is over 45 / 60 / 90 days).
        over_45 = over_60 = over_90 = 0.0
        over_45_customers = 0
        if aging_available and row_age_days is not None:
            amounts = df[out_col].values
            ages = row_age_days.values
            for amt, age in zip(amounts, ages):
                if pd.isna(age):
                    continue
                if age >= 45:
                    over_45 += float(amt)
                if age >= 60:
                    over_60 += float(amt)
                if age >= 90:
                    over_90 += float(amt)
            for cust, age in oldest_age.items():
                if age is not None and age >= 45:
                    over_45_customers += 1

        customers: List[ReceivableCustomer] = []
        for cust, amount in per_cust.head(TOP_N).items():
            share = (float(amount) / total_outstanding * 100.0) if total_outstanding > 0 else 0.0
            age = oldest_age.get(cust)
            bucket = _bucket(age)
            explanation = _build_explanation(cust, float(amount), age, bucket)
            customers.append(ReceivableCustomer(
                customer=cust[:80],
                outstanding=round(float(amount), 2),
                share_pct=round(share, 1),
                aging_bucket=bucket,
                oldest_unpaid_days=age,
                explanation=explanation,
            ))

        headline = _build_headline_action(
            total_outstanding, customer_count, over_45, over_45_customers, aging_available,
        )

        return ReceivablesRiskResult(
            customers=customers,
            total_outstanding=round(total_outstanding, 2),
            customer_count=customer_count,
            aging_available=aging_available,
            over_45_amount=round(over_45, 2),
            over_60_amount=round(over_60, 2),
            over_90_amount=round(over_90, 2),
            over_45_customer_count=over_45_customers,
            confidence=_confidence(customer_count, len(df)),
            warning=None,
            headline_action=headline,
        )
    except Exception:
        return None


def _build_explanation(
    cust: str, amount: float, age: Optional[int], bucket: Optional[str],
) -> str:
    amt_str = format_inr(amount)
    if bucket and age is not None and age >= 45:
        return f"'{cust}' owes {amt_str}, with the oldest unpaid bill ~{age} days old ({bucket} day bucket)."
    if age is not None:
        return f"'{cust}' owes {amt_str}; oldest unpaid bill ~{age} days old."
    return f"'{cust}' owes {amt_str} outstanding."


def _build_headline_action(
    total_outstanding: float,
    customer_count: int,
    over_45: float,
    over_45_customers: int,
    aging_available: bool,
) -> Optional[str]:
    if total_outstanding <= 0:
        return None
    total_str = format_inr_lakh(total_outstanding)
    if aging_available and over_45 > 0 and over_45_customers > 0:
        over_str = format_inr_lakh(over_45)
        return (
            f"{over_45_customers} customer(s) are over 45 days late on {over_str} combined — "
            f"make these your priority collection calls ({total_str} outstanding in total)."
        )
    return (
        f"{total_str} is outstanding across {customer_count} customer(s) — "
        f"prioritise collection on the largest balances."
    )
