# 🪞 Measurement Mirror — Discipline

*[한국어 →](DISCIPLINE_KO.md)*

> Does my measurement reflect the **truth**, or what I **want to see**? Verify that in **both
> directions** (false positive *and* false negative) — before believing either a positive or a
> negative result.

This is the **methodology** of the [Mirror Stack](https://github.com/mirror-stack): *how to
think* when you measure. The tools are *how to prove you thought it*. The two are married below —
each principle names the probe that seals it. A compact form of this is injected automatically by
the [unified MCP server](https://github.com/mirror-stack/mirror-stack-mcp) when an agent connects.

## The rule that comes first: tool vs. judgment

Most measurement failures come from a narrative ("X is special") contaminating the measurement
so it reflects hope. The discipline blocks that. But the discipline's own catches are **your
judgment**, guided by a checklist — and judgment can itself be a false positive or negative. So
the most important rule is honest attribution:

- **"the tool flagged X"** — only when an `mm_*` probe returned a **Finding you can quote**.
- **"applying the discipline, I suspect X"** — when it is your reasoning.

Both are valid. **Never borrow the tool's deterministic credibility for a judgment call.** A
catch with no Finding and no ledger entry is reasoning, not measurement.

## The 7 principles (each with its proof)

| # | Principle | What it blocks | Prove it with |
|---|---|---|---|
| 1 | **Preregistration** | post-hoc metric swap; moving the goalposts | `mm_preregister` (sealed, chained) |
| 2 | **Fair baseline** | a positive that is a "free pass" — crippled/weak baseline | `mm_baseline_fairness` |
| 3 | **Gaming line** | rewarding the eval metric directly = self-fulfilling. *Only removal/swap is honest; adding reward is an artifact.* | `mm_verify(reward_terms=…)` (gaming) |
| 4 | **Both directions** | false *positive* (illusory win) **and** false *negative* (unfair null, wrong framing, testing a stand-in not the real target) | `mm_negative_audit` |
| 5 | **Multi-seed + independent reproduction** | lucky seed; signal/noise confusion. *Agreement without reproduction is void.* | `mm_multiseed_check`; cross-witness from another agent (`am_witness`) |
| 6 | **Scope honesty** | over- and under-claiming — state what you closed and did **not** close | `mm_verify(claimed_scope, tested_scope)` |
| 7 | **Self-catch** | "too good to be true" — suspect your own result first | `mm_too_good_check` |

## The 4 augmentations the stack adds

The 7 are the mental anchors. The stack adds four checks the original checklist did not name:

- **A. Falsifiability (kill-condition).** Strengthens #1: don't just seal the bar — seal *what
  would kill the claim*. A claim with no kill-condition is unfalsifiable. → `mm_falsifiability_check`
  (the kill_threshold registered with `mm_preregister`).
- **B. Power (quantified false-negative).** Strengthens #4: *is n big enough to detect the
  effect?* Design-time, before spending compute. → `mm_power_check`.
- **C. Statistical hygiene.** Two cheap, decisive checks the checklist omitted: **multiple
  comparisons** (k experiments on one ledger → Bonferroni) and **GRIM** (reported acc × n must be
  an achievable integer — catches fabricated/typo'd numbers). → `mm_verify` (multiplicity, grim).
- **D. Judge reliability** *(conditional — only when an LLM judge is used).* Is the judge itself
  trustworthy? Consistency, position bias, AB→BA swap, A>B>C>A transitivity, degenerate scores.
  → `mm_judge_*` / `mm_inter_rater_agreement` / `mm_ranking_stability_check`.

## The record layer (your discipline, made tamper-evident)

The discipline says "think honestly." The stack adds "+ your record proves you did, and cannot
be faked after the fact":

- **Seal** claims and actions; tie each action to its claim (`am_record target=<claim_id>`).
- **Anchor** externally at milestones (`mm_anchor`) — detects whole-file replacement.
- **Witness** across agents (`am_witness`) — what hash chains alone cannot catch.
- **Retract** in the open (`mm_retract`) — negatives and withdrawals are sealed too; dependents
  go STALE. A *missing* ledger is itself a signal.
- Run `stack_verify_all` before declaring a verdict.

## Honest limits

- **The tool cannot do most of the catching.** Crippled baseline, a wrong stand-in model,
  gaming — these are *design* flaws found by reasoning, not arithmetic. The probes flag
  suspicion (e.g. "baseline suspiciously close"); the *insight* is judgment. Keep methodology
  primary; tools are proof where proof is possible, not a replacement for thinking.
- **This is guidance, not enforcement.** Nothing here forces honesty — an agent can simply not
  record. The guarantee is asymmetric by design: sealed preregistrations and time-pinned
  witnesses cannot be fabricated retroactively, so the *absence* of a record becomes the signal.
  Process can be enforced at the harness (hooks) or CI (a gate) layer — never at the "make the
  agent honest" level.
- **Independent reproduction means *independent*.** Witnesses operated by one family are not
  third parties (see the stack's honesty box).

---

*Lineage: this discipline was forged while killing our own projects — every closure in that work
is honest because the mirror caught the illusions (false positives) and guarded the premature
closures (false negatives). See the [case study](CASE_STUDY_compute_governor.md).*
