import os
import urllib.request
import urllib.parse
import json
import uuid

BASE_URL = "http://127.0.0.1:8080/api"

def post_multipart(url, file_path, file_type):
    """
    Constructs and sends a multipart/form-data request using Python's standard library.
    Allows testing file upload without relying on external libraries like requests.
    """
    boundary = '----WebKitFormBoundary' + uuid.uuid4().hex
    filename = os.path.basename(file_path)
    
    with open(file_path, 'rb') as f:
        file_content = f.read()
        
    parts = [
        f'--{boundary}'.encode(),
        f'Content-Disposition: form-data; name="file_type"'.encode(),
        b'',
        file_type.encode(),
        f'--{boundary}'.encode(),
        f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode(),
        b'Content-Type: application/octet-stream',
        b'',
        file_content,
        f'--{boundary}--'.encode(),
        b''
    ]
    
    body = b'\r\n'.join(parts)
    
    req = urllib.request.Request(url, data=body)
    req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
    
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode('utf-8'))

def post_json(url, data):
    body = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode('utf-8'))

def get_json(url):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode('utf-8'))

def test_api():
    print("=== STARTING LIVE API INTEGRATION TESTS ===")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cmdb_file = os.path.join(base_dir, "data_samples", "cmdb_inventory.csv")
    actual_file = os.path.join(base_dir, "data_samples", "actual_infrastructure.json")
    
    # 1. Upload CMDB CSV
    print("\n1. Testing POST /api/upload for CMDB file (CSV)...")
    upload_url = f"{BASE_URL}/upload"
    cmdb_res = post_multipart(upload_url, cmdb_file, "cmdb")
    print(f"   [OK] CMDB Upload response: {cmdb_res}")
    cmdb_path = cmdb_res["saved_filepath"]
    
    # 2. Upload Actual JSON
    print("\n2. Testing POST /api/upload for Actual file (JSON)...")
    actual_res = post_multipart(upload_url, actual_file, "actual")
    print(f"   [OK] Actual Upload response: {actual_res}")
    actual_path = actual_res["saved_filepath"]
    
    # 3. Trigger Reconcile Analysis
    print("\n3. Testing POST /api/analyze...")
    analyze_url = f"{BASE_URL}/analyze"
    analyze_payload = {
        "name": "Live HTTP Integration Audit",
        "cmdb_file_path": cmdb_path,
        "actual_file_path": actual_path
    }
    analyze_res = post_json(analyze_url, analyze_payload)
    print(f"   [OK] Analyze response: {analyze_res}")
    analysis_id = analyze_res["analysis_id"]
    
    # 4. Check list endpoint
    print("\n4. Testing GET /api/analyses...")
    list_url = f"{BASE_URL}/analyses"
    list_res = get_json(list_url)
    print(f"   [OK] History list contains {len(list_res)} audit records.")
    
    # Verify our run is in the list
    run_found = any(item["id"] == analysis_id for item in list_res)
    if run_found:
        print(f"   [OK] Created run '{analysis_id}' verified in history list.")
    else:
        raise ValueError(f"   [FAIL] Created run '{analysis_id}' not found in history list.")
        
    # 5. Check detail endpoint
    print("\n5. Testing GET /api/analyses/{id}...")
    detail_url = f"{BASE_URL}/analyses/{analysis_id}"
    detail_res = get_json(detail_url)
    print(f"   [OK] Run Name: {detail_res['name']}")
    print(f"   [OK] Discrepancies Count: {detail_res['summary_stats']['total_discrepancies']}")
    print(f"   [OK] Discrepancies details array length: {len(detail_res['discrepancies'])}")
    
    # 6. Check report PDF endpoint
    print("\n6. Testing GET /api/reports/{id}...")
    report_url = f"http://127.0.0.1:8080/api/reports/{analysis_id}"
    output_pdf_path = os.path.join(base_dir, "reports", f"AuditReport_HTTP_{analysis_id}.pdf")
    
    # Download using urllib urlretrieve
    urllib.request.urlretrieve(report_url, output_pdf_path)
    
    if os.path.exists(output_pdf_path) and os.path.getsize(output_pdf_path) > 0:
        print(f"   [OK] Generated and downloaded PDF report successfully ({os.path.getsize(output_pdf_path)} bytes) at:")
        print(f"        {output_pdf_path}")
    else:
        raise FileNotFoundError("   [FAIL] Live downloaded PDF report not found or is empty.")
        
    print("\n=== LIVE HTTP API INTEGRATION TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    test_api()
