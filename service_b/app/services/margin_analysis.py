"""
Kaizen Margin Analysis Service — V1.0

Detects cost columns and computes gross margin metrics.
Schema-agnostic: silently returns None if no cost column exists.
Never blocks the main analysis pipeline.
"""

from __future__ import annotations
import logging
import pandas as pd
import numpy as np
from typing import Optional, List
from pydantic import BaseModel

logger = logging.getLogger(__name__)

COST_SYNONYMS = [
    "cost_of_goods", "cogs", "unit_cost", "cost_price", "purchase_price",
    "cost", "total_cost", "product_cost", "landed_cost", "cost_of_sales",
    "variable_cost", "material_cost",
]

MIN_ROWS_FOR_MARGIN = 5


class ProductMarginRow(BaseModel):
    product: str
    revenue: float
    cost: float
    gross_profit: float
    margin_pct: float
    tier: str           # "healthy" | "thin" | "loss_making"
    revenue_share_pct: float
    watchlist: bool


class MarginAnalysisResult(BaseModel):
    total_revenue: float
    total_cost: float
    total_gross_profit: float
    overall_margin_pct: float
    margin_health: str              # "healthy" | "moderate" | "thin" | "critical"
    margin_health_explanation: str
    revenue_column_used: str
    cost_column_used: str
    has_product_breakdown: bool
    product_breakdown: Optional[List[ProductMarginRow]] = None
    products_loss_making: int
    products_thin_margin: int        # margin < 10%
    products_healthy: int            # margin >= 20%
    baseline_margin_pct: Optional[float] = None
    margin_change_pct: Optional[float] = None
    margin_direction: Optional[str] = None
    confidence: str
    confidence_reason: str
    warning: Optional[str] = None
    sample_size: int


def _detect_cost_column(df: pd.DataFrame) -> Optional[str]:
    """Detect the most likely cost column. Returns None if not found."""
    cols_lower = {col.lower().strip(): col for col in df.columns}
    for syn in COST_SYNONYMS:
        if syn in cols_lower:
            return cols_lower[syn]
    return None


def _classify_margin_tier(margin_pct: float) -> str:
    if margin_pct < 0:
        return "loss_making"
    elif margin_pct < 10:
        return "thin"
    elif margin_pct < 20:
        return "moderate"
    else:
        return "healthy"


def compute_margin_analysis(
    current_df: pd.DataFrame,
    revenue_column: str,
    baseline_df: Optional[pd.DataFrame] = None,
    baseline_revenue_column: Optional[str] = None,
) -> Optional[MarginAnalysisResult]:
    """
    Main entry point. Returns None if no cost column detected or data insufficient.
    """
    try:
        cost_col = _detect_cost_column(current_df)
        if cost_col is None:
            return None  # Silently skip — no cost data

        df = current_df.copy()
        df["__revenue"] = pd.to_numeric(df[revenue_column], errors="coerce")
        df["__cost"] = pd.to_numeric(df[cost_col], errors="coerce")

        # Drop rows where both revenue AND cost are NaN
        df = df.dropna(subset=["__revenue", "__cost"])

        if len(df) < MIN_ROWS_FOR_MARGIN:
            return None

        total_revenue = float(df["__revenue"].sum())
        total_cost = float(df["__cost"].sum())

        if total_revenue == 0:
            return None

        total_gross_profit = total_revenue - total_cost
        overall_margin_pct = (total_gross_profit / total_revenue) * 100

        # Health classification
        if overall_margin_pct >= 30:
            health = "healthy"
            health_explanation = (
                f"Overall gross margin of {overall_margin_pct:.1f}% is healthy — "
                f"the business retains strong value per unit sold."
            )
        elif overall_margin_pct >= 15:
            health = "moderate"
            health_explanation = (
                f"Overall gross margin of {overall_margin_pct:.1f}% is moderate — "
                f"review pricing and cost structure to improve retention."
            )
        elif overall_margin_pct >= 0:
            health = "thin"
            health_explanation = (
                f"Gross margin of {overall_margin_pct:.1f}% is thin — "
                f"the business is covering costs but has very little buffer."
            )
        else:
            health = "critical"
            health_explanation = (
                f"Negative gross margin of {overall_margin_pct:.1f}% — "
                f"costs exceed revenue. Immediate pricing or cost action required."
            )

        # Product-level breakdown
        has_product_breakdown = False
        product_breakdown = None
        products_loss_making = 0
        products_thin = 0
        products_healthy = 0

        product_candidates = [
            "product", "product_name", "item", "sku", "description",
            "product_id", "item_name", "product_category", "category",
        ]
        cols_lower = {col.lower().strip(): col for col in df.columns}
        product_col = next((cols_lower[c] for c in product_candidates if c in cols_lower), None)

        if product_col:
            try:
                grp = df.groupby(product_col).agg(
                    revenue=("__revenue", "sum"),
                    cost=("__cost", "sum"),
                ).reset_index()
                grp = grp[grp["revenue"] > 0].copy()

                if len(grp) > 0:
                    grp["gross_profit"] = grp["revenue"] - grp["cost"]
                    grp["margin_pct"] = (grp["gross_profit"] / grp["revenue"]) * 100
                    grp["revenue_share_pct"] = (grp["revenue"] / total_revenue) * 100
                    grp["tier"] = grp["margin_pct"].apply(_classify_margin_tier)
                    grp["watchlist"] = grp["tier"].isin(["loss_making", "thin"])

                    grp = grp.sort_values("revenue", ascending=False).head(50)  # Cap at 50

                    products_loss_making = int((grp["tier"] == "loss_making").sum())
                    products_thin = int((grp["tier"] == "thin").sum())
                    products_healthy = int((grp["tier"] == "healthy").sum())

                    product_breakdown = [
                        ProductMarginRow(
                            product=str(row[product_col]),
                            revenue=round(float(row["revenue"]), 2),
                            cost=round(float(row["cost"]), 2),
                            gross_profit=round(float(row["gross_profit"]), 2),
                            margin_pct=round(float(row["margin_pct"]), 2),
                            tier=str(row["tier"]),
                            revenue_share_pct=round(float(row["revenue_share_pct"]), 2),
                            watchlist=bool(row["watchlist"]),
                        )
                        for _, row in grp.iterrows()
                    ]
                    has_product_breakdown = True
            except Exception as e:
                logger.debug(f"Product margin breakdown failed: {e}")

        # Baseline comparison
        baseline_margin_pct = None
        margin_change_pct = None
        margin_direction = None

        if baseline_df is not None and baseline_revenue_column is not None:
            try:
                baseline_cost_col = _detect_cost_column(baseline_df)
                if baseline_cost_col:
                    bdf = baseline_df.copy()
                    bdf["__revenue"] = pd.to_numeric(bdf[baseline_revenue_column], errors="coerce")
                    bdf["__cost"] = pd.to_numeric(bdf[baseline_cost_col], errors="coerce")
                    bdf = bdf.dropna(subset=["__revenue", "__cost"])
                    b_rev = float(bdf["__revenue"].sum())
                    b_cost = float(bdf["__cost"].sum())
                    if b_rev > 0:
                        baseline_margin_pct = round(((b_rev - b_cost) / b_rev) * 100, 2)
                        margin_change_pct = round(overall_margin_pct - baseline_margin_pct, 2)
                        margin_direction = (
                            "improving" if margin_change_pct > 1 else
                            "declining" if margin_change_pct < -1 else
                            "stable"
                        )
            except Exception as e:
                logger.debug(f"Baseline margin comparison failed: {e}")

        # Confidence
        n = len(df)
        if n >= 100:
            confidence = "high"
            confidence_reason = f"Computed from {n:,} records with detected cost column '{cost_col}'"
        elif n >= 20:
            confidence = "medium"
            confidence_reason = f"Moderate sample ({n} records) — directionally reliable"
        else:
            confidence = "low"
            confidence_reason = f"Small sample ({n} records) — treat as indicative only"

        warning = None
        if products_loss_making > 0:
            warning = f"{products_loss_making} product(s) are selling below cost. Audit pricing immediately."

        return MarginAnalysisResult(
            total_revenue=round(total_revenue, 2),
            total_cost=round(total_cost, 2),
            total_gross_profit=round(total_gross_profit, 2),
            overall_margin_pct=round(overall_margin_pct, 2),
            margin_health=health,
            margin_health_explanation=health_explanation,
            revenue_column_used=revenue_column,
            cost_column_used=cost_col,
            has_product_breakdown=has_product_breakdown,
            product_breakdown=product_breakdown,
            products_loss_making=products_loss_making,
            products_thin_margin=products_thin,
            products_healthy=products_healthy,
            baseline_margin_pct=baseline_margin_pct,
            margin_change_pct=margin_change_pct,
            margin_direction=margin_direction,
            confidence=confidence,
            confidence_reason=confidence_reason,
            warning=warning,
            sample_size=n,
        )

    except Exception as e:
        logger.warning(f"Margin analysis failed: {e}", exc_info=True)
        return None
