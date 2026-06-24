# What the Mirror Stack guarantees — four pillars

*[한국어 →](PILLARS_KO.md)*

> **One sentence:** the stack does not prevent dishonesty; it makes four specific properties of a
> record **provable** — and it is equally honest about the one property it cannot give you.

The stack proves a deliberately *narrow* thing about a record: not that a claim is **true**, but
that the record of it has these four properties. Each is delivered by a mechanism you can
**recompute**, not by our word.

## The four pillars

### 1. Integrity — you can't tamper
The ledger is a hash chain: every entry seals the one before it, so an edit, insertion, or reorder
breaks the chain and is detectable.
- **Mechanism:** `prev_seal→seal` linkage + native seal recomputation — `verify_self.py`,
  `am verify`, `stack_verify_all`.
- **Limit:** catches tampering with *recorded* entries. Who is allowed to check it → pillar 4.

### 2. Non-erasure — you can't memory-hole a failure
Retractions and negative verdicts are sealed into the **same** chain as the wins. You cannot
quietly delete a killed hypothesis; a removed failure breaks the chain.
- **Mechanism:** `mm_retract` (chain-linked); negatives sealed as actions; `tombstone.py` surfaces
  the graveyard and confirms the chain is intact.
- **Limit:** non-erasure *of what was sealed* — **not** completeness of what happened. A failure
  that was never recorded leaves no trace. (A missing ledger is a signal; absence *within* a ledger
  is not.)

### 3. Falsifiability — you commit before you look
A claim must seal its kill-condition **before** compute; a result must seal a resolution **before**
publish. Moving the goalposts after seeing the data is structurally blocked.
- **Mechanism:** `mm_preregister(kill_threshold=…)`; the `mirror-stack-gate` CLI / pre-commit hook
  actually exits non-zero (`mm_preflight` *judges*; the gate *enforces*).
- **Limit:** enforcement is opt-in, at *your* action site — the tool judges, your launcher/hook
  blocks. The MCP cannot reach external compute or a commit.

### 4. Verifiability — anyone recomputes, no trust required
The checks are deterministic and reproducible by a third party. The strongest form anchors a ledger
head into Bitcoin and cross-checks it on a **public** explorer — the clock is Bitcoin's and the
lookup is someone else's, not ours.
- **Mechanism:** `verify_self.py` / `verify_all.py`, `mm_anchor_bitcoin` / `mm_anchor_verify`, and
  the one-command `mirror-stack-verify` (chain + Bitcoin cross-check, no MCP client, no config).
- **Limit:** proves **integrity + precedence** (not-tampered, not-backdated) — **not** content truth.

## What is NOT a pillar (and why we say so out loud)

- **Transparency** is not a separate guarantee. Its safe form *is* pillar 4 (verifiable
  disclosure). Its unsafe form has a hole the stack can't close — **selective disclosure**: you can
  be "transparent" about a curated subset and simply never start a ledger for the embarrassing
  thing. We name *verifiability*, not *transparency*, on purpose.
- **Independence** — genuinely separate witnesses — is the deepest gap, and it is a **social**
  property, not a cryptographic one. No tool delivers it: an external Bitcoin anchor is a *clock*,
  not a *judge*; signing keys give attribution but one operator can mint many (Sybil). The honest
  path is **visibility** (record each reproducer, publish keys) so non-independence is *detectable*
  — not prevention. See the threat-model + independence notes in [MIRROR_STACK.md](MIRROR_STACK.md).
- **Identity** (optional Ed25519 in action-mirror) upgrades the "who" from self-asserted to
  attested — but that buys attribution / impersonation-resistance / non-repudiation, **still not**
  independence.

## In one line

**Integrity + non-erasure + falsifiability + verifiability** — four properties a machine can prove.
Independence it cannot — and we mark that as an open wall rather than dress it up as a feature.
That refusal to oversell is itself the point: a tool for honest measurement has to be honest about
its own reach.
