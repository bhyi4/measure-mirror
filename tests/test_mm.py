"""measure-mirror test suite — regression gate (dog-fooded)."""
import json
import hashlib
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


# ─── New probes (③⑤⑦) ─────────────────────────────────────────

def test_gaming_check_fail():
    assert mm.gaming_check("acc", ["acc_loss", "entropy"]).level == "FAIL"


def test_gaming_check_ok():
    assert mm.gaming_check("acc", ["cross_entropy", "kl_div"]).level == "OK"


def test_multiseed_unstable():
    assert mm.multiseed_check([0.48, 0.72, 0.65], baseline=0.5).level == "FAIL"


def test_multiseed_high_cv():
    assert mm.multiseed_check([0.60, 0.90, 0.75], baseline=0.5).level == "WARN"


def test_multiseed_stable():
    assert mm.multiseed_check([0.74, 0.75, 0.76], baseline=0.5).level == "OK"


def test_multiseed_single():
    assert mm.multiseed_check([0.75], baseline=0.5).level == "WARN"


def test_too_good_flagged():
    assert mm.too_good_check("test", 0.95, 0.5, suspicious_margin=0.30).level == "WARN"


def test_too_good_ok():
    assert mm.too_good_check("test", 0.60, 0.5, suspicious_margin=0.30).level == "OK"


# ─── Continuous metric audit ──────────────────────────────────

def test_continuous_audit_ok():
    findings = mm.continuous_audit("/dev/null", "reg1",
                                   reported_metric="mse", reported_value=0.10,
                                   baseline_value=0.15, n=500, higher_better=False)
    assert all(x.level != "FAIL" for x in findings)


def test_continuous_audit_direction_fail():
    findings = mm.continuous_audit("/dev/null", "reg2",
                                   reported_metric="mse", reported_value=0.20,
                                   baseline_value=0.15, n=500, higher_better=False)
    assert any(x.level == "FAIL" for x in findings)


def test_continuous_audit_effect_size_warn():
    findings = mm.continuous_audit("/dev/null", "reg3",
                                   reported_metric="pearson_r", reported_value=0.55,
                                   baseline_value=0.50, n=100, std=0.20, higher_better=True)
    assert any("effect-size" in x.probe and x.level == "WARN" for x in findings)


def test_continuous_audit_ledger(tmp_path):
    """Pre-registration + metric swap → FAIL."""
    ledger = str(tmp_path / "c.jsonl")
    mm.preregister(ledger, "reg4", metric="pearson_r", min_n=100, baseline=0.5, pass_threshold=0.6)
    findings = mm.continuous_audit(ledger, "reg4",
                                   reported_metric="spearman_r",
                                   reported_value=0.70, baseline_value=0.50, n=200)
    assert any("metric-swap" in x.probe for x in findings)
    assert any(x.level == "FAIL" for x in findings)


# ─── ① Chain hash tests ───────────────────────────────────────

def test_chain_intact_single(tmp_path):
    """Single registration → chain OK."""
    ledger = str(tmp_path / "l.jsonl")
    mm.preregister(ledger, "exp1", metric="acc", min_n=200, baseline=0.5, pass_threshold=0.6)
    findings = mm.verify_chain(ledger)
    assert all(f.level == "OK" for f in findings), findings


def test_chain_intact_two_entries(tmp_path):
    """Two registrations → chain links correctly."""
    ledger = str(tmp_path / "l.jsonl")
    e1 = mm.preregister(ledger, "exp1", metric="acc", min_n=200, baseline=0.5, pass_threshold=0.6)
    e2 = mm.preregister(ledger, "exp2", metric="f1",  min_n=100, baseline=0.5, pass_threshold=0.7)
    # second entry must link to first
    assert e2["prev_seal"] == e1["seal"]
    findings = mm.verify_chain(ledger)
    assert all(f.level == "OK" for f in findings), findings


def test_chain_tamper_content(tmp_path):
    """Modifying entry content → seal mismatch → FAIL."""
    ledger = str(tmp_path / "l.jsonl")
    mm.preregister(ledger, "exp1", metric="acc", min_n=200, baseline=0.5, pass_threshold=0.6)
    with open(ledger) as f:
        entry = json.loads(f.read())
    entry["metric"] = "f1"   # tamper without updating seal
    with open(ledger, "w") as f:
        f.write(json.dumps(entry) + "\n")
    findings = mm.verify_chain(ledger)
    assert any(f.level == "FAIL" and "chain-integrity" in f.probe for f in findings)


def test_chain_break_deleted_middle_entry(tmp_path):
    """Deleting a middle entry → chain break → FAIL."""
    ledger = str(tmp_path / "l.jsonl")
    mm.preregister(ledger, "exp1", metric="acc", min_n=200, baseline=0.5, pass_threshold=0.6)
    mm.preregister(ledger, "exp2", metric="f1",  min_n=100, baseline=0.5, pass_threshold=0.7)
    mm.preregister(ledger, "exp3", metric="r2",  min_n=50,  baseline=0.0, pass_threshold=0.5)
    # Remove middle entry (exp2)
    with open(ledger) as f:
        lines = f.readlines()
    with open(ledger, "w") as f:
        f.write(lines[0])   # exp1
        f.write(lines[2])   # exp3 — its prev_seal points to exp2, not exp1
    findings = mm.verify_chain(ledger)
    assert any(f.level == "FAIL" and "chain-integrity" in f.probe for f in findings)


def test_chain_break_first_entry_deleted(tmp_path):
    """Deleting the first entry → chain break at entry 1 (prev≠genesis)."""
    ledger = str(tmp_path / "l.jsonl")
    mm.preregister(ledger, "exp1", metric="acc", min_n=200, baseline=0.5, pass_threshold=0.6)
    mm.preregister(ledger, "exp2", metric="f1",  min_n=100, baseline=0.5, pass_threshold=0.7)
    # Keep only exp2 (exp1 deleted)
    with open(ledger) as f:
        lines = f.readlines()
    with open(ledger, "w") as f:
        f.write(lines[1])   # exp2 — prev_seal points to exp1, not genesis
    findings = mm.verify_chain(ledger)
    assert any(f.level == "FAIL" and "chain-integrity" in f.probe for f in findings)


def test_chain_legacy_entry_no_prev_seal(tmp_path):
    """Legacy entry without prev_seal: seal check passes, no chain check (graceful)."""
    ledger = str(tmp_path / "l.jsonl")
    legacy = {
        "ts": "2025-01-01T00:00:00",
        "claim_id": "legacy",
        "metric": "acc",
        "min_n": 100,
        "baseline": 0.5,
        "pass_threshold": 0.6,
    }
    legacy["seal"] = hashlib.sha256(
        json.dumps(legacy, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:16]
    with open(ledger, "w") as f:
        f.write(json.dumps(legacy) + "\n")
    findings = mm.verify_chain(ledger)
    assert all(f.level == "OK" for f in findings), findings


def test_chain_empty_ledger_no_file(tmp_path):
    """Non-existent ledger → chain OK (empty)."""
    findings = mm.verify_chain(str(tmp_path / "nonexistent.jsonl"))
    assert all(f.level == "OK" for f in findings)


# ─── ⑧ Power probe tests ─────────────────────────────────────

def test_power_insufficient_small_n():
    """n=50, Δ=0.05 above baseline=0.5 → WARN (need ~300+)."""
    f = mm.power_check(50, 0.5, min_detectable_effect=0.05)
    assert f.level == "WARN"
    assert f.probe == "⑧ power"
    assert "n≥" in f.msg


def test_power_sufficient_large_n():
    """n=500, Δ=0.10 → OK."""
    f = mm.power_check(500, 0.5, min_detectable_effect=0.10)
    assert f.level == "OK"


def test_power_large_effect_small_n():
    """n=50 is enough for Δ=0.20 (large effect detectable with less data)."""
    f = mm.power_check(50, 0.5, min_detectable_effect=0.20)
    assert f.level == "OK"


def test_power_very_small_n_always_warn():
    """n=10 never sufficient for small effects."""
    f = mm.power_check(10, 0.5, min_detectable_effect=0.05)
    assert f.level == "WARN"


def test_power_required_n_in_message():
    """Message includes required n."""
    f = mm.power_check(10, 0.5, min_detectable_effect=0.05)
    assert "n≥" in f.msg


# ─── ⑨ Multiple comparisons tests ────────────────────────────

def test_multicomp_single_experiment(tmp_path):
    """One claim in ledger → OK."""
    ledger = str(tmp_path / "l.jsonl")
    mm.preregister(ledger, "exp1", metric="acc", min_n=200, baseline=0.5, pass_threshold=0.6)
    f = mm.multiple_comparisons_check(ledger)
    assert f.level == "OK"


def test_multicomp_three_experiments(tmp_path):
    """Three distinct claims → WARN with Bonferroni α=0.05/3."""
    ledger = str(tmp_path / "l.jsonl")
    mm.preregister(ledger, "exp1", metric="acc", min_n=200, baseline=0.5, pass_threshold=0.6)
    mm.preregister(ledger, "exp2", metric="f1",  min_n=100, baseline=0.5, pass_threshold=0.7)
    mm.preregister(ledger, "exp3", metric="r2",  min_n=50,  baseline=0.0, pass_threshold=0.5)
    f = mm.multiple_comparisons_check(ledger)
    assert f.level == "WARN"
    assert f.probe == "⑨ multiple-comparisons"
    assert "k=3" in f.msg
    assert "0.0167" in f.msg  # 0.05/3 ≈ 0.0167


def test_multicomp_no_ledger(tmp_path):
    """Non-existent ledger → OK."""
    f = mm.multiple_comparisons_check(str(tmp_path / "none.jsonl"))
    assert f.level == "OK"


def test_multicomp_rereg_same_claim_counts_once(tmp_path):
    """Re-registering same claim_id counts as 1 unique — still OK."""
    ledger = str(tmp_path / "l.jsonl")
    mm.preregister(ledger, "exp1", metric="acc", min_n=200, baseline=0.5, pass_threshold=0.6)
    mm.preregister(ledger, "exp1", metric="f1",  min_n=10,  baseline=0.5, pass_threshold=0.5)
    f = mm.multiple_comparisons_check(ledger)
    assert f.level == "OK"  # still k=1 unique claim


# ─── full_audit new probes integration ───────────────────────

def test_full_audit_basic(tmp_path):
    ledger = str(tmp_path / "f.jsonl")
    findings = mm.full_audit(ledger, "fa1",
                             reported_metric="acc", reported_acc=0.72, n=500, baseline=0.5)
    assert isinstance(findings, list) and len(findings) > 0


def test_full_audit_all_probes(tmp_path):
    """All optional probes activated at once."""
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


def test_full_audit_power_probe(tmp_path):
    """min_detectable_effect activates ⑧ power."""
    ledger = str(tmp_path / "f3.jsonl")
    mm.preregister(ledger, "fa3", metric="acc", min_n=10, baseline=0.5, pass_threshold=0.6)
    findings = mm.full_audit(ledger, "fa3",
                             reported_metric="acc", reported_acc=0.72, n=20, baseline=0.5,
                             min_detectable_effect=0.05)
    assert any(f.probe == "⑧ power" for f in findings)


def test_full_audit_multiplicity_probe(tmp_path):
    """check_multiplicity=True activates ⑨ with k=2."""
    ledger = str(tmp_path / "f4.jsonl")
    mm.preregister(ledger, "m1", metric="acc", min_n=10, baseline=0.5, pass_threshold=0.6)
    mm.preregister(ledger, "m2", metric="acc", min_n=10, baseline=0.5, pass_threshold=0.6)
    findings = mm.full_audit(ledger, "m1",
                             reported_metric="acc", reported_acc=0.72, n=500, baseline=0.5,
                             check_multiplicity=True)
    probes = {f.probe for f in findings}
    assert "⑨ multiple-comparisons" in probes


# ─── ⑩ GRIM tests ────────────────────────────────────────────

def test_grim_ok_exact():
    """acc=0.70, n=10 → k=7, round(7/10,2)=0.70 → OK."""
    f = mm.grim_check(0.70, 10)
    assert f.level == "OK"
    assert f.probe == "⑩ GRIM"


def test_grim_ok_large_n():
    """acc=0.72, n=500 → k=360, round(360/500,2)=0.72 → OK."""
    f = mm.grim_check(0.72, 500)
    assert f.level == "OK"


def test_grim_fail_impossible():
    """acc=0.33, n=10 → round(3/10,2)=0.30, round(4/10,2)=0.40 → FAIL."""
    f = mm.grim_check(0.33, 10)
    assert f.level == "FAIL"
    assert f.probe == "⑩ GRIM"
    assert "Fabricated" in f.msg or "arithmetically impossible" in f.msg


def test_grim_fail_three_decimals():
    """acc=0.556, n=9 → round(5/9,3)=0.556 → OK (real catch from dog-food)."""
    f = mm.grim_check(0.556, 9)
    # 5/9 ≈ 0.5556 rounds to 0.556 at 3 dp — should be OK
    assert f.level == "OK"


def test_grim_invalid_n():
    """n=0 → WARN."""
    f = mm.grim_check(0.70, 0)
    assert f.level == "WARN"


def test_grim_explicit_decimals():
    """n_decimals override respected: force 1 dp check."""
    # 0.3, n=10 → k=3, round(3/10,1)=0.3 → OK
    f = mm.grim_check(0.3, 10, n_decimals=1)
    assert f.level == "OK"


def test_grim_in_audit_fail_appended(tmp_path):
    """GRIM FAIL is appended to audit findings (probe name in result set)."""
    ledger = str(tmp_path / "l.jsonl")
    # acc=0.33, n=10 is GRIM-impossible (no k gives round(k/10,2)=0.33)
    findings = mm.audit(ledger, "grim_test",
                        reported_metric="acc", reported_acc=0.33, n=10)
    assert any(f.probe == "⑩ GRIM" and f.level == "FAIL" for f in findings)


def test_grim_ok_not_appended_to_audit(tmp_path):
    """GRIM OK is silently dropped from audit output to keep output clean."""
    ledger = str(tmp_path / "l.jsonl")
    # acc=0.70, n=10 → GRIM OK → should not appear in findings
    findings = mm.audit(ledger, "clean_test",
                        reported_metric="acc", reported_acc=0.70, n=10)
    assert not any(f.probe == "⑩ GRIM" for f in findings)
