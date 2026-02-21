#!/usr/bin/env python3
"""
Service B V1.75 Test Suite Runner
Executes all tests from Phase C and generates results report.
"""

import requests
import json
import time
import os
from pathlib import Path
from datetime import datetime

API_BASE = "http://localhost:8000"
TEST_DATA_DIR = Path(__file__).parent / "test_data"
OUTPUTS_DIR = Path(__file__).parent / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)

results = []

def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}")

def save_result(test_name, response, expected_status, passed, notes=""):
    result = {
        "test": test_name,
        "status": response.status_code if response else "N/A",
        "expected_status": expected_status,
        "passed": passed,
        "notes": notes,
        "response": response.text[:2000] if response else "No response",
        "timestamp": datetime.now().isoformat()
    }
    results.append(result)
    
    # Save individual result
    filename = f"{test_name.replace(' ', '_').lower()}_{int(time.time())}.json"
    with open(OUTPUTS_DIR / filename, "w") as f:
        json.dump(result, f, indent=2)
    
    return result

def run_test(name, current_file, baseline_file=None, options=None, expected_status=200):
    """Run a single test case."""
    log(f"Running: {name}")
    
    default_options = {
        "normalize_columns": "true",
        "drop_duplicates": "true",
        "drop_missing": "true",
        "cap_outliers": "false"
    }
    if options:
        default_options.update(options)
    
    files = {"current_file": open(current_file, "rb")}
    if baseline_file:
        files["baseline_file"] = open(baseline_file, "rb")
    
    try:
        start = time.time()
        response = requests.post(
            f"{API_BASE}/v1/analyze",
            files=files,
            data=default_options,
            timeout=120
        )
        latency = (time.time() - start) * 1000
        
        passed = response.status_code == expected_status
        notes = f"Latency: {latency:.0f}ms"
        
        if passed:
            log(f"  ✅ PASS - Status {response.status_code} ({latency:.0f}ms)")
        else:
            log(f"  ❌ FAIL - Expected {expected_status}, got {response.status_code}")
            notes += f" | Expected {expected_status}"
        
        # Close files
        for f in files.values():
            f.close()
        
        return save_result(name, response, expected_status, passed, notes)
        
    except Exception as e:
        log(f"  ❌ ERROR - {str(e)}")
        for f in files.values():
            f.close()
        return save_result(name, None, expected_status, False, str(e))

def run_test_with_content(name, current_content, baseline_content=None, options=None, expected_status=200):
    """Run a test with in-memory CSV content."""
    log(f"Running: {name}")
    
    default_options = {
        "normalize_columns": "true",
        "drop_duplicates": "true",
        "drop_missing": "true",
        "cap_outliers": "false"
    }
    if options:
        default_options.update(options)
    
    files = {"current_file": ("test.csv", current_content, "text/csv")}
    if baseline_content:
        files["baseline_file"] = ("baseline.csv", baseline_content, "text/csv")
    
    try:
        start = time.time()
        response = requests.post(
            f"{API_BASE}/v1/analyze",
            files=files,
            data=default_options,
            timeout=120
        )
        latency = (time.time() - start) * 1000
        
        passed = response.status_code == expected_status
        notes = f"Latency: {latency:.0f}ms"
        
        if passed:
            log(f"  ✅ PASS - Status {response.status_code} ({latency:.0f}ms)")
        else:
            log(f"  ❌ FAIL - Expected {expected_status}, got {response.status_code}")
            notes += f" | Expected {expected_status}"
        
        return save_result(name, response, expected_status, passed, notes)
        
    except Exception as e:
        log(f"  ❌ ERROR - {str(e)}")
        return save_result(name, None, expected_status, False, str(e))


def main():
    log("=" * 60)
    log("Service B V1.75 Test Suite")
    log("=" * 60)
    
    # Pre-flight: Health check
    log("\n--- Pre-flight Checks ---")
    try:
        r = requests.get(f"{API_BASE}/health", timeout=5)
        log(f"Health check: {r.status_code} - {r.json()}")
        save_result("Health Check", r, 200, r.status_code == 200)
    except Exception as e:
        log(f"Health check FAILED: {e}")
        save_result("Health Check", None, 200, False, str(e))
        log("Aborting tests - server not reachable")
        return
    
    log("\n--- Test Suite ---\n")
    
    # Test A: Golden path (exact revenue match)
    run_test(
        "Test A: Golden Path",
        TEST_DATA_DIR / "q4_2024_revenue.csv",
        TEST_DATA_DIR / "q3_2024_revenue.csv",
        expected_status=200
    )
    
    # Test B: Semantic match (V1.75)
    run_test(
        "Test B: Semantic Match",
        TEST_DATA_DIR / "q4_2024_sales.csv",
        TEST_DATA_DIR / "q3_2024_turnover.csv",
        expected_status=200
    )
    
    # Test C: Ambiguity (should reject)
    run_test(
        "Test C: Ambiguity Rejection",
        TEST_DATA_DIR / "current_metrics.csv",
        TEST_DATA_DIR / "baseline_metrics.csv",
        expected_status=400
    )
    
    # Test D: Single dataset (no baseline)
    run_test(
        "Test D: Single Dataset",
        TEST_DATA_DIR / "single_period_revenue.csv",
        expected_status=200
    )
    
    # Test E: Missing revenue column
    run_test(
        "Test E: Missing Revenue Column",
        TEST_DATA_DIR / "no_revenue.csv",
        expected_status=400
    )
    
    # Test F: Empty after cleaning
    run_test(
        "Test F: Empty After Cleaning",
        TEST_DATA_DIR / "duplicates_only.csv",
        options={"drop_duplicates": "true"},
        expected_status=400
    )
    
    # Test G: Malformed CSV
    run_test(
        "Test G: Malformed CSV",
        TEST_DATA_DIR / "broken.csv",
        expected_status=400
    )
    
    # Test H: Large file performance
    log("Generating large test file (50k rows)...")
    large_csv = "date,revenue\n"
    import random
    for i in range(50000):
        large_csv += f"2024-01-{(i % 28) + 1},{random.randint(1000, 50000)}\n"
    
    run_test_with_content(
        "Test H: Large File (50k rows)",
        large_csv,
        expected_status=200
    )
    
    # Summary
    log("\n" + "=" * 60)
    log("TEST SUMMARY")
    log("=" * 60)
    
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    
    log(f"\nTotal: {total} | Passed: {passed} | Failed: {total - passed}")
    log(f"Pass Rate: {(passed/total)*100:.1f}%\n")
    
    for r in results:
        status = "✅" if r["passed"] else "❌"
        log(f"  {status} {r['test']}: {r['status']} (expected {r['expected_status']})")
    
    # Save full results
    summary_file = OUTPUTS_DIR / f"test_summary_{int(time.time())}.json"
    with open(summary_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": (passed/total)*100,
            "results": results
        }, f, indent=2)
    
    log(f"\nResults saved to: {summary_file}")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
