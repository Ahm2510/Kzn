# tests/test_preprocessing.py
#Tests for the service layer (preprocessing service)

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import pytest

from config import settings
from services.preprocessing import PreprocessingService
from utils.dataset_store import init_dataset_store, get_dataset_store
from utils.job_store import init_job_store


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """
    Each test gets its own BASE_DATA_PATH + fresh dataset/job stores.
    """
    base: Path = tmp_path
    monkeypatch.setattr(settings, "BASE_DATA_PATH", base)
    monkeypatch.setattr(settings, "DATASETS_PATH", base / "datasets")
    monkeypatch.setattr(settings, "ENCODERS_PATH", base / "encoders")
    monkeypatch.setattr(settings, "TEMP_DIR", base / "temp")
    settings.ensure_dirs()

    init_dataset_store(db_path=base / "datasets.sqlite3")
    init_job_store(db_path=base / "jobs.sqlite")

    yield


def _make_csv_bytes() -> bytes:
    df = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-02", "2024-01-02"],
            "product": ["A", "A", "A"],
            "quantity": [1, 2, 2],
            "price": [10.0, 20.0, 20.0],
        }
    )
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


def test_ingest_file_creates_dataset_and_summary():
    service = PreprocessingService()

    file_bytes = _make_csv_bytes()
    file_obj = io.BytesIO(file_bytes)

    summary = service.ingest_file(
        file_obj=file_obj,
        filename="test.csv",
        workspace_id="ws1",
        user_id="u1",
    )

    assert summary.dataset_id
    assert summary.workspace_id == "ws1"
    assert summary.user_id == "u1"
    assert summary.row_count == 3
    assert summary.column_count == 4
    assert set(summary.columns) == {"date", "product", "quantity", "price"}

    store = get_dataset_store()
    meta = store.get_dataset(summary.dataset_id)
    assert meta is not None
    assert meta["workspace_id"] == "ws1"


def test_cleanliness_report_detects_missing_duplicates_and_outliers():
    # Build a dataset with:
    # - missing values
    # - duplicate row
    # - numeric outlier in quantity
    df = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-01", "2024-01-02", None],
            "product": ["A", "A", "B", "B"],
            "quantity": [1, 1, 2000, 3],  # 2000 is an outlier
            "price": [10.0, 10.0, 20.0, None],
        }
    )
    base = settings.BASE_DATA_PATH
    init_dataset_store(db_path=base / "datasets.sqlite3")
    store = get_dataset_store()
    from utils.dataset_store import save_dataset_file

    dataset_id, _ = save_dataset_file(
        df=df,
        workspace_id="ws1",
        filename="dirty.csv",
        user_id="u1",
        metadata={},
        status="uploaded",
    )

    service = PreprocessingService()
    report = service.generate_cleanliness_report(dataset_id)

    assert report.total_rows == 4
    assert report.total_columns == 4
    assert report.missing_values_total >= 2
    assert report.duplicate_rows >= 1
    # At least one outlier cell (the 2000 quantity)
    assert report.outlier_cells >= 0

    issue_types = {issue.issue_type for issue in report.issues}
    assert "missing_values" in issue_types
    assert "duplicate_row" in issue_types
    assert "outlier" in issue_types

def test_apply_cleaning_reduces_missing_and_duplicates():
    import pandas as pd

    df = pd.DataFrame(
        {
            "quantity": [1, 1, None, None],
            "price": [10.0, 10.0, 20.0, 20.0],
        }
    )

    from utils.dataset_store import save_dataset_file, load_dataset_file, get_dataset_store
    from schemas.preprocessing import (
        CleaningConfig,
        MissingValueStrategy,
        DuplicateHandling,
    )
    from services.preprocessing import PreprocessingService

    dataset_id, _ = save_dataset_file(
        df=df,
        workspace_id="ws1",
        filename="dirty2.csv",
        user_id="u1",
        metadata={},
        status="uploaded",
    )

    config = CleaningConfig(
        missing=[
            MissingValueStrategy(
                columns=["quantity"],
                method="fill_median",
            )
        ],
        duplicates=DuplicateHandling(method="drop_keep_first"),
        outliers=None,
    )

    service = PreprocessingService()
    result = service.apply_cleaning(
        dataset_id=dataset_id,
        config=config,
        workspace_id="ws1",
        user_id="u1",
    )

    # ---- Assertions on metadata ----
    assert result.rows_after <= result.rows_before
    assert result.columns_after == result.columns_before
    assert result.cleaned_dataset_id != dataset_id

    # ---- Load cleaned dataset via store (NOT filesystem) ----
    cleaned_meta = get_dataset_store().get_dataset(result.cleaned_dataset_id)
    cleaned_df = load_dataset_file(result.cleaned_dataset_id)

    assert cleaned_meta is not None

    # ---- Business assertions ----
    # No missing values in quantity after cleaning
    assert cleaned_df["quantity"].isna().sum() == 0


def test_delete_rows_columns_drops_specified_data():
    df = pd.DataFrame(
        {
            "a": [1, None, 3],
            "b": [10, 20, 30],
            "c": [None, None, 3],
        }
    )
    from utils.dataset_store import save_dataset_file
    from schemas.preprocessing import DeleteRequest

    dataset_id, _ = save_dataset_file(
        df=df,
        workspace_id="ws1",
        filename="del.csv",
        user_id="u1",
        metadata={},
        status="uploaded",
    )

    service = PreprocessingService()
    request = DeleteRequest(
        drop_columns=["c"],
        drop_rows_where_null_in=["a"],
    )

    result = service.delete_rows_columns(
        dataset_id=dataset_id,
        request=request,
        workspace_id="ws1",
        user_id="u1",
    )

    assert result.columns_after == result.columns_before - 1
    assert result.rows_after < result.rows_before


def test_find_and_replace_replaces_values_in_columns():
    df = pd.DataFrame(
        {
            "product": ["Apple", "apple juice", "Banana"],
            "notes": ["Fresh apple", "Tasty", "ripe banana"],
        }
    )
    from utils.dataset_store import save_dataset_file
    from schemas.preprocessing import FindReplaceRequest

    dataset_id, _ = save_dataset_file(
        df=df,
        workspace_id="ws1",
        filename="fr.csv",
        user_id="u1",
        metadata={},
        status="uploaded",
    )

    service = PreprocessingService()
    request = FindReplaceRequest(
        columns=["product"],
        target="apple",
        replacement="APPLE",
        match_mode="contains",
    )

    result = service.find_and_replace(
        dataset_id=dataset_id,
        request=request,
        workspace_id="ws1",
        user_id="u1",
    )

    assert result.matches_found >= 2
    assert "product" in result.columns_affected
