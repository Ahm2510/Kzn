# utils/job_store.py
"""
Job status and result store.

Thread-safe SQLite-based store used to track background jobs
(Celery tasks, long-running operations, pipeline runs, etc.).
"""

import json
import sqlite3
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import settings


class JobStore:
    """Thread-safe SQLite store for job status and results."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        if db_path is None:
            db_path = settings.BASE_DATA_PATH / "jobs.sqlite"
        # Ensure parent directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "connection"):
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=30.0,
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    task_name TEXT,
                    task_id TEXT,
                    status TEXT,
                    progress INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    result TEXT,
                    error TEXT,
                    metadata TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)"
            )
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS update_job_timestamp
                AFTER UPDATE ON jobs
                FOR EACH ROW
                BEGIN
                    UPDATE jobs
                    SET updated_at = CURRENT_TIMESTAMP
                    WHERE job_id = OLD.job_id;
                END;
                """
            )

    def create_job(
        self,
        task_name: str,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a new job entry and return the job ID."""
        job_id = str(uuid.uuid4())
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO jobs (job_id, task_name, task_id, status, metadata)
                VALUES (?, ?, ?, 'PENDING', ?)
                """,
                (job_id, task_name, task_id, json.dumps(metadata or {})),
            )
        return job_id

    def update_job(
        self,
        job_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> bool:
        """Update job status, progress, and result."""
        updates: List[str] = []
        params: List[Any] = []

        if status is not None:
            updates.append("status = ?")
            params.append(status)

        if progress is not None:
            updates.append("progress = ?")
            params.append(progress)

        if result is not None:
            updates.append("result = ?")
            params.append(json.dumps(result))

        if error is not None:
            updates.append("error = ?")
            params.append(error)

        if task_id is not None:
            updates.append("task_id = ?")
            params.append(task_id)

        if not updates:
            return False

        query = f"UPDATE jobs SET {', '.join(updates)} WHERE job_id = ?"
        params.append(job_id)

        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.rowcount > 0

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job details by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None

            job: Dict[str, Any] = dict(row)
            if job.get("result"):
                job["result"] = json.loads(job["result"])
            if job.get("metadata"):
                job["metadata"] = json.loads(job["metadata"])
            return job


# ---- Singleton wiring ----

_JOB_STORE: Optional[JobStore] = None


def init_job_store(db_path: Optional[Path] = None) -> JobStore:
    """
    Explicit initializer for application startup/tests.
    Creates the SQLite file if it does not exist.
    """
    global _JOB_STORE
    _JOB_STORE = JobStore(db_path=db_path)
    return _JOB_STORE


def get_job_store() -> JobStore:
    """
    Lazy accessor. Creates JobStore with default path on first use
    if init_job_store() was not called.
    """
    global _JOB_STORE
    if _JOB_STORE is None:
        _JOB_STORE = JobStore()
    return _JOB_STORE
