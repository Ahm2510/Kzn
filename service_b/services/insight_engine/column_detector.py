# services/insight_engine/column_detector.py
"""
V1.75 Semantic Column Detection

Detects revenue-like columns using semantic matching with confidence thresholds.
Maintains backward compatibility with V1.5 exact matching.
"""

from typing import Optional, Tuple
import pandas as pd


# Revenue-like column names with confidence scores
# Higher score = more confident it represents revenue
REVENUE_SYNONYMS = {
    # Exact matches (V1.5 backward compatibility) - highest confidence
    "revenue": 1.0,
    
    # High confidence semantic matches
    "total_sales": 0.95,
    "sales": 0.90,
    "turnover": 0.90,
    "gross_revenue": 0.95,
    "net_revenue": 0.95,
    "total_revenue": 0.98,
    "sales_revenue": 0.95,
    "income": 0.85,
    "total_income": 0.90,
    "earnings": 0.85,
    
    # Revenue-adjacent (commonly used in ecommerce/transactional datasets)
    "amount": 0.82,
    "total_amount": 0.88,
    "total": 0.80,
    "total_price": 0.90,
    "order_value": 0.92,
    "gmv": 0.88,
    "value": 0.55,
    "total_value": 0.82,
    
    # Lower confidence - context dependent
    "gmv_value": 0.85,
    "booking_amount": 0.82,
    "transaction_value": 0.85,
}

# Minimum confidence threshold for semantic matching
CONFIDENCE_THRESHOLD = 0.80


def detect_revenue_column(
    df: pd.DataFrame,
    strict_mode: bool = False,
) -> Tuple[Optional[str], float, str]:
    """
    Detect revenue-like column in a DataFrame.
    
    Args:
        df: DataFrame to analyze
        strict_mode: If True, only accept exact "revenue" match (V1.5 behavior)
    
    Returns:
        Tuple of (column_name, confidence, detection_mode)
        - column_name: The detected column name, or None if not found
        - confidence: Confidence score (0.0 to 1.0)
        - detection_mode: "exact" for V1.5 match, "semantic" for V1.75 inference
    """
    columns_lower = {col.lower().strip(): col for col in df.columns}
    
    # V1.5 Backward Compatibility: Check for exact "revenue" match first
    if "revenue" in columns_lower:
        return columns_lower["revenue"], 1.0, "exact"
    
    # If strict mode, don't attempt semantic matching
    if strict_mode:
        return None, 0.0, "none"
    
    # V1.75 Semantic Matching: Find best matching column
    best_match: Optional[str] = None
    best_confidence: float = 0.0
    
    for col_lower, col_original in columns_lower.items():
        if col_lower in REVENUE_SYNONYMS:
            confidence = REVENUE_SYNONYMS[col_lower]
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = col_original
    
    # Only return if confidence meets threshold
    if best_match and best_confidence >= CONFIDENCE_THRESHOLD:
        return best_match, best_confidence, "semantic"
    
    return None, best_confidence, "none"


def detect_revenue_columns_pair(
    current_df: pd.DataFrame,
    baseline_df: Optional[pd.DataFrame],
) -> Tuple[Optional[str], Optional[str], float, float, str]:
    """
    Detect revenue columns in both current and baseline datasets.
    
    For comparative mode, both datasets must have matching revenue-like columns.
    
    Returns:
        Tuple of (current_col, baseline_col, current_conf, baseline_conf, mode)
    """
    current_col, current_conf, current_mode = detect_revenue_column(current_df)
    
    if baseline_df is None:
        return current_col, None, current_conf, 0.0, current_mode
    
    baseline_col, baseline_conf, baseline_mode = detect_revenue_column(baseline_df)
    
    # Determine overall mode
    if current_mode == "exact" and baseline_mode == "exact":
        mode = "exact"
    elif current_mode == "none" or baseline_mode == "none":
        mode = "none"
    else:
        mode = "semantic"
    
    return current_col, baseline_col, current_conf, baseline_conf, mode


def validate_revenue_column(
    df: pd.DataFrame,
    column: str,
) -> bool:
    """
    Validate that a column contains numeric revenue-like data.
    """
    if column not in df.columns:
        return False
    
    # Check if column is numeric
    try:
        pd.to_numeric(df[column], errors='raise')
        return True
    except (ValueError, TypeError):
        return False
