# 🪞 Measurement Mirror — Probe Guide

> **Audience**: researchers, ML engineers, and reviewers who want to understand
> what each probe does, when to use it, and how to read its output.
>
> **Companion files**: [README](../README.md) (API reference) ·
> [CHANGELOG](../CHANGELOG.md) · [CHRONICLE](CHRONICLE.md) (origin story)
>
> **한국어 버전**: [GUIDE_KO.md](GUIDE_KO.md)

---

## Philosophy: the two-sided mirror

Most evaluation integrity tools only catch **false positives** — results that
look better than they are. Measurement Mirror catches both:

| Direction | Example failure | Mirror response |
|---|---|---|
| False positive | n=9, acc=55.6% reported as breakthrough | ④a Wilson CI flags it as chance |
| **False negative** | 1 negative experiment → "approach is dead" | ⑬ negative_audit requires ≥ 3 independent angles |
| **Judge illusion** | LLM judge always picks the first response | ⑮ judge_bias_check catches position preference |

A premature negative closure is as bad as a fabricated positive. Both are
illusions that waste research resources and mislead the field.

---

## The claim lifecycle

```
① preregister               ← seal criteria BEFORE seeing results
        │
        ▼
㉗ prereg_lint               ← lint the seal's QUALITY before spending compute
        │                       (leaked kill-condition · bar at/below declared chance ·
        ▼                        unstructured kill · low n · undeclared checks)
    experiment runs
        │
        ▼
audit / full_audit           ← run all probes after results are in
  ├─ ④a statistical validity
  ├─ ①  pre-registration checks
  ├─ ⑩  GRIM arithmetic check
  ├─ ⑪  falsifiability / kill-condition
  └─ ⑫  retraction cascade
        │
        ├── positive conclusion  → publish + anchor (external hash)
        │
        ├── negative conclusion  → negative_audit (⑬) gates the closure
        │                           ≥ min_angles independent angles required
        │                           │
        │                           ▼
        │                        if later invalidated: retract() → cascade_check()
        │
        └── LLM judge evaluation → judge_run() fires ⑭⑮⑯⑰ automatically
                                    seals chain-linked entry in ledger
```

---

## Three verification tiers

| Tier | How | When |
|---|---|---|
| **FULL** | `mm.verify(ledger, data)` / `mm verify --file data.json` | one-shot audit — every probe whose inputs exist in `data` runs |
| **GROUP** | `mm.verify(ledger, data, groups=["judge"])` / `--groups judge` | focus on one verification concern |
| **INDIVIDUAL** | `mm.grim_check(...)`, `mm.judge_swap_check(...)`, … | precise control, custom pipelines |

Verification groups (see `mm verify --list-groups` or `mm.GROUPS`):

| Group | Probes | Question it answers |
|---|---|---|
| `ledger` | ① ⑫ + chain | Is the pre-registration record intact and un-retracted? |
| `stats` | ④ ⑤ ⑦ ⑧ ⑨ ⑩ | Are the numbers statistically real? |
| `design` | ② ③ ⑥ ⑪ | Is the experiment designed fairly? |
| `negative` | ⑬ | Is this negative closure premature? |
| `judge` | ⑭ ⑮ ⑯ ⑰ ⑱ | Is the LLM judge reliable? |
| `ranking` | ⑲ ⑳ | Is the leaderboard real? |

`verify()` is input-driven: a probe runs only when its keys are present in the
`data` dict, so the FULL tier never errors on missing inputs — it simply runs
whatever the data supports. `group_of(finding)` maps any Finding back to its group.

---

## Probe reference

Probes are grouped by the type of integrity failure they catch.

---

### Group 1 — Pre-registration & ledger integrity

#### ① `preregister` / `audit`

**Catches**: post-hoc metric swap · sample size underrun · tampered criteria · failed pass-threshold

Pre-registration seals the evaluation plan *before* results are seen. The SHA-256
seal and chain link make it tamper-evident: changing any field after the fact is
detectable.

```python
# BEFORE the experiment
mm.preregister("ledger.jsonl", "my_model",
               metric="acc",          # the ONE metric you commit to
               min_n=200,             # minimum acceptable sample size
               baseline=0.5,          # fair comparison baseline
               pass_threshold=0.60)   # minimum bar to claim success

# AFTER the experiment
findings = mm.audit("ledger.jsonl", "my_model",
                    reported_metric="acc",   # must match registered metric
                    reported_acc=0.72,
                    n=500)
mm.report("my_model", findings)
```

**Levels from `audit()`:**
- `FAIL [① pre-registration(metric-swap)]` — you reported `f1` but registered `acc`
- `FAIL [① pre-registration(min_n)]` — `n=9 < registered min_n=200`
- `FAIL [① pre-registration(pass-threshold)]` — result below your own bar
- `FAIL [① seal-tamper]` — ledger file was modified after registration

**Common mistake**: registering with `metric="acc"` then later reporting the metric
that happened to look better (`f1`, `auc`). The seal catches this even months later.

---

#### ① `verify_chain`

**Catches**: deleted entries · inserted entries · content modification in any entry

```python
findings = mm.verify_chain("ledger.jsonl")
mm.report("ledger integrity", findings)
```

The chain works because every entry embeds `prev_seal` — the SHA-256 of the
*previous* entry — before computing its own seal. Deleting entry N breaks the
chain at entry N+1. Inserting a fake entry also breaks it because the fake
entry's `prev_seal` won't match.

**When to run**: in CI after every experiment, and before publishing results.

---

#### `anchor` (utility)

**Catches**: complete ledger file replacement — the one attack chain hashes cannot catch

Chain hashes detect modifications *within* the file. But if someone deletes the
entire file and starts fresh, the chain is technically valid (new genesis). The
`anchor_hash` (SHA-256 of the full file bytes) detects this.

```python
# Print tamper-evident snapshot; pipe to wherever you trust
a = mm.anchor("ledger.jsonl")
# → {"_type": "anchor", "anchor_hash": "sha256hex...", "chain_ok": true, ...}

# CLI: pipe to external storage before publishing
mm anchor | gh gist create -               # GitHub Gist timestamped
mm anchor >> ~/Dropbox/mm_anchors.jsonl    # local backup
mm anchor --pretty                          # human-readable
```

**Best practice**: run `mm anchor` immediately before publishing a result. The
external timestamp proves what the ledger contained at publication time.

#### ㉗ `prereg_lint` — seal quality, before compute

`falsifiability_check` (⑪) asks *whether* a kill-condition exists. `prereg_lint`
asks whether the seal is **well-formed enough for the automated checks to fire,
and whether its bar is meaningful** — the defect classes that leak silent compute:

| Level | Defect |
|---|---|
| FAIL | kill-condition prose leaked into the `metric` field (malformed call — a human sees a criterion, the parser sees none) |
| FAIL | pass bar at or below the DECLARED chance (clearing it proves nothing; needs `chance=` — `baseline` alone is not the floor) |
| WARN | quantified kill written as free text, no structured `kill_threshold` → can never auto-evaluate |
| WARN | `min_n` below the small-sample floor (20) |
| INFO | no `pre_seal_checks` declared (reachability-smoke · mass-balance-audit · neutral-control · manipulation-check · positive-control) |

```python
mm.preregister("ledger.jsonl", "my_model",
               metric="acc", min_n=240, baseline=0.5, pass_threshold=0.60,
               kill_threshold={"metric": "acc", "threshold": 0.55, "direction": "below"},
               pre_seal_checks=["reachability-smoke", "neutral-control"])

for f in mm.prereg_lint("ledger.jsonl", "my_model"):   # claim_id=None → lint ALL claims
    print(f)
```

Deliberately **not** in the `verify()` umbrella or any group: it is a
*pre-compute* check, while `verify()`/`audit()` run at report time. It fires
automatically inside the MCP `mm_register` (the response carries the lint), and
the mirror-stack compute gate BLOCKs on a ㉗ FAIL. A FAIL means **fix and re-seal
under a NEW claim_id** — first-write-wins makes the sealed one uncorrectable.

---

### Group 2 — Statistical validity

#### ④a Wilson CI (inside `audit`)

**Catches**: results statistically indistinguishable from chance (small-sample mirage)

Wilson score confidence intervals are tighter than normal approximation at small n.
If the 95% CI contains the baseline, the result is statistically worthless.

```python
# This runs automatically inside audit()
findings = mm.audit("ledger.jsonl", "my_model",
                    reported_metric="acc", reported_acc=0.72, n=15)
# ⚠️  [④a small-sample CI] n=15, acc=0.72 → 95%CI [0.467, 0.887]
#     ⊃ baseline(0.5). Indistinguishable from chance.
```

**Rule of thumb**: at n=15, even acc=0.72 is not distinguishable from 0.5.
You need n≥200 for a +10pp improvement to be significant.

---

#### ⑧ `power_check`

**Catches**: n too small to detect the minimum effect you care about (false-negative guard)

This is the mirror's primary **false-negative probe**. A negative result from
an underpowered experiment is meaningless — you might have missed a real effect.

```python
f = mm.power_check(n=50, baseline=0.5, min_detectable_effect=0.05)
# ⚠️  [⑧ power] n=50 insufficient to detect Δ=+0.05 at 80% power.
#     Need n≥388. (α=0.05, power=0.80)

# Required n for various effect sizes at 80% power:
# Δ=+0.20 → n≈50  |  Δ=+0.10 → n≈200  |  Δ=+0.05 → n≈388

# Activate via full_audit
findings = mm.full_audit("ledger.jsonl", "my_model", ...,
                          min_detectable_effect=0.05)
```

**Common mistake**: closing a negative result ("this method doesn't help") after
testing with n=30 against Δ=+0.05. The power was only ~14% — 86% chance you missed
a real effect.

---

#### ⑨ `multiple_comparisons_check`

**Catches**: garden-of-forking-paths when k>1 experiments share a ledger

If you run 5 experiments and pick the best one, your effective α is not 0.05 —
it's 1 − (1−0.05)^5 ≈ 0.23. Bonferroni correction requires α/k per test.

```python
f = mm.multiple_comparisons_check("ledger.jsonl", alpha=0.05)
# ⚠️  [⑨ multiple-comparisons] k=5 experiments in ledger.
#     Bonferroni-corrected α = 0.010 (not 0.05). Use stricter threshold.

# Activate via full_audit
findings = mm.full_audit("ledger.jsonl", "my_model", ...,
                          check_multiplicity=True)
```

**Note**: re-registrations for the same `claim_id` count as k=1 (consistent with
first-write-wins policy). Only distinct claim_ids count.

---

### Group 3 — Comparison honesty

#### ② `baseline_fairness`

**Catches**: crippled baseline · tied results · reversed comparison

A "strong improvement" over a deliberately weak baseline is not an improvement.
A "better" result that falls within the noise margin of the baseline is a tie.

```python
# Crippled baseline: your model beats a broken competitor
f = mm.baseline_fairness("random_baseline", 0.60, 0.50)   # OK — clear win
f = mm.baseline_fairness("vs_gru_ode",      0.998, 0.996)  # FAIL — tied (Δ=0.002)

# Reversed: you lost
f = mm.baseline_fairness("strong_model", 0.72, 0.86)  # FAIL — baseline wins

# Non-binary metrics (lower is better, e.g. MSE)
f = mm.baseline_fairness("vs_baseline_mse", 0.12, 0.15, higher_better=False)
```

**Levels:**
- `FAIL [② fair-baseline] X wins` — baseline outperforms you
- `FAIL [② fair-baseline] Tied` — Δ < margin (default 0.01)
- `OK` — clear win

---

#### ⑦ `too_good_check`

**Catches**: suspiciously large improvements that warrant extra scrutiny

When a result looks "too good to be true," it often is: data leakage, evaluation
set contamination, or a reward/metric alignment bug are common causes.

```python
f = mm.too_good_check("my_model", claimed=0.95, baseline=0.50)
# ⚠️  [⑦ too-good] Δ=+0.45 over baseline — suspiciously large.
#     Investigate: data leakage? reward hacking? metric alignment bug?
```

Default threshold: Δ > 0.30 triggers a WARN. This runs automatically inside
`full_audit()` — no extra args needed.

---

### Group 4 — Data & metric integrity

#### ③ `gaming_check`

**Catches**: the evaluation metric appearing directly in the training reward/loss

When you optimize directly for the evaluation metric, the result is self-fulfilling:
the model *should* score well on the metric by construction, not because it learned
the underlying task.

```python
f = mm.gaming_check(metric="accuracy", reward_terms=["cross_entropy", "accuracy"])
# 🔴 [③ gaming] 'accuracy' appears in reward_terms.
#    Result is self-fulfilling — metric directly in training objective.

f = mm.gaming_check(metric="bleu", reward_terms=["rl_reward", "fluency"])
# ✅ OK — bleu not in reward
```

---

#### ④a `leakage_check`

**Catches**: train/test set overlap (data contamination)

Even small overlaps can dramatically inflate accuracy. The check hashes items
and computes intersection — works for any hashable item type.

```python
# With string items
train = ["sentence A", "sentence B", "sentence C"]
test  = ["sentence C", "sentence D", "sentence E"]
f = mm.leakage_check(train, test)
# 🔴 [④a leakage] 1/3 test items (33.3%) appear in train set.

# Works for integers, tuples, any hashable type
f = mm.leakage_check(list(range(100)), list(range(50, 150)))  # 50% overlap → FAIL
```

---

#### ⑤ `multiseed_check`

**Catches**: unstable signal across seeds · baseline within the seed range

A result that varies from acc=0.48 to acc=0.72 across seeds is unreliable.
If the baseline falls inside the seed range, the result is indistinguishable
from chance under different initializations.

```python
f = mm.multiseed_check([0.48, 0.72, 0.65], baseline=0.5)
# 🔴 [⑤ multi-seed] Baseline 0.500 falls within seed range [0.480, 0.720].
#    Result is not robustly above chance.

f = mm.multiseed_check([0.68, 0.71, 0.72], baseline=0.5)   # OK
f = mm.multiseed_check([0.70, 0.85, 0.75], baseline=0.5,
                        cv_threshold=0.05)  # adjust CV threshold
```

**Rule**: CV (coefficient of variation) > 10% triggers WARN by default.

---

#### ⑥ `scope_check`

**Catches**: claimed scope wider than tested scope (over-generalization)

"Works on task A" ≠ "general reasoning". The claimed_scope must be a subset
of tested_scope (or exactly equal).

```python
f = mm.scope_check(claimed_scope=["reasoning", "math"],
                   tested_scope=["musr_task_a"])
# 🔴 [⑥ scope] Over-claimed: {'reasoning', 'math'} not tested.
#    Tested: {'musr_task_a'} only.

f = mm.scope_check(claimed_scope=["task_a"],
                   tested_scope=["task_a", "held_out_b"])  # OK
```

---

#### ⑩ `grim_check`

**Catches**: arithmetically impossible accuracy / mean values — likely fabricated or mis-reported n

GRIM (Granularity-Related Inconsistency of Means): if `acc = k/N` for some
integer k (where `N = n·items`), then `round(k/N, d) == acc` must hold. If no
integer k satisfies this, the value is impossible. Works for proportions,
percentages, and means of integer (e.g. Likert) data.

```python
f = mm.grim_check(reported_acc=0.33, n=10)
# 🔴 [⑩ GRIM] acc=0.33 is arithmetically impossible for n=10.
#    No integer k satisfies round(k/10, 2) = 0.33.
#    (candidates: k=3 → 0.30, k=4 → 0.40). Fabricated value or mis-reported n.

f = mm.grim_check(reported_acc=0.30, n=10)   # OK — round(3/10, 2) = 0.30

# Means of multi-item scales: granularity is n·items
f = mm.grim_check(5.90, n=40, items=3)        # N=120

# Decimal precision is auto-inferred; override with n_decimals
f = mm.grim_check(0.333, n=10, n_decimals=3)
```

**Runs automatically inside `audit()`** — FAIL is appended, OK is silent.

> **Scope — small samples only.** GRIM's power comes from *granularity*: with a
> small `N`, only a few values are reachable, so an impossible one stands out.
> As `N` grows the reachable values fill in and GRIM goes blind — for a value
> reported to `d` decimals, GRIM can flag nothing once `N ≳ 10^d` (e.g. a
> 2-decimal mean at n ≥ 100). It also catches only *arithmetic* impossibility,
> not *distributional* fabrication: a large fabricated dataset (e.g. an AI-
> generated one) typically passes GRIM and is caught instead by digit-pattern /
> distribution forensics, which are out of scope here. **Verified empirically**:
> random 2-decimal means are GRIM-impossible ~79% of the time at n=20 but ~0% at
> n≥100. Use GRIM as a small-sample arithmetic gate, not a general fraud detector.

---

### Group 5 — Claim lifecycle

These three probes form the core of the "claim lifecycle integrity" system.
Together they turn Measurement Mirror from a statistics checklist into an
audit trail that tracks what was claimed, what would kill a claim, and whether
foundations have been pulled out from under standing conclusions.

---

#### ⑪ `falsifiability_check`

**Catches**: unfalsifiable claims (no kill-condition) · claims that already falsified themselves

A claim without a kill-condition cannot, in principle, be proven wrong — it is
unfalsifiable. A claim with a registered kill_threshold that the result triggers
is *self-falsified* at the moment of publication.

```python
# Register the kill-condition BEFORE the experiment
mm.preregister("ledger.jsonl", "my_model",
               metric="acc", min_n=200, baseline=0.5, pass_threshold=0.60,
               # human-readable description (optional but good practice)
               kill_condition="accuracy drops below 0.55 on held-out test",
               # structured form: auto-evaluated at audit time (recommended)
               kill_threshold={"metric": "acc",
                                "threshold": 0.55,
                                "direction": "below"})

# At audit — ⑪ runs automatically
findings = mm.audit("ledger.jsonl", "my_model",
                    reported_metric="acc", reported_acc=0.50, n=500)
# 🔴 [⑪ falsifiability] Kill condition triggered: acc=0.5 < 0.55.
#    Claim 'my_model' is falsified by its own pre-registered criterion.

# Standalone check (before full audit, or for a specific query)
f = mm.falsifiability_check("ledger.jsonl", "my_model", reported_acc=0.50)
```

**Levels:**
- `FAIL` — kill_threshold is registered AND reported_acc triggers it
- `WARN` — no kill-condition at all ("Unfalsifiable") OR threshold set but no result provided
- `OK` — threshold not triggered, or text-only condition registered

**Direction parameter:**
- `"below"`: FAIL when `reported_acc < threshold` (accuracy-type, higher-is-better)
- `"above"`: FAIL when `reported_acc > threshold` (error-type, e.g. MSE, lower-is-better)

**CLI:**
```bash
mm register my_model --metric acc --min-n 200 --baseline 0.5 --pass 0.60 \
  --kill "accuracy drops below 0.55" \
  --kill-threshold 0.55 --kill-direction below
```

---

#### ⑫ `cascade_check` + `retract`

**Catches**: claims built on retracted foundations (stale transitive dependencies)

Research is cumulative. Claim B often builds on Claim A. When Claim A is retracted
(dataset contamination discovered, methodology flaw found), any claim that depends
on it should be automatically flagged as STALE — even if it was published years later.

```python
# Register dependency relationships BEFORE experiments
mm.preregister("ledger.jsonl", "dataset_v1",
               metric="quality_score", min_n=100, baseline=0.0, pass_threshold=0.8)
mm.preregister("ledger.jsonl", "model_trained_on_v1",
               metric="acc", min_n=200, baseline=0.5, pass_threshold=0.60,
               depends_on=["dataset_v1"])          # ← seal the dependency
mm.preregister("ledger.jsonl", "paper_results",
               metric="acc", min_n=500, baseline=0.5, pass_threshold=0.70,
               depends_on=["model_trained_on_v1"]) # ← transitive chain

# Later: dataset contamination discovered
mm.retract("ledger.jsonl", "dataset_v1",
           reason="30% of test set found in pre-training data")

# Cascade check — no need to know the dependency chain yourself
f = mm.cascade_check("ledger.jsonl", "paper_results")
# ⚠️  [⑫ retraction-cascade] Claim 'paper_results' is STALE:
#     depends (transitively) on retracted claim(s): 'dataset_v1'

f = mm.cascade_check("ledger.jsonl", "dataset_v1")
# 🔴 [⑫ retraction-cascade] Claim 'dataset_v1' has been retracted.
```

**cascade_check levels:**
- `FAIL` — claim itself is retracted
- `WARN` — claim is STALE (a transitive dependency is retracted)
- `OK` — no retraction risk

**Key properties:**
- Retraction entries are **chain-linked** — deleting a retraction record breaks
  `verify_chain()`. You cannot silently un-retract.
- Propagation is **publication-order-independent** — a 2020 paper that depends on a
  2019 dataset retracted in 2024 is immediately flagged STALE.
- Runs **automatically inside `audit()`** (WARN/FAIL only appended).

**CLI:**
```bash
# Register with dependencies
mm register model_v2 --metric acc --min-n 200 --baseline 0.5 --pass 0.60 \
  --depends-on dataset_v1 baseline_eval

# Retract
mm retract dataset_v1 --reason "train/test overlap discovered"
```

---

#### ⑬ `negative_audit`

**Catches**: premature negative closures (Resolved-Negative with too few angles)

The hardest type of false negative in research: declaring "X does not work" after
a single negative experiment. A single failure may be a frame flaw, not a universal
wall. Multiple independent angles must converge before a negative conclusion is
trustworthy.

```python
# Each angle is a separate independent experiment testing the same hypothesis
# from a different perspective (different dataset, method, condition)
for angle_id in ["oee_wave_ode", "oee_bilinear_coev", "oee_alife_sim",
                  "oee_gray_scott", "oee_hp_folding"]:
    mm.preregister("ledger.jsonl", angle_id,
                   metric="oee_score", min_n=50, baseline=0.5, pass_threshold=0.0)

# After all angles converge to negative results — gate the closure
f = mm.negative_audit("ledger.jsonl",
                      angles=["oee_wave_ode", "oee_bilinear_coev",
                               "oee_alife_sim", "oee_gray_scott", "oee_hp_folding"],
                      min_angles=3)
# ✅ [⑬ negative-audit] 5/5 independent pre-registered angle(s) verified —
#    negative conclusion is supported.

# Optional scope check: the negative conclusion must not overgeneralize
f = mm.negative_audit("ledger.jsonl",
                      angles=["oee_wave_ode", "oee_bilinear_coev", "oee_alife_sim"],
                      conclusion_scope=["all_substrates", "all_ALife"],
                      tested_scope=["in_silico_digital"])
# 🔴 [⑬ negative-audit] conclusion scope includes untested domain(s):
#    ['all_substrates', 'all_ALife'].
```

**Levels:**
- `FAIL` — fewer angles than `min_angles` (premature closure risk)
- `FAIL` — an angle is not pre-registered (can't be trusted as independent evidence)
- `FAIL` — `conclusion_scope ⊄ tested_scope` (over-generalized negative)
- `WARN` — enough angles, but at least one is retracted (weakened case)
- `OK` — all checks pass

**CLI:**
```bash
mm negative \
  --angles oee_wave_ode oee_bilinear_coev oee_alife_sim \
  --min-angles 3
```

**Via `full_audit()`:**
```python
findings = mm.full_audit("ledger.jsonl", "main_claim", ...,
                          angles=["exp1", "exp2", "exp3"])
# ⑬ finding is appended automatically
```

---

### Group 6 — LLM-as-a-Judge probes ⑭⑮⑯⑰

These four probes audit the **judge itself** rather than the model under evaluation.
LLM judges introduce failure modes that numeric metrics cannot see: stochastic flips,
positional bias, inter-run disagreement, and degenerate scoring distributions.

All four probes live in `mm.py` (zero dependencies) and accept raw score lists, so
they work with any judge system. The optional `judge.py` module handles calling the
LLM and wires all four probes together automatically.

**Install:**
```bash
pip install "measure-mirror[judge]"   # adds openai and anthropic packages
```

---

#### ⑭ `judge_consistency_check`

**Catches**: a stochastic judge that gives different verdicts on the same item on re-run.

If you call the same judge twice on the same items and a high fraction of verdicts
flip, the judge's output is noise. Rankings derived from noisy judge scores are
meaningless even if aggregate numbers look stable.

```python
# score_pairs: list of (score_run1, score_run2) — same item judged twice
# For pairwise:  0 = A won, 1 = B won
# For rating:    integer score

score_pairs = [(1, 1), (0, 0), (1, 1), (0, 0), (1, 0)]  # 1 flip out of 5
f = mm.judge_consistency_check(score_pairs, flip_threshold=0.20)
# ✅ [⑭ judge-consistency] Judge flip rate 20.0% ≤ 20.0% (1/5 flips). Consistent.

score_pairs_bad = [(1, 0), (0, 1), (1, 0), (0, 1), (1, 0)]  # 5 flips — all wrong
f = mm.judge_consistency_check(score_pairs_bad, flip_threshold=0.20)
# 🔴 [⑭ judge-consistency] Judge flip rate 100.0% > 20.0% (5/5 items changed
#    verdict on re-run). Judge is unreliable — scores cannot be trusted.
```

**Parameters:**
| Param | Default | Notes |
|---|---|---|
| `score_pairs` | required | `[(run1, run2), ...]` — one pair per item |
| `flip_threshold` | 0.20 | max acceptable fraction of changed verdicts |

**Levels:**
- `FAIL` — flip_rate > flip_threshold
- `WARN` — empty score_pairs (can't assess)
- `OK` — flip_rate ≤ flip_threshold

---

#### ⑮ `judge_bias_check`

**Catches**: systematic position preference — the judge picks A (or B) regardless of content.

In pairwise evaluation, the judge is shown Response A and Response B in a fixed order.
A biased judge exploits position: "first answer is better" or "second answer is better"
as a shortcut. This inflates whatever candidate happens to occupy the favored position.

```python
# pairwise_results: [0, 1, 0, ...] — 0 = A won, 1 = B won

# Balanced: no bias
results = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
f = mm.judge_bias_check(results)
# ✅ [⑮ judge-bias] Position A win rate 50.0% — no significant position bias.

# A-favoring judge
results = [0, 0, 0, 0, 0, 0, 0, 0, 0, 1]  # A wins 90%
f = mm.judge_bias_check(results, bias_threshold=0.60)
# 🔴 [⑮ judge-bias] Position A win rate 90.0% > 60.0%. Strong position bias
#    detected (9/10 items favor A).
```

**Mitigation**: run each pair in both orders (AB and BA) and average.
If the judge is unbiased, switching positions should invert the verdict frequency.

**Parameters:**
| Param | Default | Notes |
|---|---|---|
| `pairwise_results` | required | `[0, 1, ...]` — one result per comparison |
| `bias_threshold` | 0.60 | win-rate above which position bias is flagged |

**Levels:**
- `FAIL` — A or B win-rate > bias_threshold
- `WARN` — empty results
- `OK` — both win-rates within threshold

---

#### ⑯ `inter_rater_agreement`

**Catches**: two judges (or two runs of the same judge) that disagree beyond chance level.

Cohen's κ measures agreement *above* what you would expect by random chance.
A κ near 0 means the two raters are effectively independent random variables — their
scores cannot be averaged or reported as a single signal.

| κ | Interpretation |
|---|---|
| < 0.20 | Poor — essentially random |
| 0.20 – 0.40 | Fair |
| 0.40 – 0.60 | Moderate (default threshold) |
| 0.60 – 0.80 | Substantial |
| > 0.80 | Near-perfect |

```python
# ratings_matrix: [(judge1_score, judge2_score), ...] — one row per item
# Use any categorical scores: 0/1 (pairwise winner) or 1–10 (rating scale)

# Perfect agreement
matrix = [(1, 1), (0, 0), (1, 1), (0, 0), (1, 1)]
f = mm.inter_rater_agreement(matrix)
# ✅ [⑯ inter-rater] Cohen's κ=1.000 ≥ 0.40 — acceptable inter-rater agreement.

# Fair agreement (κ ≈ 0.33 < 0.40)
matrix = [(0, 0), (0, 1), (0, 0), (1, 1), (1, 0), (1, 1)]
f = mm.inter_rater_agreement(matrix, min_kappa=0.40)
# ⚠️ [⑯ inter-rater] Cohen's κ=0.333 < 0.40 — fair agreement only.
#    Results may not reproduce with a different judge model.

# Poor agreement triggers FAIL
matrix = [(0, 1), (1, 0), (0, 1), (1, 0), (0, 1)]
f = mm.inter_rater_agreement(matrix)
# 🔴 [⑯ inter-rater] Cohen's κ=-1.000 < 0.20 — poor agreement.
#    Judge scores are essentially random relative to each other.
```

**Parameters:**
| Param | Default | Notes |
|---|---|---|
| `ratings_matrix` | required | `[(r1, r2), ...]` — one row per item; must be ≥ 3 items |
| `min_kappa` | 0.40 | minimum acceptable κ |

**Levels:**
- `FAIL` — κ < 0.20 (poor) or fewer than 3 items
- `WARN` — 0.20 ≤ κ < min_kappa (fair only)
- `OK` — κ ≥ min_kappa

---

#### ⑰ `judge_score_sanity`

**Catches**: a degenerate judge that assigns the same score to almost everything.

A judge with near-zero discrimination provides no signal. Rankings based on its scores
are equivalent to random ranking — no matter how many items you evaluate, the judge is
not learning anything from the content.

```python
# scores: [8, 7, 8, 9, ...] — all scores from one judge run
# Works with both integer and float scores

# Healthy distribution
scores = [3, 7, 5, 8, 4, 6, 9, 2, 7, 5, 3, 8, 6, 4, 7]
f = mm.judge_score_sanity(scores)
# ✅ [⑰ judge-score-sanity] 8 distinct values across 15 scores (53.3% unique ratio).
#    Distribution looks healthy.

# Degenerate: all scores identical
scores = [8] * 20
f = mm.judge_score_sanity(scores)
# 🔴 [⑰ judge-score-sanity] All 20 scores identical (8).
#    Judge is not discriminating — scores are meaningless.

# Near-degenerate: one dominant value
scores = [8] * 19 + [7]  # 95% are 8
f = mm.judge_score_sanity(scores)
# ⚠️ [⑰ judge-score-sanity] 95% of scores are '8' — near-degenerate distribution.
#    Judge may not be discriminating.
```

**Parameters:**
| Param | Default | Notes |
|---|---|---|
| `scores` | required | list of all scores from one judge run |
| `min_unique_ratio` | 0.10 | minimum ratio of unique values to total scores |

**Levels:**
- `FAIL` — all scores identical (ratio = 0)
- `WARN` — top-value concentration > 90% or unique_ratio < min_unique_ratio
- `OK` — distribution looks healthy

---

#### ⑱ `judge_swap_check`

**Catches**: a judge whose verdict follows the *slot*, not the content — including
the hardest case: a deterministic, balanced, content-blind judge that passes every
other probe.

Each pair is judged twice: once as (A, B) and once with positions swapped (B, A).
A content-driven judge must invert its verdict — the same response wins from either
slot. A judge whose verdict stays with the slot is reading position, not content.

```
lock = forward[i] == swapped[i]   (same slot won both times)

lock_rate ≈ 0.0  → content-driven  (verdict follows the response)  → OK
lock_rate ≈ 0.5  → noise           (verdict tracks neither)        → WARN
lock_rate ≈ 1.0  → position-locked (verdict follows the slot)      → FAIL
```

**Why aggregate win-rate (⑮) is not enough** — a deterministic judge that never
reads the responses (e.g. decides from the prompt alone) is perfectly consistent
(⑭ OK), shows a balanced win-rate (⑮ OK), agrees with itself (⑯ κ=1.0), and
produces varied scores (⑰ OK). Only the swap exposes it:

```python
# Content-driven judge: every verdict inverts with the swap
forward = [0, 1, 0, 1, 0, 1]
swapped = [1, 0, 1, 0, 1, 0]
f = mm.judge_swap_check(forward, swapped)
# ✅ [⑱ judge-swap] Position-lock rate 0.0% ≤ 35.0% (6/6 verdicts inverted
#    with the swap). Content-driven.

# Content-blind judge: verdicts identical in both orders
forward = [0, 1, 0, 1, 0, 1]
swapped = [0, 1, 0, 1, 0, 1]
f = mm.judge_swap_check(forward, swapped)
# 🔴 [⑱ judge-swap] Position-lock rate 100.0% > 65.0% (6/6 verdicts stayed
#    with the slot after AB→BA swap). Judge is reading position, not content.
```

Run `python examples/demo_judge.py` to see a mock content-blind judge pass
⑭⑮⑯⑰ and get caught only by ⑱ — no API key needed.

**Parameters:**
| Param | Default | Notes |
|---|---|---|
| `forward_results` | required | `[0, 1, ...]` — winners in original (A, B) order |
| `swapped_results` | required | `[0, 1, ...]` — winners in swapped (B, A) order |
| `position_lock_threshold` | 0.65 | lock_rate above this → FAIL |
| `noise_threshold` | 0.35 | lock_rate above this → WARN |

Pairs containing values outside {0, 1} (e.g. -1 parse failures) are excluded.

**Levels:**
- `FAIL` — lock_rate > position_lock_threshold, or forward/swapped length mismatch
- `WARN` — lock_rate in the noise band, or no valid pairs
- `OK` — lock_rate ≤ noise_threshold

---

#### `judge_run` — automatic orchestration (`judge.py`)

`judge_run` eliminates the friction of collecting scores yourself. It calls the
judge function, fires all four probes automatically, and seals a chain-linked
`_type: judge_run` entry into the ledger.

```python
from measure_mirror.judge import anthropic_judge, openai_judge, judge_run

# Step 1: build a judge callable
judge_fn = anthropic_judge(
    model="claude-opus-4-8",
    # Optional: override system prompt
    system_prompt="You are a strict, impartial evaluator.",
    # Optional: override prompt formatter
    prompt_fn=lambda item: f"Which is better? A: {item['a']}  B: {item['b']}",
    pairwise=True,   # True = A/B comparison; False = 1-10 rating
)

# Step 2: prepare items
pairs = [
    {"prompt": "Explain gradient descent",
     "a": "Response from model A", "b": "Response from model B"},
    ...  # as many as you need
]

# Step 3: run + auto-probe
result = judge_run(
    "mm_ledger.jsonl",  # ledger path — entry is chain-linked and sealed
    "my_llm_eval_v1",   # claim_id — links to a preregister entry if you have one
    judge_fn=judge_fn,
    items=pairs,
    runs=2,              # 2 = call each item twice; enables ⑭ + ⑯
    pairwise=True,       # True = enable ⑮ bias check
    swap_positions=True, # extra AB→BA pass; enables ⑱ swap test
)

# Findings from ⑭⑮⑯⑰
for f in result["findings"]:
    print(f"  {f.level}  [{f.probe}]  {f.msg}")

# Raw data
print(result["scores"])        # run-1 score per item
print(result["score_pairs"])   # (run1, run2) per item — None if runs=1
print(result["ledger_entry"])  # the sealed ledger entry
```

**Return value keys:**

| Key | Type | Contents |
|---|---|---|
| `findings` | `list[Finding]` | probe results (⑭⑮⑯⑰⑱ + `judge-parse`) |
| `scores` | `list[int]` | raw run-1 scores (one per item, may contain -1) |
| `score_pairs` | `list[tuple]` or `None` | `(run1, run2)` pairs; `None` if `runs=1` |
| `swap_scores` | `list[int]` or `None` | swapped-order scores; `None` unless `swap_positions` |
| `parse_failures` | `int` | items excluded due to unparseable responses |
| `n_items` | `int` | number of items evaluated |
| `runs` | `int` | number of repetitions performed |
| `pairwise` | `bool` | whether pairwise mode was used |
| `ledger_entry` | `dict` | chain-linked entry appended to ledger |

**Which probes run under which conditions:**

| Probe | Condition |
|---|---|
| ⑭ `judge_consistency_check` | always when `runs ≥ 2` |
| ⑮ `judge_bias_check` | always when `pairwise=True` |
| ⑯ `inter_rater_agreement` | **never auto-fired** — standalone-only, for two genuinely different judges (same-judge re-runs are ⑭'s job) |
| ⑰ `judge_score_sanity` | always |
| ⑱ `judge_swap_check` | when `swap_positions=True` (pairwise only) |
| `judge-parse` | WARN when >10% of responses unparseable; FAIL when none parsed |

**Parse-failure handling** — judge responses that cannot be parsed score -1.
Items with a -1 in any run are excluded from every probe, so parse noise cannot
distort ⑮ bias or ⑰ sanity results. The exclusion count is recorded in the
ledger entry (`parse_failures`).

---

### Group 7 — Ranking integrity ⑲⑳

The judge probes (Group 6) audit individual verdicts. These two probes audit the
**rankings built from those verdicts** — the leaderboard layer where most
publication claims actually live.

---

#### ⑲ `judge_transitivity_check`

**Catches**: preference cycles (A>B>C>A) in pairwise tournaments — a judge with
no consistent quality scale.

When a judge ranks more than two models via pairwise comparisons, the aggregated
preferences must form a transitive order. A cycle means any leaderboard built
from these verdicts is an artifact of match ordering: run the bracket in a
different order, get a different champion.

```python
# matches: [(model_a, model_b, winner), ...] — winner 0 = first, 1 = second
# Repeated matches of the same pair aggregate by majority vote.

matches = [("gpt", "claude", 0),     # gpt > claude
           ("claude", "llama", 0),   # claude > llama
           ("gpt", "llama", 0)]      # gpt > llama — transitive ✓
f = mm.judge_transitivity_check(matches)
# ✅ [⑲ judge-transitivity] Preference graph over 3 models is acyclic —
#    a consistent ranking exists.

matches = [("gpt", "claude", 0),     # gpt > claude
           ("claude", "llama", 0),   # claude > llama
           ("llama", "gpt", 0)]      # llama > gpt — cycle!
f = mm.judge_transitivity_check(matches)
# 🔴 [⑲ judge-transitivity] Preference cycle detected: gpt > claude > llama > gpt.
#    Judge is not applying a consistent quality scale.
```

Exactly tied pairs (equal wins each way) produce no edge and cannot create a
false cycle; the OK message reports how many ties were excluded.

**Levels:**
- `FAIL` — at least one cycle (an example path is shown)
- `WARN` — fewer than 3 distinct models, or no matches
- `OK` — preference graph is acyclic

---

#### ⑳ `ranking_stability_check`

**Catches**: ranking mirages — "model A beats model B" claims that flip when the
same-sized sample is redrawn.

Bootstrap resampling: redraw item indices with replacement `n_boot` times and
measure how often the observed winner stays the winner. Deterministic (seeded
RNG) — the same inputs always produce the same Finding, preserving mirror
reproducibility discipline.

```python
# Per-item scores for two models on the same items (paired by index)
scores_a = [9, 8, 9, 9, 8, 9, 8, 9]   # consistently high
scores_b = [3, 2, 3, 2, 3, 2, 3, 2]   # consistently low
f = mm.ranking_stability_check(scores_a, scores_b)
# ✅ [⑳ ranking-stability] Ranking 'A > B' survives 100.0% of 1000 bootstrap
#    resamples (n=8). Stable.

scores_a = [5, 9, 1, 8, 2, 7, 3]      # high variance,
scores_b = [6, 1, 9, 2, 8, 3, 7]      # nearly tied sums
f = mm.ranking_stability_check(scores_a, scores_b)
# 🔴 [⑳ ranking-stability] Ranking 'B > A' survives only 52.4% of 1000
#    bootstrap resamples (n=7). The ranking is noise.
```

**Parameters:**
| Param | Default | Notes |
|---|---|---|
| `scores_a`, `scores_b` | required | paired per-item scores; equal length, ≥ 5 items |
| `n_boot` | 1000 | bootstrap resamples |
| `seed` | 0 | RNG seed (determinism) |
| `min_stability` | 0.95 | required winner-preservation fraction |

**Levels:**
- `FAIL` — length mismatch · tied means · stability < 0.80
- `WARN` — fewer than 5 items · 0.80 ≤ stability < min_stability
- `OK` — stability ≥ min_stability

---

## Utility reference

### `calibrate`

Self-test: runs 5 synthetic known-good/bad cases and verifies expected outcomes.
Confirms the mirror itself has no regressions before using it to audit real results.

```python
findings = mm.calibrate()
mm.report("Mirror health", findings)
# ✅ [⚙ calibrate] 5/5 synthetic cases correct — mirror is calibrated.
```

```bash
mm calibrate
```

**Run before `witness()` or in CI** to confirm the tool is working correctly.

---

### `witness`

Execute a command, capture its output, and seal a tamper-evident run record.
Proves which command ran, when, and exactly what it produced.

```python
entry = mm.witness("ledger.jsonl", "my_model",
                   ["python", "evaluate.py", "--model", "my_model"])
# entry["output_hash"] changes if stdout/stderr/returncode ever changes
# entry is chain-linked — deletion is detected by verify_chain()
```

```bash
# CLI: calibrate first, then run and seal (--no-calibrate skips calibration)
mm run my_model -- python evaluate.py --model my_model
```

**Use case**: seal the exact output of your evaluation script before
publishing. If someone questions the numbers, the witness record proves
what the script produced.

---

### `retract`

Append a chain-linked retraction entry. See [⑫ cascade_check](#-cascade_check--retract) above.

---

### `certificate`

Issue a sealed verification certificate for a claim — the full integrity state
collapsed into one verifiable artifact for papers, READMEs, or release notes.

```python
# Structural certificate (prereg seal + chain + retraction status)
cert = mm.certificate("ledger.jsonl", "my_model")

# Full certificate — fold audit findings in
findings = mm.audit("ledger.jsonl", "my_model",
                    reported_metric="acc", reported_acc=0.72, n=500)
cert = mm.certificate("ledger.jsonl", "my_model", findings=findings)
```

```bash
mm certify my_model --pretty                  # structural only
mm certify my_model --acc 0.72 --n 500        # + audit findings folded in
mm certify my_model | gh gist create -        # publish externally
```

| Verdict | Trigger |
|---|---|
| `REJECTED` | chain broken · prereg seal tampered · claim retracted · any FAIL finding |
| `UNVERIFIED` | no pre-registration exists for this claim |
| `CERTIFIED-WITH-WARNINGS` | stale dependency or WARN findings |
| `CERTIFIED` | every check clean |

Key properties:
- Embeds the ledger's `anchor_hash` — the certificate attests to **one specific
  ledger state**; regenerate after any ledger change.
- The certificate itself is sealed (SHA-256) — any field edit is detectable.
- Not appended to the ledger; it is an output artifact like `anchor()`.

---

### `badge`

Render a certificate as an embeddable badge — the verdict made visible.

```python
cert = mm.certificate("ledger.jsonl", "my_model")
mm.badge(cert)                 # markdown — shields.io image for README
mm.badge(cert, fmt="svg")      # self-contained SVG, works offline
```

```bash
mm certify my_model --badge markdown >> README.md
mm certify my_model --badge svg > badge.svg
```

| Verdict | Color |
|---|---|
| `CERTIFIED` | brightgreen |
| `CERTIFIED-WITH-WARNINGS` | yellow |
| `UNVERIFIED` | lightgrey |
| `REJECTED` | red |

The SVG variant embeds the certificate `seal` and anchor-hash prefix in its
`<title>` tooltip — every badge is traceable back to the exact sealed
certificate it renders. No external service needed for the SVG form.

---

## Workflows

### Workflow 1: honest research paper

End-to-end flow for a classification result.

```python
from measure_mirror import mm

LEDGER = "experiment_ledger.jsonl"

# ─── 1. Before the experiment ────────────────────────────────
mm.preregister(LEDGER, "bert_sentiment",
               metric="acc",
               min_n=500,
               baseline=0.5,
               pass_threshold=0.70,
               kill_condition="accuracy falls below 0.65 on held-out",
               kill_threshold={"metric": "acc",
                                "threshold": 0.65,
                                "direction": "below"},
               depends_on=["sst2_dataset_v3"])   # dataset dependency

# ─── 2. Run and witness (optional but recommended) ───────────
mm.witness(LEDGER, "bert_sentiment",
           ["python", "train_and_eval.py", "--dataset", "sst2"])

# ─── 3. After results are in ─────────────────────────────────
findings = mm.full_audit(
    LEDGER, "bert_sentiment",
    reported_metric="acc", reported_acc=0.78, n=872,
    baseline=0.5,
    competing_name="LogReg baseline", competing_acc=0.73,  # ②
    reward_terms=["cross_entropy"],                         # ③
    train_items=train_ids, test_items=test_ids,             # ④a leakage
    seed_results=[0.77, 0.78, 0.79],                        # ⑤
    claimed_scope=["sentiment"],                            # ⑥
    tested_scope=["sst2", "yelp_polarity"],
    min_detectable_effect=0.03,                             # ⑧
    check_multiplicity=True,                                # ⑨
)
mm.report("BERT sentiment", findings)

# ─── 4. Anchor before submitting ─────────────────────────────
import subprocess
subprocess.run(["mm", "anchor", "--pretty"], check=True)
# → pipe to gist, s3, dropbox for timestamped external proof
```

---

### Workflow 2: CI gate with pytest

```python
# conftest.py
pytest_plugins = ["measure_mirror.pytest_plugin"]

# test_eval_integrity.py
from measure_mirror import mm
from measure_mirror.pytest_plugin import assert_clean

LEDGER = "production_ledger.jsonl"

def test_model_integrity():
    findings = mm.audit(LEDGER, "prod_model_v3",
                        reported_metric="acc", reported_acc=0.78, n=1000)
    assert_clean(findings)   # FAIL findings → pytest FAILS → CI goes red

def test_ledger_chain():
    findings = mm.verify_chain(LEDGER)
    assert_clean(findings)

def test_mirror_health():
    findings = mm.calibrate()
    assert_clean(findings)
```

---

### Workflow 3: closing a Resolved-Negative conclusion

```python
LEDGER = "oee_research_ledger.jsonl"

# Register each independent angle before running
angles = [
    ("oee_angle_wave",     "wave ODE — continuous field"),
    ("oee_angle_bilinear", "bilinear co-evolution"),
    ("oee_angle_alife",    "digital ALife (DISHTINY-style)"),
    ("oee_angle_folding",  "HP protein folding landscape"),
    ("oee_angle_gs",       "Gray-Scott reaction-diffusion"),
]
for cid, desc in angles:
    mm.preregister(LEDGER, cid,
                   metric="oee_score", min_n=50, baseline=0.5, pass_threshold=0.0,
                   kill_condition=f"{desc}: OEE above threshold")

# ... run all 5 experiments, all converge negative ...

# Gate the negative closure
f = mm.negative_audit(LEDGER,
                      angles=[cid for cid, _ in angles],
                      min_angles=3,
                      conclusion_scope=["self-organizing_OEE_in_silico"],
                      tested_scope=["digital_field", "alife_sim",
                                    "protein_HP", "reaction_diffusion"])
mm.report("OEE Resolved-Negative", [f])

# Anchor the final negative conclusion
import subprocess, json
snap = json.loads(subprocess.check_output(["mm", "anchor", "--ledger", LEDGER]))
print(f"Anchored: {snap['anchor_hash'][:12]}...")
```

---

### Workflow 4: retraction and cascade cleanup

```python
LEDGER = "shared_lab_ledger.jsonl"

# ─── Discovered contamination in baseline dataset ────────────
mm.retract(LEDGER, "imagenet_baseline_v1",
           reason="discovered 12% test/train overlap in preprocessing step")

# ─── Check which published results are now stale ─────────────
published_claims = ["vit_paper_2023", "resnet_ablation", "downstream_nlp"]

for claim_id in published_claims:
    f = mm.cascade_check(LEDGER, claim_id)
    if f.level != "OK":
        print(f"⚠️  {claim_id}: {f.msg}")

# Output:
# ⚠️  vit_paper_2023: Claim 'vit_paper_2023' is STALE: depends (transitively)
#     on retracted claim(s): 'imagenet_baseline_v1'
# ⚠️  downstream_nlp: Claim 'downstream_nlp' is STALE: ...
```

---

### Workflow 5: MCP agent integration

Any MCP-compatible AI (Claude Code, Cursor, Windsurf) can call all probes
directly mid-conversation. The agent can audit a claim without writing any code.

```
# In .mcp.json
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

Example agent conversation:
```
User: "My model got 87.3% on SQuAD with n=200. Is this legit?"

Agent: [calls mm_register, then mm_audit]
→ ⚠️  [④a small-sample CI] n=200, acc=0.873 → 95% CI [0.820, 0.915]
   clears baseline(0.5). OK.
→ ⚠️  [⑦ too-good] Δ=+0.373 over baseline — suspiciously large.
   Investigate: data leakage? reward hacking?

[calls mm_grim_check with reported_acc=0.873, n=200]
→ ✅ OK — round(175/200, 3) = 0.875 ≠ 0.873. Checking: round(174/200,3)=0.870...
   Actually: round(175/200,3)=0.875 ≠ 0.873. Arithmetic inconsistency → FAIL.

"Your 87.3% is GRIM-impossible for n=200: no integer k satisfies
 round(k/200, 3) = 0.873. Either n or acc is mis-reported."
```

---

## Quick reference

| # | Function | What it catches | Auto in `audit()`? |
|---|---|---|---|
| ① | `preregister`/`audit` | metric swap, min_n, pass bar, seal tamper | ✅ |
| ① | `verify_chain` | entry deletion/insertion/tamper | manual |
| ② | `baseline_fairness` | crippled/tied/reversed baseline | via `full_audit` |
| ③ | `gaming_check` | metric in reward/loss | via `full_audit` |
| ④a | Wilson CI (in `audit`) | small-sample chance results | ✅ |
| ④a | direction (in `audit`) | worse than baseline (anti-signal) | ✅ |
| ④a | `leakage_check` | train∩test overlap | via `full_audit` |
| ⑤ | `multiseed_check` | unstable seeds, baseline in range | via `full_audit` |
| ⑥ | `scope_check` | over-generalized claims | via `full_audit` |
| ⑦ | `too_good_check` | suspicious Δ over baseline | via `full_audit` |
| ⑧ | `power_check` | n too small to detect effect | via `full_audit` |
| ⑨ | `multiple_comparisons_check` | Bonferroni alarm for k>1 experiments | via `full_audit` |
| ⑩ | `grim_check` | arithmetic impossibility | ✅ (FAIL only) |
| ⑪ | `falsifiability_check` | no kill-condition; triggered kill threshold | ✅ (when prereg valid) |
| ㉗ | `prereg_lint` | malformed seal: leaked kill-condition, bar at/below declared chance, unstructured kill, low n, undeclared pre-seal checks | standalone (pre-compute; auto in MCP `mm_register`) |
| ⑫ | `cascade_check` | retracted claim or stale dependency | ✅ (WARN/FAIL only) |
| ⑬ | `negative_audit` | premature negative closure; scope overshoot | via `full_audit(angles=...)` |
| ⑭ | `judge_consistency_check` | LLM judge flip-rate too high (unreliable judge) | standalone |
| ⑮ | `judge_bias_check` | judge favors position A or B systematically | standalone |
| ⑯ | `inter_rater_agreement` | Cohen's κ below threshold (poor agreement) | standalone |
| ⑰ | `judge_score_sanity` | judge assigns identical/near-identical scores | standalone |
| ⑱ | `judge_swap_check` | verdict follows the slot, not the content (AB→BA swap) | via `judge_run(swap_positions=True)` |
| ⑲ | `judge_transitivity_check` | A>B>C>A preference cycles in tournaments | standalone / `mm judge` |
| ⑳ | `ranking_stability_check` | ranking flips under bootstrap resampling | standalone / `mm judge` |
| — | `anchor` | complete ledger replacement | manual (before publish) |
| — | `calibrate` | mirror itself has regressions | manual (before witness) |
| — | `witness` | execution record: what ran, when, output hash | manual |
| — | `retract` | create retraction record (chain-linked) | manual |
| — | `certificate` | sealed verdict artifact for one claim (anchor-pinned) | manual (before publish) |
| — | `badge` | embeddable verdict badge (markdown / SVG) | manual (`mm certify --badge`) |

**Severity policy** across the codebase:
- `FAIL` — hard stop; result is invalid or self-contradicted
- `WARN` — flag for attention; result may be valid but requires scrutiny
- `OK` — check passed; this dimension is clean

---

## Threat model — what measure-mirror cannot catch

We red-teamed measure-mirror against deliberate fabrication. It loses, by design.
This section is the honest map of that loss — read it before trusting an `OK`.

**The core limit: measure-mirror checks *internal consistency*, not *source
truth*.** It verifies that the reported numbers don't contradict each other or
the arithmetic. It cannot verify that the numbers came from a real experiment.
Fabricate every number *consistently* and the whole audit returns `OK`. This is
not a bug we can fix — no tool can detect fraud from reported numbers alone if
the fraud is internally coherent.

Verified red-team results:

| Attack | Outcome |
|---|---|
| GRIM-consistent fake means (large `n`, values snapped to `k/N`) | **passes** — GRIM is a small-`N` gate (see ⑩ scope) |
| Fully fabricated study: pre-registered, large `n`, fair baseline, kill-condition, stable seeds | **passes `full_audit` clean** — every number was invented, consistently |
| `witness()` a lying script | **passes** — witness seals *that the script ran and produced this output*, not that the output is *true* |

Every defence (pre-registration, audit, witness, anchor) rests on the assumption
that the data and code are honest. measure-mirror hardens the *paper trail*, not
the *underlying truth*.

**What it does buy you — fraud is forced to be modest.** To pass, a lie must stay
humble. Reach for too much and a probe catches you:

| Greedy lie | Caught by |
|---|---|
| Suspiciously large Δ over baseline | ⑦ `too_good_check` |
| Small sample | ⑩ `grim_check`, ④a Wilson CI |
| Unstable / impossibly perfect seeds | ⑤ `multiseed_check` |
| Claim wider than tested | ⑥ `scope_check` |

So measure-mirror's real job is **not catching the determined fraud** (a rare,
unsolvable case) but **catching honest self-deception** — p-hacking, cherry-
picking, small-`n` overconfidence, premature closure. That is the *common* form
of research dishonesty, and the tool catches it. Read an `OK` as *"the numbers
are internally honest and not over-reached"*, never as *"this is true"*.

*(This map was drawn by red-teaming the tool until it broke — the most
measure-mirror thing we could do to it.)*

---

*Built while honestly killing our own projects. The makers ran it on themselves first.*  
*→ [Origin story](CHRONICLE.md)*
