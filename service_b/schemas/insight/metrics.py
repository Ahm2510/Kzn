from pydantic import BaseModel


class MetricValue(BaseModel):
    name: str
    value: float


class MetricDelta(BaseModel):
    name: str
    current: float
    baseline: float
    absolute_change: float
    percent_change: float
