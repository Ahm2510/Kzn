"""
Business Insight Layer for Kaizen Insight Engine V1.75

This module provides an ADDITIVE overlay that generates business-meaningful
insights from existing metric data. It does NOT modify core computation logic.

Architecture:
    Raw Metrics → Existing Insight Engine (V1.75) → Business Insight Layer → Merged Output

All insights are optional and gracefully omitted if data is insufficient.
"""

import pandas as pd
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from schemas.insight.report import InsightReport
from schemas.insight.metrics import MetricDelta


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
    """
    
    # -------------------------------------------------------------------------
    # V1.75+ Enrichment Helper Methods
    # -------------------------------------------------------------------------
    
    def build_scope_block(self) -> ScopeBlock:
        """
        Build explicit scope definition for the analysis.
        Returns static scope based on V1.75 capabilities.
        """
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
        """
        Build 4-6 executive takeaway bullets prioritizing risk/critical items.
        """
        takeaways = []
        
        # Priority 1: Critical risks first
        if concentration and concentration.risk_level in ["critical", "high"]:
            takeaways.append(
                f"Concentration: top 10% of records account for {concentration.top_10_percent_contribution:.0f}% "
                f"of revenue — monitor dependency."
            )
        
        if stability and stability.category == "highly_volatile":
            takeaways.append(
                f"Volatility increased vs baseline (CV={stability.coefficient_of_variation:.2f}); "
                f"consider deeper segment analysis."
            )
        
        # Priority 2: Trend insights
        if trend:
            if trend.direction == "sharp_decline":
                takeaways.append(
                    f"Revenue declined significantly ({delta.percent_change:.1f}%); investigate root causes."
                )
            elif trend.direction == "strong_upward":
                takeaways.append(
                    f"Revenue growth driven by strong performance (+{delta.percent_change:.1f}%); "
                    f"quality of growth improved."
                )
            elif trend.direction == "moderate_growth":
                takeaways.append(
                    f"Moderate revenue growth ({delta.percent_change:.1f}%); trajectory is positive."
                )
            elif trend.direction == "early_decline":
                takeaways.append(
                    f"Early signs of revenue decline ({delta.percent_change:.1f}%); monitor closely."
                )
        
        # Priority 3: Efficiency signals
        if efficiency:
            if efficiency.signal == "efficiency_improved":
                pct = efficiency.change_percent or 0
                takeaways.append(
                    f"Efficiency improved; revenue per transaction up {pct:.0f}%."
                )
            elif efficiency.signal == "efficiency_declined":
                pct = abs(efficiency.change_percent or 0)
                takeaways.append(
                    f"Efficiency declined by {pct:.0f}%; review contributing factors."
                )
        
        # Priority 4: Stability (if not already added as risk)
        if stability and stability.category == "stable" and len(takeaways) < 5:
            takeaways.append(
                "Revenue patterns are consistent, supporting reliable forecasting."
            )
        
        # Priority 5: Moderate concentration (if not already added)
        if concentration and concentration.risk_level == "moderate" and len(takeaways) < 5:
            takeaways.append(
                f"Concentration is moderate ({concentration.top_10_percent_contribution:.0f}%); "
                f"diversification recommended."
            )
        
        # Ensure at least 4 bullets if we have data
        if len(takeaways) < 4 and delta.current > 0:
            if delta.baseline > 0:
                takeaways.append(
                    f"Revenue changed from ${delta.baseline:,.0f} to ${delta.current:,.0f} "
                    f"({delta.percent_change:+.1f}%)."
                )
            else:
                takeaways.append(f"Total revenue for the period: ${delta.current:,.0f}.")
        
        # Cap at 6 bullets
        return takeaways[:6]
    
    def _compute_confidence(
        self,
        sample_size: int,
        cv: Optional[float] = None,
        pct_change: Optional[float] = None,
    ) -> tuple:
        """
        Compute confidence level and basis string.
        
        Returns:
            Tuple of (confidence_level: str, confidence_basis: str)
        """
        pct = abs(pct_change) if pct_change is not None else 0
        cv_val = cv if cv is not None else 0.5
        
        # Build basis string
        basis_parts = [f"n={sample_size}"]
        if cv is not None:
            basis_parts.append(f"cv={cv_val:.2f}")
        if pct_change is not None:
            basis_parts.append(f"pct={pct_change:.1f}")
        basis = "; ".join(basis_parts)
        
        # Determine confidence level
        if sample_size >= 50 and (cv_val < 0.3 or pct >= 20):
            return "high", basis
        elif sample_size >= 20 and (5 <= pct <= 20 or 0.3 <= cv_val <= 0.7):
            return "medium", basis
        else:
            return "low", basis
    
    def enrich_trend_insight(
        self,
        trend: TrendInsight,
        delta: MetricDelta,
        sample_size: int,
    ) -> TrendInsight:
        """Enrich trend insight with driver, implication, action_direction, confidence_basis."""
        try:
            pct = delta.percent_change
            
            # Driver template
            if pct > 0:
                driver = "Primary driver: increase in revenue-generating activity."
            elif pct < 0:
                driver = "Primary driver: decrease in transaction volume or value."
            else:
                driver = "Primary driver: no significant change in business activity."
            
            # Implication template
            if trend.direction == "strong_upward":
                implication = "This implies improved monetization; growth trajectory is strong."
            elif trend.direction == "moderate_growth":
                implication = "Growth is positive but modest; sustained focus needed."
            elif trend.direction == "flat":
                implication = "Business is stable but not expanding; growth initiatives may be needed."
            elif trend.direction == "early_decline":
                implication = "Early warning sign; proactive intervention recommended."
            else:
                implication = "Significant decline requires immediate attention to prevent further losses."
            
            # Action direction template
            if trend.direction in ["sharp_decline", "early_decline"]:
                action_direction = "Investigate revenue decline drivers over next 2 periods."
            elif trend.direction == "strong_upward":
                action_direction = "Monitor capacity and sustainability of growth trajectory."
            else:
                action_direction = "Monitor revenue trends and identify growth opportunities."
            
            # Confidence
            _conf_level, conf_basis = self._compute_confidence(sample_size, pct_change=pct)
            
            return TrendInsight(
                direction=trend.direction,
                description=trend.description,
                confidence=trend.confidence,
                driver=driver,
                implication=implication,
                action_direction=action_direction,
                confidence_basis=conf_basis,
            )
        except Exception:
            return trend
    
    def enrich_stability_insight(
        self,
        stability: StabilityInsight,
        sample_size: int,
    ) -> StabilityInsight:
        """Enrich stability insight with driver, implication, action_direction, confidence."""
        try:
            cv = stability.coefficient_of_variation
            
            # Driver template
            if stability.category == "highly_volatile":
                driver = "Primary driver: significant variation in transaction values or timing."
            elif stability.category == "moderately_volatile":
                driver = "Primary driver: moderate fluctuations in revenue-generating activity."
            else:
                driver = "Primary driver: consistent revenue patterns across the dataset."
            
            # Implication template
            if stability.category == "highly_volatile":
                implication = "High volatility increases planning difficulty and cash flow risk."
            elif stability.category == "moderately_volatile":
                implication = "Moderate variability is manageable but warrants monitoring."
            else:
                implication = "Stable patterns support reliable forecasting and planning."
            
            # Action direction template
            if stability.category == "highly_volatile":
                action_direction = "Identify drivers of volatility for better planning."
            elif stability.category == "moderately_volatile":
                action_direction = "Monitor volatility trends over next period."
            else:
                action_direction = "Maintain current stability; monitor for changes."
            
            # Confidence
            conf_level, conf_basis = self._compute_confidence(sample_size, cv=cv)
            
            return StabilityInsight(
                category=stability.category,
                coefficient_of_variation=stability.coefficient_of_variation,
                description=stability.description,
                driver=driver,
                implication=implication,
                action_direction=action_direction,
                confidence=conf_level,
                confidence_basis=conf_basis,
            )
        except Exception:
            return stability
    
    def enrich_efficiency_insight(
        self,
        efficiency: EfficiencyInsight,
        sample_size: int,
    ) -> EfficiencyInsight:
        """Enrich efficiency insight with driver, implication, action_direction, confidence."""
        try:
            pct = efficiency.change_percent or 0
            
            # Driver template
            if efficiency.signal == "efficiency_improved":
                driver = "Primary driver: improved revenue per transaction or customer value."
            elif efficiency.signal == "efficiency_declined":
                driver = "Primary driver: decreased revenue yield per transaction."
            else:
                driver = "Primary driver: stable revenue efficiency metrics."
            
            # Implication template
            if efficiency.signal == "efficiency_improved":
                implication = "This implies improvement in monetization; acquisition pressure reduced."
            elif efficiency.signal == "efficiency_declined":
                implication = "Declining efficiency may indicate pricing or mix issues."
            else:
                implication = "Efficiency is stable; focus on volume growth if expansion needed."
            
            # Action direction template
            if efficiency.signal == "efficiency_declined":
                action_direction = "Review pricing strategy and product mix."
            elif efficiency.signal == "efficiency_improved":
                action_direction = "Sustain efficiency gains; monitor for sustainability."
            else:
                action_direction = "Monitor efficiency metrics for emerging trends."
            
            # Confidence
            conf_level, conf_basis = self._compute_confidence(sample_size, pct_change=pct)
            
            return EfficiencyInsight(
                signal=efficiency.signal,
                description=efficiency.description,
                change_percent=efficiency.change_percent,
                driver=driver,
                implication=implication,
                action_direction=action_direction,
                confidence=conf_level,
                confidence_basis=conf_basis,
            )
        except Exception:
            return efficiency
    
    def enrich_concentration_insight(
        self,
        concentration: ConcentrationInsight,
        sample_size: int,
    ) -> ConcentrationInsight:
        """Enrich concentration insight with driver, implication, action_direction, confidence."""
        try:
            contrib = concentration.top_10_percent_contribution
            
            # Driver template
            driver = f"Primary contributing group: top 10% accounts for {contrib:.0f}% of revenue."
            
            # Implication template
            if concentration.risk_level == "critical":
                implication = (
                    f"This increases fragility because the business depends on a small set of "
                    f"contributors; a shift could reduce revenue by ~{contrib:.0f}%."
                )
            elif concentration.risk_level == "high":
                implication = (
                    f"Elevated concentration risk; dependency on top contributors creates vulnerability."
                )
            elif concentration.risk_level == "moderate":
                implication = "Moderate concentration is manageable but diversification would reduce risk."
            else:
                implication = "Well-distributed revenue base reduces dependency risk."
            
            # Action direction template
            if concentration.risk_level in ["critical", "high"]:
                action_direction = "Prepare an exposure mitigation plan if the top contributor share persists."
            elif concentration.risk_level == "moderate":
                action_direction = "Monitor top contributors for retention anomalies."
            else:
                action_direction = "Maintain revenue distribution; monitor for concentration shifts."
            
            # Confidence (concentration requires sufficient sample)
            if sample_size < 20:
                conf_level = "low"
            elif concentration.risk_level in ["critical", "high"]:
                conf_level = "high"
            else:
                conf_level = "medium"
            conf_basis = f"n={sample_size}; top_10_pct={contrib:.1f}"
            
            return ConcentrationInsight(
                top_10_percent_contribution=concentration.top_10_percent_contribution,
                risk_level=concentration.risk_level,
                description=concentration.description,
                driver=driver,
                implication=implication,
                action_direction=action_direction,
                confidence=conf_level,
                confidence_basis=conf_basis,
            )
        except Exception:
            return concentration
    
    # -------------------------------------------------------------------------
    # Main Generate Method
    # -------------------------------------------------------------------------
    
    def generate(
        self,
        report: InsightReport,
        current_df: pd.DataFrame,
        baseline_df: Optional[pd.DataFrame],
        revenue_column: str,
        baseline_revenue_column: Optional[str] = None,
    ) -> Optional[BusinessInsights]:
        """
        Generate business insights from existing report and raw data.
        
        Args:
            report: The existing InsightReport from V1.75 engine
            current_df: Current period DataFrame
            baseline_df: Baseline period DataFrame (optional)
            revenue_column: Detected revenue column in current_df
            baseline_revenue_column: Detected revenue column in baseline_df
            
        Returns:
            BusinessInsights object, or None if no insights can be generated
        """
        try:
            # Find revenue metric delta
            revenue_delta = self._find_revenue_delta(report.metric_deltas)
            if revenue_delta is None:
                return None
            
            # Get sample size for confidence calculations
            sample_size = len(current_df)
            
            # Generate each insight (all are optional)
            trend = self._generate_trend_insight(revenue_delta, baseline_df is not None)
            stability = self._generate_stability_insight(current_df, revenue_column)
            efficiency = self._generate_efficiency_insight(revenue_delta, baseline_df is not None)
            concentration = self._generate_concentration_insight(current_df, revenue_column)
            
            # V1.75+ Enrichment: Add driver, implication, action_direction, confidence_basis
            try:
                if trend:
                    trend = self.enrich_trend_insight(trend, revenue_delta, sample_size)
                if stability:
                    stability = self.enrich_stability_insight(stability, sample_size)
                if efficiency:
                    efficiency = self.enrich_efficiency_insight(efficiency, sample_size)
                if concentration:
                    concentration = self.enrich_concentration_insight(concentration, sample_size)
            except Exception:
                # Enrichment is optional - continue with base insights if enrichment fails
                pass
            
            # Generate executive summary
            executive_summary = self._generate_executive_summary(
                revenue_delta, trend, stability, efficiency, concentration
            )
            
            # V1.75+ Build executive takeaways and scope
            try:
                executive_takeaways = self.build_executive_takeaways(
                    revenue_delta, trend, stability, efficiency, concentration
                )
                scope = self.build_scope_block()
            except Exception:
                executive_takeaways = None
                scope = None
            
            # Only return if at least one insight was generated
            if not any([trend, stability, efficiency, concentration, executive_summary]):
                return None
            
            return BusinessInsights(
                executive_takeaways=executive_takeaways if executive_takeaways else None,
                scope=scope,
                trend=trend,
                stability=stability,
                efficiency=efficiency,
                concentration=concentration,
                executive_summary=executive_summary,
            )
        except Exception:
            # Graceful degradation - never fail the main request
            return None
    
    def _find_revenue_delta(self, metric_deltas: List[MetricDelta]) -> Optional[MetricDelta]:
        """Find the revenue metric delta from the list."""
        for delta in metric_deltas:
            if delta.name.lower() == "revenue":
                return delta
        return None
    
    def _generate_trend_insight(
        self,
        delta: MetricDelta,
        has_baseline: bool,
    ) -> Optional[TrendInsight]:
        """
        Generate trend direction insight based on percent change.
        
        Categories:
        - Strong upward trend: > 20%
        - Moderate growth: 5% to 20%
        - Flat / stagnant: -5% to 5%
        - Early decline: -20% to -5%
        - Sharp decline: < -20%
        """
        if not has_baseline or delta.baseline == 0:
            return None
        
        pct = delta.percent_change
        
        if pct > 20:
            direction = "strong_upward"
            description = "Strong upward trend detected. Revenue is growing significantly compared to baseline."
            confidence = "high"
        elif pct > 5:
            direction = "moderate_growth"
            description = "Moderate growth observed. Revenue is trending positively but not dramatically."
            confidence = "medium"
        elif pct >= -5:
            direction = "flat"
            description = "Revenue is relatively flat compared to baseline. No significant trend detected."
            confidence = "medium"
        elif pct >= -20:
            direction = "early_decline"
            description = "Early signs of decline detected. Revenue is trending downward compared to baseline."
            confidence = "medium"
        else:
            direction = "sharp_decline"
            description = "Sharp decline detected. Revenue has dropped significantly compared to baseline."
            confidence = "high"
        
        return TrendInsight(
            direction=direction,
            description=description,
            confidence=confidence,
        )
    
    def _generate_stability_insight(
        self,
        df: pd.DataFrame,
        revenue_column: str,
    ) -> Optional[StabilityInsight]:
        """
        Generate volatility/stability insight using coefficient of variation.
        
        CV = std / mean
        Categories:
        - Stable: CV < 0.3
        - Moderately volatile: 0.3 <= CV < 0.7
        - Highly volatile: CV >= 0.7
        """
        try:
            revenue_values = df[revenue_column].dropna()
            
            if len(revenue_values) < 2:
                return None
            
            mean_val = revenue_values.mean()
            if mean_val == 0:
                return None
            
            std_val = revenue_values.std()
            cv = abs(std_val / mean_val)
            
            if cv < 0.3:
                category = "stable"
                description = "Revenue is highly consistent across the dataset. This indicates predictable income patterns."
            elif cv < 0.7:
                category = "moderately_volatile"
                description = "Revenue shows moderate variability. Some fluctuation is present but within reasonable bounds."
            else:
                category = "highly_volatile"
                description = "Revenue is highly volatile. Significant fluctuations may indicate risk or seasonality."
            
            return StabilityInsight(
                category=category,
                coefficient_of_variation=round(cv, 4),
                description=description,
            )
        except Exception:
            return None
    
    def _generate_efficiency_insight(
        self,
        delta: MetricDelta,
        has_baseline: bool,
    ) -> Optional[EfficiencyInsight]:
        """
        Generate ROI-style proxy insight (revenue efficiency signal).
        
        This is NOT true ROI - it's a revenue efficiency proxy.
        """
        if not has_baseline:
            # Standalone mode
            if delta.current > 0:
                return EfficiencyInsight(
                    signal="positive_revenue",
                    description=f"Total revenue of ${delta.current:,.2f} recorded. Baseline comparison not available.",
                )
            return None
        
        if delta.baseline == 0:
            return None
        
        pct = delta.percent_change
        
        if pct > 10:
            signal = "efficiency_improved"
            description = f"Revenue efficiency improved by {pct:.1f}% relative to baseline. Growth trajectory is positive."
        elif pct > 0:
            signal = "marginal_improvement"
            description = f"Slight improvement of {pct:.1f}% in revenue efficiency. Growth is present but modest."
        elif pct >= -10:
            signal = "efficiency_stable"
            description = f"Revenue efficiency is relatively stable ({pct:.1f}% change). No significant shift detected."
        else:
            signal = "efficiency_declined"
            description = f"Revenue efficiency declined by {abs(pct):.1f}% relative to baseline. Review contributing factors."
        
        return EfficiencyInsight(
            signal=signal,
            description=description,
            change_percent=round(pct, 2),
        )
    
    def _generate_concentration_insight(
        self,
        df: pd.DataFrame,
        revenue_column: str,
    ) -> Optional[ConcentrationInsight]:
        """
        Detect revenue concentration risk.
        
        Measures what percentage of total revenue comes from top 10% of rows.
        High concentration indicates risk exposure.
        """
        try:
            revenue_values = df[revenue_column].dropna()
            
            if len(revenue_values) < 10:
                return None
            
            total = revenue_values.sum()
            if total == 0:
                return None
            
            # Sort descending and get top 10%
            sorted_values = revenue_values.sort_values(ascending=False)
            top_10_pct_count = max(1, int(len(sorted_values) * 0.1))
            top_10_pct_sum = sorted_values.head(top_10_pct_count).sum()
            
            contribution = (top_10_pct_sum / total) * 100
            
            if contribution > 80:
                risk_level = "critical"
                description = f"Top 10% of rows contribute {contribution:.0f}% of revenue. Concentration risk is critical."
            elif contribution > 60:
                risk_level = "high"
                description = f"Top 10% of rows contribute {contribution:.0f}% of revenue. Concentration risk is elevated."
            elif contribution > 40:
                risk_level = "moderate"
                description = f"Top 10% of rows contribute {contribution:.0f}% of revenue. Concentration is moderate."
            else:
                risk_level = "low"
                description = f"Top 10% of rows contribute {contribution:.0f}% of revenue. Revenue is well-distributed."
            
            return ConcentrationInsight(
                top_10_percent_contribution=round(contribution, 2),
                risk_level=risk_level,
                description=description,
            )
        except Exception:
            return None
    
    def _generate_executive_summary(
        self,
        delta: MetricDelta,
        trend: Optional[TrendInsight],
        stability: Optional[StabilityInsight],
        efficiency: Optional[EfficiencyInsight],
        concentration: Optional[ConcentrationInsight],
    ) -> Optional[str]:
        """
        Generate a concise executive summary paragraph.
        
        Answers:
        - What happened?
        - Why it matters?
        - What should the business watch next?
        """
        parts = []
        
        # What happened
        if delta.baseline > 0:
            if delta.percent_change > 0:
                parts.append(
                    f"Revenue increased by {delta.percent_change:.1f}% to ${delta.current:,.0f} "
                    f"compared to a baseline of ${delta.baseline:,.0f}."
                )
            elif delta.percent_change < 0:
                parts.append(
                    f"Revenue decreased by {abs(delta.percent_change):.1f}% to ${delta.current:,.0f} "
                    f"from a baseline of ${delta.baseline:,.0f}."
                )
            else:
                parts.append(
                    f"Revenue remained stable at ${delta.current:,.0f}, matching baseline levels."
                )
        else:
            parts.append(f"Total revenue for the period is ${delta.current:,.0f}.")
        
        # Why it matters (based on stability and concentration)
        matters = []
        if stability:
            if stability.category == "highly_volatile":
                matters.append("high revenue volatility suggests unpredictable cash flows")
            elif stability.category == "stable":
                matters.append("consistent revenue patterns support reliable forecasting")
        
        if concentration:
            if concentration.risk_level in ["critical", "high"]:
                matters.append(f"concentration risk is {concentration.risk_level} with top contributors dominating revenue")
        
        if matters:
            parts.append("This matters because " + " and ".join(matters) + ".")
        
        # What to watch
        watch = []
        if trend:
            if trend.direction == "sharp_decline":
                watch.append("investigate root causes of revenue decline")
            elif trend.direction == "strong_upward":
                watch.append("sustain growth momentum and monitor capacity")
        
        if concentration and concentration.risk_level in ["critical", "high"]:
            watch.append("diversify revenue sources to reduce dependency risk")
        
        if stability and stability.category == "highly_volatile":
            watch.append("identify drivers of volatility for better planning")
        
        if watch:
            parts.append("Next steps: " + "; ".join(watch) + ".")
        
        if not parts:
            return None
        
        return " ".join(parts)
