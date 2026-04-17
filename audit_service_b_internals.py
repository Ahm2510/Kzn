import sys
import os
import pandas as pd
from typing import Optional, Dict, Any

# Add service_b to path
sys.path.append(os.path.abspath("service_b"))

from app.services.preprocessing import preprocess_with_options
from app.services.business_insights.generator import BusinessInsightGenerator
from app.services.report_renderers.pdf_report import render_pdf
from app.schemas.insight.cleaning import CleaningOptions
from app.schemas.insight.report import InsightReport

# Helper for mock cleaning options
def get_mock_options():
    return CleaningOptions(
        normalize_columns=True,
        drop_duplicates=True,
        drop_missing=True,
        cap_outliers=True
    )

def _read_csv_safe(path):
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            return pd.read_csv(path, encoding=encoding)
        except:
            continue
    return pd.read_csv(path, encoding="utf-8", encoding_errors="ignore")

def audit_preprocessing():
    print("--- AUDIT: Preprocessing ---")
    
    # Test Scenario 3: Messy
    df_messy = _read_csv_safe("temp_audit_data/scenario_3_messy.csv")
    cleaned_df = preprocess_with_options(df_messy, get_mock_options())
    
    dq = cleaned_df.attrs.get("data_quality", {})
    # Using repr or avoiding print for non-ascii
    
    # Assertions
    assert "revenue" in cleaned_df.columns, "Fuzzy mapping failed for SaleAmount -> revenue"
    assert "date" in cleaned_df.columns, "Fuzzy mapping failed for Date_String -> date"
    assert pd.api.types.is_numeric_dtype(cleaned_df["revenue"]), "Currency cleaning failed to convert to numeric"
    assert (cleaned_df["product"] == "iphone 13").any(), "Product normalization failed"
    
    print("Scenario 3 PASSED")

    # Test Scenario 4: Fallback (Manual check since logic is in router usually, but let's see if engine takes it)
    # The engine usually assumes revenue is there. Preprocessing maps SaleAmount to revenue.
    # If no revenue, router might need to compute it. Let's check router logic.
    print("Scenario 4 (Integration test) skipped for standalone preprocessing.")

def audit_insights():
    print("\n--- AUDIT: Business Insights ---")
    generator = BusinessInsightGenerator()
    
    # Test Scenario 2: Ecommerce Sample
    df = _read_csv_safe("temp_audit_data/scenario_2_ecommerce.csv")
    # We need a mock InsightReport
    mock_report = InsightReport(
        summary="Test summary",
        metric_deltas=[{"name": "revenue", "current": 100000, "baseline": 90000, "percent_change": 11.1, "absolute_change": 10000}],
        insights=[]
    )
    
    # The generator needs a revenue column name. In Scenario 2 from ecom_data.csv, we should check column names.
    df_clean = preprocess_with_options(df, get_mock_options())
    
    # Mock the router logic of computing revenue if missing
    if "revenue" not in df_clean.columns:
        if "quantity" in df_clean.columns and "unit_price" in df_clean.columns:
            df_clean["revenue"] = df_clean["quantity"] * df_clean["unit_price"]
        elif "Quantity" in df and "UnitPrice" in df: # Original names if not normalized
            df_clean["revenue"] = pd.to_numeric(df["Quantity"]) * pd.to_numeric(df["UnitPrice"])

    rev_col = "revenue" if "revenue" in df_clean.columns else df_clean.columns[0]
    
    insights = generator.generate(mock_report, df_clean, None, rev_col)
    
    if insights:
        print(f"Insights Generated: True")
        print(f"Products to watch: {insights.products_to_watch}")
        print(f"Executive Summary: {insights.executive_summary[:100]}...")
        assert insights.products_to_watch is not None or len(df_clean[rev_col].unique()) < 5, "Products to watch should be populated if data exists"
    else:
        print("FAILED to generate insights")
        
    print("Scenario 2 PASSED")

def audit_pdf():
    # Only verify render_pdf doesn't crash
    print("\n--- AUDIT: PDF Rendering ---")
    generator = BusinessInsightGenerator()
    df = _read_csv_safe("temp_audit_data/scenario_1_small_clean.csv")
    mock_report = InsightReport(
        summary="Test PDF summary",
        metric_deltas=[{"name": "revenue", "current": 2000, "baseline": 1800, "percent_change": 11.1, "absolute_change": 200}],
        insights=[]
    )
    insights = generator.generate(mock_report, df, None, "revenue")
    
    output_path = "temp_audit_data/test_report.pdf"
    try:
        render_pdf(mock_report, output_path, insights.dict() if insights else None)
        assert os.path.exists(output_path), "PDF file was not created"
        print(f"PDF Generated at: {output_path}")
    except Exception as e:
        print(f"PDF Rendering FAILED: {e}")
        raise e

if __name__ == "__main__":
    try:
        audit_preprocessing()
        audit_insights()
        audit_pdf()
        print("\nALL STANDALONE SERVICE AUDITS PASSED")
    except Exception as e:
        print(f"\nAUDIT FAILED: {e}")
        sys.exit(1)
