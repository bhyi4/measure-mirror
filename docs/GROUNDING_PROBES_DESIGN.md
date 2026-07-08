# Grounding Probes — design (design group ㉑㉒㉓)

Three probes wiring the mutual-grounding arc's sealed defense laws into
measure-mirror. Sourced from a micro-substrate learning-loop experiment;
**analogy only, structure not numbers** (scope: micro-substrate · 40 gens ·
single attack family · N≤8 · median verdict). Each probe carries its grounding
seal and stays in the existing `design` group (no new group — simplicity_first
3-tier structure preserved).

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

## Wiring

- `verify(ledger, data)` runs each probe when its key is present (same pattern as gaming/scope/leakage), gated on the `design` group.
- GROUPS["design"] += the three; `_SYMBOL_GROUP` ㉑㉒㉓ → design.
- `anchor_basis` / `threshold_source` also accepted as optional `preregister()` fields (declared at seal time) — audit reads them back. **This field addition is a SPEC amendment** (§7.1 preregister), not a silent change.

## Calibration gate (before "mm flagged")

Each probe gets a labeled case set (valid / trap) in `eval/self_fpfn/`, run through the probe, FP/FN measured and sealed (mm_preregister). Only then may reports say "mm flagged"; until then, "applying the discipline, I'd flag …".
