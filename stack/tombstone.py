#!/usr/bin/env python3
"""🪦 tombstone — surface the SEALED FAILURES in a mirror ledger (the graveyard).

The mirror stack's least-advertised guarantee: you cannot silently delete a
failure. Retractions and negative verdicts are sealed into the same hash chain as
the wins, so a killed hypothesis stays on the record forever. This makes that
visible — it lists every sealed negative (retraction / KILL / NULL / falsified /
inconclusive) and verifies the chain is intact, i.e. none were removed afterward.

Why this matters: for a research-integrity tool, the graveyard IS the credibility.
A system that can quietly drop its failures proves nothing by showing its wins.

Honest scope (read before quoting it):
  ✓ proves: the listed failures are ON the record and — chain intact — none were
            deleted or altered after sealing (non-erasure).
  ✗ does NOT prove: that EVERY failure was recorded. A negative that was never
            sealed leaves no trace here. This is non-erasure of what was sealed,
            NOT completeness of what happened. (A missing ledger is itself a
            signal; absence *within* a ledger is not.)

usage: tombstone.py LEDGER.jsonl [LEDGER2.jsonl ...]
       (no args → the bundled evidence/ ledger)
"""
import re
import sys
from pathlib import Path

from verify_self import FAIL, OK, WARN, generic_linkage, load_jsonl

HERE = Path(__file__).resolve().parent

# Negative outcome tokens, matched at the START of a structured verdict (or of an
# explicit "VERDICT … = TOKEN" declaration). Start-anchored on purpose: a positive
# verdict like "supported (not falsified)" must NOT be mistaken for a tombstone.
_NEG = ("KILL", "KILLED", "NULL", "FALSIFIED", "NEGATIVE", "REJECTED",
        "CLOSED-NEGATIVE", "CLOSED_NEGATIVE", "RESOLVED-NEGATIVE", "RESOLVED_NEGATIVE")
_VERDICT_DECL = re.compile(r"VERDICT\b.*?=\s*([A-Za-z_-]+)", re.I)


def classify(e):
    """Return 'retraction' | 'kill' | 'inconclusive' | None for one ledger entry.

    Conservative by design: it trusts the STRUCTURED verdict (payload.verdict or an
    explicit 'VERDICT … = X' declaration), never free prose — under-detecting from
    narrative text beats over-claiming a tombstone that isn't one.
    """
    if e.get("_type") == "retraction":
        return "retraction"
    if e.get("_type") == "action":
        pv = e.get("payload")
        verdict = pv.get("verdict") if isinstance(pv, dict) else ""
        if not isinstance(verdict, str) or not verdict:   # verdict may be absent or a nested dict
            m = _VERDICT_DECL.search(e.get("action", "") or "")
            verdict = m.group(1) if m else ""
        vu = verdict.strip().upper()
        if vu.startswith("INCONCLUSIVE"):
            return "inconclusive"
        if vu.startswith(_NEG):
            return "kill"
    return None


_MARK = {"retraction": "⚰️  retraction", "kill": "🪦  kill/negative",
         "inconclusive": "⊘  inconclusive"}


def collect(entries):
    graves = []
    for e in entries:
        kind = classify(e)
        if not kind:
            continue
        ident = e.get("claim_id") or e.get("target") or (e.get("action", "") or "")[:48]
        why = e.get("reason") or (e.get("action", "") or "")
        graves.append((kind, str(ident), str(why).strip().replace("\n", " "),
                       str(e.get("seal", ""))[:12], e.get("ts", "")))
    return graves


def render(ledger):
    name = Path(ledger).stem
    chain_ok = {"v": True}

    def report(level, layer, nm, msg):
        if level != OK:
            chain_ok["v"] = False
        print(f"   {level} [{layer}] {msg}")

    print(f"\n=== 🪦 {name} ===")
    entries = generic_linkage(ledger, name, report)          # proves nothing was deleted
    if entries is None:
        return 0, False
    graves = collect(entries)
    if not graves:
        print(f"   (no sealed negatives in {len(entries)} entries)")
        return 0, chain_ok["v"]
    for kind, ident, why, seal, ts in graves:
        print(f"   {_MARK[kind]}  {seal}  {ident}")
        if why and why != ident:
            print(f"        ↳ {why[:110]}")
        if ts:
            print(f"        ({ts})")
    guarantee = ("chain intact → none of these were deleted or altered after sealing"
                 if chain_ok["v"] else
                 "⚠️ CHAIN BROKEN → cannot guarantee the record is complete")
    print(f"   — {len(graves)} sealed negative(s); {guarantee}")
    return len(graves), chain_ok["v"]


def main():
    ledgers = sys.argv[1:] or [str(HERE / "evidence/compute_governor.jsonl")]
    print("=== 🪦 tombstone — sealed failures (non-erasure view) ===")
    total, all_chains_ok = 0, True
    for lg in ledgers:
        n, ok = render(lg)
        total += n
        all_chains_ok = all_chains_ok and ok
    print(f"\n=== {total} sealed negative(s) across {len(ledgers)} ledger(s); "
          f"chains: {'all intact' if all_chains_ok else 'BREAK DETECTED'} ===")
    print("scope: non-erasure of what was sealed — NOT completeness of what happened.")
    sys.exit(0 if all_chains_ok else 1)


if __name__ == "__main__":
    main()
