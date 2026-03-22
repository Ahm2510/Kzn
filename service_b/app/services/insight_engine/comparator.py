import pandas as pd
from typing import Optional
from app.schemas.insight.metrics import MetricDelta


def compute_metric_delta(
    name: str,
    current_df: pd.DataFrame,
    baseline_df: Optional[pd.DataFrame],
    column: str,
    baseline_column: Optional[str] = None,
) -> MetricDelta:
    """
    Compute metric delta between current and baseline datasets.
    
    If baseline_df is None, returns standalone metric with baseline=0.
    
    Args:
        name: Name of the metric
        current_df: Current period DataFrame
        baseline_df: Baseline period DataFrame (optional)
        column: Column name in current_df
        baseline_column: Column name in baseline_df (defaults to same as column)
    """
    # Use same column name for baseline if not specified
    if baseline_column is None:
        baseline_column = column
    
    current_value = current_df[column].sum()
    
    # Defensive check: handle None or empty baseline
    if baseline_df is None or (isinstance(baseline_df, pd.DataFrame) and baseline_df.empty):
        baseline_value = 0.0
        absolute = current_value
        percent = 0.0  # No comparison available
    else:
        baseline_value = baseline_df[baseline_column].sum()
        absolute = current_value - baseline_value
        percent = (
            (absolute / baseline_value) * 100 if baseline_value != 0 else 0.0
        )

    return MetricDelta(
        name=name,
        current=current_value,
        baseline=baseline_value,
        absolute_change=absolute,
        percent_change=percent,
    )
