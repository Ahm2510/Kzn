# utils/dataset_store.py
"""
Dataset metadata and file storage management.

Thread-safe SQLite-based store for dataset metadata and file operations.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from app.config import settings

# Thread-local storage for database connections
_thread_local = threading.local()


class DatasetStore:
    """Thread-safe SQLite store for dataset metadata and file operations."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """
        Args:
            db_path: Path to the SQLite database file. If None, use default.
        """
        if db_path is None:
            db_path = settings.BASE_DATA_PATH / "datasets.sqlite3"
        # Ensure parent directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a thread-local database connection."""
        if not hasattr(_thread_local, "connection"):
            _thread_local.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=30.0,
            )
            _thread_local.connection.row_factory = sqlite3.Row
        return _thread_local.connection

    def _init_db(self) -> None:
        """Initialize the database with required tables if they don't exist."""
        conn = self._get_connection()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS datasets (
                dataset_id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                dataset_hash TEXT,
                row_count INTEGER,
                column_count INTEGER,
                status TEXT NOT NULL CHECK(
                    status IN ('uploaded', 'processing', 'cleaned', 'failed', 'transformed')
                ),
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_datasets_workspace ON datasets(workspace_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_datasets_user ON datasets(user_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_datasets_status ON datasets(status)"
        )
        conn.execute(
            """
            CREATE TRIGGER IF NOT EXISTS update_dataset_timestamp
            AFTER UPDATE ON datasets
            FOR EACH ROW
            BEGIN
                UPDATE datasets
                SET updated_at = CURRENT_TIMESTAMP
                WHERE dataset_id = OLD.dataset_id;
            END;
            """
        )
        conn.commit()

    def create_dataset(
        self,
        dataset_id: str,
        workspace_id: str,
        user_id: str,
        filename: str,
        file_path: Path,
        file_size: Optional[int] = None,
        dataset_hash: Optional[str] = None,
        row_count: Optional[int] = None,
        column_count: Optional[int] = None,
        status: str = "uploaded",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Create a new dataset entry in the store."""
        # Ensure tables exist (lazy initialization)
        self._init_db()
        metadata_str = json.dumps(metadata) if metadata is not None else None

        conn = self._get_connection()
        conn.execute(
            """
            INSERT INTO datasets (
                dataset_id, workspace_id, user_id, filename, file_path,
                file_size, dataset_hash, row_count, column_count,
                status, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dataset_id,
                workspace_id,
                user_id,
                filename,
                str(file_path),
                file_size,
                dataset_hash,
                row_count,
                column_count,
                status,
                metadata_str,
            ),
        )
        conn.commit()

    def update_dataset(
        self,
        dataset_id: str,
        status: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        row_count: Optional[int] = None,
        column_count: Optional[int] = None,
        dataset_hash: Optional[str] = None,
    ) -> bool:
        """Update an existing dataset's metadata."""
        updates: List[str] = []
        params: List[Any] = []

        if status is not None:
            updates.append("status = ?")
            params.append(status)

        if metadata is not None:
            existing = self.get_dataset(dataset_id)
            current_metadata: Dict[str, Any] = {}
            if existing and existing.get("metadata"):
                # existing["metadata"] is already a dict via _row_to_dict
                current_metadata.update(existing["metadata"])
            current_metadata.update(metadata)
            updates.append("metadata = ?")
            params.append(json.dumps(current_metadata))

        if row_count is not None:
            updates.append("row_count = ?")
            params.append(row_count)

        if column_count is not None:
            updates.append("column_count = ?")
            params.append(column_count)

        if dataset_hash is not None:
            updates.append("dataset_hash = ?")
            params.append(dataset_hash)

        if not updates:
            return False

        query = f"UPDATE datasets SET {', '.join(updates)} WHERE dataset_id = ?"
        params.append(dataset_id)

        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.rowcount > 0

    def get_dataset(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a dataset's metadata by ID."""
        # Ensure tables exist (lazy initialization)
        self._init_db()
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM datasets WHERE dataset_id = ?", (dataset_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)

    def list_datasets(
        self,
        workspace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List datasets with optional filtering."""
        query = "SELECT * FROM datasets WHERE 1=1"
        params: List[Any] = []

        if workspace_id is not None:
            query += " AND workspace_id = ?"
            params.append(workspace_id)

        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)

        if status is not None:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def delete_dataset(self, dataset_id: str) -> bool:
        """Delete a dataset from the store."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM datasets WHERE dataset_id = ?", (dataset_id,)
            )
            return cursor.rowcount > 0

    def dataset_exists(self, dataset_id: str) -> bool:
        """Check if a dataset exists in the store."""
        return self.get_dataset(dataset_id) is not None

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a database row to a dictionary."""
        result: Dict[str, Any] = dict(row)

        # Parse JSON fields
        if "metadata" in result and result["metadata"] is not None:
            try:
                result["metadata"] = json.loads(result["metadata"])
            except (json.JSONDecodeError, TypeError):
                result["metadata"] = {}

        # Convert file_path string to Path
        if "file_path" in result and result["file_path"] is not None:
            result["file_path"] = Path(result["file_path"])

        return result


# ---- Convenience API & singleton wiring ----

_DATASET_STORE: Optional[DatasetStore] = None


def init_dataset_store(db_path: Optional[Path] = None) -> DatasetStore:
    """
    Explicit initializer for application startup/tests.
    Creates the SQLite file if it does not exist.
    """
    global _DATASET_STORE
    _DATASET_STORE = DatasetStore(db_path=db_path)
    return _DATASET_STORE


def get_dataset_store() -> DatasetStore:
    """
    Lazy accessor. Creates DatasetStore with default path on first use
    if init_dataset_store() was not called.
    """
    global _DATASET_STORE
    if _DATASET_STORE is None:
        _DATASET_STORE = DatasetStore()
    return _DATASET_STORE


def get_dataset_path(dataset_id: str) -> Optional[Path]:
    """
    Get the file path for a dataset by ID.
    """
    store = get_dataset_store()
    dataset = store.get_dataset(dataset_id)
    if dataset and "file_path" in dataset and dataset["file_path"]:
        return Path(dataset["file_path"])
    return None


def save_dataset_file(
    df: pd.DataFrame,
    workspace_id: str,
    filename: str,
    user_id: str = "system",
    metadata: Optional[Dict[str, Any]] = None,
    status: str = "cleaned",
) -> Tuple[str, Path]:
    """
    Save a DataFrame to disk and register it in the dataset store.
    Returns (dataset_id, file_path).
    """
    datasets_root = settings.DATASETS_PATH or (settings.BASE_DATA_PATH / "datasets")
    datasets_root.mkdir(parents=True, exist_ok=True)

    dataset_id = str(uuid.uuid4())
    file_path = datasets_root / f"{dataset_id}.parquet"

    df.to_parquet(file_path, index=False)

    file_size = file_path.stat().st_size
    row_count = len(df)
    column_count = len(df.columns)

    dataset_metadata: Dict[str, Any] = {
        "original_filename": filename,
        "columns": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        **(metadata or {}),
    }

    store = get_dataset_store()
    store.create_dataset(
        dataset_id=dataset_id,
        workspace_id=workspace_id,
        user_id=user_id,
        filename=filename,
        file_path=file_path,
        file_size=file_size,
        row_count=row_count,
        column_count=column_count,
        status=status,
        metadata=dataset_metadata,
    )

    return dataset_id, file_path


def load_dataset_file(dataset_id: str) -> pd.DataFrame:
    """
    Load a dataset from disk by ID.
    """
    file_path = get_dataset_path(dataset_id)
    if not file_path:
        raise ValueError(f"Dataset {dataset_id} not found")

    if not file_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {file_path}")

    return pd.read_parquet(file_path)
