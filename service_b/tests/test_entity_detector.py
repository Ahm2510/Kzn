"""
Unit tests for distribution-niche multi-entity column detection.

Run: python -m pytest service_b/tests/test_entity_detector.py -v
  OR: cd service_b && python tests/test_entity_detector.py
"""
import os
import sys

import pandas as pd

# Ensure service_b app is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.insight_engine.entity_detector import (  # noqa: E402
    CONFIDENCE_THRESHOLD,
    detect_customer_column,
    detect_sku_column,
    detect_quantity_column,
    detect_date_column,
    detect_outstanding_column,
    detect_route_column,
    detect_distribution_schema,
    resolve_schema,
    build_schema_warnings,
    format_inr,
    format_inr_lakh,
)


def _tally_like_df() -> pd.DataFrame:
    return pd.DataFrame({
        "Party Name": ["Shop A", "Shop B", "Shop C"],
        "Stock Item": ["Widget", "Gadget", "Sprocket"],
        "Qty": [10, 5, 2],
        "Voucher Date": ["2024-01-01", "2024-01-05", "2024-02-01"],
        "Outstanding": [1000, 0, 5000],
        "Beat": ["North", "South", "North"],
        "Revenue": [1000, 500, 200],
    })


def test_individual_detectors_match_tally_synonyms():
    df = _tally_like_df()
    col, conf, mode = detect_customer_column(df)
    assert col == "Party Name" and conf >= CONFIDENCE_THRESHOLD and mode in ("exact", "semantic")

    col, conf, _ = detect_sku_column(df)
    assert col == "Stock Item" and conf >= CONFIDENCE_THRESHOLD

    col, conf, mode = detect_quantity_column(df)
    assert col == "Qty" and mode == "exact"  # qty == 1.0

    col, conf, _ = detect_date_column(df)
    assert col == "Voucher Date" and conf >= CONFIDENCE_THRESHOLD

    col, conf, mode = detect_outstanding_column(df)
    assert col == "Outstanding" and mode == "exact"

    col, conf, _ = detect_route_column(df)
    assert col == "Beat" and conf >= CONFIDENCE_THRESHOLD


def test_orchestrator_returns_full_schema():
    df = _tally_like_df()
    schema = detect_distribution_schema(df)
    assert set(schema.keys()) == {
        "customer_col", "sku_col", "qty_col", "date_col", "outstanding_col", "route_col",
    }
    resolved = resolve_schema(schema)
    assert resolved["customer_col"] == "Party Name"
    assert resolved["sku_col"] == "Stock Item"
    assert resolved["outstanding_col"] == "Outstanding"


def test_missing_columns_fail_gracefully():
    df = pd.DataFrame({"foo": [1, 2], "bar": [3, 4]})
    schema = detect_distribution_schema(df)
    for key, (col, conf, mode) in schema.items():
        assert col is None and conf == 0.0 and mode == "none"
    warnings = build_schema_warnings(schema)
    # Required columns (customer, sku) must be flagged.
    assert any("customer" in w.lower() for w in warnings)
    assert any("sku" in w.lower() or "product" in w.lower() for w in warnings)


def test_empty_dataframe_never_raises():
    schema = detect_distribution_schema(pd.DataFrame())
    assert all(v[0] is None for v in schema.values())


def test_threshold_rejects_weak_match():
    # "value" is a revenue synonym but here we test that an unrelated column does
    # not get mis-detected as a customer column.
    df = pd.DataFrame({"random_label": ["x"], "notes": ["y"]})
    col, conf, mode = detect_customer_column(df)
    assert col is None and mode == "none"


def test_currency_formatting():
    assert format_inr(1234567) == "₹12,34,567"
    assert format_inr(-5000) == "-₹5,000"
    assert format_inr("not-a-number") == "₹0"
    assert format_inr_lakh(420000) == "₹4.2L"
    assert format_inr_lakh(15000000) == "₹1.5 Cr"
    assert format_inr_lakh(4200) == "₹4,200"


if __name__ == "__main__":
    test_individual_detectors_match_tally_synonyms()
    test_orchestrator_returns_full_schema()
    test_missing_columns_fail_gracefully()
    test_empty_dataframe_never_raises()
    test_threshold_rejects_weak_match()
    test_currency_formatting()
    print("All entity_detector tests passed.")
