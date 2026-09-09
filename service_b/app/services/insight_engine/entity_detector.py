# services/insight_engine/entity_detector.py
"""
Distribution-Niche Multi-Entity Column Detection

Distributor (FMCG / pharma / auto-parts) datasets exported from Tally or Excel
always carry more structure than a single revenue column: a customer/party/shop
name, a product/SKU, a quantity, a transaction date, and very often an
outstanding/receivable amount and a route/salesman.

This module mirrors the exact pattern established by ``column_detector.py``
(``detect_revenue_column``): synonym dictionaries scored by confidence, an
exact-then-semantic match, and a shared ``CONFIDENCE_THRESHOLD``. Each detector
returns ``(column_name, confidence, detection_mode)`` and fails gracefully —
it never raises, returning ``(None, 0.0, "none")`` when nothing matches.

``detect_distribution_schema`` orchestrates every detector into a single
structured dict so downstream distributor features (churn, dead stock,
receivables, action list) can share one detection pass.
"""

from typing import Dict, Optional, Tuple
import re

import pandas as pd


# Minimum confidence for a semantic match to be accepted.
# Mirrors column_detector.CONFIDENCE_THRESHOLD so behaviour is consistent.
CONFIDENCE_THRESHOLD = 0.80


# ─────────────────────────────────────────────────────────────────────────────
# Synonym dictionaries (name -> confidence). Higher = more certain.
# Exact, canonical terms score 1.0 (V1.5-style exact match); softer / context
# dependent terms score lower so the threshold can filter ambiguous columns.
# ─────────────────────────────────────────────────────────────────────────────

CUSTOMER_SYNONYMS = {
    "customer": 1.0,
    "customer_name": 0.98,
    "customer_id": 0.95,
    "party": 0.95,
    "party_name": 0.95,
    "party_ledger": 0.92,     # Tally ledger export
    "ledger_name": 0.85,      # Tally
    "shop": 0.90,
    "shop_name": 0.92,
    "retailer": 0.90,
    "retailer_name": 0.90,
    "account_name": 0.85,
    "buyer": 0.85,
    "buyer_name": 0.88,
    "client_name": 0.90,
    "dealer": 0.85,
    "dealer_name": 0.88,
}

SKU_SYNONYMS = {
    "sku": 1.0,
    "product": 1.0,
    "product_name": 0.98,
    "item_name": 0.95,
    "stock_item": 0.95,       # Tally
    "item": 0.90,
    "item_code": 0.88,
    "material": 0.85,
    "material_name": 0.88,
    "product_code": 0.88,
}

QUANTITY_SYNONYMS = {
    "qty": 1.0,
    "quantity": 1.0,
    "units_sold": 0.92,
    "no_of_units": 0.90,
    "units": 0.90,
    "qty_sold": 0.92,
    "billed_qty": 0.88,
}

DATE_SYNONYMS = {
    "date": 1.0,
    "invoice_date": 0.98,
    "transaction_date": 0.95,
    "voucher_date": 0.95,     # Tally
    "bill_date": 0.92,
    "order_date": 0.90,
}

OUTSTANDING_SYNONYMS = {
    "outstanding": 1.0,
    "due_amount": 0.95,
    "balance_due": 0.95,
    "receivable": 0.95,
    "unpaid_amount": 0.92,
    "pending_amount": 0.90,
    "due": 0.90,
    "outstanding_amount": 0.98,
    "closing_balance": 0.85,  # Tally outstanding ledger
    "amount_due": 0.93,
}

ROUTE_SYNONYMS = {
    "route": 1.0,
    "salesman": 0.95,
    "sales_rep": 0.92,
    "territory": 0.92,
    "beat": 0.90,             # FMCG distribution "beat plan"
    "zone_rep": 0.90,
    "salesperson": 0.92,
    "sales_executive": 0.88,
}


# ─────────────────────────────────────────────────────────────────────────────
# Core detection
# ─────────────────────────────────────────────────────────────────────────────

def _normalize(name: str) -> str:
    """Lowercase, strip, and collapse separators so 'Party Name', 'party-name'
    and 'party_name' all resolve to the same key."""
    key = str(name).lower().strip()
    key = re.sub(r"[\s\-./]+", "_", key)
    return key


def _detect_by_synonyms(
    df: pd.DataFrame,
    synonyms: Dict[str, float],
    threshold: float = CONFIDENCE_THRESHOLD,
) -> Tuple[Optional[str], float, str]:
    """
    Shared engine behind every public detector. Mirrors
    ``detect_revenue_column``: exact (confidence 1.0) match first, then the
    best-scoring semantic match above ``threshold``.

    Returns ``(column_name, confidence, detection_mode)`` where mode is
    "exact" for a 1.0 hit, "semantic" for a threshold hit, "none" otherwise.
    """
    if df is None or len(df.columns) == 0:
        return None, 0.0, "none"

    columns_norm = {_normalize(col): col for col in df.columns}

    # Exact / canonical match first (V1.5-style backward-compatible behaviour).
    for norm, original in columns_norm.items():
        if synonyms.get(norm) == 1.0:
            return original, 1.0, "exact"

    # Semantic match: pick the highest-confidence synonym present.
    best_match: Optional[str] = None
    best_confidence: float = 0.0
    for norm, original in columns_norm.items():
        conf = synonyms.get(norm, 0.0)
        if conf > best_confidence:
            best_confidence = conf
            best_match = original

    if best_match and best_confidence >= threshold:
        return best_match, best_confidence, "semantic"

    return None, best_confidence, "none"


def detect_customer_column(df: pd.DataFrame) -> Tuple[Optional[str], float, str]:
    """Detect the customer / party / shop identifier column."""
    return _detect_by_synonyms(df, CUSTOMER_SYNONYMS)


def detect_sku_column(df: pd.DataFrame) -> Tuple[Optional[str], float, str]:
    """Detect the product / SKU / stock-item column."""
    return _detect_by_synonyms(df, SKU_SYNONYMS)


def detect_quantity_column(df: pd.DataFrame) -> Tuple[Optional[str], float, str]:
    """Detect the quantity / units column."""
    return _detect_by_synonyms(df, QUANTITY_SYNONYMS)


def detect_date_column(df: pd.DataFrame) -> Tuple[Optional[str], float, str]:
    """Detect the transaction / invoice / voucher date column."""
    col, conf, mode = _detect_by_synonyms(df, DATE_SYNONYMS)
    # Name match is enough to report detection; parseability is validated by
    # the consuming feature (e.g. churn) the same way revenue numericness is
    # validated separately from name detection in column_detector.
    return col, conf, mode


def detect_outstanding_column(df: pd.DataFrame) -> Tuple[Optional[str], float, str]:
    """Detect the outstanding / receivable / due-amount column."""
    return _detect_by_synonyms(df, OUTSTANDING_SYNONYMS)


def detect_route_column(df: pd.DataFrame) -> Tuple[Optional[str], float, str]:
    """Detect the route / salesman / territory column (optional, low priority)."""
    return _detect_by_synonyms(df, ROUTE_SYNONYMS)


# ─────────────────────────────────────────────────────────────────────────────
# Orchestration
# ─────────────────────────────────────────────────────────────────────────────

# Stable key order so downstream consumers can rely on it.
_SCHEMA_KEYS = (
    "customer_col",
    "sku_col",
    "qty_col",
    "date_col",
    "outstanding_col",
    "route_col",
)


def detect_distribution_schema(
    df: pd.DataFrame,
) -> Dict[str, Tuple[Optional[str], float, str]]:
    """
    Run every entity detector and return a structured schema dict.

    Each value is a ``(column_name, confidence, detection_mode)`` tuple. Missing
    columns yield ``(None, 0.0, "none")`` — the function never raises, even on a
    malformed / empty DataFrame.
    """
    try:
        if df is None:
            raise ValueError("no dataframe")
        return {
            "customer_col": detect_customer_column(df),
            "sku_col": detect_sku_column(df),
            "qty_col": detect_quantity_column(df),
            "date_col": detect_date_column(df),
            "outstanding_col": detect_outstanding_column(df),
            "route_col": detect_route_column(df),
        }
    except Exception:
        return {key: (None, 0.0, "none") for key in _SCHEMA_KEYS}


def resolve_schema(
    schema: Dict[str, Tuple[Optional[str], float, str]],
) -> Dict[str, Optional[str]]:
    """Flatten a schema dict to plain ``{key: column_name_or_None}`` for the
    feature modules that only need the resolved name."""
    resolved: Dict[str, Optional[str]] = {}
    for key in _SCHEMA_KEYS:
        entry = schema.get(key) if schema else None
        resolved[key] = entry[0] if entry else None
    return resolved


# Human-readable labels for schema warnings.
_REQUIRED_FOR_NICHE = {
    "customer_col": "customer / account name",
    "sku_col": "product / SKU",
}
_OPTIONAL_FOR_NICHE = {
    "qty_col": "quantity",
    "date_col": "transaction date",
    "outstanding_col": "outstanding / receivable amount",
    "route_col": "route / salesman",
}


def build_schema_warnings(
    schema: Dict[str, Tuple[Optional[str], float, str]],
) -> list:
    """
    Produce clear, user-facing warnings about which distributor columns could
    not be detected above the confidence threshold. Required columns
    (customer, SKU) and the feature-gating optional columns are reported so the
    frontend never silently shows a broken/empty downstream feature.
    """
    warnings: list = []
    if not schema:
        return ["Could not analyze the dataset's columns for key business fields."]

    for key, label in _REQUIRED_FOR_NICHE.items():
        col, conf, _mode = schema.get(key, (None, 0.0, "none"))
        if col is None:
            warnings.append(
                f"No {label} column detected. Customer-level "
                f"insights (churn, segmentation) cannot be generated for this file."
            )

    # Optional columns: note which downstream feature is skipped.
    feature_for = {
        "outstanding_col": "Receivables / payments-due analysis is skipped",
        "date_col": "Churn timing and dead-stock recency cannot be computed",
        "qty_col": "Quantity-based movement checks are skipped",
    }
    for key in ("date_col", "outstanding_col", "qty_col"):
        col, _conf, _mode = schema.get(key, (None, 0.0, "none"))
        if col is None and key in feature_for:
            label = _OPTIONAL_FOR_NICHE.get(key, key)
            warnings.append(f"No {label} column detected. {feature_for[key]}.")

    return warnings


# ─────────────────────────────────────────────────────────────────────────────
# Indian-currency formatting helpers (shared by the distributor features)
# ─────────────────────────────────────────────────────────────────────────────

def format_inr(amount) -> str:
    """Format a number as ₹ with Indian digit grouping (e.g. ₹12,34,567)."""
    try:
        value = float(amount)
    except (TypeError, ValueError):
        return "₹0"
    negative = value < 0
    whole = str(int(round(abs(value))))
    if len(whole) > 3:
        last3 = whole[-3:]
        rest = whole[:-3]
        rest = re.sub(r"(?<=\d)(?=(\d\d)+$)", ",", rest)
        whole = f"{rest},{last3}"
    return f"{'-' if negative else ''}₹{whole}"


def format_inr_lakh(amount) -> str:
    """Format a number using lakh / crore shorthand familiar to Indian SMBs."""
    try:
        value = float(amount)
    except (TypeError, ValueError):
        return "₹0"
    abs_value = abs(value)
    sign = "-" if value < 0 else ""
    if abs_value >= 1e7:
        return f"{sign}₹{abs_value / 1e7:.1f} Cr"
    if abs_value >= 1e5:
        return f"{sign}₹{abs_value / 1e5:.1f}L"
    return format_inr(value)
