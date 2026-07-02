"""Regression tests for the kill_threshold validation gap (issue #18).

Malformed kill_threshold used to seal silently at preregister() and then
KeyError inside audit()/falsifiability_check(); first-write-wins made it
uncorrectable. Now: fail fast at seal time, and degrade gracefully on
already-sealed ledgers.
"""
import json

import pytest

from measure_mirror import mm


def test_preregister_rejects_kill_threshold_without_threshold_key(tmp_path):
    led = str(tmp_path / "l.jsonl")
    with pytest.raises(ValueError, match="numeric 'threshold' key"):
        mm.preregister(led, "c", metric="acc", min_n=10, baseline=0.5,
                       pass_threshold=0.6,
                       kill_threshold={"H1_reject_if": "effect>=0"})


def test_preregister_rejects_non_numeric_threshold(tmp_path):
    led = str(tmp_path / "l.jsonl")
    with pytest.raises(ValueError, match="must be numeric"):
        mm.preregister(led, "c", metric="acc", min_n=10, baseline=0.5,
                       pass_threshold=0.6,
                       kill_threshold={"threshold": "soon"})


def test_preregister_rejects_bad_direction(tmp_path):
    led = str(tmp_path / "l.jsonl")
    with pytest.raises(ValueError, match="'below' or 'above'"):
        mm.preregister(led, "c", metric="acc", min_n=10, baseline=0.5,
                       pass_threshold=0.6,
                       kill_threshold={"threshold": 0.55, "direction": "under"})


def test_preregister_accepts_valid_structured_threshold(tmp_path):
    led = str(tmp_path / "l.jsonl")
    e = mm.preregister(led, "c", metric="acc", min_n=10, baseline=0.5,
                       pass_threshold=0.6,
                       kill_threshold={"metric": "acc", "threshold": 0.55,
                                       "direction": "below"})
    assert e["kill_threshold"]["threshold"] == 0.55
    # and it evaluates without crashing
    f = mm.falsifiability_check(led, "c", reported_acc=0.51)
    assert f.level == "FAIL"  # 0.51 < 0.55 → triggered


def test_falsifiability_degrades_on_legacy_malformed_entry(tmp_path):
    """A ledger that already contains a malformed kill_threshold (written by an
    older version) must WARN, not KeyError."""
    led = tmp_path / "legacy.jsonl"
    entry = {
        "ts": "2026-07-03T00:00:00", "claim_id": "legacy", "metric": "acc",
        "min_n": 10, "baseline": 0.5, "pass_threshold": 0.6,
        "prev_seal": "genesis",
        "kill_threshold": {"H1_reject_if": "effect>=0"},  # no 'threshold'
    }
    led.write_text(json.dumps(entry, ensure_ascii=False) + "\n", encoding="utf-8")
    f = mm.falsifiability_check(str(led), "legacy", reported_acc=0.55)
    assert f.level == "WARN"
    assert "Malformed kill_threshold" in f.msg
