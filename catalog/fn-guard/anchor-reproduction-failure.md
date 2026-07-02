# anchor-reproduction-failure — 양성대조 재현 실패한 측정을 판정으로 읽기

> If the positive control fails to reproduce, every negative from that experiment is void.

- **증상(시그니처)**: 실험의 통제/앵커 조건(이전에 확립된 양성 수치)이 이번 런에서 재현되지 않는데, 처치 조건의 음성만 골라 결론으로 보고.
- **기전**: 앵커가 안 나온다는 것은 이번 실험 설정 어딘가에 미통제 변수(confound)가 들어왔다는 신호다. 그 상태의 음성은 "가설이 틀림"과 "실험이 깨짐"을 구별할 수 없다. 특히 설정을 손대고(하이퍼파라미터, vocab 등) 그 영향을 앵커로 확인하지 않으면 조용히 무효 측정이 된다.
- **실사례**: neoul_residual_decomp — closure/sanity 조건 `ctrl_reproduces_0p745` 실패. 원인은 compact arm VOCAB을 256(앵커 실험값)→1024로 바꿔 4× 큰 softmax가 수렴을 늦춘 것. INCONCLUSIVE-confound로 자가적발·철회. 출처: db/curated/false_negative_guards.jsonl — ledger_retraction:neoul_residual_decomp
- **탐지법**: 사전등록에 앵커 재현을 **closure 조건**으로 명시(① preregistration). 앵커 실패 시 자동 무효 처리(판정 산출 차단). 설정 변경은 amendment로 가시화.
- **오적용 주의**: 앵커 수치에도 정당한 분산이 있다 — 시드 분산 범위 내 미달을 "재현 실패"로 과잉 판정하면 유효한 실험을 계속 버리게 된다. 앵커의 허용 범위를 사전에 수치로 박아라.
