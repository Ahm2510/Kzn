"""
Unit tests for customer / shop churn & risk detection.

Run: python -m pytest service_b/tests/test_customer_churn_risk.py -v
  OR: cd service_b && python tests/test_customer_churn_risk.py
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.customer_churn_risk import (  # noqa: E402
    CustomerChurnRiskResult,
    compute_customer_churn_risk,
)


def _build_df() -> pd.DataFrame:
    """
    Four shops with the dataset's latest date = 2024-03-01:
      - ActiveShop:  weekly orders right up to the end  -> active
      - QuietShop:   used to order ~every 10 days, silent since 2024-01-01 -> at risk/churned
      - ChurnedShop: one ancient order in 2023-06       -> churned
      - SteadyShop:  fortnightly orders to late Feb      -> active
    """
    rows = []
    # ActiveShop — weekly through 2024-02-26
    for d in pd.date_range("2024-01-01", "2024-02-26", freq="7D"):
        rows.append(("ActiveShop", d, 2000))
    # QuietShop — every 10 days but stops at 2024-01-01
    for d in pd.date_range("2023-11-01", "2024-01-01", freq="10D"):
        rows.append(("QuietShop", d, 5000))
    # ChurnedShop — single ancient order
    rows.append(("ChurnedShop", pd.Timestamp("2023-06-01"), 8000))
    # SteadyShop — fortnightly through 2024-02-24
    for d in pd.date_range("2024-01-02", "2024-02-24", freq="14D"):
        rows.append(("SteadyShop", d, 1500))
    df = pd.DataFrame(rows, columns=["customer", "date", "Revenue"])
    return df


def test_churn_detects_quiet_and_churned_shops():
    df = _build_df()
    result = compute_customer_churn_risk(df, "Revenue")
    assert isinstance(result, CustomerChurnRiskResult)
    assert result.total_customers == 4
    assert result.has_at_risk is True
    flagged = {c.customer: c.risk for c in result.customers}
    # ChurnedShop must be flagged churned; QuietShop must be flagged at minimum at-risk.
    assert flagged.get("ChurnedShop") == "churned"
    assert flagged.get("QuietShop") in ("at_risk", "churned")
    # Active shops should not appear in the flagged list.
    assert "ActiveShop" not in flagged or flagged["ActiveShop"] == "active"


def test_ranking_puts_highest_revenue_at_risk_first():
    df = _build_df()
    result = compute_customer_churn_risk(df, "Revenue")
    flagged = [c for c in result.customers if c.risk in ("at_risk", "churned")]
    # Revenue at risk should be the sum of flagged customers' revenue and > 0.
    assert result.revenue_at_risk > 0
    # The headline action must be operator-facing and mention calling shops.
    assert result.headline_action and "call" in result.headline_action.lower()
    # Flagged are ordered churned-first then by revenue desc within risk tier.
    assert len(flagged) >= 2


def test_no_customer_column_returns_warning_not_crash():
    df = pd.DataFrame({"foo": [1, 2, 3], "Revenue": [1, 2, 3]})
    result = compute_customer_churn_risk(df, "Revenue")
    assert isinstance(result, CustomerChurnRiskResult)
    assert result.warning is not None
    assert result.has_at_risk is False


def test_no_date_column_returns_warning():
    df = pd.DataFrame({"customer": ["A", "B", "C"], "Revenue": [1, 2, 3]})
    result = compute_customer_churn_risk(df, "Revenue")
    assert result.warning is not None


if __name__ == "__main__":
    test_churn_detects_quiet_and_churned_shops()
    test_ranking_puts_highest_revenue_at_risk_first()
    test_no_customer_column_returns_warning_not_crash()
    test_no_date_column_returns_warning()
    print("All customer_churn_risk tests passed.")
