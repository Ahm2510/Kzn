"""Typed response contract for the public /analyze endpoint.

The report and business_insights payloads are deep, evolving nested structures;
they are declared as ``Dict[str, Any]`` so the rich shape is never silently
dropped by response validation, while the envelope itself (which fields exist,
which are optional) is a real, documented contract the frontend types against.
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AnalyzeResponse(BaseModel):
    report: Dict[str, Any]
    pdf_path: Optional[str] = None
    pdf_base64: Optional[str] = None
    business_insights: Optional[Dict[str, Any]] = None
    distribution_schema: Optional[Dict[str, Any]] = None
    schema_warnings: Optional[List[str]] = None
    cached: bool = False
