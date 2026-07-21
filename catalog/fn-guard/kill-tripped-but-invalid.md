# kill-tripped-but-invalid — kill 액면 발동 ≠ 유효한 반증

> A tripped kill-condition only falsifies the hypothesis if the measurement itself was valid.

- **증상(시그니처)**: 사전등록된 kill-condition이 수치상 발동했고, 그대로 KILL을 선언하려 함 — 그런데 측정 설계에 결함이 있어 그 수치가 가설과 무관.
- **기전**: kill-condition은 "유효한 측정"을 전제로 한 계약이다. 측정이 가설의 대상을 재지 못하면(예: 비교 대상이 이미 과제를 다른 경로로 수행, 조작변수가 실제로 조작되지 않음) 발동한 kill은 형식적 참일 뿐 내용적 반증이 아니다. 규율을 지키는 것(발동=KILL 자동 선언)이 오히려 거짓음성을 만드는 드문 역설 — 해법은 무시가 아니라 **무효 선언 후 재설계**다.
- **실사례**: (한 신경망 능력 게이트 실험) neoul_window_elastic_copy — kill 조건(reach span<8)이 액면 트립했으나 설계결함 2건으로 무효 측정: ①KSET≤64는 조작변수가 재려던 능력(window 결속)을 재지 않음 — 순수 GDN이 이미 K48=0.82로 copy 수행 ②그 결과 SWA window가 reach를 통제하지 못해 eval_W 무관(W16 그리드 ≡ W128 그리드 완전 동일 — 이 불변성 자체가 tell). 결과 확정 전 INCONCLUSIVE-confound로 자가적발·철회(prereg seal ea07165), v2 재설계로 유효 측정 수행. 출처: db/curated/false_negative_guards.jsonl — ledger_retraction:neoul_window_elastic_copy
- **실사례 2 (지표 분모 결함 변종)**: vault_conflict_recall_v21(2026-07-03) — 교정(충돌 전수 스캔)이 목표를 달성(오발화 13→0·정밀도 1.0)했는데 K2 "conflict AMBIGUOUS율≥0.95"가 0.932로 발동. 원인=측정이 아니라 *지표 스펙*: 정직한 결과가 ABSTAIN인 부분모집단(hop1이 held-out 표현인 2hop 사슬)을 분모에 포함. 데이터 확증(미달 12/176 전부 ABSTAIN∧hop1_held, seal 643db6c4) 후 KILL을 등록대로 봉인하고 교정 지표로 v21b 재등록→PASS(926fa410). 사후합리화 방어: 결함 주장에 전수 분해 데이터 첨부·KILL 자체를 먼저 봉인. 출처: db/curated/false_negative_guards.jsonl — neoul_vault_conflict_recall_20260703
- **탐지법**: KILL 선언 전 측정 유효성 체크리스트(조작변수가 실제 조작됐나, baseline이 과제를 우회하지 않나). 무효 판정도 철회로 봉인하되 사유에 "KILL 아님·무효"를 명시(침묵 폐기 금지). v2 재실험은 새 사전등록으로.
- **오적용 주의**: 이 라벨은 kill 회피의 만능 탈출구가 되기 쉽다 — **불리한 결과가 나온 뒤에** 설계결함을 "발견"하는 패턴은 사후합리화다. 결함 주장은 구체적 기전과 독립 증거(예: baseline이 이미 과제 수행)를 요구하고, 무효 선언 자체를 봉인해 남겨라.
