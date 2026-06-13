# 🪞🔎🪪 Mirror Stack — Joint Convention v0.1

> **One sentence:** Make a loop agent's honesty *provable* instead of *promised*.
> This is not a system that prevents dishonesty — it is a system in which only honesty
> leaves evidence that cannot be reconstructed after the fact.

The stack bundles three existing, independent tools (no code merge — only conventions):

| Mirror | Question it answers | Ledger unit |
|---|---|---|
| **measure-mirror** (this repo) | Is this **claim** honest? (preregistration, kill conditions, 31 statistical/gaming probes) | claim |
| **action-mirror** | Did the agent actually **do** it? (chain-linked action history + mutual witness) | action |
| **provenance-mirror** | Where did this **artifact** come from? (distribution fingerprinting, tracing) | artifact |

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

## verify-all — three verification layers

`verify_all.py` checks everything in one command:

- **L1 self-chain:** every entry's `prev_seal` links to the previous `seal` (format-agnostic),
  plus each tool's own seal verification where available.
- **L2 cross-witness:** pinned heads in the witness ledger match the claims ledger's actual
  history (append-only respected).
- **L3 external anchors:** current ledger vs stored snapshots — `intact` (unchanged),
  `extended` (anchored head still present at its anchored position), or **`REPLACED?`**
  (anchored head vanished — tampering signal).

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
snapshots bundled under [`evidence/`](evidence/). Run `python verify_all.py` in this directory
to verify them yourself.

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
