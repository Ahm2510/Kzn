"""Large dataset and temp file leak testing"""
import requests
import io
import os
import glob
import tempfile
import time

BASE_URL = "http://127.0.0.1:8000"

def generate_large_csv(rows=10000):
    """Generate a large CSV dataset"""
    lines = ["date,revenue,cost,quantity"]
    for i in range(rows):
        month = (i % 12) + 1
        year = 2020 + (i // 12)
        revenue = 1000 + (i * 10) + (i % 100)
        cost = revenue * 0.6
        quantity = 10 + (i % 50)
        lines.append(f"{year}-{month:02d},{revenue},{cost},{quantity}")
    return "\n".join(lines)

def count_temp_pdfs():
    """Count PDF files in temp directory"""
    temp_dir = tempfile.gettempdir()
    return len(glob.glob(os.path.join(temp_dir, "*.pdf")))

def test_large_dataset():
    """Test with 10,000 rows"""
    print("Generating 10,000 row dataset...")
    csv_data = generate_large_csv(10000)
    print(f"  CSV size: {len(csv_data) / 1024:.1f} KB")
    
    files = {"current_file": ("large.csv", io.StringIO(csv_data), "text/csv")}
    
    start = time.time()
    r = requests.post(f"{BASE_URL}/v1/analyze", files=files)
    elapsed = time.time() - start
    
    print(f"Large dataset (10k rows): {r.status_code}")
    print(f"  - Processing time: {elapsed:.2f}s")
    print(f"  - Under 10s: {elapsed < 10}")
    
    if r.status_code == 200:
        data = r.json()
        print(f"  - Has report: {'report' in data}")
        print(f"  - Has insights: {len(data.get('report', {}).get('insights', [])) > 0}")
    
    return r.status_code == 200 and elapsed < 10

def test_temp_file_cleanup():
    """Test that temp files are cleaned up after errors"""
    before_count = count_temp_pdfs()
    
    # Make several requests that should fail
    for i in range(3):
        csv_data = "not,valid,revenue\ndata"
        files = {"current_file": ("bad.csv", io.StringIO(csv_data), "text/csv")}
        requests.post(f"{BASE_URL}/v1/analyze", files=files)
    
    after_count = count_temp_pdfs()
    
    print(f"Temp file cleanup test:")
    print(f"  - PDFs before: {before_count}")
    print(f"  - PDFs after: {after_count}")
    print(f"  - No leak: {after_count <= before_count + 1}")  # Allow 1 for concurrent
    
    return after_count <= before_count + 1

if __name__ == "__main__":
    print("=" * 50)
    print("LARGE DATASET & TEMP FILE TESTING")
    print("=" * 50)
    
    results = []
    results.append(("Large Dataset (10k rows)", test_large_dataset()))
    results.append(("Temp File Cleanup", test_temp_file_cleanup()))
    
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
