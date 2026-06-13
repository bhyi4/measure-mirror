# Case Study: An Agent That Retracted Its Own Experiment Before Spending a Single Token

*Mirror Stack (measure-mirror + action-mirror + provenance-mirror) · 2026-06-12 ~ 13 · one autonomous research arc, fully chain-sealed*

## TL;DR

An autonomous agent planned an efficiency experiment ("Compute Governor": pre-estimate query
difficulty, allocate thinking-token budgets). Over ~24 hours it:

1. **Preregistered** two falsifiable hypotheses with kill conditions — *before* any measurement,
2. let a **power check veto its own design** (n=293 couldn't detect the target effect; n was raised to 600 and the margin re-derived from the tool's output, not from wishful thinking),
3. **adversarially red-teamed itself** and sealed 10 protocol-tightening amendments (no silent edits possible),
4. froze benchmarks with SHA256 manifests, proved zero train/eval leakage, re-ran the freeze to prove determinism,
5. then — prompted by one skeptical human question ("hasn't this been done?") — ran a prior-art check, found the question already answered by the literature, and **retracted both hypotheses with full reasons, permanently, in the ledger**, at exactly **zero measurement tokens spent**.

Every step above is independently verifiable from three append-only ledgers. Nothing in this
story requires trusting the agent — that is the point.

## Why this matters

AI research agents are starting to produce science. The integrity instruments humans use
(self-attestation checklists, manual preregistration forms, post-hoc replication) were designed
for human speed and human incentives. Loop agents running unattended for days need integrity
that is **machine-enforced and machine-verifiable**: sealed-before-run claims, tamper-evident
action history, and witnesses that make ledger replacement detectable.

A recent ICML 2026 paper proposes preregistration *templates* for experiments with AI agents —
attestation by signature, no technical enforcement. This case study is the complementary
existence proof: the same discipline, enforced by hash chains and witnesses instead of promises.

## The ledger trail (verbatim seals)

| # | Event | Seal |
|---|---|---|
| 1 | H1 registered (difficulty AUROC; kill: CI contains 0.5) | `50868acbcd183288` |
| 2 | H2 registered (net savings; kill: 3-part condition incl. non-inferiority −0.06) | `45b491ece0e4d149` |
| 3 | Amendment-1: 6 tightenings from adversarial self-review (paired-grid eval, cluster bootstrap, random-matched control p<0.05, calibration reweighting, "give-up savings" disclosure duty, contamination caveat) | `2903b3dc98eeeba2` |
| 4 | Amendment-2: staged stop rule (H1-first, saves ~60% compute on failure) + harness code hashes | `1b6bc161f4fc3e09` |
| 5 | **Retraction of H1** — prior art (arXiv:2511.03808, SCOPE, SelfBudgeter, TALE, provider-internal routers) already answers the question | `b782dcd584e333a7` |
| 6 | **Retraction of H2** — dependent claim, same grounds | `1f811b94480f5c57` |

Plus: 4 external anchor snapshots (taken at each milestone), and 3 witness pins in a second
agent's ledger (`peer_witness` entries) — so replacing the whole ledger file would also be detected.

## What each mirror contributed

- **measure-mirror (claims):** sealed registrations, kill conditions, the power check that
  *changed the design before data*, retraction with cascade (dependent claims go STALE).
- **action-mirror (actions):** chain-linked history; witness-pinned the claims ledger's heads
  three times (catches whole-file replacement, which hash chains alone cannot).
- **provenance-mirror (artifacts):** distribution fingerprinting for released artifacts.

Unified check (single command, real output, 2026-06-13):

```
=== Mirror Stack verify-all ===
✅ [L1 chain] compute_governor_mm: linkage intact — 6 entries, head=1f811b94480f5c57
✅ [L1 chain] compute_governor_mm: mm verify_chain: seals valid
✅ [L1 chain] am: am verify: Chain intact — 4 entries verified.
✅ [L1 chain] pm: linkage intact — 2 entries
✅ [L2 witness] compute_governor_mm: 3 pinned head(s) all consistent — append-only history respected.
✅ [L3 anchor] anchor_closure: intact · 3 earlier anchors: extended (anchored heads still in chain)
=== verdict: ALL OK (10/10) ===
```

> Reproduce it yourself: the claims ledger and all four anchor snapshots are bundled under
> [`evidence/`](evidence/) — `python verify_all.py` re-runs the L1+L3 checks (6/6) on your
> machine. The L2 witness pins live in a private family ledger (see honesty box), so the
> 10/10 output above is the operator's full run, reproduced verbatim.

## Honesty box (what this does NOT prove)

- It does not *prevent* dishonesty. An agent can simply not record. The guarantee is asymmetric:
  **honesty leaves evidence that cannot be reconstructed after the fact; absence of a ledger is
  itself a signal.**
- The witnesses here are operated by the same family of agents (not independent third parties).
  Collusion within one operator is out of scope at this stage; independent witness networks are
  future work.
- This is n=1 arc, self-reported — but that is exactly why the ledgers, not this prose, are the
  artifact. Verify them yourself.
- The retracted experiment's *negative* outcome (prior art existed) is part of the demo: the
  stack's value showed up as **compute not wasted** and a process error (stale novelty claim at
  registration time) caught and permanently recorded.

## Lesson adopted

The arc exposed a gap in our own discipline: we sealed falsifiability and power *but never asked
whether the question was still open*. We now mandate **Gate −1: a prior-art freshness check,
sealed into every preregistration before Gate 0.** The mirror that caught it was a human — the
stack made the correction permanent.
