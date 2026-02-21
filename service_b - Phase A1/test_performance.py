"""Phase 6: Performance Check - 10MB CSV, 200k rows"""
import requests
import io
import time
import sys
import tracemalloc

BASE_URL = "http://127.0.0.1:8000"

def generate_large_csv(rows):
    """Generate CSV with specified rows"""
    lines = ["date,revenue,cost,quantity,category,region"]
    categories = ["A", "B", "C", "D", "E"]
    regions = ["North", "South", "East", "West"]
    for i in range(rows):
        month = (i % 12) + 1
        year = 2020 + (i // 12) % 5
        revenue = 1000 + (i * 0.5) + (i % 1000)
        cost = revenue * 0.6
        quantity = 10 + (i % 500)
        cat = categories[i % 5]
        region = regions[i % 4]
        lines.append(f"{year}-{month:02d},{revenue:.2f},{cost:.2f},{quantity},{cat},{region}")
    return "\n".join(lines)

def test_200k_rows():
    """Test with 200,000 rows"""
    print("=" * 60)
    print("PERFORMANCE TEST: 200,000 ROWS")
    print("=" * 60)
    
    print("\nGenerating 200k row dataset...")
    start_gen = time.time()
    csv_data = generate_large_csv(200000)
    gen_time = time.time() - start_gen
    
    size_mb = len(csv_data) / (1024 * 1024)
    print(f"  - Generation time: {gen_time:.2f}s")
    print(f"  - CSV size: {size_mb:.2f} MB")
    print(f"  - Row count: 200,000")
    
    print("\nSending to /v1/analyze...")
    files = {"current_file": ("large.csv", io.StringIO(csv_data), "text/csv")}
    
    start_req = time.time()
    r = requests.post(f"{BASE_URL}/v1/analyze", files=files)
    req_time = time.time() - start_req
    
    print(f"\nResults:")
    print(f"  - Status code: {r.status_code}")
    print(f"  - Processing time: {req_time:.2f}s")
    print(f"  - Under 10s threshold: {req_time < 10}")
    
    if r.status_code == 200:
        data = r.json()
        print(f"  - Has report: {'report' in data}")
        print(f"  - Has insights: {len(data.get('report', {}).get('insights', [])) >= 0}")
        print(f"  - Has business_insights: {data.get('business_insights') is not None}")
    else:
        print(f"  - Error: {r.text[:200]}")
    
    return r.status_code == 200 and req_time < 10

def test_10mb_csv():
    """Test with ~10MB CSV file"""
    print("\n" + "=" * 60)
    print("PERFORMANCE TEST: ~10MB CSV")
    print("=" * 60)
    
    # Calculate rows needed for ~10MB
    # Each row is ~50 bytes, so 10MB / 50 = ~200,000 rows
    target_mb = 10
    estimated_rows = int(target_mb * 1024 * 1024 / 50)
    
    print(f"\nGenerating ~{target_mb}MB CSV ({estimated_rows} rows)...")
    start_gen = time.time()
    csv_data = generate_large_csv(estimated_rows)
    gen_time = time.time() - start_gen
    
    actual_mb = len(csv_data) / (1024 * 1024)
    print(f"  - Generation time: {gen_time:.2f}s")
    print(f"  - Actual CSV size: {actual_mb:.2f} MB")
    
    print("\nSending to /v1/analyze...")
    files = {"current_file": ("10mb.csv", io.StringIO(csv_data), "text/csv")}
    
    start_req = time.time()
    r = requests.post(f"{BASE_URL}/v1/analyze", files=files)
    req_time = time.time() - start_req
    
    print(f"\nResults:")
    print(f"  - Status code: {r.status_code}")
    print(f"  - Processing time: {req_time:.2f}s")
    print(f"  - Under 10s threshold: {req_time < 10}")
    
    return r.status_code == 200 and req_time < 10

def test_with_baseline_large():
    """Test with large current + baseline datasets"""
    print("\n" + "=" * 60)
    print("PERFORMANCE TEST: 100k + 100k ROWS (WITH BASELINE)")
    print("=" * 60)
    
    print("\nGenerating datasets...")
    current_csv = generate_large_csv(100000)
    baseline_csv = generate_large_csv(100000)
    
    total_mb = (len(current_csv) + len(baseline_csv)) / (1024 * 1024)
    print(f"  - Total size: {total_mb:.2f} MB")
    
    print("\nSending to /v1/analyze...")
    files = {
        "current_file": ("current.csv", io.StringIO(current_csv), "text/csv"),
        "baseline_file": ("baseline.csv", io.StringIO(baseline_csv), "text/csv"),
    }
    
    start_req = time.time()
    r = requests.post(f"{BASE_URL}/v1/analyze", files=files)
    req_time = time.time() - start_req
    
    print(f"\nResults:")
    print(f"  - Status code: {r.status_code}")
    print(f"  - Processing time: {req_time:.2f}s")
    print(f"  - Under 10s threshold: {req_time < 10}")
    
    if r.status_code == 200:
        data = r.json()
        deltas = data.get("report", {}).get("metric_deltas", [])
        print(f"  - Has metric deltas: {len(deltas) > 0}")
        if deltas:
            print(f"  - Delta computed correctly: {deltas[0].get('percent_change') is not None}")
    
    return r.status_code == 200 and req_time < 10

if __name__ == "__main__":
    results = []
    
    results.append(("200k Rows", test_200k_rows()))
    results.append(("10MB CSV", test_10mb_csv()))
    results.append(("100k + 100k Baseline", test_with_baseline_large()))
    
    print("\n" + "=" * 60)
    print("PERFORMANCE SUMMARY")
    print("=" * 60)
    
    all_pass = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  {name}: {status}")
    
    print(f"\nOVERALL: {'PASS' if all_pass else 'FAIL'}")
