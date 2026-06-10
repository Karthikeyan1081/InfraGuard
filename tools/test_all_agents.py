"""Test all agent endpoints sequentially."""
import json
import urllib.request
import urllib.error
from pathlib import Path

BASE = "http://127.0.0.1:8000"

# Sample infrastructure data
SAMPLE_DATA = {
    "assets": [
        {
            "asset_id": "srv-001",
            "hostname": "web-server-01",
            "ip": "192.168.1.10",
            "status": "Active",
        },
        {
            "asset_id": "srv-002",
            "hostname": "app-server-01",
            "ip": "192.168.1.20",
            "status": "Active",
        },
        {
            "asset_id": "srv-003",
            "hostname": "db-server-01",
            "ip": "192.168.1.30",
            "status": "Inactive",
        },
    ],
    "mismatches": [
        {
            "asset_id": "srv-001",
            "reason": "Hostname mismatch in CMDB",
        },
        {
            "asset_id": "unknown-host",
            "reason": "Untracked active asset",
        },
    ],
}


def post_json(url, data):
    """Send POST request with JSON payload."""
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def test_risk_analysis():
    """Test risk analysis endpoint."""
    print("\n=== Testing Risk Analysis ===")
    url = f"{BASE}/api/risk/analyze"
    payload = {"infrastructure_data": SAMPLE_DATA}
    status, response = post_json(url, payload)
    print(f"Status: {status}")
    print(f"Response: {json.dumps(response, indent=2)[:500]}...")
    return response


def test_recommendations(risk_assessment=None):
    """Test recommendation generation endpoint."""
    print("\n=== Testing Recommendations ===")
    url = f"{BASE}/api/recommendations/generate"
    payload = {"infrastructure_data": SAMPLE_DATA, "risk_assessment": risk_assessment}
    status, response = post_json(url, payload)
    print(f"Status: {status}")
    print(f"Response: {json.dumps(response, indent=2)[:500]}...")
    return response


def test_planning(risk_assessment=None, recommendations=None):
    """Test planning/execution plan endpoint."""
    print("\n=== Testing Planning ===")
    url = f"{BASE}/api/planning/create-plan"
    payload = {
        "infrastructure_data": SAMPLE_DATA,
        "risk_assessment": risk_assessment,
        "recommendations": recommendations,
    }
    status, response = post_json(url, payload)
    print(f"Status: {status}")
    print(f"Response: {json.dumps(response, indent=2)[:500]}...")
    return response


def test_orchestration():
    """Test full orchestration endpoint."""
    print("\n=== Testing Full Orchestration ===")
    url = f"{BASE}/api/orchestration/analyze"
    payload = {"infrastructure_data": SAMPLE_DATA, "include_planning": True}
    status, response = post_json(url, payload)
    print(f"Status: {status}")
    print(f"Response: {json.dumps(response, indent=2)[:500]}...")
    return response


def test_orchestration_status():
    """Test orchestration status endpoint."""
    print("\n=== Testing Orchestration Status ===")
    url = f"{BASE}/api/orchestration/status"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            status_code = response.status
            data = json.loads(response.read().decode("utf-8"))
            print(f"Status: {status_code}")
            print(f"Response: {json.dumps(data, indent=2)}")
            return data
    except Exception as e:
        print(f"Error: {e}")
        return None


def main():
    """Run all agent tests."""
    print("Starting Agent Orchestration Tests")
    print("=" * 50)

    # Test individual agents first
    risk_result = test_risk_analysis()
    risk_text = risk_result.get("risk_assessment", "")

    rec_result = test_recommendations(risk_text)
    rec_text = rec_result.get("recommendations", "")

    test_planning(risk_text, rec_text)

    # Test full orchestration
    test_orchestration()

    # Test status
    test_orchestration_status()

    print("\n" + "=" * 50)
    print("Agent Orchestration Tests Completed")


if __name__ == "__main__":
    main()
