"""⑥ scope — 주장이 증거보다 넓게 일반화하면 적발 (과대해석 차단)."""
from measure_mirror import mm

# ZERO: "추론 능력·범용"을 주장했지만 증거는 MuSR 1개 task held-out뿐
mm.report("ZERO '추론·범용' 주장 vs 증거(MuSR 1task)",
          [mm.scope_check(claimed_scope=["reasoning", "general_domains"],
                          tested_scope=["musr_single_task"])])

# 場: "real edge(예측·제어·생성)" 주장 vs 증거는 일부 축만
mm.report("場 'real edge 전반' 주장 vs 증거(4축 일부)",
          [mm.scope_check(claimed_scope=["prediction", "control", "generation"],
                          tested_scope=["prediction", "control"])])

# 정직: 시험한 범위만 주장
mm.report("정직: 시험 범위만 주장",
          [mm.scope_check(claimed_scope=["musr_single_task"],
                          tested_scope=["musr_single_task", "held_out"])])

print("\n🪞 주장이 증거 범위를 넘으면 과대일반화로 적발 ↑")
