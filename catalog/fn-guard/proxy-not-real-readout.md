# proxy-not-real-readout — 프록시가 진짜 readout 아님

> A proxy metric (e.g. cosine) standing in for the real readout can hide preserved information.

- **증상(시그니처)**: 코사인 유사도 같은 프록시로 "정보 없음/붕괴"를 결론. 그러나 프록시는 진짜 readout이 아님.
- **기전**: 프록시(거리·상관)는 실제 디코딩 가능성을 대신 못 잰다. 표현이 선형/비선형 probe로는 복원되는데 코사인으론 안 보일 수 있다. 프록시 음성을 정보 부재로 오독하면 거짓음성.
- **실사례**: aphasia에서 Match_tf 코사인 프록시로 판단 → fresh linear/MLP probe로 직접 측정 → 정보보존 10.2% 확정(프록시가 놓친 정보). 출처: db/curated/false_negative_guards.jsonl — aphasia_576d_attractor_collapse
- **탐지법**: ⑤ 음성 전 프록시 대신 직접 readout(fresh linear/MLP probe)로 재측정. mm_verify(claimed=측정하려는 것, tested=프록시)로 대리 불일치 검출.
- **오적용 주의**: 프록시와 직접 probe가 일치하면 프록시는 정당한 지표다. "프록시라서 무효"가 아니라, 프록시 음성이 직접 probe와 갈릴 때만 문제. 또 probe가 과적합해 유령 정보를 만들지 않게 held-out으로 검증.
