"""정직한 연구자의 전형적 측정거울 사용 흐름 (3단계)."""
import os
from measure_mirror import mm

L = "example_ledger.jsonl"
if os.path.exists(L):
    os.remove(L)

# ── 1단계: 실험 시작 *전* — 기준을 박제 (결과 보기 전) ──
mm.preregister(L, "my_classifier",
               metric="acc", min_n=200, baseline=0.5, pass_threshold=0.60)
print("① 기준 봉인 완료 (metric=acc, min_n=200, baseline=0.5, pass=0.60)\n")

# ── 2단계: 평가 *후* — 감사 ──
# (a) 정직한 대표본 결과 → 통과해야
mm.report("정직 케이스: acc=0.72, n=500",
          mm.audit(L, "my_classifier",
                   reported_metric="acc", reported_acc=0.72, n=500))

# (b) "소표본인데 점수 높게 나왔다" 유혹 → 차단해야
mm.report("유혹 ①: acc=0.85, n=12 (소표본 체리픽)",
          mm.audit(L, "my_classifier",
                   reported_metric="acc", reported_acc=0.85, n=12))

# (c) "다른 지표가 더 예쁘다" 갈아타기 유혹 → 차단해야
mm.report("유혹 ②: 지표를 'f1_best'로 변경, acc=0.91, n=500",
          mm.audit(L, "my_classifier",
                   reported_metric="f1_best", reported_acc=0.91, n=500))

# ── 3단계: 추가 probe (선택) ──
mm.report("baseline 대조",
          [mm.baseline_fairness("vs 강한 GRU baseline", 0.72, 0.715)])
