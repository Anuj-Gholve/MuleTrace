"""Comprehensive test for the detection engine and API."""
import sys
import traceback
import io
import json
import pandas as pd

# ----- Test 1: Import check -----
print("=" * 60)
print("TEST 1: Import check")
try:
    from detection_engine import (
        parse_csv, precompute_metrics, detect_cycles,
        detect_smurfing, detect_shell_networks,
        compute_suspicion_scores, compute_ring_risk,
        run_pipeline, _account_patterns, _sliding_window_unique,
    )
    print("  PASS: All imports OK")
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()

# ----- Test 2: CSV parsing -----
print("=" * 60)
print("TEST 2: CSV Parsing")
try:
    df = pd.read_csv(r"d:\RIFT\v1\sample_transactions.csv")
    print(f"  CSV loaded: {len(df)} rows, columns: {list(df.columns)}")
    graph_data = parse_csv(df)
    print(f"  Accounts: {len(graph_data['all_accounts'])}")
    print(f"  Edges: {graph_data['edge_count']}")
    print(f"  Adjacency keys: {len(graph_data['adjacency_list'])}")
    print(f"  Reverse adjacency keys: {len(graph_data['reverse_adjacency'])}")
    print("  PASS")
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()

# ----- Test 3: Metrics -----
print("=" * 60)
print("TEST 3: Precompute Metrics")
try:
    metrics = precompute_metrics(graph_data)
    print(f"  Metrics computed for {len(metrics)} accounts")
    # Check a sample
    for acc in list(metrics.keys())[:3]:
        m = metrics[acc]
        print(f"    {acc}: in={m['in_degree']} out={m['out_degree']} total={m['total_degree']} incoming_txns={len(m['incoming_sorted'])} outgoing_txns={len(m['outgoing_sorted'])}")
    print("  PASS")
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()

# ----- Test 4: Cycle detection -----
print("=" * 60)
print("TEST 4: Cycle Detection")
try:
    ring_counter = [0]
    cycle_rings, cycle_suspicious = detect_cycles(
        graph_data["adjacency_list"], graph_data["all_accounts"], ring_counter
    )
    print(f"  Cycles found: {len(cycle_rings)}")
    print(f"  Suspicious accounts from cycles: {len(cycle_suspicious)}")
    for r in cycle_rings[:3]:
        print(f"    {r['ring_id']}: {r['detected_pattern']} members={r['member_accounts']}")
    print("  PASS")
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()

# ----- Test 5: Smurfing -----
print("=" * 60)
print("TEST 5: Smurfing Detection")
try:
    smurfing_rings, fan_in, fan_out = detect_smurfing(metrics, ring_counter)
    print(f"  Smurfing rings: {len(smurfing_rings)}")
    print(f"  Fan-in accounts: {fan_in}")
    print(f"  Fan-out accounts: {fan_out}")
    for r in smurfing_rings:
        print(f"    {r['ring_id']}: {r['detected_pattern']} members={len(r['member_accounts'])}")
    print("  PASS")
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()

# ----- Test 6: Shell networks -----
print("=" * 60)
print("TEST 6: Shell Network Detection")
try:
    shell_rings, shell_suspicious = detect_shell_networks(
        graph_data["adjacency_list"], metrics, graph_data["all_accounts"], ring_counter
    )
    print(f"  Shell rings: {len(shell_rings)}")
    print(f"  Shell suspicious: {len(shell_suspicious)}")
    for r in shell_rings[:3]:
        print(f"    {r['ring_id']}: members={r['member_accounts']}")
    print("  PASS")
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()

# ----- Test 7: Suspicion scores -----
print("=" * 60)
print("TEST 7: Suspicion Scoring")
try:
    scores = compute_suspicion_scores(
        graph_data["all_accounts"], cycle_suspicious, fan_in, fan_out, shell_suspicious
    )
    print(f"  Scores computed for {len(scores)} accounts")
    flagged = {k: v for k, v in scores.items() if v > 0}
    print(f"  Non-zero scores: {len(flagged)}")
    for acc, sc in sorted(flagged.items(), key=lambda x: -x[1])[:5]:
        print(f"    {acc}: {sc}")
    # Validate range
    assert all(0 <= v <= 100 for v in scores.values()), "Score out of range!"
    print("  PASS")
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()

# ----- Test 8: Ring risk -----
print("=" * 60)
print("TEST 8: Ring Risk Scoring")
try:
    all_rings = cycle_rings + smurfing_rings + shell_rings
    all_rings = compute_ring_risk(all_rings, scores)
    for r in all_rings[:3]:
        print(f"    {r['ring_id']}: type={r['pattern_type']} risk={r['risk_score']}")
    print("  PASS")
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()

# ----- Test 9: Full pipeline -----
print("=" * 60)
print("TEST 9: Full Pipeline (run_pipeline)")
try:
    result = run_pipeline(df)
    s = result["summary"]
    print(f"  total_accounts_analyzed: {s['total_accounts_analyzed']}")
    print(f"  suspicious_accounts_flagged: {s['suspicious_accounts_flagged']}")
    print(f"  fraud_rings_detected: {s['fraud_rings_detected']}")
    print(f"  processing_time_seconds: {s['processing_time_seconds']}")

    # Validate schema
    assert "suspicious_accounts" in result, "Missing suspicious_accounts"
    assert "fraud_rings" in result, "Missing fraud_rings"
    assert "summary" in result, "Missing summary"
    assert "graph" in result, "Missing graph"
    assert "nodes" in result["graph"], "Missing graph.nodes"
    assert "edges" in result["graph"], "Missing graph.edges"

    for a in result["suspicious_accounts"]:
        assert a["ring_id"] is not None, f"Null ring_id for {a['account_id']}"
        assert 0 <= a["suspicion_score"] <= 100, f"Score {a['suspicion_score']} out of range"

    for r in result["fraud_rings"]:
        assert "risk_score" in r, f"Missing risk_score in {r['ring_id']}"

    print("  PASS: All schema validations OK")
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()

# ----- Test 10: JSON serialization -----
print("=" * 60)
print("TEST 10: JSON Serialization")
try:
    json_str = json.dumps(result)
    print(f"  JSON size: {len(json_str)} chars")
    parsed_back = json.loads(json_str)
    print("  PASS: Round-trip OK")
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()

# ----- Test 11: Invalid CSV -----
print("=" * 60)
print("TEST 11: Invalid CSV handling")
try:
    bad_df = pd.DataFrame({"wrong_col": [1, 2]})
    parse_csv(bad_df)
    print("  FAIL: Should have raised ValueError")
except ValueError as ve:
    print(f"  PASS: Correctly raised ValueError: {ve}")
except Exception as e:
    print(f"  FAIL: Wrong exception type: {e}")
    traceback.print_exc()

# ----- Test 12: FastAPI app import -----
print("=" * 60)
print("TEST 12: FastAPI app import")
try:
    from main import app
    print(f"  App title: {app.title}")
    print(f"  Routes: {[r.path for r in app.routes]}")
    print("  PASS")
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()

print("=" * 60)
print("ALL TESTS COMPLETE")
