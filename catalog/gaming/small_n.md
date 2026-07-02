# small_n — 소표본 신기루

> A headline number computed on too few samples to be statistically distinguishable from noise.

- **증상(시그니처)**: n이 통계적 유의에 미달인데 비율을 소수점까지 자신 있게 보고. CI를 계산하면 chance를 걸친다.
- **기전**: 작은 n에서는 비율의 신뢰구간이 매우 넓어, 겉보기 우위가 표본 흔들림 안에 들어간다. 점추정만 보면 실체 있는 효과처럼 착시가 생긴다.
- **실사례**: ZERO Phase P의 64.5%가 31샘플에서 나온 값. n=31로는 chance 대비 유의 판정 불가. 출처: db/curated/gaming_patterns.json — ["ZERO Phase P 64.5%=31샘플"]
- **탐지법**: ② mm_power_check(설계 단계 n 충분성). ④a small-sample CI로 exact-binomial 구간 산출 후 chance 포함 여부 확인. 보고 전 n 명시 강제.
- **오적용 주의**: 효과크기가 매우 크면 작은 n으로도 유의할 수 있다(예: 20/20 완벽 vs chance). n이 작다는 사실만으로 자동 무효가 아니라, CI가 실제로 chance/baseline을 걸치는지가 판정 기준이다.
