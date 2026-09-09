"""
Operator Action List (V1 — Additive, distribution niche)

Distributor-owners are operators, not analysts. They want a to-do list, not a BI
dashboard. This module assembles a short, imperative action list by pulling the
single highest-priority item from each distributor signal:

  * customer churn risk   (customer_churn_risk.py)
  * dead / slow-moving stock (inventory_health.py)
  * receivables / payments due (receivables_risk.py)

Each item is phrased as a direct instruction generated dynamically from the real
numbers. The module is additive and defensive — it never raises and returns an
empty list when no signal has anything actionable to say.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.services.insight_engine.entity_detector import format_inr_lakh


class ActionItem(BaseModel):
    category: str          # "churn" | "dead_stock" | "receivables"
    priority: int          # 1 = highest
    headline: str          # imperative, operator-facing sentence
    detail: Optional[str] = None


def _churn_item(churn) -> Optional[ActionItem]:
    """Top churn action: which quiet accounts to call this week."""
    if churn is None:
        return None
    has_at_risk = getattr(churn, "has_at_risk", None)
    headline = getattr(churn, "headline_action", None)
    if not has_at_risk or not headline:
        return None
    customers = getattr(churn, "customers", []) or []
    names = ", ".join(c.customer for c in customers if c.risk in ("churned", "at_risk"))[:200]
    detail = f"Quiet accounts: {names}." if names else None
    return ActionItem(category="churn", priority=1, headline=headline, detail=detail)


def _receivables_item(receivables) -> Optional[ActionItem]:
    """Top collections action: which overdue customers to chase."""
    if receivables is None:
        return None
    total = getattr(receivables, "total_outstanding", 0.0) or 0.0
    headline = getattr(receivables, "headline_action", None)
    if total <= 0 or not headline:
        return None
    customers = getattr(receivables, "customers", []) or []
    names = ", ".join(c.customer for c in customers[:5])[:200]
    detail = f"Largest balances: {names}." if names else None
    return ActionItem(category="receivables", priority=2, headline=headline, detail=detail)


def _dead_stock_item(inventory_health) -> Optional[ActionItem]:
    """Top inventory action: clear the capital tied up in dead stock."""
    if inventory_health is None:
        return None
    count = getattr(inventory_health, "dead_stock_count", None)
    value = getattr(inventory_health, "total_dead_stock_value", None)
    window = getattr(inventory_health, "dead_stock_window_days", None) or 60
    if not count:
        return None
    if value is not None and value > 0:
        headline = (
            f"{format_inr_lakh(value)} is sitting in {count} SKU(s) that haven't moved in "
            f"{window}+ days — run a clearance push or stop reordering them."
        )
    else:
        headline = (
            f"{count} SKU(s) haven't moved in {window}+ days — review them for a clearance "
            f"push or discontinued reorders."
        )
    skus = getattr(inventory_health, "dead_stock_skus", None) or []
    names = ", ".join(str(s.get("sku")) for s in skus[:5])[:200]
    detail = f"Idle SKUs: {names}." if names else None
    return ActionItem(category="dead_stock", priority=3, headline=headline, detail=detail)


def build_action_list(
    churn=None,
    inventory_health=None,
    receivables=None,
) -> List[ActionItem]:
    """
    Assemble the operator action list from the three distributor signals.

    Accepts the result objects (or anything attribute-compatible) from
    ``compute_customer_churn_risk``, ``compute_inventory_health_score`` and
    ``compute_receivables_risk``. Returns a priority-sorted list; empty when no
    signal is actionable. Never raises.
    """
    try:
        items: List[ActionItem] = []
        for builder, arg in (
            (_churn_item, churn),
            (_receivables_item, receivables),
            (_dead_stock_item, inventory_health),
        ):
            try:
                item = builder(arg)
                if item is not None:
                    items.append(item)
            except Exception:
                continue
        items.sort(key=lambda i: i.priority)
        return items
    except Exception:
        return []
