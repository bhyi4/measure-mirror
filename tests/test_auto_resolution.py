"""P1 — falsifiability_check auto-resolution: a kill-condition should be evaluated
from a *sealed* resolution (retraction / am_record) without hand-feeding reported_acc.
Unresolved claims keep the current WARN; an explicit reported_acc still wins.
"""
import json

import measure_mirror.mm as mm


def _prereg(led):
    mm.preregister(str(led), "c1", metric="acc", min_n=10, baseline=0.5, pass_threshold=0.6,
                   kill_threshold={"metric": "acc", "threshold": 0.55, "direction": "below"})


def _append(path, obj):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj) + "\n")


def test_unresolved_keeps_warn(tmp_path):
    led = tmp_path / "l.jsonl"
    _prereg(led)
    f = mm.falsifiability_check(str(led), "c1")
    assert f.level == "WARN"                                   # nothing sealed → current behaviour


def test_recover_numeric_result_from_am_record(tmp_path):
    led, am = tmp_path / "l.jsonl", tmp_path / "am.jsonl"
    _prereg(led)
    _append(am, {"_type": "action", "target": "c1", "payload": {"reported_acc": 0.40}})
    f = mm.falsifiability_check(str(led), "c1", am_ledger=str(am))
    assert f.level == "FAIL" and "auto-recovered" in f.msg     # 0.40 < 0.55 → kill fired


def test_recover_kill_verdict(tmp_path):
    led, am = tmp_path / "l.jsonl", tmp_path / "am.jsonl"
    _prereg(led)
    _append(am, {"_type": "action", "target": "c1", "action": "VERDICT c1 = KILL",
                 "payload": {"verdict": "KILL"}})
    assert mm.falsifiability_check(str(led), "c1", am_ledger=str(am)).level == "FAIL"


def test_recover_pass_verdict(tmp_path):
    led, am = tmp_path / "l.jsonl", tmp_path / "am.jsonl"
    _prereg(led)
    _append(am, {"_type": "action", "target": "c1", "payload": {"verdict": "PASS"}})
    assert mm.falsifiability_check(str(led), "c1", am_ledger=str(am)).level == "OK"


def test_sealed_retraction_is_resolved_negative(tmp_path):
    led = tmp_path / "l.jsonl"
    _prereg(led)
    _append(led, {"_type": "retraction", "claim_id": "c1", "reason": "kill fired"})
    f = mm.falsifiability_check(str(led), "c1")
    assert f.level == "FAIL" and "RETRACTED" in f.msg


def test_explicit_reported_acc_overrides_recovery(tmp_path):
    led, am = tmp_path / "l.jsonl", tmp_path / "am.jsonl"
    _prereg(led)
    _append(am, {"_type": "action", "target": "c1", "payload": {"reported_acc": 0.40}})  # would FAIL
    f = mm.falsifiability_check(str(led), "c1", reported_acc=0.90, am_ledger=str(am))
    assert f.level == "OK"                                     # explicit 0.90 wins, kill not tripped


def test_co_located_action_in_claims_ledger(tmp_path):
    # actions sometimes live in the same file as the prereg — recovery must see them too.
    led = tmp_path / "l.jsonl"
    _prereg(led)
    _append(led, {"_type": "action", "target": "c1", "payload": {"verdict": "KILL"}})
    assert mm.falsifiability_check(str(led), "c1").level == "FAIL"


def test_unknown_verdict_falls_through_to_warn(tmp_path):
    led, am = tmp_path / "l.jsonl", tmp_path / "am.jsonl"
    _prereg(led)
    _append(am, {"_type": "action", "target": "c1", "payload": {"verdict": "PENDING_REVIEW"}})
    assert mm.falsifiability_check(str(led), "c1", am_ledger=str(am)).level == "WARN"
