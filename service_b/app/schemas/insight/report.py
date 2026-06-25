from typing import List, Optional
from pydantic import BaseModel
from .metrics import MetricDelta
from .insights import Insight


class InsightReport(BaseModel):
    summary: str
    metric_deltas: List[MetricDelta]
    insights: List[Insight]
    total_transactions: Optional[int] = None
    products_analyzed: Optional[int] = None
