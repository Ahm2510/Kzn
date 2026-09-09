"""
S3 storage helper for Kaizen Lite (Streamlit Cloud).
Handles upload and download of files to/from AWS S3.
"""
import streamlit as st
import boto3
from botocore.exceptions import ClientError
from typing import Optional
from io import BytesIO


def get_s3_client():
    """Get an S3 client configured from Streamlit secrets."""
    return boto3.client(
        's3',
        aws_access_key_id=st.secrets.get("aws_access_key_id"),
        aws_secret_access_key=st.secrets.get("aws_secret_access_key"),
        region_name=st.secrets.get("aws_region", "us-east-1")
    )


def get_bucket_name():
    """Get the S3 bucket name from secrets."""
    bucket = st.secrets.get("s3_bucket_name")
    if not bucket:
        raise ValueError("S3_BUCKET_NAME not set in Streamlit secrets")
    return bucket


def upload_file(file_bytes: bytes, key: str, content_type: str = "application/octet-stream") -> str:
    """
    Upload a file to S3 and return the S3 key.
    
    Args:
        file_bytes: The file content as bytes
        key: The S3 key (path within the bucket)
        content_type: MIME type of the file
    
    Returns:
        The S3 key (same as input key)
    """
    s3 = get_s3_client()
    bucket = get_bucket_name()
    
    try:
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=file_bytes,
            ContentType=content_type
        )
        return key
    except ClientError as e:
        raise Exception(f"Failed to upload to S3: {str(e)}")


def download_file(key: str) -> bytes:
    """
    Download a file from S3 and return its bytes.
    
    Args:
        key: The S3 key
    
    Returns:
        The file content as bytes
    """
    s3 = get_s3_client()
    bucket = get_bucket_name()
    
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        return response['Body'].read()
    except ClientError as e:
        raise Exception(f"Failed to download from S3: {str(e)}")


def file_exists(key: str) -> bool:
    """Check if a file exists in S3."""
    s3 = get_s3_client()
    bucket = get_bucket_name()
    
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError:
        return False


def delete_file(key: str):
    """Delete a file from S3."""
    s3 = get_s3_client()
    bucket = get_bucket_name()
    
    try:
        s3.delete_object(Bucket=bucket, Key=key)
    except ClientError as e:
        raise Exception(f"Failed to delete from S3: {str(e)}")


def generate_pdf_key(firm_id: int, client_id: int, filename: str) -> str:
    """Generate an S3 key for a PDF report."""
    return f"kaizen_lite/{firm_id}/{client_id}/reports/{filename}"


def generate_upload_key(firm_id: int, client_id: int, filename: str) -> str:
    """Generate an S3 key for an uploaded file."""
    return f"kaizen_lite/{firm_id}/{client_id}/uploads/{filename}"
