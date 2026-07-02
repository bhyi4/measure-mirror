# tool-self-validation-gap — 무결성 도구가 자기 입력을 검증하지 않음

> The integrity tool sealed a malformed input silently, then crashed at evaluation — the auditor un-audited itself.

- **증상(시그니처)**: 검증 도구가 잘못된 입력을 조용히 받아들이고(봉인까지 성공), 나중 평가 단계에서 예외로 터진다. 도구 자신이 "입력 검증"이라는 자기 규율을 안 지킴.
- **기전**: 무결성 도구는 남의 주장을 검사하지만, 자기 API 입력에는 같은 엄격함을 적용하지 않기 쉽다. 특히 "선택적 구조화 필드"를 검증 없이 저장하면, 형식 오류가 봉인 시점(고칠 수 있을 때)이 아니라 평가 시점(이미 봉인된 뒤)에 드러난다. append-only·first-write-wins면 사후 교정도 막힌다.
- **실사례**: measure-mirror 자신. 비표준 `kill_threshold`(예 `{"H1_reject_if": ...}`, `threshold` 키 없음)를 `preregister()`가 검증 없이 봉인 → `audit()`/`falsifiability_check()`에서 `KeyError: 'threshold'`. first-write-wins라 같은 claim_id 재등록으로 교정 불가(새 id로 re-key만이 우회). 도그푸딩 중 자가적발(issue #18, fix PR #19: seal 시점 검증 + 기존 원장 graceful WARN).
- **탐지법**: 도구의 입력 경계에 **fail-fast 검증**(잘못된 형식은 저장/봉인 전에 거부). ⑦ self-catch: "내 도구는 자기 입력에 자기 기준을 적용하나?" append-only 저장 전 스키마 체크는 필수(사후 불가역이므로).
- **오적용 주의**: 모든 필드를 과잉 검증하면 자유형식(free-text)의 유연성을 죽인다. 검증은 *자동 평가에 쓰이는* 구조화 필드에만 — 사람이 읽는 서술 필드까지 강제 스키마를 걸지 말 것.
