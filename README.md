# 🪞 Measurement Mirror

<p align="center">
  <img src="docs/measure_mirror_og.png" alt="Measurement Mirror" width="500">
</p>

[![CI](https://github.com/bhyi4/measure-mirror/actions/workflows/ci.yml/badge.svg)](https://github.com/bhyi4/measure-mirror/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![deps: zero](https://img.shields.io/badge/deps-zero-brightgreen.svg)](pyproject.toml)

AI 평가 *주장*이 진짜 신호인지 **측정 착시(거짓양성/거짓음성)**인지 자동 적발.
**훈련 0 · 결정론적 · 의존성 0** (Python 3.10+ 표준 라이브러리만). 場과 정반대 — 붕괴 없음.

> 場(WaveODE/CDE)을 정직하게 검증하며 태어난 도구. 만든 자가 *자기 프로젝트를 먼저 죽였다.*
> → [🦋 크리살리스 연대기](docs/CHRONICLE.md) · License: Apache-2.0

## 설치

```bash
pip install -e .        # → `mm` 명령이 생김
```

## 사용법 — CLI

```bash
# ① 실험 *전*: 기준 박제 (해시 봉인)
mm register my_model --metric acc --min-n 200 --baseline 0.5

# ② 평가 *후*: 한 단어 — my_model.json 자동 로드
mm my_model

# (또는 명시적으로)
mm audit my_model --acc 0.72 --n 500
mm audit --file results.json     # {"claim_id","metric","acc","n"}
```

`mm <name>` 은 `<name>.json`(또는 `results/`, `mm_results/`)을 자동으로 찾아 감사한다.

## 사용법 — Python API

```python
from measure_mirror import mm
mm.preregister("ledger.jsonl", "my_model",
               metric="acc", min_n=200, baseline=0.5, pass_threshold=0.60)
mm.report("my_model", mm.audit("ledger.jsonl", "my_model",
          reported_metric="acc", reported_acc=0.72, n=500))
mm.report("baseline", [mm.baseline_fairness("vs GRU", 0.72, 0.71)])
mm.report("leak",     [mm.leakage_check(train_items, test_items)])
```

핵심: **사전등록을 *결과 보기 전*에 해야** ②에서 지표 갈아타기·표본 미달이 잡힌다.
사전등록 없이도 소표본 CI·방향·baseline·누설은 동작한다.

## probe 목록 (현재 6종)

| 함수 | 체크 | 잡는 것 |
|---|---|---|
| `preregister` / `audit` | ① 사전등록 | 사후 지표변경 · 표본 미달 |
| `audit` (소표본 CI) | ④a | chance 구별 불가 (소표본) |
| `audit` (방향) | ④a | anti-signal (chance 미만) |
| `leakage_check` | ④a | train∩test 데이터 누설 |
| `baseline_fairness` | ② | baseline 동률·역전 (crippled) |
| `scope_check` | ⑥ | 주장이 증거 범위 넘는 과대일반화 |

## 실제 적발 화면 예시 (Audit Output)

`examples/demo_zero.py` 및 `demo_field.py` 실행 시 소표본 신기루, 사후 지표 변경, 공정 baseline 동률/역전, 데이터 누설을 자동 적발하는 출력 화면입니다.

### 1. ZERO 소표본 및 사후 지표 변경 적발 (`demo_zero.py`)
```text
[사전등록 봉인] zero_phase_r_musr metric=acc_full_balanced min_n=200 seal=6c802655ab095e8b

🪞 측정거울 감사: ZERO 주장 ① Phase R '55.6% Best'
   종합: 🔴 FAIL
   🔴 [④a 소표본 CI] n=9, acc=0.556 → 95%CI [0.267, 0.811] ⊃ baseline(0.5). **chance와 통계적으로 구별 불가.**
   🔴 [① 사전등록(min_n)] 보고 n=9 < 등록 min_n=200. 표본 미달.
   🔴 [① 사전등록(지표변경)] 보고 지표 'best_of_9' ≠ 등록 지표 'acc_full_balanced'. **사후 지표 갈아타기.** (seal=6c802655ab095e8b)
```

### 2. 연속 매질(場) 거짓양성 및 데이터 누설 적발 (`demo_field.py`)
```text
🪞 측정거울 감사: 場 후보5 (control sim, 공정 baseline)
   종합: 🔴 FAIL
   🔴 [② 공정 baseline] 후보5 場 vs universal GRU-ODE: 주장 0.996 ≈ baseline 0.998 (Δ+0.002 < 0.01). **동률 — 고유 우위 없음.**

🪞 측정거울 감사: swarm (학습 vs 학습0 baseline)
   종합: 🔴 FAIL
   🔴 [② 공정 baseline] swarm 학습된 모델 vs 학습0: 주장 0.860 이 baseline 0.920 *보다 나쁨*. baseline 우수 — 주장 무효/게이밍.

🪞 측정거울 감사: 데이터 누설 (toy 예시)
   종합: 🔴 FAIL
   🔴 [④a 데이터누설] train∩test = 5건 (50.0% of test). **평가셋 오염.**
```

## 예제 실행

```bash
pip install -e .
python examples/usage_example.py   # 정직한 연구자 사용 흐름
python examples/demo_zero.py       # 우리 ZERO '55.6%' 자동 적발 (도그푸딩)
python examples/demo_field.py      # 場 거짓양성(후보5 동률·swarm 역전) 자동 적발
```

## 구조

```
measure-mirror/
├ pyproject.toml          # pip install → `mm` 명령
├ measure_mirror/{__init__,mm}.py   # probe + CLI + DB 조회
├ examples/               # 도그푸딩 데모 (ZERO·場)
└ db/                     # 공유 무결성 지도 (크리살리스 여정 시드)
   ├ baselines.json · gaming_patterns.json
   ├ reproductions.jsonl · contamination.jsonl
   └ false_negative_guards.jsonl · self_catches.jsonl
```

## 데이터 — 공유 무결성 지도 (`db/`)

크리살리스 여정에서 적발한 거짓양성/음성 사례를 시드. 서버 없이 Git 파일 DB,
기여는 PR, 사용자는 `mm update`로 받음 (CVE·안티바이러스 시그니처 모델).

| 파일 | 내용 |
|---|---|
| `baselines.json` | 과제별 공정 baseline (누가 등록 → 다음 사용자 baseline 자동조회) |
| `gaming_patterns.json` | 적발된 게이밍/신기루 수법 시그니처 |
| `reproductions.jsonl` | 주장 → 대표본 재현 음성 이력 |
| `contamination.jsonl` | 데이터 누설 지문 |
| `false_negative_guards.jsonl` | 거짓*음성* 가드 (진짜 대상 썼나) |
| `self_catches.jsonl` | 자가적발 — 만든 자의 프로젝트를 먼저 죽인 증거 |

## 철학
場과 정반대 = **훈련 0**. 거짓양성 **AND** 거짓음성 양방향. 사전등록 = 해시 봉인.
규율 원문: `Chrysalis/agent_chat/MEASUREMENT_MIRROR.md` (7체크). MVP는 그중 ①②④a 구현.

## 부록 — 거울 탄생 배경
- [🦋 크리살리스 연대기](docs/CHRONICLE.md) — 이 도구가 태어난 대장간. 場을 죽이며 측정거울이 벼려진 여정.

## 미구현 (다음)
- ③ 게이밍 정적분석 (AST) · ④b 적대 에이전트(LLM "진짜 대상 썼나") · ⑤ 재현 샌드박스
- PyPI 배포 (안정화 후)

## 기여 (Contributing)

`db/`에 오염·게이밍·재현실패 사례를 **PR**로 추가하면 다음 사용자가 덕봅니다
(CVE·안티바이러스 시그니처 모델). 새 probe·거짓음성 가드도 환영.

## License

Apache License 2.0 — [LICENSE](LICENSE) 참조.
