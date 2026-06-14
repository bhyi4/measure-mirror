#!/usr/bin/env python3
"""Run the v2 oracle-labeled set through the REAL probes; report per-probe
FP/FN vs the INDEPENDENT oracle, each with a Wilson CI (computed by the tool's
own wilson_ci — dogfood). Lists every disagreement (probe != oracle).

grim         : disagreement = a real bug (the 2-candidate shortcut should be
               complete vs a full brute-force k-sweep).
small_sample : disagreement = the Wilson/score-CI approximation vs the exact
               binomial test. FN = probe PASSES what exact flags as chance
               (over-optimistic); FP = probe FLAGS what exact calls significant.

Run from anywhere:  python eval/self_fpfn/v2/analyze_v2.py
"""
import sys, os, json, tempfile
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..")))
import measure_mirror as mm
import measure_mirror.mm as mmcore

CASES = os.path.join(HERE, "cases_v2.jsonl")
_EMPTY_DB = tempfile.mkdtemp()  # reused: forces no db lookups in audit()


def small_sample_level(a):
    findings = mm.audit(os.path.join(_EMPTY_DB, "none.jsonl"), "c",
                        reported_metric="acc", reported_acc=a["reported_acc"],
                        n=a["n"], baseline=a.get("baseline", 0.5), db_dir=_EMPTY_DB)
    for f in findings:
        if f.probe.startswith("④a small-sample") or f.probe.startswith("④a direction"):
            return f.level
    return "OK"


def probe_level(probe, a):
    if probe == "small_sample": return small_sample_level(a)
    if probe == "grim":         return mmcore.grim_check(a["reported_acc"], a["n"]).level
    raise ValueError(probe)


def classify(label, level):
    flagged = level in ("FAIL", "WARN")
    if label == "defective":
        return "TP" if flagged else "FN"
    return "FP" if flagged else "TN"


def evaluate(cases_path=CASES):
    cases = [json.loads(l) for l in open(cases_path, encoding="utf-8")
             if l.strip() and '"probe"' in l]
    rows = []
    for c in cases:
        lvl = probe_level(c["probe"], c["args"])
        rows.append({**c, "level": lvl, "outcome": classify(c["label"], lvl)})

    out = {"n_cases": len(rows), "per_probe": {}, "disagreements": []}
    for probe in sorted({r["probe"] for r in rows}):
        rs = [r for r in rows if r["probe"] == probe]
        c = Counter(r["outcome"] for r in rs)
        tp, fn, fp, tn = c["TP"], c["FN"], c["FP"], c["TN"]
        fn_ci = mm.wilson_ci(fn, tp + fn) if (tp + fn) else None
        fp_ci = mm.wilson_ci(fp, fp + tn) if (fp + tn) else None
        out["per_probe"][probe] = {
            "n": len(rs), "TP": tp, "FN": fn, "FP": fp, "TN": tn,
            "fn_rate": round(fn / (tp + fn), 4) if (tp + fn) else None,
            "fn_ci95": [round(x, 4) for x in fn_ci] if fn_ci else None,
            "fp_rate": round(fp / (fp + tn), 4) if (fp + tn) else None,
            "fp_ci95": [round(x, 4) for x in fp_ci] if fp_ci else None,
        }
    for r in rows:
        if r["outcome"] in ("FP", "FN"):
            out["disagreements"].append({
                "id": r["id"], "probe": r["probe"], "args": r["args"],
                "label": r["label"], "level": r["level"], "outcome": r["outcome"],
                "oracle": r.get("oracle", ""),
            })
    return out


def main():
    print(json.dumps(evaluate(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
