"""Tests for the stack tombstone (non-erasure) view.

Verifies the two things the tool claims: it surfaces sealed negatives precisely
(retraction / kill / inconclusive — and NEVER a positive verdict), and it reports
whether the chain is intact (so a deleted failure would be detectable).
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "stack"))
import tombstone  # noqa: E402
from verify_self import OK  # noqa: E402

# A linked chain (prev_seal -> seal). Seals are arbitrary here — generic_linkage
# checks linkage, not hash correctness; that is mm_self_verify's separate job.
ENTRIES = [
    {"_type": "action", "action": "ran a thing", "seal": "s1", "prev_seal": "genesis"},
    {"_type": "action", "action": "VERDICT foo = KILL", "target": "foo",
     "payload": {"verdict": "KILL"}, "seal": "s2", "prev_seal": "s1"},
    {"_type": "retraction", "claim_id": "bar", "reason": "falsified by own kill-condition",
     "seal": "s3", "prev_seal": "s2"},
    {"_type": "action", "action": "VERDICT baz = supported", "target": "baz",
     "payload": {"verdict": "supported (not falsified)"}, "seal": "s4", "prev_seal": "s3"},
    {"_type": "action", "action": "VERDICT qux", "target": "qux",
     "payload": {"verdict": "INCONCLUSIVE_measurement_self_catch"}, "seal": "s5", "prev_seal": "s4"},
    {"_type": "action", "action": "noted a KILL switch in the UI copy",  # prose mention, not a verdict
     "seal": "s6", "prev_seal": "s5"},
]


def test_classify_each_kind():
    assert tombstone.classify(ENTRIES[1]) == "kill"
    assert tombstone.classify(ENTRIES[2]) == "retraction"
    assert tombstone.classify(ENTRIES[4]) == "inconclusive"


def test_positive_verdict_is_never_a_tombstone():
    # "supported (not falsified)" contains 'falsified' but is a PASS — must not flag.
    assert tombstone.classify(ENTRIES[3]) is None


def test_prose_mention_of_kill_is_not_a_tombstone():
    # only a structured verdict / "VERDICT … = X" declaration counts, not narrative.
    assert tombstone.classify(ENTRIES[5]) is None


def test_collect_finds_exactly_the_three():
    kinds = sorted(g[0] for g in tombstone.collect(ENTRIES))
    assert kinds == ["inconclusive", "kill", "retraction"]


def _linkage_ok(entries, tmp_path):
    p = tmp_path / "led.jsonl"
    p.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")
    levels = []
    tombstone.generic_linkage(str(p), "led", lambda lvl, *a: levels.append(lvl))
    return all(l == OK for l in levels)


def test_chain_intact_passes(tmp_path):
    assert _linkage_ok(ENTRIES, tmp_path) is True


def test_deleted_failure_breaks_the_chain(tmp_path):
    # Drop the retraction (s3): s4's prev_seal (s3) no longer matches s2 -> linkage FAIL.
    tampered = [e for e in ENTRIES if e["seal"] != "s3"]
    assert _linkage_ok(tampered, tmp_path) is False
