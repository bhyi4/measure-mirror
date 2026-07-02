# label_encoding_loss — 라벨 인코딩 손실

> Information destroyed by a lossy label/target encoding, capping the metric before any modeling.

- **증상(시그니처)**: 인코딩 단계에서 라벨 정보가 절삭/손상돼, 모델이 아무리 좋아도 상한이 걸림. 측정 이전에 입력이 무너짐.
- **기전**: 비트폭이 부족한 인코딩(예: 받침 4비트 절삭)은 일부 클래스를 표현 못 해 영구 정보 손실을 낸다. 이는 모델 실패가 아니라 데이터 파이프라인 손상 — 성능 천장의 숨은 원인.
- **실사례**: 코돈 종성 인코딩에서 받침 4비트 절삭으로 ~30% 손상 → 수정=5비트 확장 + w_single 가중치 마스크. 출처: db/curated/contamination.jsonl — label_encoding_loss
- **탐지법**: 인코딩 왕복(round-trip) 무결성 테스트 — encode→decode가 원본을 복원하는지. plateau/천장을 볼 때 fn-guard/plateau-not-ceiling과 교차(인코딩 손실이 진범일 수 있음).
- **오적용 주의**: 의도된 손실 압축(허용 오차 내)이라면 손상이 아니다. 문제는 태스크에 필요한 클래스 구분이 인코딩에서 사라질 때. 왕복 테스트가 필요한 정보를 보존하면 이 라벨을 붙이지 말 것.
