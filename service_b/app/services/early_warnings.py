"""
Early Warning Alerts (V1 — Additive)
 
Deterministic, rule-based alerting layer that flags business risk signals
from already-computed business insights. This module is a meta-layer —
it reads from existing insight objects rather than recomputing from raw data.
 
Each rule evaluates a specific risk condition and emits a structured alert
if the condition is met. Rules are independent and evaluated in priority order.
The output is a ranked list of alerts sorted by severity.
 
Alert severities: critical > high > medium > low
"""
from __future__ import annotations
 
from typing import Any, Dict, List, Optional
 
import pandas as pd
from pydantic import BaseModel
 
 
# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────
 
class EarlyWarningAlert(BaseModel):
    """A single early-warning alert."""
 
    alert_code: str                  # Machine-readable code, e.g. "REVENUE_DECLINE_RISK"
    severity: str                    # "critical" | "high" | "medium" | "low"
    title: str                       # Short human-readable title
    description: str                 # One-paragraph explanation
    driver: str                      # What caused this alert
    implication: str                 # What it means for the business
    action_direction: str            # What to do about it
    confidence: str                  # "high" | "medium" | "low"
    confidence_basis: Optional[str] = None  # Why that confidence level
    metric_ref: Optional[str] = None        # Optional reference metric name
 
 
class EarlyWarningResult(BaseModel):
    """Container for all early-warning alerts."""
 
    alerts: List[EarlyWarningAlert] = []    # Ranked list (highest severity first)
    alert_count: int = 0                     # Total number of alerts
    has_critical: bool = False               # Quick flag for critical alerts
    has_high: bool = False                   # Quick flag for high alerts
 
 
# ─────────────────────────────────────────────
# Severity ordering
# ─────────────────────────────────────────────
 
_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
 
 
def _sort_alerts(alerts: List[EarlyWarningAlert]) -> List[EarlyWarningAlert]:
    return sorted(alerts, key=lambda a: _SEVERITY_ORDER.get(a.severity, 99))
 
 
# ─────────────────────────────────────────────
# Individual rule functions
# ─────────────────────────────────────────────
 
def _rule_sharp_revenue_decline(bi: Dict[str, Any]) -> Optional[EarlyWarningAlert]:
    """
    Trigger: trend direction is sharp_decline (>20% drop vs baseline).
    Severity: critical.
    """
    trend = bi.get("trend")
    if not trend or not isinstance(trend, dict):
        return None
    direction = trend.get("direction", "")
    if direction != "sharp_decline":
        return None
 
    return EarlyWarningAlert(
        alert_code="REVENUE_DECLINE_CRITICAL",
        severity="critical",
        title="Sharp Revenue Decline Detected",
        description=(
            "Revenue has declined sharply compared to the baseline period. "
            "This level of contraction typically signals structural issues requiring immediate investigation."
        ),
        driver=trend.get("driver", "Significant period-over-period revenue contraction observed."),
        implication="Continued decline at this rate may erode margins and cash reserves, impacting operational sustainability.",
        action_direction="Conduct root-cause analysis on revenue drivers immediately; review pricing, customer churn, and product mix.",
        confidence=trend.get("confidence", "medium"),
        confidence_basis=trend.get("confidence_basis"),
        metric_ref="revenue",
    )
 
 
def _rule_early_decline(bi: Dict[str, Any]) -> Optional[EarlyWarningAlert]:
    """
    Trigger: trend direction is early_decline (5–20% drop vs baseline).
    Severity: high.
    """
    trend = bi.get("trend")
    if not trend or not isinstance(trend, dict):
        return None
    if trend.get("direction") != "early_decline":
        return None
 
    return EarlyWarningAlert(
        alert_code="REVENUE_DECLINE_EARLY",
        severity="high",
        title="Early Revenue Decline Signal",
        description=(
            "Revenue has declined moderately compared to baseline, indicating the beginning of a potential downtrend. "
            "Early intervention can prevent further deterioration."
        ),
        driver=trend.get("driver", "Moderate period-over-period revenue contraction detected."),
        implication="If left unaddressed, this trajectory may accelerate into a larger decline.",
        action_direction="Monitor weekly; identify which segments or products are driving the decrease.",
        confidence=trend.get("confidence", "medium"),
        confidence_basis=trend.get("confidence_basis"),
        metric_ref="revenue",
    )
 
 
def _rule_extreme_volatility(bi: Dict[str, Any]) -> Optional[EarlyWarningAlert]:
    """
    Trigger: stability category is highly_volatile (CV ≥ 0.7).
    Severity: high.
    """
    stability = bi.get("stability")
    if not stability or not isinstance(stability, dict):
        return None
    if stability.get("category") != "highly_volatile":
        return None
 
    cv = stability.get("coefficient_of_variation", 0)
    return EarlyWarningAlert(
        alert_code="VOLATILITY_EXTREME",
        severity="high",
        title="Extreme Revenue Volatility",
        description=(
            f"Revenue coefficient of variation is {cv:.2f}, indicating extreme and unpredictable "
            f"swings in transaction values. Cash flow planning becomes unreliable at this volatility level."
        ),
        driver=stability.get("driver", f"CV of {cv:.2f} exceeds the high-volatility threshold of 0.70."),
        implication="Unpredictable revenue makes budgeting, hiring, and investment decisions high-risk.",
        action_direction="Investigate the source of revenue swings — large one-off orders, returns, or pricing inconsistencies.",
        confidence=stability.get("confidence", "medium"),
        confidence_basis=stability.get("confidence_basis"),
        metric_ref="revenue_cv",
    )
 
 
def _rule_moderate_volatility(bi: Dict[str, Any]) -> Optional[EarlyWarningAlert]:
    """
    Trigger: stability category is moderately_volatile (CV 0.3–0.7).
    Severity: medium.
    """
    stability = bi.get("stability")
    if not stability or not isinstance(stability, dict):
        return None
    if stability.get("category") != "moderately_volatile":
        return None
 
    cv = stability.get("coefficient_of_variation", 0)
    return EarlyWarningAlert(
        alert_code="VOLATILITY_MODERATE",
        severity="medium",
        title="Moderate Revenue Volatility",
        description=(
            f"Revenue shows moderate volatility (CV={cv:.2f}), which may complicate short-term planning."
        ),
        driver=f"Transaction-level variation (CV={cv:.2f}) exceeds the stability threshold of 0.30.",
        implication="Moderate volatility suggests uneven demand patterns that could mask underlying trends.",
        action_direction="Segment revenue by product/customer to identify volatility sources.",
        confidence=stability.get("confidence", "medium"),
        confidence_basis=stability.get("confidence_basis"),
        metric_ref="revenue_cv",
    )
 
 
def _rule_high_concentration(bi: Dict[str, Any]) -> Optional[EarlyWarningAlert]:
    """
    Trigger: concentration risk_level is "high" (top 10% > 60% of revenue).
    Severity: high.
    """
    conc = bi.get("concentration")
    if not conc or not isinstance(conc, dict):
        return None
    if conc.get("risk_level") != "high":
        return None
 
    contrib = conc.get("top_10_percent_contribution", 0)
    return EarlyWarningAlert(
        alert_code="CONCENTRATION_HIGH",
        severity="high",
        title="High Revenue Concentration Risk",
        description=(
            f"The top 10% of transactions account for {contrib:.0f}% of total revenue. "
            f"Losing even a few high-value contributors could cause disproportionate revenue loss."
        ),
        driver=conc.get("driver", f"Top 10% drives {contrib:.0f}% of revenue — extreme dependency."),
        implication="Business is vulnerable to churn or order cancellation from a small number of high-value events.",
        action_direction="Diversify revenue base; develop retention strategies for top contributors.",
        confidence=conc.get("confidence", "medium"),
        confidence_basis=conc.get("confidence_basis"),
        metric_ref="concentration",
    )
 
 
def _rule_moderate_concentration(bi: Dict[str, Any]) -> Optional[EarlyWarningAlert]:
    """
    Trigger: concentration risk_level is "moderate" (top 10% = 40–60%).
    Severity: medium.
    """
    conc = bi.get("concentration")
    if not conc or not isinstance(conc, dict):
        return None
    if conc.get("risk_level") != "moderate":
        return None
 
    contrib = conc.get("top_10_percent_contribution", 0)
    return EarlyWarningAlert(
        alert_code="CONCENTRATION_MODERATE",
        severity="medium",
        title="Moderate Revenue Concentration",
        description=(
            f"Top 10% of transactions contribute {contrib:.0f}% of revenue — "
            f"concentration is approaching dependency levels."
        ),
        driver=f"Revenue distribution is moderately concentrated (top 10% = {contrib:.0f}%).",
        implication="Growing concentration increases exposure to single-event revenue shocks.",
        action_direction="Monitor concentration trends; consider broadening the revenue base.",
        confidence=conc.get("confidence", "medium"),
        confidence_basis=conc.get("confidence_basis"),
        metric_ref="concentration",
    )
 
 
def _rule_product_underperformance(bi: Dict[str, Any]) -> Optional[EarlyWarningAlert]:
    """
    Trigger: products_to_watch has 3+ items.
    Severity: medium.
    """
    ptw = bi.get("products_to_watch")
    if not ptw or not isinstance(ptw, list) or len(ptw) < 3:
        return None
 
    names = ", ".join(str(p) for p in ptw[:5])
    return EarlyWarningAlert(
        alert_code="PRODUCT_UNDERPERFORMANCE",
        severity="medium",
        title="Multiple Underperforming Products",
        description=(
            f"{len(ptw)} products are underperforming relative to the portfolio. "
            f"Products flagged include: {names}."
        ),
        driver=f"{len(ptw)} products fall in the bottom 20% of revenue contribution.",
        implication="Persistent underperformance may indicate pricing issues, poor positioning, or declining demand.",
        action_direction="Review pricing, marketing, and availability for flagged products; consider discontinuation if unrecoverable.",
        confidence="medium",
        confidence_basis=f"{len(ptw)} products below revenue threshold",
        metric_ref="product_revenue",
    )
 
 
def _rule_low_rsi(bi: Dict[str, Any]) -> Optional[EarlyWarningAlert]:
    """
    Trigger: Revenue Stability Index score < 40 (Highly Unstable).
    Severity: high.
    """
    rsi = bi.get("revenue_stability_index")
    if not rsi or not isinstance(rsi, dict):
        return None
    score = rsi.get("score")
    if score is None or score >= 40:
        return None
 
    return EarlyWarningAlert(
        alert_code="RSI_CRITICAL",
        severity="high",
        title="Revenue Stability Index — Highly Unstable",
        description=(
            f"Revenue Stability Index is {score:.0f}/100, classified as highly unstable. "
            f"Revenue patterns are erratic and may not support reliable business planning."
        ),
        driver=rsi.get("explanation", f"RSI score of {score:.0f} is below the stability threshold of 40."),
        implication="Unreliable revenue patterns increase risk for budgeting, hiring, and investment decisions.",
        action_direction="Investigate root causes of instability — returns, seasonal spikes, or customer concentration.",
        confidence=rsi.get("confidence", "medium"),
        metric_ref="revenue_stability_index",
    )
 
 
def _rule_warning_rsi(bi: Dict[str, Any]) -> Optional[EarlyWarningAlert]:
    """
    Trigger: Revenue Stability Index score 40–59 (Unstable).
    Severity: medium.
    """
    rsi = bi.get("revenue_stability_index")
    if not rsi or not isinstance(rsi, dict):
        return None
    score = rsi.get("score")
    if score is None or score < 40 or score >= 60:
        return None
 
    return EarlyWarningAlert(
        alert_code="RSI_WARNING",
        severity="medium",
        title="Revenue Stability Index — Unstable",
        description=(
            f"Revenue Stability Index is {score:.0f}/100, indicating concerning instability "
            f"that warrants monitoring."
        ),
        driver=rsi.get("explanation", f"RSI score of {score:.0f} falls in the warning range (40–59)."),
        implication="Revenue instability at this level may affect short-term planning accuracy.",
        action_direction="Monitor RSI trend over subsequent periods and identify volatility drivers.",
        confidence=rsi.get("confidence", "medium"),
        metric_ref="revenue_stability_index",
    )
 
 
def _rule_unhealthy_inventory(bi: Dict[str, Any]) -> Optional[EarlyWarningAlert]:
    """
    Trigger: Inventory Health Score < 40 (Unhealthy).
    Severity: high.
    """
    ihs = bi.get("inventory_health_score")
    if not ihs or not isinstance(ihs, dict):
        return None
    score = ihs.get("score")
    if score is None or score >= 40:
        return None
 
    return EarlyWarningAlert(
        alert_code="IHS_CRITICAL",
        severity="high",
        title="Inventory Health — Unhealthy",
        description=(
            f"Inventory Health Score is {score:.0f}/100, indicating significant dead stock, "
            f"poor product movement, or stock imbalance."
        ),
        driver=ihs.get("explanation", f"IHS score of {score:.0f} is below the healthy threshold."),
        implication="Cash may be trapped in unsold stock; product availability issues may exist.",
        action_direction="Review slow-moving SKUs; consider markdowns, bundling, or discontinuation.",
        confidence=ihs.get("confidence", "medium"),
        metric_ref="inventory_health_score",
    )
 
 
def _rule_warning_inventory(bi: Dict[str, Any]) -> Optional[EarlyWarningAlert]:
    """
    Trigger: Inventory Health Score 40–59 (Warning).
    Severity: medium.
    """
    ihs = bi.get("inventory_health_score")
    if not ihs or not isinstance(ihs, dict):
        return None
    score = ihs.get("score")
    if score is None or score < 40 or score >= 60:
        return None
 
    return EarlyWarningAlert(
        alert_code="IHS_WARNING",
        severity="medium",
        title="Inventory Health — Warning",
        description=(
            f"Inventory Health Score is {score:.0f}/100, suggesting some slow-moving "
            f"or uneven product movement patterns."
        ),
        driver=ihs.get("explanation", f"IHS score of {score:.0f} falls in the warning range."),
        implication="Without intervention, inventory health may deteriorate further.",
        action_direction="Monitor slow-moving products and review restock/clearance strategy.",
        confidence=ihs.get("confidence", "medium"),
        metric_ref="inventory_health_score",
    )
 
 
def _rule_efficiency_decline(bi: Dict[str, Any]) -> Optional[EarlyWarningAlert]:
    """
    Trigger: efficiency signal is "efficiency_declined".
    Severity: medium.
    """
    eff = bi.get("efficiency")
    if not eff or not isinstance(eff, dict):
        return None
    if eff.get("signal") != "efficiency_declined":
        return None
 
    pct = eff.get("change_percent", 0)
    return EarlyWarningAlert(
        alert_code="EFFICIENCY_DECLINE",
        severity="medium",
        title="Revenue Efficiency Declining",
        description=(
            f"Revenue yield per transaction has declined {abs(pct):.1f}% vs baseline, "
            f"indicating worsening monetization."
        ),
        driver=eff.get("driver", f"Average revenue per transaction dropped {abs(pct):.1f}%."),
        implication="Declining efficiency may signal discounting pressure, product mix shift, or customer downgrade.",
        action_direction="Review pricing strategy, discount policies, and product mix changes.",
        confidence=eff.get("confidence", "medium"),
        confidence_basis=eff.get("confidence_basis"),
        metric_ref="efficiency",
    )
 
 
def _rule_data_reliability(
    bi: Dict[str, Any],
    current_df: Optional[pd.DataFrame],
) -> Optional[EarlyWarningAlert]:
    """
    Trigger: dataset has fewer than 50 rows, OR high ratio of negative quantities.
    Severity: low (informational).
    """
    if current_df is None:
        return None
 
    n = len(current_df)
    factors = []
 
    if n < 50:
        factors.append(f"only {n} records in the dataset")
 
    # Check for negative quantity ratio (returns / cancellations)
    qty_candidates = ["quantity", "qty"]
    cols_lower = {c.lower().strip(): c for c in current_df.columns}
    qty_col = next((cols_lower[c] for c in qty_candidates if c in cols_lower), None)
    if qty_col:
        qty_items = pd.to_numeric(current_df[qty_col], errors="coerce").dropna()
        if len(qty_items) > 0:
            neg_ratio = float((qty_items < 0).sum() / len(qty_items))
            if neg_ratio > 0.05:
                factors.append(f"{neg_ratio * 100:.0f}% of rows have negative quantities (returns/cancellations)")
 
    if not factors:
        return None
 
    return EarlyWarningAlert(
        alert_code="DATA_RELIABILITY",
        severity="low",
        title="Data Reliability Notice",
        description=(
            "The dataset has characteristics that may affect analysis confidence: "
            + "; ".join(factors)
            + ". Interpret all signals cautiously."
        ),
        driver="; ".join(factors),
        implication="Low data volume or data anomalies may reduce the reliability of computed scores and insights.",
        action_direction="Consider supplementing with additional data or filtering out problematic records before analysis.",
        confidence="low",
        confidence_basis=f"n={n}",
        metric_ref="data_quality",
    )
 
 
# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────
 
# Ordered list of all rule functions.
# Rules that take only bi dict come first; the data-reliability rule also needs the DF.
_BI_ONLY_RULES = [
    _rule_sharp_revenue_decline,
    _rule_early_decline,
    _rule_extreme_volatility,
    _rule_high_concentration,
    _rule_low_rsi,
    _rule_unhealthy_inventory,
    _rule_efficiency_decline,
    _rule_moderate_volatility,
    _rule_moderate_concentration,
    _rule_product_underperformance,
    _rule_warning_rsi,
    _rule_warning_inventory,
]
 
 
def compute_early_warnings(
    business_insights_dict: Dict[str, Any],
    current_df: Optional[pd.DataFrame] = None,
) -> Optional[EarlyWarningResult]:
    """
    Evaluate all early-warning rules against the business insights payload.
 
    Parameters
    ----------
    business_insights_dict
        The serialized ``BusinessInsights.dict()`` output (or equivalent plain dict).
        This is the *already-computed* business insights — EWA does not recompute stats.
    current_df
        Optional raw DataFrame for the data-reliability rule only.
 
    Returns ``None`` only if an unexpected error occurs.
    Returns an ``EarlyWarningResult`` with an empty alert list when no warnings apply.
    This function never raises.
    """
    try:
        alerts: List[EarlyWarningAlert] = []
 
        # Run bi-only rules
        for rule_fn in _BI_ONLY_RULES:
            try:
                alert = rule_fn(business_insights_dict)
                if alert is not None:
                    alerts.append(alert)
            except Exception:
                continue  # Never let a single rule crash the whole system
 
        # Run data-reliability rule (needs DF)
        try:
            dr_alert = _rule_data_reliability(business_insights_dict, current_df)
            if dr_alert is not None:
                alerts.append(dr_alert)
        except Exception:
            pass
 
        # Sort by severity
        alerts = _sort_alerts(alerts)
 
        return EarlyWarningResult(
            alerts=alerts,
            alert_count=len(alerts),
            has_critical=any(a.severity == "critical" for a in alerts),
            has_high=any(a.severity == "high" for a in alerts),
        )
 
    except Exception:
        return None
