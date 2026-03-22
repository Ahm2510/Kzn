import logging
from typing import List, Optional
import pandas as pd

from app.schemas.insight.insights import Insight

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Comparative rules (require baseline)
# ---------------------------------------------------------------------------

def revenue_drop_rule(metric_delta) -> Optional[Insight]:
    if metric_delta.name == "revenue" and metric_delta.percent_change < -10:
        pct = abs(metric_delta.percent_change)
        lost = abs(metric_delta.absolute_change)
        return Insight(
            code="REVENUE_DROP",
            severity="high",
            title="Significant revenue drop detected",
            description=(
                f"Revenue dropped by {pct:.1f}% compared to baseline, "
                f"a decline of ${lost:,.2f} in absolute terms."
            ),
            affected_metric="revenue",
            driver=f"Revenue contracted from ${metric_delta.baseline:,.2f} to ${metric_delta.current:,.2f} ({pct:.1f}% decline)",
            implication="This decline may indicate weakening demand, customer churn, or pricing pressure that requires immediate attention.",
            action_direction="Investigate top revenue segments for drop-off; review pricing, retention, and acquisition funnels.",
            confidence="HIGH" if pct >= 20 else "MEDIUM",
            confidence_basis=f"Based on {pct:.1f}% change between full baseline (${metric_delta.baseline:,.2f}) and current (${metric_delta.current:,.2f}) periods",
        )
    return None


def revenue_increase_rule(metric_delta) -> Optional[Insight]:
    if metric_delta.name == "revenue" and metric_delta.percent_change > 10:
        pct = metric_delta.percent_change
        gained = metric_delta.absolute_change
        return Insight(
            code="REVENUE_INCREASE",
            severity="low",
            title="Revenue growth detected",
            description=(
                f"Revenue increased by {pct:.1f}% compared to baseline, "
                f"a gain of ${gained:,.2f} in absolute terms."
            ),
            affected_metric="revenue",
            driver=f"Revenue expanded from ${metric_delta.baseline:,.2f} to ${metric_delta.current:,.2f} ({pct:.1f}% growth)",
            implication="Positive growth trajectory suggests strong market traction; verify whether growth is sustainable or one-time.",
            action_direction="Identify top-performing segments driving growth and allocate resources to sustain momentum.",
            confidence="HIGH" if pct >= 20 else "MEDIUM",
            confidence_basis=f"Based on {pct:.1f}% change between full baseline (${metric_delta.baseline:,.2f}) and current (${metric_delta.current:,.2f}) periods",
        )
    return None


def revenue_moderate_change_rule(metric_delta) -> Optional[Insight]:
    if metric_delta.name == "revenue" and -10 <= metric_delta.percent_change <= 10:
        pct = metric_delta.percent_change
        direction = "increased" if pct > 0 else "decreased" if pct < 0 else "remained flat"
        return Insight(
            code="REVENUE_STABLE",
            severity="low",
            title="Revenue largely stable",
            description=(
                f"Revenue {direction} by {abs(pct):.1f}% compared to baseline — "
                f"within normal fluctuation range."
            ),
            affected_metric="revenue",
            driver=f"Current revenue ${metric_delta.current:,.2f} vs baseline ${metric_delta.baseline:,.2f} shows {abs(pct):.1f}% variance",
            implication="Stability suggests consistent operational performance with no major disruptions or breakthroughs.",
            action_direction="Monitor for emerging trends; use stability window to invest in growth experiments.",
            confidence="HIGH",
            confidence_basis=f"Small variance ({abs(pct):.1f}%) between full baseline and current periods indicates high signal reliability",
        )
    return None


# ---------------------------------------------------------------------------
# Data-driven rules (work without baseline)
# ---------------------------------------------------------------------------

def avg_revenue_per_row_rule(df: pd.DataFrame, rev_col: str) -> Optional[Insight]:
    vals = pd.to_numeric(df[rev_col], errors="coerce").dropna()
    if len(vals) < 2:
        return None
    avg = vals.mean()
    median = vals.median()
    skew_direction = "above" if avg > median else "below"
    return Insight(
        code="AVG_REVENUE_PER_ROW",
        severity="low",
        title="Average revenue per transaction",
        description=(
            f"Average revenue per row is ${avg:,.2f} (median: ${median:,.2f}). "
            f"Mean is {skew_direction} median, indicating {'right' if avg > median else 'left'}-skewed distribution."
        ),
        affected_metric="revenue",
        driver=f"Computed from {len(vals):,} revenue records with mean ${avg:,.2f} and median ${median:,.2f}",
        implication="Understanding average transaction value helps set realistic targets and identify pricing opportunities.",
        action_direction="Compare against industry benchmarks; explore upsell strategies for below-average transactions.",
        confidence="MEDIUM" if len(vals) < 100 else "HIGH",
        confidence_basis=f"Calculated from {len(vals):,} non-null records; {'large' if len(vals) >= 100 else 'moderate'} sample size",
    )


def revenue_concentration_rule(df: pd.DataFrame, rev_col: str) -> Optional[Insight]:
    vals = pd.to_numeric(df[rev_col], errors="coerce").dropna()
    if len(vals) < 10 or vals.sum() == 0:
        return None
    top_n = max(1, int(len(vals) * 0.1))
    top_10_sum = vals.sort_values(ascending=False).head(top_n).sum()
    total = vals.sum()
    contrib_pct = (top_10_sum / total) * 100

    if contrib_pct > 60:
        severity, risk = "high", "high"
    elif contrib_pct > 40:
        severity, risk = "medium", "moderate"
    else:
        severity, risk = "low", "low"

    return Insight(
        code="REVENUE_CONCENTRATION",
        severity=severity,
        title="Revenue concentration analysis",
        description=(
            f"Top 10% of transactions ({top_n:,} records) contribute {contrib_pct:.1f}% of total revenue. "
            f"Concentration risk: {risk}."
        ),
        affected_metric="revenue",
        driver=f"Top {top_n:,} of {len(vals):,} records generate ${top_10_sum:,.2f} out of ${total:,.2f} total revenue",
        implication="High concentration creates dependency risk — losing top contributors would disproportionately impact revenue."
            if contrib_pct > 40 else "Revenue is well-distributed across transactions, reducing dependency risk.",
        action_direction="Diversify revenue sources and build redundancy in top-performing segments."
            if contrib_pct > 40 else "Maintain distribution health; monitor for emerging concentration patterns.",
        confidence="HIGH",
        confidence_basis=f"Statistical measure computed from {len(vals):,} records with deterministic top-10% cutoff",
    )


def revenue_volatility_rule(df: pd.DataFrame, rev_col: str) -> Optional[Insight]:
    vals = pd.to_numeric(df[rev_col], errors="coerce").dropna()
    if len(vals) < 10 or vals.mean() == 0:
        return None
    cv = abs(vals.std() / vals.mean())

    if cv > 1.0:
        severity, label = "high", "very high"
    elif cv > 0.5:
        severity, label = "medium", "moderate"
    else:
        severity, label = "low", "low"

    return Insight(
        code="REVENUE_VOLATILITY",
        severity=severity,
        title="Revenue volatility assessment",
        description=(
            f"Coefficient of variation is {cv:.2f}, indicating {label} revenue volatility. "
            f"Standard deviation: ${vals.std():,.2f}, mean: ${vals.mean():,.2f}."
        ),
        affected_metric="revenue",
        driver=f"CV of {cv:.2f} computed from {len(vals):,} records (std=${vals.std():,.2f}, mean=${vals.mean():,.2f})",
        implication="High volatility creates cash flow unpredictability and makes forecasting unreliable."
            if cv > 0.5 else "Low volatility supports stable forecasting and predictable revenue planning.",
        action_direction="Identify outlier transactions driving variance; consider smoothing strategies."
            if cv > 0.5 else "Leverage stability for confident forward planning and resource allocation.",
        confidence="HIGH" if len(vals) >= 50 else "MEDIUM",
        confidence_basis=f"CV computed from {len(vals):,} records; {'statistically robust' if len(vals) >= 50 else 'moderate'} sample",
    )


def revenue_distribution_rule(df: pd.DataFrame, rev_col: str) -> Optional[Insight]:
    vals = pd.to_numeric(df[rev_col], errors="coerce").dropna()
    if len(vals) < 4:
        return None

    q25 = vals.quantile(0.25)
    q50 = vals.quantile(0.50)
    q75 = vals.quantile(0.75)
    min_val = vals.min()
    max_val = vals.max()

    iqr = q75 - q25
    safe_median = max(abs(q50), 0.01)
    spread = "wide" if iqr / safe_median > 1.0 else ("moderate" if iqr / safe_median > 0.3 else "narrow")
    return Insight(
        code="REVENUE_DISTRIBUTION",
        severity="low",
        title="Revenue distribution profile",
        description=(
            f"Revenue ranges from ${min_val:,.2f} to ${max_val:,.2f}. "
            f"25th percentile: ${q25:,.2f}, median: ${q50:,.2f}, 75th percentile: ${q75:,.2f}."
        ),
        affected_metric="revenue",
        driver=f"Quartile analysis across {len(vals):,} revenue records (IQR: ${iqr:,.2f})",
        implication=f"A {spread} spread indicates {'significant variation in transaction sizes' if spread == 'wide' else 'relatively uniform transaction sizes'}.",
        action_direction="Segment transactions by value tier to identify targeted pricing or upsell opportunities."
            if spread != "narrow" else "Distribution is tight — focus on volume growth rather than value optimization.",
        confidence="HIGH",
        confidence_basis=f"Quartile statistics computed from {len(vals):,} non-null records; deterministic calculation",
    )


# ---------------------------------------------------------------------------
# Product-level rules (require product column)
# ---------------------------------------------------------------------------

def _detect_product_column(df: pd.DataFrame) -> Optional[str]:
    candidates = ["product", "product_name", "item", "sku", "description",
                   "product_id", "item_name", "product_category", "category"]
    cols_lower = {col.lower().strip(): col for col in df.columns}
    for c in candidates:
        if c in cols_lower:
            return cols_lower[c]
    return None


def top_product_rule(df: pd.DataFrame, rev_col: str) -> Optional[Insight]:
    prod_col = _detect_product_column(df)
    if prod_col is None:
        return None
    vals = pd.to_numeric(df[rev_col], errors="coerce")
    grouped = df.assign(__rev=vals).groupby(prod_col)["__rev"].sum().dropna()
    if len(grouped) < 2 or grouped.sum() == 0:
        return None
    top = grouped.idxmax()
    top_rev = grouped.max()
    pct = (top_rev / grouped.sum()) * 100
    return Insight(
        code="TOP_PRODUCT",
        severity="low" if pct < 30 else "medium",
        title="Top performing product identified",
        description=(
            f"'{top}' is the top revenue product, generating ${top_rev:,.2f} "
            f"({pct:.1f}% of total product revenue)."
        ),
        affected_metric="revenue",
        driver=f"Product '{top}' leads {len(grouped)} products with ${top_rev:,.2f} revenue ({pct:.1f}% share)",
        implication="High single-product dependency increases risk if that product underperforms."
            if pct > 30 else "Healthy product distribution with no single-product dependency.",
        action_direction="Protect and invest in top performer while developing secondary products."
            if pct > 30 else "Continue balanced portfolio strategy; monitor for share shifts.",
        confidence="HIGH",
        confidence_basis=f"Computed from {len(grouped)} distinct products across {len(df):,} records",
    )


def product_concentration_rule(df: pd.DataFrame, rev_col: str) -> Optional[Insight]:
    prod_col = _detect_product_column(df)
    if prod_col is None:
        return None
    vals = pd.to_numeric(df[rev_col], errors="coerce")
    grouped = df.assign(__rev=vals).groupby(prod_col)["__rev"].sum().dropna().sort_values(ascending=False)
    if len(grouped) < 3 or grouped.sum() == 0:
        return None
    top3_sum = grouped.head(3).sum()
    total = grouped.sum()
    top3_pct = (top3_sum / total) * 100
    top3_names = list(grouped.head(3).index)
    return Insight(
        code="PRODUCT_CONCENTRATION",
        severity="high" if top3_pct > 70 else ("medium" if top3_pct > 50 else "low"),
        title="Product revenue concentration",
        description=(
            f"Top 3 products ({', '.join(str(n) for n in top3_names)}) "
            f"generate {top3_pct:.1f}% of total revenue."
        ),
        affected_metric="revenue",
        driver=f"Top 3 of {len(grouped)} products contribute ${top3_sum:,.2f} of ${total:,.2f} total ({top3_pct:.1f}%)",
        implication="Heavy reliance on few products creates vulnerability to market shifts."
            if top3_pct > 50 else "Revenue is diversified across products, reducing concentration risk.",
        action_direction="Develop mid-tier products to reduce top-3 dependency."
            if top3_pct > 50 else "Maintain portfolio balance; invest in emerging product opportunities.",
        confidence="HIGH",
        confidence_basis=f"Deterministic revenue aggregation across {len(grouped)} products",
    )


def underperforming_products_rule(df: pd.DataFrame, rev_col: str) -> Optional[Insight]:
    prod_col = _detect_product_column(df)
    if prod_col is None:
        return None
    vals = pd.to_numeric(df[rev_col], errors="coerce")
    grouped = df.assign(__rev=vals).groupby(prod_col)["__rev"].sum().dropna().sort_values(ascending=True)
    if len(grouped) < 5 or grouped.sum() == 0:
        return None
    bottom_n = max(1, int(len(grouped) * 0.2))
    bottom_sum = grouped.head(bottom_n).sum()
    total = grouped.sum()
    bottom_pct = (bottom_sum / total) * 100
    return Insight(
        code="UNDERPERFORMING_PRODUCTS",
        severity="low" if bottom_pct > 5 else "medium",
        title="Underperforming product segment",
        description=(
            f"Bottom 20% of products ({bottom_n} products) generate only "
            f"{bottom_pct:.1f}% of total revenue (${bottom_sum:,.2f})."
        ),
        affected_metric="revenue",
        driver=f"Lowest {bottom_n} of {len(grouped)} products contribute ${bottom_sum:,.2f} ({bottom_pct:.1f}%) to total ${total:,.2f}",
        implication="Long-tail products may consume resources disproportionate to their revenue contribution.",
        action_direction="Evaluate whether underperformers justify their operational costs; consider pruning or repositioning.",
        confidence="MEDIUM" if len(grouped) < 20 else "HIGH",
        confidence_basis=f"Revenue ranking across {len(grouped)} products; bottom 20% cutoff = {bottom_n} products",
    )


def product_baseline_comparison_rule(
    current_df: pd.DataFrame,
    baseline_df: Optional[pd.DataFrame],
    rev_col: str,
    baseline_rev_col: Optional[str],
) -> List[Insight]:
    if baseline_df is None or baseline_rev_col is None:
        return []
    prod_col_cur = _detect_product_column(current_df)
    prod_col_base = _detect_product_column(baseline_df)
    if prod_col_cur is None or prod_col_base is None:
        return []

    cur_vals = pd.to_numeric(current_df[rev_col], errors="coerce")
    base_vals = pd.to_numeric(baseline_df[baseline_rev_col], errors="coerce")
    cur_grouped = current_df.assign(__rev=cur_vals).groupby(prod_col_cur)["__rev"].sum().dropna()
    base_grouped = baseline_df.assign(__rev=base_vals).groupby(prod_col_base)["__rev"].sum().dropna()

    common = set(cur_grouped.index) & set(base_grouped.index)
    if not common:
        return []

    insights = []
    for prod in sorted(common, key=lambda p: cur_grouped.get(p, 0), reverse=True)[:5]:
        cur_val = cur_grouped[prod]
        base_val = base_grouped[prod]
        if base_val == 0:
            continue
        pct_change = ((cur_val - base_val) / base_val) * 100
        if abs(pct_change) < 5:
            continue
        direction = "increased" if pct_change > 0 else "decreased"
        impl = ("Growth opportunity — investigate what drove this product's success."
                if pct_change > 0
                else "Declining product requires investigation into demand or competitive shifts.")
        act = ("Scale successful strategies from this product to others."
               if pct_change > 0
               else "Review pricing, positioning, and market conditions for this product.")
        insights.append(Insight(
            code="PRODUCT_REVENUE_CHANGE",
            severity="high" if abs(pct_change) > 30 else ("medium" if abs(pct_change) > 15 else "low"),
            title=f"Product '{prod}' revenue {direction}",
            description=(
                f"'{prod}' revenue {direction} by {abs(pct_change):.1f}% "
                f"(${base_val:,.2f} → ${cur_val:,.2f})."
            ),
            affected_metric="revenue",
            driver=f"Product '{prod}': ${base_val:,.2f} baseline → ${cur_val:,.2f} current ({pct_change:+.1f}%)",
            implication=impl,
            action_direction=act,
            confidence="MEDIUM",
            confidence_basis=f"Comparison of aggregated revenue for product '{prod}' across baseline and current periods",
        ))
    return insights
