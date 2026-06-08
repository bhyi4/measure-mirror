"""측정거울 pytest 통합 — 평가를 테스트로 만들어 CI에서 자동 차단.

코어(mm.py)는 의존성 0을 유지하고, 이 헬퍼는 pytest 없이도 동작한다
(FAIL 시 AssertionError를 던지므로 pytest가 자연히 실패로 처리).

사용:
    from measure_mirror import mm
    from measure_mirror.pytest_plugin import assert_clean

    def test_my_model_is_real():
        findings = mm.audit("ledger.jsonl", "my_model",
                            reported_metric="acc", reported_acc=0.78, n=1000)
        assert_clean(findings)   # 측정 착시 있으면 → 테스트 FAIL → CI 빨간불
"""
from .mm import Finding


def assert_clean(findings, *, allow_warn: bool = True) -> None:
    """findings에 FAIL(또는 allow_warn=False면 WARN도) 있으면 AssertionError.

    allow_warn=True(기본): 사전등록 없음 같은 WARN은 통과, FAIL만 차단.
    """
    bad = [f for f in findings
           if f.level == "FAIL" or (not allow_warn and f.level == "WARN")]
    if bad:
        lines = "\n".join(f"  {f.level} [{f.probe}] {f.msg}" for f in findings)
        raise AssertionError("🪞 측정거울 감사 실패:\n" + lines)
