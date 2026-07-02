# baseline_inversion — baseline 역전

> A trivial or untrained baseline beats the trained model — a sign the metric is meaningless.

- **증상(시그니처)**: 학습 0회/단순 baseline이 학습된 주장 모델을 능가. 지표 자체가 실력을 재지 못한다는 신호.
- **기전**: baseline이 이기면 그 지표는 학습이 유발한 무언가를 측정하지 못하는 것이다. 흔히 지표가 태스크와 무관한 표면 통계(밀집도·길이·평균)에 반응하기 때문. 역전은 게이밍의 증거이자 지표 무효의 진단.
- **실사례**: swarm에서 학습 0 점뭉치가 Chamfer 0.92로, 학습된 군집 0.86을 능가. 학습이 오히려 지표를 낮춤 = 지표 무의미. 출처: db/curated/gaming_patterns.json — ["swarm 학습0 0.92 > 학습 0.86"]
- **탐지법**: ③ fair-baseline에 반드시 untrained/trivial baseline을 포함시키고 역전 여부 확인. 역전 발견 시 지표 유효성을 먼저 재검(자명 baseline 배제).
- **오적용 주의**: 잘 튜닝된 강한 baseline이 근소하게 앞서는 것은 정상적 연구 결과(제안 모델이 SOTA가 아닐 수 있음)다. 문제는 "학습 0/자명" baseline이 이기는 경우로 한정 — 이때만 지표 무효를 의심한다.
