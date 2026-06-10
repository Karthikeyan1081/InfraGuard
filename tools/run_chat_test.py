import json
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8000"


def post_json(url, data):
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


def main():
    url = f"{BASE}/api/chat/"
    payload = {
        "model": "gemini-1.0",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant for the AssetSync app."},
            {"role": "user", "content": "Summarize the latest inventory reconciliation workflow."},
        ],
    }
    print(f"Calling {url}")
    res = post_json(url, payload)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
