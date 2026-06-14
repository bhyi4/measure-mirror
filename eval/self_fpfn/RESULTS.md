# measure-mirror self FP/FN — results (mm_self_fpfn_v1)

Answers external critique point ⑤ ("the tool itself isn't measured"): turns the
suite's FP/FN from *anecdotal* (db/curated case libraries) into a *measured* number.

## Provenance (sealed before running)
- Pre-registration seal: `6a029bdca093bbac` (ledger `/data/seara/mirror_ledgers/mm_self_eval.jsonl`)
- `cases.jsonl` sha256: `828bdffd92bba1fa2836d5a55347abf96554c2a299bd06f515c562f6cccb3b46`
- `run_eval.py` sha256: `c01589fda374dda79b6f3a7ba4b8fe5de42f3209236ed64fbd2aa3fd502a7465`
- Action seal: `877dd9e126c7b152` (am ledger `seara.jsonl`)
- Verify: L1 chain `seals valid`. L2 witness `WARN` (no independent peer witness — self-run).

## Core (33 in-scope deterministic cases)
| | value |
|---|---|
| TP / FN | 19 / **0** |
| TN / FP | 14 / **0** |
| core_fn_rate | 0.0  (Wilson 95% CI [0, 0.168]) |
| core_fp_rate | 0.0  (Wilson 95% CI [0, 0.215]) |
| kill (core_fn_rate>0.10) | **NOT triggered** |

⑧ power probe flags this eval itself: `WARN n=19 insufficient (need ≥782)`.
→ 0 errors rules out **gross** miscalibration; small n means the true rate could
still be ~17–22% (rule of three). This is a **smoke test**, not a tight estimate.

## Known-limitation traps (4, pre-registered, EXCLUDED from core rate)
Each fired exactly as designed — the disclosed limitations are now measured:
| id | probe | limitation | outcome | critique |
|---|---|---|---|---|
| lk03 | leakage | near-dup paraphrase | **FN** (tool OK) | pt4 |
| lk04 | leakage | case-only duplicate | **FN** (tool OK) | pt4 |
| bf04 | baseline_fairness | n-blind fixed margin | **FN** (tool OK) | pt3 |
| sc_trap01 | scope | exact-match case-sensitivity | **FP** (tool FAIL) | scope-analog |

## Scope / honesty
- Calibration on **hand-built** cases; constructor knew the probe logic → **not field FP/FN**.
- **Deterministic probes only.** LLM-judge probes (consistency/bias/swap) not covered (need an LLM).
- Self-run, no independent witness (L2 WARN). Reproducible: probes are pure functions, inputs hash-sealed.

## So what
- Core deterministic suite: no implementation bug surfaced on in-scope cases (bounded by small n).
- Critique pts ③④ are **confirmed and quantified**, not denied — strengthens honesty, not the tool.
- Precision pass: see [v2/RESULTS_v2.md](v2/RESULTS_v2.md) (oracle-labeled, 1119 cases).

## Update — ③④ patched (mm_fix_pt34_v1, seal `af14a7ce5fac14ba`)
The traps above drove a fix; the **same eval is the regression proof** (re-run,
sealed, core stayed 0/0, no pre-existing test regression):

| trap | before | after | how |
|---|---|---|---|
| lk04 (case-only near-dup) | FN | **TP — fixed** | leakage_check normalization (case/whitespace/punct) |
| bf04 (n-blind baseline) | FN | **TP — fixed** | baseline_fairness optional `n` → Wilson-CI distinguishability |
| lk03 (semantic paraphrase) | FN | FN — **still open** | needs embedding matching; token Jaccard 0.375 < 0.7 (a low threshold to force-catch was rejected — trades misses for false alarms) |
| sc_trap01 (scope exact-match) | FP | FP — **out of scope** | scope is a separate limitation, not part of the ③④ patch |

Honest partial fix: lexical near-dups closed, semantic paraphrase explicitly
left to a future embedding-based pass rather than papered over.
