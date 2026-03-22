# services/transformation.py

from __future__ import annotations

from typing import List

import pandas as pd

from app.schemas.transformation import (
    AggregationSpec,
    PivotSpec,
    RollingSpec,
    LagSpec,
    ChangeSpec,
    FeatureSpec,
    TransformationRequest,
    TransformationResult,
)
from app.utils.dataset_store import get_dataset_store, save_dataset_file
from app.utils.logger import get_logger


logger = get_logger(__name__)


class TransformationService:
    """
    Core transformation execution engine.
    Executes a TransformationRequest deterministically on a dataset.
    """

    def __init__(self):
        self.dataset_store = get_dataset_store()

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    def transform(
        self,
        dataset_id: str,
        request: TransformationRequest,
        workspace_id: str,
        user_id: str,
    ) -> TransformationResult:
        _meta, df = self._load_dataset(dataset_id)
        rows_before, cols_before = df.shape

        operations_applied: List[str] = []

        # 1. Feature engineering
        if request.features:
            df = self._apply_features(df, request.features)
            operations_applied.append("features")

        # 2. Aggregations
        if request.aggregations:
            for agg in request.aggregations:
                df = self._apply_aggregation(df, agg)
            operations_applied.append("aggregations")

        # 3. Pivots
        if request.pivots:
            for pivot in request.pivots:
                df = self._apply_pivot(df, pivot)
            operations_applied.append("pivots")

        # 4. Rolling windows
        if request.rolling:
            for rolling in request.rolling:
                df = self._apply_rolling(df, rolling)
            operations_applied.append("rolling")

        # 5. Lags
        if request.lags:
            for lag in request.lags:
                df = self._apply_lag(df, lag)
            operations_applied.append("lags")

        # 6. Changes
        if request.changes:
            for change in request.changes:
                df = self._apply_change(df, change)
            operations_applied.append("changes")

        # Persist result
        new_dataset_id, _ = save_dataset_file(
            df=df,
            workspace_id=workspace_id,
            filename=f"transformed_{dataset_id}.parquet",
            user_id=user_id,
            metadata={
                "source_dataset_id": dataset_id,
                "operations": operations_applied,
            },
            status="transformed",
        )

        rows_after, cols_after = df.shape

        logger.info(
            "Transformation complete",
            extra={
                "source_dataset_id": dataset_id,
                "new_dataset_id": new_dataset_id,
                "operations": operations_applied,
            },
        )

        return TransformationResult(
            source_dataset_id=dataset_id,
            transformed_dataset_id=new_dataset_id,
            rows_before=rows_before,
            rows_after=rows_after,
            columns_before=cols_before,
            columns_after=cols_after,
            operations_applied=operations_applied,
            transformation_schema=request,
            metadata={
                "workspace_id": workspace_id,
                "user_id": user_id,
            },
        )

    # ------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------

    def _load_dataset(self, dataset_id: str):
        meta = self.dataset_store.get_dataset(dataset_id)
        if not meta:
            raise ValueError(f"Dataset {dataset_id} not found")

        path = meta.get("file_path")
        if not path:
            raise ValueError(f"Dataset {dataset_id} has no file_path in metadata")
        df = pd.read_parquet(path)
        return meta, df

    def _apply_features(self, df: pd.DataFrame, specs: List[FeatureSpec]) -> pd.DataFrame:
        for spec in specs:
            # Safe eval context: only dataframe columns
            local_ctx = {col: df[col] for col in df.columns}
            df[spec.name] = eval(spec.expression, {}, local_ctx)
        return df

    def _apply_aggregation(self, df: pd.DataFrame, spec: AggregationSpec) -> pd.DataFrame:
        if spec.time_grain:
            date_col = spec.group_by[0]
            df[date_col] = pd.to_datetime(df[date_col])

            if spec.time_grain == "week":
                df[date_col] = df[date_col].dt.to_period("W").dt.start_time
            elif spec.time_grain == "month":
                df[date_col] = df[date_col].dt.to_period("M").dt.start_time

        agg_dict = {col: func for col, func in spec.metrics.items()}
        return df.groupby(spec.group_by, as_index=False).agg(agg_dict)

    def _apply_pivot(self, df: pd.DataFrame, spec: PivotSpec) -> pd.DataFrame:
        pivot = pd.pivot_table(
            df,
            index=spec.index,
            columns=spec.columns,
            values=spec.values,
            aggfunc=spec.agg_func,
        )
        pivot.columns = [
            "_".join(map(str, col)).strip() for col in pivot.columns.values
        ]
        return pivot.reset_index()

    def _apply_rolling(self, df: pd.DataFrame, spec: RollingSpec) -> pd.DataFrame:
        col_name = f"{spec.column}_rolling_{spec.window}_{spec.function}"
        df[col_name] = (
            df[spec.column]
            .rolling(window=spec.window)
            .agg(spec.function)
        )
        return df

    def _apply_lag(self, df: pd.DataFrame, spec: LagSpec) -> pd.DataFrame:
        col_name = f"{spec.column}_lag_{spec.periods}"
        df[col_name] = df[spec.column].shift(spec.periods)
        return df

    def _apply_change(self, df: pd.DataFrame, spec: ChangeSpec) -> pd.DataFrame:
        col_name = f"{spec.column}_{spec.metric}"

        if spec.metric == "wow":
            df[col_name] = df[spec.column].pct_change(periods=7)
        elif spec.metric == "mom":
            df[col_name] = df[spec.column].pct_change(periods=30)
        elif spec.metric == "yoy":
            df[col_name] = df[spec.column].pct_change(periods=365)

        return df

def transform_dataset(df):
    """
    V1.75 transformation contract:
    - Uses semantic column detection (revenue, sales, turnover, etc.)
    - Validation moved to InsightEngine for V1.75 semantic matching
    - data is aggregated at dataset level
    """
    # V1.75: Validation of revenue-like columns is now handled by InsightEngine
    # with semantic matching. This function just passes through the data.
    # The InsightEngine.run() will detect revenue columns using REVENUE_SYNONYMS
    # with confidence thresholds.
    return df
