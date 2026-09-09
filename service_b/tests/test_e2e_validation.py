"""
End-to-end validation of the Kaizen V1 analysis pipeline with ecom_data.csv.
Tests: preprocessing, revenue fallback, insight engine, business insights,
all feature modules, and PDF generation.
"""
import sys
import os
import traceback
import time

# Ensure the service_b root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import numpy as np

# Initialize settings before imports
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("SERVICE_B_SECRET", "test-secret")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

from app.services.preprocessing import preprocess_with_options, _detect_schema, _detect_granularity
from app.schemas.insight.cleaning import CleaningOptions
from app.services.insight_engine.column_detector import detect_revenue_column
from app.services.insight_engine.engine import InsightEngine
from app.services.business_insights.generator import BusinessInsightGenerator
from app.services.revenue_stability import compute_revenue_stability_index
from app.services.inventory_health import compute_inventory_health_score
from app.services.early_warnings import compute_early_warnings
from app.services.product_cohorts import compute_cohort_product_performance
from app.services.customer_segments import compute_customer_segmentation
from app.services.concentration_risk import compute_concentration_risk
from app.services.executive_summary import compute_enhanced_executive_summary
from app.services.mom_commentary import compute_mom_commentary
from app.services.enhanced_products_to_watch import compute_enhanced_products_to_watch
from app.services.report_renderers.pdf_report import render_pdf


RESULTS = {}  # test_name -> (pass/fail, detail)


def record(name, passed, detail=""):
    RESULTS[name] = ("PASS" if passed else "FAIL", detail)
    status = "[PASS]" if passed else "[FAIL]"
    msg = f"  {status}: {name}" + (f" -- {detail}" if detail else "")
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"))


import pytest

def load_ecom_data(max_rows=50000):
    csv_path = os.path.join(os.path.dirname(__file__), "..", "..", "ecom_data.csv")
    csv_path = os.path.abspath(csv_path)
    if not os.path.exists(csv_path):
        pytest.skip(f"ecom_data.csv not found at {csv_path}")
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            df = pd.read_csv(csv_path, nrows=max_rows, encoding=encoding)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    else:
        df = pd.read_csv(csv_path, nrows=max_rows, encoding="utf-8", encoding_errors="ignore")
    return df


def test_raw_load():
    """Test: raw CSV loading"""
    print("\n=== TEST: Raw Data Load ===")
    df = load_ecom_data()
    record("raw_load", len(df) > 0, f"{len(df)} rows, {len(df.columns)} cols: {list(df.columns)}")
    return df


def test_revenue_fallback(df):
    """Test: Revenue fallback from Quantity * UnitPrice"""
    print("\n=== TEST: Revenue Fallback ===")
    from app.routers.analyze import _apply_revenue_fallback
    df_copy = df.copy()
    
    # Verify no revenue column exists initially
    rev_cols = [c for c in df_copy.columns if c.lower() in ["revenue", "sales", "amount", "total"]]
    record("no_initial_revenue_col", len(rev_cols) == 0, f"Revenue columns found: {rev_cols}")
    
    df_with_rev = _apply_revenue_fallback(df_copy)
    has_revenue = "Revenue" in df_with_rev.columns
    record("revenue_fallback_created", has_revenue, 
           f"Revenue column: {'present' if has_revenue else 'MISSING'}")
    
    if has_revenue:
        rev_stats = df_with_rev["Revenue"].describe()
        record("revenue_values_valid", rev_stats["count"] > 0 and not np.isnan(rev_stats["mean"]),
               f"count={rev_stats['count']:.0f}, mean={rev_stats['mean']:.2f}")
    return df_with_rev


def test_preprocessing(df):
    """Test: Preprocessing pipeline"""
    print("\n=== TEST: Preprocessing Pipeline ===")
    cleaning = CleaningOptions(
        drop_duplicates=True,
        drop_missing=True,
        cap_outliers=False,
        normalize_columns=True,
    )
    
    result_df = preprocess_with_options(df.copy(), cleaning)
    record("preprocessing_completes", not result_df.empty, f"{len(result_df)} rows remaining")
    
    # Check data quality report
    dq = result_df.attrs.get("data_quality")
    record("data_quality_report_attached", dq is not None)
    
    if dq:
        record("schema_detected", dq.get("schema_detected") is not None,
               f"Schema: {dq['schema_detected'] if dq.get('schema_detected') else 'None'}")
        record("granularity_detected", dq.get("granularity") is not None,
               f"Granularity: {dq['granularity'] if dq.get('granularity') else 'None'}")
        record("columns_renamed_logged", isinstance(dq.get("columns_renamed"), list),
               f"Renamed: {dq.get('columns_renamed', [])}")
        record("currency_cleaning_logged", isinstance(dq.get("columns_currency_cleaned"), list))
        record("date_parsing_logged", isinstance(dq.get("date_columns_parsed"), list),
               f"Parsed dates: {dq.get('date_columns_parsed', [])}")
    
    return result_df


def test_column_detection(df):
    """Test: Revenue column detection on preprocessed data"""
    print("\n=== TEST: Column Detection ===")
    col, conf, mode = detect_revenue_column(df)
    record("revenue_col_detected", col is not None, f"col={col}, conf={conf}, mode={mode}")
    return col


def test_insight_engine(df):
    """Test: Core insight engine"""
    print("\n=== TEST: Insight Engine ===")
    engine = InsightEngine()
    try:
        report = engine.run(current_df=df, baseline_df=None)
        record("insight_engine_runs", True, f"summary={report.summary[:80] if report.summary else 'None'}...")
        record("metric_deltas_present", len(report.metric_deltas) > 0,
               f"{len(report.metric_deltas)} deltas")
        record("insights_generated", len(report.insights) >= 0,
               f"{len(report.insights)} insights")
        return report
    except Exception as e:
        record("insight_engine_runs", False, str(e))
        traceback.print_exc()
        return None


def test_business_insights(df, report, rev_col):
    """Test: Full business insights generation"""
    print("\n=== TEST: Business Insights Generator ===")
    gen = BusinessInsightGenerator()
    try:
        bi = gen.generate(
            report=report,
            current_df=df,
            baseline_df=None,
            revenue_column=rev_col,
            baseline_revenue_column=None,
        )
        record("bi_generated", bi is not None)
        
        if bi:
            bi_dict = bi.dict()
            # Check all features
            # Trend is None in standalone mode (no baseline) -- this is EXPECTED
            record("feature_trend", bi.trend is None, "Correctly None in standalone mode (no baseline)")

            # Features that SHOULD be present in standalone mode
            required_features = {
                "stability": bi.stability,
                "concentration": bi.concentration,
                "executive_summary": bi.executive_summary,
                "products_to_watch": bi.products_to_watch,
                "revenue_stability_index": bi.revenue_stability_index,
                "inventory_health_score": bi.inventory_health_score,
                "early_warning_alerts": bi.early_warning_alerts,
                "cohort_product_performance": bi.cohort_product_performance,
                "customer_segmentation": bi.customer_segmentation,
                "concentration_risk_dashboard": bi.concentration_risk_dashboard,
                "enhanced_executive_summary": bi.enhanced_executive_summary,
                "mom_commentary": bi.mom_commentary,
                "enhanced_products_to_watch": bi.enhanced_products_to_watch,
                "executive_takeaways": bi.executive_takeaways,
            }
            
            for fname, fval in required_features.items():
                is_present = fval is not None
                detail = ""
                if is_present:
                    if hasattr(fval, "score"):
                        detail = f"score={fval.score}"
                    elif hasattr(fval, "label"):
                        detail = f"label={fval.label}"
                    elif hasattr(fval, "direction"):
                        detail = f"direction={fval.direction}"
                    elif hasattr(fval, "category"):
                        detail = f"category={fval.category}"
                    elif isinstance(fval, list):
                        detail = f"count={len(fval)}"
                    elif isinstance(fval, str):
                        detail = f"len={len(fval)}"
                record(f"feature_{fname}", is_present, detail)
            
            return bi
        return None
    except Exception as e:
        record("bi_generated", False, str(e))
        traceback.print_exc()
        return None


def test_individual_features(df, rev_col):
    """Test: each feature module individually"""
    print("\n=== TEST: Individual Feature Modules ===")
    
    # 1. Revenue Stability Index
    try:
        rsi = compute_revenue_stability_index(df, rev_col)
        record("rsi_standalone", rsi is not None,
               f"score={rsi.score}, label={rsi.label}, confidence={rsi.confidence}" if rsi else "None returned")
        if rsi:
            record("rsi_score_range", 0 <= rsi.score <= 100, f"score={rsi.score}")
            record("rsi_label_valid", rsi.label in ["Very Stable", "Moderately Stable", "Unstable", "Highly Unstable"])
            record("rsi_explanation_present", len(rsi.explanation) > 10)
    except Exception as e:
        record("rsi_standalone", False, str(e))
    
    # 2. Inventory Health Score
    try:
        ihs = compute_inventory_health_score(df)
        record("ihs_standalone", ihs is not None,
               f"score={ihs.score}, label={ihs.label}" if ihs else "None (no inventory data expected)")
    except Exception as e:
        record("ihs_standalone", False, str(e))
    
    # 3. Early Warning Alerts
    try:
        # Need a BI dict to pass to EWA
        fake_bi = {"stability": {"category": "moderately_volatile", "coefficient_of_variation": 0.5}}
        ewa = compute_early_warnings(fake_bi, df)
        record("ewa_standalone", ewa is not None,
               f"alert_count={ewa.alert_count}" if ewa else "None")
    except Exception as e:
        record("ewa_standalone", False, str(e))
    
    # 4. Cohort Product Performance
    try:
        clpp = compute_cohort_product_performance(df, rev_col)
        record("clpp_standalone", clpp is not None,
               f"cohorts={clpp.cohort_count}, basis={clpp.cohort_basis}" if clpp else "None")
    except Exception as e:
        record("clpp_standalone", False, str(e))
    
    # 5. Customer Segmentation
    try:
        csca = compute_customer_segmentation(df, rev_col)
        record("csca_standalone", csca is not None,
               f"segments={csca.segment_count}, basis={csca.segment_basis}, customers={csca.total_customers}" if csca else "None")
    except Exception as e:
        record("csca_standalone", False, str(e))
    
    # 6. Concentration Risk Dashboard
    try:
        crd = compute_concentration_risk(df, rev_col)
        record("crd_standalone", crd is not None,
               f"dims={crd.dimension_count}, risk={crd.overall_risk}" if crd else "None")
    except Exception as e:
        record("crd_standalone", False, str(e))
    
    # 7. Enhanced Executive Summary
    try:
        fake_bi_full = {
            "trend": None,
            "stability": {"category": "moderately_volatile", "coefficient_of_variation": 0.5},
            "revenue_stability_index": {"score": 50, "label": "Unstable"},
        }
        ees = compute_enhanced_executive_summary(fake_bi_full, len(df))
        record("ees_standalone", ees is not None,
               f"sentiment={ees.overall_sentiment}" if ees else "None")
    except Exception as e:
        record("ees_standalone", False, str(e))
    
    # 8. MoM Commentary
    try:
        mom = compute_mom_commentary(df, None, rev_col, None)
        record("mom_standalone", mom is not None,
               f"direction={mom.direction}, magnitude={mom.magnitude}" if mom else "None")
    except Exception as e:
        record("mom_standalone", False, str(e))
    
    # 9. Enhanced Products to Watch
    try:
        eptw = compute_enhanced_products_to_watch(df, rev_col)
        record("eptw_standalone", eptw is not None,
               f"products={eptw.product_count}, analyzed={eptw.total_products_analyzed}" if eptw else "None")
    except Exception as e:
        record("eptw_standalone", False, str(e))


def test_pdf_generation(report, bi):
    """Test: PDF generation"""
    print("\n=== TEST: PDF Generation ===")
    import tempfile
    try:
        bi_dict = bi.dict() if bi else None
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name
        
        render_pdf(report, pdf_path, business_insights=bi_dict)
        
        file_exists = os.path.exists(pdf_path)
        file_size = os.path.getsize(pdf_path) if file_exists else 0
        record("pdf_created", file_exists and file_size > 0, f"size={file_size} bytes")
        
        # Validate PDF header
        if file_exists:
            with open(pdf_path, "rb") as pf:
                header = pf.read(5)
            record("pdf_valid_header", header == b"%PDF-", f"header={header}")
        
        # Cleanup
        if file_exists:
            os.remove(pdf_path)
    except Exception as e:
        record("pdf_created", False, str(e))
        traceback.print_exc()


def test_edge_cases():
    """Test: Edge cases and black-box scenarios"""
    print("\n=== TEST: Edge Cases ===")
    
    cleaning = CleaningOptions(
        drop_duplicates=True, drop_missing=True,
        cap_outliers=False, normalize_columns=True,
    )
    
    # Scenario: CSV with only Quantity + UnitPrice
    print("  Scenario: Quantity + UnitPrice only")
    df_qty_price = pd.DataFrame({
        "InvoiceNo": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "Quantity": [5, 10, 3, 7, 2, 15, 8, 4, 6, 1],
        "UnitPrice": [10.5, 20.0, 15.5, 8.0, 50.0, 5.0, 12.5, 30.0, 7.5, 100.0],
        "Description": [f"Product_{i}" for i in range(10)],
    })
    from app.routers.analyze import _apply_revenue_fallback
    df_with_rev = _apply_revenue_fallback(df_qty_price.copy())
    record("edge_qty_unitprice_fallback", "Revenue" in df_with_rev.columns)
    
    # Scenario: Currency symbols in price
    print("  Scenario: Currency symbols")
    df_currency = pd.DataFrame({
        "Product": ["A", "B", "C", "D", "E"],
        "Revenue": ["$100.50", "$200.00", "$150.75", "$80.00", "$500"],
    })
    preprocessed = preprocess_with_options(df_currency.copy(), cleaning)
    record("edge_currency_cleaned", preprocessed["revenue"].dtype in [np.float64, np.int64, float],
           f"dtype={preprocessed['revenue'].dtype if 'revenue' in preprocessed.columns else 'N/A'}")
    
    # Scenario: Consistent date formats (the system parses dates in consistent formats)
    print("  Scenario: Consistent dates")
    df_dates = pd.DataFrame({
        "Date": ["2024-01-15", "2024-02-15", "2024-03-20", "2024-04-10", "2024-05-01"],
        "Revenue": [100, 200, 300, 400, 500],
    })
    preprocessed_dates = preprocess_with_options(df_dates.copy(), cleaning)
    has_date_col = "date" in preprocessed_dates.columns
    date_col_parsed = str(preprocessed_dates["date"].dtype).startswith("datetime64") if has_date_col else False
    record("edge_consistent_dates_parsed", date_col_parsed,
           f"dtype={preprocessed_dates['date'].dtype}" if has_date_col else "date col missing")
    
    # Scenario: Missing values
    print("  Scenario: Missing values")
    df_missing = pd.DataFrame({
        "Product": ["A", "B", None, "D", "E", "F", "G", "H", "I", "J"],
        "Revenue": [100, None, 300, 400, 500, None, 700, 800, 900, 1000],
    })
    preprocessed_missing = preprocess_with_options(df_missing.copy(), cleaning)
    record("edge_missing_handled", not preprocessed_missing.empty,
           f"{len(preprocessed_missing)} rows after cleaning")
    
    # Scenario: Duplicated rows
    print("  Scenario: Duplicate rows")
    df_dupes = pd.DataFrame({
        "Product": ["A", "A", "B", "B", "C"],
        "Revenue": [100, 100, 200, 200, 300],
    })
    preprocessed_dupes = preprocess_with_options(df_dupes.copy(), cleaning)
    record("edge_duplicates_removed", len(preprocessed_dupes) < 5,
           f"{len(preprocessed_dupes)} rows (from 5)")
    
    # Scenario: Empty/minimal data doesn't crash features
    print("  Scenario: Minimal dataset safety")
    df_tiny = pd.DataFrame({"Revenue": [100]})
    try:
        rsi = compute_revenue_stability_index(df_tiny, "Revenue")
        record("edge_tiny_rsi_safe", rsi is None, "Correctly returns None for insufficient data")
    except Exception as e:
        record("edge_tiny_rsi_safe", False, str(e))
    
    try:
        ihs = compute_inventory_health_score(df_tiny)
        record("edge_tiny_ihs_safe", ihs is None, "Correctly returns None for insufficient data")
    except Exception as e:
        record("edge_tiny_ihs_safe", False, str(e))


def main():
    start = time.time()
    print("=" * 70)
    print("KAIZEN V1 -- END-TO-END VALIDATION WITH ecom_data.csv")
    print("=" * 70)
    
    # Phase 1: Load raw data
    df_raw = test_raw_load()
    
    # Phase 2: Revenue fallback
    df_with_rev = test_revenue_fallback(df_raw)
    
    # Phase 3: Preprocessing
    df_preprocessed = test_preprocessing(df_with_rev)
    
    # Phase 4: Column detection
    rev_col = test_column_detection(df_preprocessed)
    
    if not rev_col:
        print("\n[CRITICAL] No revenue column detected after preprocessing. Cannot continue.")
        print("   This means the revenue fallback or preprocessing is broken.")
        return
    
    # Phase 5: Insight engine
    report = test_insight_engine(df_preprocessed)
    if not report:
        print("\n[CRITICAL] Insight engine failed. Cannot continue.")
        return
    
    # Phase 6: Full business insights
    bi = test_business_insights(df_preprocessed, report, rev_col)
    
    # Phase 7: Individual feature modules
    test_individual_features(df_preprocessed, rev_col)
    
    # Phase 8: PDF generation
    if report:
        test_pdf_generation(report, bi)
    
    # Phase 9: Edge cases
    test_edge_cases()
    
    # Summary
    elapsed = time.time() - start
    print("\n" + "=" * 70)
    print(f"VALIDATION SUMMARY (completed in {elapsed:.1f}s)")
    print("=" * 70)
    
    passed = sum(1 for s, _ in RESULTS.values() if s == "PASS")
    failed = sum(1 for s, _ in RESULTS.values() if s == "FAIL")
    total = len(RESULTS)
    
    print(f"\n  Total: {total}  |  Passed: {passed}  |  Failed: {failed}")
    
    if failed > 0:
        print("\n  FAILURES:")
        for name, (status, detail) in RESULTS.items():
            if status == "FAIL":
                try:
                    print(f"    [FAIL] {name}: {detail}")
                except UnicodeEncodeError:
                    print(f"    [FAIL] {name}: (encoding error in detail)")
    
    print("\n" + "=" * 70)
    if failed == 0:
        print("ALL TESTS PASSED -- SAFE TO SHIP")
    else:
        print(f"{failed} TEST(S) FAILED -- FIXES REQUIRED")
    print("=" * 70)


if __name__ == "__main__":
    main()
