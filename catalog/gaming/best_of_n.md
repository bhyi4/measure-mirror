# best_of_n — Best-of-N 체리픽

> Reporting the maximum over N runs as if it were the expected performance.

- **증상(시그니처)**: 보고값이 N회 시도 중 최고값. 재현 시 평균은 훨씬 낮고, "성공한 seed 하나"만 반복 인용됨.
- **기전**: max of N은 N이 커질수록 우연히 올라간다. 분산이 큰 지표에서 최고값은 실력이 아니라 표본 크기의 함수다. 평균·분산·N을 함께 보고하지 않으면 우상향처럼 보인다.
- **실사례**: ZERO Phase R에서 55.6%가 best/9(9회 중 최고), ep9의 66.7%가 best/3. 최고값을 대표값으로 보고. 출처: db/curated/gaming_patterns.json — ["ZERO Phase R 55.6%=best/9", "ZERO ep9 66.7%=best/3"]
- **탐지법**: ① preregistration diff로 "N회 중 최고"를 사전에 집계규칙으로 못박았는지 확인. ④a로 평균±CI·N 강제. mm_verify(multiple-comparisons)로 N번 뽑기의 다중성 보정.
- **오적용 주의**: best-of-N 자체가 목적인 태스크(예: 샘플링 후 검증기로 채택하는 파이프라인)에서는 max가 정당한 지표다. 집계규칙을 사전에 선언하고 동일 N으로 baseline도 뽑았다면 게이밍이 아니다.
