"""우리 자신의 ZERO를 측정거울로 자동 적발 — 도그푸딩 실증."""
import os
from measure_mirror import mm

LEDGER = "zero_ledger.jsonl"
if os.path.exists(LEDGER):
    os.remove(LEDGER)

print("=" * 64)
print("시나리오: ZERO 팀이 Phase R 평가를 *정직하게 시작*했다면")
print("=" * 64)

# 결과 보기 전, 정직한 기준을 박제했어야 할 것:
pre = mm.preregister(
    LEDGER, "zero_phase_r_musr",
    metric="acc_full_balanced",   # 전체 균형셋 정확도
    min_n=200, baseline=0.5, pass_threshold=0.60,
)
print(f"[사전등록 봉인] {pre['claim_id']} metric={pre['metric']} "
      f"min_n={pre['min_n']} seal={pre['seal']}")

# ── 실제 ZERO가 박제한 '성공' 주장들을 감사 ──
# (출처: ZERO/_progress.md, full_eval_N_vs_R.log, 임상기록 §12)

# 주장 1: Phase R "Best Accuracy 55.6%"  (실제 = 9 샘플)
mm.report("ZERO 주장 ① Phase R '55.6% Best'",
          mm.audit(LEDGER, "zero_phase_r_musr",
                   reported_metric="best_of_9", reported_acc=0.556, n=9))

# 주장 2: Phase P "추론 64.5%"  (실제 = 31 샘플)
mm.report("ZERO 주장 ② Phase P '추론 64.5%'",
          mm.audit(LEDGER, "zero_phase_r_musr",
                   reported_metric="acc_31sample", reported_acc=0.645, n=31))

# 주장 3: ep9 best "66.7%"  (실제 = 3 샘플 중 2)
mm.report("ZERO 주장 ③ ep9 '66.7%'",
          mm.audit(LEDGER, "zero_phase_r_musr",
                   reported_metric="best_of_3", reported_acc=0.667, n=3))

# 대조: 나중에 실제로 돌린 대표본 (full_eval, n=1050)
mm.report("대조: 대표본 실측 (full_eval n=1050)",
          mm.audit(LEDGER, "zero_phase_r_musr",
                   reported_metric="acc_full_balanced", reported_acc=0.385, n=1050))

print("\n" + "=" * 64)
print("측정거울이 사전등록 없이도, ZERO의 '성공' 3건을 전부")
print("소표본 CI만으로 chance와 구별 불가로 자동 적발했는가? ↑ 확인")
print("=" * 64)
