# target_leak — 타깃 누설

> Future/target information leaking into the input, so the model "predicts" what it was already given.

- **증상(시그니처)**: 입력에 미래/타깃 정보가 새어 들어가 예측이 비현실적으로 쉬움. 사실상 정답을 복사.
- **기전**: 시계열/인과 태스크에서 미래 스텝이 입력에 포함되면 모델은 예측이 아니라 복사를 학습한다. 누설 배율이 클수록 성능이 부풀려지며, 인과 방향을 어긴 특징이 원인.
- **실사례**: (한 시계열 예측 모델 'ZERO DCC' 사전훈련) 미래 정보 20.6배 누설(모델이 입력을 그대로 복사) → 수정=인과 구동신호 dx_t=dX[t]-dX[t-1]. 출처: db/curated/contamination.jsonl — target_leak
- **탐지법**: ④a mm_leakage_check — 입력이 타깃/미래를 포함하는지 인과 감사. 특징을 인과 차분(dx_t)으로 재구성. baseline이 누설로 자명해지는지(gaming/baseline_inversion) 교차.
- **오적용 주의**: 합법적으로 과거 정보를 많이 쓰는 것은 누설이 아니다. 문제는 예측 시점 이후/타깃 자체가 입력에 들어갈 때. 시점 경계를 명확히 하고, 인과적으로 허용된 특징이면 라벨 금지.
