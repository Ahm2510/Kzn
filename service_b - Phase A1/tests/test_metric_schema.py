"""Tests for optional metric_schema behavior on /v1/analyze.

These tests are intentionally minimal and additive. They verify that:
- Default behavior (no metric_schema) is unchanged and still revenue-based.
- metric_schema="custom:revenue" behaves identically to the default path
  with respect to core metric deltas.
- Invalid custom schema values surface as HTTP 400 without stack traces.
- metric_schema="cost" leaves the core report revenue-based while the
  BusinessInsights overlay uses the cost column for stability-style metrics.
"""

import io

import pytest


@pytest.mark.parametrize("path", ["/v1/analyze"])
def test_default_path_revenue_and_trend(client, path):
    """Default path (no metric_schema) remains revenue-based.

    Upload a normal CSV with a revenue column (and baseline) and assert that:
    - The first metric delta is still named "revenue".
    - BusinessInsights.trend is present (requires baseline).
    """
    current_csv = (
        "date,revenue,cost\n"
        "2024-01,1000,500\n"
        "2024-02,1200,600\n"
        "2024-03,1100,550\n"
    )
    baseline_csv = (
        "date,revenue,cost\n"
        "2023-01,800,400\n"
        "2023-02,900,450\n"
        "2023-03,950,475\n"
    )

    files = {
        "current_file": ("current.csv", current_csv.encode("utf-8"), "text/csv"),
        "baseline_file": ("baseline.csv", baseline_csv.encode("utf-8"), "text/csv"),
    }

    response = client.post(path, files=files)
    assert response.status_code == 200

    payload = response.json()
    report = payload["report"]
    deltas = report.get("metric_deltas", [])
    assert deltas, "Expected at least one metric delta"
    first_delta = deltas[0]
    assert first_delta["name"] == "revenue"

    business_insights = payload.get("business_insights")
    assert business_insights is not None
    # With baseline present and non-zero, a trend insight should exist
    assert business_insights.get("trend") is not None


def test_custom_revenue_matches_default_metrics(client):
    """metric_schema="custom:revenue" behaves like the default path.

    The core report metric deltas must be identical to the default call.
    """
    current_csv = (
        "date,revenue,cost\n"
        "2024-01,1000,500\n"
        "2024-02,1200,600\n"
        "2024-03,1100,550\n"
    )
    baseline_csv = (
        "date,revenue,cost\n"
        "2023-01,800,400\n"
        "2023-02,900,450\n"
        "2023-03,950,475\n"
    )

    files_default = {
        "current_file": ("current.csv", current_csv.encode("utf-8"), "text/csv"),
        "baseline_file": ("baseline.csv", baseline_csv.encode("utf-8"), "text/csv"),
    }
    resp_default = client.post("/v1/analyze", files=files_default)
    assert resp_default.status_code == 200
    delta_default = resp_default.json()["report"]["metric_deltas"][0]

    files_custom = {
        "current_file": ("current.csv", current_csv.encode("utf-8"), "text/csv"),
        "baseline_file": ("baseline.csv", baseline_csv.encode("utf-8"), "text/csv"),
    }
    data_custom = {"metric_schema": "custom:revenue"}
    resp_custom = client.post("/v1/analyze", files=files_custom, data=data_custom)
    assert resp_custom.status_code == 200
    delta_custom = resp_custom.json()["report"]["metric_deltas"][0]

    # All core metric values should be identical
    assert delta_custom["name"] == "revenue"
    assert delta_custom == delta_default


def test_custom_missing_column_returns_400(client):
    """metric_schema="custom:missing_col" should return HTTP 400.

    The error message should indicate that the custom column was not found.
    """
    current_csv = (
        "date,revenue,cost\n"
        "2024-01,1000,500\n"
        "2024-02,1200,600\n"
        "2024-03,1100,550\n"
    )

    files = {
        "current_file": ("current.csv", current_csv.encode("utf-8"), "text/csv"),
    }
    data = {"metric_schema": "custom:missing_col"}

    response = client.post("/v1/analyze", files=files, data=data)
    assert response.status_code == 400

    detail = response.json().get("detail", "").lower()
    assert "not found" in detail


def test_cost_schema_uses_cost_in_business_insights(client):
    """metric_schema="cost" keeps core report revenue-based but shifts BI column.

    Use a CSV where revenue is stable but cost is highly volatile. The core
    report should still be based on revenue, while the BusinessInsights
    stability classification should reflect the more volatile cost series
    when metric_schema="cost" is provided.
    """
    # Revenue is constant; cost is highly variable.
    current_csv = (
        "date,revenue,cost\n"
        "2024-01,1000,100\n"
        "2024-02,1000,5000\n"
        "2024-03,1000,200\n"
        "2024-04,1000,8000\n"
        "2024-05,1000,150\n"
        "2024-06,1000,3000\n"
        "2024-07,1000,50\n"
        "2024-08,1000,10000\n"
        "2024-09,1000,300\n"
        "2024-10,1000,6000\n"
    )

    # Default call (no metric_schema)
    files_default = {
        "current_file": ("current.csv", current_csv.encode("utf-8"), "text/csv"),
    }
    resp_default = client.post("/v1/analyze", files=files_default)
    assert resp_default.status_code == 200
    payload_default = resp_default.json()
    delta_default = payload_default["report"]["metric_deltas"][0]
    bi_default = payload_default.get("business_insights")

    # Cost-schema call
    files_cost = {
        "current_file": ("current.csv", current_csv.encode("utf-8"), "text/csv"),
    }
    data_cost = {"metric_schema": "cost"}
    resp_cost = client.post("/v1/analyze", files=files_cost, data=data_cost)
    assert resp_cost.status_code == 200
    payload_cost = resp_cost.json()
    delta_cost = payload_cost["report"]["metric_deltas"][0]
    bi_cost = payload_cost.get("business_insights")

    # Core report remains revenue-based and unchanged
    assert delta_default["name"] == "revenue"
    assert delta_cost["name"] == "revenue"
    assert delta_cost == delta_default

    # BusinessInsights should be present in both calls
    assert bi_default is not None
    assert bi_cost is not None

    # Stability classification should differ when using cost as the metric
    # because cost is much more volatile than revenue in this synthetic data.
    stability_default = bi_default.get("stability") or {}
    stability_cost = bi_cost.get("stability") or {}

    default_category = stability_default.get("category")
    cost_category = stability_cost.get("category")

    # Default stability should be at most moderately volatile for flat revenue
    # (often "stable" given constant values).
    assert default_category in {None, "stable", "moderately_volatile"}

    # Under cost schema, volatility should be higher, and classification
    # should differ from the default path.
    assert cost_category in {"moderately_volatile", "highly_volatile"}
    if default_category is not None:
        assert cost_category != default_category
