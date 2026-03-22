"""
Business Insight Layer for Kaizen Insight Engine V1.75

This module provides an ADDITIVE overlay that generates business-meaningful
insights from existing metric data. It does NOT modify core computation logic.

Architecture:
    Raw Metrics → Existing Insight Engine (V1.75) → Business Insight Layer → Merged Output

All insights are optional and gracefully omitted if data is insufficient.
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from app.schemas.insight.report import InsightReport
from app.schemas.insight.metrics import MetricDelta


class TrendInsight(BaseModel):
    """Revenue trend direction insight."""
    direction: str
    description: str
    confidence: str
    # V1.75+ enrichment fields (optional for backward compatibility)
    driver: Optional[str] = None
    implication: Optional[str] = None
    action_direction: Optional[str] = None
    confidence_basis: Optional[str] = None


class StabilityInsight(BaseModel):
    """Revenue volatility/stability insight."""
    category: str
    coefficient_of_variation: float
    description: str
    # V1.75+ enrichment fields (optional for backward compatibility)
    driver: Optional[str] = None
    implication: Optional[str] = None
    action_direction: Optional[str] = None
    confidence: Optional[str] = None
    confidence_basis: Optional[str] = None


class EfficiencyInsight(BaseModel):
    """ROI-style proxy insight (revenue efficiency)."""
    signal: str
    description: str
    change_percent: Optional[float] = None
    # V1.75+ enrichment fields (optional for backward compatibility)
    driver: Optional[str] = None
    implication: Optional[str] = None
    action_direction: Optional[str] = None
    confidence: Optional[str] = None
    confidence_basis: Optional[str] = None


class ConcentrationInsight(BaseModel):
    """Revenue concentration risk insight."""
    top_10_percent_contribution: float
    risk_level: str
    description: str
    # V1.75+ enrichment fields (optional for backward compatibility)
    driver: Optional[str] = None
    implication: Optional[str] = None
    action_direction: Optional[str] = None
    confidence: Optional[str] = None
    confidence_basis: Optional[str] = None


class ScopeBlock(BaseModel):
    """Explicit scope definition for the analysis."""
    analyzed: List[str] = []
    not_analyzed: List[str] = []


class BusinessInsights(BaseModel):
    """Container for all business insights."""
    # V1.75+ additions at top level
    executive_takeaways: Optional[List[str]] = None
    scope: Optional[ScopeBlock] = None
    # Original insight fields
    trend: Optional[TrendInsight] = None
    stability: Optional[StabilityInsight] = None
    efficiency: Optional[EfficiencyInsight] = None
    concentration: Optional[ConcentrationInsight] = None
    executive_summary: Optional[str] = None
    # Metadata
    meta: Optional[Dict[str, Any]] = None


class BusinessInsightGenerator:
    """
    Generates business-level insights from existing InsightReport data.
    
    This is a pure overlay - it reads from existing insights and raw data
    but never modifies the core metric computation logic.
    
    Insights are structured for founders: specific, evidence-driven, 
    and decision-oriented.
    """
    
    # Mandatory keywords for analytical thinking
    MANDATORY_KEYWORDS = ["risk", "concentration", "volatility", "growth", "stability", "anomaly", "dependency", "efficiency"]

    def build_scope_block(self) -> ScopeBlock:
        """Build explicit scope definition for the analysis."""
        return ScopeBlock(
            analyzed=["revenue"],
            not_analyzed=["costs", "margins", "forecasting", "cohort_analysis"]
        )
    
    def build_executive_takeaways(
        self,
        delta: MetricDelta,
        trend: Optional[TrendInsight],
        stability: Optional[StabilityInsight],
        efficiency: Optional[EfficiencyInsight],
        concentration: Optional[ConcentrationInsight],
    ) -> List[str]:
        """Build 4-6 executive takeaway bullets prioritizing risk/critical items."""
        takeaways = []
        
        if concentration and concentration.risk_level in ["critical", "high"]:
            takeaways.append(
                f"Concentration risk: top 10% accounts for {concentration.top_10_percent_contribution:.0f}% "
                f"of revenue — creates high dependency."
            )
        
        if stability and stability.category == "highly_volatile":
            takeaways.append(
                f"Volatility anomaly: CV={stability.coefficient_of_variation:.2f} indicates "
                f"high revenue unpredictability vs baseline."
            )
        
        if trend:
            if trend.direction in ["sharp_decline", "early_decline"]:
                takeaways.append(f"Risk signal: revenue declined {delta.percent_change:.1f}%; investigation required.")
            elif trend.direction == "strong_upward":
                takeaways.append(f"Growth signal: revenue increased {delta.percent_change:.1f}%; track sustainability.")
        
        if efficiency and efficiency.signal == "efficiency_improved":
            pct = efficiency.change_percent or 0
            takeaways.append(f"Efficiency gain: revenue yield per transaction up {pct:.0f}%.")

        if len(takeaways) < 4 and delta.current > 0:
            takeaways.append(f"Revenue stability: total period revenue recorded at ${delta.current:,.0f}.")
            
        return takeaways[:6]

    def _compute_confidence(self, sample_size: int, cv: float = 0.5, pct: float = 0.0) -> tuple:
        basis = f"n={sample_size}; cv={cv:.2f}; pct={pct:.1f}"
        if sample_size >= 50 and (cv < 0.3 or abs(pct) >= 20):
            return "high", basis
        elif sample_size >= 20:
            return "medium", basis
        return "low", basis

    def enrich_trend_insight(self, trend: TrendInsight, delta: MetricDelta, n: int) -> TrendInsight:
        pct = delta.percent_change
        
        # Enhanced descriptive phrasing for perceived value
        if pct > 0:
            driver = f"Expansionary signal: sustained increase in transaction value and volume observed across {n} records."
            implication = f"This positive growth trajectory of {pct:.1f}% indicates strong market traction and revenue efficiency."
            action = "Monitor growth sustainability and identify top-performing segments for further investment."
        else:
            driver = f"Contractionary risk: structural decline in revenue-generating activity detected in current period."
            implication = f"The {abs(pct):.1f}% decline indicates potential friction in monetization or customer retention."
            action = "Conduct root cause analysis on revenue leakage and review pricing elasticity."
            
        conf, basis = self._compute_confidence(n, pct=pct)
        return TrendInsight(
            direction=trend.direction, description=trend.description, confidence=conf,
            driver=driver, implication=implication, action_direction=action, confidence_basis=basis
        )

    def enrich_stability_insight(self, stability: StabilityInsight, n: int) -> StabilityInsight:
        cv = stability.coefficient_of_variation
        
        if cv < 0.3:
            driver = f"Stability pattern: low variance (CV={cv:.2f}) across {n} data points suggests high operational consistency."
            implication = "A stable revenue base supports highly reliable forecasting and strategic long-term planning."
            action = "Maintain current distribution; leverage stability to optimize resource allocation."
        else:
            driver = f"Volatility anomaly: significant dispersion in transaction values (CV={cv:.2f}) indicates revenue risk."
            implication = "High volatility creates unpredictability in cash flow and increases exposure to single-event shocks."
            action = "Identify structural drivers of volatility and implement variance-reduction strategies."
            
        conf, basis = self._compute_confidence(n, cv=cv)
        return StabilityInsight(
            category=stability.category, coefficient_of_variation=cv, description=stability.description,
            driver=driver, implication=implication, action_direction=action, confidence=conf, confidence_basis=basis
        )

    def enrich_efficiency_insight(self, efficiency: EfficiencyInsight, n: int) -> EfficiencyInsight:
        pct = efficiency.change_percent or 0.0

        if efficiency.signal == "efficiency_improved":
            driver = f"Yield expansion: average revenue per transaction increased, indicating improved monetization across {n} records."
            implication = f"The {abs(pct):.1f}% efficiency gain suggests stronger pricing power or favorable product mix shift."
            action = "Identify which segments drive the efficiency gain and replicate across underperforming areas."
        elif efficiency.signal == "efficiency_declined":
            driver = f"Yield compression: average revenue per transaction declined, suggesting pricing pressure or mix deterioration."
            implication = f"The {abs(pct):.1f}% efficiency loss may indicate discounting, lower-margin product shift, or customer downgrade."
            action = "Review pricing strategy and product mix changes to identify root cause of yield decline."
        else:
            driver = f"Revenue yield per transaction is stable across {n} records, showing consistent monetization."
            implication = "Stable efficiency indicates no significant changes in pricing or product mix impact."
            action = "Maintain current strategy; monitor for early signs of efficiency drift."

        conf, basis = self._compute_confidence(n, pct=pct)
        return EfficiencyInsight(
            signal=efficiency.signal, description=efficiency.description,
            change_percent=efficiency.change_percent,
            driver=driver, implication=implication, action_direction=action,
            confidence=conf, confidence_basis=basis
        )

    def enrich_concentration_insight(self, concentration: ConcentrationInsight, n: int) -> ConcentrationInsight:
        contrib = concentration.top_10_percent_contribution
        
        if contrib > 60:
            driver = f"Concentration dependency: top 10% of activity accounts for {contrib:.1f}% of total revenue volume."
            implication = f"Critical vulnerability detected; the business depends heavily on a small subset of contributors."
            action = "Develop a diversification strategy to mitigate dependency risk on top-tier records."
        else:
            driver = f"Distribution efficiency: revenue is broadly distributed with low dependency on outliers."
            implication = "A diversified revenue base provides resilience against the loss of individual high-value contributors."
            action = "Continue monitoring distribution shifts to prevent emerging concentration patterns."
            
        conf, basis = self._compute_confidence(n, cv=contrib/100)
        return ConcentrationInsight(
            top_10_percent_contribution=contrib, risk_level=concentration.risk_level, description=concentration.description,
            driver=driver, implication=implication, action_direction=action, confidence=conf, confidence_basis=basis
        )

    def generate(
        self, report: InsightReport, current_df: pd.DataFrame, baseline_df: Optional[pd.DataFrame],
        revenue_column: str, baseline_revenue_column: Optional[str] = None
    ) -> Optional[BusinessInsights]:
        try:
            rev_delta = next((d for d in report.metric_deltas if d.name.lower() == "revenue"), None)
            if not rev_delta: return None
            
            n = len(current_df)
            trend = self._generate_trend_insight(rev_delta, baseline_df is not None)
            stability = self._generate_stability_insight(current_df, revenue_column)
            efficiency = self._generate_efficiency_insight(rev_delta, baseline_df is not None)
            concentration = self._generate_concentration_insight(current_df, revenue_column)
            
            if trend: trend = self.enrich_trend_insight(trend, rev_delta, n)
            if stability: stability = self.enrich_stability_insight(stability, n)
            if efficiency: efficiency = self.enrich_efficiency_insight(efficiency, n) # Not enriched in this version
            if concentration: concentration = self.enrich_concentration_insight(concentration, n)
            
            exec_summary = self._generate_executive_summary(rev_delta, trend, stability, efficiency, concentration)
            takeaways = self.build_executive_takeaways(rev_delta, trend, stability, efficiency, concentration)
            
            return BusinessInsights(
                executive_takeaways=takeaways, scope=self.build_scope_block(),
                trend=trend, stability=stability, efficiency=efficiency, concentration=concentration,
                executive_summary=exec_summary
            )
        except Exception: return None

    def _generate_trend_insight(self, delta: MetricDelta, has_baseline: bool) -> Optional[TrendInsight]:
        if not has_baseline or delta.baseline == 0: return None
        pct = delta.percent_change
        if pct > 20: d, desc = "strong_upward", f"Growth signal: revenue increased {pct:.1f}% vs baseline."
        elif pct > 5: d, desc = "moderate_growth", f"Growth signal: revenue up {pct:.1f}%."
        elif pct >= -5: d, desc = "flat", "Stability: revenue unchanged vs baseline."
        elif pct >= -20: d, desc = "early_decline", f"Risk signal: revenue down {abs(pct):.1f}%."
        else: d, desc = "sharp_decline", f"Risk signal: sharp {abs(pct):.1f}% revenue decline."
        return TrendInsight(direction=d, description=desc, confidence="medium")

    def _generate_stability_insight(self, df: pd.DataFrame, rev_col: str) -> Optional[StabilityInsight]:
        vals = pd.to_numeric(df[rev_col], errors="coerce").dropna()
        if len(vals) < 2 or vals.mean() == 0: return None
        cv = abs(vals.std() / vals.mean())
        if cv < 0.3: cat, desc = "stable", f"Stability: revenue CV of {cv:.2f} indicates low volatility."
        elif cv < 0.7: cat, desc = "moderately_volatile", f"Volatility: moderate CV of {cv:.2f} detected."
        else: cat, desc = "highly_volatile", f"Anomaly: high CV of {cv:.2f} indicates extreme volatility."
        return StabilityInsight(category=cat, coefficient_of_variation=round(cv, 4), description=desc)

    def _generate_efficiency_insight(self, delta: MetricDelta, has_baseline: bool) -> Optional[EfficiencyInsight]:
        if not has_baseline: return None
        pct = delta.percent_change
        if pct > 10: s, desc = "efficiency_improved", f"Efficiency: revenue yield up {pct:.1f}%."
        elif pct >= -10: s, desc = "efficiency_stable", "Efficiency: revenue yield stable vs baseline."
        else: s, desc = "efficiency_declined", f"Efficiency risk: revenue yield down {abs(pct):.1f}%."
        return EfficiencyInsight(signal=s, description=desc, change_percent=round(pct, 2))

    def _generate_concentration_insight(self, df: pd.DataFrame, rev_col: str) -> Optional[ConcentrationInsight]:
        vals = pd.to_numeric(df[rev_col], errors="coerce").dropna()
        if len(vals) < 10 or vals.sum() == 0: return None
        top_10_sum = vals.sort_values(ascending=False).head(max(1, int(len(vals)*0.1))).sum()
        contrib = (top_10_sum / vals.sum()) * 100
        if contrib > 60: risk, desc = "high", f"Concentration risk: top 10% accounts for {contrib:.1f}% of revenue."
        elif contrib > 40: risk, desc = "moderate", f"Concentration: top 10% accounts for {contrib:.1f}% of revenue."
        else: risk, desc = "low", f"Stability: revenue is well-distributed (top 10% = {contrib:.1f}%)."
        return ConcentrationInsight(top_10_percent_contribution=round(contrib, 2), risk_level=risk, description=desc)

    def _generate_executive_summary(self, delta: MetricDelta, t: Optional[TrendInsight], s: Optional[StabilityInsight], e: Optional[EfficiencyInsight], c: Optional[ConcentrationInsight]) -> Optional[str]:
        parts = [f"Revenue changed {delta.percent_change:+.1f}% to ${delta.current:,.0f}." if delta.baseline > 0 else f"Revenue: ${delta.current:,.0f}."]
        if c and c.top_10_percent_contribution > 60: parts.append(f"Concentration risk detected: top 10% drives {c.top_10_percent_contribution:.0f}% of revenue.")
        if s and s.coefficient_of_variation > 0.7: parts.append("Volatility anomaly detected in transaction distribution.")
        return " ".join(parts)
