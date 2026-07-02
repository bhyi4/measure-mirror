# crippled_baseline — 약화된 baseline

> Winning by handicapping the comparison, not by being better.

- **증상(시그니처)**: baseline이 의도적으로 약화(불공정 예산/형태/초기화)돼 우위가 연출됨. baseline을 공정화하면 우위가 소멸.
- **기전**: 비교 대상을 낮추면 같은 성능도 상대적으로 우월해 보인다. 특히 baseline의 수치적분기·용량·데이터를 제안 모델과 다르게 주면 "형태 일치"로 우위가 조작(rigged)된다.
- **실사례**: 場 후보5가 0.295로 압도적 양성처럼 보였으나, crippled GRU-ODE+Euler 형태일치로 rigged된 상태였음. 공정 universal GRU-ODE baseline에서 0.996≈0.998 동률. 출처: db/curated/gaming_patterns.json — ["場 후보5 0.295=crippled GRU-ODE+Euler 형태일치 rigged"]
- **탐지법**: ③ mm_baseline_fairness — 동일 예산/데이터/적분기 강제. self-catch ⑦로 "너무 압도적"을 먼저 의심하고 baseline 설정을 감사.
- **오적용 주의**: baseline이 단순하다는 것 자체는 약화가 아니다. 태스크 관행상 표준 baseline이고 동일 예산을 받았다면 정당하다. "약화"는 제안 모델과 비교해 부당하게 불리한 조건을 준 경우로 한정.
