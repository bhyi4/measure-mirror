# metric_switch — 사후 지표 갈아타기

> Reporting a different metric than the one preregistered, chosen after seeing results.

- **증상(시그니처)**: 사전등록 지표 ≠ 보고 지표. 결과를 본 뒤 더 유리한 지표로 갈아탐.
- **기전**: 여러 지표를 계산해두고 사후에 가장 좋은 것을 고르면, 우연히 좋은 지표를 선택하게 된다(다중비교·garden of forking paths). 사전에 못박지 않으면 선택 자유도가 곧 게이밍 대역폭이 된다.
- **실사례**: ZERO에서 사전등록된 acc_full 대신 best_of_9로 보고 지표를 교체. 출처: db/curated/gaming_patterns.json — ["ZERO acc_full→best_of_9"]
- **탐지법**: ① preregistration diff — 사전등록 지표와 보고 지표를 직접 대조. mm_preregister에 primary metric을 kill-condition과 함께 못박고, mm_verify로 불일치 검출.
- **오적용 주의**: 사전등록 시점에 더 적절한 지표를 발견해 명시적으로 amendment로 기록하고 그 근거를 남겼다면 정당한 개선이다. 침묵 교체만 게이밍이며, 문서화된 프로토콜 수정은 아니다.
