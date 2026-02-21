# tests/test_transformation.py

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from config import settings
from services.transformation import TransformationService
from schemas.transformation import (
    AggregationSpec,
    RollingSpec,
    LagSpec,
    ChangeSpec,
    FeatureSpec,
    TransformationRequest,
)
from utils.dataset_store import init_dataset_store, save_dataset_file
from utils.job_store import init_job_store


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    base: Path = tmp_path
    monkeypatch.setattr(settings, "BASE_DATA_PATH", base)
    monkeypatch.setattr(settings, "DATASETS_PATH", base / "datasets")
    monkeypatch.setattr(settings, "ENCODERS_PATH", base / "encoders")
    monkeypatch.setattr(settings, "TEMP_DIR", base / "temp")
    settings.ensure_dirs()

    init_dataset_store(db_path=base / "datasets.sqlite3")
    init_job_store(db_path=base / "jobs.sqlite")

    yield


def _make_base_dataset():
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=10, freq="D"),
            "product": ["A"] * 10,
            "quantity": range(1, 11),
            "price": [10.0] * 10,
        }
    )


def test_feature_engineering_adds_column():
    df = _make_base_dataset()
    dataset_id, _ = save_dataset_file(
        df=df,
        workspace_id="ws1",
        filename="base.parquet",
        user_id="u1",
        metadata={},
        status="uploaded",
    )

    request = TransformationRequest(
        features=[
            FeatureSpec(
                name="revenue",
                expression="price * quantity",
            )
        ]
    )

    service = TransformationService()
    result = service.transform(dataset_id, request, "ws1", "u1")

    path = settings.DATASETS_PATH / f"{result.transformed_dataset_id}.parquet"
    out = pd.read_parquet(path)

    assert "revenue" in out.columns
    assert out["revenue"].iloc[0] == 10.0


def test_weekly_aggregation_reduces_rows():
    df = _make_base_dataset()
    dataset_id, _ = save_dataset_file(
        df=df,
        workspace_id="ws1",
        filename="base.parquet",
        user_id="u1",
        metadata={},
        status="uploaded",
    )

    request = TransformationRequest(
        aggregations=[
            AggregationSpec(
                group_by=["date"],
                metrics={"quantity": "sum"},
                time_grain="week",
            )
        ]
    )

    service = TransformationService()
    result = service.transform(dataset_id, request, "ws1", "u1")

    out = pd.read_parquet(
        settings.DATASETS_PATH / f"{result.transformed_dataset_id}.parquet"
    )

    assert result.rows_after < result.rows_before
    assert "quantity" in out.columns


def test_rolling_sum_creates_new_column():
    df = _make_base_dataset()
    dataset_id, _ = save_dataset_file(
        df=df,
        workspace_id="ws1",
        filename="base.parquet",
        user_id="u1",
        metadata={},
        status="uploaded",
    )

    request = TransformationRequest(
        rolling=[
            RollingSpec(
                column="quantity",
                window=3,
                function="sum",
            )
        ]
    )

    service = TransformationService()
    result = service.transform(dataset_id, request, "ws1", "u1")

    out = pd.read_parquet(
        settings.DATASETS_PATH / f"{result.transformed_dataset_id}.parquet"
    )

    rolling_cols = [c for c in out.columns if "rolling" in c]
    assert len(rolling_cols) == 1
    assert out[rolling_cols[0]].iloc[2] == 6  # 1+2+3


def test_lag_creates_shifted_column():
    df = _make_base_dataset()
    dataset_id, _ = save_dataset_file(
        df=df,
        workspace_id="ws1",
        filename="base.parquet",
        user_id="u1",
        metadata={},
        status="uploaded",
    )

    request = TransformationRequest(
        lags=[
            LagSpec(
                column="quantity",
                periods=1,
            )
        ]
    )

    service = TransformationService()
    result = service.transform(dataset_id, request, "ws1", "u1")

    out = pd.read_parquet(
        settings.DATASETS_PATH / f"{result.transformed_dataset_id}.parquet"
    )

    lag_cols = [c for c in out.columns if "lag" in c]
    assert len(lag_cols) == 1
    assert pd.isna(out[lag_cols[0]].iloc[0])
    assert out[lag_cols[0]].iloc[1] == 1


def test_change_metric_adds_growth_column():
    df = _make_base_dataset()
    dataset_id, _ = save_dataset_file(
        df=df,
        workspace_id="ws1",
        filename="base.parquet",
        user_id="u1",
        metadata={},
        status="uploaded",
    )

    request = TransformationRequest(
        changes=[
            ChangeSpec(
                column="quantity",
                metric="wow",
            )
        ]
    )

    service = TransformationService()
    result = service.transform(dataset_id, request, "ws1", "u1")

    out = pd.read_parquet(
        settings.DATASETS_PATH / f"{result.transformed_dataset_id}.parquet"
    )

    change_cols = [c for c in out.columns if "wow" in c]
    assert len(change_cols) == 1
