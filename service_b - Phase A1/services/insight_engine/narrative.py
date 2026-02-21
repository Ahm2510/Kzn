from typing import List
from schemas.insight.metrics import MetricDelta
from schemas.insight.insights import Insight


def generate_summary(
    metric_deltas: List[MetricDelta],
    insights: List[Insight],
) -> str:
    if not insights:
        return "No significant changes detected in the selected period."

    main = insights[0]
    return f"{main.title}. {main.description}."
