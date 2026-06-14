#!/usr/bin/env python3
"""Generate a LARGE labeled set with oracles INDEPENDENT of the probe code,
to tighten the Wilson CI on the two probes that carry an approximation:

  grim         : oracle = full brute-force k-sweep (probe uses a 2-candidate
                 shortcut). Tests the shortcut is complete.
  small_sample : oracle = exact two-sided binomial test vs baseline (probe uses
                 a Wilson/score CI). Tests the approximation near the boundary —
                 this is where real FP/FN of the approximation live.

Ground truth is computed here from the DEFINITION, never by calling the probe.
Deterministic (no RNG) -> fully reproducible; cases_v2.jsonl is hash-sealed.
"""
import sys, os, json
from scipy.stats import binomtest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..")))
import measure_mirror.mm as mmcore  # for _infer_decimals (shared decimals convention)

OUT = os.path.join(HERE, "cases_v2.jsonl")
BASELINE = 0.5
ALPHA = 0.05


# ---- GRIM oracle: brute-force reachability over ALL integer k in [0,N] -------
def grim_reachable(acc, n):
    d = max(mmcore._infer_decimals(acc), 1)
    target = round(acc, d)
    return any(round(k / n, d) == target for k in range(0, n + 1))


def gen_grim():
    cases, cid = [], 0
    for n in range(3, 41):
        for d in (2, 3):
            reachable_vals, unreachable_vals, seen = [], [], set()
            for m in range(0, 10 ** d + 1):
                acc = round(m / 10 ** d, d)
                if acc > 1.0 or acc in seen:
                    continue
                seen.add(acc)
                (reachable_vals if grim_reachable(acc, n) else unreachable_vals).append(acc)
            for acc in reachable_vals[1:len(reachable_vals):max(1, len(reachable_vals)//2)][:2]:
                cid += 1
                cases.append({"id": f"g{cid:04d}", "probe": "grim", "label": "clean",
                              "bucket": "oracle_grim", "args": {"reported_acc": acc, "n": n},
                              "oracle": "bruteforce_reachable=True"})
            for acc in unreachable_vals[:len(unreachable_vals):max(1, len(unreachable_vals)//2)][:2]:
                cid += 1
                cases.append({"id": f"g{cid:04d}", "probe": "grim", "label": "defective",
                              "bucket": "oracle_grim", "args": {"reported_acc": acc, "n": n},
                              "oracle": "bruteforce_reachable=False"})
    return cases


# ---- small-sample oracle: EXACT two-sided binomial test vs baseline ----------
def smallsample_label(k, n):
    p = binomtest(k, n, BASELINE, alternative="two-sided").pvalue
    acc = k / n
    if p > ALPHA:
        return "defective", f"binom p={p:.4f}>α -> indistinguishable"
    if acc < BASELINE:
        return "defective", f"binom p={p:.4f}≤α & acc<base -> anti-signal"
    return "clean", f"binom p={p:.4f}≤α & acc>base -> real signal"


def gen_smallsample():
    cases, cid = [], 0
    ns = [5, 6, 7, 8, 9, 10, 12, 15, 18, 20, 25, 30, 40, 50, 60, 80, 100, 150, 200, 300]
    for n in ns:
        for k in range(0, n + 1):
            acc = k / n
            near = abs(acc - BASELINE) <= 0.30
            anchor = k in (0, n) or abs(acc - BASELINE) > 0.45
            if not (near or anchor):
                continue
            label, why = smallsample_label(k, n)
            cid += 1
            cases.append({"id": f"s{cid:04d}", "probe": "small_sample", "label": label,
                          "bucket": "oracle_smallsample",
                          "args": {"reported_acc": round(acc, 6), "n": n, "baseline": BASELINE},
                          "oracle": why})
    return cases


def build():
    return gen_grim() + gen_smallsample()


def main():
    cases = build()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(json.dumps({"_doc": "v2 oracle-labeled set. Ground truth from "
                            "INDEPENDENT oracles (grim=brute-force k-sweep, "
                            "small_sample=exact binomial test), never from the probe. "
                            "Deterministic. Tightens Wilson CI on the two "
                            "approximation-bearing probes."}, ensure_ascii=False) + "\n")
        for c in cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    from collections import Counter
    by = Counter((c["probe"], c["label"]) for c in cases)
    print(f"wrote {len(cases)} cases -> {OUT}")
    for k in sorted(by):
        print(f"  {k}: {by[k]}")


if __name__ == "__main__":
    main()
