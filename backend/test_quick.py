"""Quick verification of new detection algorithms."""
import pandas as pd
import json
from detection_engine import run_pipeline

df = pd.read_csv("d:/RIFT/v1/sample_transactions.csv")
r = run_pipeline(df)
s = r["summary"]

print(f"Accounts: {s['total_accounts_analyzed']}")
print(f"Suspicious: {s['suspicious_accounts_flagged']}")
print(f"Rings: {s['fraud_rings_detected']}")

# Count by type
types = {}
for x in r["fraud_rings"]:
    t = x["pattern_type"]
    types[t] = types.get(t, 0) + 1
print(f"Ring types: {types}")

# Show suspicious nodes with their patterns
print("\nSuspicious nodes:")
for n in r["graph"]["nodes"]:
    if n["is_suspicious"]:
        print(f"  {n['id']}: score={n['suspicion_score']} patterns={n['detected_patterns']}")

# Verify JSON
json.dumps(r)
print("\nJSON serialization: OK")
print("ALL CHECKS PASSED")
