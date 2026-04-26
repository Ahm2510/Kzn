"""
Cohort-Level Product Performance (V1 — Additive)
 
Deterministic analysis layer that groups products into cohorts and evaluates
their performance. Cohorts are derived from:
  1. Product category column (if available)
  2. Launch period — month of first appearance (if date column available)
  3. Revenue tier — top/middle/bottom by total product revenue (fallback)
 
Each cohort is scored for revenue contribution, growth trend, stability,
and assigned a performance tier. Output is a ranked list.
"""
from __future__ import annotations
 
from typing import List, Optional, Tuple
 
import numpy as np
import pandas as pd
from pydantic import BaseModel
 
 
# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────
 
class ProductCohort(BaseModel):
    cohort_label: str
    cohort_basis: str
    product_count: int
    transaction_count: int
    total_revenue: float
    revenue_share_pct: float
    avg_revenue_per_product: float
    period_growth_pct: Optional[float] = None
    stability: str
    performance_tier: str
    confidence: str
    explanation: str
    warning: Optional[str] = None
    watchlist: bool = False
 
 
class CohortProductPerformanceResult(BaseModel):
    cohorts: List[ProductCohort] = []
    cohort_count: int = 0
    cohort_basis: str = ""
    has_declining: bool = False
    has_underperformer: bool = False
    warning: Optional[str] = None
    confidence: str = "medium"
 
 
# ─────────────────────────────────────────────
# Column detection helpers
# ─────────────────────────────────────────────
 
_PRODUCT_CANDIDATES = [
    "product", "product_name", "item", "sku", "description",
    "product_id", "item_name", "stockcode", "stock_code",
]
 
_CATEGORY_CANDIDATES = [
    "category", "product_category", "department", "group",
    "product_group", "product_type", "type",
]
 
_DATE_CANDIDATES = [
    "date", "invoice_date", "invoicedate", "order_date",
    "orderdate", "transaction_date", "created_at",
]
 
_QTY_CANDIDATES = ["quantity", "qty"]
 
 
def _detect_col(df: pd.DataFrame, candidates: list) -> Optional[str]:
    cols_lower = {c.lower().strip(): c for c in df.columns}
    return next((cols_lower[c] for c in candidates if c in cols_lower), None)
 
 
def _detect_date_col(df: pd.DataFrame) -> Optional[str]:
    col = _detect_col(df, _DATE_CANDIDATES)
    if col:
        try:
            parsed = pd.to_datetime(df[col], errors="coerce")
            if parsed.notna().sum() > len(df) * 0.5:
                return col
        except Exception:
            pass
    # Fallback: try all object/datetime columns
    for c in df.columns:
        if df[c].dtype == "datetime64[ns]":
            return c
        if df[c].dtype == object:
            try:
                parsed = pd.to_datetime(df[c], errors="coerce")
                if parsed.notna().sum() > len(df) * 0.5:
                    return c
            except Exception:
                continue
    return None
 
 
# ─────────────────────────────────────────────
# Cohort formation strategies
# ─────────────────────────────────────────────
 
def _form_category_cohorts(
    df: pd.DataFrame, product_col: str, cat_col: str, rev_col: str,
) -> Tuple[pd.Series, str]:
    """Assign each row to a cohort based on the category column."""
    return df[cat_col].astype(str), "category"
 
 
def _form_launch_period_cohorts(
    df: pd.DataFrame, product_col: str, date_col: str, rev_col: str,
) -> Tuple[pd.Series, str]:
    """
    Assign each product to the month it first appeared.
    Then map that label back to every row.
    """
    dates = pd.to_datetime(df[date_col], errors="coerce")
    first_seen = dates.groupby(df[product_col]).min()
    first_seen_label = first_seen.dt.to_period("M").astype(str)
    cohort_map = first_seen_label.to_dict()
    return df[product_col].map(cohort_map).fillna("unknown"), "launch_period"
 
 
def _form_revenue_tier_cohorts(
    df: pd.DataFrame, product_col: str, rev_col: str,
) -> Tuple[pd.Series, str]:
    """
    Group products into top 20% / middle 60% / bottom 20% by total revenue.
    """
    rev = pd.to_numeric(df[rev_col], errors="coerce").fillna(0)
    product_rev = rev.groupby(df[product_col]).sum().sort_values(ascending=False)
    cumul = product_rev.cumsum() / product_rev.sum()
    tier_map = {}
    for prod, pct in cumul.items():
        if pct <= 0.20:
            tier_map[prod] = "Top 20% Revenue"
        elif pct <= 0.80:
            tier_map[prod] = "Middle 60% Revenue"
        else:
            tier_map[prod] = "Bottom 20% Revenue"
    return df[product_col].map(tier_map).fillna("Bottom 20% Revenue"), "revenue_tier"
 
 
# ─────────────────────────────────────────────
# Per-cohort metric computation
# ─────────────────────────────────────────────
 
def _compute_cohort_growth(
    cohort_df: pd.DataFrame, date_col: Optional[str], rev_col: str,
) -> Optional[float]:
    """Period-over-period growth: first half vs second half of date range."""
    if not date_col:
        return None
    try:
        dates = pd.to_datetime(cohort_df[date_col], errors="coerce")
        valid = dates.dropna()
        if len(valid) < 4:
            return None
        mid = valid.min() + (valid.max() - valid.min()) / 2
        rev = pd.to_numeric(cohort_df[rev_col], errors="coerce").fillna(0)
        first_half = float(rev[dates <= mid].sum())
        second_half = float(rev[dates > mid].sum())
        if first_half <= 0:
            return None
        return round(((second_half - first_half) / first_half) * 100, 1)
    except Exception:
        return None
 
 
def _compute_stability(
    cohort_df: pd.DataFrame, product_col: str, rev_col: str,
) -> str:
    """CV of per-product revenue within the cohort."""
    try:
        rev = pd.to_numeric(cohort_df[rev_col], errors="coerce").fillna(0)
        product_rev = rev.groupby(cohort_df[product_col]).sum()
        if len(product_rev) < 2 or product_rev.mean() == 0:
            return "stable"
        cv = float(abs(product_rev.std() / product_rev.mean()))
        if cv < 0.5:
            return "stable"
        elif cv < 1.0:
            return "moderate"
        return "volatile"
    except Exception:
        return "stable"
 
 
def _assign_tier(
    revenue_share: float,
    growth: Optional[float],
    product_count: int,
) -> str:
    if product_count < 3:
        return "insufficient_data"
    if growth is not None:
        if revenue_share >= 20 and growth >= 5:
            return "top_performer"
        if growth < -15:
            return "declining_cohort"
        if revenue_share < 5 and growth < -5:
            return "declining_cohort"
        if revenue_share < 10 and growth < 0:
            return "underperformer"
    else:
        if revenue_share >= 25:
            return "top_performer"
        if revenue_share < 5:
            return "underperformer"
    if revenue_share >= 10:
        return "stable_performer"
    return "stable_performer"
 
 
def _compute_confidence(product_count: int, txn_count: int) -> str:
    if product_count >= 10 and txn_count >= 50:
        return "high"
    if product_count >= 5 or txn_count >= 20:
        return "medium"
    return "low"
 
 
def _build_explanation(
    label: str, revenue_share: float, product_count: int,
    growth: Optional[float], stability: str, tier: str,
) -> str:
    parts = [f"Cohort '{label}' contains {product_count} products contributing {revenue_share:.1f}% of total revenue."]
    if growth is not None:
        if growth > 0:
            parts.append(f"Growth of +{growth:.1f}% in the second half of the period indicates positive momentum.")
        elif growth < -5:
            parts.append(f"Revenue declined {abs(growth):.1f}% in the second half of the period, signaling weakening demand.")
        else:
            parts.append("Revenue is roughly flat across the analyzed period.")
    if stability == "volatile":
        parts.append("Revenue is unevenly distributed across products within this cohort.")
    tier_text = {
        "top_performer": "Overall, this cohort is a top performer.",
        "stable_performer": "This cohort is performing steadily.",
        "underperformer": "This cohort is underperforming relative to the portfolio.",
        "declining_cohort": "This cohort is declining and requires attention.",
        "insufficient_data": "Too few products to assess reliably.",
    }
    parts.append(tier_text.get(tier, ""))
    return " ".join(parts)
 
 
# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────
 
MAX_COHORTS = 10
MIN_PRODUCTS_FOR_ANALYSIS = 5  # need at least 5 distinct products total
 
 
def compute_cohort_product_performance(
    current_df: pd.DataFrame,
    revenue_column: str,
) -> Optional[CohortProductPerformanceResult]:
    """
    Compute cohort-level product performance from the given DataFrame.
 
    Returns None only on unexpected error.
    Returns a result with warning if data is insufficient.
    """
    try:
        product_col = _detect_col(current_df, _PRODUCT_CANDIDATES)
        if not product_col:
            return CohortProductPerformanceResult(
                warning="No product column detected; cohort analysis not applicable.",
                confidence="low",
            )
 
        rev = pd.to_numeric(current_df[revenue_column], errors="coerce").fillna(0)
        total_revenue = float(rev.sum())
        if total_revenue <= 0:
            return CohortProductPerformanceResult(
                warning="No positive revenue detected; cohort analysis not applicable.",
                confidence="low",
            )
 
        n_products = current_df[product_col].nunique()
        if n_products < MIN_PRODUCTS_FOR_ANALYSIS:
            return CohortProductPerformanceResult(
                warning=f"Only {n_products} distinct products — too few for cohort analysis.",
                confidence="low",
            )
 
        # Detect optional columns
        cat_col = _detect_col(current_df, _CATEGORY_CANDIDATES)
        date_col = _detect_date_col(current_df)
 
        # Choose cohort strategy
        if cat_col and current_df[cat_col].nunique() >= 2:
            cohort_labels, basis = _form_category_cohorts(current_df, product_col, cat_col, revenue_column)
        elif date_col:
            cohort_labels, basis = _form_launch_period_cohorts(current_df, product_col, date_col, revenue_column)
        else:
            cohort_labels, basis = _form_revenue_tier_cohorts(current_df, product_col, revenue_column)
 
        # Build working frame
        work = current_df[[product_col, revenue_column]].copy()
        work["__cohort"] = cohort_labels
        work["__rev"] = rev
 
        # Per-cohort computation
        cohorts: list[ProductCohort] = []
        for label, group_df in work.groupby("__cohort"):
            label_str = str(label)
            if not label_str or label_str == "nan":
                continue
 
            pcount = group_df[product_col].nunique()
            txn_count = len(group_df)
            cohort_rev = float(group_df["__rev"].sum())
            rev_share = (cohort_rev / total_revenue * 100) if total_revenue > 0 else 0
            avg_rev = (cohort_rev / pcount) if pcount > 0 else 0
 
            growth = _compute_cohort_growth(
                current_df.loc[group_df.index], date_col, revenue_column,
            )
            stab = _compute_stability(group_df, product_col, "__rev")
            tier = _assign_tier(rev_share, growth, pcount)
            conf = _compute_confidence(pcount, txn_count)
            explanation = _build_explanation(label_str, rev_share, pcount, growth, stab, tier)
 
            warning = None
            if pcount < 3:
                warning = f"Only {pcount} product(s) in this cohort — interpret cautiously."
 
            cohorts.append(ProductCohort(
                cohort_label=label_str,
                cohort_basis=basis,
                product_count=pcount,
                transaction_count=txn_count,
                total_revenue=round(cohort_rev, 2),
                revenue_share_pct=round(rev_share, 1),
                avg_revenue_per_product=round(avg_rev, 2),
                period_growth_pct=growth,
                stability=stab,
                performance_tier=tier,
                confidence=conf,
                explanation=explanation,
                warning=warning,
                watchlist=(tier in ("underperformer", "declining_cohort")),
            ))
 
        # Sort by revenue share descending, cap at MAX_COHORTS
        cohorts.sort(key=lambda c: c.revenue_share_pct, reverse=True)
        cohorts = cohorts[:MAX_COHORTS]
 
        has_dec = any(c.performance_tier == "declining_cohort" for c in cohorts)
        has_under = any(c.performance_tier == "underperformer" for c in cohorts)
 
        # Overall confidence
        all_conf = [c.confidence for c in cohorts]
        if not all_conf:
            overall_conf = "low"
        elif all_conf.count("high") > len(all_conf) / 2:
            overall_conf = "high"
        elif all_conf.count("low") > len(all_conf) / 2:
            overall_conf = "low"
        else:
            overall_conf = "medium"
 
        return CohortProductPerformanceResult(
            cohorts=cohorts,
            cohort_count=len(cohorts),
            cohort_basis=basis,
            has_declining=has_dec,
            has_underperformer=has_under,
            confidence=overall_conf,
        )
 
    except Exception:
        return None
