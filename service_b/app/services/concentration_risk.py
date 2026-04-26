"""
Concentration Risk Dashboard (V1 — Additive)
 
Deterministic analysis layer that measures how concentrated the business is
across products, customers, categories, or other meaningful business units.
 
For each detected dimension, computes:
  - HHI (Herfindahl-Hirschman Index)
  - Gini coefficient
  - Pareto ratio (80/20 test)
  - Top-N contributor shares
  - Composite risk score (0-100)
  - Risk label and trend detection
 
Output is a ranked list of dimension-level concentration findings.
"""
from __future__ import annotations
 
from typing import List, Optional, Tuple, Dict, Any
 
import numpy as np
import pandas as pd
from pydantic import BaseModel
 
 
# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────
 
class TopContributor(BaseModel):
    name: str
    revenue: float
    share_pct: float
 
 
class ConcentrationDimension(BaseModel):
    dimension: str
    dimension_column: str
    contributor_count: int
    top_1_share_pct: float
    top_5_share_pct: float
    top_10_share_pct: float
    top_20_pct_share: float
    hhi: float
    gini: float
    pareto_ratio: float
    composite_score: float
    risk_level: str
    top_contributors: List[TopContributor] = []
    trend: Optional[str] = None
    hhi_change_pct: Optional[float] = None
    confidence: str
    explanation: str
    warning: Optional[str] = None
    watchlist: bool = False
 
 
class ConcentrationRiskDashboardResult(BaseModel):
    dimensions: List[ConcentrationDimension] = []
    dimension_count: int = 0
    overall_risk: str = "low"
    overall_score: float = 0.0
    has_critical: bool = False
    has_high: bool = False
    warning: Optional[str] = None
    confidence: str = "medium"
 
 
# ─────────────────────────────────────────────
# Column detection helpers
# ─────────────────────────────────────────────
 
_DIMENSION_CANDIDATES = {
    "product": [
        "product", "product_name", "item", "sku", "description",
        "product_id", "item_name", "stockcode", "stock_code",
    ],
    "customer": [
        "customer_id", "customerid", "customer", "cust_id",
        "buyer", "buyer_id", "user_id", "userid",
        "client", "client_id", "member_id",
    ],
    "category": [
        "category", "product_category", "department", "group",
        "product_group", "product_type", "type",
    ],
    "region": [
        "country", "region", "state", "city", "location", "geo",
    ],
}
 
_DATE_CANDIDATES = [
    "date", "invoice_date", "invoicedate", "order_date",
    "orderdate", "transaction_date", "created_at",
]
 
MIN_CONTRIBUTORS = 3
MIN_ROWS = 10
 
 
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
    for c in df.columns:
        if df[c].dtype == "datetime64[ns]":
            return c
    return None
 
 
# ─────────────────────────────────────────────
# Statistical computation helpers
# ─────────────────────────────────────────────
 
def _compute_hhi(shares: np.ndarray) -> float:
    """Herfindahl-Hirschman Index. shares are fractions (0-1). Returns 0-10000."""
    return float(np.sum(shares ** 2) * 10000)
 
 
def _compute_gini(values: np.ndarray) -> float:
    """Gini coefficient. Returns 0-1."""
    if len(values) < 2 or values.sum() == 0:
        return 0.0
    sorted_v = np.sort(values)
    n = len(sorted_v)
    index = np.arange(1, n + 1)
    return float((2 * np.sum(index * sorted_v)) / (n * np.sum(sorted_v)) - (n + 1) / n)
 
 
def _compute_pareto_ratio(revenue_sorted_desc: np.ndarray, total_revenue: float) -> float:
    """Fraction of contributors needed to reach 80% of total revenue. Returns 0-1."""
    if total_revenue <= 0 or len(revenue_sorted_desc) == 0:
        return 1.0
    cumsum = np.cumsum(revenue_sorted_desc)
    threshold = total_revenue * 0.80
    count_needed = int(np.searchsorted(cumsum, threshold, side="left")) + 1
    return round(count_needed / len(revenue_sorted_desc), 4)
 
 
def _composite_score(hhi: float, gini: float, pareto_ratio: float) -> float:
    hhi_norm = min(hhi / 100, 100)
    gini_norm = gini * 100
    pareto_norm = max(0, (1 - pareto_ratio) * 100)
    return round(0.40 * hhi_norm + 0.35 * gini_norm + 0.25 * pareto_norm, 1)
 
 
def _risk_label(score: float) -> str:
    if score >= 75:
        return "critical"
    elif score >= 50:
        return "high"
    elif score >= 25:
        return "moderate"
    return "low"
 
 
def _compute_confidence(contributor_count: int, row_count: int) -> str:
    if contributor_count >= 50 and row_count >= 500:
        return "high"
    if contributor_count >= 10 or row_count >= 100:
        return "medium"
    return "low"
 
 
def _hhi_trend(
    df: pd.DataFrame, dim_col: str, rev_col: str, date_col: str,
) -> Tuple[Optional[str], Optional[float]]:
    """Compute HHI change between first and second half of time range."""
    try:
        dates = pd.to_datetime(df[date_col], errors="coerce")
        valid = dates.dropna()
        if len(valid) < 10:
            return None, None
        mid = valid.min() + (valid.max() - valid.min()) / 2
        rev = pd.to_numeric(df[rev_col], errors="coerce").fillna(0)
 
        mask_h1 = dates <= mid
        mask_h2 = dates > mid
 
        def half_hhi(mask):
            half_rev = rev[mask].groupby(df[dim_col][mask]).sum()
            half_rev = half_rev[half_rev > 0]
            if len(half_rev) < MIN_CONTRIBUTORS or half_rev.sum() <= 0:
                return None
            shares = (half_rev / half_rev.sum()).values
            return _compute_hhi(shares)
 
        hhi1 = half_hhi(mask_h1)
        hhi2 = half_hhi(mask_h2)
        if hhi1 is None or hhi2 is None or hhi1 == 0:
            return None, None
 
        pct_change = round(((hhi2 - hhi1) / hhi1) * 100, 1)
        if pct_change > 5:
            return "increasing", pct_change
        elif pct_change < -5:
            return "decreasing", pct_change
        return "stable", pct_change
    except Exception:
        return None, None
 
 
def _build_explanation(
    dim_name: str, risk: str, contributor_count: int,
    top_5_share: float, hhi: float, gini: float, pareto_ratio: float,
    trend: Optional[str],
) -> str:
    parts = []
    dim_title = dim_name.capitalize()
    if risk == "critical":
        parts.append(
            f"{dim_title} concentration is critical: the top 5 {dim_name}s account for "
            f"{top_5_share:.1f}% of revenue (HHI: {hhi:.0f}). "
            f"The business is heavily dependent on a very small set of {dim_name}s."
        )
    elif risk == "high":
        parts.append(
            f"{dim_title} concentration is high: significant revenue dependency exists among "
            f"{contributor_count} {dim_name}s (HHI: {hhi:.0f}, Gini: {gini:.2f})."
        )
    elif risk == "moderate":
        parts.append(
            f"{dim_title} concentration is moderate: revenue is reasonably distributed across "
            f"{contributor_count} {dim_name}s (HHI: {hhi:.0f}, Gini: {gini:.2f})."
        )
    else:
        parts.append(
            f"{dim_title} concentration is low: the business appears healthy from a "
            f"{dim_name} concentration standpoint (HHI: {hhi:.0f})."
        )
    if trend == "increasing":
        parts.append(f"Concentration is increasing over time — dependency risk is growing.")
    elif trend == "decreasing":
        parts.append(f"Concentration is decreasing — the revenue base is diversifying.")
    if pareto_ratio <= 0.10:
        parts.append(f"Critical: only {pareto_ratio*100:.0f}% of {dim_name}s drive 80% of revenue.")
    elif pareto_ratio <= 0.20:
        parts.append(f"Pareto pattern: {pareto_ratio*100:.0f}% of {dim_name}s drive 80% of revenue.")
    return " ".join(parts)
 
 
# ─────────────────────────────────────────────
# Per-dimension analysis
# ─────────────────────────────────────────────
 
def _analyze_dimension(
    df: pd.DataFrame, dim_name: str, dim_col: str,
    rev_col: str, date_col: Optional[str],
) -> Optional[ConcentrationDimension]:
    """Compute full concentration metrics for a single dimension."""
    try:
        rev = pd.to_numeric(df[rev_col], errors="coerce").fillna(0)
        contrib_rev = rev.groupby(df[dim_col]).sum()
        contrib_rev = contrib_rev[contrib_rev > 0].sort_values(ascending=False)
 
        n_contrib = len(contrib_rev)
        if n_contrib < MIN_CONTRIBUTORS:
            return None
 
        total_rev = float(contrib_rev.sum())
        if total_rev <= 0:
            return None
 
        # Shares
        shares = (contrib_rev / total_rev).values
        rev_sorted = contrib_rev.values  # already sorted desc
 
        # Top-N shares
        top_1 = round(float(shares[0]) * 100, 1) if n_contrib >= 1 else 0
        top_5 = round(float(shares[:5].sum()) * 100, 1)
        top_10 = round(float(shares[:10].sum()) * 100, 1)
        top_20_pct_count = max(1, int(n_contrib * 0.20))
        top_20_pct = round(float(shares[:top_20_pct_count].sum()) * 100, 1)
 
        # Indices
        hhi = round(_compute_hhi(shares), 1)
        gini = round(_compute_gini(rev_sorted), 4)
        pareto = _compute_pareto_ratio(rev_sorted, total_rev)
        score = _composite_score(hhi, gini, pareto)
        risk = _risk_label(score)
 
        # Top contributors
        top_contribs = []
        for name, rev_val in contrib_rev.head(5).items():
            top_contribs.append(TopContributor(
                name=str(name)[:80],
                revenue=round(float(rev_val), 2),
                share_pct=round(float(rev_val / total_rev * 100), 1),
            ))
 
        # Trend
        trend_dir, hhi_chg = (None, None)
        if date_col:
            trend_dir, hhi_chg = _hhi_trend(df, dim_col, rev_col, date_col)
 
        conf = _compute_confidence(n_contrib, len(df))
        explanation = _build_explanation(
            dim_name, risk, n_contrib, top_5, hhi, gini, pareto, trend_dir,
        )
 
        warning = None
        if n_contrib < 10:
            warning = f"Only {n_contrib} {dim_name}s detected — results may be less reliable."
 
        return ConcentrationDimension(
            dimension=dim_name,
            dimension_column=dim_col,
            contributor_count=n_contrib,
            top_1_share_pct=top_1,
            top_5_share_pct=top_5,
            top_10_share_pct=top_10,
            top_20_pct_share=top_20_pct,
            hhi=hhi,
            gini=gini,
            pareto_ratio=pareto,
            composite_score=score,
            risk_level=risk,
            top_contributors=top_contribs,
            trend=trend_dir,
            hhi_change_pct=hhi_chg,
            confidence=conf,
            explanation=explanation,
            warning=warning,
            watchlist=(risk in ("high", "critical")),
        )
    except Exception:
        return None
 
 
# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────
 
def compute_concentration_risk(
    current_df: pd.DataFrame,
    revenue_column: str,
) -> Optional[ConcentrationRiskDashboardResult]:
    """
    Compute multi-dimensional concentration risk analysis.
 
    Returns None only on unexpected error.
    Returns a result with warning if data is insufficient.
    """
    try:
        if len(current_df) < MIN_ROWS:
            return ConcentrationRiskDashboardResult(
                warning="Dataset too small for concentration analysis.",
                confidence="low",
            )
 
        date_col = _detect_date_col(current_df)
        dimensions: List[ConcentrationDimension] = []
 
        for dim_name, candidates in _DIMENSION_CANDIDATES.items():
            col = _detect_col(current_df, candidates)
            if not col:
                continue
            if current_df[col].nunique() < MIN_CONTRIBUTORS:
                continue
            result = _analyze_dimension(current_df, dim_name, col, revenue_column, date_col)
            if result:
                dimensions.append(result)
 
        if not dimensions:
            return ConcentrationRiskDashboardResult(
                warning="No suitable grouping columns detected for concentration analysis.",
                confidence="low",
            )
 
        # Sort by composite score descending (highest risk first)
        dimensions.sort(key=lambda d: d.composite_score, reverse=True)
 
        overall_score = max(d.composite_score for d in dimensions)
        overall_risk = _risk_label(overall_score)
        has_crit = any(d.risk_level == "critical" for d in dimensions)
        has_high = any(d.risk_level == "high" for d in dimensions)
 
        all_conf = [d.confidence for d in dimensions]
        if all_conf.count("high") > len(all_conf) / 2:
            overall_conf = "high"
        elif all_conf.count("low") > len(all_conf) / 2:
            overall_conf = "low"
        else:
            overall_conf = "medium"
 
        return ConcentrationRiskDashboardResult(
            dimensions=dimensions,
            dimension_count=len(dimensions),
            overall_risk=overall_risk,
            overall_score=round(overall_score, 1),
            has_critical=has_crit,
            has_high=has_high,
            confidence=overall_conf,
        )
    except Exception:
        return None
