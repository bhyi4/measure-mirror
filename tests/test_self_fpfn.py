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
    """The disclosed limitations behave as RESULTS.md records.

    After the ③④ patch (n-aware baseline_fairness, fuzzy leakage):
      - lk04 (case-only near-dup)   FIXED  -> caught (TP) by normalization
      - bf04 (n-blind baseline)     FIXED  -> caught (TP) by Wilson-CI at n
    Still open (honest):
      - lk03 (semantic paraphrase)  -> FN, needs embedding matching (out of scope)
      - sc_trap01 (scope exact-match) -> FP, a separate limitation (not ③④)
    """
    by_id = {t["id"]: t["outcome"] for t in result["trap_detail"]}
    assert by_id["lk04"] == "TP"   # fixed: normalized near-dup
    assert by_id["bf04"] == "TP"   # fixed: n-aware distinguishability
    assert by_id["lk03"] == "FN"   # still open: semantic paraphrase
    assert by_id["sc_trap01"] == "FP"  # out of patch scope: scope exact-match


def test_grounding_traps_fail_closed(result):
    """Grounding probes ㉑㉒㉓ are vocab classifiers that fail CLOSED: a clean
    paraphrase outside the declared vocab false-alarms (disclosed limitation,
    mm_grounding_probes_selfcal_v1 seal 033ff84b966ca561). If a fix later adds
    fuzzy/embedding vocab matching, these flip to TN — record it here."""
    by_id = {t["id"]: t["outcome"] for t in result["trap_detail"]}
    assert by_id["ab_trap01"] == "FP"  # anchor_basis: paraphrased dynamics basis
    assert by_id["th_trap01"] == "FP"  # threshold_provenance: paraphrased fixed
    assert by_id["cd_trap01"] == "FP"  # content_delta: paraphrased content term


def test_grounding_core_cases_present(result):
    """The calibration set actually exercises all three grounding probes in the
    core bucket (guards against silently dropping the labeled cases)."""
    core_probes = {r["probe"] for r in result["rows"] if r["bucket"] == "core"}
    assert {"anchor_basis", "threshold_provenance", "content_delta"} <= core_probes


def test_a2_anchor_traps_fail_closed(result):
    """A2 anchor-discipline probes ㉔㉕ are vocab classifiers that fail CLOSED:
    a clean paraphrase outside the declared vocab false-alarms (disclosed
    limitation, mm_a2_anchor_probes_selfcal_v1 seal c4684d9f485cd0f5)."""
    by_id = {t["id"]: t["outcome"] for t in result["trap_detail"]}
    assert by_id["al_trap01"] == "FP"  # anchor_line_source paraphrase
    assert by_id["ac_trap01"] == "FP"  # anchor_cell paraphrase


def test_a2_core_cases_present(result):
    """The calibration set exercises both A2 anchor-discipline probes in core."""
    core_probes = {r["probe"] for r in result["rows"] if r["bucket"] == "core"}
    assert {"anchor_line_source", "anchor_cell"} <= core_probes


def test_v2_grim_shortcut_is_complete():
    """v2 kill-condition guard: the GRIM 2-candidate shortcut must agree with a
    full brute-force k-sweep on every case (any disagreement = a real bug)."""
    sys.path.insert(0, os.path.abspath(os.path.join(EVAL_DIR, "v2")))
    import analyze_v2
    out = analyze_v2.evaluate()
    grim = out["per_probe"]["grim"]
    assert grim["FN"] == 0 and grim["FP"] == 0, \
        [d for d in out["disagreements"] if d["probe"] == "grim"]
