# Grounding Probes — design (design group ㉑㉒㉓㉔㉕)

Probes wiring the mutual-grounding arc's sealed defense laws into
measure-mirror. Sourced from a micro-substrate learning-loop experiment;
**analogy only, structure not numbers** (scope: micro-substrate · 40 gens ·
single attack family · N≤8 · median verdict). Each probe carries its grounding
seal and stays in the existing `design` group (no new group — simplicity_first
3-tier structure preserved).

Rollout: ㉑㉒㉓ = SPEC amendment A1. ㉔㉕ (+ `known_confounds` INFO) = A2 — the
other two `anchor-reproduction-failure` subtypes, completing the anchor-discipline
trio with ㉑.

> Discipline: a probe earns "mm flagged" language ONLY after its own FP/FN
> calibration (`eval/self_fpfn/` extension). Until then these are advisory
> Findings, not deterministic verdicts. SPEC field additions land as an
> amendment (no silent edit).

## ㉑ anchor_basis_check — PC anchor must be measured dynamics, not a static guarantee

- **Input** (`data["anchor_basis"]` or prereg field): `"dynamics-measured"` | `"structural-argument"`.
- **Finding**: `structural-argument` → WARN. A "structurally guaranteed" positive-control anchor can be refuted by the substrate's own dynamics (M11b: vote wiring worked 100%, yet resource-depletion self-limited the attack → anchor failed). Static structural argument ≠ anchor; require a dynamics smoke test.
- **Grounds**: M11b `ef5fdb20`. Catalog: `anchor-reproduction-failure` (structural-guarantee subtype, **3rd real case**).

## ㉒ threshold_provenance_check — threshold externally fixed, not observed-distribution

- **Input** (`data["threshold_source"]` or prereg field): `"external-fixed"` | `"observed-distribution"`.
- **Finding**: `observed-distribution` → WARN. A threshold re-derived from the observed submission distribution is self-calibrating; an attacker floods low-quality submissions to drag it down (worse than fixed). Even "uncontaminable source" variants failed.
- **Grounds**: M9b `c79e541a` · M10b `eb64d325`.

## ㉓ content_delta_check — judgment needs a content check, not agreement alone

- **Input** (`data["judgment_basis"]`): list/str of judgment bases; match/agreement terms vs content-delta terms (incompressibility / change-magnitude / cxpl).
- **Finding**: match-only (no content-delta) → WARN. An agreement/match-only gate is rubber-stampable by near-identity (contentless) claims; belief/depth metrics are blind — only a content check (incompressibility/length) detects it.
- **Grounds**: M5 `1990c34c`.

## ㉔ anchor_line_source_check — anchor LINE aligned to this cell, not copied (A2)

- **Input** (`data["anchor_line_source"]` or prereg field): `"separator-aligned"` | `"copied-from-other-cell"`.
- **Finding**: `copied-from-other-cell` → WARN. A PC anchor line fit to a strong-pathology cell misjudges a mild cell — a fresh-seed median inside the collapse zone reads as anchor failure and blocks the whole grid. Align the line to THIS cell's sealed separatrix.
- **Grounds**: M7b `50537aa6` (anchor-reproduction-failure, anchor-line-copy subtype).

## ㉕ anchor_cell_check — anchor CELL in a deep regime, not on the threshold (A2)

- **Input** (`data["anchor_cell"]` or prereg field): `"deep-regime"` | `"threshold-cell"`.
- **Finding**: `threshold-cell` → WARN. Even with a separatrix-aligned line, a PC cell placed at the grounding threshold itself straddles the boundary seed-to-seed and cannot reproduce stably. Move the anchor to a deep-regime cell.
- **Grounds**: M8 `4a839158` (anchor-reproduction-failure, threshold-cell subtype).

## known_confounds — pre-declared confound (A2, INFO not a probe)

- **Input** (`preregister(known_confounds=[...])`): list of strings.
- **Finding**: audit surfaces an INFO listing the declared confounds. Not a verdict — a pre-declared confound legitimizes later attribution cycles (growth arc G3L-b: declaring "pure-batch confounded with self-direction" up front justified the c/d attribution cycles); an undeclared confound found post-hoc does not.

## Wiring

- `verify(ledger, data)` runs each probe when its key is present (same pattern as gaming/scope/leakage), gated on the `design` group.
- GROUPS["design"] += all five; `_SYMBOL_GROUP` ㉑㉒㉓㉔㉕ (+㉖ for the known-confounds INFO) → design.
- `anchor_basis` / `threshold_source` (A1) and `anchor_cell` / `anchor_line_source` / `known_confounds` (A2) accepted as optional `preregister()` fields (declared at seal time) — audit reads them back. **These field additions are SPEC amendments** (§7.1 preregister), not silent changes.

## Calibration gate (before "mm flagged")

Each probe gets a labeled case set (valid / trap) in `eval/self_fpfn/`, run through the probe, FP/FN measured and sealed (mm_preregister). Only then may reports say "mm flagged"; until then, "applying the discipline, I'd flag …".
