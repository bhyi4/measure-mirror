"""Tests for measure_mirror.judge — LLM-as-a-Judge runner.

All tests are dependency-free: API calls are replaced by mock judge_fn callables.
We never actually call OpenAI / Anthropic here.
"""
from __future__ import annotations

import json

import pytest

# If openai / anthropic are not installed, the import-error tests still run
# because they test the adapter factories under ImportError conditions.
from measure_mirror import judge as jm
from measure_mirror import mm


# ─── parser unit tests ────────────────────────────────────────

def test_parse_pairwise_a():
    assert jm._parse_pairwise("A") == 0
    assert jm._parse_pairwise("  a ") == 0
    assert jm._parse_pairwise("Answer: A is better.") == 0


def test_parse_pairwise_b():
    assert jm._parse_pairwise("B") == 1
    assert jm._parse_pairwise("b.") == 1


def test_parse_pairwise_unparseable():
    assert jm._parse_pairwise("Neither") == -1


def test_parse_rating():
    assert jm._parse_rating("8") == 8
    assert jm._parse_rating("I rate it 7 out of 10.") == 7
    assert jm._parse_rating("no number here") == -1


# ─── adapter import-error tests ──────────────────────────────

def test_openai_judge_import_error(monkeypatch):
    """openai_judge() raises ImportError when openai package is absent."""
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "openai":
            raise ImportError("No module named 'openai'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ImportError, match="openai"):
        fn = jm.openai_judge()
        fn({"prompt": "x", "a": "a", "b": "b"})


def test_anthropic_judge_import_error(monkeypatch):
    """anthropic_judge() raises ImportError when anthropic package is absent."""
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "anthropic":
            raise ImportError("No module named 'anthropic'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ImportError, match="anthropic"):
        fn = jm.anthropic_judge()
        fn({"prompt": "x", "a": "a", "b": "b"})


# ─── judge_run core tests ─────────────────────────────────────

def _make_deterministic_judge(scores: list[int]):
    """Returns a judge_fn that pops from scores in order."""
    it = iter(scores)

    def _judge(item):
        return next(it)

    return _judge


def test_judge_run_basic(tmp_path):
    """judge_run returns expected dict keys and seals ledger entry."""
    ledger = str(tmp_path / "l.jsonl")
    items = [{"prompt": "p", "a": "x", "b": "y"}] * 4
    # runs=2: 4 items × 2 runs = 8 calls; 4 A-wins run1, 4 A-wins run2 (no flips)
    judge_fn = _make_deterministic_judge([0, 0, 0, 0, 0, 0, 0, 0])
    result = jm.judge_run(ledger, "eval1", judge_fn=judge_fn,
                          items=items, runs=2, pairwise=True)

    assert "findings" in result
    assert "scores" in result
    assert "score_pairs" in result
    assert result["n_items"] == 4
    assert result["runs"] == 2
    assert result["ledger_entry"] is not None


def test_judge_run_fires_all_probes(tmp_path):
    """judge_run with runs=2, pairwise=True fires probes ⑭⑮⑯⑰."""
    ledger = str(tmp_path / "l.jsonl")
    items = [{"prompt": f"p{i}", "a": "x", "b": "y"} for i in range(10)]
    # Alternating 0/1 → no flip (same across runs), balanced bias, varied scores
    scores_run1 = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
    scores_run2 = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
    judge_fn = _make_deterministic_judge(scores_run1 + scores_run2)
    result = jm.judge_run(ledger, "eval2", judge_fn=judge_fn,
                          items=items, runs=2, pairwise=True)
    probes = {f.probe for f in result["findings"]}
    assert "⑭ judge-consistency" in probes
    assert "⑮ judge-bias" in probes
    assert "⑯ inter-rater" in probes
    assert "⑰ judge-score-sanity" in probes


def test_judge_run_no_bias_probe_without_pairwise(tmp_path):
    """Rating mode (pairwise=False) skips ⑮ bias check."""
    ledger = str(tmp_path / "l.jsonl")
    items = [{"prompt": f"p{i}", "response": "r"} for i in range(5)]
    scores = [5, 7, 6, 8, 7, 5, 7, 6, 8, 7]  # 5 items × 2 runs
    judge_fn = _make_deterministic_judge(scores)
    result = jm.judge_run(ledger, "eval3", judge_fn=judge_fn,
                          items=items, runs=2, pairwise=False)
    probes = {f.probe for f in result["findings"]}
    assert "⑮ judge-bias" not in probes


def test_judge_run_seals_into_ledger(tmp_path):
    """judge_run appends a _type=judge_run chain-linked entry."""
    ledger = str(tmp_path / "l.jsonl")
    items = [{"prompt": "q", "a": "a", "b": "b"}] * 3
    judge_fn = _make_deterministic_judge([0, 1, 0, 0, 1, 0])
    jm.judge_run(ledger, "eval4", judge_fn=judge_fn,
                 items=items, runs=2, pairwise=True)

    with open(ledger, encoding="utf-8") as f:
        entries = [json.loads(line) for line in f if line.strip()]

    jr = [e for e in entries if e.get("_type") == "judge_run"]
    assert len(jr) == 1
    assert jr[0]["claim_id"] == "eval4"
    assert jr[0]["n_items"] == 3
    assert "seal" in jr[0]
    assert "prev_seal" in jr[0]


def test_judge_run_empty_items(tmp_path):
    """Empty items list returns WARN finding, no ledger write."""
    ledger = str(tmp_path / "l.jsonl")
    judge_fn = _make_deterministic_judge([])
    result = jm.judge_run(ledger, "eval5", judge_fn=judge_fn,
                          items=[], runs=2, pairwise=True)
    assert result["n_items"] == 0
    assert result["ledger_entry"] is None
    assert any(f.level == "WARN" for f in result["findings"])


# ─── parse-failure handling tests ────────────────────────────

def test_judge_run_filters_unparseable(tmp_path):
    """Items scoring -1 in any run are excluded from probes."""
    ledger = str(tmp_path / "l.jsonl")
    items = [{"prompt": f"p{i}", "a": "x", "b": "y"} for i in range(5)]
    # run1: item2 unparseable; run2: clean → item2 excluded everywhere
    judge_fn = _make_deterministic_judge([0, 1, -1, 0, 1,   0, 1, 0, 0, 1])
    result = jm.judge_run(ledger, "ev_parse", judge_fn=judge_fn,
                          items=items, runs=2, pairwise=True)
    assert result["parse_failures"] == 1
    # bias check saw only 4 valid items: [0, 1, 0, 1] → balanced, no phantom FAIL
    bias = [f for f in result["findings"] if f.probe == "⑮ judge-bias"]
    assert bias and bias[0].level == "OK"
    assert result["ledger_entry"]["parse_failures"] == 1


def test_judge_run_warn_high_parse_failure(tmp_path):
    """Parse failure rate > 10% → judge-parse WARN appended."""
    ledger = str(tmp_path / "l.jsonl")
    items = [{"prompt": f"p{i}", "a": "x", "b": "y"} for i in range(5)]
    # 2/5 = 40% unparseable in run1
    judge_fn = _make_deterministic_judge([-1, -1, 0, 1, 0,   0, 1, 0, 1, 0])
    result = jm.judge_run(ledger, "ev_warn", judge_fn=judge_fn,
                          items=items, runs=2, pairwise=True)
    parse = [f for f in result["findings"] if f.probe == "judge-parse"]
    assert parse and parse[0].level == "WARN"


def test_judge_run_fail_all_unparseable(tmp_path):
    """Nothing parsed → judge-parse FAIL, no probe results."""
    ledger = str(tmp_path / "l.jsonl")
    items = [{"prompt": "p", "a": "x", "b": "y"}] * 3
    judge_fn = _make_deterministic_judge([-1] * 6)
    result = jm.judge_run(ledger, "ev_fail", judge_fn=judge_fn,
                          items=items, runs=2, pairwise=True)
    assert result["parse_failures"] == 3
    parse = [f for f in result["findings"] if f.probe == "judge-parse"]
    assert parse and parse[0].level == "FAIL"
    assert not any(f.probe.startswith("⑮") for f in result["findings"])


# ─── swap_positions (⑱) tests ────────────────────────────────

def test_judge_run_swap_fires_swap_check(tmp_path):
    """swap_positions=True adds an extra pass and fires ⑱."""
    ledger = str(tmp_path / "l.jsonl")
    items = [{"prompt": f"p{i}", "a": "x", "b": "y"} for i in range(4)]
    # 2 runs × 4 + 1 swap pass × 4 = 12 calls
    # forward [0,1,0,1]; swap pass [1,0,1,0] → all inverted → content-driven OK
    judge_fn = _make_deterministic_judge(
        [0, 1, 0, 1,   0, 1, 0, 1,   1, 0, 1, 0])
    result = jm.judge_run(ledger, "ev_swap", judge_fn=judge_fn,
                          items=items, runs=2, pairwise=True,
                          swap_positions=True)
    swap = [f for f in result["findings"] if f.probe == "⑱ judge-swap"]
    assert swap and swap[0].level == "OK"
    assert result["swap_scores"] == [1, 0, 1, 0]
    assert result["ledger_entry"]["swap_lock_rate"] == 0.0


def test_judge_run_swap_catches_position_lock(tmp_path):
    """Position-locked judge → ⑱ FAIL even when run-level bias is mixed."""
    ledger = str(tmp_path / "l.jsonl")
    items = [{"prompt": f"p{i}", "a": "x", "b": "y"} for i in range(4)]
    # forward [0,0,1,1]; swap pass identical [0,0,1,1] → 100% locked
    judge_fn = _make_deterministic_judge(
        [0, 0, 1, 1,   0, 0, 1, 1,   0, 0, 1, 1])
    result = jm.judge_run(ledger, "ev_lock", judge_fn=judge_fn,
                          items=items, runs=2, pairwise=True,
                          swap_positions=True)
    swap = [f for f in result["findings"] if f.probe == "⑱ judge-swap"]
    assert swap and swap[0].level == "FAIL"
    assert result["ledger_entry"]["swap_lock_rate"] == 1.0
