#!/usr/bin/env python3
"""🪞🔎🪪 Mirror Stack verify-all — verify all mirror ledgers + joints in one command.

Layers:
  L1 self-chain    : prev_seal→seal linkage (format-agnostic) + native seal verification
  L2 cross-witness : witness ledger's pinned heads vs claims ledger's actual history
  L3 external anchor: stored snapshots vs current ledger — intact / extended / REPLACED?

Philosophy: this does not prevent dishonesty — it makes only honesty provable.
Sealed preregistrations and time-pinned witnesses cannot be fabricated retroactively.

Default config verifies the bundled evidence/ (see CASE_STUDY_compute_governor.md).
The witness (L2) ledger from the case study is a private family ledger and is not bundled;
pass your own via --config to enable L2. usage: verify_all.py [--config stack.json]
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = {
    "mm_ledgers": {"compute_governor_mm": str(HERE / "evidence/compute_governor.jsonl")},
    "am_ledger": None,
    "pm_ledger": None,
    "anchor_dirs": [str(HERE / "evidence")],
}

OK, FAIL, WARN = "✅", "❌", "⚠️"
results = []


def report(level, layer, name, msg):
    results.append(level == OK)
    print(f"{level} [{layer}] {name}: {msg}")


def load_jsonl(path):
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def generic_linkage(path, name, layer="L1 chain"):
    """Format-agnostic prev_seal→seal linkage check (works on any mirror ledger)."""
    try:
        entries = load_jsonl(path)
    except OSError as e:
        report(FAIL, layer, name, f"ledger unreadable: {e}")
        return None
    prev = None
    for i, e in enumerate(entries):
        declared_prev = str(e.get("prev_seal", ""))
        if i == 0:
            if declared_prev.lower() != "genesis":
                report(WARN, layer, name, f"first entry prev_seal={declared_prev!r} (not genesis)")
        elif declared_prev != prev:
            report(FAIL, layer, name,
                   f"linkage broken at entry {i}: prev_seal={declared_prev} != {prev}")
            return entries
        prev = str(e.get("seal", ""))
    report(OK, layer, name, f"linkage intact — {len(entries)} entries, head={prev[:16]}")
    return entries


def mm_self_verify(path, name):
    try:
        sys.path.insert(0, str(HERE.parent))  # measure_mirror package at repo root
        from measure_mirror.mm import verify_chain
        findings = verify_chain(str(path))
        bad = [f for f in findings if getattr(f, "level", "OK") not in ("OK", "INFO")]
        if bad:
            report(FAIL, "L1 chain", name, f"mm verify_chain: {[str(f) for f in bad]}")
        else:
            report(OK, "L1 chain", name, "mm verify_chain: seals valid")
    except Exception as e:
        report(WARN, "L1 chain", name, f"mm lib unavailable, linkage-only ({e})")


def am_self_verify(am_ledger):
    r = subprocess.run(["am", "--ledger", am_ledger, "verify"],
                       capture_output=True, text=True)
    ok = r.returncode == 0 and "OK" in r.stdout
    report(OK if ok else FAIL, "L1 chain", "am",
           "am verify: " + (r.stdout.strip().splitlines()[-1] if r.stdout else r.stderr.strip()))


def cross_witness(am_ledger, peer_name, peer_path):
    r = subprocess.run(["am", "--ledger", am_ledger, "verify-peer",
                        "--name", peer_name, peer_path],
                       capture_output=True, text=True)
    out = (r.stdout or r.stderr).strip().replace("\n", " | ")
    ok = r.returncode == 0 and ("OK" in out or "✅" in out or "consistent" in out.lower())
    report(OK if ok else FAIL, "L2 witness", peer_name, out)


def anchor_check(anchor_file):
    a = json.loads(Path(anchor_file).read_text())
    lp = Path(a["ledger_path"])
    if not lp.exists():  # bundled evidence: fall back to local copy next to the anchor
        lp = Path(anchor_file).parent / lp.name
    name = f"{Path(anchor_file).name}→{lp.name}"
    if not lp.exists():
        report(FAIL, "L3 anchor", name, "ledger missing")
        return
    cur = hashlib.sha256(lp.read_bytes()).hexdigest()
    if cur == a["anchor_hash"]:
        report(OK, "L3 anchor", name, f"intact (unchanged since {a['ts']})")
        return
    entries = load_jsonl(lp)
    n = a["entry_count"]
    if len(entries) >= n and str(entries[n - 1].get("seal", "")) == a["head_seal"]:
        report(OK, "L3 anchor", name,
               f"extended ({n}→{len(entries)} entries, anchored head still in chain)")
    else:
        report(FAIL, "L3 anchor", name,
               "REPLACED? anchored head_seal not found at anchored position")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    args = ap.parse_args()
    cfg = DEFAULT_CONFIG if not args.config else json.loads(Path(args.config).read_text())

    print("=== Mirror Stack verify-all ===")
    for name, path in cfg["mm_ledgers"].items():
        if generic_linkage(path, name) is not None:
            mm_self_verify(path, name)
    if cfg.get("am_ledger"):
        generic_linkage(cfg["am_ledger"], "am")
        am_self_verify(cfg["am_ledger"])
    else:
        print(f"{WARN} [L2 witness] skipped — no witness ledger configured "
              "(case-study witness ledger is private; see honesty box)")
    if cfg.get("pm_ledger"):
        generic_linkage(cfg["pm_ledger"], "pm")
    for name, path in cfg["mm_ledgers"].items():
        if cfg.get("am_ledger"):
            cross_witness(cfg["am_ledger"], name, path)
    for d in cfg.get("anchor_dirs", []):
        for f in sorted(Path(d).glob("anchor_*.json")):
            anchor_check(f)

    n_ok = sum(results)
    verdict = "ALL OK" if n_ok == len(results) else "FAILURES PRESENT"
    print(f"=== verdict: {verdict} ({n_ok}/{len(results)}) ===")
    sys.exit(0 if n_ok == len(results) else 1)


if __name__ == "__main__":
    main()
