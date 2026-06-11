# 🪞 Measurement Mirror

<p align="center">
  <img src="docs/measure_mirror_og.png" alt="Measurement Mirror" width="500">
</p>

[![CI](https://github.com/bhyi4/measure-mirror/actions/workflows/ci.yml/badge.svg)](https://github.com/bhyi4/measure-mirror/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![deps: zero](https://img.shields.io/badge/deps-zero-brightgreen.svg)](pyproject.toml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)

**Catch AI evaluation illusions — false positives and false negatives — automatically.**  
Zero training · Deterministic · Zero dependencies (Python 3.10+ stdlib only).

> Built while honestly killing our own project.  
> The makers ran it on themselves first. → [🦋 Origin Story](docs/CHRONICLE.md)

---

## The Problem

AI/ML papers routinely overclaim. The most common failure modes:

| Illusion | How it happens |
|---|---|
| Small-sample mirage | n=9, acc=55.6% reported as breakthrough |
| Post-hoc metric swap | Register accuracy, report the F1 that happened to look better |
| Crippled baseline | Compare against a deliberately weak competitor |
| Data leakage | Train/test overlap inflating every number |
| Scope overreach | "Works on task A" claimed as "general reasoning" |

Measurement Mirror catches these **structurally**, not by opinion.

---

## Install

```bash
pip install -e .                   # core (zero deps)
pip install -e ".[mcp]"            # + MCP server for AI agents
pip install -e ".[test]"           # + pytest plugin
pip install -e ".[mcp,test]"       # everything
```

CLI entry point: `mm`  
MCP entry point: `mm-mcp`

---

## Quick Start

### CLI

```bash
# Step 1 — BEFORE running your experiment: seal the criteria
mm register my_model --metric acc --min-n 200 --baseline 0.5 --pass 0.60

# Step 2 — AFTER evaluation: one-command audit
mm my_model                            # auto-loads my_model.json
mm audit my_model --acc 0.72 --n 500
mm audit --file results.json
```

`results.json` format: `{"claim_id": "my_model", "metric": "acc", "acc": 0.72, "n": 500}`

### Python API

```python
from measure_mirror import mm

LEDGER = "mm_ledger.jsonl"

# ① Before experiment — seal criteria (tamper-evident hash)
mm.preregister(LEDGER, "my_model",
               metric="acc", min_n=200, baseline=0.5, pass_threshold=0.60)

# ② After evaluation — full 7-probe audit at once
findings = mm.full_audit(
    LEDGER, "my_model",
    reported_metric="acc", reported_acc=0.72, n=500,
    baseline=0.5,
    competing_name="strong_baseline", competing_acc=0.68,   # ② fairness
    reward_terms=["cross_entropy"],                          # ③ gaming check
    train_items=train_set, test_items=test_set,              # ④ leakage
    seed_results=[0.70, 0.72, 0.74],                         # ⑤ multi-seed
    claimed_scope=["reasoning"], tested_scope=["task_a"],    # ⑥ scope
)
mm.report("my_model", findings)

# Individual probes
mm.report("fairness", [mm.baseline_fairness("vs GRU", 0.72, 0.68)])
mm.report("leakage",  [mm.leakage_check(train_items, test_items)])
mm.report("seeds",    [mm.multiseed_check([0.70, 0.72, 0.74], baseline=0.5)])
```

### Regression / Continuous Metrics

For MSE, Pearson r, RMSE, and other non-binary metrics:

```python
findings = mm.continuous_audit(
    LEDGER, "my_regressor",
    reported_metric="mse", reported_value=0.10,
    baseline_value=0.15, n=500,
    higher_better=False,   # lower MSE is better
    std=0.02,              # optional: enables effect-size check
)
mm.report("regression", findings)
```

### pytest Integration (CI Gate)

```python
# conftest.py
pytest_plugins = ["measure_mirror.pytest_plugin"]

# test_eval.py
from measure_mirror import mm
from measure_mirror.pytest_plugin import assert_clean

def test_my_model_is_real():
    findings = mm.audit("ledger.jsonl", "my_model",
                        reported_metric="acc", reported_acc=0.78, n=1000)
    assert_clean(findings)   # FAIL findings → test fails → CI goes red
```

---

## All 13 Probes + 2 Utilities

| Probe | Check # | Catches |
|---|---|---|
| `preregister` / `audit` | ① | Post-hoc metric swap · sample underrun · ledger tampering |
| `verify_chain` | ① | Deleted/inserted entries · ledger tampering |
| `baseline_fairness` | ② | Crippled / tied / reversed baseline |
| `gaming_check` | ③ | Metric directly in reward/loss (self-fulfilling) |
| `audit` — Wilson CI | ④a | Results indistinguishable from chance (small sample) |
| `audit` — direction | ④a | Performance worse than baseline (anti-signal) |
| `leakage_check` | ④a | Train∩test data contamination |
| `multiseed_check` | ⑤ | Unstable signal / lucky seed |
| `scope_check` | ⑥ | Claimed scope wider than tested scope |
| `too_good_check` | ⑦ | Suspiciously large Δ over baseline |
| `power_check` | ⑧ | n too small to detect minimum effect (false-negative guard) |
| `multiple_comparisons_check` | ⑨ | k>1 experiments in ledger — Bonferroni correction alarm |
| `grim_check` | ⑩ | Reported acc × n is arithmetically impossible (fabricated value) |

| Utility | Purpose |
|---|---|
| `calibrate` | Self-test: 5 synthetic known-good/bad cases; confirms tool health |
| `witness` | Execute a command, capture output, seal tamper-evident run record |

### Chain hash ledger (① extended)

Every `preregister()` call now embeds the previous entry's seal into the new one
before computing the SHA-256. This makes the ledger tamper-evident end-to-end:

```python
# verify the entire ledger chain at any time
findings = mm.verify_chain("mm_ledger.jsonl")
mm.report("ledger integrity", findings)
```

Catches: entry deletion, entry insertion, content modification.  
**Documented limitation**: complete file deletion + fresh re-registration is not caught —
commit the ledger file to git for that guarantee.

### Power check ⑧

```python
# warn when n is too small to detect a real effect
f = mm.power_check(n=50, baseline=0.5, min_detectable_effect=0.05)
# ⚠️  n=50 insufficient to detect Δ=+0.05 at 80% power (need n≥388)

# or activate via full_audit
findings = mm.full_audit(LEDGER, "my_model", ..., min_detectable_effect=0.05)
```

### Multiple comparisons ⑨

```python
# warn when k>1 experiments share a ledger (Bonferroni)
f = mm.multiple_comparisons_check("mm_ledger.jsonl")
# ⚠️  k=3 experiments → Bonferroni α=0.0167 (not 0.05)

# or activate via full_audit
findings = mm.full_audit(LEDGER, "my_model", ..., check_multiplicity=True)
```

### Calibrate + Witness run

```bash
# Verify the mirror itself is working correctly
mm calibrate
# ✅ [⚙ calibrate] 5/5 synthetic cases correct — mirror is calibrated.

# Witness-execute a command: calibrate first, then run and seal the record
mm run my_model -- python evaluate.py --model my_model
# ✅ [⚙ calibrate] 5/5 synthetic cases correct — mirror is calibrated.
#
# 🎬 Witnessed: my_model
#    Command:     python evaluate.py --model my_model
#    Started:     2026-06-11T12:00:00Z
#    Ended:       2026-06-11T12:00:03Z
#    Exit code:   0  (ok)
#    Output hash: a3b9f2c1e8d74f6a
#    Prev seal:   6c802655ab095e8b
#    Seal:        9d1e83a4b72f0c5e
```

```python
# Python API
findings = mm.calibrate()
mm.report("Mirror calibration", findings)

entry = mm.witness("mm_ledger.jsonl", "my_model",
                   ["python", "evaluate.py", "--model", "my_model"])
# entry["output_hash"] changes if the script output ever changes
```

### GRIM ⑩

```python
# catch arithmetically impossible accuracy values
f = mm.grim_check(reported_acc=0.33, n=10)
# 🔴  acc=0.33 is arithmetically impossible for n=10.
#     No integer k satisfies round(k/10, 2) = 0.33.
#     (candidates: k=3 → 0.3, k=4 → 0.4). Fabricated value or mis-reported n.

# GRIM runs automatically inside audit() — FAIL is appended to findings
findings = mm.audit(LEDGER, "my_model", reported_metric="acc", reported_acc=0.33, n=10)
```

---

## MCP Server — AI Agent Integration

Any MCP-compatible AI (Claude Code, Cursor, Windsurf, …) can call Measurement Mirror directly mid-conversation.

### Setup

```bash
pip install "measure-mirror[mcp]"
```

**Claude Code** — add to `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "measure-mirror": {
      "command": "python",
      "args": ["-m", "measure_mirror.mcp_server"],
      "cwd": "/path/to/measure-mirror"
    }
  }
}
```

**Other MCP clients** — run `mm-mcp` as the stdio server command.

All 13 probes + 2 utilities are exposed as MCP tools:  
`mm_register` · `mm_verify_chain` · `mm_audit` · `mm_continuous_audit` · `mm_full_audit` ·  
`mm_baseline_fairness` · `mm_gaming_check` · `mm_multiseed_check` · `mm_scope_check` ·  
`mm_too_good_check` · `mm_power_check` · `mm_multiple_comparisons_check` · `mm_grim_check` ·  
`mm_calibrate` · `mm_witness`

---

## Real Catches — Dog-Fooding

We ran Measurement Mirror on our own AI research before publishing. It caught:

```
🪞 Audit: ZERO "55.6% Best" claim
   🔴 FAIL
   🔴 [④a small-sample CI] n=9, acc=0.556 → 95%CI [0.267, 0.811] ⊃ baseline(0.5)
       Statistically indistinguishable from chance.
   🔴 [① pre-registration(min_n)] reported n=9 < registered min_n=200. Undersized.
   🔴 [① pre-registration(metric swap)] reported 'best_of_9' ≠ registered 'acc_full_balanced'
       Post-hoc metric swap detected. (seal=6c802655ab095e8b)

🪞 Audit: Field candidate 5 (control sim)
   🔴 FAIL
   🔴 [② fair baseline] Field 0.996 ≈ GRU-ODE 0.998 (Δ+0.002 < 0.01). Tied — no genuine advantage.
```

Run the demos yourself:

```bash
python examples/quickstart.py    # happy path: honest researcher
python examples/demo_zero.py     # ZERO 55.6% mirage (our own project killed)
python examples/demo_field.py    # Field candidate false positives
```

---

## Project Structure

```
measure-mirror/
├── measure_mirror/
│   ├── mm.py              # 10 probes + CLI + DB lookup
│   ├── mcp_server.py      # MCP server (pip install .[mcp])
│   └── pytest_plugin.py   # assert_clean() for CI gates
├── examples/
│   ├── quickstart.py      # happy path demo
│   ├── demo_zero.py       # ZERO false-positive (dog-food)
│   ├── demo_field.py      # Field false-positive (dog-food)
│   └── mcp_example.py     # MCP tool usage reference
├── db/                    # shared integrity database (git-based, no server)
│   ├── baselines.json         task-level fair baselines
│   ├── gaming_patterns.json   known gaming signatures
│   ├── reproductions.jsonl    failed replications
│   ├── contamination.jsonl    data leakage fingerprints
│   ├── false_negative_guards.jsonl
│   └── self_catches.jsonl     our own false positives
└── tests/test_mm.py       # 28 tests, CI-enforced
```

---

## Shared Integrity Database (`db/`)

Git-based, no server required. Contribute via PR; pull via git.  
Model: CVE / antivirus signature — each catch makes future users safer.

Auto-lookup: pass `task="musr"` to `audit()` and the registered baseline is fetched automatically, no extra code needed.

---

## Design Principles

- **Zero dependencies** — pure Python stdlib. Nothing to install, nothing to break.
- **Bidirectional** — catches false *positives* **and** false *negatives*. Premature negative closures are also illusions.
- **Tamper-evident pre-registration** — SHA-256 seal on first write. Re-registration is silently ignored. Ledger tampering is detected on every audit.
- **Independent probes** — each check is a standalone function. Add new ones without touching existing code.
- **Adversarial by default** — "too good to be true" is flagged before you believe it.

---

## Contributing

New probes, false-positive/negative cases, and baseline contributions are welcome.

1. Fork → branch → PR
2. **`db/` contributions**: add a JSONL line with `source`, `description`, and `evidence`
3. **New probes**: add the function to `mm.py` + tests in `tests/test_mm.py`
4. CI must stay green: `pytest tests/`

---

## License

[Apache 2.0](LICENSE)

---

**[한국어 README →](README_KO.md)**
