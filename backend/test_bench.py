"""Benchmark: correctness + timing."""
import time, pandas as pd, json
from detection_engine import run_pipeline

df = pd.read_csv("d:/RIFT/v1/sample_transactions.csv")

# Warm up
run_pipeline(df)

# Benchmark
times = []
for i in range(5):
    t0 = time.perf_counter()
    r = run_pipeline(df)
    t1 = time.perf_counter()
    times.append(t1 - t0)

s = r["summary"]
print(f"Accounts: {s['total_accounts_analyzed']}")
print(f"Suspicious: {s['suspicious_accounts_flagged']}")
print(f"Rings: {s['fraud_rings_detected']}")
types = {}
for x in r["fraud_rings"]:
    types[x["pattern_type"]] = types.get(x["pattern_type"], 0) + 1
print(f"Ring types: {types}")
print(f"\nTiming (5 runs): {[round(t*1000, 1) for t in times]} ms")
print(f"Average: {round(sum(times)/len(times)*1000, 1)} ms")
print(f"Min: {round(min(times)*1000, 1)} ms")

# Verify JSON
json.dumps(r)
print("\nJSON OK. All checks passed.")
