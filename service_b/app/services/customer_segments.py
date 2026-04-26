"""
Customer Segmentation & Cohort Analysis (V1 — Additive)
 
Deterministic analysis layer that segments customers into meaningful groups
and evaluates how each group contributes to the business.
 
Segmentation strategies (in priority order):
  1. RFV — Recency / Frequency / Value (customer ID + date + order ID)
  2. FV  — Frequency / Value (customer ID, no date)
  3. Region — Geographic cohorts (no customer ID, region column exists)
 
Each segment is scored for revenue contribution, growth trend, stability,
and assigned a value tier. Output is a ranked list.
"""
from __future__ import annotations
 
from typing import Dict, List, Optional, Tuple
 
import numpy as np
import pandas as pd
from pydantic import BaseModel
 
 
# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────
 
class CustomerSegment(BaseModel):
    segment_label: str
    segment_basis: str
    tier: str
    customer_count: int
    total_revenue: float
    revenue_share_pct: float
    avg_revenue_per_customer: float
    avg_order_frequency: Optional[float] = None
    avg_recency_days: Optional[float] = None
    period_growth_pct: Optional[float] = None
    concentration_pct: float
    stability: str
    confidence: str
    explanation: str
    warning: Optional[str] = None
    watchlist: bool = False
 
 
class CustomerSegmentationResult(BaseModel):
    segments: List[CustomerSegment] = []
    segment_count: int = 0
    segment_basis: str = ""
    total_customers: int = 0
    has_at_risk: bool = False
    has_declining: bool = False
    warning: Optional[str] = None
    confidence: str = "medium"
 
 
# ─────────────────────────────────────────────
# Column detection helpers
# ─────────────────────────────────────────────
 
_CUSTOMER_CANDIDATES = [
    "customer_id", "customerid", "customer", "cust_id",
    "buyer", "buyer_id", "user_id", "userid",
    "client", "client_id", "member_id",
]
_DATE_CANDIDATES = [
    "date", "invoice_date", "invoicedate", "order_date",
    "orderdate", "transaction_date", "created_at",
]
_ORDER_CANDIDATES = [
    "invoice_no", "invoiceno", "order_id", "orderid",
    "order_no", "orderno", "transaction_id", "txn_id",
]
_REGION_CANDIDATES = [
    "country", "region", "state", "city", "location", "geo",
]
 
 
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
# Percentile-based tier helpers
# ─────────────────────────────────────────────
 
def _value_tier(revenue: float, p30: float, p80: float) -> str:
    if revenue >= p80:
        return "high_value"
    elif revenue >= p30:
        return "mid_value"
    return "low_value"
 
 
def _frequency_tier(freq: int, p25: float, p75: float) -> str:
    if freq >= p75:
        return "frequent"
    elif freq >= p25:
        return "occasional"
    return "rare"
 
 
def _recency_tier(rec_days: float, t_active: float, t_cooling: float) -> str:
    if rec_days <= t_active:
        return "active"
    elif rec_days <= t_cooling:
        return "cooling"
    return "inactive"
 
 
# ─────────────────────────────────────────────
# Segment naming (RFV mode)
# ─────────────────────────────────────────────
 
def _rfv_segment_name(val: str, freq: str, rec: str) -> Tuple[str, str]:
    """Return (segment_label, tier)."""
    if val == "high_value" and freq == "frequent" and rec == "active":
        return "Champions", "high_value"
    if val == "high_value" and rec in ("active", "cooling") and freq in ("frequent", "occasional"):
        return "Loyal High-Value", "high_value"
    if val == "high_value":
        return "High-Value At Risk", "at_risk"
    if val == "mid_value" and freq == "frequent" and rec == "active":
        return "Growing Mid-Value", "growing"
    if val == "mid_value" and rec == "inactive":
        return "Mid-Value Declining", "declining"
    if val == "mid_value":
        return "Stable Mid-Value", "stable_value"
    if val == "low_value" and rec == "active":
        return "Low-Value Active", "stable_value"
    if val == "low_value" and rec == "inactive":
        return "Low-Value Inactive", "declining"
    return "Other Low-Value", "stable_value"
 
 
def _fv_segment_name(val: str, freq: str) -> Tuple[str, str]:
    """Return (segment_label, tier) — no recency available."""
    if val == "high_value" and freq == "frequent":
        return "High-Value Frequent", "high_value"
    if val == "high_value":
        return "High-Value Infrequent", "at_risk"
    if val == "mid_value" and freq == "frequent":
        return "Mid-Value Frequent", "growing"
    if val == "mid_value":
        return "Mid-Value Standard", "stable_value"
    return "Low-Value", "declining"
 
 
# ─────────────────────────────────────────────
# Growth & stability helpers
# ─────────────────────────────────────────────
 
def _segment_growth(
    seg_df: pd.DataFrame, date_col: Optional[str], rev_col: str,
) -> Optional[float]:
    if not date_col or seg_df.empty:
        return None
    try:
        dates = pd.to_datetime(seg_df[date_col], errors="coerce")
        valid = dates.dropna()
        if len(valid) < 4:
            return None
        min_date = valid.min()
        max_date = valid.max()
        if min_date == max_date:
            return None
        mid = min_date + (max_date - min_date) / 2
        rev = pd.to_numeric(seg_df[rev_col], errors="coerce").fillna(0)
        h1 = float(rev[dates <= mid].sum())
        h2 = float(rev[dates > mid].sum())
        if h1 <= 0:
            return None
        return round(((h2 - h1) / h1) * 100, 1)
    except Exception:
        return None
 
 
def _segment_stability(per_cust_rev: pd.Series) -> str:
    if len(per_cust_rev) < 2 or per_cust_rev.mean() == 0:
        return "stable"
    cv = float(abs(per_cust_rev.std() / per_cust_rev.mean()))
    if cv < 0.5:
        return "stable"
    elif cv < 1.0:
        return "moderate"
    return "volatile"
 
 
def _compute_confidence(cust_count: int, txn_count: int) -> str:
    if cust_count >= 20 and txn_count >= 100:
        return "high"
    if cust_count >= 10 or txn_count >= 50:
        return "medium"
    return "low"
 
 
def _build_explanation(
    label: str, tier: str, cust_count: int, rev_share: float,
    avg_freq: Optional[float], avg_rec: Optional[float],
    growth: Optional[float], stability: str,
) -> str:
    parts = [f"'{label}' segment: {cust_count} customers contributing {rev_share:.1f}% of total revenue."]
    if tier == "high_value":
        parts.append("This is a high-value group critical to business performance.")
    elif tier == "at_risk":
        parts.append("This group shows risk signals — high value but declining engagement.")
    elif tier == "growing":
        parts.append("This group is growing and may become a major revenue contributor.")
    elif tier == "declining":
        parts.append("This group is weakening and requires attention.")
    if avg_freq is not None:
        parts.append(f"Average order frequency: {avg_freq:.1f} orders per customer.")
    if avg_rec is not None:
        parts.append(f"Average recency: {avg_rec:.0f} days since last purchase.")
    if growth is not None:
        if growth > 5:
            parts.append(f"Revenue grew {growth:.1f}% in the second half of the period.")
        elif growth < -5:
            parts.append(f"Revenue declined {abs(growth):.1f}% in the second half of the period.")
        else:
            parts.append("Revenue is roughly flat across the analyzed period.")
    if stability == "volatile":
        parts.append("Revenue is unevenly distributed across customers in this segment.")
    return " ".join(parts)
 
 
# ─────────────────────────────────────────────
# Core segmentation strategies
# ─────────────────────────────────────────────
 
MAX_SEGMENTS = 10
MIN_CUSTOMERS = 5
 
 
def _run_rfv_or_fv(
    df: pd.DataFrame, cust_col: str, rev_col: str,
    date_col: Optional[str], order_col: Optional[str],
) -> Optional[CustomerSegmentationResult]:
    """RFV or FV segmentation depending on available columns."""
    rev = pd.to_numeric(df[rev_col], errors="coerce").fillna(0)
    total_revenue = float(rev.sum())
    if total_revenue <= 0:
        return CustomerSegmentationResult(
            warning="No positive revenue detected; customer segmentation not applicable.",
            confidence="low",
        )
 
    # Build per-customer metrics
    current_cust_rev = rev.groupby(df[cust_col]).sum()
    current_cust_rev = current_cust_rev[current_cust_rev > 0]  # drop non-revenue customers
    n_cust = len(current_cust_rev)
    if n_cust < MIN_CUSTOMERS:
        return CustomerSegmentationResult(
            total_customers=n_cust,
            warning=f"Only {n_cust} customers — too few for meaningful segmentation.",
            confidence="low",
        )
 
    # Value percentiles
    p30 = float(current_cust_rev.quantile(0.30))
    p80 = float(current_cust_rev.quantile(0.80))
 
    # Frequency
    if order_col:
        cust_freq = df.groupby(cust_col)[order_col].nunique()
    else:
        cust_freq = df.groupby(cust_col).size()
    fp25 = float(cust_freq.quantile(0.25))
    fp75 = float(cust_freq.quantile(0.75))
 
    # Recency (if dates available)
    has_recency = False
    cust_recency: Optional[pd.Series] = None
    t_active = 30.0
    t_cooling = 90.0
    if date_col:
        try:
            dates = pd.to_datetime(df[date_col], errors="coerce")
            max_date = dates.max()
            last_seen = dates.groupby(df[cust_col]).max()
            cust_rec_raw = (max_date - last_seen).dt.days.astype(float)
            # Reindex to match current_cust_rev exactly
            cust_recency = cust_rec_raw.reindex(current_cust_rev.index).fillna(999)
            
            date_range = (dates.max() - dates.min()).days
            if 0 < date_range < 90:
                t_active = date_range / 3
                t_cooling = 2 * date_range / 3
            has_recency = True
        except Exception:
            has_recency = False
 
    basis = "rfv" if has_recency else "fv"
 
    # Assign segment per customer
    seg_assignments: Dict[str, Tuple[str, str]] = {}  # cust_id -> (label, tier)
    for cid in current_cust_rev.index:
        val_t = _value_tier(float(current_cust_rev.get(cid, 0)), p30, p80)
        freq_t = _frequency_tier(int(cust_freq.get(cid, 0)), fp25, fp75)
        if has_recency and cust_recency is not None:
            rec_t = _recency_tier(float(cust_recency.get(cid, 999)), t_active, t_cooling)
            label, tier = _rfv_segment_name(val_t, freq_t, rec_t)
        else:
            label, tier = _fv_segment_name(val_t, freq_t)
        seg_assignments[cid] = (label, tier)
 
    # Map back to dataframe (using string labels)
    df_cust_mapping = df[cust_col].astype(str)
    cust_labels = df_cust_mapping.map(lambda c: seg_assignments.get(c, ("Unknown", "stable_value"))[0])
 
    # Build segment aggregates
    segments: List[CustomerSegment] = []
    # Distinct labels
    all_labels = sorted(set(l for l, _ in seg_assignments.values()))
    
    for seg_label in all_labels:
        # Find which tier this label implies
        seg_tier = next(t for l, t in seg_assignments.values() if l == seg_label)
        mask = cust_labels == seg_label
        
        seg_df = df[mask]
        seg_cust_ids = [str(cid) for cid, (l, _) in seg_assignments.items() if l == seg_label]
        seg_cust_count = len(seg_cust_ids)
        if seg_cust_count == 0:
            continue
 
        seg_rev_vals = rev[mask]
        seg_total_rev = float(seg_rev_vals.sum())
        seg_rev_share = (seg_total_rev / total_revenue * 100) if total_revenue > 0 else 0
        seg_avg_rev = seg_total_rev / seg_cust_count
 
        # Avg frequency
        seg_avg_freq = None
        current_freq_vals = cust_freq.reindex(seg_cust_ids).dropna()
        if len(current_freq_vals) > 0:
            seg_avg_freq = round(float(current_freq_vals.mean()), 1)
 
        # Avg recency
        seg_avg_rec = None
        if has_recency and cust_recency is not None:
            current_rec_vals = cust_recency.reindex(seg_cust_ids).dropna()
            if len(current_rec_vals) > 0:
                seg_avg_rec = round(float(current_rec_vals.mean()), 0)
 
        # Growth
        growth = _segment_growth(seg_df, date_col, rev_col)
 
        # Stability (per-customer revenue distribution within segment)
        per_cust_data = current_cust_rev.reindex(seg_cust_ids).dropna()
        stab = _segment_stability(per_cust_data)
 
        conf = _compute_confidence(seg_cust_count, len(seg_df))
        explanation = _build_explanation(
            seg_label, seg_tier, seg_cust_count, seg_rev_share,
            seg_avg_freq, seg_avg_rec, growth, stab,
        )
 
        seg_warning = None
        if seg_cust_count < 5:
            seg_warning = f"Only {seg_cust_count} customer(s) in this segment — interpret cautiously."
 
        segments.append(CustomerSegment(
            segment_label=seg_label,
            segment_basis=basis,
            tier=seg_tier,
            customer_count=seg_cust_count,
            total_revenue=round(seg_total_rev, 2),
            revenue_share_pct=round(seg_rev_share, 1),
            avg_revenue_per_customer=round(seg_avg_rev, 2),
            avg_order_frequency=seg_avg_freq,
            avg_recency_days=seg_avg_rec,
            period_growth_pct=growth,
            concentration_pct=round(seg_rev_share, 1),
            stability=stab,
            confidence=conf,
            explanation=explanation,
            warning=seg_warning,
            watchlist=(seg_tier in ("at_risk", "declining")),
        ))
 
    # Sort by revenue share desc, cap
    segments.sort(key=lambda s: s.revenue_share_pct, reverse=True)
    segments = segments[:MAX_SEGMENTS]
 
    return CustomerSegmentationResult(
        segments=segments,
        segment_count=len(segments),
        segment_basis=basis,
        total_customers=n_cust,
        has_at_risk=any(s.tier == "at_risk" for s in segments),
        has_declining=any(s.tier == "declining" for s in segments),
        confidence="medium" if not segments else segments[0].confidence,
    )
 
 
def _run_region_segmentation(
    df: pd.DataFrame, region_col: str, rev_col: str, date_col: Optional[str],
) -> Optional[CustomerSegmentationResult]:
    """Fallback: region-based cohorts when no customer column exists."""
    rev_vals = pd.to_numeric(df[rev_col], errors="coerce").fillna(0)
    total_rev = float(rev_vals.sum())
    if total_rev <= 0:
        return CustomerSegmentationResult(
            warning="No positive revenue detected; segmentation not applicable.",
            confidence="low",
        )
 
    n_regions = df[region_col].nunique()
    if n_regions < 2:
        return CustomerSegmentationResult(
            warning="Only one region — segmentation not meaningful.",
            confidence="low",
        )
 
    segments: List[CustomerSegment] = []
    for region, gdf in df.groupby(region_col):
        region_str = str(region)
        if not region_str or region_str == "nan":
            continue
        seg_rev = float(pd.to_numeric(gdf[rev_col], errors="coerce").fillna(0).sum())
        seg_share = (seg_rev / total_rev * 100) if total_rev > 0 else 0
        txn_count = len(gdf)
        avg_rev = seg_rev / max(txn_count, 1)
        growth = _segment_growth(gdf, date_col, rev_col)
        per_txn_rev = pd.to_numeric(gdf[rev_col], errors="coerce").fillna(0)
        stab = _segment_stability(per_txn_rev)
 
        if seg_share >= 25:
            tier = "high_value"
        elif seg_share >= 10:
            tier = "stable_value"
        elif growth is not None and growth < -10:
            tier = "declining"
        else:
            tier = "stable_value"
 
        conf = _compute_confidence(txn_count, txn_count)
        explanation = _build_explanation(
            region_str, tier, txn_count, seg_share, None, None, growth, stab,
        )
 
        segments.append(CustomerSegment(
            segment_label=region_str,
            segment_basis="region",
            tier=tier,
            customer_count=txn_count,
            total_revenue=round(seg_rev, 2),
            revenue_share_pct=round(seg_share, 1),
            avg_revenue_per_customer=round(avg_rev, 2),
            period_growth_pct=growth,
            concentration_pct=round(seg_share, 1),
            stability=stab,
            confidence=conf,
            explanation=explanation,
            watchlist=(tier in ("at_risk", "declining")),
        ))
 
    segments.sort(key=lambda s: s.revenue_share_pct, reverse=True)
    segments = segments[:MAX_SEGMENTS]
 
    return CustomerSegmentationResult(
        segments=segments,
        segment_count=len(segments),
        segment_basis="region",
        total_customers=len(df),
        has_at_risk=any(s.tier == "at_risk" for s in segments),
        has_declining=any(s.tier == "declining" for s in segments),
        confidence="medium",
    )
 
 
# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────
 
def compute_customer_segmentation(
    current_df: pd.DataFrame,
    revenue_column: str,
) -> Optional[CustomerSegmentationResult]:
    """
    Compute customer segmentation from the given DataFrame.
 
    Returns None only on unexpected error.
    Returns a result with warning if data is insufficient.
    """
    try:
        cust_col = _detect_col(current_df, _CUSTOMER_CANDIDATES)
        date_col = _detect_date_col(current_df)
        order_col = _detect_col(current_df, _ORDER_CANDIDATES)
        region_col = _detect_col(current_df, _REGION_CANDIDATES)
 
        if cust_col:
            return _run_rfv_or_fv(current_df, cust_col, revenue_column, date_col, order_col)
        elif region_col:
            return _run_region_segmentation(current_df, region_col, revenue_column, date_col)
        else:
            return CustomerSegmentationResult(
                warning="No customer ID or region column detected; customer segmentation not applicable.",
                confidence="low",
            )
    except Exception:
        return None
