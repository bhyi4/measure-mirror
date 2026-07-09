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

## Update — grounding probes ㉑㉒㉓ calibrated (mm_grounding_probes_selfcal_v1)

The three grounding probes (`anchor_basis_check`, `threshold_provenance_check`,
`content_delta_check` — mutual-grounding arc sealed defense laws, see
`docs/GROUNDING_PROBES_DESIGN.md`) got their own labeled set, extending this
eval. This is the qualification gate the design doc requires before reports may
say "mm flagged" for these probes.

### Provenance (sealed before running)
- Pre-registration seal: `033ff84b966ca561` (ledger `mm_self_eval.jsonl`);
  kill = core FN rate **or** core FP rate > 0.10.
- `cases.jsonl` sha256: `1f3595fa40515b7222303aa8bb38909f2b7266a8cf6729aea05be63517dbbd7b`
- `run_eval.py` sha256: `3edcaa6a9716f152fd20c0acf64a2680195091645f765124743aabcc0100b579`
- Result seal: `a3b1af02f833d668` (am ledger `seara.jsonl`, target=claim).

### Core (27 grounding cases; ground truth from the sealed laws, not probe code)
| | value |
|---|---|
| TP / FN | 15 / **0** |
| TN / FP | 12 / **0** |
| kill (either rate > 0.10) | **NOT triggered** |
| whole-suite core after extension | 60 cases, still 0 FN / 0 FP (no regression) |

### Known-limitation traps (3, pre-registered, EXCLUDED from core rate)
The probes are vocab classifiers and **fail closed** (unrecognized → WARN).
That direction is asymmetric by design: unknown-vocab *defectives* still get
flagged (ab09/th09/cd09 are core TPs), but unknown-vocab *clean paraphrases*
false-alarm — the disclosed limitation, analog of `sc_trap01`:

| id | probe | clean paraphrase outside vocab | outcome |
|---|---|---|---|
| ab_trap01 | anchor_basis | "validated-by-live-run" | **FP** (as designed) |
| th_trap01 | threshold_provenance | "frozen-at-design-time" | **FP** (as designed) |
| cd_trap01 | content_delta | ["match","entropy-of-diff"] | **FP** (as designed) |

### Scope / honesty
- Same caveats as v1: hand-built calibration by an author who knew the probe
  logic → **not field FP/FN**; n=27 with 0 errors still leaves a rule-of-three
  ~11% upper bound → smoke test for gross miscalibration.
- Source-experiment numbers (ε/T*/N) were **not ported** into the probes or the
  cases — structure only (micro-substrate analogy scope).

## Update — anchor-discipline probes ㉔㉕ calibrated (mm_a2_anchor_probes_selfcal_v1)

SPEC amendment A2 adds the other two `anchor-reproduction-failure` subtypes
(`anchor_line_source_check` ㉔ = M7b anchor-line-copy; `anchor_cell_check` ㉕ =
M8 threshold-cell), completing the anchor-discipline trio with ㉑. Same
qualification gate.

### Provenance (sealed before running)
- Pre-registration seal: `c4684d9f485cd0f5`; kill = core FN **or** FP rate > 0.10.
- `cases.jsonl` sha256: `24ce855a58e87d3012cc0dd7f1620c1b43efd87b167d0f59cbbd809c5469bf0f`
- Result seal: `9254145ee260df09` (am ledger `seara.jsonl`, target=claim).

### Core (14 anchor-discipline cases; ground truth from the catalog subtypes)
| | value |
|---|---|
| TP / FN | 8 / **0** |
| TN / FP | 6 / **0** |
| kill (either rate > 0.10) | **NOT triggered** |
| whole-suite core after extension | 74 cases, still 0 FN / 0 FP (no regression) |

### Known-limitation traps (2, pre-registered, EXCLUDED from core rate)
Same fail-closed vocab limitation as the A1 grounding probes:

| id | probe | clean paraphrase outside vocab | outcome |
|---|---|---|---|
| al_trap01 | anchor_line_source | "fit-to-this-cell" | **FP** (as designed) |
| ac_trap01 | anchor_cell | "far-from-boundary" | **FP** (as designed) |

### Scope / honesty
- Same caveats: hand-built calibration → **not field FP/FN**; n=14 with 0
  errors leaves a rule-of-three ~19% upper bound → smoke test only.
- Source-experiment numbers **not ported** — structure only.
