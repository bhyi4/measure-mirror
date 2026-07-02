# effdim_collapse — 유효차원 붕괴 은닉

> A "perfect" convergence score that actually hides an information void (collapsed effective dimensionality).

- **증상(시그니처)**: Match/수렴 지표가 1.0 완벽인데, 실은 표현이 저차원으로 붕괴해 정보가 공동(空洞)임. 완벽함이 병리를 가린다.
- **기전**: 모든 입력이 같은 소수 차원으로 몰리면 매칭·재구성 지표가 역설적으로 완벽에 가까워질 수 있다(전부 비슷하게 맞음). effdim(유효차원)을 함께 재지 않으면 정보 소실을 성공으로 오독한다.
- **실사례**: aphasia에서 Match_cr=1.0 완벽수렴이 실은 effdim 1.8/576으로 붕괴 — match_cr=1.0이 실어증의 원인이었음. 출처: db/curated/gaming_patterns.json — ["aphasia 1.8/576", "match_cr=1.0이 실어증 원인"]
- **탐지법**: ④a로 지표를 effective rank/PR-dimension 등 정보량 지표와 교차. self-catch ⑦: "완벽 수렴"을 먼저 의심. fresh linear/MLP probe로 정보 실측(프록시 아닌 직접 readout, fn-guard 참조).
- **오적용 주의**: 낮은 유효차원이 항상 병리는 아니다 — 태스크 본질이 저차원이면 정당하다. 완벽 지표가 *정보 소실*과 동반될 때만 붕괴 은닉. effdim이 태스크에 필요한 만큼 유지되면 라벨 금지.
