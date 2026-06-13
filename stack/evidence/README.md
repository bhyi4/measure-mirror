# evidence/ — bundled verbatim artifacts

- `compute_governor.jsonl` — the claims ledger, byte-identical to the operator's original
  (chain-sealed; any edit would break `verify_all.py` L1).
- `anchor_*.json` — the four anchor snapshots. **One redaction for publication:** the
  `ledger_path` locator field was changed from an absolute local path to the relative
  `compute_governor.jsonl`. All integrity-bearing fields — `anchor_hash` (SHA256 of the
  ledger file), `head_seal`, `entry_count`, `ts` — are unchanged from the stored originals.
  You can confirm the redaction touched nothing load-bearing: `python ../verify_all.py`
  recomputes the ledger hash and must still match `anchor_hash` (verdict: intact/extended).
