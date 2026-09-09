"""
Period-over-period delta computation.
Core differentiator: shows what changed between reports.
"""
from typing import Dict, Any, List, Optional, Tuple
import json


def compute_deltas(current_summary: Dict, previous_summary: Dict) -> List[Dict[str, Any]]:
    """
    Compute deltas between current and previous summary.
    Returns a list of delta objects with direction and description.
    """
    deltas = []
    
    # Define metric configurations: (key, label, higher_is_better, format_fn)
    metric_configs = [
        ("receivables_risk_score", "Receivables Risk", False, lambda v: f"₹{v:,.0f}" if v else "N/A"),
        ("concentration_hhi", "Concentration Risk (HHI)", False, lambda v: f"{v:,.0f}" if v else "N/A"),
        ("revenue_stability_score", "Revenue Stability", True, lambda v: f"{v:.0f}/100" if v else "N/A"),
        ("margin_pct", "Margin %", True, lambda v: f"{v:.1f}%" if v else "N/A"),
        ("quiet_account_count", "Quiet Accounts", False, lambda v: f"{int(v)}" if v else "0"),
        ("inventory_health_score", "Inventory Health", True, lambda v: f"{v:.0f}/100" if v else "N/A"),
        ("alert_count", "Alert Count", False, lambda v: f"{int(v)}" if v else "0"),
    ]
    
    for key, label, higher_is_better, format_fn in metric_configs:
        current_val = current_summary.get(key)
        previous_val = previous_summary.get(key)
        
        # Skip if either value is missing
        if current_val is None or previous_val is None:
            continue
        
        # Determine direction
        if current_val > previous_val:
            direction = "improved" if higher_is_better else "worsened"
        elif current_val < previous_val:
            direction = "worsened" if higher_is_better else "improved"
        else:
            direction = "unchanged"
        
        # Generate plain-language description
        description = _generate_delta_description(
            label, current_val, previous_val, direction, format_fn
        )
        
        deltas.append({
            "metric": label,
            "current": current_val,
            "previous": previous_val,
            "direction": direction,
            "description": description,
            "format_fn": format_fn,
        })
    
    # Sort: worsened first, then improved, then unchanged
    priority_order = {"worsened": 0, "improved": 1, "unchanged": 2}
    deltas.sort(key=lambda d: priority_order.get(d["direction"], 2))
    
    return deltas


def _generate_delta_description(
    label: str,
    current: float,
    previous: float,
    direction: str,
    format_fn
) -> str:
    """Generate a plain-language description of the change."""
    current_str = format_fn(current)
    previous_str = format_fn(previous)
    
    if direction == "unchanged":
        return f"{label} unchanged at {current_str}."
    
    # Calculate percent change for numeric metrics
    if previous != 0:
        pct_change = ((current - previous) / abs(previous)) * 100
        if abs(pct_change) < 1:
            change_str = "minimal change"
        else:
            change_str = f"{abs(pct_change):.0f}% {'increase' if pct_change > 0 else 'decrease'}"
    else:
        change_str = "change from zero"
    
    if direction == "worsened":
        return f"{label} worsened: now {current_str}, up from {previous_str} ({change_str})."
    else:
        return f"{label} improved: now {current_str}, up from {previous_str} ({change_str})."


def compute_client_risk_trend(firm_id: int, client_id: int) -> str:
    """
    Compute a one-word risk trend indicator for a client based on their two most recent reports.
    Returns: "Improving", "Worsening", "Stable", or "First report"
    """
    from db import get_client_last_two_reports
    
    current, previous = get_client_last_two_reports(firm_id, client_id)
    
    if not current:
        return "First report"
    
    if not previous:
        return "First report"
    
    # Parse summary JSON
    current_summary = json.loads(current["summary_json"])
    previous_summary = json.loads(previous["summary_json"])
    
    # Compute deltas
    deltas = compute_deltas(current_summary, previous_summary)
    
    # Count worsened vs improved
    worsened_count = sum(1 for d in deltas if d["direction"] == "worsened")
    improved_count = sum(1 for d in deltas if d["direction"] == "improved")
    
    if worsened_count > improved_count:
        return "Worsening"
    elif improved_count > worsened_count:
        return "Improving"
    else:
        return "Stable"
