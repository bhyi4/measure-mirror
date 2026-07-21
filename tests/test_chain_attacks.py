"""Adversarial chain-integrity tests — the first line of defense.

SPEC §4 rule 3 mandates prev_seal on every entry and says a missing prev_seal
is treated as the empty string, so the §5 linkage comparison fails naturally.
These pin the attack an earlier verify_chain silently passed: strip prev_seal
to downgrade a chained ledger to an unchained bag, then delete/reorder freely.
"""
import hashlib
import json

from measure_mirror import mm


def _reseal_stripping_prev(entry: dict) -> dict:
    """Attacker move: drop prev_seal, recompute a self-consistent seal."""
    e = {k: v for k, v in entry.items() if k not in ("seal", "prev_seal")}
    e["seal"] = hashlib.sha256(
        json.dumps(e, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return e


def _seed(led, *cids):
    for c in cids:
        mm.preregister(led, c, metric="acc", min_n=10, baseline=0.5, pass_threshold=0.6)
    return [json.loads(l) for l in open(led, encoding="utf-8") if l.strip()]


def test_strip_prev_seal_then_delete_is_caught(tmp_path):
    led = tmp_path / "l.jsonl"
    rows = _seed(str(led), "c1", "c2", "c3")
    attacked = [_reseal_stripping_prev(rows[0]), _reseal_stripping_prev(rows[2])]  # c2 deleted
    led.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in attacked) + "\n",
                   encoding="utf-8")
    assert any(f.level == "FAIL" for f in mm.verify_chain(str(led)))


def test_single_missing_prev_seal_is_caught(tmp_path):
    led = tmp_path / "l.jsonl"
    rows = _seed(str(led), "c1", "c2")
    rows[1] = _reseal_stripping_prev(rows[1])  # strip only the 2nd entry's link
    led.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                   encoding="utf-8")
    assert any(f.level == "FAIL" for f in mm.verify_chain(str(led)))


def test_first_entry_missing_prev_seal_is_caught(tmp_path):
    led = tmp_path / "l.jsonl"
    rows = _seed(str(led), "c1", "c2")
    rows[0] = _reseal_stripping_prev(rows[0])  # genesis entry loses its prev_seal
    led.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                   encoding="utf-8")
    assert any(f.level == "FAIL" for f in mm.verify_chain(str(led)))


def test_tamper_plus_reseal_middle_is_caught(tmp_path):
    """Reseal a tampered middle entry (keeping prev_seal): breaks at the next link."""
    led = tmp_path / "l.jsonl"
    rows = _seed(str(led), "c1", "c2", "c3")
    rows[1]["baseline"] = 0.9                                   # tamper
    body = {k: v for k, v in rows[1].items() if k != "seal"}
    rows[1]["seal"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()   # reseal
    led.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                   encoding="utf-8")
    assert any(f.level == "FAIL" for f in mm.verify_chain(str(led)))


def test_clean_chain_still_ok(tmp_path):
    led = tmp_path / "l.jsonl"
    _seed(str(led), "a", "b", "c")
    assert all(f.level == "OK" for f in mm.verify_chain(str(led)))
