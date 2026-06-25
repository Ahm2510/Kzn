"""
Unit tests for outstanding payments / receivables risk.

Run: python -m pytest service_b/tests/test_receivables_risk.py -v
  OR: cd service_b && python tests/test_receivables_risk.py
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.receivables_risk import (  # noqa: E402
    ReceivablesRiskResult,
    compute_receivables_risk,
)


def _build_df() -> pd.DataFrame:
    # Latest date in the data = 2024-03-01.
    return pd.DataFrame({
        "party_name": ["Shop A", "Shop B", "Shop C", "Shop A", "Shop D"],
        "outstanding": [50000, 20000, 0, 30000, 10000],
        "invoice_date": [
            "2024-02-20",  # Shop A — recent (0-45)
            "2023-11-15",  # Shop B — very old (90+)
            "2024-02-28",  # Shop C — paid (0 outstanding, dropped)
            "2023-12-20",  # Shop A — old (60-90)
            "2024-01-05",  # Shop D — ~56 days (45-60)
        ],
    })


def test_totals_and_ranking():
    df = _build_df()
    result = compute_receivables_risk(df)
    assert isinstance(result, ReceivablesRiskResult)
    # Shop A: 50000 + 30000 = 80000 outstanding -> top of the list.
    assert result.customers[0].customer == "Shop A"
    assert result.customers[0].outstanding == 80000
    # Total excludes the zero-balance row.
    assert result.total_outstanding == 110000
    assert result.customer_count == 3  # A, B, D (C had 0)


def test_aging_buckets_computed():
    df = _build_df()
    result = compute_receivables_risk(df)
    assert result.aging_available is True
    # Shop B (Nov 2023) is well over 90 days old.
    assert result.over_90_amount >= 20000
    assert result.over_45_amount > 0
    assert result.headline_action is not None


def test_no_outstanding_column_returns_none():
    df = pd.DataFrame({"party_name": ["A", "B"], "Revenue": [1, 2]})
    result = compute_receivables_risk(df)
    assert result is None  # graceful no-op; flagged upstream in schema_warnings


def test_outstanding_without_customer_warns():
    df = pd.DataFrame({"outstanding": [100, 200], "foo": [1, 2]})
    result = compute_receivables_risk(df)
    assert isinstance(result, ReceivablesRiskResult)
    assert result.warning is not None


if __name__ == "__main__":
    test_totals_and_ranking()
    test_aging_buckets_computed()
    test_no_outstanding_column_returns_none()
    test_outstanding_without_customer_warns()
    print("All receivables_risk tests passed.")
