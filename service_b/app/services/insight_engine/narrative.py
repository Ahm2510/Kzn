from typing import List
from app.schemas.insight.metrics import MetricDelta
from app.schemas.insight.insights import Insight


def generate_summary(
    metric_deltas: List[MetricDelta],
    insights: List[Insight],
) -> str:
    if not insights:
        return "No significant changes detected in the selected period."

    # Lead with primary insight
    main = insights[0]
    parts = [f"{main.title}. {main.description}"]

    # Add high-severity findings
    high_severity = [i for i in insights[1:] if i.severity == "high"]
    for ins in high_severity[:2]:
        parts.append(ins.description)

    # Add count of total findings
    if len(insights) > 1:
        parts.append(f"{len(insights)} insights generated in total.")

    return " ".join(parts)
