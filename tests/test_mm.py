"""measure-mirror 자체 테스트 — CI에서 회귀 차단 (도그푸딩)."""
from measure_mirror import mm
from measure_mirror.pytest_plugin import assert_clean


def test_small_sample_caught():
    # n=9 소표본 0.556 → chance(0.5) 구별 불가 → FAIL
    f = mm.audit("/dev/null", "x", reported_metric="acc", reported_acc=0.556, n=9)
    assert any(x.level == "FAIL" for x in f)


def test_honest_passes():
    # 대표본·baseline 초과 → FAIL 없음, assert_clean 통과(WARN 허용)
    f = mm.audit("/dev/null", "x", reported_metric="acc", reported_acc=0.78, n=1000)
    assert all(x.level != "FAIL" for x in f)
    assert_clean(f)


def test_anti_signal():
    # 0.385 < chance → anti-signal
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


def test_wilson_extreme():  # crash 방어
    assert mm.wilson_ci(0, 0) == (0.0, 1.0)


def test_db_baseline_lookup():
    # db/baselines.json 의 musr=0.5 자동조회
    assert mm.lookup_baseline("musr", db_dir="db") == 0.5
    assert mm.lookup_baseline("nonexistent", db_dir="db") is None
