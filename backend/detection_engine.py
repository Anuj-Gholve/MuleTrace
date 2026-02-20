"""
detection_engine.py  — OPTIMIZED
Core graph-based financial crime detection algorithms.

Performance optimizations vs original:
  - parse_csv: vectorized pandas + itertuples (10-50x faster than iterrows)
  - cycle detection: set-based visited tracking, tuple paths
  - smurfing: early exits, pre-length checks
  - pass-through: two-pointer merge instead of nested loop
  - temporal burst: single-pass sliding window
  - _account_patterns: pre-built account→ring index (O(1) lookups)
"""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import timedelta
from typing import Any

import pandas as pd


# ---------------------------------------------------------------------------
# STEP 1 — Parse CSV & build graph structures  (OPTIMIZED)
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS = {"transaction_id", "sender_id", "receiver_id", "amount", "timestamp"}


def parse_csv(df: pd.DataFrame) -> dict[str, Any]:
    """Vectorized CSV parsing. O(E) with minimal Python-level iteration."""
    df.columns = df.columns.str.strip()

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {missing}")

    df = df.copy()
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="%Y-%m-%d %H:%M:%S", errors="coerce")

    if df["amount"].isna().any():
        raise ValueError("Column 'amount' contains non-numeric values.")
    if df["timestamp"].isna().any():
        raise ValueError("Column 'timestamp' contains values not matching YYYY-MM-DD HH:MM:SS.")

    # Vectorized strip
    for col in ("transaction_id", "sender_id", "receiver_id"):
        df[col] = df[col].astype(str).str.strip()

    # Convert timestamps to Python datetimes once (vectorized)
    import numpy as np
    timestamps = np.array(df["timestamp"].dt.to_pydatetime())

    adjacency_list: dict[str, list[str]] = defaultdict(list)
    reverse_adjacency: dict[str, list[str]] = defaultdict(list)
    account_incoming: dict[str, list[dict]] = defaultdict(list)
    account_outgoing: dict[str, list[dict]] = defaultdict(list)
    all_accounts: set[str] = set()

    # itertuples is 10-50x faster than iterrows
    for row in df.itertuples(index=True):
        idx = row.Index
        sender = row.sender_id
        receiver = row.receiver_id
        ts = timestamps[idx]

        txn = {
            "transaction_id": row.transaction_id,
            "sender_id": sender,
            "receiver_id": receiver,
            "amount": float(row.amount),
            "timestamp": ts,
        }
        adjacency_list[sender].append(receiver)
        reverse_adjacency[receiver].append(sender)
        account_outgoing[sender].append(txn)
        account_incoming[receiver].append(txn)
        all_accounts.add(sender)
        all_accounts.add(receiver)

    return {
        "adjacency_list": dict(adjacency_list),
        "reverse_adjacency": dict(reverse_adjacency),
        "account_incoming": dict(account_incoming),
        "account_outgoing": dict(account_outgoing),
        "all_accounts": all_accounts,
        "edge_count": len(df),
    }


# ---------------------------------------------------------------------------
# STEP 2 — Precompute Metrics
# ---------------------------------------------------------------------------

def precompute_metrics(graph_data: dict[str, Any]) -> dict[str, dict]:
    adj = graph_data["adjacency_list"]
    rev = graph_data["reverse_adjacency"]
    inc = graph_data["account_incoming"]
    out = graph_data["account_outgoing"]

    metrics: dict[str, dict] = {}
    for acc in graph_data["all_accounts"]:
        out_deg = len(adj.get(acc, []))
        in_deg = len(rev.get(acc, []))
        incoming = sorted(inc.get(acc, []), key=lambda t: t["timestamp"])
        outgoing = sorted(out.get(acc, []), key=lambda t: t["timestamp"])
        metrics[acc] = {
            "in_degree": in_deg,
            "out_degree": out_deg,
            "total_degree": in_deg + out_deg,
            "incoming_sorted": incoming,
            "outgoing_sorted": outgoing,
        }
    return metrics


# ---------------------------------------------------------------------------
# STEP 3 — Cycle Detection (length 3-5)  — iterative DFS
# ---------------------------------------------------------------------------

def detect_cycles(
    adjacency_list: dict[str, list[str]],
    all_accounts: set[str],
    ring_counter: list[int],
) -> tuple[list[dict], set[str]]:
    found_cycles: set[tuple[str, ...]] = set()
    rings: list[dict] = []
    suspicious: set[str] = set()
    nodes = sorted(all_accounts)

    for start in nodes:
        neighbors = adjacency_list.get(start)
        if not neighbors:
            continue
        # DFS stack: (current_node, path_tuple)
        stack = [(start, (start,))]
        while stack:
            node, path = stack.pop()
            depth = len(path)
            if depth > 5:
                continue
            for nb in adjacency_list.get(node, ()):
                if nb == start and depth >= 3:
                    min_node = min(path)
                    if min_node != start:
                        continue
                    idx = path.index(min_node)
                    canonical = path[idx:] + path[:idx]
                    if canonical not in found_cycles:
                        found_cycles.add(canonical)
                        ring_counter[0] += 1
                        rings.append({
                            "ring_id": f"RING_{ring_counter[0]:03d}",
                            "member_accounts": list(canonical),
                            "pattern_type": "cycle",
                            "detected_pattern": f"cycle_length_{len(canonical)}",
                        })
                        suspicious.update(canonical)
                elif nb not in path and depth < 5:
                    stack.append((nb, path + (nb,)))

    return rings, suspicious


# ---------------------------------------------------------------------------
# STEP 4 — Smurfing Detection (72h sliding window)
# ---------------------------------------------------------------------------

_WINDOW_DELTA = timedelta(hours=72)
_MIN_UNIQUE = 10
_DENSITY_THRESHOLD_MINUTES = 45  # avg gap below this = suspicious clustering


def _sliding_window_check(transactions: list[dict], partner_key: str) -> bool:
    n = len(transactions)
    if n < _MIN_UNIQUE:
        return False

    left = 0
    counts: dict[str, int] = defaultdict(int)
    unique = 0

    for right in range(n):
        p = transactions[right][partner_key]
        if counts[p] == 0:
            unique += 1
        counts[p] += 1

        while transactions[right]["timestamp"] - transactions[left]["timestamp"] > _WINDOW_DELTA:
            lp = transactions[left][partner_key]
            counts[lp] -= 1
            if counts[lp] == 0:
                unique -= 1
            left += 1

        if unique >= _MIN_UNIQUE:
            return True
    return False


def _is_time_clustered(
    transactions: list[dict],
    threshold_minutes: float = _DENSITY_THRESHOLD_MINUTES,
) -> bool:
    """Return True if transactions are suspiciously clustered in time.

    Computes the average gap between consecutive (already-sorted) transactions.
    A small average gap indicates automated, rapid-fire deposits (smurfing),
    whereas a larger gap spread over a business day indicates normal merchant
    activity.
    """
    if len(transactions) < 2:
        return False
    first_ts = transactions[0]["timestamp"]
    last_ts = transactions[-1]["timestamp"]
    span_minutes = (last_ts - first_ts).total_seconds() / 60.0
    avg_gap = span_minutes / (len(transactions) - 1)
    return avg_gap < threshold_minutes


def detect_smurfing(
    metrics: dict[str, dict], ring_counter: list[int],
) -> tuple[list[dict], set[str], set[str]]:
    rings: list[dict] = []
    fan_in: set[str] = set()
    fan_out: set[str] = set()

    for acc, m in metrics.items():
        if (len(m["incoming_sorted"]) >= _MIN_UNIQUE
                and _sliding_window_check(m["incoming_sorted"], "sender_id")
                and _is_time_clustered(m["incoming_sorted"])):
            fan_in.add(acc)
            ring_counter[0] += 1
            senders = sorted({t["sender_id"] for t in m["incoming_sorted"]})
            rings.append({
                "ring_id": f"RING_{ring_counter[0]:03d}",
                "member_accounts": [acc] + senders,
                "pattern_type": "smurfing",
                "detected_pattern": "fan_in_72h",
            })

        if (len(m["outgoing_sorted"]) >= _MIN_UNIQUE
                and _sliding_window_check(m["outgoing_sorted"], "receiver_id")
                and _is_time_clustered(m["outgoing_sorted"])):
            fan_out.add(acc)
            ring_counter[0] += 1
            receivers = sorted({t["receiver_id"] for t in m["outgoing_sorted"]})
            rings.append({
                "ring_id": f"RING_{ring_counter[0]:03d}",
                "member_accounts": [acc] + receivers,
                "pattern_type": "smurfing",
                "detected_pattern": "fan_out_72h",
            })

    return rings, fan_in, fan_out


# ---------------------------------------------------------------------------
# STEP 5 — Shell Network Detection
# ---------------------------------------------------------------------------

def detect_shell_networks(
    adjacency_list: dict[str, list[str]],
    metrics: dict[str, dict],
    all_accounts: set[str],
    ring_counter: list[int],
) -> tuple[list[dict], set[str]]:
    rings: list[dict] = []
    suspicious: set[str] = set()
    found: set[tuple[str, ...]] = set()

    candidates = [a for a in all_accounts if metrics[a]["total_degree"] >= 3]

    for start in candidates:
        stack = [(start, (start,))]
        while stack:
            node, path = stack.pop()
            if len(path) > 4:
                continue
            for nb in adjacency_list.get(node, ()):
                if nb in path:
                    continue
                new_path = path + (nb,)
                if len(new_path) >= 4:
                    end = new_path[-1]
                    intermediates = new_path[1:-1]
                    if (metrics[end]["total_degree"] >= 3
                            and all(metrics[n]["total_degree"] <= 2 for n in intermediates)):
                        if new_path not in found:
                            found.add(new_path)
                            ring_counter[0] += 1
                            rings.append({
                                "ring_id": f"RING_{ring_counter[0]:03d}",
                                "member_accounts": list(new_path),
                                "pattern_type": "shell_chain",
                                "detected_pattern": "shell_chain",
                            })
                            suspicious.update(new_path)
                if len(new_path) < 5:
                    stack.append((nb, new_path))

    return rings, suspicious


# ---------------------------------------------------------------------------
# STEP 5B — Rapid Pass-Through (OPTIMIZED — two-pointer)
# ---------------------------------------------------------------------------

_PT_WINDOW = timedelta(hours=24)
_PT_TOL = 0.15  # 15% amount tolerance


def detect_rapid_passthrough(
    metrics: dict[str, dict], ring_counter: list[int],
) -> tuple[list[dict], set[str]]:
    rings: list[dict] = []
    suspicious: set[str] = set()

    for acc, m in metrics.items():
        incoming = m["incoming_sorted"]
        outgoing = m["outgoing_sorted"]
        if not incoming or not outgoing:
            continue

        partners: set[str] = set()
        matches = 0
        out_start = 0  # two-pointer index into outgoing

        for in_txn in incoming:
            in_ts = in_txn["timestamp"]
            in_amt = in_txn["amount"]
            in_sender = in_txn["sender_id"]
            if in_amt <= 0:
                continue

            # Advance out_start to first outgoing >= in_ts
            while out_start < len(outgoing) and outgoing[out_start]["timestamp"] < in_ts:
                out_start += 1

            # Scan forward within window
            j = out_start
            while j < len(outgoing):
                out_txn = outgoing[j]
                delta = out_txn["timestamp"] - in_ts
                if delta > _PT_WINDOW:
                    break
                if out_txn["receiver_id"] != in_sender:
                    if abs(out_txn["amount"] - in_amt) / in_amt <= _PT_TOL:
                        matches += 1
                        partners.add(in_sender)
                        partners.add(out_txn["receiver_id"])
                        break  # one match per incoming txn is enough
                j += 1

            if matches >= 2:
                # Early exit — already flagged
                break

        if matches >= 2:
            suspicious.add(acc)
            ring_counter[0] += 1
            rings.append({
                "ring_id": f"RING_{ring_counter[0]:03d}",
                "member_accounts": sorted({acc} | partners),
                "pattern_type": "passthrough",
                "detected_pattern": "rapid_passthrough_24h",
            })

    return rings, suspicious


# ---------------------------------------------------------------------------
# STEP 5C — Temporal Burst (OPTIMIZED — single pass)
# ---------------------------------------------------------------------------

_BURST_WINDOW = timedelta(hours=1)
_BURST_MIN = 5


def detect_temporal_bursts(
    metrics: dict[str, dict], ring_counter: list[int],
) -> tuple[list[dict], set[str]]:
    rings: list[dict] = []
    suspicious: set[str] = set()

    for acc, m in metrics.items():
        total_txns = len(m["incoming_sorted"]) + len(m["outgoing_sorted"])
        if total_txns < _BURST_MIN:
            continue

        # Merge timestamps only (lightweight)
        all_ts = []
        for t in m["incoming_sorted"]:
            all_ts.append((t["timestamp"], t["sender_id"]))
        for t in m["outgoing_sorted"]:
            all_ts.append((t["timestamp"], t["receiver_id"]))
        all_ts.sort(key=lambda x: x[0])

        left = 0
        max_burst = 0
        burst_partners: set[str] = set()

        for right in range(len(all_ts)):
            while all_ts[right][0] - all_ts[left][0] > _BURST_WINDOW:
                left += 1
            burst = right - left + 1
            if burst > max_burst:
                max_burst = burst
            if burst >= _BURST_MIN:
                for i in range(left, right + 1):
                    burst_partners.add(all_ts[i][1])

        if max_burst >= _BURST_MIN:
            suspicious.add(acc)
            ring_counter[0] += 1
            rings.append({
                "ring_id": f"RING_{ring_counter[0]:03d}",
                "member_accounts": sorted({acc} | burst_partners),
                "pattern_type": "temporal_burst",
                "detected_pattern": "burst_1h",
            })

    return rings, suspicious


# ---------------------------------------------------------------------------
# STEP 6 — Suspicion Scoring
# ---------------------------------------------------------------------------

def compute_suspicion_scores(
    all_accounts: set[str],
    cycle_sus: set[str],
    fan_in: set[str],
    fan_out: set[str],
    shell_sus: set[str],
    pt_sus: set[str],
    burst_sus: set[str],
) -> dict[str, float]:
    scores: dict[str, float] = {}
    for acc in all_accounts:
        s = 0.0
        if acc in cycle_sus:   s += 40
        if acc in fan_in:      s += 25
        if acc in fan_out:     s += 25
        if acc in shell_sus:   s += 20
        if acc in pt_sus:      s += 15
        if acc in burst_sus:   s += 10
        scores[acc] = min(s, 100.0)
    return scores


# ---------------------------------------------------------------------------
# STEP 7 — Ring Risk Score
# ---------------------------------------------------------------------------

_MULTIPLIERS = {"cycle": 1.3, "smurfing": 1.1, "shell_chain": 1.2, "passthrough": 1.15, "temporal_burst": 1.05}


def compute_ring_risk(rings: list[dict], scores: dict[str, float]) -> list[dict]:
    for r in rings:
        members = r["member_accounts"]
        avg = sum(scores.get(m, 0) for m in members) / max(len(members), 1)
        r["risk_score"] = round(avg * _MULTIPLIERS.get(r["pattern_type"], 1.0), 1)
    return rings


# ---------------------------------------------------------------------------
# STEP 8 — Build Output JSON  (OPTIMIZED — pre-built indexes)
# ---------------------------------------------------------------------------

def run_pipeline(df: pd.DataFrame) -> dict[str, Any]:
    t0 = time.time()

    # Steps 1-2
    graph_data = parse_csv(df)
    metrics = precompute_metrics(graph_data)

    # Steps 3-5C
    rc: list[int] = [0]
    cycle_rings, cycle_sus = detect_cycles(graph_data["adjacency_list"], graph_data["all_accounts"], rc)
    smurf_rings, fan_in, fan_out = detect_smurfing(metrics, rc)
    shell_rings, shell_sus = detect_shell_networks(graph_data["adjacency_list"], metrics, graph_data["all_accounts"], rc)
    pt_rings, pt_sus = detect_rapid_passthrough(metrics, rc)
    burst_rings, burst_sus = detect_temporal_bursts(metrics, rc)

    # Step 6
    scores = compute_suspicion_scores(graph_data["all_accounts"], cycle_sus, fan_in, fan_out, shell_sus, pt_sus, burst_sus)

    # Step 7
    all_rings = cycle_rings + smurf_rings + shell_rings + pt_rings + burst_rings
    all_rings = compute_ring_risk(all_rings, scores)

    # Step 8 — Build output with pre-indexed lookups
    suspicious_set = cycle_sus | fan_in | fan_out | shell_sus | pt_sus | burst_sus

    # Pre-build account → (patterns, ring_ids) index  O(total_ring_members)
    acc_patterns: dict[str, list[str]] = defaultdict(list)
    acc_ring_ids: dict[str, list[str]] = defaultdict(list)

    pattern_sets = {
        "cycle": cycle_sus, "fan_in_72h": fan_in, "fan_out_72h": fan_out,
        "shell_chain": shell_sus, "rapid_passthrough_24h": pt_sus, "burst_1h": burst_sus,
    }
    for label, s in pattern_sets.items():
        for acc in s:
            if label not in acc_patterns[acc]:
                acc_patterns[acc].append(label)

    # Override cycle patterns with specific length labels
    for r in cycle_rings:
        for acc in r["member_accounts"]:
            if r["detected_pattern"] not in acc_patterns[acc]:
                acc_patterns[acc].append(r["detected_pattern"])
            # Remove generic "cycle" if present
            if "cycle" in acc_patterns[acc]:
                acc_patterns[acc].remove("cycle")

    for r in all_rings:
        for acc in r["member_accounts"]:
            if r["ring_id"] not in acc_ring_ids[acc]:
                acc_ring_ids[acc].append(r["ring_id"])

    suspicious_accounts: list[dict] = []
    for acc in sorted(suspicious_set):
        patterns = acc_patterns.get(acc, [])
        ring_ids = acc_ring_ids.get(acc, [])
        for rid in ring_ids:
            suspicious_accounts.append({
                "account_id": acc,
                "suspicion_score": round(scores[acc], 1),
                "detected_patterns": patterns,
                "ring_id": rid,
            })
        if not ring_ids:
            suspicious_accounts.append({
                "account_id": acc,
                "suspicion_score": round(scores[acc], 1),
                "detected_patterns": patterns,
                "ring_id": all_rings[-1]["ring_id"] if all_rings else "RING_001",
            })

    suspicious_accounts.sort(key=lambda x: x["suspicion_score"], reverse=True)

    elapsed = round(time.time() - t0, 2)

    # Graph data for frontend
    edge_set: set[tuple[str, str]] = set()
    edges: list[dict] = []
    for sender, receivers in graph_data["adjacency_list"].items():
        for receiver in receivers:
            key = (sender, receiver)
            if key not in edge_set:
                edge_set.add(key)
                edges.append({"source": sender, "target": receiver})

    nodes: list[dict] = []
    for acc in sorted(graph_data["all_accounts"]):
        m = metrics[acc]
        nodes.append({
            "id": acc,
            "in_degree": m["in_degree"],
            "out_degree": m["out_degree"],
            "total_degree": m["total_degree"],
            "suspicion_score": round(scores.get(acc, 0), 1),
            "is_suspicious": acc in suspicious_set,
            "detected_patterns": acc_patterns.get(acc, []),
        })

    return {
        "suspicious_accounts": suspicious_accounts,
        "fraud_rings": [
            {"ring_id": r["ring_id"], "member_accounts": r["member_accounts"],
             "pattern_type": r["pattern_type"], "risk_score": r["risk_score"]}
            for r in all_rings
        ],
        "summary": {
            "total_accounts_analyzed": len(graph_data["all_accounts"]),
            "suspicious_accounts_flagged": len(suspicious_set),
            "fraud_rings_detected": len(all_rings),
            "processing_time_seconds": elapsed,
        },
        "graph": {"nodes": nodes, "edges": edges},
    }
