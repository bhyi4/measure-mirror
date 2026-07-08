#!/usr/bin/env python3
"""Measure measure-mirror's OWN false-positive / false-negative rate.

Feeds a labeled set (cases.jsonl) through the REAL probe functions and tallies:
  defective + flagged -> TP      defective + passed -> FN
  clean     + flagged -> FP      clean     + passed -> TN
"flagged" = probe level in {FAIL, WARN}.  "passed" = OK.

Two buckets reported separately (pre-registered):
  core                  -> in-scope; FP/FN here = real reliability number.
  known_limitation_trap -> disclosed limitations (near-dup leakage, n-blind
                           baseline, exact-match scope); FN/FP here is EXPECTED
                           and quantifies the limitation, not a surprise.

HONESTY SCOPE: constructor knew the probe logic -> this is CALIBRATION on
hand-built cases, NOT field FP/FN. Probes are deterministic pure functions ->
results are fully reproducible (cases.jsonl is hash-sealed in the ledger).
LLM-judge probes (consistency/bias/swap) are NOT covered here (need an LLM).

Run from anywhere:  python eval/self_fpfn/run_eval.py
"""
import sys, os, json, tempfile
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, REPO_ROOT)
import measure_mirror as mm  # noqa: E402

CASES = os.path.join(HERE, "cases.jsonl")


def small_sample_level(a):
    """Exercise the REAL audit() path; extract the small-sample/direction finding."""
    tmp = tempfile.mkdtemp()
    findings = mm.audit(
        os.path.join(tmp, "none.jsonl"), "eval_case",
        reported_metric="acc", reported_acc=a["reported_acc"], n=a["n"],
        baseline=a.get("baseline", 0.5), db_dir=tmp,  # empty db_dir -> no lookups
    )
    for f in findings:
        if f.probe.startswith("④a small-sample") or f.probe.startswith("④a direction"):
            return f.level
    return "OK"


def probe_level(probe, a):
    if probe == "small_sample":     return small_sample_level(a)
    if probe == "grim":             return mm.grim_check(a["reported_acc"], a["n"]).level
    if probe == "leakage":          return mm.leakage_check(a["train"], a["test"]).level
    if probe == "baseline_fairness":return mm.baseline_fairness("case", a["claimed"], a["baseline"], n=a.get("intended_n")).level
    if probe == "gaming":           return mm.gaming_check(a["metric"], a["reward_terms"]).level
    if probe == "multiseed":        return mm.multiseed_check(a["seeds"]).level
    if probe == "scope":            return mm.scope_check(a["claimed_scope"], a["tested_scope"]).level
    if probe == "too_good":         return mm.too_good_check("case", a["claimed"], a["baseline"]).level
    if probe == "power":            return mm.power_check(a["n"], a["baseline"]).level
    if probe == "anchor_basis":     return mm.anchor_basis_check(a["anchor_basis"]).level
    if probe == "threshold_provenance": return mm.threshold_provenance_check(a["threshold_source"]).level
    if probe == "content_delta":    return mm.content_delta_check(a["judgment_basis"]).level
    raise ValueError(f"unknown probe {probe}")


def classify(label, level):
    flagged = level in ("FAIL", "WARN")
    if label == "defective":
        return "TP" if flagged else "FN"
    return "FP" if flagged else "TN"


def tally(rows):
    c = Counter(r["outcome"] for r in rows)
    tp, fn, fp, tn = c["TP"], c["FN"], c["FP"], c["TN"]
    return {
        "n": len(rows), "TP": tp, "FN": fn, "FP": fp, "TN": tn,
        "fn_rate": (fn / (tp + fn)) if (tp + fn) else None,
        "fp_rate": (fp / (fp + tn)) if (fp + tn) else None,
    }


def evaluate(cases_path=CASES):
    cases = [json.loads(l) for l in open(cases_path, encoding="utf-8")
             if l.strip() and '"probe"' in l]
    rows = []
    for c in cases:
        level = probe_level(c["probe"], c["args"])
        rows.append({
            "id": c["id"], "probe": c["probe"], "label": c["label"],
            "bucket": c["bucket"], "level": level,
            "outcome": classify(c["label"], level),
        })

    core = [r for r in rows if r["bucket"] == "core"]
    trap = [r for r in rows if r["bucket"] == "known_limitation_trap"]

    return {
        "n_cases": len(rows),
        "core": tally(core),
        "trap": tally(trap),
        "trap_detail": [
            {"id": r["id"], "probe": r["probe"], "label": r["label"],
             "level": r["level"], "outcome": r["outcome"]} for r in trap
        ],
        "unexpected_core": [r for r in core if r["outcome"] in ("FP", "FN")],
        "rows": rows,
    }


def main():
    print(json.dumps(evaluate(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
