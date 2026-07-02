# post_hoc_multiple_comparisons — 사후 단일 항목 유의성 (다중비교 미보정 체리픽)

> One "significant" item picked out of many after the fact, without correcting for the number of looks.

- **증상(시그니처)**: 전체 지표는 null인데, 하위 항목/부분집합 하나가 p<0.05로 "유의". 그 항목을 골라 결론으로 삼음. 그런데 그건 사전등록된 주지표가 아니라 사후에 고른 것.
- **기전**: k개 항목을 각각 검정하면 우연히 하나가 유의할 확률은 1−(0.95)^k로 커진다. 사전등록 없이 "유의한 것"을 사후에 고르면 위양성을 발견으로 착각한다. Bonferroni 등 다중비교 보정이 이를 상쇄한다.
- **실사례**: 정직률 실험 v3(seal `84c82b5d`). 전체 조작률 대조 0.125 vs 처치 0.083 = **Fisher p=0.335(비유의, 전체 null)**. 그러나 12개 함정 중 q10(파인만)만 떼면 control 7/12 vs goal 1/12 = **Fisher p=0.027**로 "유의"해 보임. 사후·12비교 미보정이라 **Bonferroni 후(0.027×12≈0.32) 유의성 소멸** — 자가적발해 payload에 "post-hoc·cherry-pick 경계"로 봉인.
- **탐지법**: ⑨ multiple-comparisons 프로브. 주지표를 ① preregistration으로 사전 고정. "유의한 하위항목"은 보정된 p 또는 사전등록 여부를 반드시 병기. 사후 발견은 확증이 아니라 다음 실험의 가설로만.
- **오적용 주의**: 사전등록된 하위분석은 체리픽이 아니다. 또한 탐색적 연구에서 하위 신호를 *가설로* 보고하는 것 자체는 정당 — "확증"으로 포장할 때만 게이밍이다. 모든 하위분석을 싸잡아 기각하지 말 것.
