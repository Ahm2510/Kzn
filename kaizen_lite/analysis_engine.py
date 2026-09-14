"""
Analysis engine integration layer.
Imports and calls service_b's analysis modules in-process.
"""
import sys
from pathlib import Path

# Add service_b to Python path for in-process imports
SERVICE_B_PATH = Path(__file__).parent.parent / "service_b"
sys.path.insert(0, str(SERVICE_B_PATH))

import pandas as pd
import json
from datetime import datetime
from typing import Dict, Any, Optional, List

# Import service_b modules
from app.services.preprocessing import preprocess_with_options
from app.services.schemas.insight.cleaning import CleaningOptions
from app.services.insight_engine.column_detector import detect_revenue_column
from app.services.insight_engine.engine import InsightEngine
from app.services.business_insights.generator import BusinessInsightGenerator
from app.services.executive_summary import compute_enhanced_executive_summary
from app.services.action_list import build_action_list
from app.services.report_renderers.pdf_report import render_pdf


def analyze_ledger(
    df: pd.DataFrame,
    firm_name: str,
    logo_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run the full analysis pipeline on a ledger DataFrame.
    Returns a summary dict with all key metrics for delta computation.
    """
    # Preprocessing
    cleaning = CleaningOptions(
        drop_duplicates=True,
        drop_missing=True,
        cap_outliers=False,
        normalize_columns=True,
    )
    df_clean = preprocess_with_options(df, cleaning)
    
    if df_clean.empty:
        raise ValueError("Dataset is empty after preprocessing. Please check your data.")
    
    # Detect revenue column
    revenue_col, _, _ = detect_revenue_column(df_clean)
    if not revenue_col:
        raise ValueError("No revenue-like column detected. Please ensure your data contains a column such as 'revenue', 'sales', 'amount', or 'total'.")
    
    # Run insight engine
    from app.schemas.insight.report import InsightReport
    insight_engine_instance = InsightEngine()
    report = insight_engine_instance.run(current_df=df_clean, baseline_df=None)
    
    # Generate business insights (this orchestrates all modules: RSI, IHS, EWA, CRD, churn, receivables, margin, etc.)
    bi_generator = BusinessInsightGenerator()
    bi_result = bi_generator.generate(
        report=report,
        current_df=df_clean,
        baseline_df=None,
        revenue_column=revenue_col,
        baseline_revenue_column=None,
    )
    
    if bi_result:
        business_insights = bi_result.dict()
    else:
        business_insights = {}
    
    # Compute enhanced executive summary
    exec_summary = compute_enhanced_executive_summary(
        business_insights,
        row_count=len(df_clean)
    )
    
    # Compute action list
    churn_result = business_insights.get("customer_churn_risk")
    inventory_result = business_insights.get("inventory_health_score")
    receivables_result = business_insights.get("receivables_risk")
    
    action_items = build_action_list(
        churn=churn_result,
        inventory_health=inventory_result,
        receivables=receivables_result,
    )
    
    # Build summary JSON for delta computation
    summary = {
        "receivables_risk_score": _extract_score(receivables_result),
        "concentration_hhi": _extract_hhi(business_insights),
        "revenue_stability_score": _extract_rsi_score(business_insights),
        "margin_pct": _extract_margin_pct(business_insights),
        "quiet_account_count": _extract_churn_count(business_insights),
        "overall_sentiment": exec_summary.overall_sentiment if exec_summary else "neutral",
        "alert_count": _extract_alert_count(business_insights),
        "inventory_health_score": _extract_ihs_score(business_insights),
    }
    
    return {
        "summary": summary,
        "business_insights": business_insights,
        "executive_summary": exec_summary.dict() if exec_summary else None,
        "action_list": [item.dict() for item in action_items] if action_items else [],
        "report": report.dict(),
    }


def generate_pdf(
    analysis_result: Dict[str, Any],
    output_path: str,
    firm_name: str,
    logo_path: Optional[str] = None
) -> bytes:
    """
    Generate a white-labeled PDF report and return as bytes.
    """
    from app.schemas.insight.report import InsightReport
    
    report = InsightReport(**analysis_result["report"])
    business_insights = analysis_result["business_insights"]
    
    # Generate PDF to a temporary file, then read as bytes
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        render_pdf(report, tmp_path, business_insights=business_insights)
        with open(tmp_path, "rb") as f:
            pdf_bytes = f.read()
        return pdf_bytes
    finally:
        import os
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _extract_score(receivables_result) -> Optional[float]:
    """Extract a simple risk score from receivables result."""
    if not receivables_result:
        return None
    # Use over_45_amount as a proxy for risk score
    return receivables_result.get("over_45_amount")


def _extract_hhi(business_insights: Dict) -> Optional[float]:
    """Extract HHI from concentration risk dashboard."""
    crd = business_insights.get("concentration_risk_dashboard")
    if crd and crd.get("dimensions"):
        # Use the first dimension's HHI
        dim = crd["dimensions"][0] if crd["dimensions"] else None
        if dim:
            return dim.get("hhi")
    # Fallback to basic concentration
    conc = business_insights.get("concentration")
    if conc:
        # Convert top_10_percent_contribution to a pseudo-HHI
        top_10 = conc.get("top_10_percent_contribution", 0)
        return (top_10 / 100) ** 2 * 10000  # Rough HHI approximation
    return None


def _extract_rsi_score(business_insights: Dict) -> Optional[float]:
    """Extract Revenue Stability Index score."""
    rsi = business_insights.get("revenue_stability_index")
    if rsi:
        return rsi.get("score")
    return None


def _extract_margin_pct(business_insights: Dict) -> Optional[float]:
    """Extract overall margin percentage."""
    margin = business_insights.get("margin_analysis")
    if margin:
        return margin.get("overall_margin_pct")
    return None


def _extract_churn_count(business_insights: Dict) -> Optional[int]:
    """Extract quiet/churned account count."""
    churn = business_insights.get("customer_churn_risk")
    if churn:
        return (churn.get("at_risk_count") or 0) + (churn.get("churned_count") or 0)
    return None


def _extract_alert_count(business_insights: Dict) -> Optional[int]:
    """Extract early warning alert count."""
    ewa = business_insights.get("early_warning_alerts")
    if ewa:
        return ewa.get("alert_count")
    return None


def _extract_ihs_score(business_insights: Dict) -> Optional[float]:
    """Extract Inventory Health Score."""
    ihs = business_insights.get("inventory_health_score")
    if ihs:
        return ihs.get("score")
    return None
