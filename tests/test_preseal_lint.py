"""Tests for ⑫ pre-seal lint — seal QUALITY, not just presence.

These pin the failure classes a real experiment arc lost silent compute to
(semantic-fuel cell arc, 2026-07-20~21):
  • a kill-condition that leaked into the `metric` field from a malformed call
    (the human eye sees a criterion, the parser sees none) — self-catch #2;
  • a bar sitting at/below chance;
  • quantified kills written as free text with no structured threshold;
  • no cheap pre-seal machine-checks declared.
"""
import json

import pytest

from measure_mirror import mm


def _levels(findings):
    return {(f.probe, f.level) for f in findings}


def _msgs(findings):
    return "\n".join(f.msg for f in findings)


# ── ⑫a field-leak (self-catch #2) ────────────────────────────────────────────
def test_kill_condition_leaked_into_metric_is_FAIL():
    pre = {"claim_id": "gate0",
           "metric": "gene1 equilibrium; KILL if delta < 0.03 across all arms",
           "min_n": 24, "baseline": 0.5, "pass_threshold": 0.6}
    fs = mm._preseal_lint(pre)
    assert ("㉗ prereg-lint", "FAIL") in _levels(fs)
    assert "leaked into `metric`" in _msgs(fs)


def test_real_metric_name_is_not_flagged_as_leak():
    # A legitimate metric name with an operator-ish token must NOT false-positive.
    for name in ("acc", "separation_d", "bpb_ko", "delta_vs_baseline", "gene1_eq"):
        pre = {"claim_id": "c", "metric": name, "min_n": 200, "baseline": 0.5,
               "pass_threshold": 0.6,
               "kill_threshold": {"threshold": 0.1, "direction": "below"}}
        msgs = _msgs(mm._preseal_lint(pre))
        assert "leaked into `metric`" not in msgs, name


# ── ⑫b quantified text-only kill ─────────────────────────────────────────────
def test_quantified_text_only_kill_warns():
    pre = {"claim_id": "c", "metric": "acc", "min_n": 200, "baseline": 0.5,
           "pass_threshold": 0.6,
           "kill_condition": "fails if accuracy drops below 0.55"}
    msgs = _msgs(mm._preseal_lint(pre))
    assert "no structured kill_threshold" in msgs


def test_structured_threshold_suppresses_the_quantified_warning():
    pre = {"claim_id": "c", "metric": "acc", "min_n": 200, "baseline": 0.5,
           "pass_threshold": 0.6,
           "kill_condition": "fails below 0.55",
           "kill_threshold": {"threshold": 0.55, "direction": "below"}}
    assert "no structured kill_threshold" not in _msgs(mm._preseal_lint(pre))


# ── ⑫c bar at/below chance ───────────────────────────────────────────────────
def test_pass_bar_at_or_below_chance_is_FAIL():
    pre = {"claim_id": "c", "metric": "acc", "min_n": 200, "baseline": 0.5,
           "pass_threshold": 0.45,
           "kill_threshold": {"threshold": 0.4, "direction": "below"}}
    msgs = _msgs(mm._preseal_lint(pre))
    assert "at or below chance" in msgs


def test_declared_chance_overrides_baseline_for_the_bar_check():
    # A 1/24 chance metric with a healthy-looking baseline=0.5 but pass=0.04.
    pre = {"claim_id": "c", "metric": "rank_acc", "min_n": 200, "baseline": 0.5,
           "pass_threshold": 0.04, "chance": 1 / 24, "metric_range": [0, 1],
           "kill_threshold": {"threshold": 0.02, "direction": "below"}}
    # 0.04 > 1/24 (0.0417)?  1/24 ≈ 0.04167 so 0.04 < chance → FAIL
    assert "at or below chance" in _msgs(mm._preseal_lint(pre))


def test_unbounded_metric_without_chance_skips_bar_check():
    # No usable chance floor → do not false-FAIL a delta/span metric.
    pre = {"claim_id": "c", "metric": "separation_delta", "min_n": 200,
           "baseline": 0.5, "pass_threshold": 0.1, "metric_range": "unbounded",
           "kill_threshold": {"threshold": 0.0, "direction": "below"}}
    assert "at or below chance" not in _msgs(mm._preseal_lint(pre))


# ── ⑫d underpowered ──────────────────────────────────────────────────────────
def test_low_min_n_warns():
    pre = {"claim_id": "c", "metric": "acc", "min_n": 10, "baseline": 0.5,
           "pass_threshold": 0.6,
           "kill_threshold": {"threshold": 0.5, "direction": "below"}}
    assert "below the small-sample floor" in _msgs(mm._preseal_lint(pre))


# ── ⑫e pre-seal machine-checks declaration ───────────────────────────────────
def test_missing_pre_seal_checks_draws_info_nudge():
    pre = {"claim_id": "c", "metric": "acc", "min_n": 200, "baseline": 0.5,
           "pass_threshold": 0.6,
           "kill_threshold": {"threshold": 0.5, "direction": "below"}}
    fs = mm._preseal_lint(pre)
    assert ("㉗ prereg-lint", "INFO") in _levels(fs)
    assert "no pre-seal machine-checks" in _msgs(fs)


def test_declared_pre_seal_checks_report_OK():
    pre = {"claim_id": "c", "metric": "acc", "min_n": 200, "baseline": 0.5,
           "pass_threshold": 0.6,
           "kill_threshold": {"threshold": 0.5, "direction": "below"},
           "pre_seal_checks": ["reachability-smoke", "neutral-control"]}
    fs = mm._preseal_lint(pre)
    assert ("㉗ prereg-lint", "OK") in _levels(fs)
    assert "no pre-seal machine-checks" not in _msgs(fs)


def test_healthy_seal_has_no_warn_or_fail():
    pre = {"claim_id": "good", "metric": "separation_d", "min_n": 240,
           "baseline": 0.5, "pass_threshold": 0.6,
           "kill_threshold": {"metric": "d", "threshold": 0.1, "direction": "below"},
           "pre_seal_checks": ["reachability-smoke", "mass-balance-audit"]}
    assert not [f for f in mm._preseal_lint(pre) if f.level in ("WARN", "FAIL")]


# ── ledger wrapper + preregister round-trip ──────────────────────────────────
def test_preregister_persists_pre_seal_checks_and_lint_reads_them(tmp_path):
    led = str(tmp_path / "l.jsonl")
    e = mm.preregister(led, "c", metric="acc", min_n=200, baseline=0.5,
                       pass_threshold=0.6,
                       kill_threshold={"threshold": 0.55, "direction": "below"},
                       pre_seal_checks=["reachability-smoke"])
    assert e["pre_seal_checks"] == ["reachability-smoke"]
    fs = mm.prereg_lint(led, "c")
    assert not [f for f in fs if f.level in ("WARN", "FAIL")]


def test_prereg_lint_all_claims(tmp_path):
    led = str(tmp_path / "l.jsonl")
    mm.preregister(led, "good", metric="acc", min_n=200, baseline=0.5,
                   pass_threshold=0.6,
                   kill_threshold={"threshold": 0.55, "direction": "below"},
                   pre_seal_checks=["reachability-smoke"])
    mm.preregister(led, "weak", metric="acc", min_n=10, baseline=0.5,
                   pass_threshold=0.6,
                   kill_threshold={"threshold": 0.55, "direction": "below"})
    fs = mm.prereg_lint(led)  # claim_id=None → all
    weak_warns = [f for f in fs if "'weak'" in f.msg and f.level == "WARN"]
    assert weak_warns  # the low-n claim surfaces


def test_prereg_lint_missing_claim(tmp_path):
    led = str(tmp_path / "l.jsonl")
    mm.preregister(led, "c", metric="acc", min_n=200, baseline=0.5,
                   pass_threshold=0.6,
                   kill_threshold={"threshold": 0.55, "direction": "below"})
    fs = mm.prereg_lint(led, "nope")
    assert fs[0].level == "WARN" and "No pre-registration" in fs[0].msg
