"""Quick API test script."""
import urllib.request
import json
import uuid

boundary = uuid.uuid4().hex
body = b""
body += ("--" + boundary + "\r\n").encode()
body += b'Content-Disposition: form-data; name="file"; filename="sample.csv"\r\n'
body += b"Content-Type: text/csv\r\n\r\n"
with open(r"d:\RIFT\v1\sample_transactions.csv", "rb") as f:
    body += f.read()
body += ("\r\n--" + boundary + "--\r\n").encode()

req = urllib.request.Request("http://localhost:8001/api/upload", data=body, method="POST")
req.add_header("Content-Type", "multipart/form-data; boundary=" + boundary)

resp = urllib.request.urlopen(req)
data = json.loads(resp.read())

print("STATUS:", resp.status)
s = data.get("summary", {})
print("ACCOUNTS:", s.get("total_accounts_analyzed"))
print("SUSPICIOUS:", s.get("suspicious_accounts_flagged"))
print("RINGS:", s.get("fraud_rings_detected"))
print("TIME:", s.get("processing_time_seconds"))

rings = data.get("fraud_rings", [])
for r in rings[:5]:
    print("  %s | %s | members=%d | risk=%s" % (r["ring_id"], r["pattern_type"], len(r["member_accounts"]), r["risk_score"]))

accts = data.get("suspicious_accounts", [])
print("TOP SCORES:")
for a in accts[:5]:
    print("  %s score=%s ring=%s patterns=%s" % (a["account_id"], a["suspicion_score"], a["ring_id"], a["detected_patterns"]))

# Validate schema
assert "suspicious_accounts" in data
assert "fraud_rings" in data
assert "summary" in data
assert "graph" in data
for a in data["suspicious_accounts"]:
    assert a["ring_id"] is not None, "null ring_id!"
    assert 0 <= a["suspicion_score"] <= 100, "score out of range!"
print("\nALL SCHEMA CHECKS PASSED")
