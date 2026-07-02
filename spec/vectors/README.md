# MIRROR-SPEC v1 Conformance Vectors

Ledger samples with expected verdicts (`expected.json`). An implementation is
SPEC-conformant iff it reproduces every expected verdict. Run against the
reference verifier:

```
python spec/reference_verifier.py --vectors spec/vectors
```

Regenerate deterministically with `python spec/gen_vectors.py` (seals are
computed per SPEC §4; no timestamps are generated at runtime).

| Vector | Tests | Expected |
|---|---|---|
| valid_01_minimal | preregister (no `_type`, §7.1) + retraction | L1 OK, L1+ OK |
| valid_02_legacy | uppercase `GENESIS` (§5.1), no-Z timestamp (§3.4), non-ASCII fields (§4.2), amendment via `amends_seal` | L1 OK, L1+ OK |
| valid_03_peer / valid_03_witness | action ledger + peer_witness pair (§6.3) | L1 OK, L1+ OK, L2 OK |
| valid_04_numbers | §4.1 canonical JSON byte-pin: shortest-repr floats, int vs float, recursive key sort, unicode, bool, null | L1 OK, L1+ OK |
| invalid_01_linkage_broken | `prev_seal` mismatch mid-chain | L1 FAIL |
| invalid_02_no_genesis | first entry not rooted at genesis | L1 FAIL |
| invalid_03_malformed | non-JSON line | L1 FAIL |
| invalid_04_empty | zero entries | L1 FAIL |
| invalid_05_tampered_content | kill threshold silently loosened; declared chain kept consistent | L1 OK, **L1+ FAIL** (§6.2 is why recomputation exists) |
| invalid_06_peer_truncated | peer shorter than witnessed count | L2 FAIL (TRUNCATED) |
| invalid_07_peer_rewritten | peer rewritten with valid internal chain | L1 OK, **L2 FAIL** (REWRITTEN — the attack L1 cannot see) |
| invalid_08_non_object | line parses as JSON but is not an object (`42`, §3.1) | L1 FAIL (malformed) |

## Findings from first conformance run (2026-07-02)

Running `valid_02_legacy` against the pre-SPEC implementations exposed a real
divergence, previously latent:

- Producers disagree on genesis case: `mm` emits `"genesis"` (mm.py:75),
  `am` emits `"GENESIS"` (am.py:78). 9 real family ledgers begin with
  uppercase `GENESIS`.
- `mm.linkage_check` accepts both (case-insensitive, mm.py:304) — this is the
  behavior SPEC §5.1 codifies.
- `mm.verify_chain` compared case-sensitively and therefore false-FAILed any
  am-produced ledger. **Fixed in 0.19.1** (first-entry genesis comparison is
  now case-insensitive, guarded by
  `test_verify_chain_accepts_uppercase_genesis`).
