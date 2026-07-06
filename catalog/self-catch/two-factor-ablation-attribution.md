# two-factor-ablation-attribution — 2요소 동시제거 절제의 단일요소 귀속

> An ablation arm silently removed two factors at once; the effect was credited to the headline factor.

- **증상(시그니처)**: 절제(control/drift/ablation) arm이 명목상 요소 X(예: 선택)를 제거했다며 "X가 효과의 동력"으로 귀속하는데, 그 arm의 구현을 보면 X 외에 Y(예: 환경 래칫/체인연장)도 함께 꺼져 있음. 절제 arm의 효과=0이 "구조적으로 0일 수밖에 없는" 설계.
- **기전**: control 구현의 편의(negative arm엔 래칫도 굳이 안 돌림)가 절제 변수를 2개로 만든다. 결과가 X 제거로 죽으면 X 귀속이 자연스러워 보이지만, 실제로는 Y 제거만으로도 죽는 설계였다면 X의 기여는 미측정. 봉인 판정의 kill-condition은 그 정의된 control로 충족되므로 판정 자체는 살고, **귀속 gloss만 오염**되어 후속 설계에 상속된다.
- **실사례**: compose 엔진 sealed GO(dbc74ca6)의 gloss "축적은 선택구동(무선택 drift=1 근거)" — drift arm은 선택 제거 + **체인연장 금지**를 동시 적용(연장은 control!="negative" 조건). molting 설계 스모크에서 연장 허용 무선택 arm이 cap까지 축적하는 것을 자가적발 → 정식 prereg(a526a55e) paired 검정: FIXED8 18.2 vs 무선택 16.6, paired_delta mean 1.6 ≤ 2 = **KILL**. 진짜 동력=크라우딩 차단(보호)×지속 SGD 훈련, 선택 기여 ~+1.6. gloss amendment(4bdd520318e11441), sealed GO 자체 불침해(crowded=1로 보호 필요성은 성립). 출처: db/curated/self_catches.jsonl — compose_q2_20260703.
- **탐지법**: 절제 arm마다 "이 arm에서 꺼진 것 전부"를 명시적으로 나열해 claim의 귀속 요소와 1:1인지 검사. 귀속 주장 전 단일요소 절제(다른 요소는 살려둔)로 재검. 구조상 절제 arm이 효과를 낼 수 없게 설계됐는지("by-construction 0") 질문.
- **오적용 주의**: ①복수 요소 동시 절제라도 claim이 "X+Y 결합이 필요"로 정직하게 쓰였으면 해당 없음. ②단일요소 재검서 X 기여가 실제로 크면(UPHOLD) 원 귀속은 유효 — 이 라벨은 재검 결과가 아니라 절제 설계의 구조를 보고 붙이는 것도 금지(재검으로 확정 후에만). ③판정 자체(kill-condition 충족)와 gloss를 구분 — 판정까지 소급 폐기하는 과잉적발 금지.
