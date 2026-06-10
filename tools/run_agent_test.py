import os
import urllib.request
import json

BASE = "http://127.0.0.1:8000"

def post_json(url, data, timeout=300):
    body = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode('utf-8'))

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cmdb = os.path.join(base_dir, "data_samples", "cmdb_inventory.csv")
    actual = os.path.join(base_dir, "data_samples", "actual_infrastructure.json")

    url = f"{BASE}/api/agent/run"
    payload = {"cmdb_file_path": cmdb, "actual_file_path": actual}
    print("Calling", url)
    res = post_json(url, payload)
    print(json.dumps(res, indent=2))

if __name__ == '__main__':
    main()
