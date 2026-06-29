"""P2 — `linkage_check` is the SINGLE SOURCE of the format-agnostic prev_seal→seal
linkage used by the stack verifiers (stack/verify_self.py + the outsider
mirror-stack-verify CLI). These pin the edge behaviour that the two copies had
drifted on (empty / malformed / missing previously crashed verify_self).
"""
import measure_mirror.mm as mm


def _mk(tmp_path, lines):
    p = tmp_path / "l.jsonl"
    p.write_text("\n".join(lines), encoding="utf-8")
    return str(p)


def test_intact_chain(tmp_path):
    p = _mk(tmp_path, ['{"prev_seal":"genesis","seal":"a"}',
                       '{"prev_seal":"a","seal":"b"}'])
    ok, msg, entries = mm.linkage_check(p)
    assert ok is True
    assert "linkage intact" in msg and "head=b" in msg
    assert len(entries) == 2


def test_broken_linkage(tmp_path):
    p = _mk(tmp_path, ['{"prev_seal":"genesis","seal":"a"}',
                       '{"prev_seal":"WRONG","seal":"b"}'])
    ok, msg, entries = mm.linkage_check(p)
    assert ok is False
    assert "linkage broken at entry 1" in msg
    assert entries is not None          # readable → caller can still inspect


def test_first_entry_must_be_genesis(tmp_path):
    p = _mk(tmp_path, ['{"prev_seal":"x","seal":"a"}'])
    ok, msg, _ = mm.linkage_check(p)
    assert ok is False
    assert "is not 'genesis'" in msg


def test_empty_ledger_is_not_confirmed(tmp_path):
    """Previously crashed generic_linkage with None[:16] TypeError."""
    p = _mk(tmp_path, [])
    ok, msg, entries = mm.linkage_check(p)
    assert ok is False
    assert msg == "ledger is empty"
    assert entries == []


def test_malformed_json_is_handled(tmp_path):
    """Previously crashed generic_linkage with an uncaught JSONDecodeError."""
    p = _mk(tmp_path, ['{"prev_seal":"genesis","seal":"a"}', '{not json}'])
    ok, msg, entries = mm.linkage_check(p)
    assert ok is False
    assert "malformed JSON" in msg
    assert entries is None


def test_missing_file_is_handled():
    ok, msg, entries = mm.linkage_check("/no/such/ledger.jsonl")
    assert ok is False
    assert "unreadable" in msg
    assert entries is None
