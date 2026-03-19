from typing import List, Optional
from pydantic import BaseModel


class Insight(BaseModel):
    code: str  # e.g. REVENUE_DROP
    severity: str  # low / medium / high
    title: str
    description: str
    affected_metric: str
    driver: Optional[str] = None
    implication: Optional[str] = None
    action_direction: Optional[str] = None
    confidence: Optional[str] = None
    confidence_basis: Optional[str] = None


class InsightBundle(BaseModel):
    insights: List[Insight]
