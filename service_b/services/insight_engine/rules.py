import pandas as pd
import numpy as np
from typing import List, Optional

from schemas.insight.insights import Insight


def revenue_drop_rule(metric_delta) -> Insight | None:
    if metric_delta.name == "revenue" and metric_delta.percent_change < -10:
        return Insight(
            code="REVENUE_DROP",
            severity="high",
            title="Significant revenue drop detected",
            description=f"Revenue dropped by {abs(metric_delta.percent_change):.1f}%",
            affected_metric="revenue",
        )
    return None


def revenue_increase_rule(metric_delta) -> Optional[Insight]:
    """Generate insight when revenue increases significantly vs baseline."""
    if metric_delta.name == "revenue" and metric_delta.percent_change > 10:
        return Insight(
            code="REVENUE_INCREASE",
            severity="low",
            title="Significant revenue increase detected",
            description=(
                f"Revenue increased by {metric_delta.percent_change:.1f}% "
                f"from ${metric_delta.baseline:,.2f} to ${metric_delta.current:,.2f}."
            ),
            affected_metric="revenue",
        )
    return None


def revenue_moderate_change_rule(metric_delta) -> Optional[Insight]:
    """Generate insight for moderate revenue changes (-10% to +10%, non-zero)."""
    if metric_delta.name != "revenue" or metric_delta.baseline == 0:
        return None
    pct = metric_delta.percent_change
    if -10 <= pct <= 10 and abs(pct) > 1:
        direction = "increased" if pct > 0 else "decreased"
        return Insight(
            code="REVENUE_STABLE",
            severity="low",
            title="Revenue remains relatively stable",
            description=(
                f"Revenue {direction} by {abs(pct):.1f}% compared to baseline. "
                f"Current: ${metric_delta.current:,.2f}, Baseline: ${metric_delta.baseline:,.2f}."
            ),
            affected_metric="revenue",
        )
    return None


def avg_revenue_per_row_rule(
    df: pd.DataFrame,
    revenue_col: str,
) -> Optional[Insight]:
    """Generate insight for average revenue per transaction/row."""
    vals = pd.to_numeric(df[revenue_col], errors="coerce").dropna()
    if vals.empty:
        return None

    avg_val = vals.mean()
    median_val = vals.median()

    # Skew detection: if mean >> median, distribution is right-skewed
    skew_note = ""
    if median_val > 0 and avg_val > 0:
        ratio = avg_val / median_val
        if ratio > 2.0:
            skew_note = (
                f" The median (${median_val:,.2f}) is significantly lower than the mean, "
                f"indicating a right-skewed distribution with high-value outliers."
            )

    return Insight(
        code="AVG_REVENUE_PER_ROW",
        severity="low",
        title="Average revenue per transaction",
        description=(
            f"Average revenue per row is ${avg_val:,.2f} across {len(vals):,} records.{skew_note}"
        ),
        affected_metric="revenue",
    )


def revenue_concentration_rule(
    df: pd.DataFrame,
    revenue_col: str,
) -> Optional[Insight]:
    """Check if top 10% of rows generate a disproportionate share of revenue."""
    vals = pd.to_numeric(df[revenue_col], errors="coerce").dropna()
    if len(vals) < 10 or vals.sum() == 0:
        return None

    sorted_vals = vals.sort_values(ascending=False)
    top_n = max(1, int(len(sorted_vals) * 0.10))
    top_sum = sorted_vals.head(top_n).sum()
    contrib = (top_sum / vals.sum()) * 100

    if contrib > 60:
        severity = "high"
        desc = (
            f"Revenue is heavily concentrated: top 10% of transactions "
            f"generate {contrib:.1f}% of total revenue. "
            f"This creates dependency risk on a small number of high-value records."
        )
    elif contrib > 40:
        severity = "medium"
        desc = (
            f"Moderate revenue concentration detected: top 10% of transactions "
            f"account for {contrib:.1f}% of total revenue."
        )
    else:
        severity = "low"
        desc = (
            f"Revenue is well-distributed across transactions. "
            f"Top 10% accounts for {contrib:.1f}% of total revenue."
        )

    return Insight(
        code="REVENUE_CONCENTRATION",
        severity=severity,
        title="Revenue concentration analysis",
        description=desc,
        affected_metric="revenue",
    )


def revenue_volatility_rule(
    df: pd.DataFrame,
    revenue_col: str,
) -> Optional[Insight]:
    """Assess revenue volatility using coefficient of variation."""
    vals = pd.to_numeric(df[revenue_col], errors="coerce").dropna()
    if len(vals) < 2 or vals.mean() == 0:
        return None

    cv = abs(vals.std() / vals.mean())

    if cv > 0.7:
        severity = "high"
        desc = (
            f"High revenue volatility detected (CV={cv:.2f}). "
            f"Transaction values vary significantly, indicating unpredictable revenue streams."
        )
    elif cv > 0.3:
        severity = "medium"
        desc = (
            f"Moderate revenue volatility (CV={cv:.2f}). "
            f"Some variation in transaction values across the dataset."
        )
    else:
        severity = "low"
        desc = (
            f"Revenue volatility is low (CV={cv:.2f}). "
            f"Income streams appear stable and predictable."
        )

    return Insight(
        code="REVENUE_VOLATILITY",
        severity=severity,
        title="Revenue stability assessment",
        description=desc,
        affected_metric="revenue",
    )


def revenue_distribution_rule(
    df: pd.DataFrame,
    revenue_col: str,
) -> Optional[Insight]:
    """Provide quartile distribution of revenue values."""
    vals = pd.to_numeric(df[revenue_col], errors="coerce").dropna()
    if len(vals) < 4:
        return None

    q25 = vals.quantile(0.25)
    q50 = vals.quantile(0.50)
    q75 = vals.quantile(0.75)
    min_val = vals.min()
    max_val = vals.max()

    return Insight(
        code="REVENUE_DISTRIBUTION",
        severity="low",
        title="Revenue distribution profile",
        description=(
            f"Revenue ranges from ${min_val:,.2f} to ${max_val:,.2f}. "
            f"25th percentile: ${q25:,.2f}, median: ${q50:,.2f}, 75th percentile: ${q75:,.2f}."
        ),
        affected_metric="revenue",
    )


# -----------------------------------------------------------------------
# Product-Level Ecommerce Insights
# -----------------------------------------------------------------------

PRODUCT_COLUMN_CANDIDATES = [
    "product", "product_name", "item", "sku", "description",
    "product_id", "item_name", "product_category", "category",
]


def _detect_product_column(df: pd.DataFrame) -> Optional[str]:
    """Detect product-like column in the DataFrame. Returns None if not found."""
    cols_lower = {col.lower().strip(): col for col in df.columns}
    for candidate in PRODUCT_COLUMN_CANDIDATES:
        if candidate in cols_lower:
            return cols_lower[candidate]
    return None


def top_product_rule(
    df: pd.DataFrame,
    revenue_col: str,
) -> Optional[Insight]:
    """Identify top-performing product by revenue."""
    product_col = _detect_product_column(df)
    if product_col is None:
        return None

    rev_series = pd.to_numeric(df[revenue_col], errors="coerce")
    product_rev = df.assign(__rev=rev_series).groupby(product_col)["__rev"].sum()
    product_rev = product_rev.dropna().sort_values(ascending=False)

    if product_rev.empty or product_rev.sum() == 0:
        return None

    top_name = product_rev.index[0]
    top_val = product_rev.iloc[0]
    top_pct = (top_val / product_rev.sum()) * 100

    return Insight(
        code="TOP_PRODUCT",
        severity="low" if top_pct < 30 else "medium",
        title="Top-performing product identified",
        description=(
            f"'{top_name}' is the highest revenue product, contributing "
            f"${top_val:,.2f} ({top_pct:.1f}% of total revenue)."
        ),
        affected_metric="revenue",
    )


def product_concentration_rule(
    df: pd.DataFrame,
    revenue_col: str,
) -> Optional[Insight]:
    """Check if revenue is concentrated among a few products."""
    product_col = _detect_product_column(df)
    if product_col is None:
        return None

    rev_series = pd.to_numeric(df[revenue_col], errors="coerce")
    product_rev = df.assign(__rev=rev_series).groupby(product_col)["__rev"].sum()
    product_rev = product_rev.dropna().sort_values(ascending=False)

    if len(product_rev) < 3 or product_rev.sum() == 0:
        return None

    top3_sum = product_rev.head(3).sum()
    top3_pct = (top3_sum / product_rev.sum()) * 100

    if top3_pct > 70:
        severity = "high"
        desc = (
            f"Revenue is heavily concentrated: top 3 products generate "
            f"{top3_pct:.1f}% of total revenue out of {len(product_rev)} products. "
            f"This creates high product dependency risk."
        )
    elif top3_pct > 50:
        severity = "medium"
        desc = (
            f"Moderate product concentration: top 3 products account for "
            f"{top3_pct:.1f}% of total revenue across {len(product_rev)} products."
        )
    else:
        severity = "low"
        desc = (
            f"Revenue is well-distributed across {len(product_rev)} products. "
            f"Top 3 products account for {top3_pct:.1f}% of total revenue."
        )

    return Insight(
        code="PRODUCT_CONCENTRATION",
        severity=severity,
        title="Product revenue concentration",
        description=desc,
        affected_metric="revenue",
    )


def underperforming_products_rule(
    df: pd.DataFrame,
    revenue_col: str,
) -> Optional[Insight]:
    """Identify underperforming products (bottom 20% by revenue)."""
    product_col = _detect_product_column(df)
    if product_col is None:
        return None

    rev_series = pd.to_numeric(df[revenue_col], errors="coerce")
    product_rev = df.assign(__rev=rev_series).groupby(product_col)["__rev"].sum()
    product_rev = product_rev.dropna().sort_values(ascending=False)

    if len(product_rev) < 5 or product_rev.sum() == 0:
        return None

    bottom_n = max(1, int(len(product_rev) * 0.20))
    bottom_sum = product_rev.tail(bottom_n).sum()
    bottom_pct = (bottom_sum / product_rev.sum()) * 100

    return Insight(
        code="UNDERPERFORMING_PRODUCTS",
        severity="medium" if bottom_pct < 5 else "low",
        title="Underperforming products identified",
        description=(
            f"Bottom {bottom_n} products ({int(bottom_n / len(product_rev) * 100)}% of catalog) "
            f"generate only ${bottom_sum:,.2f} ({bottom_pct:.1f}% of total revenue)."
        ),
        affected_metric="revenue",
    )


def product_baseline_comparison_rule(
    current_df: pd.DataFrame,
    baseline_df: Optional[pd.DataFrame],
    revenue_col: str,
    baseline_revenue_col: Optional[str],
) -> List[Insight]:
    """Compare product revenue between current and baseline periods."""
    if baseline_df is None or baseline_revenue_col is None:
        return []

    product_col_current = _detect_product_column(current_df)
    product_col_baseline = _detect_product_column(baseline_df)

    if product_col_current is None or product_col_baseline is None:
        return []

    cur_rev = pd.to_numeric(current_df[revenue_col], errors="coerce")
    cur_by_product = current_df.assign(__rev=cur_rev).groupby(product_col_current)["__rev"].sum()

    base_rev = pd.to_numeric(baseline_df[baseline_revenue_col], errors="coerce")
    base_by_product = baseline_df.assign(__rev=base_rev).groupby(product_col_baseline)["__rev"].sum()

    # Only compare products present in both periods
    common = cur_by_product.index.intersection(base_by_product.index)
    if len(common) == 0:
        return []

    insights: List[Insight] = []

    # Find biggest gainer
    changes = {}
    for product in common:
        cur_val = cur_by_product[product]
        base_val = base_by_product[product]
        if base_val > 0:
            pct_change = ((cur_val - base_val) / base_val) * 100
            changes[product] = pct_change

    if not changes:
        return []

    # Top gainer
    top_gainer = max(changes, key=changes.get)
    top_pct = changes[top_gainer]
    if abs(top_pct) > 5:
        direction = "increased" if top_pct > 0 else "decreased"
        insights.append(Insight(
            code="PRODUCT_REVENUE_CHANGE",
            severity="low" if abs(top_pct) < 30 else "medium",
            title=f"Notable product revenue change",
            description=(
                f"Product '{top_gainer}' revenue {direction} {abs(top_pct):.1f}% "
                f"compared to baseline period."
            ),
            affected_metric="revenue",
        ))

    return insights
