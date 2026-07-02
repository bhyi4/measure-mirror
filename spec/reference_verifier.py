#!/usr/bin/env python3
"""MIRROR-SPEC v1 reference verifier — single file, zero dependencies.

Implements the normative verification levels of docs/SPEC.md:
  L1  linkage check          (SPEC §6.1) — declared-seal chain, format-agnostic
  L1+ seal recomputation     (SPEC §4, §6.2)
  L2  peer-witness check     (SPEC §6.3)

Usage:
  python reference_verifier.py <ledger.jsonl>                 # L1 + L1+
  python reference_verifier.py <witness.jsonl> --peer <peer.jsonl>   # + L2
  python reference_verifier.py --vectors <vectors_dir>        # conformance run

Exit code 0 iff every check is OK (or every vector matches expected.json).
This file is a *reference implementation*; docs/SPEC.md is the source of truth.
"""
import hashlib
import json
import sys


def compute_seal(entry):
    """SPEC §4: SHA-256 over sorted-key, non-ASCII-preserving JSON, 16 hex chars."""
    body = {k: v for k, v in entry.items() if k not in ("seal", "sig")}
    serialized = json.dumps(body, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def l1_linkage(path):
    """SPEC §6.1. Returns (ok, message, entries|None)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = [ln for ln in f.read().splitlines() if ln.strip()]
    except OSError as e:
        return False, f"ledger unreadable: {e}", None
    try:
        entries = [json.loads(ln) for ln in lines]
    except json.JSONDecodeError as e:
        return False, f"malformed JSON: {e}", None
    # SPEC §3.1: non-object JSON lines are malformed, same as unparseable JSON
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            return False, f"malformed JSON: entry {i} is not an object", None
    if not entries:
        return False, "ledger is empty", []
    prev = None
    for i, entry in enumerate(entries):
        declared = str(entry.get("prev_seal", ""))
        if i == 0:
            if declared.lower() != "genesis":  # SPEC §5.1: case-insensitive
                return False, f"first entry prev_seal={declared!r} is not 'genesis'", entries
        elif declared != prev:
            return False, f"linkage broken at entry {i}: prev_seal {declared} != {prev}", entries
        prev = str(entry.get("seal", ""))
    return True, f"linkage intact — {len(entries)} entries, head={prev}", entries


def l1_recompute(entries):
    """SPEC §6.2. Returns (ok, message)."""
    for i, entry in enumerate(entries):
        expected = compute_seal(entry)
        if entry.get("seal") != expected:
            return False, f"seal mismatch at entry {i}: declared {entry.get('seal')}, recomputed {expected}"
    return True, f"all {len(entries)} seals recompute correctly"


def l2_peer_witness(witness_entries, peer_entries):
    """SPEC §6.3. Returns (level, message) where level is OK|WARN|FAIL."""
    peer = peer_entries or []
    pins = [w for w in witness_entries if w.get("_type") == "peer_witness"]
    if not pins:
        return "WARN", "no peer_witness entries — peer unverifiable"
    for w in pins:
        n = int(w.get("peer_entries", 0))
        if len(peer) < n:
            return "FAIL", f"TRUNCATED: peer has {len(peer)} entries < witnessed {n}"
        if str(peer[n - 1].get("seal", "")) != str(w.get("peer_head_seal", "")):
            return "FAIL", f"REWRITTEN: seal at witnessed position {n - 1} differs from pinned head"
    return "OK", f"{len(pins)} pinned head(s) consistent — append-only history respected"


def verify(path, peer_path=None):
    """Full single-ledger verification. Returns (all_ok, findings list)."""
    findings = []
    ok, msg, entries = l1_linkage(path)
    findings.append(("L1", "OK" if ok else "FAIL", msg))
    if ok:
        rok, rmsg = l1_recompute(entries)
        findings.append(("L1+", "OK" if rok else "FAIL", rmsg))
        ok = ok and rok
    if peer_path is not None and entries:
        pok, pmsg, peer = l1_linkage(peer_path)
        level, wmsg = l2_peer_witness(entries, peer if pok else [])
        findings.append(("L2", level, wmsg))
        ok = ok and level != "FAIL"
    return ok, findings


def run_vectors(vectors_dir):
    """Conformance run against expected.json. Returns exit code."""
    import os
    with open(os.path.join(vectors_dir, "expected.json"), encoding="utf-8") as f:
        expected = json.load(f)
    mismatches = []
    for name, exp in sorted(expected.items()):
        path = os.path.join(vectors_dir, name)
        ok, msg, entries = l1_linkage(path)
        checks = [("L1", exp.get("L1"), "OK" if ok else "FAIL", msg)]
        if "L1_seal_recompute" in exp and entries:
            rok, rmsg = l1_recompute(entries)
            checks.append(("L1_seal_recompute", exp["L1_seal_recompute"],
                           "OK" if rok else "FAIL", rmsg))
        for key in exp:
            if key.startswith("L2_vs_"):
                other = os.path.join(vectors_dir, key[len("L2_vs_"):] )
                _, _, other_entries = l1_linkage(other)
                # witness role: whichever file holds peer_witness entries
                wit = entries if any(e.get("_type") == "peer_witness" for e in entries or []) else other_entries
                peer = other_entries if wit is entries else entries
                level, wmsg = l2_peer_witness(wit or [], peer or [])
                checks.append((key, exp[key], level, wmsg))
        for check, want, got, msg in checks:
            if want is None:
                continue
            mark = "✓" if got == want else "✗"
            print(f"{mark} {name} [{check}]: expected {want}, got {got} ({msg})")
            if got != want:
                mismatches.append((name, check, want, got))
    print()
    if mismatches:
        print(f"CONFORMANCE: {len(mismatches)} MISMATCH(ES)")
        return 1
    print("CONFORMANCE: ALL VECTORS MATCH")
    return 0


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] == "--vectors":
        return run_vectors(argv[1])
    peer = None
    if "--peer" in argv:
        i = argv.index("--peer")
        peer = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    ok, findings = verify(argv[0], peer)
    for level_name, level, msg in findings:
        print(f"[{level_name}] {level}: {msg}")
    print(f"verdict: {'OK' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
