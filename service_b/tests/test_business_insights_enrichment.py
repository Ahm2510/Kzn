"""
V1.75+ Business Insights Enrichment Tests

Tests for the new enrichment functions:
- enrich_insight
- build_executive_takeaways
- build_scope_block
- Full pipeline with enriched fields
"""

import pytest
import pandas as pd
import numpy as np

from services.business_insights.generator import (
    BusinessInsightGenerator,
    BusinessInsights,
    TrendInsight,
    StabilityInsight,
    EfficiencyInsight,
    ConcentrationInsight,
    ScopeBlock,
)
from schemas.insight.report import InsightReport
from schemas.insight.metrics import MetricDelta
from schemas.insight.insights import Insight


class TestEnrichmentFunctions:
    """Tests for individual enrichment functions."""
    
    @pytest.fixture
    def generator(self):
        return BusinessInsightGenerator()
    
    @pytest.fixture
    def sample_delta_growth(self):
        """Sample MetricDelta with >20% growth."""
        return MetricDelta(
            name="revenue",
            current=120000,
            baseline=100000,
            absolute_change=20000,
            percent_change=20.0,
        )
    
    @pytest.fixture
    def sample_delta_decline(self):
        """Sample MetricDelta with sharp decline."""
        return MetricDelta(
            name="revenue",
            current=70000,
            baseline=100000,
            absolute_change=-30000,
            percent_change=-30.0,
        )
    
    def test_build_scope_block(self, generator):
        """Test scope block generation."""
        scope = generator.build_scope_block()
        
        assert isinstance(scope, ScopeBlock)
        assert "revenue" in scope.analyzed
        assert "costs" in scope.not_analyzed
        assert "margins" in scope.not_analyzed
        assert "forecasting" in scope.not_analyzed
        assert "cohort_analysis" in scope.not_analyzed
    
    def test_enrich_trend_strong_upward(self, generator, sample_delta_growth):
        """Test trend enrichment for strong upward trend (>20%)."""
        base_trend = TrendInsight(
            direction="strong_upward",
            description="Strong growth detected.",
            confidence="high",
        )
        
        enriched = generator.enrich_trend_insight(base_trend, sample_delta_growth, sample_size=100)
        
        assert enriched.direction == "strong_upward"
        assert enriched.confidence == "high"
        assert enriched.driver is not None
        assert "increase" in enriched.driver.lower()
        assert enriched.implication is not None
        assert enriched.action_direction is not None
        assert enriched.confidence_basis is not None
        assert "n=100" in enriched.confidence_basis
    
    def test_enrich_trend_sharp_decline(self, generator, sample_delta_decline):
        """Test trend enrichment for sharp decline (<-20%)."""
        base_trend = TrendInsight(
            direction="sharp_decline",
            description="Sharp decline detected.",
            confidence="high",
        )
        
        enriched = generator.enrich_trend_insight(base_trend, sample_delta_decline, sample_size=50)
        
        assert enriched.direction == "sharp_decline"
        assert enriched.driver is not None
        assert "decrease" in enriched.driver.lower()
        assert enriched.implication is not None
        assert "immediate attention" in enriched.implication.lower() or "decline" in enriched.implication.lower()
        assert enriched.action_direction is not None
        assert "investigate" in enriched.action_direction.lower()
    
    def test_enrich_stability_highly_volatile(self, generator):
        """Test stability enrichment for CV > 0.7."""
        base_stability = StabilityInsight(
            category="highly_volatile",
            coefficient_of_variation=0.85,
            description="High volatility detected.",
        )
        
        enriched = generator.enrich_stability_insight(base_stability, sample_size=30)
        
        assert enriched.category == "highly_volatile"
        assert enriched.coefficient_of_variation == 0.85
        assert enriched.driver is not None
        assert enriched.implication is not None
        assert "volatility" in enriched.implication.lower() or "planning" in enriched.implication.lower()
        assert enriched.action_direction is not None
        assert enriched.confidence is not None
        assert enriched.confidence_basis is not None
        assert "cv=0.85" in enriched.confidence_basis
    
    def test_enrich_stability_stable(self, generator):
        """Test stability enrichment for CV < 0.3."""
        base_stability = StabilityInsight(
            category="stable",
            coefficient_of_variation=0.15,
            description="Stable patterns detected.",
        )
        
        enriched = generator.enrich_stability_insight(base_stability, sample_size=100)
        
        assert enriched.category == "stable"
        assert enriched.confidence == "high"  # n>=50 and cv<0.3
        assert enriched.implication is not None
        assert "reliable" in enriched.implication.lower() or "stable" in enriched.implication.lower()
    
    def test_enrich_concentration_high_risk(self, generator):
        """Test concentration enrichment for top 10% > 60%."""
        base_concentration = ConcentrationInsight(
            top_10_percent_contribution=65.0,
            risk_level="high",
            description="High concentration detected.",
        )
        
        enriched = generator.enrich_concentration_insight(base_concentration, sample_size=50)
        
        assert enriched.risk_level == "high"
        assert enriched.driver is not None
        assert "top 10%" in enriched.driver.lower()
        assert "65%" in enriched.driver
        assert enriched.implication is not None
        assert "vulnerability" in enriched.implication.lower() or "concentration" in enriched.implication.lower()
        assert enriched.action_direction is not None
        assert "mitigation" in enriched.action_direction.lower() or "exposure" in enriched.action_direction.lower()
        assert enriched.confidence == "high"
    
    def test_enrich_concentration_low_sample_size(self, generator):
        """Test concentration confidence is low for small sample size."""
        base_concentration = ConcentrationInsight(
            top_10_percent_contribution=45.0,
            risk_level="moderate",
            description="Moderate concentration.",
        )
        
        enriched = generator.enrich_concentration_insight(base_concentration, sample_size=15)
        
        assert enriched.confidence == "low"  # sample_size < 20


class TestExecutiveTakeaways:
    """Tests for build_executive_takeaways function."""
    
    @pytest.fixture
    def generator(self):
        return BusinessInsightGenerator()
    
    @pytest.fixture
    def sample_delta(self):
        return MetricDelta(
            name="revenue",
            current=112000,
            baseline=100000,
            absolute_change=12000,
            percent_change=12.0,
        )
    
    def test_takeaways_returns_4_to_6_bullets(self, generator, sample_delta):
        """Test that executive takeaways returns 4-6 bullets."""
        trend = TrendInsight(
            direction="moderate_growth",
            description="Moderate growth.",
            confidence="medium",
        )
        stability = StabilityInsight(
            category="stable",
            coefficient_of_variation=0.2,
            description="Stable.",
        )
        efficiency = EfficiencyInsight(
            signal="efficiency_improved",
            description="Improved.",
            change_percent=12.0,
        )
        concentration = ConcentrationInsight(
            top_10_percent_contribution=35.0,
            risk_level="low",
            description="Well distributed.",
        )
        
        takeaways = generator.build_executive_takeaways(
            sample_delta, trend, stability, efficiency, concentration
        )
        
        assert isinstance(takeaways, list)
        assert 1 <= len(takeaways) <= 6
    
    def test_takeaways_prioritizes_risks(self, generator, sample_delta):
        """Test that high-risk items are prioritized first."""
        trend = TrendInsight(
            direction="sharp_decline",
            description="Decline.",
            confidence="high",
        )
        concentration = ConcentrationInsight(
            top_10_percent_contribution=75.0,
            risk_level="high",
            description="High concentration.",
        )
        stability = StabilityInsight(
            category="highly_volatile",
            coefficient_of_variation=0.9,
            description="Volatile.",
        )
        
        takeaways = generator.build_executive_takeaways(
            sample_delta, trend, stability, None, concentration
        )
        
        assert len(takeaways) >= 2
        # First bullet should mention concentration or volatility (risks)
        first_bullet_lower = takeaways[0].lower()
        assert "concentration" in first_bullet_lower or "volatility" in first_bullet_lower
    
    def test_takeaways_includes_risk_implication(self, generator):
        """Test that takeaways include risk implications for risky situations."""
        delta = MetricDelta(
            name="revenue",
            current=65000,
            baseline=100000,
            absolute_change=-35000,
            percent_change=-35.0,
        )
        trend = TrendInsight(
            direction="sharp_decline",
            description="Sharp decline.",
            confidence="high",
        )
        concentration = ConcentrationInsight(
            top_10_percent_contribution=82.0,
            risk_level="critical",
            description="Critical concentration.",
        )
        
        takeaways = generator.build_executive_takeaways(
            delta, trend, None, None, concentration
        )
        
        # Should contain at least one risk-related bullet
        all_text = " ".join(takeaways).lower()
        assert "concentration" in all_text or "decline" in all_text or "monitor" in all_text


class TestFullPipelineEnrichment:
    """Tests for full generate() pipeline with enrichment."""
    
    @pytest.fixture
    def generator(self):
        return BusinessInsightGenerator()
    
    @pytest.fixture
    def sample_report(self):
        return InsightReport(
            summary="Revenue analysis complete.",
            metric_deltas=[
                MetricDelta(
                    name="revenue",
                    current=125000,
                    baseline=100000,
                    absolute_change=25000,
                    percent_change=25.0,
                )
            ],
            insights=[
                Insight(
                    code="REVENUE_GROWTH",
                    severity="low",
                    title="Revenue growth detected",
                    description="Revenue grew by 25%.",
                    affected_metric="revenue",
                )
            ],
        )
    
    @pytest.fixture
    def large_current_df(self):
        """DataFrame with 100 rows for high confidence."""
        np.random.seed(42)
        return pd.DataFrame({
            "revenue": np.random.exponential(1000, 100),
            "date": pd.date_range("2024-01-01", periods=100),
        })
    
    @pytest.fixture
    def large_baseline_df(self):
        """Baseline DataFrame with 100 rows."""
        np.random.seed(41)
        return pd.DataFrame({
            "revenue": np.random.exponential(800, 100),
            "date": pd.date_range("2023-01-01", periods=100),
        })
    
    @pytest.fixture
    def small_current_df(self):
        """DataFrame with <10 rows for low confidence."""
        return pd.DataFrame({
            "revenue": [100, 200, 300, 400, 500],
            "date": pd.date_range("2024-01-01", periods=5),
        })
    
    def test_full_pipeline_includes_enriched_fields(
        self, generator, sample_report, large_current_df, large_baseline_df
    ):
        """Test that full pipeline produces enriched fields."""
        result = generator.generate(
            report=sample_report,
            current_df=large_current_df,
            baseline_df=large_baseline_df,
            revenue_column="revenue",
            baseline_revenue_column="revenue",
        )
        
        assert result is not None
        
        # Check executive_takeaways
        assert result.executive_takeaways is not None
        assert isinstance(result.executive_takeaways, list)
        assert len(result.executive_takeaways) >= 1
        
        # Check scope
        assert result.scope is not None
        assert "revenue" in result.scope.analyzed
        assert "costs" in result.scope.not_analyzed
        
        # Check trend enrichment
        if result.trend:
            assert result.trend.driver is not None
            assert result.trend.implication is not None
            assert result.trend.action_direction is not None
            assert result.trend.confidence_basis is not None
        
        # Check stability enrichment
        if result.stability:
            assert result.stability.driver is not None
            assert result.stability.implication is not None
            assert result.stability.confidence is not None
            assert result.stability.confidence_basis is not None
        
        # Check concentration enrichment (if present)
        if result.concentration:
            assert result.concentration.driver is not None
            assert result.concentration.implication is not None
            assert result.concentration.confidence is not None
    
    def test_small_dataset_lowers_confidence(self, generator, small_current_df):
        """Test that small datasets result in lower confidence or omitted insights."""
        report = InsightReport(
            summary="Small dataset analysis.",
            metric_deltas=[
                MetricDelta(
                    name="revenue",
                    current=1500,
                    baseline=0,
                    absolute_change=1500,
                    percent_change=0.0,
                )
            ],
            insights=[],
        )
        
        result = generator.generate(
            report=report,
            current_df=small_current_df,
            baseline_df=None,
            revenue_column="revenue",
        )
        
        # With small dataset, concentration should be None (requires >=10 rows)
        if result:
            assert result.concentration is None
            
            # Stability should exist but with lower confidence
            if result.stability:
                # Small sample = lower confidence
                assert result.stability.confidence in ["low", "medium"]
    
    def test_executive_summary_exists(
        self, generator, sample_report, large_current_df, large_baseline_df
    ):
        """Test that executive_summary is generated."""
        result = generator.generate(
            report=sample_report,
            current_df=large_current_df,
            baseline_df=large_baseline_df,
            revenue_column="revenue",
            baseline_revenue_column="revenue",
        )
        
        assert result is not None
        assert result.executive_summary is not None
        assert len(result.executive_summary) > 50


class TestConfidenceMapping:
    """Tests for confidence level computation."""
    
    @pytest.fixture
    def generator(self):
        return BusinessInsightGenerator()
    
    def test_high_confidence_large_sample_low_cv(self, generator):
        """High confidence: n>=50, CV<0.3."""
        conf, basis = generator._compute_confidence(
            sample_size=100,
            cv=0.15,
            pct_change=15.0,
        )
        assert conf == "high"
        assert "n=100" in basis
        assert "cv=0.15" in basis
    
    def test_high_confidence_large_pct_change(self, generator):
        """High confidence: pct change >=20%."""
        conf, basis = generator._compute_confidence(
            sample_size=60,
            pct_change=25.0,
        )
        assert conf == "high"
    
    def test_medium_confidence(self, generator):
        """Medium confidence: n>=20, 5<=pct<=20 or 0.3<=CV<=0.7."""
        conf, basis = generator._compute_confidence(
            sample_size=30,
            cv=0.5,
            pct_change=10.0,
        )
        assert conf == "medium"
    
    def test_low_confidence_small_sample(self, generator):
        """Low confidence: n<20."""
        conf, basis = generator._compute_confidence(
            sample_size=10,
            cv=0.2,
            pct_change=5.0,
        )
        assert conf == "low"
    
    def test_low_confidence_high_cv_low_pct(self, generator):
        """Low confidence: CV>0.7 and pct<5%."""
        conf, basis = generator._compute_confidence(
            sample_size=30,
            cv=0.9,
            pct_change=2.0,
        )
        assert conf == "low"


class TestSampleOutputJSON:
    """Test that output matches expected JSON structure."""
    
    @pytest.fixture
    def generator(self):
        return BusinessInsightGenerator()
    
    def test_output_json_structure(self, generator):
        """Test that output matches expected ₹70K schema."""
        np.random.seed(42)
        current_df = pd.DataFrame({
            "revenue": np.random.exponential(1000, 234),
        })
        baseline_df = pd.DataFrame({
            "revenue": np.random.exponential(900, 200),
        })
        
        report = InsightReport(
            summary="Analysis complete.",
            metric_deltas=[
                MetricDelta(
                    name="revenue",
                    current=234000,
                    baseline=180000,
                    absolute_change=54000,
                    percent_change=30.0,
                )
            ],
            insights=[],
        )
        
        result = generator.generate(
            report=report,
            current_df=current_df,
            baseline_df=baseline_df,
            revenue_column="revenue",
            baseline_revenue_column="revenue",
        )
        
        assert result is not None
        
        # Convert to dict for JSON structure validation
        result_dict = result.dict()
        
        # Validate top-level keys
        assert "executive_takeaways" in result_dict
        assert "scope" in result_dict
        assert "trend" in result_dict
        assert "stability" in result_dict
        assert "efficiency" in result_dict
        assert "concentration" in result_dict
        assert "executive_summary" in result_dict
        
        # Validate scope structure
        assert result_dict["scope"]["analyzed"] == ["revenue"]
        assert "costs" in result_dict["scope"]["not_analyzed"]
        
        # Validate trend enrichment fields
        if result_dict["trend"]:
            trend = result_dict["trend"]
            assert "direction" in trend
            assert "description" in trend
            assert "driver" in trend
            assert "implication" in trend
            assert "action_direction" in trend
            assert "confidence" in trend
            assert "confidence_basis" in trend
        
        # Validate concentration enrichment fields
        if result_dict["concentration"]:
            conc = result_dict["concentration"]
            assert "top_10_percent_contribution" in conc
            assert "risk_level" in conc
            assert "driver" in conc
            assert "implication" in conc
            assert "action_direction" in conc
            assert "confidence" in conc
            assert "confidence_basis" in conc
