# 🪞🔎🪪 Mirror Stack — Joint Convention v0.1

<p align="center">
  <img src="docs/mirror_stack_og.png" alt="Mirror Stack" width="600">
</p>

*[한국어 →](MIRROR_STACK_KO.md)*

> **One sentence:** Make a loop agent's honesty *provable* instead of *promised*.
> This is not a system that prevents dishonesty — it is a system in which only honesty
> leaves evidence that cannot be reconstructed after the fact.

The stack bundles three existing, independent tools (no code merge — only conventions):

| Mirror | Question it answers | Ledger unit |
|---|---|---|
| **measure-mirror** (this repo) | Is this **claim** honest? (preregistration, kill conditions, 31 statistical/gaming probes) | claim |
| **[action-mirror](https://github.com/bhyi4/action-mirror)** | Did the agent actually **do** it? (chain-linked action history + mutual witness) | action |
| **[provenance-mirror](https://github.com/bhyi4/provenance-mirror)** | Where did this **artifact** come from? (distribution fingerprinting, tracing) | artifact |

All three are open (Apache 2.0), so every layer of the case study below is independently
verifiable — not just the claims layer.

Plus a shared **[witness hub](https://github.com/bhyi4/mirror-witness)** — a public, CI-verified
GitHub board where operators declare their ledger heads, so witnessing (J3) can extend beyond one
agent family. No server: GitHub provides timestamping + immutable history, CI provides the
consistency check.

The methodology that drives all this — *how to measure honestly* — is the
**[Measurement Mirror Discipline](DISCIPLINE.md)** (7 principles + their proving probes + the
stack's augmentations). A compact form is auto-injected by the unified MCP server on connect.

## The five conventions (J1–J5)

- **J1 action→claim:** when recording an experiment run in the action ledger, set
  `target=<claim_id>` — "this action was performed for this claim."
- **J2 claim→artifact:** embed SHA256 of the protocol document and data manifests inside the
  sealed registration text.
- **J3 witness:** another agent's ledger pins this ledger's head (`am witness`). Hash chains
  detect *edits*; witnesses detect **whole-ledger replacement**, which chains alone cannot.
- **J4 external anchor:** at every milestone, store an anchor snapshot (entry count, head seal,
  file hash) *outside* the ledger.
- **J5 distribution fingerprint:** when an artifact leaves the system, fingerprint it per
  recipient (provenance-mirror). The thinnest joint — stated honestly.

## Verification — two scripts, by layer of responsibility

The split is deliberate: a single mirror should not contain the engine that coordinates all
three. So verification is two files.

- **`verify_self.py`** — *measure-mirror's own job*. Verifies one claims ledger and its anchors:
  - **L1 self-chain:** every entry's `prev_seal` links to the previous `seal` + mm native seal recomputation.
  - **L3 external anchors:** current ledger vs stored snapshots — `intact` / `extended`
    (anchored head still at its position) / **`REPLACED?`** (anchored head vanished — tampering signal).
  - **Zero external-tool dependency** — needs only this repo. This is the part that legitimately
    belongs to measure-mirror.
- **`verify_all.py`** — *the stack orchestrator, one layer up*. Delegates L1+L3 to `verify_self`,
  then adds the check no single mirror can do alone:
  - **L2 cross-witness:** pinned heads in another agent's ledger match this claims ledger's
    actual history (append-only respected). Requires the action-mirror `am` CLI; if absent, L2
    is skipped and the stack degrades to measure-mirror's self-verification.

Run `python verify_self.py` to check the bundled evidence with nothing installed; run
`python verify_all.py --config your_stack.json` once you have all three mirrors wired together.
(When the stack grows beyond measure-mirror, `verify_all.py` is what graduates to its own repo —
`verify_self.py` stays here.)

### `tombstone.py` — the non-erasure view

A *view* built on the same linkage check, not a third verifier. `python tombstone.py LEDGER.jsonl`
lists the sealed **negatives** in a ledger — retractions and `KILL` / `NULL` / falsified verdicts —
and confirms the chain is intact, so a *deleted* failure would show up. This makes visible the
guarantee the stack leans on most: you cannot quietly drop a failure; a killed hypothesis stays on
the record. Honest scope is in the tool — it proves **non-erasure of what was sealed**, not
completeness of what happened.

## Threat model (honesty box)

**Catches:** post-hoc edits and deletions (L1), tail-cutting and whole-file replacement
(L2+L3), hypothesis-switching after results (sealed preregistration), silent protocol changes
after peeking (amendments are append-only).

**Does not catch:**
- An agent that simply never records. The guarantee is asymmetric by design: *sealed
  preregistrations and time-pinned witnesses cannot be fabricated retroactively* — so the
  absence of a ledger becomes the signal.
- Collusion within a single operator. The witnesses in the bundled case study are operated by
  the same agent family — they are **not independent third parties**. An independent witness
  network is future work.

### Multi-agent independence (verified, not guaranteed)

The discipline leans on multiple agents (independent reproduction; cross-witness). The stack
verifies the **record** of that — sealed, chained, witnessed — but **cannot guarantee the agents
were genuinely independent.** If agent B "reproduces" A's result but B is the same model, or A
told B the answer, the cross-witness still passes while the spirit of "reproduction, not
agreement" is violated. Independence cannot be manufactured by a tool; it must come from
genuinely separate operators/models.

Two consequences worth stating plainly:

- **The "who" is currently self-asserted.** An action's `agent` field is a plaintext label, not a
  cryptographic identity — the chain proves the *entry* wasn't altered, not that the named agent
  is who acted. There is no per-session signing key today; agent harnesses expose a `session_id`
  (a UUID), but it is self-reportable, not a signature.
- **The honest path is *visibility*, not prevention.** Recording each reproducer's model/operator,
  and sealing B's *own run artifact* (so "agreement without a run" is detectable), makes
  non-independence **visible** even though the tool cannot forbid it. A cryptographic **session
  identity** (each agent signs its entries; public keys published, e.g. on the witness board)
  would upgrade the "who" from self-asserted to attested — but even keys give attribution and
  impersonation-resistance, **not** independence: one operator can mint many keys (Sybil). Keys
  make *same-identity* provable; they do not make distinct keys *independent*.

## Evidence

See [`CASE_STUDY_compute_governor.md`](CASE_STUDY_compute_governor.md) — a full autonomous
research arc (preregistration → power-check design correction → adversarial amendments →
prior-art retraction at zero measurement cost), with the real claims ledger and anchor
snapshots bundled under [`evidence/`](evidence/). Run `python verify_self.py` in this directory
to verify them yourself (no install needed).

## Relation to neighboring work (checked 2026-06-13)

- *Preregistration for Experiments with AI Agents* (ICML 2026): a paper **template** with
  signature attestation, for experiments where agents are subjects — no technical enforcement.
  Complementary: same discipline, here enforced by hash chains and witnesses.
- Hash-chained agent action logs (e.g., community projects around LangChain): the action layer
  only. Mirror Stack adds the claims layer (machine-enforced preregistration + statistical
  probes) and mutual witness on top.
- Platform audit logs (LangSmith/Langfuse enterprise): administrative-action logs that require
  trusting the platform. Mirror Stack is local-first and self-sovereign; trust comes from
  chains, witnesses, and anchors instead of a vendor.
