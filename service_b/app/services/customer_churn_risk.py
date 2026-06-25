"""
Customer / Shop Churn & Risk Detection (V1 — Additive, distribution niche)

For an FMCG / pharma / auto-parts distributor, the single highest-value insight
is knowing which retail shops have gone quiet. A shop that used to order every
two weeks and hasn't ordered in two months is silent revenue leakage.

This module is deterministic and additive — it mirrors the shape and
defensive style of ``customer_segments.py`` and ``early_warnings.py``:

  * a pydantic result model,
  * a ``compute_*`` entry point that returns ``Optional[...]`` and never raises,
  * internal column self-detection (with the option to receive an already
    resolved distribution schema so the whole pipeline shares one detection
    pass).

For every customer it derives the historical order cadence from the *actual*
transaction dates (no assumed fixed cadence), how long they have been silent,
and a churn risk flag, then ranks by the revenue now at risk so the output reads
"highest-revenue customers who have gone quiet" rather than a flat list.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel

from app.services.insight_engine.entity_detector import (
    detect_customer_column,
    detect_date_column,
    format_inr,
    format_inr_lakh,
)


# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────

class ChurnCustomer(BaseModel):
    customer: str
    risk: str                       # "churned" | "at_risk" | "active"
    order_count: int
    days_since_last_order: int
    avg_gap_days: Optional[float] = None
    last_order_date: Optional[str] = None
    total_revenue: float
    revenue_share_pct: float
    explanation: str


class CustomerChurnRiskResult(BaseModel):
    customers: List[ChurnCustomer] = []   # ranked: at-risk/churned first, by revenue
    total_customers: int = 0
    at_risk_count: int = 0
    churned_count: int = 0
    revenue_at_risk: float = 0.0          # revenue of at-risk + churned customers
    revenue_at_risk_pct: float = 0.0
    has_at_risk: bool = False
    basis: str = ""
    confidence: str = "medium"
    warning: Optional[str] = None
    headline_action: Optional[str] = None  # imperative one-liner for the action list


# ─────────────────────────────────────────────
# Column detection helpers (self-detect or accept a resolved schema)
# ─────────────────────────────────────────────

def _resolve_columns(
    df: pd.DataFrame,
    schema: Optional[Dict[str, Optional[str]]],
) -> Dict[str, Optional[str]]:
    cust_col = schema.get("customer_col") if schema else None
    date_col = schema.get("date_col") if schema else None
    if not cust_col:
        cust_col, _conf, _mode = detect_customer_column(df)
    if not date_col:
        date_col, _conf, _mode = detect_date_column(df)
    return {"customer_col": cust_col, "date_col": date_col}


def _confidence(cust_count: int, txn_count: int) -> str:
    if cust_count >= 20 and txn_count >= 100:
        return "high"
    if cust_count >= 8 or txn_count >= 50:
        return "medium"
    return "low"


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

MIN_CUSTOMERS = 3
TOP_N = 10


def compute_customer_churn_risk(
    current_df: pd.DataFrame,
    revenue_column: str,
    schema: Optional[Dict[str, Optional[str]]] = None,
) -> Optional[CustomerChurnRiskResult]:
    """
    Detect customers (shops) that have gone quiet.

    Returns ``None`` only on an unexpected error. Returns a result carrying a
    ``warning`` when the data is structurally insufficient (no customer column,
    no usable dates, too few customers).
    """
    try:
        cols = _resolve_columns(current_df, schema)
        cust_col = cols["customer_col"]
        date_col = cols["date_col"]

        if not cust_col:
            return CustomerChurnRiskResult(
                warning="No customer / party / shop column detected; churn analysis not applicable.",
                confidence="low",
            )

        if not date_col:
            return CustomerChurnRiskResult(
                warning="No transaction date column detected; cannot compute order cadence or churn timing.",
                confidence="low",
            )

        if revenue_column not in current_df.columns:
            return CustomerChurnRiskResult(
                warning="Revenue column unavailable; churn analysis cannot rank customers by value.",
                confidence="low",
            )

        df = current_df[[cust_col, date_col, revenue_column]].copy()
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df[revenue_column] = pd.to_numeric(df[revenue_column], errors="coerce")
        df = df.dropna(subset=[cust_col, date_col])
        if df.empty:
            return CustomerChurnRiskResult(
                warning="No rows with both a customer and a parseable date; churn analysis not applicable.",
                confidence="low",
            )

        df[cust_col] = df[cust_col].astype(str)
        dataset_max = df[date_col].max()
        dataset_min = df[date_col].min()
        total_span_days = max((dataset_max - dataset_min).days, 1)

        # Per-customer revenue (used for ranking and at-risk totals).
        cust_revenue = df.groupby(cust_col)[revenue_column].sum().fillna(0.0)
        total_revenue = float(cust_revenue.sum())

        n_cust = int(df[cust_col].nunique())
        if n_cust < MIN_CUSTOMERS:
            return CustomerChurnRiskResult(
                total_customers=n_cust,
                warning=f"Only {n_cust} customer(s); too few for meaningful churn analysis.",
                confidence="low",
            )

        # Fallback cadence: the median per-order gap across the whole dataset,
        # used for single-order customers who have no personal gap history.
        global_gaps: List[float] = []

        records: List[ChurnCustomer] = []
        at_risk_count = 0
        churned_count = 0
        revenue_at_risk = 0.0

        # First pass: collect gaps so we can build the global median fallback.
        grouped = df.groupby(cust_col)
        per_cust_dates: Dict[str, pd.Series] = {}
        for cust, gdf in grouped:
            dates = gdf[date_col].sort_values()
            per_cust_dates[cust] = dates
            if len(dates) >= 2:
                gaps = dates.diff().dropna().dt.days
                global_gaps.extend([float(g) for g in gaps if g > 0])

        global_median_gap = float(np.median(global_gaps)) if global_gaps else float(total_span_days)

        for cust, dates in per_cust_dates.items():
            order_count = int(len(dates))
            last_order = dates.max()
            days_since = int((dataset_max - last_order).days)
            cust_rev = float(cust_revenue.get(cust, 0.0))
            rev_share = (cust_rev / total_revenue * 100.0) if total_revenue > 0 else 0.0

            if order_count >= 2:
                gaps = dates.diff().dropna().dt.days
                positive_gaps = [float(g) for g in gaps if g > 0]
                avg_gap = float(np.mean(positive_gaps)) if positive_gaps else global_median_gap
            else:
                avg_gap = global_median_gap

            avg_gap = max(avg_gap, 1.0)

            # Risk classification, anchored to the customer's own cadence.
            # churned: silent for >4x their normal gap, or no order in the most
            #          recent full cadence window the data covers.
            # at_risk: silent for >2x their normal gap.
            if days_since > 4 * avg_gap or (order_count >= 2 and days_since > total_span_days * 0.75 and days_since > 2 * avg_gap):
                risk = "churned"
            elif days_since > 2 * avg_gap:
                risk = "at_risk"
            else:
                risk = "active"

            if risk == "churned":
                churned_count += 1
                revenue_at_risk += cust_rev
            elif risk == "at_risk":
                at_risk_count += 1
                revenue_at_risk += cust_rev

            explanation = _build_explanation(
                cust, risk, order_count, days_since, avg_gap, cust_rev,
            )

            records.append(ChurnCustomer(
                customer=cust[:80],
                risk=risk,
                order_count=order_count,
                days_since_last_order=days_since,
                avg_gap_days=round(avg_gap, 1),
                last_order_date=last_order.strftime("%Y-%m-%d"),
                total_revenue=round(cust_rev, 2),
                revenue_share_pct=round(rev_share, 1),
                explanation=explanation,
            ))

        # Rank: quiet customers first (churned above at_risk), then by revenue.
        risk_rank = {"churned": 0, "at_risk": 1, "active": 2}
        records.sort(key=lambda r: (risk_rank.get(r.risk, 3), -r.total_revenue))
        flagged = [r for r in records if r.risk in ("churned", "at_risk")]
        top = (flagged or records)[:TOP_N]

        revenue_at_risk_pct = (revenue_at_risk / total_revenue * 100.0) if total_revenue > 0 else 0.0

        headline = _build_headline_action(top, revenue_at_risk)

        return CustomerChurnRiskResult(
            customers=top,
            total_customers=n_cust,
            at_risk_count=at_risk_count,
            churned_count=churned_count,
            revenue_at_risk=round(revenue_at_risk, 2),
            revenue_at_risk_pct=round(revenue_at_risk_pct, 1),
            has_at_risk=(at_risk_count + churned_count) > 0,
            basis=f"Recency vs per-customer cadence over {total_span_days} days of transactions on '{cust_col}'.",
            confidence=_confidence(n_cust, len(df)),
            warning=None if (at_risk_count + churned_count) > 0 else "No customers currently flagged as at-risk or churned.",
            headline_action=headline,
        )
    except Exception:
        return None


def _build_explanation(
    cust: str, risk: str, order_count: int, days_since: int,
    avg_gap: float, revenue: float,
) -> str:
    rev_str = format_inr(revenue)
    if risk == "churned":
        return (
            f"'{cust}' looks churned: {days_since} days since the last order versus a usual "
            f"~{avg_gap:.0f}-day cadence across {order_count} order(s). Historic value {rev_str}."
        )
    if risk == "at_risk":
        return (
            f"'{cust}' is going quiet: {days_since} days since the last order, well past its "
            f"~{avg_gap:.0f}-day cadence ({order_count} order(s)). Historic value {rev_str}."
        )
    return (
        f"'{cust}' is ordering on schedule: {days_since} days since the last order, in line with its "
        f"~{avg_gap:.0f}-day cadence ({order_count} order(s))."
    )


def _build_headline_action(top: List[ChurnCustomer], revenue_at_risk: float) -> Optional[str]:
    flagged = [r for r in top if r.risk in ("churned", "at_risk")]
    if not flagged:
        return None
    n = len(flagged)
    rev_str = format_inr_lakh(sum(r.total_revenue for r in flagged))
    return (
        f"Call these {n} shop(s) this week — they used to order regularly and have gone quiet, "
        f"with {rev_str} of historic business at risk."
    )
