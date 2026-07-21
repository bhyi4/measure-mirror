# untestable-substrate — 기질 무능을 가설 반증으로 오독

> When the substrate can't do the task at all, the hypothesis wasn't refuted — it was never tested.

- **증상(시그니처)**: 가설 검증에 쓴 기질(모델/시스템)이 검증 과제 *자체*를 chance 수준으로 수행. 그 위에서 나온 음성을 가설 KILL로 보고.
- **기전**: "X가 Y를 개선하는가"를 검증하려면 기질이 최소한 Y를 측정 가능한 수준으로 수행해야 한다. 바닥(chance)에 붙어 있으면 개선의 여지 자체가 측정 불가능하고, 음성은 가설이 아니라 기질에 대한 사실이다. 반증(KILL)과 검증불가(UNTESTABLE)는 다른 종결이다.
- **실사례**: (언어모델 메타인지 자기감시 실험) metacog_lang_selfmonitor — 기질검증에서 frozen neoul_recall_last가 과제 자체를 chance로 수행(free-gen recall acc 0.00~0.20, forced-choice ~0.5) → 가설 KILL이 아닌 UNTESTABLE terminal GUARD로 철회. 출처: db/curated/false_negative_guards.jsonl — ledger_retraction:metacog_lang_selfmonitor
- **탐지법**: 본실험 전 기질 자격검증(substrate qualification)을 별도 게이트로. 사전등록에 "기질이 기본과제 ≥ 임계"를 전제조건으로 명시(①). 철회 사유에 KILL/UNTESTABLE을 구별해 봉인.
- **오적용 주의**: 기질 무능이 곧 가설의 *간접 증거*인 경우가 있다(가설이 "이 기질로 가능하다"였다면 무능 자체가 반증). 가설의 주어가 기질인지 메커니즘인지 먼저 구별하라.
