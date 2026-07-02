# template_drawing — 손코딩을 창발로 위장

> A result hand-drawn by a template or reward term, then claimed as emergent behavior.

- **증상(시그니처)**: template/reward loss로 직접 *그린* 결과를 자발적 창발이라 주장. 보상항을 빼면 현상이 사라진다.
- **기전**: 손실함수나 보상에 목표 패턴을 직접 넣으면 모델은 그것을 그리도록 강제된다. 이는 창발이 아니라 지시의 재현이다. 지표를 보상으로 주는 것 자체가 artifact이며, 제거/교체만이 정직한 검증이다.
- **실사례**: 3-A 막에서 template loss로 형태를 그림. ratchet에서 β·run_len을 직접 주입해 산출. 창발이 아닌 손코딩. 출처: db/curated/gaming_patterns.json — ["3-A 막 template loss", "ratchet β run_len 직접주입"]
- **탐지법**: ④ mm_verify(reward_terms) — 보상/손실항에 목표 지표가 들어갔는지 감사(게이밍 라인: 보상=artifact, 제거·교체만 정직). ablation으로 해당 항 제거 후 현상 잔존 여부.
- **오적용 주의**: 보상으로 유도했더라도 학습된 표현이 분포 밖으로 일반화하면 그 부분은 진짜 획득이다. "보상항 존재=자동 위장"이 아니라, 보상을 제거·교체해도 현상이 남는지로 판정. 남으면 창발 성분이 있는 것.
