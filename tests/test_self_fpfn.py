"""Regression guard for the self-FP/FN eval (eval/self_fpfn/).

Locks in two things:
  1. the core deterministic suite mis-decides ZERO in-scope cases, and
  2. the known-limitation traps behave exactly as documented.

When a disclosed limitation is later FIXED (e.g. near-dup leakage, n-blind
baseline), the corresponding trap assertion here is expected to change — that
is the signal the fix worked, and this test is where you record it.
"""
import os
import sys

import pytest

EVAL_DIR = os.path.join(os.path.dirname(__file__), "..", "eval", "self_fpfn")
sys.path.insert(0, os.path.abspath(EVAL_DIR))
import run_eval  # noqa: E402


@pytest.fixture(scope="module")
def result():
    return run_eval.evaluate()


def test_core_no_false_decisions(result):
    """In-scope deterministic probes mis-decide nothing (bounded by small n)."""
    assert result["core"]["FN"] == 0, result["unexpected_core"]
    assert result["core"]["FP"] == 0, result["unexpected_core"]
    assert result["unexpected_core"] == []


def test_traps_match_documented_behaviour(result):
    """The disclosed limitations behave as RESULTS.md records (current tool)."""
    by_id = {t["id"]: t["outcome"] for t in result["trap_detail"]}
    # near-duplicate leakage slips past exact-hash matching -> FN
    assert by_id["lk03"] == "FN"
    assert by_id["lk04"] == "FN"
    # n-blind fixed baseline margin -> FN on a statistically-tied claim
    assert by_id["bf04"] == "FN"
    # exact-match scope is case-sensitive -> FP on a covered-but-recased scope
    assert by_id["sc_trap01"] == "FP"


def test_v2_grim_shortcut_is_complete():
    """v2 kill-condition guard: the GRIM 2-candidate shortcut must agree with a
    full brute-force k-sweep on every case (any disagreement = a real bug)."""
    sys.path.insert(0, os.path.abspath(os.path.join(EVAL_DIR, "v2")))
    import analyze_v2
    out = analyze_v2.evaluate()
    grim = out["per_probe"]["grim"]
    assert grim["FN"] == 0 and grim["FP"] == 0, \
        [d for d in out["disagreements"] if d["probe"] == "grim"]
