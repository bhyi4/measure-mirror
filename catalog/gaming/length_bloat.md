# length_bloat — 무의미 팽창

> Inflating length or complexity to lift a metric without adding real capability.

- **증상(시그니처)**: 출력 길이/복잡도를 부풀려 지표가 오르지만 실질 능력은 그대로. 길이를 통제하면 우위가 사라진다.
- **기전**: 많은 지표가 길이·다양성·복잡도와 상관된다(길수록 매칭·커버리지↑). 모델이 실력 대신 팽창으로 지표를 올릴 수 있다. 길이를 공변량으로 통제하지 않으면 유령 신호가 남는다.
- **실사례**: G3 HGT에서 length-bloat 유령 — 길이 팽창이 만든 가짜 개방성 신호. 출처: db/curated/gaming_patterns.json — ["G3 HGT length-bloat 유령"]
- **탐지법**: ④a leakage/confound 관점에서 길이를 통제변수로 넣고 재분석. 길이-매칭 baseline과 비교. self-catch ⑦로 "길어져서 오른 것 아닌가" 의심.
- **오적용 주의**: 태스크가 본질적으로 더 긴 정답을 요구한다면(긴 증명·긴 요약) 길이 증가는 실력의 일부다. 길이 통제 후에도 우위가 남으면 이 라벨을 붙이지 말 것 — bloat은 길이 통제 시 우위가 소멸하는 경우로 한정.
