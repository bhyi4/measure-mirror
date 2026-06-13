#!/usr/bin/env python3
"""🪞 verify-self — verify ONE measure-mirror claims ledger + its external anchors.

This is the measure-mirror layer of verification: it needs nothing but this repo.
  L1 self-chain     : prev_seal→seal linkage (format-agnostic) + mm native seal verification
  L3 external anchor : stored snapshots vs current ledger — intact / extended / REPLACED?

Zero external-tool dependency by design — no `am`, no subprocess, no other mirror.
Cross-witness (L2) lives one layer up, in the stack orchestrator (verify_all.py), because
witnessing is *between* mirrors and is not measure-mirror's job.

usage: verify_self.py LEDGER.jsonl [ANCHOR_DIR]   (defaults to bundled evidence/)
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OK, FAIL, WARN = "✅", "❌", "⚠️"


def load_jsonl(path):
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def generic_linkage(path, name, report):
    """Format-agnostic prev_seal→seal linkage check (works on any mirror ledger)."""
    try:
        entries = load_jsonl(path)
    except OSError as e:
        report(FAIL, "L1 chain", name, f"ledger unreadable: {e}")
        return None
    prev = None
    for i, e in enumerate(entries):
        declared_prev = str(e.get("prev_seal", ""))
        if i == 0:
            if declared_prev.lower() != "genesis":
                report(WARN, "L1 chain", name, f"first entry prev_seal={declared_prev!r} (not genesis)")
        elif declared_prev != prev:
            report(FAIL, "L1 chain", name,
                   f"linkage broken at entry {i}: prev_seal={declared_prev} != {prev}")
            return entries
        prev = str(e.get("seal", ""))
    report(OK, "L1 chain", name, f"linkage intact — {len(entries)} entries, head={prev[:16]}")
    return entries


def mm_self_verify(path, name, report):
    """Recompute mm seals via the measure_mirror package (same repo, zero-dep core)."""
    try:
        sys.path.insert(0, str(HERE.parent))
        from measure_mirror.mm import verify_chain
        findings = verify_chain(str(path))
        bad = [f for f in findings if getattr(f, "level", "OK") not in ("OK", "INFO")]
        if bad:
            report(FAIL, "L1 chain", name, f"mm verify_chain: {[str(f) for f in bad]}")
        else:
            report(OK, "L1 chain", name, "mm verify_chain: seals valid")
    except Exception as e:
        report(WARN, "L1 chain", name, f"mm lib unavailable, linkage-only ({e})")


def anchor_check(anchor_file, report):
    a = json.loads(Path(anchor_file).read_text())
    lp = Path(a["ledger_path"])
    if not lp.exists():  # bundled evidence: fall back to a copy next to the anchor
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


def verify_self(ledger, anchor_dir, report):
    """Run L1+L3 for a single mm ledger. Returns nothing; appends via report()."""
    if generic_linkage(ledger, Path(ledger).stem, report) is not None:
        mm_self_verify(ledger, Path(ledger).stem, report)
    for f in sorted(Path(anchor_dir).glob("anchor_*.json")):
        anchor_check(f, report)


def main():
    ledger = sys.argv[1] if len(sys.argv) > 1 else str(HERE / "evidence/compute_governor.jsonl")
    anchor_dir = sys.argv[2] if len(sys.argv) > 2 else str(HERE / "evidence")
    results = []

    def report(level, layer, name, msg):
        results.append(level == OK)
        print(f"{level} [{layer}] {name}: {msg}")

    print("=== verify-self (measure-mirror: L1 chain + L3 anchors) ===")
    verify_self(ledger, anchor_dir, report)
    n_ok = sum(results)
    verdict = "ALL OK" if n_ok == len(results) else "FAILURES PRESENT"
    print(f"=== verdict: {verdict} ({n_ok}/{len(results)}) ===")
    sys.exit(0 if n_ok == len(results) else 1)


if __name__ == "__main__":
    main()
