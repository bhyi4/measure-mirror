# unswept-knob-attribution — 스윕 안 한 노브에의 벽 귀속

> A ceiling was attributed to a capacity knob that was never swept; the confirm-sweep found the ceiling knob-invariant.

- **증상(시그니처)**: "벽/천장/원인 = 노브 X" 귀속 주장인데 X를 실제로 스윕(≥3레벨)한 적이 없음. 근거가 "정적 추정치와 결과의 수치 근접"(예: solo 용량 추정 ~12 ≈ 천장 13-16)뿐. 후속 아크가 그 귀속 위에 설계되기 시작함.
- **기전**: 한 지점(single operating point)에서 두 수치가 비슷하면 인과 귀속이 공짜로 따라온다. 스윕 없이는 "X가 벽"과 "X와 무관하게 그 근방에서 다른 것이 포화"를 구별 불가. 봉인된 판정(포화=BOUNDED)은 유효해도, 판정문에 얹힌 귀속 gloss는 미검 주장으로 함께 봉인돼 다음 아크의 전제로 상속된다.
- **실사례**: compose 아크 종결 결론 "새 벽=단일개체 용량~12를 보호+선택이 ~13-16까지 확장 후 포화"(32b37b33·090d3b19의 해석 gloss) — HIDDEN 스윕 없이 귀속. 확인 스윕 capsweep(prereg d08f297d→판정 5224d2e0): HIDDEN 4배(5→20)에 solo·protected 천장 둘 다 flat(pearson 0.105) = 귀속 미지지. 이어 wallid(6a1ea40c→8f61853b): 훈련예산 16×도 벽 아님(오히려 하락). 귀속 위에 설계된 후속 molting(growing-capacity) 아크를 착수 전 KILL — 확인 스윕이 대형 아크 헛돌기를 선방지. 출처: db/curated/self_catches.jsonl — compose_capsweep_20260703, 원장 river_engine_ignition.jsonl.
- **실사례 2 (설계자 직면이 적발)**: 너울 코어 v2 "3-hop=스케일 한계"(ee30dc5e gloss, dm512·10000step·경계성적 0.35~0.53에서 귀속) — 스케일 노브 무스윕인 채 "스케일업은 불필요" 권고까지 얹음(이중 모순: 벽은 스케일 탓, 검증은 회피). 대장님 직면("소형이라 안 된다면서 스케일업 불필요?")→검증 depth3_scale_v1(78e93d9e→b596da415): 같은 19.2M 모델, 스텝 2배만으로 3-hop grok 6/6 = 예산벽. 용량 축은 돌릴 필요도 없었음. 같은 세션 raw-span 선례(609bff1d)가 있었는데도 반복한 점이 교훈: 귀속 교정은 사례 1회로 체화 안 됨, 모든 활성 "벽" 봉인에 노브 스윕 여부를 소급 점검해야. 출처: db/curated/self_catches.jsonl — neoul_depth3_budget_wall_20260704.
- **탐지법**: 귀속 주장에는 해당 노브 스윕을 요구(≥3레벨, 앵커/드리프트 동반). prereg kill-condition에 "노브 스윕서 불변이면 귀속 철회" 명시. 후속 아크 착수 전 그 전제의 저비용 확인 실험 먼저(이번 saga의 "②를 ①보다 먼저" 순서가 정확히 이것).
- **오적용 주의**: ①스윕이 K3(동일 예산에서 노브가 실현조차 안 됨)로 끝나면 귀속 '반증'이 아니라 '미지지/미결' — 이번 사례도 refuted가 아닌 unsupported로 기록했다. ②명시적 스윕 근거를 갖춘 귀속이나, "귀속은 잠정" 라벨이 붙은 서술엔 이 라벨을 붙이지 말 것. 봉인된 포화 판정 자체(BOUNDED)는 침해되지 않는다 — 교정 대상은 gloss뿐.
