"""Test: time-density filter eliminates merchant false positives in smurfing detection.

Scenario A  (SMURF_01)   : 12 deposits from unique senders, 30-min gaps  → SHOULD be flagged
Scenario B  (MERCHANT_01): 20 deposits from unique senders, 60-min gaps  → should NOT be flagged
"""

import pandas as pd
from datetime import datetime, timedelta
from detection_engine import (
    parse_csv,
    precompute_metrics,
    detect_smurfing,
    _is_time_clustered,
    _DENSITY_THRESHOLD_MINUTES,
)

PASS = 0
FAIL = 0


def check(label: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ PASS: {label}")
    else:
        FAIL += 1
        print(f"  ✗ FAIL: {label}  {detail}")


# ── Helpers ──────────────────────────────────────────────────────────────────
def _make_fan_in_csv(target: str, num_senders: int, gap_minutes: int) -> pd.DataFrame:
    """Build a CSV DataFrame where `num_senders` unique accounts each send one
    transaction to `target`, spaced `gap_minutes` apart."""
    rows = []
    base = datetime(2025, 6, 1, 8, 0, 0)
    for i in range(num_senders):
        rows.append({
            "transaction_id": f"TX_{target}_{i:03d}",
            "sender_id": f"SENDER_{target}_{i:03d}",
            "receiver_id": target,
            "amount": 500.00,
            "timestamp": (base + timedelta(minutes=i * gap_minutes)).strftime("%Y-%m-%d %H:%M:%S"),
        })
    return pd.DataFrame(rows)


# ── Test 1: _is_time_clustered helper ────────────────────────────────────────
print("=" * 60)
print("TEST 1: _is_time_clustered() helper function")

# Clustered (30-min gaps → avg gap = 30 < 45 → True)
smurf_df = _make_fan_in_csv("SMURF_01", 12, gap_minutes=30)
smurf_graph = parse_csv(smurf_df)
smurf_metrics = precompute_metrics(smurf_graph)
smurf_incoming = smurf_metrics["SMURF_01"]["incoming_sorted"]
check(
    "Smurf deposits (30-min gap) are clustered",
    _is_time_clustered(smurf_incoming),
    f"threshold={_DENSITY_THRESHOLD_MINUTES}min",
)

# Spread out (60-min gaps → avg gap = 60 > 45 → False)
merch_df = _make_fan_in_csv("MERCHANT_01", 20, gap_minutes=60)
merch_graph = parse_csv(merch_df)
merch_metrics = precompute_metrics(merch_graph)
merch_incoming = merch_metrics["MERCHANT_01"]["incoming_sorted"]
check(
    "Merchant deposits (60-min gap) are NOT clustered",
    not _is_time_clustered(merch_incoming),
    f"threshold={_DENSITY_THRESHOLD_MINUTES}min",
)

# Edge case: only 1 transaction → should NOT be clustered
single_txn = [{"timestamp": datetime(2025, 1, 1, 10, 0)}]
check("Single transaction is NOT clustered", not _is_time_clustered(single_txn))


# ── Test 2: detect_smurfing end-to-end ───────────────────────────────────────
print("=" * 60)
print("TEST 2: detect_smurfing() end-to-end with density filter")

# Smurf scenario
rc = [0]
smurf_rings, smurf_fan_in, smurf_fan_out = detect_smurfing(smurf_metrics, rc)
check(
    "SMURF_01 IS flagged as fan-in",
    "SMURF_01" in smurf_fan_in,
    f"fan_in={smurf_fan_in}",
)
check(
    "Smurf rings detected ≥ 1",
    len(smurf_rings) >= 1,
    f"rings={len(smurf_rings)}",
)

# Merchant scenario
rc2 = [0]
merch_rings, merch_fan_in, merch_fan_out = detect_smurfing(merch_metrics, rc2)
check(
    "MERCHANT_01 is NOT flagged as fan-in",
    "MERCHANT_01" not in merch_fan_in,
    f"fan_in={merch_fan_in}",
)
check(
    "No rings for merchant scenario",
    len(merch_rings) == 0,
    f"rings={len(merch_rings)}",
)


# ── Test 3: Combined dataset ────────────────────────────────────────────────
print("=" * 60)
print("TEST 3: Combined dataset (smurf + merchant together)")

combined_df = pd.concat([smurf_df, merch_df], ignore_index=True)
combined_graph = parse_csv(combined_df)
combined_metrics = precompute_metrics(combined_graph)
rc3 = [0]
comb_rings, comb_fan_in, comb_fan_out = detect_smurfing(combined_metrics, rc3)

check(
    "SMURF_01 flagged in combined dataset",
    "SMURF_01" in comb_fan_in,
    f"fan_in={comb_fan_in}",
)
check(
    "MERCHANT_01 NOT flagged in combined dataset",
    "MERCHANT_01" not in comb_fan_in,
    f"fan_in={comb_fan_in}",
)


# ── Summary ──────────────────────────────────────────────────────────────────
print("=" * 60)
total = PASS + FAIL
print(f"\nResults: {PASS}/{total} passed, {FAIL} failed")
if FAIL == 0:
    print("ALL TESTS PASSED ✓")
else:
    print("SOME TESTS FAILED ✗")
    exit(1)
