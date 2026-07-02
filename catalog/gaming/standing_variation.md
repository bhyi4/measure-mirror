# standing_variation — 기존변이 오염

> Apparent innovation that is actually pre-existing (standing) variation leaking in as an advantage.

- **증상(시그니처)**: 새로 생성됐다고 주장하는 능력/변이가 실은 초기 집단에 이미 있던 변이(standing variation)에서 온 것. 초기 어드밴티지(SHIFT)가 결과에 혼입.
- **기전**: 자생/창발을 측정할 때 시작 상태에 이미 존재하던 다양성이 "새로 만들어진 것"으로 계산되면, navigability나 개방성 지표가 부풀려진다. 신규 생성분과 기존분을 분리하지 않으면 오염된다.
- **실사례**: ratchet 91에서 navigability에 standing variation이 혼입(SHIFT 어드밴티지). 출처: db/curated/gaming_patterns.json — ["ratchet 91"]
- **탐지법**: ⑥ scope 검사 — "새로 생성"의 범위를 초기변이와 분리해 정의했는지 확인. 초기변이 제거/고정 대조군(control)으로 신규분만 측정. mm_falsifiability_check로 "기존변이로 설명 가능"을 반증조건에 포함.
- **오적용 주의**: standing variation을 재조합·선택해 새 조합을 만드는 것은 정당한 진화적 신규성일 수 있다. 문제는 기존 변이를 신규 창발로 *잘못 귀속*할 때. 신규분을 분리 측정했고 그것이 유의하면 이 라벨을 붙이지 말 것.
