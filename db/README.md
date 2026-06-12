# `db/` — local memory, split by who produced it

This directory holds two **different kinds of record**, deliberately kept in
separate subdirectories so they are never confused:

```
db/
├── measured/   ← what MEASURE-MIRROR produces (quantitative, verdict by code)
│   ├── baselines.json          read by lookup_baseline(task)
│   └── reproductions.jsonl     written by record_reproduction(); verdict
│                               (FAIL/PASS) auto-judged from the reproduction's
│                               own Wilson CI vs the task baseline
└── curated/    ← what WE wrote by hand (qualitative, human judgment)
    ├── self_catches.jsonl           false positives we flagged on ourselves
    ├── false_negative_guards.jsonl  false negatives we re-checked
    ├── gaming_patterns.json         gaming / mirage signatures we've seen
    ├── contamination.jsonl          data leakage we found
    └── research_closures.jsonl      qualitative negative conclusions (OEE/場…)
```

## Why the split

The honest distinction (verified — see below):

- **`measured/`** records carry a quantitative reproduction (`acc`, `n`) and
  their verdict is computed by measure-mirror itself. Re-running the tool on the
  same numbers reproduces the same verdict **exactly**. These are the tool's own
  output, and they grow only via `record_reproduction()`.

- **`curated/`** records are our human-curated catch log and research closures —
  **representative cases, not an exhaustive log.** Each record stands for a
  pattern (one `gaming_patterns` entry covers many sightings; one
  `research_closures` entry compresses a whole multi-angle arc). The full record
  of what we caught lives in our memory and agent_chat ledgers; `curated/` is the
  reusable index into it. They are **not** measure-mirror's automatic output, and
  most carry no `acc`/`n` the tool could re-judge. Calling `db/` as a whole
  "measure-mirror history" would over-claim — only `measured/` is that.

## Verification

Every `measured/reproductions.jsonl` record with quantitative data was
cross-checked: feeding its `(acc, n)` back through measure-mirror's own
Wilson-CI logic reproduces the recorded verdict with **0 mismatches**. The 13
qualitative closures that used to sit in `reproductions.jsonl` (verdict `FAIL`
but no `acc`/`n`) were moved to `curated/research_closures.jsonl`, where they
belong — they are our conclusions, not the tool's measurements.

## Code wiring

| Function | Reads / writes |
|---|---|
| `lookup_baseline(task)` | `measured/baselines.json` |
| `lookup_reproduction(task)` | `measured/reproductions.jsonl` (read) |
| `record_reproduction(...)` | `measured/reproductions.jsonl` (append) |
| `catch_history(kind=...)` | `curated/*` (read-only) |

`audit()` findings themselves are **not** persisted here — an audit is a
read-only check that returns findings to the caller. Only an explicit
`record_reproduction()` writes to `measured/`.
