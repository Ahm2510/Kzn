import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List, Tuple
from pydantic import BaseModel

class ProductWatchItem(BaseModel):
    product: str                           # Product name/label
    status: str                            # "watch", "improving", "declining", "unstable", "low_confidence", "insufficient_data"
    reason: str                            # Human-readable reason for watch status
    revenue: float                         # Total revenue for this product
    revenue_share_pct: float               # Share of total revenue (%)
    transaction_count: int                 # Number of transactions
    trend_direction: Optional[str] = None  # "up", "down", "flat", "insufficient_data"
    momentum: Optional[str] = None         # "accelerating", "decelerating", "steady", None
    volatility: Optional[str] = None       # "high", "moderate", "low", None
    confidence: str = "medium"             # "high", "medium", "low"
    severity: str = "medium"               # "high", "medium", "low"
    action_direction: Optional[str] = None # Recommended action
    warning: Optional[str] = None          # Any data quality note

class EnhancedProductsToWatchResult(BaseModel):
    products: List[ProductWatchItem] = []  # Ranked list
    product_count: int = 0                 # Count of flagged products
    total_products_analyzed: int = 0       # Total unique products in dataset
    has_declining: bool = False            # Quick flags
    has_unstable: bool = False
    confidence: str = "medium"
    warning: Optional[str] = None

def _detect_product_column(df: pd.DataFrame) -> Optional[str]:
    product_col_candidates = [
        "product", "product_name", "item", "sku", "description",
        "product_id", "item_name", "product_category", "category",
    ]
    cols_lower = {col.lower().strip(): col for col in df.columns}
    return next((cols_lower[c] for c in product_col_candidates if c in cols_lower), None)

def _detect_date_column(df: pd.DataFrame) -> Optional[str]:
    date_col_candidates = ["date", "order_date", "invoice_date", "transaction_date", "created_at", "invoicedate"]
    cols_lower = {col.lower().strip(): col for col in df.columns}
    return next((cols_lower[c] for c in date_col_candidates if c in cols_lower), None)

def _build_action(status: str) -> Optional[str]:
    if status == "declining":
        return "Investigate root cause of decline — check pricing, availability, competitive pressure, and seasonal patterns."
    elif status == "unstable":
        return "Review transaction patterns for this product — high variance may indicate promotional dependency or irregular demand."
    elif status == "watch":
        return "Monitor closely in next period — if underperformance persists, consider repositioning or phasing out."
    elif status == "improving":
        return "Positive trajectory — consider increasing investment, visibility, or inventory allocation."
    elif status == "low_confidence":
        return "Collect more data before making decisions — sample size is insufficient for reliable assessment."
    return None

def compute_enhanced_products_to_watch(
    df: pd.DataFrame,
    revenue_column: str,
) -> Optional[EnhancedProductsToWatchResult]:
    """
    Computes an enhanced, actionable product watchlist using deterministic rules.
    """
    try:
        # Step 1: Detect Columns
        product_col = _detect_product_column(df)
        if not product_col:
            return None
        
        date_col = _detect_date_column(df)
        
        # Step 2: Aggregates
        rev_series = pd.to_numeric(df[revenue_column], errors="coerce")
        work = df.assign(__rev=rev_series).dropna(subset=["__rev", product_col])
        work = work[work["__rev"] > 0]
        
        if work.empty:
            return None
            
        grouped = work.groupby(product_col).agg(
            revenue=("__rev", "sum"),
            txn_count=("__rev", "count"),
            mean_rev=("__rev", "mean"),
            std_rev=("__rev", "std"),
        ).reset_index()
        
        total_rev = float(grouped["revenue"].sum())
        total_products = len(grouped)
        
        if total_rev == 0 or total_products == 0:
            return None
            
        grouped["revenue_share_pct"] = (grouped["revenue"] / total_rev) * 100
        grouped["cv"] = grouped["std_rev"] / grouped["mean_rev"].replace(0, np.nan)
        
        # Step 3: Trend Analysis (if date available)
        growth_map = {}
        h2_share_map = {}
        if date_col:
            work["__date"] = pd.to_datetime(work[date_col], errors="coerce")
            valid_dates = work.dropna(subset=["__date"])
            if len(valid_dates) > 10:
                midpoint = valid_dates["__date"].quantile(0.5)
                first_half = valid_dates[valid_dates["__date"] <= midpoint]
                second_half = valid_dates[valid_dates["__date"] > midpoint]
                
                rev_h1 = first_half.groupby(product_col)["__rev"].sum()
                rev_h2 = second_half.groupby(product_col)["__rev"].sum()
                
                # Growth: (H2 - H1) / H1
                growth_map = (((rev_h2 - rev_h1) / rev_h1.replace(0, np.nan)) * 100).to_dict()
                
                # H2 Share of product total
                prod_total = rev_h1.add(rev_h2, fill_value=0)
                h2_share_map = (rev_h2 / prod_total.replace(0, np.nan)).to_dict()
                
        # Step 4: Rule Engine
        products = []
        for _, row in grouped.iterrows():
            prod_name = str(row[product_col])
            rev = float(row["revenue"])
            share = float(row["revenue_share_pct"])
            txns = int(row["txn_count"])
            cv = float(row["cv"]) if not np.isnan(row["cv"]) else 0.0
            
            growth = growth_map.get(prod_name)
            h2_share = h2_share_map.get(prod_name)
            
            status = "stable"
            severity = "low"
            reasons = []
            
            # Rule: Consistent underperformer
            is_underperformer = share < 2.0 and txns > 5 # Arbitrary threshold for "underperformer"
            if is_underperformer:
                status = "watch"
                severity = "medium"
                reasons.append(f"Bottom-tier revenue contributor ({share:.1f}% share)")
                
            # Rule: Declining trend
            if growth is not None:
                if growth < -15 and txns >= 10:
                    status = "declining"
                    severity = "high"
                    reasons.append(f"Revenue declined {abs(growth):.0f}% between first and second half of the period")
                elif growth > 15 and txns >= 10 and status != "declining":
                    status = "improving"
                    severity = "low"
                    reasons.append(f"Revenue grew {growth:.0f}% between first and second half")
                    
            # Rule: Instability
            if cv > 1.0 and txns >= 8:
                # Severity update only if not already high
                if severity != "high":
                    status = "unstable"
                    severity = "medium"
                reasons.append(f"High revenue volatility (CV: {cv:.2f}) indicates unpredictable performance")
                
            # Rule: Momentum
            if h2_share is not None and h2_share < 0.4 and txns >= 10:
                if status != "declining":
                    status = "declining"
                    severity = "medium"
                reasons.append(f"Weak recent momentum — only {h2_share*100:.0f}% of revenue came in the later half")
                
            # Rule: Low confidence
            if txns < 5 and share > 1.0:
                status = "low_confidence"
                severity = "low"
                reasons.append("Small sample size reduces reliability of performance metrics")
            elif txns < 3:
                status = "insufficient_data"
                severity = "low"
            
            if status != "stable" and status != "insufficient_data":
                products.append(ProductWatchItem(
                    product=prod_name,
                    status=status,
                    reason="; ".join(reasons) if reasons else "Selected for portfolio review",
                    revenue=round(rev, 2),
                    revenue_share_pct=round(share, 2),
                    transaction_count=txns,
                    trend_direction="down" if growth and growth < -5 else "up" if growth and growth > 5 else "flat" if date_col else "insufficient_data",
                    momentum="decelerating" if h2_share and h2_share < 0.4 else "accelerating" if h2_share and h2_share > 0.6 else "steady" if date_col else None,
                    volatility="high" if cv > 0.7 else "moderate" if cv > 0.3 else "low",
                    confidence="high" if txns >= 50 else "medium" if txns >= 10 else "low",
                    severity=severity,
                    action_direction=_build_action(status)
                ))
                
        # Sort and return
        severity_order = {"high": 0, "medium": 1, "low": 2}
        products.sort(key=lambda p: (severity_order.get(p.severity, 3), -p.revenue_share_pct))
        
        return EnhancedProductsToWatchResult(
            products=products[:10],
            product_count=len(products),
            total_products_analyzed=total_products,
            has_declining=any(p.status == "declining" for p in products),
            has_unstable=any(p.status == "unstable" for p in products),
            confidence="high" if total_products > 20 else "medium",
            warning="Limited product data" if total_products < 5 else None
        )
    except Exception:
        return None
