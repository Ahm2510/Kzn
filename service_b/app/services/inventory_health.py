"""
Inventory Health Score (V1 — Additive)
 
Computes a deterministic, normalized 0–100 inventory health score from a sales dataset.
This module is fully standalone — it does not modify any existing computation logic.
 
Score bands:
    80–100  Very Healthy
    60–79   Mostly Healthy
    40–59   Warning
    0–39    Unhealthy
 
Components:
    1. SKU Activity Score     40% weight  (0–40 pts)  requires: product column
    2. Quantity Movement Score 30% weight  (0–30 pts)  requires: quantity column
    3. Stock Level Score      30% weight  (0–30 pts)  requires: stock column
 
If a component's required column is absent, a neutral mid-point is used (20, 15, 15).
This means IHS can still be computed from purely transactional data with no stock column.
"""
from __future__ import annotations
 
from typing import List, Optional
 
import pandas as pd
from pydantic import BaseModel
 
 
class InventoryHealthResult(BaseModel):
    """Structured result for the Inventory Health Score."""
 
    score: float                     # 0–100, rounded to 1 decimal place
    label: str                       # "Very Healthy" / "Mostly Healthy" / "Warning" / "Unhealthy"
    confidence: str                  # "high" / "medium" / "low"
    explanation: str                 # One human-readable paragraph
    contributing_factors: List[str]  # Bullet-ready factor descriptions
    warning: Optional[str] = None    # Set when n < 20 or data is sparse
    data_source: str                 # Human-readable description of what signals were used
    has_product_data: bool           # Whether product/SKU column was detected and used
    has_quantity_data: bool          # Whether quantity column was detected and used
    has_stock_data: bool             # Whether stock-level column was detected and used
    watchlist: Optional[List[str]] = None  # Up to 5 SKUs with single or near-zero transactions
 
 
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
 
 
def _build_explanation(
    score: float,
    has_product: bool,
    has_qty: bool,
    has_stock: bool,
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
 
    if parts:
        data_note = f" Score is based on {' and '.join(parts)}."
    else:
        data_note = ""
 
    return f"{base}{data_note}"
 
 
# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────
 
def compute_inventory_health_score(
    df: pd.DataFrame,
) -> Optional[InventoryHealthResult]:
    """
    Compute the Inventory Health Score.
 
    Returns ``None`` if no inventory-relevant signal exists or any error occurs.
    This function never raises.
 
    Column detection is performed internally using lightweight case-insensitive matching.
    No revenue column is required — the function works on product/quantity/stock signals.
    """
    try:
        n = len(df)
        if n < 2:
            return None
 
        product_col = _detect_product_col(df)
        qty_col = _detect_qty_col(df)
        stock_col = _detect_stock_col(df)
 
        # Require at least one inventory-relevant signal to proceed
        if not product_col and not qty_col and not stock_col:
            return None
 
        contributing_factors: List[str] = []
        watchlist: Optional[List[str]] = None
 
        # ── Component 1: SKU Activity Score (0–40 pts) ───────────────────────
        # Neutral = 20.0 when no product column (no penalty for non-product datasets)
        sku_score = 20.0
        has_product_data = False
 
        if product_col:
            try:
                sales_counts = df.groupby(product_col).size()
                total_skus = len(sales_counts)
 
                if total_skus >= 2:
                    # Dead SKUs: appeared only once (barely moved in the entire period)
                    dead_skus = int((sales_counts == 1).sum())
                    dead_ratio = dead_skus / total_skus
 
                    # Slow SKUs: below 15th percentile of sales counts
                    slow_threshold = float(sales_counts.quantile(0.15))
                    slow_skus = int((sales_counts < slow_threshold).sum())
                    slow_ratio = slow_skus / total_skus
 
                    # Dead SKUs weighted 60%, slow SKUs 40%
                    penalty = min(1.0, 0.6 * dead_ratio + 0.4 * slow_ratio)
                    sku_score = 40.0 * (1.0 - penalty)
                    has_product_data = True
 
                    contributing_factors.append(
                        f"SKU activity: {total_skus} products — "
                        f"{dead_ratio * 100:.0f}% single-transaction (dead stock risk), "
                        f"{slow_ratio * 100:.0f}% slow-moving"
                    )
 
                    # Watchlist: SKUs appearing exactly once
                    dead_names = sales_counts[sales_counts == 1].index.tolist()
                    if dead_names:
                        watchlist = [str(s) for s in dead_names[:5]]
 
                else:
                    # Too few distinct SKUs to evaluate distribution
                    sku_score = 30.0
                    has_product_data = True
                    contributing_factors.append(
                        f"SKU activity: only {total_skus} product(s) — "
                        "insufficient variety for distribution analysis"
                    )
            except Exception:
                pass  # Keep sku_score = 20.0 neutral
 
        # ── Component 2: Quantity Movement Score (0–30 pts) ──────────────────
        # Neutral = 15.0 when no quantity column
        qty_score = 15.0
        has_quantity_data = False
 
        if qty_col:
            try:
                qty_vals = pd.to_numeric(df[qty_col], errors="coerce")
                qty_numeric = qty_vals.dropna()
                n_qty = len(qty_numeric)
 
                if n_qty >= 2:
                    # Returns / cancellations: quantity <= 0
                    neg_return_ratio = float((qty_numeric <= 0).sum() / n_qty)
 
                    # Zero-quantity rows (unshipped / voided orders)
                    zero_qty_ratio = float((qty_numeric == 0).sum() / n_qty)
 
                    # CV of positive quantities (erratic ordering patterns)
                    pos_qty = qty_numeric[qty_numeric > 0]
                    qty_cv = 0.0
                    if len(pos_qty) >= 2 and pos_qty.mean() > 0.0:
                        qty_cv = float(abs(pos_qty.std() / pos_qty.mean()))
 
                    # 50% weight on returns, 30% on volatility, 20% on zero-qty
                    return_penalty = min(1.0, neg_return_ratio * 3.0)
                    cv_penalty = min(1.0, qty_cv / 3.0)
                    qty_penalty = min(
                        1.0,
                        0.5 * return_penalty
                        + 0.3 * cv_penalty
                        + 0.2 * zero_qty_ratio,
                    )
                    qty_score = 30.0 * (1.0 - qty_penalty)
                    has_quantity_data = True
 
                    contributing_factors.append(
                        f"Quantity movement: {neg_return_ratio * 100:.0f}% zero/negative qty "
                        f"(returns risk), CV={qty_cv:.2f}"
                    )
            except Exception:
                pass  # Keep qty_score = 15.0 neutral
 
        # ── Component 3: Stock Level Score (0–30 pts) ────────────────────────
        # Neutral = 15.0 when no stock column
        stock_score = 15.0
        has_stock_data = False
 
        if stock_col:
            try:
                stock_vals = pd.to_numeric(df[stock_col], errors="coerce").dropna()
                n_stock = len(stock_vals)
 
                if n_stock >= 2:
                    median_stock = float(stock_vals.median())
 
                    # Stockouts: zero stock on hand
                    zero_stock_ratio = float((stock_vals == 0).sum() / n_stock)
 
                    # Negative stock: over-selling / data error
                    neg_stock_ratio = float((stock_vals < 0).sum() / n_stock)
 
                    # Overstock: more than 3× the median (trapped cash risk)
                    overstock_threshold = max(median_stock * 3.0, 1.0)
                    high_stock_ratio = float(
                        (stock_vals > overstock_threshold).sum() / n_stock
                    )
 
                    # 50% stockout, 30% negative, 20% overstock
                    stock_penalty = min(
                        1.0,
                        0.5 * zero_stock_ratio
                        + 0.3 * neg_stock_ratio
                        + 0.2 * high_stock_ratio,
                    )
                    stock_score = 30.0 * (1.0 - stock_penalty)
                    has_stock_data = True
 
                    contributing_factors.append(
                        f"Stock levels: {zero_stock_ratio * 100:.0f}% stockout, "
                        f"{high_stock_ratio * 100:.0f}% potential overstock"
                    )
            except Exception:
                pass  # Keep stock_score = 15.0 neutral
 
        # ── Final score ───────────────────────────────────────────────────────
        raw = sku_score + qty_score + stock_score
        score = round(min(100.0, max(0.0, raw)), 1)
 
        # ── Low-sample cap ────────────────────────────────────────────────────
        warning: Optional[str] = None
        if n < 10:
            score = min(score, 50.0)
            warning = (
                "Fewer than 10 records available; "
                "inventory health score is directional only."
            )
        elif n < 20:
            score = min(score, 65.0)
            warning = "Low data volume; inventory health score may not be fully representative."
 
        # ── Label ─────────────────────────────────────────────────────────────
        label = _label_from_score(score)
 
        # ── Confidence ────────────────────────────────────────────────────────
        if n >= 50 and has_product_data and has_quantity_data:
            confidence = "high"
        elif n >= 20 and (has_product_data or has_quantity_data):
            confidence = "medium"
        else:
            confidence = "low"
 
        # ── Data source description ───────────────────────────────────────────
        sources = []
        if has_product_data:
            sources.append("product activity")
        if has_quantity_data:
            sources.append("quantity movement")
        if has_stock_data:
            sources.append("stock levels")
        data_source = " + ".join(sources) if sources else "transaction patterns"
 
        return InventoryHealthResult(
            score=score,
            label=label,
            confidence=confidence,
            explanation=_build_explanation(score, has_product_data, has_quantity_data, has_stock_data),
            contributing_factors=contributing_factors,
            warning=warning,
            data_source=data_source,
            has_product_data=has_product_data,
            has_quantity_data=has_quantity_data,
            has_stock_data=has_stock_data,
            watchlist=watchlist,
        )
 
    except Exception:
        return None
