import pandas as pd
from typing import List, Optional

from schemas.insight.report import InsightReport
from schemas.insight.insights import Insight
from schemas.insight.metrics import MetricDelta
from services.insight_engine.comparator import compute_metric_delta
from services.insight_engine.rules import revenue_drop_rule
from services.insight_engine.narrative import generate_summary
from services.insight_engine.column_detector import detect_revenue_column


class InsightEngine:
    def run(
        self,
        current_df: pd.DataFrame,
        baseline_df: Optional[pd.DataFrame] = None,
    ) -> InsightReport:

        metric_deltas: List[MetricDelta] = []
        insights: List[Insight] = []

        # V1.75: Detect revenue columns using semantic matching
        current_col, _current_conf, _current_mode = detect_revenue_column(current_df)
        
        # Validate current dataset has revenue-like column
        if current_col is None:
            raise ValueError(
                "No revenue-like column detected in the current dataset. "
                "Please ensure your data contains a column such as 'revenue', 'sales', 'turnover', or similar. "
                f"Columns found: {list(current_df.columns)}"
            )
        
        # Handle baseline dataset
        baseline_col = None
        if baseline_df is not None and not baseline_df.empty:
            baseline_col, _baseline_conf, _baseline_mode = detect_revenue_column(baseline_df)
            
            # Validate baseline dataset has revenue-like column
            if baseline_col is None:
                raise ValueError(
                    "No revenue-like column detected in the baseline dataset. "
                    "Please ensure your baseline data contains a column such as 'revenue', 'sales', 'turnover', or similar. "
                    f"Columns found: {list(baseline_df.columns)}"
                )

        # Compute metric delta with detected columns
        revenue_delta = compute_metric_delta(
            name="revenue",
            current_df=current_df,
            baseline_df=baseline_df,
            column=current_col,
            baseline_column=baseline_col,
        )
        metric_deltas.append(revenue_delta)

        # Generate insights based on mode
        if baseline_df is None or (isinstance(baseline_df, pd.DataFrame) and baseline_df.empty):
            # Standalone mode: generate standalone insights
            standalone_insight = self._generate_standalone_insight(revenue_delta)
            if standalone_insight:
                insights.append(standalone_insight)
        else:
            # Comparative mode: generate comparative insights
            insight = revenue_drop_rule(revenue_delta)
            if insight:
                insights.append(insight)

        summary = generate_summary(metric_deltas, insights)

        return InsightReport(
            summary=summary,
            metric_deltas=metric_deltas,
            insights=insights,
        )

    def _generate_standalone_insight(self, metric_delta: MetricDelta) -> Optional[Insight]:
        """
        Generate standalone insight when no baseline is provided.
        """
        if metric_delta.name == "revenue":
            return Insight(
                code="REVENUE_SUMMARY",
                severity="low",
                title="Revenue summary",
                description=f"Total revenue is ${metric_delta.current:,.2f}",
                affected_metric="revenue",
            )
        return None
