import logging
import pandas as pd
from typing import List, Optional

from app.schemas.insight.report import InsightReport
from app.schemas.insight.insights import Insight
from app.schemas.insight.metrics import MetricDelta
from app.services.insight_engine.comparator import compute_metric_delta
from app.services.insight_engine.rules import (
    revenue_drop_rule,
    revenue_increase_rule,
    revenue_moderate_change_rule,
    avg_revenue_per_row_rule,
    revenue_concentration_rule,
    revenue_volatility_rule,
    revenue_distribution_rule,
    top_product_rule,
    product_concentration_rule,
    underperforming_products_rule,
    product_baseline_comparison_rule,
)
from app.services.insight_engine.narrative import generate_summary
from app.services.insight_engine.column_detector import detect_revenue_column

logger = logging.getLogger(__name__)


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
            for rule in [revenue_drop_rule, revenue_increase_rule, revenue_moderate_change_rule]:
                insight = rule(revenue_delta)
                if insight:
                    insights.append(insight)

        # Data-driven insights (both modes) — safe, only use actual computed values
        for rule in [avg_revenue_per_row_rule, revenue_concentration_rule,
                      revenue_volatility_rule, revenue_distribution_rule]:
            try:
                insight = rule(current_df, current_col)
                if insight:
                    insights.append(insight)
            except Exception as e:
                logger.debug(f"Optional insight rule {rule.__name__} failed: {e}")

        # Product-level ecommerce insights (only if product column detected)
        for rule in [top_product_rule, product_concentration_rule,
                      underperforming_products_rule]:
            try:
                insight = rule(current_df, current_col)
                if insight:
                    insights.append(insight)
            except Exception as e:
                logger.debug(f"Optional product insight rule {rule.__name__} failed: {e}")

        # Product baseline comparison (returns a list)
        try:
            product_insights = product_baseline_comparison_rule(
                current_df, baseline_df, current_col, baseline_col,
            )
            insights.extend(product_insights)
        except Exception as e:
            logger.debug(f"Product baseline comparison failed: {e}")

        summary = generate_summary(metric_deltas, insights)

        # Count total transactions (non-null revenue rows in current dataset)
        try:
            total_transactions = int(
                pd.to_numeric(current_df[current_col], errors="coerce").notna().sum()
            )
        except Exception:
            total_transactions = len(current_df)

        # Count distinct products if product column exists
        products_analyzed = None
        try:
            product_candidates = [
                "product", "product_name", "item", "sku", "description",
                "product_id", "item_name", "product_category", "category",
            ]
            cols_lower = {col.lower().strip(): col for col in current_df.columns}
            product_col = next(
                (cols_lower[c] for c in product_candidates if c in cols_lower), None
            )
            if product_col:
                products_analyzed = int(current_df[product_col].nunique())
        except Exception:
            products_analyzed = None

        return InsightReport(
            summary=summary,
            metric_deltas=metric_deltas,
            insights=insights,
            total_transactions=total_transactions,
            products_analyzed=products_analyzed,
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
                driver=f"Aggregated revenue across all records totals ${metric_delta.current:,.2f}",
                implication="Establishes the current revenue baseline for performance tracking.",
                action_direction="Use as reference point for setting targets and measuring future performance.",
                confidence="HIGH",
                confidence_basis="Computed from complete dataset without sampling bias",
            )
        return None
