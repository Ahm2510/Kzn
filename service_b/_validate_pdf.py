import tempfile, os
from app.services.report_renderers.pdf_report import render_pdf
from app.schemas.insight.report import InsightReport
from app.schemas.insight.metrics import MetricDelta
from app.schemas.insight.insights import Insight

# Simulate exactly what the rules engine produces
report = InsightReport(
    summary="Revenue summary. Total revenue is $2,954,160.31.",
    metric_deltas=[
        MetricDelta(
            name="revenue",
            current=2954160.31,
            baseline=0.0,
            absolute_change=2954160.31,
            percent_change=0.0,
        )
    ],
    insights=[
        Insight(
            code="REVENUE_VOLATILITY",
            severity="high",
            title="Revenue volatility assessment",
            description=(
                "Coefficient of variation is 27.04, indicating very high revenue volatility. "
                "Standard deviation: $534.72, mean: $19.78."
            ),
            affected_metric="revenue",
            driver="CV of 27.04 computed from 149,367 records (std=$534.72, mean=$19.78)",
            implication="High volatility creates cash flow unpredictability and makes forecasting unreliable.",
            action_direction="Identify outlier transactions driving variance; consider smoothing strategies.",
            confidence="HIGH",
            confidence_basis="CV computed from 149,367 records; statistically robust sample",
        ),
        Insight(
            code="PRODUCT_CONCENTRATION",
            severity="low",
            title="Product revenue concentration",
            description="Top 3 products (A, B, C) generate 4.0% of total revenue.",
            affected_metric="revenue",
            driver="Top 3 of 3,642 products contribute $118,166.41 of $2,954,160.31 total (4.0%)",
            implication="Revenue is diversified across products, reducing concentration risk.",
            action_direction="Maintain portfolio balance; invest in emerging product opportunities.",
            confidence="HIGH",
            confidence_basis="Deterministic revenue aggregation across 3,642 products",
        ),
    ],
)

business_insights = {
    "executive_takeaways": [
        "Concentration risk: top 10% accounts for 61% of revenue — creates high dependency.",
        "Volatility anomaly: CV=27.04 indicates high revenue unpredictability vs baseline.",
    ],
    "scope": {"analyzed": ["revenue"], "not_analyzed": ["costs"]},
    "stability": {
        "category": "highly_volatile",
        "coefficient_of_variation": 27.04,
        "description": "Anomaly: high CV of 27.04 indicates extreme volatility.",
        "driver": "Volatility anomaly: significant dispersion in transaction values (CV=27.04) indicates revenue risk.",
        "implication": "High volatility creates unpredictability in cash flow.",
        "action_direction": "Identify structural drivers of volatility and implement variance-reduction strategies.",
        "confidence": "high",
        "confidence_basis": "full dataset; no sampling",
    },
}

fd = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
fd.close()
render_pdf(report, fd.name, business_insights=business_insights)

with open(fd.name, "rb") as f:
    data = f.read()
os.remove(fd.name)

s = data.decode("latin-1", errors="ignore")

checks = {
    # Fix 1: volatility body text
    "volatility_body_plain": "Revenue swings dramatically across transactions" in s,
    "volatility_body_no_stat": "Coefficient of variation is" not in s and "Standard deviation:" not in s,
    # Fix 2: product concentration driver
    "prod_driver_plain": "Revenue is spread across 3,642 products" in s and "4.0% of total revenue" in s,
    "prod_driver_no_generic": "A small slice of transactions" not in s,
    # Fix 3: stability description plain
    "stability_desc_plain": "Revenue swings are extreme" in s,
    "stability_desc_no_cv": "CV of 27.04 indicates extreme" not in s,
    # Fix 4: no dash for transactions
    "no_transactions_dash": "Total Transactions: \x97" not in s and "Total Transactions:</b> \x97" not in s,
    # Takeaway plain english
    "takeaway_plain": "Revenue volatility is extremely high" in s,
    # No time in date
    "date_only": "Generated on" in s and " at " not in s,
    # No Additional Notes
    "no_additional_notes": "Additional Notes" not in s,
}

all_pass = all(checks.values())
print("ALL PASS:", all_pass)
for k, v in checks.items():
    status = "OK" if v else "FAIL"
    print(f"  [{status}] {k}")
