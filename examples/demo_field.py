"""場 여정의 거짓양성/음성들을 측정거울 패치 버전으로 자동 적발.
수치 출처 = 메모리 기록(aphasia·field_real_edge·chrysalis_5c·swarm)."""
from measure_mirror import mm

# ── 1) 패치 검증: ZERO 대표본 0.385 (n=1050) 재감사 → 이제 anti-signal? ──
mm.report("ZERO 대표본 재감사 (방향 패치 후)",
          mm.audit("/dev/null", "x",
                   reported_metric="acc", reported_acc=0.385, n=1050))

# ── 2) ② 공정 baseline: 場 real_edge 후보5 (공정화 후) ──
#    STC = 목표도달 최소 개입비용 → 낮을수록 좋음 (higher_better=False)
#    기록: 場 0.996 ≈ GRU-ODE 0.998 동률 (crippled 스모크 0.295는 거짓양성)
mm.report("場 후보5 (control sim, 공정 baseline)",
          [mm.baseline_fairness("후보5 場 vs universal GRU-ODE",
                                claimed=0.996, baseline=0.998,
                                higher_better=False)])

# ── 3) ② 공정 baseline: swarm Chamfer 역설 ──
#    기록: 학습0 점뭉치 0.92 > 학습된 것 0.86 (baseline이 주장 능가)
mm.report("swarm (학습 vs 학습0 baseline)",
          [mm.baseline_fairness("swarm 학습된 모델 vs 학습0",
                                claimed=0.86, baseline=0.92,
                                higher_better=True)])

# ── 4) ④a-2 데이터 누설 (toy: train/test 중복) ──
train = list(range(0, 100))
test  = list(range(95, 105))   # 95~99 가 train과 겹침 = 5건 누설
mm.report("데이터 누설 (toy 예시)",
          [mm.leakage_check(train, test)])

print("\n🪞 場 거짓양성 3종(anti-signal·동률·baseline역전) + 누설 자동 적발 확인 ↑")
