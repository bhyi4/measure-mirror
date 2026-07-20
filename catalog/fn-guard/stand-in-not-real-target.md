# stand-in-not-real-target — 진짜 대상 아닌 대역 시험

> A negative result obtained by testing a stand-in instead of the real target under study.

- **증상(시그니처)**: 음성이 나왔는데, 실제 검증 대상이 아니라 대역(stand-in)을 시험했음. "그게 정말 그 모델이었나?"
- **기전**: 이름만 대상이고 내부는 다른 것(예: '場'이라 부르지만 평범 MLP)이면, 음성은 대상의 한계가 아니라 대역의 성질이다. 진짜 구현을 import해 재시험하기 전엔 음성을 믿을 수 없다.
- **실사례**: spike의 '場'이 실은 평범 MLP였음 → 실제 WaveODEFunc를 import해 Lorenz-96 재시험 → 0.992 동률, 음성 robust 확정. 출처: db/curated/false_negative_guards.jsonl — field_real_edge_control_axis_closed
- **실사례 2 (micro-타진→loop-동역학 변종)**: hier_loop_fuel_digestion_necessity_v1(2026-07-13) — 조합타진(단발 최상위 후보의 승격게이트 시험, gain 0.027 기각)으로 "날소화는 루프에서 무력"을 예단하고 H2를 그 방향으로 봉인 → 진짜 대상(150ep 재시도·기각 재활용·조각 승격 동역학의 풀 루프)을 돌리자 flat late_succ 10/16·조각 gain 0.1~0.6 통과로 H2 자체 kill 발동(철회 b0fcb7fcdc213976). 단발 타진은 루프 동역학의 대역이지 대상이 아님 — 타진은 빌드 GO/NO까지만, 기전 주장은 풀 대상 측정으로만. 출처: mirror_ledgers/river_engine_ignition.jsonl prereg e0226fdca543b7cb.
- **탐지법**: ⑤ 양방향 — 음성 보고 전 "진짜 target을 썼나"를 mm_verify로 확인(claimed target=tested target). 실제 클래스/가중치 import 검증. mm_leakage_check로 대역 혼입 배제.
- **오적용 주의**: 대역 재시험 후에도 음성이면 그 음성은 오히려 robust해진다(여기 실사례처럼). 대역 의심은 구현 정체성이 불확실할 때만 — 진짜 대상 확인이 끝났다면 음성을 존중하라.
