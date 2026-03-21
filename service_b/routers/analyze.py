from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, Request
import base64
import pandas as pd
import tempfile
import json
import os

from slowapi import Limiter
from slowapi.util import get_remote_address

from config.settings import settings
from utils.security import require_internal_auth
from services.insight_v1_5 import InsightV15Service
from schemas.insight.cleaning import CleaningOptions
from services.report_renderers.pdf_report import render_pdf
from services.business_insights.generator import BusinessInsightGenerator
from services.insight_engine.column_detector import detect_revenue_column
from services.preprocessing import preprocess_with_options
from services.schema_selector import select_metric_column

import logging

router = APIRouter()
service = InsightV15Service()
business_insight_generator = BusinessInsightGenerator()
logger = logging.getLogger(__name__)

# Rate limiter instance (uses app.state.limiter)
limiter = Limiter(key_func=get_remote_address, enabled=settings.RATE_LIMIT_ENABLED)

MAX_ANALYSIS_ROWS = 200000


def _read_csv_safe(file_obj) -> pd.DataFrame:
    """
    Read CSV with encoding fallback: UTF-8 → latin-1 → cp1252.
    Handles files with special characters (e.g. £, €, accented names).
    """
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            file_obj.seek(0)
            return pd.read_csv(file_obj, encoding=encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
    # Last resort: ignore bad bytes
    file_obj.seek(0)
    return pd.read_csv(file_obj, encoding="utf-8", encoding_errors="ignore")


def _validate_upload_file(file: UploadFile, file_label: str) -> None:
    """
    Validate uploaded file for security and size constraints.
    Raises HTTPException if validation fails.
    """
    # Sanitize filename to prevent path traversal
    if file.filename:
        safe_filename = os.path.basename(file.filename)
        if safe_filename != file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid {file_label} filename. Path traversal characters not allowed."
            )
    
    # Check file extension
    if file.filename:
        _, ext = os.path.splitext(file.filename.lower())
        if ext not in [".csv"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid {file_label} file type. Only CSV files are supported."
            )
    
    # Check content type (best effort - can be spoofed)
    if file.content_type and file.content_type not in ["text/csv", "application/csv", "application/octet-stream"]:
        # Allow octet-stream as browsers may use it for CSV
        pass  # Warning only, don't reject
    
    # Check file size
    try:
        file.file.seek(0, 2)  # Seek to end
        size_bytes = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
        if size_bytes > max_bytes:
            # 413 is the correct status for payload size violations.
            # This is intentionally used to differentiate from 400-level
            # CSV/content validation errors.
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"The {file_label} file exceeds the maximum allowed size of {settings.MAX_UPLOAD_MB}MB."
            )
    except HTTPException:
        raise
    except Exception:
        pass  # Size check failed, continue anyway


def _validate_dataframe(df: pd.DataFrame, file_label: str) -> None:
    """
    Validate DataFrame for row count and revenue column presence.
    Raises HTTPException if validation fails.
    """
    # Check row count
    if len(df) > settings.MAX_ROWS:
        # Instead of failing, we now sample down to MAX_ANALYSIS_ROWS
        pass
    
    # Check for at least one numeric column (revenue-like)
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    if not numeric_cols:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The {file_label} file must contain at least one numeric column for revenue analysis."
        )


def _apply_revenue_fallback(df: pd.DataFrame) -> pd.DataFrame:
    """
    SAFE Revenue Fallback:
    If no revenue-like column exists, compute Revenue = Quantity * UnitPrice
    if both columns are present.
    """
    # 1. Check if revenue-like column already exists (case-insensitive)
    revenue_synonyms = [
        "revenue", "sales", "amount", "total", "total_price", "order_value",
        "gmv", "turnover", "gross_revenue", "net_revenue", "total_revenue",
        "total_sales", "sales_revenue", "income", "total_income", "earnings",
        "total_amount", "total_value", "gmv_value", "booking_amount",
        "transaction_value",
    ]
    cols_lower = {col.lower().strip(): col for col in df.columns}
    
    if any(syn in cols_lower for syn in revenue_synonyms):
        return df

    # 2. Look for Quantity and UnitPrice candidates
    qty_candidates = ["quantity", "qty", "count", "units", "unit_count", "volume"]
    price_candidates = ["unitprice", "price", "unit_price", "rate", "unit_cost", "item_price"]
    
    found_qty_col = next((cols_lower[c] for c in qty_candidates if c in cols_lower), None)
    found_price_col = next((cols_lower[c] for c in price_candidates if c in cols_lower), None)
    
    if found_qty_col and found_price_col:
        try:
            # 3. Ensure numeric safety
            qty_series = pd.to_numeric(df[found_qty_col], errors="coerce")
            price_series = pd.to_numeric(df[found_price_col], errors="coerce")
            
            # 4. Compute Revenue
            df["Revenue"] = qty_series * price_series
            
            # 5. Drop rows where multiplication failed (NaN) to avoid skewing analysis
            before_count = len(df)
            df = df.dropna(subset=["Revenue"])
            dropped = before_count - len(df)
            if dropped > 0:
                logger.info(f"Dropped {dropped} rows with invalid Revenue computation")
            
            logger.info(f"Revenue column generated from {found_qty_col} * {found_price_col}")
        except Exception as e:
            logger.error(f"Failed to compute revenue fallback: {str(e)}")
            
    return df


@router.post("/analyze")
@limiter.limit(settings.ANALYZE_LIMIT)
async def analyze(
    request: Request,
    current_file: UploadFile = File(...),
    baseline_file: UploadFile | None = File(None),
    drop_duplicates: bool = Form(True),
    drop_missing: bool = Form(True),
    cap_outliers: bool = Form(False),
    normalize_columns: bool = Form(True),
    metric_schema: str | None = Form(None),
    _auth: bool = Depends(require_internal_auth),
):
    pdf_path = None  # Track for cleanup on error
    try:
        # Validate current file upload
        _validate_upload_file(current_file, "current dataset")
        
        # Parse current dataset
        try:
            current_df = _read_csv_safe(current_file.file)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to read the current dataset file. Please ensure it is a valid CSV file."
            )
        
        # SAFE DATASET SIZE LIMIT: Sample if dataset is too large
        if len(current_df) > MAX_ANALYSIS_ROWS:
            logger.info(f"Current dataset contains {len(current_df)} rows. Sampling down to {MAX_ANALYSIS_ROWS} for analysis.")
            current_df = current_df.sample(MAX_ANALYSIS_ROWS, random_state=42)
        
        # SAFE REVENUE FALLBACK: Compute Revenue if not present
        current_df = _apply_revenue_fallback(current_df)
        
        # Validate current dataframe
        _validate_dataframe(current_df, "current dataset")

        # Validate current dataset is not empty before processing
        if current_df.empty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The current dataset file is empty. Please upload a file with data."
            )

        # Parse baseline dataset if provided
        baseline_df = None
        if baseline_file:
            # Validate baseline file upload
            _validate_upload_file(baseline_file, "baseline dataset")
            
            try:
                baseline_df = _read_csv_safe(baseline_file.file)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unable to read the baseline dataset file. Please ensure it is a valid CSV file."
                )
            
            # SAFE DATASET SIZE LIMIT: Sample if dataset is too large
            if len(baseline_df) > MAX_ANALYSIS_ROWS:
                logger.info(f"Baseline dataset contains {len(baseline_df)} rows. Sampling down to {MAX_ANALYSIS_ROWS} for analysis.")
                baseline_df = baseline_df.sample(MAX_ANALYSIS_ROWS, random_state=42)
            
            # SAFE REVENUE FALLBACK: Compute Revenue if not present
            baseline_df = _apply_revenue_fallback(baseline_df)
            
            # Validate baseline dataframe
            _validate_dataframe(baseline_df, "baseline dataset")
            
            # Validate baseline dataset is not empty
            if baseline_df.empty:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The baseline dataset file is empty. Please upload a file with data or omit the baseline file."
                )

        # Construct CleaningOptions from parsed form fields
        cleaning = CleaningOptions(
            drop_duplicates=drop_duplicates,
            drop_missing=drop_missing,
            cap_outliers=cap_outliers,
            normalize_columns=normalize_columns,
        )

        # Process datasets and generate report
        try:
            report = service.run(
                current_df=current_df,
                baseline_df=baseline_df,
                cleaning=cleaning,
            )
        except ValueError as e:
            # User-facing validation errors
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            # Unexpected errors - log actual error for debugging
            logger.error(f"Analysis pipeline error: {type(e).__name__}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing your request. Please try again or contact support."
            )

        # Generate business insights BEFORE PDF so the PDF includes them.
        # (additive layer - never fails main request for default usage;
        # explicit metric_schema errors surface as 400s)
        business_insights = None
        try:
            # Re-preprocess for business insights (matches what service.run does)
            bi_current_df = preprocess_with_options(current_df.copy(), cleaning)
            bi_baseline_df = None
            if baseline_df is not None:
                bi_baseline_df = preprocess_with_options(baseline_df.copy(), cleaning)

            # Optional schema-based column selection for business insights only
            explicit_current_col = None
            explicit_baseline_col = None
            if metric_schema is not None:
                try:
                    explicit_current_col = select_metric_column(
                        bi_current_df,
                        metric_schema,
                    )
                    if bi_baseline_df is not None and not bi_baseline_df.empty:
                        explicit_baseline_col = select_metric_column(
                            bi_baseline_df,
                            metric_schema,
                        )
                except ValueError as exc:
                    # User-provided schema hint is invalid or cannot be satisfied
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=str(exc),
                    ) from exc

            # Detect revenue-like columns for business insight generator,
            # falling back to existing auto-detection when no explicit schema
            if explicit_current_col:
                current_rev_col = explicit_current_col
            else:
                current_rev_col, _, _ = detect_revenue_column(bi_current_df)

            baseline_rev_col = None
            if bi_baseline_df is not None and not bi_baseline_df.empty:
                if explicit_baseline_col:
                    baseline_rev_col = explicit_baseline_col
                else:
                    baseline_rev_col, _, _ = detect_revenue_column(bi_baseline_df)
            
            if current_rev_col:
                bi_result = business_insight_generator.generate(
                    report=report,
                    current_df=bi_current_df,
                    baseline_df=bi_baseline_df,
                    revenue_column=current_rev_col,
                    baseline_revenue_column=baseline_rev_col,
                )
                if bi_result:
                    business_insights = bi_result.dict()
                    
                    # V1.75+ Defensive guard: Payload size check (max 10KB)
                    try:
                        serialized_size = len(json.dumps(business_insights))
                        if serialized_size > 10240:  # 10KB limit
                            # Truncate executive_takeaways to 4 bullets
                            if business_insights.get("executive_takeaways"):
                                business_insights["executive_takeaways"] = business_insights["executive_takeaways"][:4]
                            # Add truncated flag in meta
                            if business_insights.get("meta") is None:
                                business_insights["meta"] = {}
                            business_insights["meta"]["truncated"] = True
                    except Exception:
                        pass  # Payload size check is defensive - never fail
        except HTTPException:
            # Re-raise HTTP exceptions (e.g., invalid metric_schema) as-is
            raise
        except Exception:
            # Business insights are optional - never fail main request
            pass

        # Generate PDF report (now includes business insights if available)
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                render_pdf(report, f.name, business_insights=business_insights)
                pdf_path = f.name
        except Exception as e:
            # PDF generation failure
            logger.error(f"PDF generation error: {type(e).__name__}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while generating the PDF report. Please try again."
            )

        # Encode PDF as base64 for cross-service transfer (no shared filesystem needed)
        pdf_base64 = None
        if pdf_path and os.path.exists(pdf_path):
            try:
                with open(pdf_path, "rb") as pf:
                    pdf_base64 = base64.b64encode(pf.read()).decode("utf-8")
            except Exception:
                pass  # PDF encoding is best-effort

        return {
            "report": report.dict(),
            "pdf_path": pdf_path,
            "pdf_base64": pdf_base64,
            "business_insights": business_insights,
        }
    
    except HTTPException:
        # Cleanup temp file on error
        if pdf_path and os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except Exception:
                pass  # Best effort cleanup
        # Re-raise HTTP exceptions as-is
        raise
    except Exception:
        # Cleanup temp file on error
        if pdf_path and os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except Exception:
                pass  # Best effort cleanup
        # Catch-all for any unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your request. Please try again or contact support."
        )
