"""Phase 4: Business Logic Validation - Verify insight structure"""
import requests
import io
import json

BASE_URL = "http://127.0.0.1:8000"

def test_insight_structure():
    """Verify insights have required business structure"""
    # Create test data with revenue decline to trigger insights
    current = "date,revenue,cost\n2024-01,800,500\n2024-02,750,480\n2024-03,700,450\n"
    baseline = "date,revenue,cost\n2023-01,1000,500\n2023-02,1050,520\n2023-03,1100,550\n"
    
    files = {
        "current_file": ("current.csv", io.StringIO(current), "text/csv"),
        "baseline_file": ("baseline.csv", io.StringIO(baseline), "text/csv"),
    }
    
    r = requests.post(f"{BASE_URL}/v1/analyze", files=files)
    if r.status_code != 200:
        print(f"Request failed: {r.status_code}")
        return False
    
    data = r.json()
    report = data.get("report", {})
    business_insights = data.get("business_insights", {})
    
    print("=" * 60)
    print("BUSINESS LOGIC VALIDATION")
    print("=" * 60)
    
    results = []
    
    # 1. Check report has summary
    has_summary = bool(report.get("summary"))
    print(f"\n1. Has Summary: {has_summary}")
    if has_summary:
        print(f"   Summary: {report['summary'][:100]}...")
    results.append(("Has Summary", has_summary))
    
    # 2. Check metric deltas exist
    deltas = report.get("metric_deltas", [])
    has_deltas = len(deltas) > 0
    print(f"\n2. Has Metric Deltas: {has_deltas}")
    if deltas:
        d = deltas[0]
        print(f"   - name: {d.get('name')}")
        print(f"   - current_value: {d.get('current_value')}")
        print(f"   - baseline_value: {d.get('baseline_value')}")
        print(f"   - absolute_change: {d.get('absolute_change')}")
        print(f"   - percent_change: {d.get('percent_change')}")
    results.append(("Has Metric Deltas", has_deltas))
    
    # 3. Check insights exist
    insights = report.get("insights", [])
    has_insights = len(insights) > 0
    print(f"\n3. Has Insights: {has_insights}")
    if insights:
        for i, ins in enumerate(insights):
            print(f"   Insight {i+1}:")
            print(f"   - code: {ins.get('code')}")
            print(f"   - severity: {ins.get('severity')}")
            print(f"   - title: {ins.get('title')}")
            print(f"   - description: {ins.get('description')[:80]}..." if ins.get('description') else "   - description: None")
    results.append(("Has Insights", has_insights))
    
    # 4. Check business insights layer
    print(f"\n4. Business Insights Layer:")
    
    # 4a. Trend insight with implication/action
    trend = business_insights.get("trend") if business_insights else None
    has_trend = trend is not None
    print(f"   4a. Has Trend: {has_trend}")
    if trend:
        print(f"       - direction: {trend.get('direction')}")
        print(f"       - description: {trend.get('description')}")
        print(f"       - confidence: {trend.get('confidence')}")
        print(f"       - implication: {trend.get('implication', 'N/A')[:60]}..." if trend.get('implication') else "       - implication: N/A")
        print(f"       - action_direction: {trend.get('action_direction', 'N/A')[:60]}..." if trend.get('action_direction') else "       - action_direction: N/A")
    results.append(("Has Trend Insight", has_trend))
    
    # 4b. Stability insight
    stability = business_insights.get("stability") if business_insights else None
    has_stability = stability is not None
    print(f"   4b. Has Stability: {has_stability}")
    if stability:
        print(f"       - level: {stability.get('level')}")
        print(f"       - coefficient_of_variation: {stability.get('coefficient_of_variation')}")
        print(f"       - risk_category: {stability.get('risk_category', 'N/A')}")
    results.append(("Has Stability Insight", has_stability))
    
    # 4c. Efficiency insight
    efficiency = business_insights.get("efficiency") if business_insights else None
    has_efficiency = efficiency is not None
    print(f"   4c. Has Efficiency: {has_efficiency}")
    if efficiency:
        print(f"       - signal: {efficiency.get('signal')}")
        print(f"       - description: {efficiency.get('description')}")
    results.append(("Has Efficiency Insight", has_efficiency))
    
    # 4d. Concentration risk
    concentration = business_insights.get("concentration") if business_insights else None
    has_concentration = concentration is not None
    print(f"   4d. Has Concentration: {has_concentration}")
    if concentration:
        print(f"       - risk_level: {concentration.get('risk_level')}")
        print(f"       - top_contributor_pct: {concentration.get('top_contributor_pct')}")
    results.append(("Has Concentration Risk", has_concentration))
    
    # 4e. Executive summary
    exec_summary = business_insights.get("executive_summary") if business_insights else None
    has_exec_summary = exec_summary is not None and len(str(exec_summary)) > 50
    print(f"   4e. Has Executive Summary: {has_exec_summary}")
    if exec_summary:
        print(f"       {exec_summary[:150]}...")
    results.append(("Has Executive Summary", has_exec_summary))
    
    # 5. Verify insights are NOT purely numerical
    print(f"\n5. Insight Quality Check:")
    purely_numerical = True
    if insights:
        for ins in insights:
            desc = ins.get("description", "")
            # Check if description contains words (not just numbers)
            has_words = any(c.isalpha() for c in desc)
            if has_words:
                purely_numerical = False
                break
    
    not_purely_numerical = not purely_numerical or len(insights) == 0
    print(f"   Insights contain narrative text: {not_purely_numerical}")
    results.append(("Not Purely Numerical", not_purely_numerical))
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    all_pass = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  {name}: {status}")
    
    print(f"\nOVERALL: {'PASS' if all_pass else 'FAIL'}")
    return all_pass

if __name__ == "__main__":
    test_insight_structure()
