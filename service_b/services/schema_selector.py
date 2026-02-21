import pandas as pd
from typing import Optional


def _normalize_schema(metric_schema: Optional[str]) -> Optional[str]:
    """Normalize the metric_schema hint.

    Returns a lowercased, trimmed value or None if not provided/empty.
    """
    if metric_schema is None:
        return None
    value = metric_schema.strip()
    if not value:
        return None
    return value.lower()


def select_metric_column(df: pd.DataFrame, metric_schema: Optional[str]) -> Optional[str]:
    """Resolve a specific metric column based on an optional schema hint.

    This helper is intentionally narrow in scope:
    - It never mutates the DataFrame.
    - It never calls into the core insight engine.
    - It only inspects existing columns and dtypes.

    Returns:
        The selected column name, or None to indicate the caller should
        fall back to existing revenue auto-detection.

    Raises:
        ValueError: If metric_schema is invalid or cannot be satisfied
        (e.g. custom column missing or not numeric).
    """
    normalized = _normalize_schema(metric_schema)

    # Default / auto behaviour: let existing revenue detection run unchanged.
    if normalized is None or normalized == "auto":
        return None

    # Explicit revenue selection still defers to existing revenue detector.
    if normalized == "revenue":
        return None

    columns_lower = {col.lower().strip(): col for col in df.columns}
    if not columns_lower:
        raise ValueError("The dataset does not contain any columns to analyze.")

    # Custom column: custom:<column_name>
    if normalized.startswith("custom:"):
        raw_name = metric_schema.split(":", 1)[1].strip() if metric_schema else ""
        if not raw_name:
            raise ValueError(
                "Invalid metric_schema value. Expected 'custom:<column_name>'."
            )

        target_lower = raw_name.lower().strip()
        if target_lower not in columns_lower:
            raise ValueError(
                f"Requested custom metric column '{raw_name}' was not found in the dataset."
            )

        col_name = columns_lower[target_lower]
        if not pd.api.types.is_numeric_dtype(df[col_name]):
            raise ValueError(
                f"Requested custom metric column '{col_name}' must be numeric for analysis."
            )
        return col_name

    # Predefined non-revenue schemas
    if normalized == "cost":
        candidates = [
            "cost",
            "costs",
            "cogs",
            "cost_of_goods_sold",
            "expense",
            "expenses",
            "operating_cost",
            "operating_costs",
        ]
        metric_label = "cost"
    elif normalized == "quantity":
        candidates = [
            "quantity",
            "qty",
            "units",
            "unit_count",
            "volume",
        ]
        metric_label = "quantity"
    else:
        raise ValueError(
            "Invalid metric_schema value. Allowed values are 'auto', 'revenue', "
            "'cost', 'quantity', or 'custom:<column_name>'."
        )

    # Try to find a matching numeric column for the requested schema.
    for candidate in candidates:
        key = candidate.lower().strip()
        if key in columns_lower:
            col_name = columns_lower[key]
            if not pd.api.types.is_numeric_dtype(df[col_name]):
                # Skip non-numeric matches and continue searching.
                continue
            return col_name

    raise ValueError(
        f"No {metric_label}-like numeric column was found for metric_schema='{metric_schema}'. "
        "Please ensure the dataset contains an appropriate numeric column."
    )
