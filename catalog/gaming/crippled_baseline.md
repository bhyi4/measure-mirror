# crippled_baseline — 약화된 baseline

> Winning by handicapping the comparison, not by being better.

- **증상(시그니처)**: baseline이 의도적으로 약화(불공정 예산/형태/초기화)돼 우위가 연출됨. baseline을 공정화하면 우위가 소멸.
- **기전**: 비교 대상을 낮추면 같은 성능도 상대적으로 우월해 보인다. 특히 baseline의 수치적분기·용량·데이터를 제안 모델과 다르게 주면 "형태 일치"로 우위가 조작(rigged)된다.
- **실사례**: 場 후보5가 0.295로 압도적 양성처럼 보였으나, crippled GRU-ODE+Euler 형태일치로 rigged된 상태였음. 공정 universal GRU-ODE baseline에서 0.996≈0.998 동률. 출처: db/curated/gaming_patterns.json — ["場 후보5 0.295=crippled GRU-ODE+Euler 형태일치 rigged"]
- **실사례2(귀속판)**: 크리살리스 세포 o15가 'well-mixed mass-action granted(κ0.067) ≪ full-MD(κ0.372) ⇒ 선택이 irreducibly spatial'을 첫 양성으로 lean. 그러나 mass-action baseline은 **개별-접촉/조우 구조를 버린 crippled granted**였음 — o18 적대검증서 힘 없는 값싼 개별-접촉 모델(BRD κ0.29)이 gap의 ~67%를 재현(공간 confinement은 무관·역방향). ⇒ gap이 'spatial'로 보인 건 baseline이 접촉구조를 빠뜨린 탓, 진짜 축은 individual-contact vs mean-field. 공정 baseline으로 우위(=full-MD만의 몫)가 0.305→0.084로 급감. seal: mm river_engine_ignition.jsonl prereg fa246db0342a9622→retract e2aed947fe7bd47b(2026-07-10). ★변주=gap을 '값비싼/이색 기제(full-MD-spatial)'로 오귀속시키는 crippled baseline(우위 소멸 아니라 원인 오귀속).
- **실사례3(불완전 baseline=거짓 방어양성)**: 실사례2의 잔차 후속. 크리살리스 o19가 clean 앵커 κ_MD=0.339(prior 0.372=integrator 무결정 wobble 부풀림·교정) vs 값싼 접촉모델(o16·o-BRD ~0.30) paired 잔차 +0.031(n24 CI[0.009,0.054] 유의) = '아크 최초 작은 방어된 양성'으로 잠정 봉인. 그러나 o20이 기제를 국소화=**힘 사전정렬**(접촉쌍 코드상보 0.54 vs 중립껍질 0.03·strain게이트 inert), o21이 그 사전정렬을 값싼 모델에 **코드-gated 접촉**(g leak-매칭·반응 무차별)으로 부여하니 fresh paired 잔차 **−0.005 CI[−0.031,+0.024]=완전 닫힘**. ⇒ '방어된 양성'은 테스트한 값싼 baseline이 **기제(사전정렬)를 누락**한 탓 = 거짓 잔차. seal: mm river_engine_ignition.jsonl o19 prereg b87dd6eb→retract a91a44df·o21 prereg dd59da6a→am 462ce3f0(2026-07-11). ★변주=baseline이 '약화(rigged)'가 아니라 **'불완전(기제 무지로 누락)'** — 값싼 모델이 못 잡아도 기제 규명→그 기제 부여하면 닫힐 수 있으니 '방어된 양성'은 **테스트한 모델 집합의 완전성**에 조건부. ★추가교훈: 주변부 CI 겹침≠dissolve(paired 민감검정 필수)·봉인 앵커도 엔진 무결정이면 wobble.
- **탐지법**: ③ mm_baseline_fairness — 동일 예산/데이터/적분기 강제. self-catch ⑦로 "너무 압도적"을 먼저 의심하고 baseline 설정을 감사. ★잔차/우위가 남으면 **기제를 국소화**해 baseline이 그 기제를 빠뜨렸는지 확인(불완전 baseline 잔차 착시).
- **오적용 주의**: baseline이 단순하다는 것 자체는 약화가 아니다. 태스크 관행상 표준 baseline이고 동일 예산을 받았다면 정당하다. "약화"는 제안 모델과 비교해 부당하게 불리한 조건을 준 경우로 한정.
