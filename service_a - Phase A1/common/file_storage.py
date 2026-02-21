"""
Simple file storage utilities for uploaded CSV files.
"""
import os
import uuid
from pathlib import Path
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile


def get_upload_directory() -> Path:
    """Get the directory for storing uploaded files."""
    upload_dir = Path(settings.MEDIA_ROOT)
    upload_dir.mkdir(exist_ok=True)
    return upload_dir


def save_uploaded_file(uploaded_file: UploadedFile, project_id: int) -> str:
    """
    Save an uploaded CSV file to disk.
    
    Args:
        uploaded_file: Django UploadedFile object
        project_id: ID of the project this file belongs to
        
    Returns:
        Absolute path to the saved file
    """
    upload_dir = get_upload_directory() / str(project_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_ext = Path(uploaded_file.name).suffix or '.csv'
    filename = f"{uuid.uuid4()}{file_ext}"
    file_path = upload_dir / filename
    
    # Save file
    with open(file_path, 'wb') as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)
    
    return str(file_path.absolute())


def delete_file(file_path: str) -> None:
    """Delete a file from disk if it exists."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass  # Silently fail on deletion errors

