# MIRROR-SPEC v1.1 — Mirror Stack Ledger Format & Verification Protocol

**Status: v1.1, amended 2026-07-17** (v1.0 ratified 2026-07-02; see Amendment log). Frozen per §9 — normative statements
will not change; clarifications append as errata. Ratification criterion:
two clean-room interoperability rounds (an agent given only this document
achieved byte-exact seal reproduction, 5/5 blind-vector verdicts, and valid
ledger production including amendments).

This document is the **normative specification** of the Mirror Stack ledger format.
The Python packages (`measure-mirror`, `action-mirror`, `provenance-mirror`) are
**reference implementations** of this spec, not its definition. Any system, in any
language, that produces or verifies ledgers conforming to this document is a
Mirror Stack implementation.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are to be interpreted
as described in RFC 2119.

---

## 1. Purpose and honest scope

A Mirror Stack ledger makes honesty **provable**, not mandatory. It guarantees:

- **Integrity** — any modification, deletion, insertion, or reordering of past
  entries is detectable (§6).
- **Non-erasability** — negatives, retractions, and amendments are appended,
  never removed; a missing ledger is itself a signal.
- **Falsifiability** — claims are sealed together with their kill conditions
  *before* results exist.
- **Verifiability** — every guarantee above is checkable by a third party from
  the ledger bytes alone, with zero dependencies.

It does NOT guarantee:

- **Content truth.** A sealed lie is still a lie; the seal proves only *when*
  it was told and that it was not silently edited.
- **Independence.** Witnesses within one operator's control are not independent
  judges. Independence is a social property and cannot be built into a format.
- Bitcoin anchoring (§6.5) proves **no-backdating only** — that the ledger head
  existed before a given block — never that its contents are correct.

## 2. Terminology

| Term | Meaning |
|---|---|
| **ledger** | An append-only UTF-8 JSONL file; one JSON object ("entry") per line. |
| **entry** | A single JSON object in a ledger. |
| **seal** | 16-char hex digest binding an entry's content (§4). |
| **chain** | The linkage of entries via `prev_seal` (§5). |
| **head** | The `seal` of the last entry in a ledger. |
| **anchor** | An out-of-ledger snapshot of a ledger's state (§6.4, §6.5). |
| **peer witness** | An entry in ledger A pinning the head of ledger B (§6.3). |

## 3. Ledger file format

1. A ledger MUST be a UTF-8 encoded file of newline-separated JSON objects
   (JSONL). Blank lines (empty or whitespace-only) MUST be ignored by
   verifiers. A non-blank line that parses as JSON but is not an object
   (e.g. `42`, `[1,2]`) makes the ledger malformed, exactly like unparseable
   JSON (§6.1 step 2). Bytes that do not decode as UTF-8 are likewise
   malformed content (§6.1 step 2), not an unreadable file. If a line
   contains duplicate keys, the last occurrence wins (common-parser
   behavior, pinned here because it changes recomputed seals).
2. Entries MUST only ever be appended. Implementations MUST NOT rewrite,
   reorder, or delete existing lines.
3. Every entry MUST contain the fields `seal` (string) and `prev_seal`
   (string), and SHOULD contain an ISO 8601 timestamp field (`ts`, or
   `ts_start`/`ts_end` for command witnesses). A verifier MUST treat a
   missing `seal` or `prev_seal` as the empty string, and a present but
   non-string value by its decimal/JSON string form (`42` → `"42"`); either
   way the §6 comparisons then fail naturally and the verifier MUST NOT
   crash.
4. Timestamps SHOULD be UTC with an explicit `Z` suffix. Verifiers MUST accept
   timestamps without a timezone suffix (legacy entries exist).
5. The bytes of a ledger line are NOT required to be the canonical
   serialization of §4 — key order and whitespace on disk are unconstrained.
   Only the seal *computation* canonicalizes. Producers SHOULD terminate
   lines with LF (`\n`); note that any byte-level change, including
   CRLF↔LF conversion, alters the whole-file hashes used by L3 anchors
   (§6.4–§6.5) — by design.

## 4. Seal algorithm (normative)

Given an entry object `E`:

```
body       = E with the keys "seal" and "sig" removed
serialized = canonical-JSON(body)          # §4.1, byte-exact
seal       = lowercase hex SHA-256 of serialized (UTF-8 bytes), truncated to
             the first 16 characters
```

### 4.1 Canonical JSON (normative, byte-exact)

The canonical serialization is the output of Python's
`json.dumps(body, sort_keys=True, ensure_ascii=False)`. Because seals bind
bytes, a cross-language implementation MUST reproduce these bytes exactly.
Spelled out:

1. **Key order** — object keys sorted by Unicode codepoint, **recursively at
   every nesting level**.
2. **Separators** — `", "` between array/object members, `": "` between key
   and value (single space after comma and colon, none before).
3. **Strings** — non-ASCII characters emitted as raw UTF-8 (NOT `\uXXXX`).
   The two mandatory escapes are `\"` and `\\`; control characters U+0000–1F
   use `\b \f \n \r \t` where defined, `\u00XX` otherwise.
4. **Numbers** — integers without decimal point or exponent (`120`); floats
   as the **shortest string that round-trips to the same IEEE-754 double**
   (`0.5` never `0.50`; `1` and `1.0` are *different values with different
   serializations*). Where shortest-round-trip renderings differ across
   languages (e.g. exponent-notation thresholds: Python emits `1e+16`,
   JavaScript `10000000000000000`), **Python's `repr` output is normative**.
   Producers SHOULD avoid non-finite floats (`NaN`/`Infinity` are not
   interoperable JSON) and SHOULD avoid magnitudes where exponent notation
   kicks in.
5. **Literals** — `true`, `false`, `null`.

The conformance vector `valid_04_numbers.jsonl` pins these bytes (nested
keys, floats, ints, unicode, booleans, null); an implementation whose seals
match it has the canonicalization right.

Rules:

1. The keys `seal` and `sig` MUST be excluded from the sealed body. All other
   keys, including `prev_seal`, MUST be included.
2. Serialization MUST follow §4.1 byte-exactly.
3. The seal MUST be the full 64-lowercase-hex digest. *(v1.1 — v1.0 truncated
   to 16 hex chars. Verifiers MUST accept an exactly-16-hex seal by comparing
   it against the first 16 characters of the recomputed digest: legacy
   acceptance. No other lengths are valid.)*
4. An entry MAY additionally carry an Ed25519 signature. `sig` is the
   lowercase-hex Ed25519 signature over the **UTF-8 bytes of the seal string
   as stored** (64-hex; 16-hex in v1.0 ledgers — not the raw digest); `pubkey` is the
   lowercase-hex 32-byte raw public key. `pubkey` IS part of the sealed body;
   `sig` is not.
5. Seals do not guarantee uniqueness: identical entries produce identical
   seals (and v1.0 legacy 64-bit truncation admits collisions in principle). Verifiers do not
   check for duplicate seals; chain position (§5), not the seal value, is an
   entry's identity.

*Seal-width note (v1.1):* v1.0's 16-hex (64-bit) truncation was a
tamper-evidence checksum only: a **dishonest sealer** can birthday-search
(~2^32 hashes, GPU-minutes) two different entries sharing one truncated seal
and swap them after sealing. v1.1 therefore seals with the full 256-bit
digest, closing that gap at the chain layer; whole-file SHA-256 (§6.4, §6.5)
remains the file-level commitment. Legacy 16-hex seals verify by prefix —
their original (weaker) strength is unchanged.

## 5. Chain rules

1. The first entry of a ledger MUST have `prev_seal` equal to `"genesis"`,
   compared ASCII-case-insensitively.
2. Every subsequent entry MUST have `prev_seal` equal to the `seal` of the
   immediately preceding entry (exact string match).
3. A producer appending to a missing or empty ledger MUST treat the previous
   seal as `"genesis"`.

## 6. Verification levels

### 6.1 L1 — Linkage check (format-agnostic)

Input: ledger path. Output: `(ok, message, entries)`.

A conforming L1 verifier MUST evaluate, in order:

1. File unreadable → FAIL (`entries = null`)
2. Any non-blank line not parseable as a JSON **object** → FAIL
   (`entries = null`; non-object JSON like `42` or `[1,2]` is malformed, §3.1)
3. Zero entries → FAIL (`entries = []`)
4. First entry `prev_seal` ≠ `"genesis"` (case-insensitive) → FAIL
5. Any entry `i > 0` whose declared `prev_seal` ≠ declared `seal` of entry
   `i−1` → FAIL, reporting the first broken index
6. Otherwise → OK, reporting entry count and head seal

Indices are 0-based entry positions (blank lines excluded), not file line
numbers. Missing `seal`/`prev_seal` fields are read as `""` (§3.3) and fail
steps 4–5 naturally. On step 4/5 failures `entries` is the parsed list (only
steps 1–2 return `null`). Conformance (§8) is judged on the OK/FAIL verdict
and, for FAILs, which step fired; human-readable message text is informative
only.

L1 compares **declared** seals only; it MUST NOT require knowledge of record
types, so it works on any ledger following §3–§5.

Detects: in-place tampering of any field that shifts `seal` expectations,
deletion, insertion, reordering, malformed files.
Does NOT detect: consistent whole-file replacement (a rewritten ledger with a
valid internal chain passes L1 — this is L2/L3's job).

### 6.2 L1+ — Seal recomputation

A recomputing verifier (e.g. `verify_chain`) SHOULD additionally recompute
each entry's seal per §4 and FAIL on mismatch. L1+ runs only when L1
returned OK (a broken or malformed chain is already FAIL; recomputation adds
nothing). This needs no record-type knowledge — §4 is uniform across all
types. Reporting the first mismatch is sufficient. This catches edits that
keep the declared chain consistent but alter sealed content.

### 6.3 L2 — Peer witness (cross-ledger)

A **peer_witness** entry in ledger A records ledger B's state (schema §7).
Verification of A's witnesses against current B MUST check, per witness:

1. `len(B) ≥ peer_entries`, else **TRUNCATED** → FAIL
2. `B[peer_entries − 1].seal == peer_head_seal`, else **REWRITTEN** → FAIL
3. No witness entries exist for the named peer → WARN (unverifiable)
4. All pinned heads consistent → OK

This position-pinned check detects whole-ledger replacement and truncation —
the attacks L1 cannot see. Erasing history then requires rewriting **all**
witnessing ledgers simultaneously.

### 6.4 L3a — Local anchor

An **anchor** artifact (schema §7) snapshots a ledger. Verification:

```
if SHA256(ledger bytes) == anchor_hash            → "intact"   (OK)
elif len(ledger) ≥ entry_count
     and ledger[entry_count − 1].seal == head_seal → "extended" (OK, append-only)
else                                               → "REPLACED?" (FAIL)
```

Anchors MUST be stored outside the ledger (separate file, external service).

### 6.5 L3b — Bitcoin anchor (OpenTimestamps)

A manifest (schema §7) listing ledger hashes and heads is stamped with OTS.
Verification MUST extract the Bitcoin block height and merkle root from the
`.ots` proof and compare the merkle root against an **independent public block
explorer** (not the prover's own node). Match → the manifest, hence the ledger
heads, existed before that block's time. Scope: no-backdating only (§1).

### 6.6 Stack orchestration

A full-stack verification (`verify_all`) SHOULD run: L1/L1+ on each ledger →
L3a for each anchor → L2 for each witness relationship. Verdict is **ALL OK**
iff no check FAILed; WARNs (e.g. missing witnesses) MUST be reported but do not
break the verdict.

## 7. Record types

All types share §3–§5 (`seal`, `prev_seal`, timestamp). Fields marked (opt)
are optional. Verifiers MUST ignore unknown extra fields (forward
compatibility); producers SHOULD NOT invent new meanings for reserved names.

### 7.1 Ledger-resident types

**preregister** — seal a claim before results exist. Identified by shape
(has `claim_id` + `metric` + `pass_threshold`), not by `_type`: legacy
entries carry no `_type` field. Producers MAY add `_type: "preregister"`;
verifiers and audit tools MUST accept both forms.
`ts, claim_id, metric, min_n, baseline, pass_threshold` + (opt)
`kill_condition` (human-readable falsification criterion), `kill_threshold`
(object; reserved keys `metric`, `threshold`, `direction`:"below"|"above" —
other keys implementation-defined), `depends_on` (list of claim_ids, enables
retraction cascade), `metric_range` ([lo,hi] or "unbounded"), `chance` (float).
`kill_condition`/`kill_threshold` SHOULD be present together; a preregistration
without either is unfalsifiable and SHOULD be flagged by audit tooling.

**amendment** — a preregister-shaped entry carrying **top-level
`amends_seal`** (the seal of the entry it amends) — that is the normative
and sole identifying marker (`_type`, if present, MAY be `"preregister"` or
`"amendment"`; verifiers MUST NOT rely on it). Two additional legacy conventions exist in real ledgers and MUST be
tolerated (but need not be produced): a duplicated `amends_seal` plus a
`change` summary inside `kill_threshold`, and an `"[AMENDMENT to seal …]"`
prefix on `metric`. Amendments change kill conditions *visibly*; silent
edits are what the chain forbids.

**retraction** — `_type: "retraction"`, `ts, claim_id, reason`. Marks a claim
falsified/withdrawn. MUST be appended, never substituted for deletion.
Whether `claim_id` matches a prior preregistration is an audit-layer concern
(certificate/falsifiability tooling), outside L1/L1+ scope.

**witness** (command execution) — `_type: "witness"`, `ts_start, ts_end,
claim_id, command` (argv list), `returncode`, `run_status`:"ok"|"timeout"|
"error", `output_hash` = full 64-hex SHA-256 over *(v1.0: first 16 hex chars — legacy accepted)*
`"{returncode}\n{stdout}\n{stderr}"`.

**action** — `_type: "action"`, `ts, agent, action` + (opt) `target` (path,
claim_id, ticket…; set `target = <claim_id>` to bind an action to a claim),
`content_hash` (64-hex SHA-256 of artifact bytes; v1.0: 16-hex — legacy accepted), `payload` (free JSON —
**opaque to verifiers**), `pubkey` + `sig` (§4 rule 4).

**peer_witness** — `_type: "peer_witness"`, `ts, peer, peer_entries,
peer_head_seal, peer_anchor` (16-hex SHA-256 of peer file at witness time;
forensic only — legitimate appends change it, so verification uses the
position-pinned head, §6.3).

**verdict** (provenance) — `_type: "verdict"`, `ts, file_hash` (full 64-hex),
`origin` (string|null), `verdict` with precedence
`TAMPERED > SYNTHETIC > CONFLICTING > AUTHENTIC-SIGNED > UNVERIFIED`
(UNVERIFIED = "no usable signal", explicitly NOT evidence of fakery),
`signals` (object mapping probe id → result; probe ids ①…⑤ =
c2pa-manifest, generator-meta, ai-watermark, tamper-anchor, format-integrity).

**distribution** — `_type: "distribution"`, `ts, doc_id, recipient,
clean_hash, marked_hash` (fingerprinted copy for leak tracing).

### 7.2 Out-of-ledger artifacts

**anchor** — `_type: "anchor"`, `ts, ledger_path, entry_count, head_seal`
("empty" if ledger absent), `anchor_hash` (full SHA-256 of ledger bytes),
`chain_ok` (bool). Not chain-linked; stored externally.

**ots_anchor_manifest** — `_type: "ots_anchor_manifest"`, `ts, purpose,
ledger_count, ledgers` (list of `{ledger, path, bytes, sha256, head_seal}`),
accompanied by a binary `.ots` proof.

**certificate** — `_type: "certificate"`, `ts, claim_id, verdict`
(`REJECTED`|`UNVERIFIED`|`CERTIFIED-WITH-WARNINGS`|`CERTIFIED`) + (opt)
`prereg_seal, prereg_seal_ok, cascade, chain_ok, ledger_entries, anchor_hash,
findings {ok, warn, fail}`. An attestation artifact; not appended to ledgers.

## 8. Conformance

**Producer** conformance: emits entries per §3–§5 and §7; never rewrites
history; records amendments and retractions as appends.

**Verifier** conformance: implements at least L1 (§6.1) with the exact
evaluation order; full-stack verifiers implement §6.2–§6.6. A verifier MUST
have no dependencies beyond SHA-256, JSON, and file I/O (L3b additionally
needs an OTS parser and a public block explorer).

**Test vectors:** `spec/vectors/` contains valid and invalid ledgers with
expected verdicts. The vectors are companion artifacts distributed alongside
this spec (same repository), not part of the normative text: the text alone
suffices to implement; running the vectors is required only to *claim*
conformance. An implementation is conformant iff it reproduces every
expected verdict. (Seed suites: `tests/test_linkage_check.py`,
mirror-stack-mcp `tests/test_linkage_conformance.py`.)

## 9. Versioning

v1.0 is **frozen** once ratified: normative statements here will not change.
Clarifications may be appended as errata. Breaking changes (e.g. mandatory
`_type` on preregistrations, mandatory UTC timestamps) belong to a future v2.
A ledger valid under v1 remains verifiable forever — verifiability of old
records outranks format elegance.

## 10. Known legacy variances (normative acceptance)

Verifiers MUST accept, without warning:

1. `preregister`/`amendment` entries lacking `_type` (§7.1).
2. Timestamps without timezone suffix (§3.4).
3. `genesis` in any letter case (§5.1).
4. Heterogeneous `kill_threshold`/`payload` shapes (opaque beyond reserved keys).

## 11. Amendments (appended per §9; the v1.0 normative text above is unchanged)

### A1 — optional `preregister` grounding-declaration fields (2026-07-08)

Adds two **optional** producer fields to the `preregister` type (§7.1):

- `anchor_basis` (string, opt) — basis of the claim's positive-control anchor.
  Recommended vocabulary: `"dynamics-measured"` | `"structural-argument"`.
- `threshold_source` (string, opt) — provenance of the pass/kill threshold.
  Recommended vocabulary: `"external-fixed"` | `"observed-distribution"`.

Rationale: the mutual-grounding arc sealed two failure laws — a positive
control anchored on a static "structurally guaranteed" argument can be refuted
by the substrate's own dynamics, and a threshold re-derived from the observed
distribution is self-calibrating (attacker-draggable). Declaring both at seal
time makes them checkable before compute is spent; audit tooling (measure-mirror
probes ㉑/㉒) reads the fields back and evaluates them automatically.

Compatibility: non-breaking. Verifiers already MUST ignore unknown extra
fields (§7); L1/L1+ semantics are untouched (the fields are sealed like any
other entry bytes). Consumption is an audit-layer concern. Producers MAY omit
both fields; no vocabulary is enforced at the format level (audit tooling
treats unrecognized values as fail-closed advisories).

### A2 — optional `preregister` anchor-discipline + confound fields (2026-07-09)

Adds three more **optional** producer fields to the `preregister` type (§7.1):

- `anchor_cell` (string, opt) — placement of the positive-control anchor cell.
  Recommended vocabulary: `"deep-regime"` | `"threshold-cell"`.
- `anchor_line_source` (string, opt) — source of the anchor line.
  Recommended vocabulary: `"separator-aligned"` | `"copied-from-other-cell"`.
- `known_confounds` (array of strings, opt) — confounds declared BEFORE results.

Rationale: `anchor_cell` and `anchor_line_source` complete the anchor-discipline
trio with A1's `anchor_basis` — the three sealed `anchor-reproduction-failure`
subtypes (an anchor line copied from another cell, an anchor cell sitting on the
threshold, and a static structural guarantee all fail to reproduce). Audit
tooling (probes ㉔/㉕) evaluates the first two automatically. `known_confounds`
records confounds pre-declared before results — a pre-declared confound
legitimizes later attribution cycles, whereas one found post-hoc does not; audit
surfaces it as an INFO (a declaration, not a verdict).

Compatibility: identical to A1 — non-breaking, verifiers ignore unknown fields
(§7), L1/L1+ untouched, consumption is audit-layer, producers MAY omit, no
format-level vocabulary enforcement.

---

## Amendment log

- **v1.1 (2026-07-17)** — §4: seal widened from 16-hex (64-bit) truncation to the
  full 64-hex SHA-256 digest; verifiers MUST accept legacy exactly-16-hex seals by
  prefix. Rationale: 64-bit truncation permits a dishonest sealer to prepare
  colliding entry pairs (birthday ≈2^32) and swap them post-seal — reported by
  external review, verified, fixed. `output_hash`/`content_hash` widened likewise.
  Conformance vector `valid_05_legacy16.jsonl` added (legacy acceptance).
- **v1.0 (2026-07-02)** — initial ratification.

---

*Reference implementations:* `measure-mirror` (canonical `linkage_check`),
`action-mirror`, `provenance-mirror`, `mirror-stack-mcp` (MCP exposure).
*This spec is the source of truth; where code and spec disagree after v1.0
ratification, the code is wrong.*
