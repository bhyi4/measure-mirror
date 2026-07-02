# plateau-not-ceiling — plateau를 '천장'으로 단정

> Mistaking a temporary plateau for a fundamental ceiling when a fix actually exists.

- **증상(시그니처)**: 성능이 한 값에서 멈춰 "여기가 천장(아키텍처 한계)"이라 단정. 그러나 처방이 존재해 뚫린다.
- **기전**: plateau는 최적화·손실설계·헤드 구조의 우연일 수 있다. 이를 본질적 상한으로 오독하면 개선을 포기(거짓음성)한다. 진범(손실·본체)을 진단하지 않으면 처방을 놓친다.
- **실사례**: DCC 한글 char-LM 0.32 plateau를 '천장'으로 단정 → 천장 아님(PHANTOM), 이중진범=비트BCE손실+ODE본체, 처방=자모CE헤드+보존ODE. 출처: db/curated/false_negative_guards.jsonl — dcc_plateau_metric_phantom
- **탐지법**: ⑤ 음성(천장) 주장 전 손실/헤드/본체 ablation으로 진범 격리. mm_falsifiability_check에 "처방으로 뚫림"을 반증조건. gaming/effdim_collapse와 교차(붕괴가 plateau를 만들 수도).
- **오적용 주의**: 여러 독립 처방을 시도해도 안 뚫리면 그것은 진짜 천장에 가깝다. "처방이 있을 것"을 근거 없이 계속 주장하면 성급낙관 — 진범 진단이 특정 처방을 지목할 때만 이 라벨.
