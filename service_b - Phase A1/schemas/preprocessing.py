#schemas/preprocessing.py

from __future__ import annotations

from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field


# ---------- Core dataset references ----------


class DatasetSummary(BaseModel):
    dataset_id: str = Field(..., description="Unique identifier of the dataset in the store")
    workspace_id: str = Field(..., description="Workspace / client identifier")
    user_id: str = Field(..., description="User who created the dataset")
    row_count: int = Field(..., ge=0)
    column_count: int = Field(..., ge=0)
    columns: List[str] = Field(default_factory=list)


# ---------- Cleanliness reporting ----------


IssueType = Literal[
    "missing_values",
    "invalid_type",
    "outlier",
    "duplicate_row",
]


class CleanlinessIssue(BaseModel):
    column: Optional[str] = Field(
        default=None,
        description="Column where the issue was detected; None for dataset-level issues",
    )
    issue_type: IssueType
    count: int = Field(..., ge=0)
    example_values: Optional[List[Any]] = Field(
        default=None,
        description="Example values that triggered the issue, if available",
    )
    recommended_action: Optional[str] = Field(
        default=None,
        description="Human-readable suggestion, not executable code",
    )


class CleanlinessReport(BaseModel):
    dataset_id: str
    workspace_id: str
    total_rows: int = Field(..., ge=0)
    total_columns: int = Field(..., ge=0)
    missing_values_total: int = Field(..., ge=0)
    duplicate_rows: int = Field(..., ge=0)
    outlier_cells: int = Field(..., ge=0)
    issues: List[CleanlinessIssue] = Field(default_factory=list)


# ---------- Cleaning config ----------


MissingMethod = Literal[
    "drop_rows",
    "fill_mean",
    "fill_median",
    "fill_mode",
    "fill_constant",
]


class MissingValueStrategy(BaseModel):
    columns: List[str] = Field(
        ...,
        description="Columns to which this missing-value strategy applies",
    )
    method: MissingMethod
    constant: Optional[float | str] = Field(
        default=None,
        description="Constant value to use when method == 'fill_constant'",
    )


DuplicateMethod = Literal[
    "drop_all",
    "drop_keep_first",
    "ignore",
]


class DuplicateHandling(BaseModel):
    method: DuplicateMethod = Field(
        default="drop_keep_first",
        description="How to handle duplicate rows",
    )


OutlierMethod = Literal[
    "clip",
    "remove_rows",
    "ignore",
]


class OutlierHandling(BaseModel):
    columns: List[str] = Field(
        ...,
        description="Numeric columns to which this outlier strategy applies",
    )
    method: OutlierMethod
    zscore_threshold: float = Field(
        default=3.0,
        gt=0,
        description="Z-score threshold used to detect outliers",
    )


class CleaningConfig(BaseModel):
    """
    Configuration representing how the user wants to clean the dataset.

    All fields are optional; any omitted part is left unchanged.
    """

    missing: Optional[List[MissingValueStrategy]] = None
    duplicates: Optional[DuplicateHandling] = None
    outliers: Optional[List[OutlierHandling]] = None


class CleaningResult(BaseModel):
    source_dataset_id: str
    cleaned_dataset_id: str
    workspace_id: str
    rows_before: int
    rows_after: int
    columns_before: int
    columns_after: int

    applied_strategies: CleaningConfig
    cleanliness_report: CleanlinessReport


# ---------- Delete rows/columns ----------


class DeleteRequest(BaseModel):
    """
    Delete operation on a dataset.

    Either or both of:
    - drop_columns: list of column names to remove
    - drop_rows_where_null_in: list of columns where null -> row removal
    """

    drop_columns: Optional[List[str]] = None
    drop_rows_where_null_in: Optional[List[str]] = None


class DeleteResult(BaseModel):
    source_dataset_id: str
    updated_dataset_id: str
    workspace_id: str
    rows_before: int
    rows_after: int
    columns_before: int
    columns_after: int


# ---------- Find & replace ----------


MatchMode = Literal["exact", "contains", "regex"]


class FindReplaceRequest(BaseModel):
    columns: Optional[List[str]] = Field(
        default=None,
        description="If None, apply to all columns; otherwise, only these columns",
    )
    target: str = Field(..., description="Target string or pattern to search for")
    replacement: str = Field(..., description="Replacement string")
    match_mode: MatchMode = Field(
        default="exact",
        description="How to match the target string",
    )


class FindReplaceResult(BaseModel):
    source_dataset_id: str
    updated_dataset_id: str
    workspace_id: str
    matches_found: int
    rows_affected: int
    columns_affected: List[str] = Field(default_factory=list)


# ---------- Upload / endpoint payloads ----------


class IngestResponse(BaseModel):
    """
    Response returned after an upload/ingest operation.
    """

    dataset: DatasetSummary
    message: str = Field(
        default="File ingested successfully",
        description="Human-readable status message",
    )


class CleanlinessReportResponse(BaseModel):
    dataset: DatasetSummary
    report: CleanlinessReport


class CleaningResponse(BaseModel):
    result: CleaningResult


class DeleteResponse(BaseModel):
    result: DeleteResult


class FindReplaceResponse(BaseModel):
    result: FindReplaceResult
