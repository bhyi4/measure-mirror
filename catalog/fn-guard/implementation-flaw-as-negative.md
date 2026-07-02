# implementation-flaw-as-negative — 구현 결함이 음성으로 위장

> A negative that is really an implementation bug masquerading as a real limitation.

- **증상(시그니처)**: "이 방법은 안 된다"는 음성이, 실은 자기 구현의 결함(비효율·버그) 때문. 결함을 고치면 PASS로 뒤집힘.
- **기전**: 잘못된 비용 산정·불필요한 연산·버그가 방법을 불가능처럼 보이게 만든다. 방법의 본질적 한계와 구현 우연을 분리하지 않으면 거짓음성이 남는다.
- **실사례**: FM회귀가 "Adjoint 필요"라는 거짓음성 → O(1) Adjoint불요 자가정정 → F1 PASS. 출처: db/curated/false_negative_guards.jsonl — fm_cde_pixel_feasibility
- **탐지법**: ⑤ 음성 시 최적/정당 구현을 썼는지 감사. 대안 구현으로 재시험(결과 뒤집히면 구현 결함). self-catch/adjoint-cost-overestimate와 짝.
- **오적용 주의**: 모든 음성을 "구현 탓"으로 미루면 진짜 벽을 부정하게 된다(성급낙관). 구현 결함 라벨은 실제 대안이 결과를 뒤집을 때만 — 여러 정당 구현에서도 음성이면 그것은 진짜 한계.
