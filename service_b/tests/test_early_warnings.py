"""
Verification script for Early Warning Alerts using ecom_data.csv.
 
This script loads the dataset, simulates the minimal pipeline steps needed
to produce business insights, then runs compute_early_warnings() and
prints all results for manual verification.
 
Run: python -m pytest service_b/tests/test_early_warnings.py -v -s
  OR: cd service_b && python tests/test_early_warnings.py
"""
import os
import sys
import pandas as pd
 
# Ensure service_b app is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
 
from app.services.early_warnings import (
    EarlyWarningResult,
    compute_early_warnings,
)
 
 
def _load_ecom_data() -> pd.DataFrame:
    """Load ecom_data.csv from project root."""
    csv_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "ecom_data.csv"
    )
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"ecom_data.csv not found at {csv_path}")
    df = pd.read_csv(csv_path, encoding="latin-1", nrows=10000)  # limit for test speed
    # Compute revenue fallback
    if "Revenue" not in df.columns and "Quantity" in df.columns and "UnitPrice" in df.columns:
        df["Revenue"] = pd.to_numeric(df["Quantity"], errors="coerce") * pd.to_numeric(df["UnitPrice"], errors="coerce")
    return df
 
 
def _build_mock_bi(df: pd.DataFrame) -> dict:
    """
    Build a mock business_insights dict from the dataframe,
    simulating what the real pipeline would produce.
    """
    rev = pd.to_numeric(df.get("Revenue", pd.Series(dtype=float)), errors="coerce").dropna()
    n = len(rev)
    mean_rev = float(rev.mean()) if n > 0 else 0
    cv = float(abs(rev.std() / mean_rev)) if mean_rev != 0 and n >= 2 else 0
 
    # Stability
    if cv < 0.3:
        stab_cat = "stable"
    elif cv < 0.7:
        stab_cat = "moderately_volatile"
    else:
        stab_cat = "highly_volatile"
 
    # Concentration
    conc_contrib = 0.0
    conc_risk = "low"
    if n >= 10 and rev.sum() > 0:
        top_10 = rev.sort_values(ascending=False).head(max(1, int(n * 0.1))).sum()
        conc_contrib = float((top_10 / rev.sum()) * 100)
        if conc_contrib > 60:
            conc_risk = "high"
        elif conc_contrib > 40:
            conc_risk = "moderate"
 
    # Products to watch
    ptw = []
    prod_col = "Description"
    if prod_col in df.columns:
        grouped = df.assign(__rev=rev).groupby(prod_col)["__rev"].sum().dropna()
        grouped = grouped[grouped > 0].sort_values()
        if not grouped.empty:
            total = grouped.sum()
            threshold = total * 0.20
            cumul = 0
            for prod, r in grouped.items():
                if cumul + r <= threshold:
                    ptw.append(str(prod))
                    cumul += r
                else:
                    break
            ptw = ptw[:5]
 
    return {
        "trend": None,  # No baseline in standalone mode
        "stability": {
            "category": stab_cat,
            "coefficient_of_variation": round(cv, 4),
            "description": f"CV={cv:.2f}",
            "confidence": "medium",
        },
        "concentration": {
            "top_10_percent_contribution": round(conc_contrib, 2),
            "risk_level": conc_risk,
            "description": f"Top 10% = {conc_contrib:.0f}%",
            "confidence": "medium",
        },
        "efficiency": None,
        "products_to_watch": ptw if ptw else None,
        "revenue_stability_index": None,
        "inventory_health_score": None,
    }
 
 
def test_early_warnings_with_ecom_data():
    """End-to-end verification with ecom_data.csv."""
    df = _load_ecom_data()
    bi = _build_mock_bi(df)
    result = compute_early_warnings(bi, df)
 
    assert result is not None, "compute_early_warnings returned None"
    assert isinstance(result, EarlyWarningResult)
 
    print(f"\n{'='*60}")
    print(f"EARLY WARNING ALERTS - ecom_data.csv ({len(df)} rows)")
    print(f"{'='*60}")
    print(f"Total alerts: {result.alert_count}")
    print(f"Has critical: {result.has_critical}")
    print(f"Has high:     {result.has_high}")
    print()
 
    for i, alert in enumerate(result.alerts, 1):
        print(f"--- Alert #{i} ---")
        print(f"  Code:        {alert.alert_code}")
        print(f"  Severity:    {alert.severity}")
        print(f"  Title:       {alert.title}")
        print(f"  Description: {alert.description}")
        print(f"  Driver:      {alert.driver}")
        print(f"  Implication: {alert.implication}")
        print(f"  Action:      {alert.action_direction}")
        print(f"  Confidence:  {alert.confidence}")
        print()
 
    # Assert structural correctness
    for alert in result.alerts:
        assert alert.alert_code, "alert_code must be non-empty"
        assert alert.severity in ("critical", "high", "medium", "low")
        assert alert.title, "title must be non-empty"
        assert alert.description, "description must be non-empty"
        assert alert.driver, "driver must be non-empty"
 
    # Verify sorting: no lower-severity alert appears before a higher-severity one
    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    for i in range(len(result.alerts) - 1):
        assert sev_order[result.alerts[i].severity] <= sev_order[result.alerts[i + 1].severity], \
            f"Alerts not sorted by severity: {result.alerts[i].severity} > {result.alerts[i+1].severity}"
 
 
def test_empty_insights_returns_empty_alerts():
    """When business insights are empty/minimal, no false alerts should fire."""
    result = compute_early_warnings({})
    assert result is not None
    assert result.alert_count == 0
    assert result.alerts == []
    assert result.has_critical is False
    assert result.has_high is False
 
 
def test_no_crash_on_none_values():
    """EWA should never crash, even with None values everywhere."""
    bi = {
        "trend": None,
        "stability": None,
        "concentration": None,
        "efficiency": None,
        "products_to_watch": None,
        "revenue_stability_index": None,
        "inventory_health_score": None,
    }
    result = compute_early_warnings(bi, None)
    assert result is not None
    assert result.alert_count == 0
 
 
if __name__ == "__main__":
    test_empty_insights_returns_empty_alerts()
    print("PASS: empty insights -> empty alerts")
 
    test_no_crash_on_none_values()
    print("PASS: None values -> no crash")
 
    test_early_warnings_with_ecom_data()
    print("\nPASS: ecom_data.csv verification complete")
