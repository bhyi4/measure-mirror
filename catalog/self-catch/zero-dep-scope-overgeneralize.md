# zero-dep-scope-overgeneralize — "zero deps·audits all" scope 과대 자가적발

> A self-audit caught the tool's own README overclaiming its scope and dependencies.

- **증상(시그니처)**: "zero dependencies" + "audits all AI eval claims" 같은 전방위 주장. scope 검사에서 과대일반화로 FAIL.
- **기전**: 도구의 실제 커버리지(분류/회귀/판정/순위 한정)와 광고 범위("all")가 불일치. 게다가 선택 의존(judge.py의 openai/anthropic 옵션)을 "zero-dep"으로 뭉뚱그리면 검증범위를 초과 주장한다.
- **실사례**: 측정거울 자기측정 ⑥ scope — mm_scope_check가 과대일반화 FAIL(judge.py는 openai/anthropic 옵션의존, 커버는 분류/회귀/판정/순위 한정) → README를 "Zero-dep core; judge optional"로 정직화. 출처: db/curated/self_catches.jsonl — measure_mirror_self_audit_20260612
- **탐지법**: ⑥ mm_verify(claimed_scope, tested_scope)로 광고범위≤실제 커버 강제. 의존성 실측(코어 vs 옵션 분리 표기). gaming/overclaim의 도구판.
- **오적용 주의**: 정직하게 한정된 범용 주장("분류·회귀에 대해")은 과대가 아니다. 문제는 "all/zero"처럼 검증 못 한 범위로 확장할 때. 커버 범위를 명시하면 이 라벨을 붙이지 말 것.
