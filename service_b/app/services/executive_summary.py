"""
Enhanced Executive Summary (V1 — Additive)
 
Meta-layer that synthesizes multiple analysis signals (trend, stability, RSI, 
IHS, EWA, CLPP, CSCA, CRD) into a cohesive, deterministic business narrative.
 
This is not a generic summary; it is a rule-based engine that identifies
the most critical positives and risks and provides an action direction.
"""
from __future__ import annotations

from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from app.services.insight_engine.entity_detector import format_inr_lakh
 
 
# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────
 
class ExecutiveSummarySection(BaseModel):
    heading: str
    content: str
    sentiment: str  # "positive", "negative", "neutral", "warning"
 
 
class EnhancedExecutiveSummaryResult(BaseModel):
    narrative: str
    sections: List[ExecutiveSummarySection] = []
    overall_sentiment: str = "neutral"  # "positive", "negative", "mixed", "neutral"
    confidence: str = "medium"
    key_positives: List[str] = []
    key_risks: List[str] = []
    watchpoints: List[str] = []
    headline_metrics: List[str] = []   # top-line rupee figures (dead stock, receivables, churn)
    data_coverage: str = "limited"
    warning: Optional[str] = None
 
 
# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────
 
def compute_enhanced_executive_summary(
    bi_dict: Dict[str, Any],
    row_count: int,
) -> Optional[EnhancedExecutiveSummaryResult]:
    """
    Synthesize all available business insights into a structured executive summary.
    
    Returns None only on unexpected crash.
    Returns a result with warning if data is insufficient.
    """
    try:
        # 1. Collect signals
        positives = _collect_positives(bi_dict)
        risks = _collect_risks(bi_dict)
        
        # 2. Determine sentiment and data posture
        sentiment = _determine_sentiment(positives, risks)
        coverage = _determine_coverage(bi_dict)
        confidence = _determine_confidence(row_count, coverage)
        
        # 3. Build action-oriented watchpoints
        watchpoints = _collect_watchpoints(bi_dict, risks, row_count)

        # 3b. Headline rupee figures for the distributor niche (dead stock,
        #     receivables) — surfaced with the same prominence as top-line metrics.
        headline_metrics = _collect_headline_metrics(bi_dict)

        # 4. Build structured narrative sections
        sections = _build_sections(bi_dict, positives, risks, watchpoints, sentiment, coverage, confidence, headline_metrics)
        
        # 5. Generate final narrative string
        narrative = " ".join([s.content for s in sections if s.content])
        
        # 6. Safety check for insufficient data
        if not narrative or narrative.isspace():
            narrative = "Insufficient analysis data to generate a meaningful executive summary. The dataset may be too small or lack key business dimensions."
 
        # 7. Final warning if needed
        warning = None
        if confidence == "low":
            warning = "Low confidence: limited data or analysis coverage reduces the reliability of this summary."
        elif row_count < 50:
            warning = "Very small dataset — executive summary is based on limited evidence."
 
        return EnhancedExecutiveSummaryResult(
            narrative=narrative,
            sections=sections,
            overall_sentiment=sentiment,
            confidence=confidence,
            key_positives=positives[:4],
            key_risks=risks[:4],
            watchpoints=watchpoints[:4],
            headline_metrics=headline_metrics[:4],
            data_coverage=coverage,
            warning=warning
        )
    except Exception:
        return None
 
 
# ─────────────────────────────────────────────
# Helper Logic
# ─────────────────────────────────────────────
 
def _collect_positives(bi: Dict[str, Any]) -> List[str]:
    positives = []
    
    # Trend
    trend = bi.get("trend")
    if trend and trend.get("direction") in ("strong_upward", "moderate_growth"):
        positives.append("Revenue is trending upward compared to baseline.")
        
    # Stability
    stb = bi.get("stability")
    if stb and stb.get("category") == "stable":
        positives.append("Revenue distribution is stable with low volatility.")
        
    # Efficiency
    eff = bi.get("efficiency")
    if eff and eff.get("signal") == "efficiency_improved":
        pct = abs(eff.get("change_percent", 0))
        positives.append(f"Revenue yield per transaction improved ({pct:.1f}% gain).")
        
    # RSI (Revenue Stability Index)
    rsi = bi.get("revenue_stability_index")
    if rsi and rsi.get("score", 0) >= 70:
        positives.append(f"Revenue Stability Index is healthy ({rsi.get('label', '')}).")
        
    # IHS (Inventory Health Score)
    ihs = bi.get("inventory_health_score")
    if ihs and ihs.get("score", 0) >= 70:
        positives.append(f"Inventory Health Score is strong ({ihs.get('label', '')}).")
        
    # CRD (Concentration Risk Dashboard)
    crd = bi.get("concentration_risk_dashboard")
    if crd and crd.get("overall_risk") == "low":
        positives.append("Concentration risk is low across analyzed dimensions.")
        
    # Alerts
    ewa = bi.get("early_warning_alerts")
    if ewa and ewa.get("alert_count", 0) == 0:
        positives.append("No early warning alerts triggered in this period.")
 
    return positives
 
 
def _collect_risks(bi: Dict[str, Any]) -> List[str]:
    risks = []
    
    # Trend
    trend = bi.get("trend")
    if trend and trend.get("direction") in ("sharp_decline", "early_decline"):
        risks.append("Revenue is declining compared to the baseline period.")
        
    # Stability
    stb = bi.get("stability")
    if stb and stb.get("category") == "highly_volatile":
        risks.append("Revenue is highly volatile, indicating unpredictable cash flow.")
        
    # Efficiency
    eff = bi.get("efficiency")
    if eff and eff.get("signal") == "efficiency_declined":
        pct = abs(eff.get("change_percent", 0))
        risks.append(f"Revenue yield per transaction declined ({pct:.1f}% loss).")
        
    # Concentration (Basic)
    conc = bi.get("concentration")
    if conc and conc.get("risk_level") in ("high", "critical"):
        risks.append("Basic revenue concentration risk detected among top contributors.")
        
    # CRD (Detailed)
    crd = bi.get("concentration_risk_dashboard")
    if crd and crd.get("overall_risk") in ("high", "critical"):
        risks.append(f"Critical concentration risk detected: {crd.get('overall_risk')} risk overall.")
        
    # RSI
    rsi = bi.get("revenue_stability_index")
    if rsi and rsi.get("score", 100) < 40:
        risks.append(f"Revenue Stability Index is weak ({rsi.get('label', '')}).")
        
    # IHS
    ihs = bi.get("inventory_health_score")
    if ihs and ihs.get("score", 100) < 40:
        risks.append(f"Inventory Health Score is concerning ({ihs.get('label', '')}).")
        
    # Alerts
    ewa = bi.get("early_warning_alerts")
    if ewa:
        if ewa.get("has_critical"):
            risks.append(f"Critical early warning alerts detected ({ewa.get('alert_count', 0)} total).")
        elif ewa.get("has_high"):
            risks.append(f"High-severity early warning alerts triggered ({ewa.get('alert_count', 0)} total).")
            
    # Cohorts
    clpp = bi.get("cohort_product_performance")
    if clpp and clpp.get("has_declining"):
        risks.append("Declining product cohorts identified in cohort analysis.")
        
    # Segments
    csca = bi.get("customer_segmentation")
    if csca:
        if csca.get("has_at_risk"):
            risks.append("At-risk customer segments identified.")
        elif csca.get("has_declining"):
            risks.append("Declining customer segments detected.")

    # Customer churn (distribution niche)
    ccr = bi.get("customer_churn_risk")
    if ccr and ccr.get("has_at_risk"):
        flagged = (ccr.get("at_risk_count") or 0) + (ccr.get("churned_count") or 0)
        risks.append(f"{flagged} account(s) have gone quiet and may be churning.")

    # Receivables (distribution niche)
    rr = bi.get("receivables_risk")
    if rr and rr.get("aging_available") and (rr.get("over_45_amount") or 0) > 0:
        risks.append(
            f"{format_inr_lakh(rr.get('over_45_amount'))} of receivables is over 45 days overdue."
        )

    return risks


def _collect_headline_metrics(bi: Dict[str, Any]) -> List[str]:
    """Top-line rupee figures for the distributor niche — presented with the
    same prominence as existing headline metrics."""
    metrics: List[str] = []

    # Dead stock (Feature 3): rupee value of capital tied up.
    ihs = bi.get("inventory_health_score")
    if ihs and isinstance(ihs, dict):
        dead_value = ihs.get("total_dead_stock_value")
        dead_count = ihs.get("dead_stock_count")
        window = ihs.get("dead_stock_window_days") or 60
        if dead_value and dead_count:
            metrics.append(
                f"{format_inr_lakh(dead_value)} of capital is tied up in {dead_count} "
                f"dead-stock SKU(s) idle {window}+ days."
            )

    # Receivables (Feature 4): outstanding and aged amounts.
    rr = bi.get("receivables_risk")
    if rr and isinstance(rr, dict):
        total = rr.get("total_outstanding")
        cust_n = rr.get("customer_count")
        over_45 = rr.get("over_45_amount")
        if total and cust_n:
            line = f"{format_inr_lakh(total)} outstanding across {cust_n} customer(s)"
            if rr.get("aging_available") and over_45:
                line += f", {format_inr_lakh(over_45)} of which is over 45 days old"
            metrics.append(line + ".")

    # Churn (Feature 2): revenue now at risk from quiet shops.
    ccr = bi.get("customer_churn_risk")
    if ccr and isinstance(ccr, dict):
        rev_at_risk = ccr.get("revenue_at_risk")
        flagged = (ccr.get("at_risk_count") or 0) + (ccr.get("churned_count") or 0)
        if rev_at_risk and flagged:
            metrics.append(
                f"{format_inr_lakh(rev_at_risk)} of historic revenue is at risk across "
                f"{flagged} quiet account(s)."
            )

    return metrics


def _collect_watchpoints(bi: Dict[str, Any], risks: List[str], row_count: int) -> List[str]:
    watchpoints = []
    
    # Alert management
    ewa = bi.get("early_warning_alerts")
    if ewa and ewa.get("alert_count", 0) > 0:
        watchpoints.append("Immediate action required on triggered alerts, prioritizing critical items.")
        
    # Concentration mitigation
    crd = bi.get("concentration_risk_dashboard")
    if crd and crd.get("overall_risk") in ("high", "critical"):
        watchpoints.append("Implement diversification strategy to reduce dependency on top revenue drivers.")
        
    # Customer retention
    csca = bi.get("customer_segmentation")
    if csca and (csca.get("has_at_risk") or csca.get("has_declining")):
        watchpoints.append("Execute retention campaigns targeting at-risk and declining customer segments.")
        
    # Product review
    clpp = bi.get("cohort_product_performance")
    if clpp and (clpp.get("has_declining") or clpp.get("has_underperformer")):
        watchpoints.append("Review pricing and positioning for underperforming product cohorts.")
        
    # Watchlist items
    ptw = bi.get("products_to_watch")
    if ptw and len(ptw) > 0:
        watchpoints.append(f"Review the {len(ptw)} product(s) currently on the watchlist.")
        
    # Data gathering
    if row_count < 100:
        watchpoints.append("Increase transaction capture to improve analysis confidence in future periods.")
 
    if not watchpoints and risks:
        watchpoints.append("Monitor the risk signals identified in this report for further deterioration.")
        
    return watchpoints
 
 
def _determine_sentiment(positives: List[str], risks: List[str]) -> str:
    p = len(positives)
    r = len(risks)
    if r == 0 and p > 0: return "positive"
    if r > p and r >= 2: return "negative"
    if r > 0 and p > 0: return "mixed"
    return "neutral"
 
 
def _determine_coverage(bi: Dict[str, Any]) -> str:
    keys = [
        "trend", "stability", "efficiency", "concentration",
        "revenue_stability_index", "inventory_health_score",
        "early_warning_alerts", "cohort_product_performance",
        "customer_segmentation", "concentration_risk_dashboard",
    ]
    count = sum(1 for k in keys if bi.get(k))
    if count >= 8: return "comprehensive"
    if count >= 4: return "partial"
    return "limited"
 
 
def _determine_confidence(row_count: int, coverage: str) -> str:
    if row_count >= 1000 and coverage == "comprehensive": return "high"
    if row_count >= 100 and coverage != "limited": return "medium"
    return "low"
 
 
def _build_sections(
    bi: Dict[str, Any], positives: List[str], risks: List[str],
    watchpoints: List[str], sentiment: str, coverage: str, confidence: str,
    headline_metrics: Optional[List[str]] = None,
) -> List[ExecutiveSummarySection]:
    sections = []

    # 1. Overview
    overview_text = bi.get("executive_summary", "")
    if not overview_text:
        trend_desc = (bi.get("trend") or {}).get("description", "Revenue performance is stable.")
        overview_text = f"Performance overview: {trend_desc}"

    sections.append(ExecutiveSummarySection(
        heading="Performance Overview",
        content=overview_text,
        sentiment="neutral"
    ))

    # 1b. Headline Numbers — prominent top-line rupee figures (dead stock,
    #     receivables, churn) for the distributor niche.
    if headline_metrics:
        sections.append(ExecutiveSummarySection(
            heading="Headline Numbers",
            content=" ".join(headline_metrics[:4]),
            sentiment="warning"
        ))

    # 2. Positives
    if positives:
        sections.append(ExecutiveSummarySection(
            heading="Key Strengths",
            content=" ".join(positives[:3]),
            sentiment="positive"
        ))
        
    # 3. Risks
    if risks:
        sections.append(ExecutiveSummarySection(
            heading="Key Risks & Warnings",
            content=" ".join(risks[:3]),
            sentiment="negative"
        ))
        
    # 4. Implication
    state_map = {
        "positive": "healthy and expanding",
        "negative": "under pressure",
        "mixed": "in a state of transition with mixed signals",
        "neutral": "stable with evolving patterns"
    }
    implication = (
        f"The analysis suggests the business is {state_map.get(sentiment, 'stable')} "
        f"based on {coverage} data coverage. "
    )
    if sentiment == "negative":
        implication += "Leadership should prioritize risk mitigation and stability."
    elif sentiment == "positive":
        implication += "Conditions are favorable for scaling and continued investment."
    else:
        implication += "Monitor the watchpoints below to maintain momentum."
 
    sections.append(ExecutiveSummarySection(
        heading="Business Implication",
        content=implication,
        sentiment=sentiment
    ))
    
    # 5. Watchpoints
    if watchpoints:
        sections.append(ExecutiveSummarySection(
            heading="Leadership Watchpoints",
            content=" ".join(watchpoints[:3]),
            sentiment="neutral"
        ))
        
    return sections
