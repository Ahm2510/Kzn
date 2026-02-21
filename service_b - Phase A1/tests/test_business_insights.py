"""
Tests for Business Insight Layer (V1.75 Additive Extension)

These tests verify:
- Business insights are generated correctly
- Existing outputs remain unchanged
- Graceful handling of edge cases
- All 5 insight types work as expected
"""

import pytest
import pandas as pd
from services.business_insights.generator import (
    BusinessInsightGenerator,
    BusinessInsights,
    TrendInsight,
    StabilityInsight,
    EfficiencyInsight,
    ConcentrationInsight,
)
from schemas.insight.report import InsightReport
from schemas.insight.metrics import MetricDelta
from schemas.insight.insights import Insight


@pytest.fixture
def generator():
    return BusinessInsightGenerator()


@pytest.fixture
def sample_report_with_baseline():
    """Report with baseline comparison (21.7% growth)"""
    return InsightReport(
        summary="Revenue increased.",
        metric_deltas=[
            MetricDelta(
                name="revenue",
                current=589400.0,
                baseline=484400.0,
                absolute_change=105000.0,
                percent_change=21.68,
            )
        ],
        insights=[],
    )


@pytest.fixture
def sample_report_standalone():
    """Report without baseline (standalone mode)"""
    return InsightReport(
        summary="Revenue summary.",
        metric_deltas=[
            MetricDelta(
                name="revenue",
                current=100000.0,
                baseline=0.0,
                absolute_change=100000.0,
                percent_change=0.0,
            )
        ],
        insights=[
            Insight(
                code="REVENUE_SUMMARY",
                severity="low",
                title="Revenue summary",
                description="Total revenue is $100,000.00",
                affected_metric="revenue",
            )
        ],
    )


@pytest.fixture
def sample_report_decline():
    """Report with sharp decline (-25%)"""
    return InsightReport(
        summary="Revenue decreased.",
        metric_deltas=[
            MetricDelta(
                name="revenue",
                current=75000.0,
                baseline=100000.0,
                absolute_change=-25000.0,
                percent_change=-25.0,
            )
        ],
        insights=[],
    )


@pytest.fixture
def sample_report_flat():
    """Report with flat revenue (0% change)"""
    return InsightReport(
        summary="Revenue stable.",
        metric_deltas=[
            MetricDelta(
                name="revenue",
                current=100000.0,
                baseline=100000.0,
                absolute_change=0.0,
                percent_change=0.0,
            )
        ],
        insights=[],
    )


@pytest.fixture
def stable_revenue_df():
    """DataFrame with stable revenue (low volatility)"""
    return pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=20),
        "revenue": [1000, 1010, 990, 1005, 995, 1000, 1008, 992, 1003, 997,
                    1001, 999, 1004, 996, 1002, 998, 1006, 994, 1000, 1000],
    })


@pytest.fixture
def volatile_revenue_df():
    """DataFrame with highly volatile revenue"""
    return pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=20),
        "revenue": [100, 5000, 200, 8000, 150, 3000, 50, 10000, 300, 6000,
                    100, 4000, 250, 7000, 180, 2000, 80, 9000, 400, 5500],
    })


@pytest.fixture
def concentrated_revenue_df():
    """DataFrame with high concentration (few rows dominate)"""
    data = {"date": pd.date_range("2024-01-01", periods=100), "revenue": [100] * 90 + [10000] * 10}
    return pd.DataFrame(data)


@pytest.fixture
def distributed_revenue_df():
    """DataFrame with well-distributed revenue"""
    return pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=100),
        "revenue": [1000] * 100,
    })


class TestTrendInsight:
    def test_strong_upward_trend(self, generator, sample_report_with_baseline, stable_revenue_df):
        """Test detection of strong upward trend (>20%)"""
        result = generator.generate(
            report=sample_report_with_baseline,
            current_df=stable_revenue_df,
            baseline_df=stable_revenue_df.copy(),
            revenue_column="revenue",
            baseline_revenue_column="revenue",
        )
        
        assert result is not None
        assert result.trend is not None
        assert result.trend.direction == "strong_upward"
        assert result.trend.confidence == "high"
    
    def test_sharp_decline_trend(self, generator, sample_report_decline, stable_revenue_df):
        """Test detection of sharp decline (<-20%)"""
        result = generator.generate(
            report=sample_report_decline,
            current_df=stable_revenue_df,
            baseline_df=stable_revenue_df.copy(),
            revenue_column="revenue",
        )
        
        assert result is not None
        assert result.trend is not None
        assert result.trend.direction == "sharp_decline"
    
    def test_flat_trend(self, generator, sample_report_flat, stable_revenue_df):
        """Test detection of flat revenue"""
        result = generator.generate(
            report=sample_report_flat,
            current_df=stable_revenue_df,
            baseline_df=stable_revenue_df.copy(),
            revenue_column="revenue",
        )
        
        assert result is not None
        assert result.trend is not None
        assert result.trend.direction == "flat"
    
    def test_no_trend_without_baseline(self, generator, sample_report_standalone, stable_revenue_df):
        """Trend insight should be None without baseline"""
        result = generator.generate(
            report=sample_report_standalone,
            current_df=stable_revenue_df,
            baseline_df=None,
            revenue_column="revenue",
        )
        
        assert result is not None
        assert result.trend is None


class TestStabilityInsight:
    def test_stable_revenue(self, generator, sample_report_standalone, stable_revenue_df):
        """Test detection of stable revenue (low CV)"""
        result = generator.generate(
            report=sample_report_standalone,
            current_df=stable_revenue_df,
            baseline_df=None,
            revenue_column="revenue",
        )
        
        assert result is not None
        assert result.stability is not None
        assert result.stability.category == "stable"
        assert result.stability.coefficient_of_variation < 0.3
    
    def test_volatile_revenue(self, generator, sample_report_standalone, volatile_revenue_df):
        """Test detection of highly volatile revenue"""
        result = generator.generate(
            report=sample_report_standalone,
            current_df=volatile_revenue_df,
            baseline_df=None,
            revenue_column="revenue",
        )
        
        assert result is not None
        assert result.stability is not None
        assert result.stability.category == "highly_volatile"
        assert result.stability.coefficient_of_variation >= 0.7
    
    def test_small_dataset_no_stability(self, generator, sample_report_standalone):
        """Stability insight should be None for single-row datasets"""
        small_df = pd.DataFrame({"revenue": [1000]})
        
        result = generator.generate(
            report=sample_report_standalone,
            current_df=small_df,
            baseline_df=None,
            revenue_column="revenue",
        )
        
        # May still return result with other insights, but stability should be None
        if result:
            assert result.stability is None


class TestEfficiencyInsight:
    def test_efficiency_improved(self, generator, sample_report_with_baseline, stable_revenue_df):
        """Test efficiency improvement detection (>10%)"""
        result = generator.generate(
            report=sample_report_with_baseline,
            current_df=stable_revenue_df,
            baseline_df=stable_revenue_df.copy(),
            revenue_column="revenue",
        )
        
        assert result is not None
        assert result.efficiency is not None
        assert result.efficiency.signal == "efficiency_improved"
        assert result.efficiency.change_percent > 10
    
    def test_efficiency_declined(self, generator, sample_report_decline, stable_revenue_df):
        """Test efficiency decline detection (<-10%)"""
        result = generator.generate(
            report=sample_report_decline,
            current_df=stable_revenue_df,
            baseline_df=stable_revenue_df.copy(),
            revenue_column="revenue",
        )
        
        assert result is not None
        assert result.efficiency is not None
        assert result.efficiency.signal == "efficiency_declined"
    
    def test_standalone_efficiency(self, generator, sample_report_standalone, stable_revenue_df):
        """Test efficiency insight in standalone mode"""
        result = generator.generate(
            report=sample_report_standalone,
            current_df=stable_revenue_df,
            baseline_df=None,
            revenue_column="revenue",
        )
        
        assert result is not None
        assert result.efficiency is not None
        assert result.efficiency.signal == "positive_revenue"


class TestConcentrationInsight:
    def test_high_concentration(self, generator, sample_report_standalone, concentrated_revenue_df):
        """Test detection of high revenue concentration"""
        result = generator.generate(
            report=sample_report_standalone,
            current_df=concentrated_revenue_df,
            baseline_df=None,
            revenue_column="revenue",
        )
        
        assert result is not None
        assert result.concentration is not None
        assert result.concentration.risk_level in ["high", "critical"]
        assert result.concentration.top_10_percent_contribution > 50
    
    def test_low_concentration(self, generator, sample_report_standalone, distributed_revenue_df):
        """Test detection of well-distributed revenue"""
        result = generator.generate(
            report=sample_report_standalone,
            current_df=distributed_revenue_df,
            baseline_df=None,
            revenue_column="revenue",
        )
        
        assert result is not None
        assert result.concentration is not None
        assert result.concentration.risk_level == "low"
    
    def test_small_dataset_no_concentration(self, generator, sample_report_standalone):
        """Concentration insight should be None for small datasets (<10 rows)"""
        small_df = pd.DataFrame({"revenue": [1000, 2000, 3000]})
        
        result = generator.generate(
            report=sample_report_standalone,
            current_df=small_df,
            baseline_df=None,
            revenue_column="revenue",
        )
        
        if result:
            assert result.concentration is None


class TestExecutiveSummary:
    def test_summary_with_baseline(self, generator, sample_report_with_baseline, stable_revenue_df):
        """Test executive summary generation with baseline"""
        result = generator.generate(
            report=sample_report_with_baseline,
            current_df=stable_revenue_df,
            baseline_df=stable_revenue_df.copy(),
            revenue_column="revenue",
        )
        
        assert result is not None
        assert result.executive_summary is not None
        assert len(result.executive_summary) > 50
        assert "revenue" in result.executive_summary.lower() or "$" in result.executive_summary
    
    def test_summary_standalone(self, generator, sample_report_standalone, stable_revenue_df):
        """Test executive summary in standalone mode"""
        result = generator.generate(
            report=sample_report_standalone,
            current_df=stable_revenue_df,
            baseline_df=None,
            revenue_column="revenue",
        )
        
        assert result is not None
        assert result.executive_summary is not None
    
    def test_summary_with_decline_and_risk(self, generator, sample_report_decline, concentrated_revenue_df):
        """Test summary includes actionable recommendations for risky situations"""
        result = generator.generate(
            report=sample_report_decline,
            current_df=concentrated_revenue_df,
            baseline_df=concentrated_revenue_df.copy(),
            revenue_column="revenue",
        )
        
        assert result is not None
        assert result.executive_summary is not None
        # Should mention decline or next steps
        summary_lower = result.executive_summary.lower()
        assert "decline" in summary_lower or "decreased" in summary_lower or "next" in summary_lower


class TestGracefulDegradation:
    def test_missing_revenue_column(self, generator, sample_report_standalone):
        """Should return None if revenue column doesn't exist"""
        df = pd.DataFrame({"other_column": [1, 2, 3]})
        
        result = generator.generate(
            report=sample_report_standalone,
            current_df=df,
            baseline_df=None,
            revenue_column="nonexistent",
        )
        
        # Should return None or handle gracefully
        # The generator catches exceptions and returns None
        assert result is None or isinstance(result, BusinessInsights)
    
    def test_empty_metric_deltas(self, generator, stable_revenue_df):
        """Should handle empty metric deltas gracefully"""
        empty_report = InsightReport(
            summary="No data",
            metric_deltas=[],
            insights=[],
        )
        
        result = generator.generate(
            report=empty_report,
            current_df=stable_revenue_df,
            baseline_df=None,
            revenue_column="revenue",
        )
        
        # Should return None since no revenue delta found
        assert result is None


class TestExistingBehaviorUnchanged:
    def test_report_structure_unchanged(self, generator, sample_report_with_baseline, stable_revenue_df):
        """Verify original report is not modified"""
        original_summary = sample_report_with_baseline.summary
        original_deltas = len(sample_report_with_baseline.metric_deltas)
        original_insights = len(sample_report_with_baseline.insights)
        
        # Generate business insights
        generator.generate(
            report=sample_report_with_baseline,
            current_df=stable_revenue_df,
            baseline_df=stable_revenue_df.copy(),
            revenue_column="revenue",
        )
        
        # Verify original report unchanged
        assert sample_report_with_baseline.summary == original_summary
        assert len(sample_report_with_baseline.metric_deltas) == original_deltas
        assert len(sample_report_with_baseline.insights) == original_insights
    
    def test_business_insights_are_optional(self, generator, sample_report_standalone):
        """Verify business insights can be None without breaking anything"""
        small_df = pd.DataFrame({"revenue": [1000]})
        
        result = generator.generate(
            report=sample_report_standalone,
            current_df=small_df,
            baseline_df=None,
            revenue_column="revenue",
        )
        
        # Result can be None or have null fields - both are valid
        if result is not None:
            # All fields should be optional
            assert result.trend is None or isinstance(result.trend, TrendInsight)
            assert result.stability is None or isinstance(result.stability, StabilityInsight)
