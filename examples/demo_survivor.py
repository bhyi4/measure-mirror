"""mm으로 *살아남는* 프로그램 — 거짓을 죽이는 거울은 진실은 통과시킨다."""
import os
from measure_mirror import mm

L = "survivor_ledger.jsonl"
if os.path.exists(L):
    os.remove(L)

# 정직한 연구: 사전등록 → 대표본 → 공정 baseline 능가 → 누설 0
mm.preregister(L, "honest_model",
               metric="acc", min_n=200, baseline=0.5, pass_threshold=0.65)

print("▶ 정직하게 측정된 진짜 신호 — 살아남는가?")
mm.report("정직 모델: acc=0.78, n=1000, 등록지표 그대로",
          mm.audit(L, "honest_model",
                   reported_metric="acc", reported_acc=0.78, n=1000))
mm.report("공정 baseline 대비 (강한 GRU-ODE 0.71)",
          [mm.baseline_fairness("vs 강한 baseline", 0.78, 0.71)])
mm.report("데이터 누설 검사",
          [mm.leakage_check(list(range(0, 1000)), list(range(1000, 1200)))])

print("\n🪞 거짓을 죽이는 거울은, 진실은 통과시킨다 ↑")
