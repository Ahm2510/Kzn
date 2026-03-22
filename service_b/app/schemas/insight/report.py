from typing import List
from pydantic import BaseModel
from .metrics import MetricDelta
from .insights import Insight


class InsightReport(BaseModel):
    summary: str
    metric_deltas: List[MetricDelta]
    insights: List[Insight]
