"""
Unit tests for dead stock / slow-moving inventory (inventory_health.py extension)
and the operator action list assembly.

Run: python -m pytest service_b/tests/test_dead_stock.py -v
  OR: cd service_b && python tests/test_dead_stock.py
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.inventory_health import compute_inventory_health_score  # noqa: E402
from app.services.action_list import build_action_list  # noqa: E402


def _build_df() -> pd.DataFrame:
    """
    Latest date = 2024-03-01.
      - LiveSKU:   sold through late February          -> NOT dead
      - DeadSKU_A: last sold 2023-12-01 (~90 days idle) -> dead, high value
      - DeadSKU_B: last sold 2023-12-20 (~70 days idle) -> dead, lower value
    """
    rows = []
    for d in pd.date_range("2024-01-01", "2024-02-25", freq="5D"):
        rows.append(("LiveSKU", d, 1000))
    for d in pd.date_range("2023-10-01", "2023-12-01", freq="10D"):
        rows.append(("DeadSKU_A", d, 9000))
    for d in pd.date_range("2023-10-10", "2023-12-20", freq="15D"):
        rows.append(("DeadSKU_B", d, 1500))
    return pd.DataFrame(rows, columns=["product", "date", "Revenue"])


def test_dead_stock_flagged_with_value():
    df = _build_df()
    result = compute_inventory_health_score(df, dead_stock_days=60)
    assert result is not None
    assert result.dead_stock_count == 2
    assert result.dead_stock_window_days == 60
    skus = {s["sku"] for s in result.dead_stock_skus}
    assert "DeadSKU_A" in skus and "DeadSKU_B" in skus
    assert "LiveSKU" not in skus
    # Rupee value of capital tied up is the headline number.
    assert result.total_dead_stock_value is not None and result.total_dead_stock_value > 0
    # Ranked by value tied up — DeadSKU_A (higher revenue) first.
    assert result.dead_stock_skus[0]["sku"] == "DeadSKU_A"


def test_window_size_changes_result():
    df = _build_df()
    # A 120-day window should flag nothing (the dead SKUs are < 120 days idle on
    # the lower-value one, but DeadSKU_A at ~90 days is still under 120).
    result = compute_inventory_health_score(df, dead_stock_days=120)
    assert result is not None
    assert (result.dead_stock_count or 0) == 0


def test_action_list_includes_dead_stock_item():
    df = _build_df()
    ihs = compute_inventory_health_score(df, dead_stock_days=60)
    items = build_action_list(churn=None, inventory_health=ihs, receivables=None)
    assert any(i.category == "dead_stock" for i in items)
    dead_item = next(i for i in items if i.category == "dead_stock")
    assert "clearance" in dead_item.headline.lower() or "reorder" in dead_item.headline.lower()


def test_action_list_empty_when_no_signals():
    assert build_action_list(None, None, None) == []


if __name__ == "__main__":
    test_dead_stock_flagged_with_value()
    test_window_size_changes_result()
    test_action_list_includes_dead_stock_item()
    test_action_list_empty_when_no_signals()
    print("All dead_stock / action_list tests passed.")
