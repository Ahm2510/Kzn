#!/usr/bin/env python3
"""
Service B V1.75 — Adversarial Black-Box Validation Suite
=========================================================
NO backend code inspection. HTTP-only testing.
Treat service as opaque production system.
"""

import requests
import json
import time
import random
import string
from datetime import datetime
from pathlib import Path
from io import BytesIO

API_BASE = "http://localhost:8000"
HARNESS_ORIGIN = "http://localhost:5500"
OUTPUTS_DIR = Path(__file__).parent / "blackbox_outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)

class TestResult:
    def __init__(self, name, phase, passed, status=None, message="", severity="normal"):
        self.name = name
        self.phase = phase
        self.passed = passed
        self.status = status
        self.message = message
        self.severity = severity
        self.timestamp = datetime.now().isoformat()

results = []

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {level}: {msg}")

def record(name, phase, passed, status=None, message="", severity="normal"):
    r = TestResult(name, phase, passed, status, message, severity)
    results.append(r)
    icon = "✅" if passed else "❌"
    log(f"{icon} {name}: {message}")
    return r

def post_analyze(current_csv, baseline_csv=None, options=None, timeout=60):
    """Core HTTP request to /v1/analyze"""
    default_opts = {
        "normalize_columns": "true",
        "drop_duplicates": "true",
        "drop_missing": "true",
        "cap_outliers": "false"
    }
    if options:
        default_opts.update(options)
    
    files = {"current_file": ("current.csv", current_csv, "text/csv")}
    if baseline_csv:
        files["baseline_file"] = ("baseline.csv", baseline_csv, "text/csv")
    
    try:
        r = requests.post(
            f"{API_BASE}/v1/analyze",
            files=files,
            data=default_opts,
            timeout=timeout,
            headers={"Origin": HARNESS_ORIGIN}
        )
        return r
    except requests.exceptions.Timeout:
        return None
    except Exception as e:
        return None

# =============================================================================
# PHASE 0 — SYSTEM SANITY
# =============================================================================
def phase_0_system_sanity():
    log("\n" + "="*60)
    log("PHASE 0 — SYSTEM SANITY")
    log("="*60)
    
    # Health endpoint
    try:
        r = requests.get(f"{API_BASE}/health", timeout=5)
        record("Health endpoint", "P0", r.status_code == 200, r.status_code, 
               f"Response: {r.text[:100]}")
    except Exception as e:
        record("Health endpoint", "P0", False, None, str(e), "critical")
        return False
    
    # CORS - valid origin
    try:
        r = requests.options(
            f"{API_BASE}/v1/analyze",
            headers={"Origin": HARNESS_ORIGIN, "Access-Control-Request-Method": "POST"},
            timeout=5
        )
        cors_header = r.headers.get("Access-Control-Allow-Origin", "")
        passed = HARNESS_ORIGIN in cors_header or cors_header == HARNESS_ORIGIN
        record("CORS valid origin", "P0", passed, r.status_code, 
               f"ACAO: {cors_header}")
    except Exception as e:
        record("CORS valid origin", "P0", False, None, str(e))
    
    # CORS - invalid origin (should not match)
    try:
        r = requests.options(
            f"{API_BASE}/v1/analyze",
            headers={"Origin": "http://evil.com", "Access-Control-Request-Method": "POST"},
            timeout=5
        )
        cors_header = r.headers.get("Access-Control-Allow-Origin", "")
        passed = "evil.com" not in cors_header
        record("CORS rejects invalid origin", "P0", passed, r.status_code,
               f"ACAO: {cors_header}")
    except Exception as e:
        record("CORS rejects invalid origin", "P0", False, None, str(e))
    
    return True

# =============================================================================
# PHASE 1 — INPUT ROBUSTNESS
# =============================================================================
def phase_1_input_robustness():
    log("\n" + "="*60)
    log("PHASE 1 — INPUT ROBUSTNESS")
    log("="*60)
    
    tests = [
        ("Empty CSV (0 bytes)", b"", 400),
        ("Header-only CSV", b"date,revenue\n", 400),
        ("CSV with unclosed quotes", b'date,revenue\n"2024-01-01,1000\n', 400),
        ("CSV with mixed delimiters", b"date;revenue\n2024-01-01;1000\n", 400),
        ("CSV with UTF-8 BOM", b'\xef\xbb\xbfdate,revenue\n2024-01-01,1000\n', 200),
        ("CSV with non-numeric revenue", b"date,revenue\n2024-01-01,abc\n2024-01-02,def\n", 400),
        ("CSV with NaN values", b"date,revenue\n2024-01-01,NaN\n2024-01-02,1000\n", 200),
        ("CSV with inf values", b"date,revenue\n2024-01-01,inf\n2024-01-02,1000\n", 200),
        ("CSV with -inf values", b"date,revenue\n2024-01-01,-inf\n2024-01-02,1000\n", 200),
        ("CSV with huge numbers (1e18)", b"date,revenue\n2024-01-01,1000000000000000000\n", 200),
        ("CSV with duplicated headers", b"date,revenue,revenue\n2024-01-01,1000,2000\n", 200),
        ("CSV with trailing commas", b"date,revenue,\n2024-01-01,1000,\n", 200),
    ]
    
    for name, csv_data, expected in tests:
        r = post_analyze(csv_data)
        if r is None:
            record(name, "P1", False, None, "Request failed/timeout", "high")
        else:
            # For 4xx expected, 4xx is pass. For 2xx expected, 2xx is pass
            passed = (expected == 400 and 400 <= r.status_code < 500) or \
                     (expected == 200 and 200 <= r.status_code < 300)
            msg = f"Got {r.status_code}, expected {expected}"
            if not passed:
                msg += f" | {r.text[:100]}"
            record(name, "P1", passed, r.status_code, msg)

# =============================================================================
# PHASE 2 — CLEANING OPTIONS VALIDATION
# =============================================================================
def phase_2_cleaning_options():
    log("\n" + "="*60)
    log("PHASE 2 — CLEANING OPTIONS VALIDATION")
    log("="*60)
    
    # Base CSV with duplicates and missing values
    base_csv = b"""date,revenue,region
2024-01-01,1000,North
2024-01-01,1000,North
2024-01-02,,South
2024-01-03,3000,East
2024-01-04,50000,West
"""
    
    options_tests = [
        ("normalize_columns ON", {"normalize_columns": "true"}, 200),
        ("normalize_columns OFF", {"normalize_columns": "false"}, 200),
        ("drop_duplicates ON", {"drop_duplicates": "true"}, 200),
        ("drop_duplicates OFF", {"drop_duplicates": "false"}, 200),
        ("drop_missing ON", {"drop_missing": "true"}, 200),
        ("drop_missing OFF", {"drop_missing": "false"}, 200),
        ("cap_outliers ON", {"cap_outliers": "true"}, 200),
        ("cap_outliers OFF", {"cap_outliers": "false"}, 200),
    ]
    
    for name, opts, expected in options_tests:
        full_opts = {
            "normalize_columns": "true",
            "drop_duplicates": "false",
            "drop_missing": "false",
            "cap_outliers": "false"
        }
        full_opts.update(opts)
        
        r = post_analyze(base_csv, options=full_opts)
        if r is None:
            record(name, "P2", False, None, "Request failed", "high")
        else:
            passed = r.status_code == expected
            record(name, "P2", passed, r.status_code, f"Expected {expected}")
    
    # Verify drop_duplicates actually works
    dup_csv = b"""date,revenue
2024-01-01,1000
2024-01-01,1000
2024-01-01,1000
"""
    r_on = post_analyze(dup_csv, options={"drop_duplicates": "true", "drop_missing": "false"})
    r_off = post_analyze(dup_csv, options={"drop_duplicates": "false", "drop_missing": "false"})
    
    if r_on and r_off and r_on.status_code == 200 and r_off.status_code == 200:
        j_on = r_on.json()
        j_off = r_off.json()
        # With duplicates dropped, total should be 1000. Without, 3000.
        rev_on = j_on.get("report", {}).get("metric_deltas", [{}])[0].get("current", 0)
        rev_off = j_off.get("report", {}).get("metric_deltas", [{}])[0].get("current", 0)
        passed = rev_on != rev_off
        record("drop_duplicates behavior verified", "P2", passed, None,
               f"ON={rev_on}, OFF={rev_off}")
    else:
        record("drop_duplicates behavior verified", "P2", False, None, "Requests failed")

# =============================================================================
# PHASE 3 — SEMANTIC MATCHING (V1.75 CORE)
# =============================================================================
def phase_3_semantic_matching():
    log("\n" + "="*60)
    log("PHASE 3 — SEMANTIC MATCHING (V1.75 CORE)")
    log("="*60)
    
    def make_csv(column_name):
        return f"""date,{column_name}
2024-01-01,1000
2024-01-02,2000
2024-01-03,3000
""".encode()
    
    # Should PASS (semantic synonyms)
    pass_pairs = [
        ("revenue", "total_sales"),
        ("revenue", "sales_amount"),
        ("revenue", "turnover"),
        ("revenue", "income"),
        ("total_sales", "turnover"),
    ]
    
    for current_col, baseline_col in pass_pairs:
        current_csv = make_csv(current_col)
        baseline_csv = make_csv(baseline_col)
        r = post_analyze(current_csv, baseline_csv)
        
        if r is None:
            record(f"Semantic: {current_col} ↔ {baseline_col}", "P3", False, None, 
                   "Request failed", "high")
        else:
            passed = r.status_code == 200
            record(f"Semantic: {current_col} ↔ {baseline_col}", "P3", passed, 
                   r.status_code, "Should match semantically")
    
    # Should FAIL (not revenue synonyms)
    fail_pairs = [
        ("revenue", "cost"),
        ("revenue", "profit"),
        ("revenue", "gross_margin"),
        ("revenue", "expenses"),
    ]
    
    for current_col, baseline_col in fail_pairs:
        current_csv = make_csv(current_col)
        baseline_csv = make_csv(baseline_col)
        r = post_analyze(current_csv, baseline_csv)
        
        if r is None:
            record(f"Reject: {current_col} ↔ {baseline_col}", "P3", False, None,
                   "Request failed", "high")
        else:
            # Baseline should fail to find revenue-like column
            passed = r.status_code == 400
            record(f"Reject: {current_col} ↔ {baseline_col}", "P3", passed,
                   r.status_code, "Should reject non-revenue baseline")

# =============================================================================
# PHASE 4 — BASELINE EDGE CASES
# =============================================================================
def phase_4_baseline_edge_cases():
    log("\n" + "="*60)
    log("PHASE 4 — BASELINE EDGE CASES")
    log("="*60)
    
    current = b"""date,revenue
2024-01-01,1000
2024-01-02,2000
2024-01-03,3000
"""
    
    # Identical baseline
    r = post_analyze(current, current)
    if r:
        record("Baseline identical to current", "P4", r.status_code == 200,
               r.status_code, "Should handle gracefully")
    
    # Baseline with fewer rows
    baseline_fewer = b"""date,revenue
2024-01-01,500
"""
    r = post_analyze(current, baseline_fewer)
    if r:
        record("Baseline with fewer rows", "P4", r.status_code == 200,
               r.status_code, "Should handle gracefully")
    
    # Baseline with extra columns
    baseline_extra = b"""date,revenue,extra,more
2024-01-01,500,x,y
2024-01-02,600,x,y
"""
    r = post_analyze(current, baseline_extra)
    if r:
        record("Baseline with extra columns", "P4", r.status_code == 200,
               r.status_code, "Should handle gracefully")
    
    # Baseline empty after cleaning (all nulls)
    baseline_empty = b"""date,revenue
2024-01-01,
2024-01-02,
"""
    r = post_analyze(current, baseline_empty, options={"drop_missing": "true"})
    if r:
        record("Baseline empty after cleaning", "P4", r.status_code == 400,
               r.status_code, "Should return 400 for empty baseline")
    
    # Malformed baseline
    baseline_malformed = b"""date,revenue
"broken
"""
    r = post_analyze(current, baseline_malformed)
    if r:
        record("Baseline malformed", "P4", r.status_code == 400,
               r.status_code, "Should return 400 for malformed baseline")

# =============================================================================
# PHASE 5 — OUTPUT INTEGRITY
# =============================================================================
def phase_5_output_integrity():
    log("\n" + "="*60)
    log("PHASE 5 — OUTPUT INTEGRITY")
    log("="*60)
    
    current = b"""date,revenue
2024-01-01,1000
2024-01-02,2000
2024-01-03,3000
"""
    baseline = b"""date,revenue
2024-01-01,800
2024-01-02,1500
"""
    
    r = post_analyze(current, baseline)
    if r and r.status_code == 200:
        data = r.json()
        
        # Check report structure
        report = data.get("report", {})
        has_summary = "summary" in report and len(report["summary"]) > 0
        record("Output has summary", "P5", has_summary, None, 
               f"Summary: {report.get('summary', '')[:50]}")
        
        has_deltas = "metric_deltas" in report and len(report.get("metric_deltas", [])) > 0
        record("Output has metric_deltas", "P5", has_deltas, None,
               f"Deltas: {len(report.get('metric_deltas', []))}")
        
        has_insights = "insights" in report
        record("Output has insights field", "P5", has_insights, None,
               f"Insights: {len(report.get('insights', []))}")
        
        # Verify metric delta correctness
        if has_deltas:
            delta = report["metric_deltas"][0]
            current_val = delta.get("current", 0)
            baseline_val = delta.get("baseline", 0)
            record("Metric delta current value", "P5", current_val == 6000, None,
                   f"Expected 6000, got {current_val}")
            record("Metric delta baseline value", "P5", baseline_val == 2300, None,
                   f"Expected 2300, got {baseline_val}")
        
        # Check PDF path
        pdf_path = data.get("pdf_path", "")
        has_pdf = len(pdf_path) > 0 and ".pdf" in pdf_path
        record("Output has pdf_path", "P5", has_pdf, None, f"Path: {pdf_path[:50]}")
    else:
        record("Output integrity test", "P5", False, 
               r.status_code if r else None, "Request failed")

# =============================================================================
# PHASE 6 — STRESS & SAFETY
# =============================================================================
def phase_6_stress_safety():
    log("\n" + "="*60)
    log("PHASE 6 — STRESS & SAFETY")
    log("="*60)
    
    # Large file (100k rows)
    log("Generating 100k row CSV...")
    rows = ["date,revenue"]
    for i in range(100000):
        rows.append(f"2024-{(i%12)+1:02d}-{(i%28)+1:02d},{random.randint(100,10000)}")
    large_csv = "\n".join(rows).encode()
    
    start = time.time()
    r = post_analyze(large_csv, timeout=120)
    elapsed = time.time() - start
    
    if r:
        passed = r.status_code == 200 and elapsed < 60
        record("100k row stress test", "P6", passed, r.status_code,
               f"Completed in {elapsed:.1f}s", "high" if not passed else "normal")
    else:
        record("100k row stress test", "P6", False, None, 
               f"Timeout after {elapsed:.1f}s", "high")

# =============================================================================
# PHASE 7 — NEGATIVE TRUST TESTS
# =============================================================================
def phase_7_negative_trust():
    log("\n" + "="*60)
    log("PHASE 7 — NEGATIVE TRUST TESTS")
    log("="*60)
    
    # Missing required field (no current_file)
    try:
        r = requests.post(
            f"{API_BASE}/v1/analyze",
            data={"normalize_columns": "true"},
            timeout=10
        )
        record("Missing current_file", "P7", r.status_code == 422, r.status_code,
               "Should reject with 422")
    except Exception as e:
        record("Missing current_file", "P7", False, None, str(e))
    
    # Unexpected form fields
    csv = b"date,revenue\n2024-01-01,1000\n"
    try:
        r = requests.post(
            f"{API_BASE}/v1/analyze",
            files={"current_file": ("test.csv", csv, "text/csv")},
            data={
                "normalize_columns": "true",
                "drop_duplicates": "true",
                "drop_missing": "true",
                "cap_outliers": "false",
                "evil_field": "malicious",
                "sql_injection": "'; DROP TABLE users;--"
            },
            timeout=10
        )
        record("Unexpected form fields", "P7", r.status_code in [200, 422], r.status_code,
               "Should ignore or reject cleanly")
    except Exception as e:
        record("Unexpected form fields", "P7", False, None, str(e))
    
    # Baseline only (no current)
    try:
        r = requests.post(
            f"{API_BASE}/v1/analyze",
            files={"baseline_file": ("base.csv", csv, "text/csv")},
            data={"normalize_columns": "true"},
            timeout=10
        )
        record("Baseline only (no current)", "P7", r.status_code == 422, r.status_code,
               "Should require current_file")
    except Exception as e:
        record("Baseline only (no current)", "P7", False, None, str(e))
    
    # Non-CSV file with .csv extension
    fake_csv = b"This is not a CSV file. It's just random text."
    r = post_analyze(fake_csv)
    if r:
        record("Non-CSV with .csv extension", "P7", r.status_code == 400, r.status_code,
               "Should reject invalid CSV content")
    
    # Binary file
    binary = bytes(range(256))
    r = post_analyze(binary)
    if r:
        record("Binary file upload", "P7", r.status_code == 400, r.status_code,
               "Should reject binary content")

# =============================================================================
# MAIN RUNNER
# =============================================================================
def generate_report():
    """Generate final audit report"""
    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed]
    silent = [r for r in failed if r.severity == "silent"]
    critical = [r for r in failed if r.severity in ["critical", "high"]]
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": len(results),
            "passed": len(passed),
            "failed": len(failed),
            "pass_rate": f"{len(passed)/len(results)*100:.1f}%",
            "silent_failures": len(silent),
            "critical_failures": len(critical)
        },
        "verdict": "GO" if len(critical) == 0 and len(passed)/len(results) >= 0.9 else "NO-GO",
        "results_by_phase": {},
        "failed_tests": [],
        "critical_issues": []
    }
    
    for r in results:
        phase = r.phase
        if phase not in report["results_by_phase"]:
            report["results_by_phase"][phase] = {"passed": 0, "failed": 0}
        if r.passed:
            report["results_by_phase"][phase]["passed"] += 1
        else:
            report["results_by_phase"][phase]["failed"] += 1
            report["failed_tests"].append({
                "name": r.name,
                "phase": r.phase,
                "status": r.status,
                "message": r.message,
                "severity": r.severity
            })
    
    for r in critical:
        report["critical_issues"].append({
            "name": r.name,
            "phase": r.phase,
            "message": r.message
        })
    
    return report

def main():
    log("="*60)
    log("SERVICE B V1.75 — ADVERSARIAL BLACK-BOX VALIDATION")
    log("="*60)
    log(f"Target: {API_BASE}")
    log(f"Origin: {HARNESS_ORIGIN}")
    
    # Run all phases
    if not phase_0_system_sanity():
        log("ABORT: System sanity failed", "ERROR")
        return
    
    phase_1_input_robustness()
    phase_2_cleaning_options()
    phase_3_semantic_matching()
    phase_4_baseline_edge_cases()
    phase_5_output_integrity()
    phase_6_stress_safety()
    phase_7_negative_trust()
    
    # Generate report
    report = generate_report()
    
    # Print summary
    log("\n" + "="*60)
    log("FINAL AUDIT REPORT")
    log("="*60)
    log(f"Total Tests: {report['summary']['total']}")
    log(f"Passed: {report['summary']['passed']}")
    log(f"Failed: {report['summary']['failed']}")
    log(f"Pass Rate: {report['summary']['pass_rate']}")
    log(f"Critical Issues: {report['summary']['critical_failures']}")
    log("")
    log(f"{'='*20} VERDICT: {report['verdict']} {'='*20}")
    
    if report["failed_tests"]:
        log("\nFailed Tests:")
        for t in report["failed_tests"]:
            log(f"  ❌ [{t['phase']}] {t['name']}: {t['message']}")
    
    # Save report
    report_file = OUTPUTS_DIR / f"blackbox_audit_{int(time.time())}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    log(f"\nReport saved: {report_file}")
    
    return report["verdict"] == "GO"

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
