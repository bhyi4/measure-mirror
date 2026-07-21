"""Seal upgrade regression: full 64-hex seals + legacy 16-hex acceptance.

The 16-hex (64-bit) truncation allowed a dishonest sealer to birthday-search
(~2^32) two entries sharing one seal. New entries seal with the full digest;
legacy ledgers must keep verifying unchanged.
"""
import hashlib
import json

from measure_mirror import mm


def _legacy_entry(claim_id, prev_seal="genesis"):
    """Build an entry sealed the OLD way (truncated) — simulates a pre-upgrade ledger."""
    e = {"ts": "2026-01-01T00:00:00", "claim_id": claim_id, "metric": "acc",
         "min_n": 10, "baseline": 0.0, "pass_threshold": 0.5, "prev_seal": prev_seal}
    e["seal"] = hashlib.sha256(
        json.dumps(e, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
    return e


def test_new_seal_is_full_digest(tmp_path):
    led = str(tmp_path / "l.jsonl")
    e = mm.preregister(led, "c1", metric="acc", min_n=10, baseline=0.0, pass_threshold=0.5)
    assert len(e["seal"]) == 64


def test_legacy_truncated_seal_still_verifies():
    e = _legacy_entry("old1")
    assert mm._verify_seal(e) is True


def test_legacy_tamper_still_detected():
    e = _legacy_entry("old2")
    e["baseline"] = 0.9
    assert mm._verify_seal(e) is False


def test_new_seal_tamper_detected(tmp_path):
    led = str(tmp_path / "l.jsonl")
    e = mm.preregister(led, "c2", metric="acc", min_n=10, baseline=0.0, pass_threshold=0.5)
    e["baseline"] = 0.9
    assert mm._verify_seal(e) is False


def test_mixed_chain_legacy_then_full(tmp_path):
    """Legacy 16-hex entry followed by a new full-seal entry: chain verifies."""
    led = tmp_path / "mixed.jsonl"
    old = _legacy_entry("old3")
    led.write_text(json.dumps(old, ensure_ascii=False) + "\n", encoding="utf-8")
    mm.preregister(str(led), "new1", metric="acc", min_n=10, baseline=0.0, pass_threshold=0.5)   # prev_seal = legacy 16-hex head
    findings = mm.verify_chain(str(led))
    assert all(f.level != "FAIL" for f in findings), [f.msg for f in findings]


def test_short_but_not_16_rejected():
    """Only exactly-16-hex legacy seals are accepted — no other truncations."""
    e = _legacy_entry("old4")
    e["seal"] = e["seal"][:12]
    assert mm._verify_seal(e) is False
