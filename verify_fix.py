import urllib.request
import json

BASE = "http://127.0.0.1:8080"
passed = 0
failed = 0

def check(label, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  [PASS] {label}")
        passed += 1
    else:
        print(f"  [FAIL] {label}" + (f" -- {detail}" if detail else ""))
        failed += 1

print("=" * 55)
print("  AssetSync Bug Fix Verification")
print("=" * 55)

# ── 1. CSS .hidden class ─────────────────────────────────
print("\n1. CSS: .hidden class defined?")
try:
    r = urllib.request.urlopen(f"{BASE}/static/styles.css?v=1.0.1")
    css = r.read().decode("utf-8")
    check(".hidden rule present",       ".hidden" in css)
    check("display:none !important",    "display: none !important" in css)
    check(".btn-spinner rule present",  ".btn-spinner" in css)
    check("@keyframes spin present",    "@keyframes spin" in css)
except Exception as e:
    check("CSS endpoint reachable", False, str(e))

# ── 2. HTML structure ────────────────────────────────────
print("\n2. HTML: correct initial state?")
try:
    r = urllib.request.urlopen(f"{BASE}/")
    html = r.read().decode("utf-8")
    check("Cache-buster v=1.0.1 on CSS link",   "styles.css?v=1.0.1" in html)
    check("empty-state-view NOT hidden at start","id=\"empty-state-view\" class=\"card empty-card\"" in html)
    check("dashboard-results-view starts hidden","id=\"dashboard-results-view\" class=\"hidden\"" in html)
    check("spinner starts hidden",               "class=\"btn-spinner hidden\"" in html)
    check("upload-status-message starts hidden", "class=\"status-msg hidden\"" in html)
except Exception as e:
    check("HTML endpoint reachable", False, str(e))

# ── 3. API /analyses list ────────────────────────────────
print("\n3. API: GET /api/analyses")
analyses = []
try:
    r = urllib.request.urlopen(f"{BASE}/api/analyses")
    analyses = json.loads(r.read())
    check("Returns HTTP 200",        True)
    check("Returns list",            isinstance(analyses, list))
    check("Has at least 1 run",      len(analyses) > 0, f"got {len(analyses)}")
    if analyses:
        first = analyses[0]
        check("Each run has 'id'",           "id" in first)
        check("Each run has 'name'",         "name" in first)
        check("Each run has 'status'",       "status" in first)
        check("Each run has 'summary_stats'","summary_stats" in first)
        check("Each run has 'created_at'",   "created_at" in first)
        print(f"     >> {len(analyses)} audit run(s) in DB")
except Exception as e:
    check("API /analyses reachable", False, str(e))

# ── 4. API /analyses/{id} detail ────────────────────────
print("\n4. API: GET /api/analyses/{id}")
if analyses:
    aid = analyses[0]["id"]
    try:
        r = urllib.request.urlopen(f"{BASE}/api/analyses/{aid}")
        detail = json.loads(r.read())
        check("Returns HTTP 200",           True)
        check("Has 'discrepancies' list",   "discrepancies" in detail and isinstance(detail["discrepancies"], list))
        check("Has 'summary_stats'",        "summary_stats" in detail)
        stats = detail.get("summary_stats", {})
        check("Stats has total_discrepancies", "total_discrepancies" in stats)
        check("Stats has high_severity",       "high_severity" in stats)
        check("Stats has medium_severity",     "medium_severity" in stats)
        check("Stats has low_severity",        "low_severity" in stats)
        disc_count = len(detail.get("discrepancies", []))
        total = stats.get("total_discrepancies", -1)
        check("Discrepancy count matches stats", disc_count == total,
              f"list={disc_count} vs stats.total={total}")
        print(f"     >> Run '{detail['name']}': {disc_count} discrepancies")
    except Exception as e:
        check("API /analyses/id reachable", False, str(e))
else:
    print("  [SKIP] No analyses in DB to test detail endpoint")

# ── 5. API /api/upload endpoint exists ──────────────────
print("\n5. API: Upload endpoint available?")
try:
    req = urllib.request.Request(f"{BASE}/api/upload", data=b"", method="POST")
    try:
        urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        # 422 Unprocessable Entity = endpoint exists, just needs real files
        check("Upload endpoint exists (422 = correct)", e.code == 422,
              f"Unexpected HTTP {e.code}")
    except Exception as e:
        check("Upload endpoint accessible", False, str(e))
except Exception as e:
    check("Upload endpoint reachable", False, str(e))

# ── Summary ──────────────────────────────────────────────
print()
print("=" * 55)
print(f"  Results: {passed} passed, {failed} failed")
print("=" * 55)
if failed == 0:
    print("  ALL CHECKS PASSED - Bug is fixed!")
else:
    print(f"  {failed} issue(s) still need attention.")
