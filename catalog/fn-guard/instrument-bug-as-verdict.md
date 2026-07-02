# instrument-bug-as-verdict — 계기 고장을 판정으로 오독

> A broken measuring instrument (NaN, empty denominator) masquerading as a scientific verdict.

- **증상(시그니처)**: 판정값이 NaN/NULL/0건 같은 퇴화값에서 나왔는데, 이를 "음성 결과"로 읽음. 분모가 비어 있거나 측정 대상 집합이 0개.
- **기전**: 파이프라인은 어떤 입력에서든 *무언가*를 출력한다. 측정 전제(예: 미사용 차원이 존재해야 floor 추정 가능)가 깨지면 출력은 계기 상태의 반영이지 대상의 속성이 아니다. verdict 필드에 값이 있다는 사실이 측정의 유효성을 보증하지 않는다.
- **실사례**: cand_a_edge_selection — D_max=30에서 SEL이 30차원 전부 점유 → 미사용(floor) 차원 0개 → 측정치 전부 None → κ=NaN → `NULL_kappa` 판정. 실판정이 아닌 계기 아티팩트로 철회. 출처: db/curated/false_negative_guards.jsonl — ledger_retraction:cand_a_edge_selection
- **탐지법**: 판정 산출 경로에 전제조건 assert(분모>0, 측정집합≠∅). 퇴화값(NaN/NULL)은 verdict 열거형에서 제외하고 "측정 무효"로 별도 분류. ⑦ self-catch: 판정이 이상하게 쉽게 나오면 계기부터 의심.
- **오적용 주의**: 진짜 0건(예: 탐색했으나 발견 0)과 계기 고장(탐색 자체가 불가능한 상태)은 다르다. 전제조건이 성립한 상태에서의 0은 유효한 음성이다 — 이 라벨로 모든 불리한 음성을 무효화하지 말 것.
