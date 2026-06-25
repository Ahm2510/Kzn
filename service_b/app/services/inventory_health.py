"""
Inventory Health Score (V2 — Refined)
 
Computes a deterministic, normalized 0–100 inventory health score from a sales dataset.
This version includes temporal analysis (declining, inactive, spiking) and an 
advanced watchlist with explained risk factors.
 
Score bands:
    80–100  Very Healthy
    60–79   Mostly Healthy
    40–59   Warning
    0–39    Unhealthy
"""
from __future__ import annotations
 
from typing import Any, List, Optional, Dict

import pandas as pd
import numpy as np
from pydantic import BaseModel

from app.services.insight_engine.column_detector import detect_revenue_column
 
 
class InventoryHealthResult(BaseModel):
    """Structured result for the Inventory Health Score."""
 
    score: float
    label: str
    confidence: str                  # "high" / "medium" / "low"
    confidence_reason: Optional[str] = None
    explanation: str
    contributing_factors: List[str]
    warning: Optional[str] = None
    data_source: str
    has_product_data: bool
    has_quantity_data: bool
    has_stock_data: bool
    has_date_data: bool
    watchlist: Optional[List[str]] = None
    # ── Dead stock / slow-moving inventory (distribution niche) ──────────────
    # SKUs with no transaction in the most recent `dead_stock_window_days`,
    # ranked by the rupee value of capital tied up in them.
    dead_stock_skus: Optional[List[Dict[str, Any]]] = None
    total_dead_stock_value: Optional[float] = None
    dead_stock_count: Optional[int] = None
    dead_stock_window_days: Optional[int] = None
 
 
# ─────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────
 
def _label_from_score(score: float) -> str:
    if score >= 80.0:
        return "Very Healthy"
    if score >= 60.0:
        return "Mostly Healthy"
    if score >= 40.0:
        return "Warning"
    return "Unhealthy"
 
 
def _detect_product_col(df: pd.DataFrame) -> Optional[str]:
    candidates = [
        "product", "product_name", "item", "sku", "description", "product_id",
        "item_name", "product_category", "category",
    ]
    cols_lower = {c.lower().strip(): c for c in df.columns}
    return next((cols_lower[c] for c in candidates if c in cols_lower), None)
 
 
def _detect_qty_col(df: pd.DataFrame) -> Optional[str]:
    candidates = ["quantity", "qty", "count", "units", "unit_count", "volume"]
    cols_lower = {c.lower().strip(): c for c in df.columns}
    return next((cols_lower[c] for c in candidates if c in cols_lower), None)
 
 
def _detect_stock_col(df: pd.DataFrame) -> Optional[str]:
    candidates = [
        "stock", "inventory", "stock_quantity", "qty_on_hand", "on_hand",
        "stock_level", "stock_count", "available", "available_qty", "remaining_stock",
    ]
    cols_lower = {c.lower().strip(): c for c in df.columns}
    return next((cols_lower[c] for c in candidates if c in cols_lower), None)
 
 
def _detect_date_col(df: pd.DataFrame) -> Optional[str]:
    candidates = ["date", "timestamp", "invoice_date", "order_date", "created_at", "occurred_at"]
    cols_lower = {c.lower().strip(): c for c in df.columns}
    return next((cols_lower[c] for c in candidates if c in cols_lower), None)
 
 
def _build_explanation(
    score: float,
    has_product: bool,
    has_qty: bool,
    has_stock: bool,
    has_date: bool,
) -> str:
    if score >= 80.0:
        base = "Inventory appears healthy with active product movement and low dead stock risk."
    elif score >= 60.0:
        base = "Inventory is mostly healthy, but some slow-moving SKUs or uneven product movement was detected."
    elif score >= 40.0:
        base = "Inventory health is concerning — significant slow-moving or dead stock signals were detected."
    else:
        base = (
            "Inventory is at risk due to substantial dead stock, poor product movement, "
            "or stockout/overstock imbalance."
        )
 
    parts = []
    if has_product:
        parts.append("product activity")
    if has_qty:
        parts.append("quantity patterns")
    if has_stock:
        parts.append("stock levels")
    if has_date:
        parts.append("temporal trends")
 
    if parts:
        data_note = f" Score is based on {' and '.join(parts)}."
    else:
        data_note = ""
 
    return f"{base}{data_note}"
 
 
# ─────────────────────────────────────────────
# Dead stock / slow-moving inventory (distribution niche)
# ─────────────────────────────────────────────

DEFAULT_DEAD_STOCK_DAYS = 60


def _compute_dead_stock(
    df: pd.DataFrame,
    product_col: str,
    date_col: Optional[str],
    n_days: int = DEFAULT_DEAD_STOCK_DAYS,
) -> Optional[Dict[str, Any]]:
    """
    Identify SKUs with no transaction in the most recent ``n_days`` (relative to
    the dataset's own date range) and estimate the rupee value of capital tied
    up in them.

    Requires a date column (recency is time-based) and a product column. The
    rupee figure uses the already-detected revenue column when available, so the
    headline reads as money sitting still — not just a SKU count. Returns
    ``None`` when dead stock cannot be computed; never raises.
    """
    try:
        if not date_col or product_col not in df.columns:
            return None

        work = df[[product_col, date_col]].copy()
        work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
        work = work.dropna(subset=[product_col, date_col])
        if work.empty:
            return None

        # Detect a revenue/value column for the rupee estimate (graceful).
        rev_col, _conf, _mode = detect_revenue_column(df)
        rev_series = None
        if rev_col and rev_col in df.columns:
            rev_series = pd.to_numeric(df[rev_col], errors="coerce")
            work["__rev"] = rev_series.reindex(work.index)

        work[product_col] = work[product_col].astype(str)
        dataset_max = work[date_col].max()
        cutoff = dataset_max - pd.Timedelta(days=int(n_days))

        last_seen = work.groupby(product_col)[date_col].max()
        dead_skus_idx = last_seen[last_seen < cutoff].index
        if len(dead_skus_idx) == 0:
            return {
                "skus": [],
                "total_value": 0.0 if rev_series is not None else None,
                "count": 0,
                "window_days": int(n_days),
            }

        # Per-SKU value tied up = total historical revenue of that SKU.
        sku_value = None
        sku_avg_value = None
        if rev_series is not None:
            sku_value = work.groupby(product_col)["__rev"].sum()
            sku_avg_value = work.groupby(product_col)["__rev"].mean()

        rows: List[Dict[str, Any]] = []
        for sku in dead_skus_idx:
            last_date = last_seen[sku]
            days_inactive = int((dataset_max - last_date).days)
            value_tied = None
            avg_txn = None
            if sku_value is not None:
                v = sku_value.get(sku)
                value_tied = round(float(v), 2) if pd.notna(v) else 0.0
                a = sku_avg_value.get(sku)
                avg_txn = round(float(a), 2) if pd.notna(a) else 0.0
            rows.append({
                "sku": str(sku)[:80],
                "last_sold": last_date.strftime("%Y-%m-%d"),
                "days_inactive": days_inactive,
                "value_tied_up": value_tied if value_tied is not None else 0.0,
                "avg_transaction_value": avg_txn if avg_txn is not None else 0.0,
            })

        # Rank by capital tied up (rupee value) descending.
        rows.sort(key=lambda r: r.get("value_tied_up", 0.0), reverse=True)

        total_value = None
        if sku_value is not None:
            total_value = round(float(sum(r["value_tied_up"] for r in rows)), 2)

        return {
            "skus": rows[:15],
            "total_value": total_value,
            "count": len(rows),
            "window_days": int(n_days),
        }
    except Exception:
        return None


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

def compute_inventory_health_score(
    df: pd.DataFrame,
    dead_stock_days: int = DEFAULT_DEAD_STOCK_DAYS,
) -> Optional[InventoryHealthResult]:
    """
    Compute the Inventory Health Score V2.

    ``dead_stock_days`` (default 60) controls the recency window used to flag
    dead / slow-moving SKUs and the rupee value of capital tied up in them.
    """
    try:
        n = len(df)
        if n < 2:
            return None
 
        product_col = _detect_product_col(df)
        qty_col = _detect_qty_col(df)
        stock_col = _detect_stock_col(df)
        date_col = _detect_date_col(df)
 
        if not product_col and not qty_col and not stock_col:
            return None
 
        contributing_factors: List[str] = []
        watchlist_map: Dict[str, str] = {} # SKU -> Reason
 
        # ── Component 1: SKU Activity Score (0–40 pts) ───────────────────────
        sku_score = 20.0
        has_product_data = False
        has_date_data = False
 
        if product_col:
            try:
                sales_counts = df.groupby(product_col).size()
                total_skus = len(sales_counts)
                has_product_data = True
 
                if total_skus >= 2:
                    # Static patterns
                    dead_skus = int((sales_counts == 1).sum())
                    dead_ratio = dead_skus / total_skus
                    slow_threshold = float(sales_counts.quantile(0.15))
                    slow_skus = int((sales_counts < slow_threshold).sum())
                    slow_ratio = slow_skus / total_skus
 
                    # Flag dead/slow in map
                    dead_names = sales_counts[sales_counts == 1].index.tolist()
                    for s in dead_names[:3]:
                        watchlist_map[str(s)] = "Dead Stock"
                    
                    slow_names = sales_counts[sales_counts < slow_threshold].index.tolist()
                    for s in slow_names[:3]:
                        if str(s) not in watchlist_map:
                            watchlist_map[str(s)] = "Low Velocity"
 
                    # Temporal patterns (if date exists)
                    temporal_penalty = 0.0
                    if date_col:
                        try:
                            # Ensure date is parsed
                            df_dated = df.copy()
                            df_dated[date_col] = pd.to_datetime(df_dated[date_col], errors='coerce')
                            df_dated = df_dated.dropna(subset=[date_col])
                            
                            if not df_dated.empty:
                                has_date_data = True
                                max_date = df_dated[date_col].max()
                                min_date = df_dated[date_col].min()
                                total_days = (max_date - min_date).days
                                
                                if total_days > 7:
                                    # 1. Zero-Movement (Recency based)
                                    # Flag SKUs with no sales in last 20% of timeframe
                                    cutoff_inactive = max_date - pd.Timedelta(days=int(total_days * 0.2))
                                    active_skus = df_dated[df_dated[date_col] >= cutoff_inactive][product_col].unique()
                                    all_skus = df_dated[product_col].unique()
                                    inactive_skus = [s for s in all_skus if s not in active_skus]
                                    
                                    if inactive_skus:
                                        inactive_ratio = len(inactive_skus) / len(all_skus)
                                        temporal_penalty += min(0.3, inactive_ratio)
                                        for s in inactive_skus[:3]:
                                            watchlist_map[str(s)] = "Inactive"
 
                                    # 2. Declining (2+ drops in volume)
                                    # Use weekly resample
                                    try:
                                        df_dated.set_index(date_col, inplace=True)
                                        weekly = df_dated.groupby(product_col).resample('W').size()
                                        for sku, counts in weekly.groupby(level=0):
                                            if len(counts) >= 3:
                                                vals = counts.values
                                                if vals[-1] < vals[-2] < vals[-3]:
                                                    watchlist_map[str(sku)] = "Declining"
                                                    temporal_penalty += 0.05
                                    except: pass
                                    
                                    # 3. Emerging Spikes
                                    cutoff_spike = max_date - pd.Timedelta(days=int(total_days * 0.1))
                                    recent_vol = df_dated[df_dated.index >= cutoff_spike].groupby(product_col).size()
                                    avg_vol = sales_counts / (total_days / 7) # avg per week
                                    
                                    for sku, r_vol in recent_vol.items():
                                        a_vol = avg_vol.get(sku, 0)
                                        if a_vol > 0 and r_vol > a_vol * 3:
                                            watchlist_map[str(sku)] = "Spiking"
                        except: pass
 
                    penalty = min(1.0, 0.5 * dead_ratio + 0.3 * slow_ratio + 0.2 * temporal_penalty)
                    sku_score = 40.0 * (1.0 - penalty)
 
                    contributing_factors.append(
                        f"SKU activity: {total_skus} products — "
                        f"{dead_ratio * 100:.0f}% dead stock, "
                        f"{slow_ratio * 100:.0f}% slow-moving"
                    )
                else:
                    sku_score = 30.0
                    contributing_factors.append(f"SKU activity: only {total_skus} product(s)")
            except Exception: pass
 
        # ── Component 2: Quantity Movement Score (0–30 pts) ──────────────────
        qty_score = 15.0
        has_quantity_data = False
 
        if qty_col:
            try:
                qty_vals = pd.to_numeric(df[qty_col], errors="coerce").dropna()
                n_qty = len(qty_vals)
 
                if n_qty >= 2:
                    neg_return_ratio = float((qty_vals <= 0).sum() / n_qty)
                    zero_qty_ratio = float((qty_vals == 0).sum() / n_qty)
                    
                    # CV and Volatility Watchlist
                    pos_qty = qty_vals[qty_vals > 0]
                    qty_cv = 0.0
                    if len(pos_qty) >= 2 and pos_qty.mean() > 0.0:
                        qty_cv = float(abs(pos_qty.std() / pos_qty.mean()))
                        
                        if qty_cv > 1.5:
                            high_vol_skus = df[pd.to_numeric(df[qty_col], errors='coerce') > pos_qty.mean() + 2*pos_qty.std()]
                            if not high_vol_skus.empty and product_col:
                                for s in high_vol_skus[product_col].unique()[:2]:
                                    watchlist_map[str(s)] = "High Volatility"
 
                    return_penalty = min(1.0, neg_return_ratio * 3.0)
                    cv_penalty = min(1.0, qty_cv / 3.0)
                    qty_penalty = min(1.0, 0.5 * return_penalty + 0.3 * cv_penalty + 0.2 * zero_qty_ratio)
                    qty_score = 30.0 * (1.0 - qty_penalty)
                    has_quantity_data = True
 
                    contributing_factors.append(
                        f"Quantity movement: {neg_return_ratio * 100:.0f}% zero/negative qty, "
                        f"CV={qty_cv:.2f}"
                    )
            except Exception: pass
 
        # ── Component 3: Stock Level Score (0–30 pts) ────────────────────────
        stock_score = 15.0
        has_stock_data = False
 
        if stock_col:
            try:
                stock_vals = pd.to_numeric(df[stock_col], errors="coerce").dropna()
                n_stock = len(stock_vals)
 
                if n_stock >= 2:
                    median_stock = float(stock_vals.median())
                    zero_stock_ratio = float((stock_vals == 0).sum() / n_stock)
                    neg_stock_ratio = float((stock_vals < 0).sum() / n_stock)
                    overstock_threshold = max(median_stock * 3.0, 1.0)
                    high_stock_ratio = float((stock_vals > overstock_threshold).sum() / n_stock)
 
                    stock_penalty = min(1.0, 0.5 * zero_stock_ratio + 0.3 * neg_stock_ratio + 0.2 * high_stock_ratio)
                    stock_score = 30.0 * (1.0 - stock_penalty)
                    has_stock_data = True
 
                    contributing_factors.append(
                        f"Stock levels: {zero_stock_ratio * 100:.0f}% stockout, "
                        f"{high_stock_ratio * 100:.0f}% overstock risk"
                    )
            except Exception: pass
 
        # ── Final score ───────────────────────────────────────────────────────
        score = round(min(100.0, max(0.0, sku_score + qty_score + stock_score)), 1)
 
        # ── Confidence logic (No capping, just markers) ───────────────────────
        confidence_reason: Optional[str] = None
        if n < 10:
            confidence = "low"
            confidence_reason = "Extremely small dataset (n<10); score reflects directional trends only."
        elif n < 50:
            confidence = "low" 
            confidence_reason = "Limited sample size (n<50); inventory patterns may not be fully representative."
        elif not (has_product_data and has_quantity_data):
            confidence = "medium"
            confidence_reason = "Reduced signal variety; missing key product or quantity movement metrics."
        else:
            confidence = "high"
 
        # ── Watchlist formatting ──────────────────────────────────────────────
        watchlist = []
        for sku, reason in watchlist_map.items():
            watchlist.append(f"{sku} ({reason})")
        watchlist = watchlist[:8] # Cap at 8 items
 
        sources = []
        if has_product_data: sources.append("product activity")
        if has_quantity_data: sources.append("quantity movement")
        if has_stock_data: sources.append("stock levels")
        if has_date_data: sources.append("temporal trends")
        data_source = " + ".join(sources) if sources else "transaction patterns"

        # ── Dead stock / slow-moving inventory with rupee value ───────────────
        # Resolve SKU/date columns with the niche-aware entity detector so Tally
        # exports ("Stock Item", "Voucher Date") are recognised; fall back to the
        # legacy detectors used by the health score itself.
        from app.services.insight_engine.entity_detector import (
            detect_sku_column as _detect_sku,
            detect_date_column as _detect_date,
        )
        ds_product_col = _detect_sku(df)[0] or product_col
        ds_date_col = _detect_date(df)[0] or date_col
        dead_stock_skus = None
        total_dead_stock_value = None
        dead_stock_count = None
        dead_stock_window_days = None
        if ds_product_col and ds_date_col:
            ds = _compute_dead_stock(df, ds_product_col, ds_date_col, dead_stock_days)
            if ds is not None:
                dead_stock_skus = ds["skus"] or None
                total_dead_stock_value = ds["total_value"]
                dead_stock_count = ds["count"]
                dead_stock_window_days = ds["window_days"]
                if dead_stock_count:
                    if total_dead_stock_value is not None:
                        from app.services.insight_engine.entity_detector import format_inr_lakh
                        contributing_factors.append(
                            f"Dead stock: {dead_stock_count} SKU(s) idle {dead_stock_window_days}+ days, "
                            f"~{format_inr_lakh(total_dead_stock_value)} of capital tied up"
                        )
                    else:
                        contributing_factors.append(
                            f"Dead stock: {dead_stock_count} SKU(s) idle {dead_stock_window_days}+ days"
                        )

        return InventoryHealthResult(
            score=score,
            label=_label_from_score(score),
            confidence=confidence,
            confidence_reason=confidence_reason,
            explanation=_build_explanation(score, has_product_data, has_quantity_data, has_stock_data, has_date_data),
            contributing_factors=contributing_factors,
            data_source=data_source,
            has_product_data=has_product_data,
            has_quantity_data=has_quantity_data,
            has_stock_data=has_stock_data,
            has_date_data=has_date_data,
            watchlist=watchlist if watchlist else None,
            dead_stock_skus=dead_stock_skus,
            total_dead_stock_value=total_dead_stock_value,
            dead_stock_count=dead_stock_count,
            dead_stock_window_days=dead_stock_window_days,
        )
 
    except Exception:
        return None
