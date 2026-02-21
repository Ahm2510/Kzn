# schemas/transformation.py

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, model_validator


# -------------------------------------------------------------------
# Core enums / literals
# -------------------------------------------------------------------

AggregationFunction = Literal[
    "sum",
    "mean",
    "count",
    "min",
    "max",
]

TimeGrain = Literal[
    "day",
    "week",
    "month",
]

ChangeMetric = Literal[
    "wow",   # week-over-week
    "mom",   # month-over-month
    "yoy",   # year-over-year
]

LagUnit = Literal[
    "rows",
    "days",
    "weeks",
    "months",
]


# -------------------------------------------------------------------
# Aggregation
# -------------------------------------------------------------------

class AggregationSpec(BaseModel):
    group_by: List[str] = Field(
        ...,
        description="Columns to group by (e.g. date, product, region).",
        min_items=1,
    )
    metrics: Dict[str, AggregationFunction] = Field(
        ...,
        description="Mapping of column -> aggregation function.",
        min_items=1,
    )
    time_grain: Optional[TimeGrain] = Field(
        default=None,
        description="Optional time grain if grouping on a date column.",
    )


# -------------------------------------------------------------------
# Pivot table
# -------------------------------------------------------------------

class PivotSpec(BaseModel):
    index: List[str] = Field(
        ...,
        description="Row index columns for the pivot table.",
        min_items=1,
    )
    columns: List[str] = Field(
        ...,
        description="Column headers for the pivot table.",
        min_items=1,
    )
    values: str = Field(
        ...,
        description="Column to aggregate in the pivot table.",
    )
    agg_func: AggregationFunction = Field(
        ...,
        description="Aggregation function to apply.",
    )


# -------------------------------------------------------------------
# Time-series transformations
# -------------------------------------------------------------------

class RollingSpec(BaseModel):
    column: str = Field(..., description="Numeric column to apply rolling window on.")
    window: int = Field(..., gt=1, description="Rolling window size.")
    function: AggregationFunction = Field(
        ..., description="Aggregation function for the rolling window."
    )


class LagSpec(BaseModel):
    column: str = Field(..., description="Column to lag.")
    periods: int = Field(..., gt=0, description="Number of periods to lag.")
    unit: LagUnit = Field(
        default="rows",
        description="Lag unit: rows or time-based.",
    )


class ChangeSpec(BaseModel):
    column: str = Field(..., description="Column to compute change on.")
    metric: ChangeMetric = Field(
        ..., description="Type of change: WoW, MoM, YoY."
    )


# -------------------------------------------------------------------
# Feature engineering
# -------------------------------------------------------------------

class FeatureSpec(BaseModel):
    name: str = Field(..., description="Name of the derived feature.")
    expression: str = Field(
        ...,
        description=(
            "Expression defining the feature, e.g. "
            "'revenue = price * quantity'. "
            "Evaluated in a safe expression context."
        ),
    )


# -------------------------------------------------------------------
# Master transformation request
# -------------------------------------------------------------------

class TransformationRequest(BaseModel):
    """
    A single transformation request. Any subset of operations may be applied,
    but at least ONE must be provided.
    """

    aggregations: Optional[List[AggregationSpec]] = None
    pivots: Optional[List[PivotSpec]] = None
    rolling: Optional[List[RollingSpec]] = None
    lags: Optional[List[LagSpec]] = None
    changes: Optional[List[ChangeSpec]] = None
    features: Optional[List[FeatureSpec]] = None

    @model_validator(mode="after")
    def at_least_one_operation(self):
        if not any(
            [
                self.aggregations,
                self.pivots,
                self.rolling,
                self.lags,
                self.changes,
                self.features,
            ]
        ):
            raise ValueError("At least one transformation operation must be specified.")
        return self


# -------------------------------------------------------------------
# Result metadata
# -------------------------------------------------------------------

class TransformationResult(BaseModel):
    source_dataset_id: str = Field(
        ..., description="Dataset ID before transformation."
    )
    transformed_dataset_id: str = Field(
        ..., description="New dataset ID after transformation."
    )

    rows_before: int
    rows_after: int
    columns_before: int
    columns_after: int

    operations_applied: List[str] = Field(
        ...,
        description="Human-readable list of transformations applied.",
    )

    transformation_schema: TransformationRequest = Field(
        ..., description="Exact schema used to generate this dataset."
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata (timestamps, user, workspace, etc.).",
    )
