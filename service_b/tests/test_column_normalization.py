# tests/test_column_normalization.py
#Tests for the column normalization (outlier clipping)

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from config import settings
from services.preprocessing import PreprocessingService
from utils.dataset_store import init_dataset_store
from utils.job_store import init_job_store
from utils.dataset_store import save_dataset_file, load_dataset_file
from schemas.preprocessing import CleaningConfig, OutlierHandling


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


def test_outlier_clipping_reduces_extreme_values():
    df = pd.DataFrame(
        {
            "quantity": [1, 2, 3, 10_000],  # extreme outlier
        }
    )
    dataset_id, _ = save_dataset_file(
        df=df,
        workspace_id="ws1",
        filename="outliers.csv",
        user_id="u1",
        metadata={},
        status="uploaded",
    )

    config = CleaningConfig(
        missing=None,
        duplicates=None,
        outliers=[
            OutlierHandling(
                columns=["quantity"],
                method="clip",
                zscore_threshold=2.0,
            )
        ],
    )

    service = PreprocessingService()
    result = service.apply_cleaning(dataset_id, config=config, workspace_id="ws1", user_id="u1")

    assert result.cleaned_dataset_id != dataset_id

    cleaned_df = load_dataset_file(result.cleaned_dataset_id)

    # Outlier should have been clipped down to a more reasonable range
    assert cleaned_df["quantity"].max() < 10_000
