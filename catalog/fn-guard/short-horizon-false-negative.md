# short-horizon-false-negative — 지평 너무 짧아 거짓음성

> A "falsified" verdict driven by too short a horizon (T), not by real absence of the effect.

- **증상(시그니처)**: "분기 FALSIFIED" 같은 음성 선언인데, 평가 지평(T)이 효과가 나타나기엔 너무 짧았음.
- **기전**: 느리게 발현하는 현상을 짧은 시간창에서 측정하면 아직 안 나온 것을 "없음"으로 오판한다. 지평이 파라미터인데 고정값 하나로 결론내면 거짓음성이 생긴다.
- **실사례**: latent_oee가 '분기1 FALSIFIED'로 선언 → 대장님 비판 적중, 지평(T) 너무 짧음 → 철회하고 지평-sweep으로 정정. 출처: db/curated/false_negative_guards.jsonl — chrysalis_latent_oee_pivot
- **탐지법**: ⑥ scope — 결론 전 지평/시간창을 sweep했는지 확인. mm_falsifiability_check로 "짧은 T로 설명 가능"을 반증조건에 포함. 음성은 지평 민감도 검사 후에만 봉인.
- **오적용 주의**: 지평을 충분히 늘려도 효과가 안 나오면 그 음성은 유효하다. "T가 짧았을 수도"를 무한히 대면 종결 불가 — sweep에서 수렴한 음성은 존중. 지평 확장에 이론적 상한을 정해두라.
