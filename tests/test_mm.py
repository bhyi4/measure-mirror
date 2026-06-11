"""measure-mirror test suite — regression gate (dog-fooded)."""
import json
import pytest
from measure_mirror import mm
from measure_mirror.pytest_plugin import assert_clean


# ─── Core probes ──────────────────────────────────────────────

def test_small_sample_caught():
    f = mm.audit("/dev/null", "x", reported_metric="acc", reported_acc=0.556, n=9)
    assert any(x.level == "FAIL" for x in f)


def test_honest_passes():
    f = mm.audit("/dev/null", "x", reported_metric="acc", reported_acc=0.78, n=1000)
    assert all(x.level != "FAIL" for x in f)
    assert_clean(f)


def test_anti_signal():
    f = mm.audit("/dev/null", "x", reported_metric="acc", reported_acc=0.385, n=1050)
    assert any("anti-signal" in x.probe for x in f)


def test_baseline_inversion():
    assert mm.baseline_fairness("x", 0.86, 0.92).level == "FAIL"


def test_baseline_tie():
    assert mm.baseline_fairness("x", 0.996, 0.998, higher_better=False).level == "FAIL"


def test_scope_overgeneralization():
    assert mm.scope_check(["reasoning"], ["musr_1task"]).level == "FAIL"


def test_scope_ok():
    assert mm.scope_check(["t"], ["t", "held_out"]).level == "OK"


def test_leakage():
    assert mm.leakage_check([1, 2, 3], [3, 4, 5]).level == "FAIL"


def test_wilson_extreme():
    assert mm.wilson_ci(0, 0) == (0.0, 1.0)


def test_db_baseline_lookup():
    assert mm.lookup_baseline("musr", db_dir="db") == 0.5
    assert mm.lookup_baseline("nonexistent", db_dir="db") is None


# ─── Bug-fix regression tests ─────────────────────────────────

def test_first_registration_wins(tmp_path):
    """Second registration for same claim_id must be ignored."""
    ledger = str(tmp_path / "l.jsonl")
    mm.preregister(ledger, "exp1", metric="acc", min_n=200, baseline=0.5, pass_threshold=0.6)
    mm.preregister(ledger, "exp1", metric="f1",  min_n=10,  baseline=0.3, pass_threshold=0.5)
    pre = mm._load_prereg(ledger, "exp1")
    assert pre["metric"] == "acc"
    assert pre["min_n"] == 200


def test_seal_tamper_detected(tmp_path):
    """Direct ledger file modification must trigger seal-tamper FAIL."""
    ledger = str(tmp_path / "l.jsonl")
    mm.preregister(ledger, "exp2", metric="acc", min_n=200, baseline=0.5, pass_threshold=0.6)
    with open(ledger) as f:
        entry = json.loads(f.read())
    entry["baseline"] = 0.1  # tamper
    with open(ledger, "w") as f:
        f.write(json.dumps(entry))
    findings = mm.audit(ledger, "exp2", reported_metric="acc", reported_acc=0.72, n=500)
    assert any("seal-tamper" in x.probe for x in findings)
    assert any(x.level == "FAIL" for x in findings)


def test_pass_threshold_fail(tmp_path):
    """acc < pass_threshold → FAIL."""
    ledger = str(tmp_path / "l.jsonl")
    mm.preregister(ledger, "exp3", metric="acc", min_n=10, baseline=0.5, pass_threshold=0.80)
    findings = mm.audit(ledger, "exp3", reported_metric="acc", reported_acc=0.75, n=500)
    assert any("pass-threshold" in x.probe for x in findings)
    assert any(x.level == "FAIL" for x in findings)


def test_pass_threshold_pass(tmp_path):
    """acc >= pass_threshold → no pass-threshold FAIL."""
    ledger = str(tmp_path / "l.jsonl")
    mm.preregister(ledger, "exp4", metric="acc", min_n=10, baseline=0.5, pass_threshold=0.70)
    findings = mm.audit(ledger, "exp4", reported_metric="acc", reported_acc=0.75, n=500)
    assert not any("pass-threshold" in x.probe and x.level == "FAIL" for x in findings)


# ─── New probes ───────────────────────────────────────────────

def test_gaming_check_fail():
    """③ Eval metric directly in reward → FAIL."""
    assert mm.gaming_check("acc", ["acc_loss", "entropy"]).level == "FAIL"


def test_gaming_check_ok():
    assert mm.gaming_check("acc", ["cross_entropy", "kl_div"]).level == "OK"


def test_multiseed_unstable():
    """⑤ Baseline within seed range → FAIL."""
    assert mm.multiseed_check([0.48, 0.72, 0.65], baseline=0.5).level == "FAIL"


def test_multiseed_high_cv():
    """⑤ High variance → WARN."""
    assert mm.multiseed_check([0.60, 0.90, 0.75], baseline=0.5).level == "WARN"


def test_multiseed_stable():
    assert mm.multiseed_check([0.74, 0.75, 0.76], baseline=0.5).level == "OK"


def test_multiseed_single():
    """⑤ Single seed → WARN (cannot verify reproducibility)."""
    assert mm.multiseed_check([0.75], baseline=0.5).level == "WARN"


def test_too_good_flagged():
    """⑦ Δ ≥ 0.30 → WARN."""
    f = mm.too_good_check("test", 0.95, 0.5, suspicious_margin=0.30)
    assert f.level == "WARN"


def test_too_good_ok():
    f = mm.too_good_check("test", 0.60, 0.5, suspicious_margin=0.30)
    assert f.level == "OK"


# ─── Continuous metric audit ──────────────────────────────────

def test_continuous_audit_ok():
    """MSE: lower is better, 0.10 < baseline 0.15 → OK."""
    findings = mm.continuous_audit("/dev/null", "reg1",
                                   reported_metric="mse", reported_value=0.10,
                                   baseline_value=0.15, n=500, higher_better=False)
    assert all(x.level != "FAIL" for x in findings)


def test_continuous_audit_direction_fail():
    """MSE: lower is better, 0.20 > baseline 0.15 → FAIL."""
    findings = mm.continuous_audit("/dev/null", "reg2",
                                   reported_metric="mse", reported_value=0.20,
                                   baseline_value=0.15, n=500, higher_better=False)
    assert any(x.level == "FAIL" for x in findings)


def test_continuous_audit_effect_size_warn():
    """std provided, z < 1.0 → WARN."""
    findings = mm.continuous_audit("/dev/null", "reg3",
                                   reported_metric="pearson_r", reported_value=0.55,
                                   baseline_value=0.50, n=100, std=0.20, higher_better=True)
    assert any("effect-size" in x.probe and x.level == "WARN" for x in findings)


def test_continuous_audit_ledger(tmp_path):
    """Pre-registration + metric swap → FAIL."""
    ledger = str(tmp_path / "c.jsonl")
    mm.preregister(ledger, "reg4", metric="pearson_r", min_n=100, baseline=0.5, pass_threshold=0.6)
    findings = mm.continuous_audit(ledger, "reg4",
                                   reported_metric="spearman_r",  # metric swap
                                   reported_value=0.70, baseline_value=0.50, n=200)
    assert any("metric-swap" in x.probe for x in findings)
    assert any(x.level == "FAIL" for x in findings)


# ─── Full audit ───────────────────────────────────────────────

def test_full_audit_basic(tmp_path):
    """full_audit basic run — returns findings list."""
    ledger = str(tmp_path / "f.jsonl")
    findings = mm.full_audit(ledger, "fa1",
                             reported_metric="acc", reported_acc=0.72, n=500, baseline=0.5)
    assert isinstance(findings, list)
    assert len(findings) > 0


def test_full_audit_all_probes(tmp_path):
    """full_audit — all optional probes activated."""
    ledger = str(tmp_path / "f2.jsonl")
    mm.preregister(ledger, "fa2", metric="acc", min_n=50, baseline=0.5, pass_threshold=0.65)
    findings = mm.full_audit(
        ledger, "fa2",
        reported_metric="acc", reported_acc=0.72, n=200, baseline=0.5,
        competing_name="gru_baseline", competing_acc=0.68,
        reward_terms=["cross_entropy"],
        train_items=[1, 2, 3], test_items=[4, 5, 6],
        seed_results=[0.70, 0.72, 0.74],
        claimed_scope=["task_a"], tested_scope=["task_a"],
    )
    probes = {f.probe for f in findings}
    assert "② fair-baseline" in probes
    assert "③ gaming" in probes
    assert "④a data-leakage" in probes
    assert "⑤ multi-seed" in probes
    assert "⑥ scope" in probes
    assert "⑦ too-good" in probes
