from schemas.insight.insights import Insight


def revenue_drop_rule(metric_delta) -> Insight | None:
    if metric_delta.name == "revenue" and metric_delta.percent_change < -10:
        return Insight(
            code="REVENUE_DROP",
            severity="high",
            title="Significant revenue drop detected",
            description=f"Revenue dropped by {abs(metric_delta.percent_change):.1f}%",
            affected_metric="revenue",
        )
    return None
