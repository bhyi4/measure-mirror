# Changelog

All notable changes to Measurement Mirror are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.6.0] — 2026-06-11

### Added
- **`anchor(ledger_path)`** — tamper-evident ledger snapshot utility. Computes
  the SHA-256 of the full ledger file (`anchor_hash`) plus the last entry's
  seal (`head_seal`), entry count, and `chain_ok` (from `verify_chain()`).
  Printed to stdout as compact JSON so users can pipe it to any external
  storage they trust (Dropbox, Gist, S3, etc.). The `anchor_hash` detects
  **complete ledger file replacement** — the one attack chain hashes cannot
  catch alone. Available as `mm anchor [--pretty]` CLI command and
  `mm_anchor` MCP tool.
- 5 new tests (total: 67 → 72, all passing).
- Sync gate: `"anchor"` added to `_MCP_UTILITY_TOOLS` exclusion list.

### Changed
- MCP server: 15 → 16 tools (13 probes + 3 utilities: anchor, calibrate, witness).
- Probe + utility table in README/README_KO updated to "13 Probes + 3 Utilities".

---

## [0.5.0] — 2026-06-11

### Added
- **`calibrate()`** — self-test utility. Runs 5 synthetic known-good/bad cases
  through the key probes (small-sample FAIL, honest large-sample OK, GRIM FAIL,
  GRIM OK, baseline inversion FAIL) and verifies expected outcomes. Returns
  `[OK]` when the mirror is healthy; `[FAIL]` with details when any case breaks.
  Available as `mm calibrate` CLI command and `mm_calibrate` MCP tool.
- **`witness(ledger_path, claim_id, command, *, timeout)`** — witness-run utility.
  Executes a command via subprocess, captures stdout/stderr/returncode, hashes
  the output (`output_hash`), and appends a chain-linked `_type="witness"` entry
  to the ledger. Proves which command ran, when, and exactly what it produced.
  Available as `mm run <claim_id> [--] <command...>` CLI command (also runs
  calibration first unless `--no-calibrate`) and `mm_witness` MCP tool.
- 8 new tests (total: 59 → 67, all passing).
- Sync gate updated: `witness` added to `_MCP_UTILITY_TOOLS` exclusion list.

### Changed
- `mm run` subcommand added to CLI alongside existing `register` / `audit`.
- Probe + utility count in README/README_KO updated: "13 Probes + 2 Utilities".
- MCP server docstring updated: 13 probes + 2 utilities (15 tools total).

---

## [0.4.0] — 2026-06-11

### Added
- **⑩ `grim_check(reported_acc, n, *, n_decimals)`** — GRIM
  (Granularity-Related Inconsistency of Means) test. Checks that
  `reported_acc × n` is consistent with a whole-number count `k`. If no
  integer `k` satisfies `round(k/n, d) == reported_acc`, the value is
  arithmetically impossible and was likely fabricated or mis-reported.
  Decimal precision is auto-inferred from the Python float representation;
  override with `n_decimals`. Example: `grim_check(0.33, 10)` → FAIL
  (no integer k satisfies round(k/10, 2) == 0.33). Runs automatically
  inside `audit()` — only appended to findings on FAIL to keep OK output clean.
- `mm_grim_check` MCP tool exposing the GRIM probe to AI agents.
- 9 new tests for GRIM (total: 46 → 55, all passing).

### Changed
- Probe count: 12 → 13 (README/README_KO updated).
- `mm.py` docstring updated: "9 probes" → "10 probes".

---

## [0.3.0] — 2026-06-11

### Added
- **① Chain hash ledger** — `preregister()` now embeds `prev_seal` in every
  entry before computing the SHA-256 seal. The full ledger becomes a
  tamper-evident chain. `verify_chain(ledger_path)` walks all entries and
  checks both individual seals and chain links. Catches: entry deletion,
  insertion, and content modification. Backward-compatible: legacy entries
  without `prev_seal` skip the chain check gracefully.
- **⑧ `power_check(n, baseline, *, min_detectable_effect, alpha, target_power)`**
  — False-negative guard. Warns when `n` is too small to detect the minimum
  detectable effect at the specified power level (default 80%). Closes the
  gap between the "bidirectional" design principle and the actual
  implementation. Available standalone and via `full_audit(min_detectable_effect=...)`.
- **⑨ `multiple_comparisons_check(ledger_path, *, alpha)`** — Garden-of-forking-
  paths detector. Counts distinct `claim_id` values in the ledger and warns
  with the Bonferroni-corrected α when k>1. Re-registrations for the same
  `claim_id` count as k=1 (consistent with first-write-wins). Available
  standalone and via `full_audit(check_multiplicity=True)`.
- `full_audit()` gains two new optional parameters: `min_detectable_effect`
  (activates ⑧) and `check_multiplicity` (activates ⑨).
- Tests expanded from 28 → 46 (all passing).

### Changed
- Probe count: 9 → 12 (README/README_KO updated).
- Documented chain-hash limitation: complete ledger file replacement is not
  caught — git commit anchoring is the recommended complement.

---

## [0.2.0] — 2026-06-11

### Added
- **③ `gaming_check(metric, reward_terms)`** — Detects eval metric appearing
  directly in the training reward/loss (self-fulfilling artifact).
- **⑤ `multiseed_check(seed_results, *, baseline, cv_threshold)`** — Alarms on
  unstable cross-seed results or baseline falling within the seed range.
- **⑦ `too_good_check(name, claimed, baseline, *, suspicious_margin)`** —
  Flags suspiciously large improvements before they are believed.
- **`continuous_audit()`** — Audits non-binary metrics (MSE, Pearson r, RMSE…)
  using direction check + optional effect-size (z-score).
- **`full_audit()`** — Single call that runs all probes; optional probes
  activate when their args are provided.
- **MCP server** (`measure_mirror/mcp_server.py`, entry point `mm-mcp`) —
  All probes exposed as MCP tools for AI agent integration.
- **pytest plugin** (`measure_mirror/pytest_plugin.py`) — `assert_clean()`
  turns FAIL findings into CI failures.
- `pyproject.toml` v0.2.0 with `[mcp]` and `[test]` optional dependencies.
- `examples/quickstart.py` and `examples/mcp_example.py`.
- English-primary README with `README_KO.md` for Korean users.

### Fixed
- `_load_prereg()` now returns the **first** matching entry (was returning
  last). This is the correct behavior: first-write wins.
- `_verify_seal()` added to `audit()` — tamper detection was missing.
- `pass_threshold` check added to `audit()` — registered bar was not enforced.

---

## [0.1.0] — 2026-06-08 (initial public release)

### Added
- Core probe engine with zero dependencies (Python stdlib only).
- **① Pre-registration** — append-only JSONL ledger, SHA-256 seal, first-write
  wins, metric-swap detection, min_n enforcement.
- **② `baseline_fairness()`** — crippled / tied / reversed baseline detection.
- **④a `wilson_ci()`** — small-sample Wilson score confidence interval.
- **④a `leakage_check()`** — train∩test hash intersection.
- **④a direction** — anti-signal detection (worse than chance).
- **⑥ `scope_check()`** — over-generalization detection.
- **`audit()`** — binary/classification metric audit combining ①+④a.
- `report()` printer, `lookup_baseline()` DB helper.
- CLI entry point `mm` with `register` and `audit` subcommands.
- `db/baselines.json` shared baseline database (git-based, no server).
- Apache 2.0 license. Dog-fooded on ZERO and Field projects.
