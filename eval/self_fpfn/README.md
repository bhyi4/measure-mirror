# self_fpfn — measuring the tool's own FP/FN

The deepest fair critique of a measurement-integrity tool is: *who measures the
measurer?* The `db/curated/` case libraries are **anecdotal**. This eval turns
the suite's false-positive / false-negative behaviour into a **number** on a
labeled set.

```bash
python eval/self_fpfn/run_eval.py        # prints JSON tally
python -m pytest tests/test_self_fpfn.py  # regression-guards the result
```

## What it does
`cases.jsonl` is a labeled set (`defective` should be flagged, `clean` should
pass). `run_eval.py` feeds each case through the **real** probe and tallies
TP/FN/FP/TN, in two pre-registered buckets:

- **core** — in-scope, statistically-grounded cases. FP/FN here is the
  reliability number.
- **known_limitation_trap** — cases that hit a *disclosed* limitation
  (near-duplicate leakage, n-blind baseline margin, exact-match scope). These
  are **expected** to mis-decide; they quantify the limitation rather than hide
  it.

See [`RESULTS.md`](RESULTS.md) for the sealed result.

## Honest scope
- Cases are **hand-built** and the author knew the probe logic → this is
  **calibration**, not field FP/FN.
- **Deterministic probes only.** LLM-judge probes (consistency / bias / swap)
  are out of scope (they need an LLM).
- Small n → even 0 observed errors leaves a wide Wilson upper bound. This is a
  smoke test for *gross* miscalibration, not a tight rate estimate.
- The run was pre-registered (kill-condition + data hash) and sealed in a local
  hash-chained ledger before execution; ledgers are local provenance, not in
  this repo.
