"""
Unit tests for the operator action list assembled from all three distributor
signals (churn, dead stock, receivables).

Run: python -m pytest service_b/tests/test_action_list.py -v
  OR: cd service_b && python tests/test_action_list.py
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.action_list import build_action_list, ActionItem  # noqa: E402
from app.services.customer_churn_risk import compute_customer_churn_risk  # noqa: E402
from app.services.receivables_risk import compute_receivables_risk  # noqa: E402
from app.services.inventory_health import compute_inventory_health_score  # noqa: E402


def _distributor_df() -> pd.DataFrame:
    """A single Tally-style frame carrying customer, sku, date, revenue and
    outstanding columns so all three signals fire at once."""
    rows = []
    # Live shop + live SKU through late Feb (latest date 2024-03-01).
    for d in pd.date_range("2024-01-01", "2024-02-25", freq="5D"):
        rows.append(("ActiveShop", "LiveSKU", d, 1000, 0))
    # Quiet shop, dead SKU, and an overdue balance.
    for d in pd.date_range("2023-10-01", "2023-12-01", freq="10D"):
        rows.append(("QuietShop", "DeadSKU", d, 9000, 40000))
    # Another active shop for customer-count minimums.
    for d in pd.date_range("2024-01-03", "2024-02-20", freq="9D"):
        rows.append(("SteadyShop", "LiveSKU", d, 1200, 0))
    return pd.DataFrame(
        rows, columns=["party_name", "product", "invoice_date", "Revenue", "outstanding"]
    )


def test_action_list_pulls_one_item_per_signal():
    df = _distributor_df()
    churn = compute_customer_churn_risk(df, "Revenue")
    receivables = compute_receivables_risk(df)
    ihs = compute_inventory_health_score(df, dead_stock_days=60)

    items = build_action_list(churn=churn, inventory_health=ihs, receivables=receivables)
    assert all(isinstance(i, ActionItem) for i in items)
    categories = [i.category for i in items]
    # Each signal contributes at most one item; at least churn + dead stock fire.
    assert len(categories) == len(set(categories))  # no category twice
    assert "dead_stock" in categories
    assert "churn" in categories
    # Priority-sorted ascending.
    assert items == sorted(items, key=lambda i: i.priority)
    # Every headline is a non-empty, complete sentence.
    for i in items:
        assert i.headline and len(i.headline) > 10 and i.headline.rstrip().endswith(".")


def test_action_list_survives_partial_signals():
    # Only receivables present.
    df = _distributor_df()
    receivables = compute_receivables_risk(df)
    items = build_action_list(churn=None, inventory_health=None, receivables=receivables)
    assert all(i.category == "receivables" for i in items)


if __name__ == "__main__":
    test_action_list_pulls_one_item_per_signal()
    test_action_list_survives_partial_signals()
    print("All action_list tests passed.")
