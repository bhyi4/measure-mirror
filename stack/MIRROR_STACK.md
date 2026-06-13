# 🪞🔎🪪 Mirror Stack — Joint Convention v0.1

*[한국어 →](MIRROR_STACK_KO.md)*

> **One sentence:** Make a loop agent's honesty *provable* instead of *promised*.
> This is not a system that prevents dishonesty — it is a system in which only honesty
> leaves evidence that cannot be reconstructed after the fact.

The stack bundles three existing, independent tools (no code merge — only conventions):

| Mirror | Question it answers | Ledger unit |
|---|---|---|
| **measure-mirror** (this repo) | Is this **claim** honest? (preregistration, kill conditions, 31 statistical/gaming probes) | claim |
| **action-mirror** | Did the agent actually **do** it? (chain-linked action history + mutual witness) | action |
| **provenance-mirror** | Where did this **artifact** come from? (distribution fingerprinting, tracing) | artifact |

Plus a shared **[witness hub](https://github.com/bhyi4/mirror-witness)** — a public, CI-verified
GitHub board where operators declare their ledger heads, so witnessing (J3) can extend beyond one
agent family. No server: GitHub provides timestamping + immutable history, CI provides the
consistency check.

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
