from typing import List
from pydantic import BaseModel


class Insight(BaseModel):
    code: str  # e.g. REVENUE_DROP
    severity: str  # low / medium / high
    title: str
    description: str
    affected_metric: str


class InsightBundle(BaseModel):
    insights: List[Insight]
