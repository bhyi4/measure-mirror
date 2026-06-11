"""measure-mirror 자체 테스트 — CI에서 회귀 차단 (도그푸딩)."""
import json
import pytest
from measure_mirror import mm
from measure_mirror.pytest_plugin import assert_clean


# ─── 기존 테스트 (회귀 방지) ───────────────────────────────────

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


# ─── 버그 수정 검증 ────────────────────────────────────────────

def test_first_registration_wins(tmp_path):
    """재등록 시도 시 첫 번째 등록만 유효."""
    ledger = str(tmp_path / "l.jsonl")
    mm.preregister(ledger, "exp1", metric="acc", min_n=200, baseline=0.5, pass_threshold=0.6)
    mm.preregister(ledger, "exp1", metric="f1",  min_n=10,  baseline=0.3, pass_threshold=0.5)
    pre = mm._load_prereg(ledger, "exp1")
    assert pre["metric"] == "acc"
    assert pre["min_n"] == 200


def test_seal_tamper_detected(tmp_path):
    """원장 파일 수정 시 봉인 위변조 탐지."""
    ledger = str(tmp_path / "l.jsonl")
    mm.preregister(ledger, "exp2", metric="acc", min_n=200, baseline=0.5, pass_threshold=0.6)
    # 원장 파일 직접 조작
    with open(ledger) as f:
        entry = json.loads(f.read())
    entry["baseline"] = 0.1  # 위변조
    with open(ledger, "w") as f:
        f.write(json.dumps(entry))
    findings = mm.audit(ledger, "exp2", reported_metric="acc", reported_acc=0.72, n=500)
    assert any("위변조" in x.probe for x in findings)
    assert any(x.level == "FAIL" for x in findings)


def test_pass_threshold_fail(tmp_path):
    """acc < pass_threshold 이면 FAIL."""
    ledger = str(tmp_path / "l.jsonl")
    mm.preregister(ledger, "exp3", metric="acc", min_n=10, baseline=0.5, pass_threshold=0.80)
    findings = mm.audit(ledger, "exp3", reported_metric="acc", reported_acc=0.75, n=500)
    assert any("pass_threshold" in x.probe for x in findings)
    assert any(x.level == "FAIL" for x in findings)


def test_pass_threshold_pass(tmp_path):
    """acc >= pass_threshold 이면 pass_threshold FAIL 없음."""
    ledger = str(tmp_path / "l.jsonl")
    mm.preregister(ledger, "exp4", metric="acc", min_n=10, baseline=0.5, pass_threshold=0.70)
    findings = mm.audit(ledger, "exp4", reported_metric="acc", reported_acc=0.75, n=500)
    assert not any("pass_threshold" in x.probe and x.level == "FAIL" for x in findings)


# ─── 신규 probe 검증 ───────────────────────────────────────────

def test_gaming_check_fail():
    """③ reward에 평가 지표 직접 포함 → FAIL."""
    assert mm.gaming_check("acc", ["acc_loss", "entropy"]).level == "FAIL"


def test_gaming_check_ok():
    assert mm.gaming_check("acc", ["cross_entropy", "kl_div"]).level == "OK"


def test_multiseed_unstable():
    """⑤ baseline이 시드 범위에 걸치면 FAIL."""
    assert mm.multiseed_check([0.48, 0.72, 0.65], baseline=0.5).level == "FAIL"


def test_multiseed_high_cv():
    """⑤ 분산 크면 WARN."""
    assert mm.multiseed_check([0.60, 0.90, 0.75], baseline=0.5).level == "WARN"


def test_multiseed_stable():
    assert mm.multiseed_check([0.74, 0.75, 0.76], baseline=0.5).level == "OK"


def test_multiseed_single():
    """⑤ 시드 1개면 WARN (재현 불가)."""
    assert mm.multiseed_check([0.75], baseline=0.5).level == "WARN"


def test_too_good_flagged():
    """⑦ Δ ≥ 0.30 → WARN."""
    f = mm.too_good_check("test", 0.95, 0.5, suspicious_margin=0.30)
    assert f.level == "WARN"


def test_too_good_ok():
    f = mm.too_good_check("test", 0.60, 0.5, suspicious_margin=0.30)
    assert f.level == "OK"


# ─── 연속 지표 감사 ────────────────────────────────────────────

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
    """std 제공, z < 1.0 → WARN."""
    findings = mm.continuous_audit("/dev/null", "reg3",
                                   reported_metric="pearson_r", reported_value=0.55,
                                   baseline_value=0.50, n=100, std=0.20, higher_better=True)
    assert any("효과크기" in x.probe and x.level == "WARN" for x in findings)


def test_continuous_audit_ledger(tmp_path):
    """사전등록 + 지표변경 → FAIL."""
    ledger = str(tmp_path / "c.jsonl")
    mm.preregister(ledger, "reg4", metric="pearson_r", min_n=100, baseline=0.5, pass_threshold=0.6)
    findings = mm.continuous_audit(ledger, "reg4",
                                   reported_metric="spearman_r",  # 지표 갈아타기
                                   reported_value=0.70, baseline_value=0.50, n=200)
    assert any("지표변경" in x.probe for x in findings)
    assert any(x.level == "FAIL" for x in findings)


# ─── 통합 감사 ────────────────────────────────────────────────

def test_full_audit_basic(tmp_path):
    """full_audit 기본 실행 — 결과 반환."""
    ledger = str(tmp_path / "f.jsonl")
    findings = mm.full_audit(ledger, "fa1",
                             reported_metric="acc", reported_acc=0.72, n=500, baseline=0.5)
    assert isinstance(findings, list)
    assert len(findings) > 0


def test_full_audit_all_probes(tmp_path):
    """full_audit — 선택 probe 전부 활성화."""
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
    assert "② 공정 baseline" in probes
    assert "③ 게이밍 분계선" in probes
    assert "④a 데이터누설" in probes
    assert "⑤ 다시드 재현" in probes
    assert "⑥ scope" in probes
    assert "⑦ 자가적발(이상값)" in probes
