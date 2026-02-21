# utils/validators.py

from pathlib import Path

from config import settings


def validate_file_extension(path: Path) -> None:
    """
    Raise ValueError if the file extension is not supported.
    """
    suffix = path.suffix.lower()
    if suffix not in settings.SUPPORTED_FILE_EXTENSIONS:
        raise ValueError(f"Unsupported file extension: {suffix}")


def validate_row_limit(n_rows: int) -> None:
    """
    Ensure the dataset does not exceed MAX_ROWS.
    """
    if n_rows > settings.MAX_ROWS:
        raise ValueError(
            f"Too many rows: {n_rows} > MAX_ROWS={settings.MAX_ROWS}"
        )


def validate_workspace_id(workspace_id: str) -> None:
    """
    Optionally enforce allowed workspaces.
    """
    if settings.ALLOWED_WORKSPACES is not None:
        if workspace_id not in settings.ALLOWED_WORKSPACES:
            raise ValueError(f"Workspace {workspace_id!r} is not allowed.")
