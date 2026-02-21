"""Endpoint testing script for audit Phase 3"""
import requests
import io
import os

BASE_URL = "http://127.0.0.1:8000"

def test_valid_csv():
    """Test 1: Valid CSV with revenue column"""
    csv_data = "date,revenue,cost\n2024-01,1000,500\n2024-02,1200,600\n2024-03,1100,550\n"
    files = {"current_file": ("test.csv", io.StringIO(csv_data), "text/csv")}
    r = requests.post(f"{BASE_URL}/v1/analyze", files=files)
    print(f"Valid CSV: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"  - Has report: {'report' in data}")
        print(f"  - Has pdf_path: {'pdf_path' in data}")
        print(f"  - Has business_insights: {'business_insights' in data}")
        return True
    else:
        print(f"  Error: {r.text[:200]}")
        return False

def test_malformed_csv():
    """Test 2: Malformed CSV"""
    csv_data = "this is not,a valid\ncsv file with \"unmatched quotes"
    files = {"current_file": ("bad.csv", io.StringIO(csv_data), "text/csv")}
    r = requests.post(f"{BASE_URL}/v1/analyze", files=files)
    print(f"Malformed CSV: {r.status_code}")
    print(f"  - Returns 400: {r.status_code == 400}")
    return r.status_code == 400

def test_missing_revenue():
    """Test 3: Missing revenue column"""
    csv_data = "date,cost,quantity\n2024-01,500,10\n2024-02,600,12\n"
    files = {"current_file": ("no_revenue.csv", io.StringIO(csv_data), "text/csv")}
    r = requests.post(f"{BASE_URL}/v1/analyze", files=files)
    print(f"Missing revenue: {r.status_code}")
    print(f"  - Returns 400: {r.status_code == 400}")
    return r.status_code == 400

def test_small_dataset():
    """Test 4: Small dataset (3 rows)"""
    csv_data = "date,revenue\n2024-01,1000\n2024-02,1200\n2024-03,1100\n"
    files = {"current_file": ("small.csv", io.StringIO(csv_data), "text/csv")}
    r = requests.post(f"{BASE_URL}/v1/analyze", files=files)
    print(f"Small dataset: {r.status_code}")
    return r.status_code == 200

def test_with_baseline():
    """Test 5: With baseline CSV"""
    current = "date,revenue\n2024-01,1000\n2024-02,1200\n2024-03,1100\n"
    baseline = "date,revenue\n2023-01,900\n2023-02,950\n2023-03,1000\n"
    files = {
        "current_file": ("current.csv", io.StringIO(current), "text/csv"),
        "baseline_file": ("baseline.csv", io.StringIO(baseline), "text/csv"),
    }
    r = requests.post(f"{BASE_URL}/v1/analyze", files=files)
    print(f"With baseline: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        report = data.get("report", {})
        deltas = report.get("metric_deltas", [])
        print(f"  - Has metric_deltas: {len(deltas) > 0}")
        if deltas:
            print(f"  - Delta has percent_change: {'percent_change' in deltas[0]}")
    return r.status_code == 200

def test_empty_file():
    """Test 6: Empty file"""
    csv_data = ""
    files = {"current_file": ("empty.csv", io.StringIO(csv_data), "text/csv")}
    r = requests.post(f"{BASE_URL}/v1/analyze", files=files)
    print(f"Empty file: {r.status_code}")
    print(f"  - Returns 400: {r.status_code == 400}")
    return r.status_code == 400

if __name__ == "__main__":
    print("=" * 50)
    print("ENDPOINT TESTING - PHASE 3")
    print("=" * 50)
    
    results = []
    results.append(("Valid CSV", test_valid_csv()))
    results.append(("Malformed CSV", test_malformed_csv()))
    results.append(("Missing Revenue", test_missing_revenue()))
    results.append(("Small Dataset", test_small_dataset()))
    results.append(("With Baseline", test_with_baseline()))
    results.append(("Empty File", test_empty_file()))
    
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
    
    all_passed = all(r[1] for r in results)
    print(f"\nOverall: {'ALL PASS' if all_passed else 'SOME FAILED'}")
