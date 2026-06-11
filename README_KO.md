# 🪞 Measurement Mirror

[![CI](https://github.com/bhyi4/measure-mirror/actions/workflows/ci.yml/badge.svg)](https://github.com/bhyi4/measure-mirror/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![deps: zero](https://img.shields.io/badge/deps-zero-brightgreen.svg)](pyproject.toml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)

**AI 평가 주장의 거짓양성과 거짓음성을 자동으로 적발합니다.**  
훈련 불요 · 결정론적 · 외부 의존성 없음 (Python 3.10+ stdlib만 사용).

> 스스로의 연구를 정직하게 죽이는 과정에서 만들어진 도구입니다.  
> 만든 사람들이 자신에게 먼저 실행해봤습니다. → [🦋 탄생 배경](docs/CHRONICLE.md)

---

## 문제

AI/ML 논문은 일상적으로 과장된 주장을 합니다. 가장 흔한 실패 패턴:

| 착시 | 발생 방식 |
|---|---|
| 소표본 신기루 | n=9, acc=55.6%를 획기적 성과로 보고 |
| 사후 지표 교체 | 정확도로 등록하고, 더 좋아 보이는 F1으로 보고 |
| 허약한 기준선 | 의도적으로 약한 경쟁자와 비교 |
| 데이터 누설 | 훈련/테스트 중복으로 수치 부풀리기 |
| 범위 과대 일반화 | "작업 A에서 동작" → "일반 추론 가능"으로 주장 |

Measurement Mirror는 이것들을 **구조적으로** 잡아냅니다. 의견이 아닌 규칙과 통계로.

---

## 설치

```bash
pip install -e .                   # 코어 (외부 의존성 없음)
pip install -e ".[mcp]"            # + AI 에이전트용 MCP 서버
pip install -e ".[test]"           # + pytest 플러그인
pip install -e ".[mcp,test]"       # 전부
```

CLI 진입점: `mm`  
MCP 진입점: `mm-mcp`

---

## 빠른 시작

### CLI

```bash
# Step 1 — 실험 실행 전: 기준 봉인
mm register my_model --metric acc --min-n 200 --baseline 0.5 --pass 0.60

# Step 2 — 평가 후: 원커맨드 감사
mm my_model                            # my_model.json 자동 로드
mm audit my_model --acc 0.72 --n 500
mm audit --file results.json
```

`results.json` 형식: `{"claim_id": "my_model", "metric": "acc", "acc": 0.72, "n": 500}`

### Python API

```python
from measure_mirror import mm

LEDGER = "mm_ledger.jsonl"

# ① 실험 전 — 기준 봉인 (SHA-256 위변조 감지)
mm.preregister(LEDGER, "my_model",
               metric="acc", min_n=200, baseline=0.5, pass_threshold=0.60)

# ② 평가 후 — 7종 probe 일괄 감사
findings = mm.full_audit(
    LEDGER, "my_model",
    reported_metric="acc", reported_acc=0.72, n=500,
    baseline=0.5,
    competing_name="strong_baseline", competing_acc=0.68,   # ② 공정성
    reward_terms=["cross_entropy"],                          # ③ 게이밍 검사
    train_items=train_set, test_items=test_set,              # ④ 누설
    seed_results=[0.70, 0.72, 0.74],                         # ⑤ 다시드
    claimed_scope=["reasoning"], tested_scope=["task_a"],    # ⑥ scope
)
mm.report("my_model", findings)

# 개별 probe
mm.report("공정성", [mm.baseline_fairness("vs GRU", 0.72, 0.68)])
mm.report("누설",   [mm.leakage_check(train_items, test_items)])
mm.report("다시드", [mm.multiseed_check([0.70, 0.72, 0.74], baseline=0.5)])
```

### 회귀/연속 지표

MSE, Pearson r, RMSE 등 이진이 아닌 지표:

```python
findings = mm.continuous_audit(
    LEDGER, "my_regressor",
    reported_metric="mse", reported_value=0.10,
    baseline_value=0.15, n=500,
    higher_better=False,   # 낮을수록 좋음
    std=0.02,              # 선택: 효과크기 검사 활성화
)
mm.report("회귀 모델", findings)
```

### pytest 통합 (CI 게이트)

```python
# conftest.py
pytest_plugins = ["measure_mirror.pytest_plugin"]

# test_eval.py
from measure_mirror import mm
from measure_mirror.pytest_plugin import assert_clean

def test_my_model_is_real():
    findings = mm.audit("ledger.jsonl", "my_model",
                        reported_metric="acc", reported_acc=0.78, n=1000)
    assert_clean(findings)   # FAIL findings → 테스트 실패 → CI 빨간불
```

---

## 16종 Probe + 4 유틸리티 전체 목록

| Probe | 번호 | 잡아내는 것 |
|---|---|---|
| `preregister` / `audit` | ① | 사후 지표 교체 · 표본 미달 · 원장 위변조 |
| `verify_chain` | ① | 엔트리 삭제/삽입 · 원장 위변조 |
| `baseline_fairness` | ② | 허약한 / 동점 / 역전된 기준선 |
| `gaming_check` | ③ | 보상/손실에 평가 지표 직접 포함 (자기충족) |
| `audit` — Wilson CI | ④a | 통계적으로 우연과 구별 불가 (소표본) |
| `audit` — direction | ④a | 기준선보다 낮은 성능 (역신호) |
| `leakage_check` | ④a | 훈련∩테스트 데이터 오염 |
| `multiseed_check` | ⑤ | 불안정한 신호 / 운 좋은 시드 |
| `scope_check` | ⑥ | 주장 범위 > 검증 범위 (과대 일반화) |
| `too_good_check` | ⑦ | 기준선 대비 지나치게 큰 개선폭 |
| `power_check` | ⑧ | n이 너무 작아 진짜 효과를 못 잡음 (거짓음성 가드) |
| `multiple_comparisons_check` | ⑨ | 같은 레저에 k>1 실험 → Bonferroni 교정 경보 |
| `grim_check` | ⑩ | 보고된 acc × n이 정수 k와 일치 불가 (수치 조작 적발) |
| `falsifiability_check` | ⑪ | kill-condition 없음→반증불가; kill_threshold 발화→주장 사망 |
| `cascade_check` | ⑫ | 주장 자신 또는 전이 의존성 철회 → FAIL/WARN 오래됨 |
| `negative_audit` | ⑬ | 음성 결론에 독립 각도 부족·미등록 각도·범위 초과 탐지 |

| 유틸리티 | 역할 |
|---|---|
| `anchor` | 변조 방지 원장 스냅샷(해시+헤드 봉인) stdout 출력 → 외부 보관 |
| `calibrate` | 자가 테스트: 5종 합성 케이스로 도구 정상 작동 확인 |
| `witness` | 커맨드 실행·출력 캡처·변조 방지 실행 봉인 원장에 기록 |
| `retract` | 체인 연결 철회 엔트리 추가 → 의존 주장 cascade_check에서 STALE |

### 체인 해시 원장 (① 확장)

모든 `preregister()` 호출이 이전 엔트리의 seal을 포함하고 SHA-256을 계산합니다.
원장 파일 전체가 위변조 방지 체인이 됩니다:

```python
# 언제든지 원장 체인 전체 검증
findings = mm.verify_chain("mm_ledger.jsonl")
mm.report("원장 무결성", findings)
```

적발 범위: 엔트리 삭제, 삽입, 내용 수정.  
**명시된 한계**: 파일 통째 삭제 + 새 등록은 못 잡음 — git 커밋으로 보완.

### 검정력 probe ⑧

```python
# n이 진짜 효과를 잡기에 충분한지 사전 경고
f = mm.power_check(n=50, baseline=0.5, min_detectable_effect=0.05)
# ⚠️  n=50은 Δ=+0.05 탐지에 부족 (필요 n≥388, 80% 검정력)

# full_audit에서 활성화
findings = mm.full_audit(LEDGER, "my_model", ..., min_detectable_effect=0.05)
```

### 다중비교 probe ⑨

```python
# 같은 레저에 k>1 실험이 있으면 Bonferroni 교정 경보
f = mm.multiple_comparisons_check("mm_ledger.jsonl")
# ⚠️  k=3 실험 → Bonferroni α=0.0167 (0.05가 아님)

# full_audit에서 활성화
findings = mm.full_audit(LEDGER, "my_model", ..., check_multiplicity=True)
```

### 반증가능성 ⑪ — 포퍼 게이트

```python
# 실험 전 — 주장을 죽이는 조건까지 봉인
mm.preregister("mm_ledger.jsonl", "my_model",
               metric="acc", min_n=200, baseline=0.5, pass_threshold=0.60,
               kill_condition="held-out 테스트에서 정확도 0.55 미만",
               kill_threshold={"metric": "acc", "threshold": 0.55, "direction": "below"})

# 실험 후 — audit()이 ⑪을 자동 실행
findings = mm.audit("mm_ledger.jsonl", "my_model",
                    reported_metric="acc", reported_acc=0.50, n=500)
# 🔴 [⑪ falsifiability] Kill condition triggered: acc=0.5 < 0.55.
#    Claim 'my_model' is falsified by its own pre-registered criterion.
```

```bash
mm register my_model --metric acc --min-n 200 --baseline 0.5 --pass 0.60 \
  --kill "0.55 미만이면 사망" --kill-threshold 0.55 --kill-direction below
```

kill-condition 없이 등록된 주장은 audit 시점에 `WARN: Unfalsifiable`을 받습니다.
OSF 사전등록도 가설만 받지 죽음조건은 받지 않습니다 — 이 도구가 최초입니다.

### 철회 cascade ⑫

```python
# 의존성이 있는 주장 등록
mm.preregister("mm_ledger.jsonl", "model_v2",
               metric="acc", min_n=200, baseline=0.5, pass_threshold=0.60,
               depends_on=["dataset_v1", "baseline_eval"])

# 나중에 dataset_v1에서 오염 발견 → 철회
mm.retract("mm_ledger.jsonl", "dataset_v1", "훈련/테스트 중복 발견")

# cascade_check가 model_v2를 자동으로 STALE 표시
f = mm.cascade_check("mm_ledger.jsonl", "model_v2")
# ⚠️  [⑫ retraction-cascade] Claim 'model_v2' is STALE: depends (transitively) on
#     retracted claim(s): 'dataset_v1'

# audit()에서 cascade_check 자동 실행 (WARN/FAIL만 추가)
findings = mm.audit("mm_ledger.jsonl", "model_v2",
                    reported_metric="acc", reported_acc=0.72, n=500)
```

```bash
mm register model_v2 --metric acc --min-n 200 --baseline 0.5 --pass 0.60 \
  --depends-on dataset_v1 baseline_eval

mm retract dataset_v1 --reason "훈련/테스트 중복 발견"
```

철회 엔트리는 **체인 연결**되어 있어 삭제하면 `verify_chain()`에서 즉시 탐지됩니다.
발표 순서와 관계없이 철회가 전파됩니다: 철회된 기반 위에 세운 주장은 자동으로 오래된 것이 됩니다.

### 음성 주장 감사 ⑬ — 성급종결 게이트

단일 음성 결과는 frame 결함일 수 있습니다. `negative_audit`는 "Resolved-Negative"
결론에 대한 게이트입니다: 종결 전 최소 `min_angles`개의 독립 사전등록 실험이 수렴해야 합니다.

```python
# 각 독립 각도를 실험 전 등록
for angle_id in ["oee_test_wave", "oee_test_bilinear", "oee_test_alife"]:
    mm.preregister("mm_ledger.jsonl", angle_id,
                   metric="oee_score", min_n=100, baseline=0.5, pass_threshold=0.0)

# 모든 각도가 음성으로 수렴한 후 — 결론 게이트
f = mm.negative_audit("mm_ledger.jsonl",
                      angles=["oee_test_wave", "oee_test_bilinear", "oee_test_alife"])
# ✅ [⑬ negative-audit] 3/3 독립 사전등록 각도 검증 — 음성 결론 지지

# 선택사항: 결론 범위가 검증 범위보다 넓으면 FAIL
f = mm.negative_audit("mm_ledger.jsonl",
                      angles=["oee_test_wave", "oee_test_bilinear", "oee_test_alife"],
                      conclusion_scope=["all_substrates"],
                      tested_scope=["in_silico"])
# 🔴 [⑬ negative-audit] 검증되지 않은 범위 포함: ['all_substrates']
```

```bash
mm negative --angles oee_test_wave oee_test_bilinear oee_test_alife --min-angles 3
```

### 앵커(Anchor) ⎈

```bash
# 변조 방지 원장 스냅샷을 stdout으로 출력 — 신뢰하는 곳에 파이프
mm anchor                              # 컴팩트 JSON (기본)
mm anchor --pretty                     # 사람이 읽기 쉬운 형태

# 외부 보관 예시 (추가 의존성 없음)
mm anchor >> ~/Dropbox/mm_anchors.jsonl        # 로컬 백업
mm anchor | gh gist create -                   # GitHub Gist
```

```python
a = mm.anchor("mm_ledger.jsonl")
# {"_type": "anchor", "ts": "...", "entry_count": 3,
#  "head_seal": "a3b9f2c1", "anchor_hash": "sha256hex...", "chain_ok": true}
```

`anchor_hash`(원장 파일 전체 SHA-256)는 **파일 통째 교체**까지 감지합니다 — 체인 해시만으로는 잡을 수 없는 유일한 공격. 결과 공개 전 외부에 저장하세요.

### 보정(Calibrate) + 증인실행(Witness run)

```bash
# 거울 자체가 정상 작동하는지 확인
mm calibrate
# ✅ [⚙ calibrate] 5/5 케이스 정상 — 거울이 보정되었습니다.

# 증인 실행: 먼저 보정하고, 커맨드 실행 후 봉인 기록
mm run my_model -- python evaluate.py --model my_model
```

```python
# Python API
findings = mm.calibrate()
mm.report("거울 보정", findings)

entry = mm.witness("mm_ledger.jsonl", "my_model",
                   ["python", "evaluate.py", "--model", "my_model"])
# entry["output_hash"]은 스크립트 출력이 바뀌면 달라짐
```

### GRIM probe ⑩

```python
# 산술적으로 불가능한 정확도 수치 적발
f = mm.grim_check(reported_acc=0.33, n=10)
# 🔴  acc=0.33은 n=10에서 산술적으로 불가능합니다.
#     round(k/10, 2) = 0.33을 만족하는 정수 k가 없습니다.
#     (후보: k=3 → 0.3, k=4 → 0.4). 수치 조작 또는 n 오기재.

# audit() 내부에서 자동 실행 — FAIL일 때만 findings에 추가됨
findings = mm.audit(LEDGER, "my_model", reported_metric="acc", reported_acc=0.33, n=10)
```

---

## MCP 서버 — AI 에이전트 연동

MCP 호환 AI(Claude Code, Cursor, Windsurf 등)가 대화 중에 Measurement Mirror를 직접 호출할 수 있습니다.

### 설정

```bash
pip install "measure-mirror[mcp]"
```

**Claude Code** — 프로젝트 루트의 `.mcp.json`에 추가:

```json
{
  "mcpServers": {
    "measure-mirror": {
      "command": "python",
      "args": ["-m", "measure_mirror.mcp_server"],
      "cwd": "/path/to/measure-mirror"
    }
  }
}
```

**기타 MCP 클라이언트** — stdio 서버 명령으로 `mm-mcp`를 실행하세요.

16종 probe + 4 유틸리티 전부 MCP 도구로 노출됩니다:  
`mm_register` · `mm_verify_chain` · `mm_audit` · `mm_continuous_audit` · `mm_full_audit` ·  
`mm_baseline_fairness` · `mm_gaming_check` · `mm_multiseed_check` · `mm_scope_check` ·  
`mm_too_good_check` · `mm_power_check` · `mm_multiple_comparisons_check` · `mm_grim_check` ·  
`mm_falsifiability_check` · `mm_cascade_check` · `mm_negative_audit` ·  
`mm_anchor` · `mm_calibrate` · `mm_witness` · `mm_retract`

---

## 실제 적발 사례 — 도그푸딩

자체 AI 연구에 Measurement Mirror를 실행해서 잡아낸 것들:

```
🪞 Audit: ZERO "55.6% Best" 주장
   🔴 FAIL
   🔴 [④a small-sample CI] n=9, acc=0.556 → 95%CI [0.267, 0.811] ⊃ baseline(0.5)
       통계적으로 우연과 구별 불가.
   🔴 [① pre-registration(min_n)] 보고 n=9 < 등록 min_n=200. 표본 미달.
   🔴 [① pre-registration(metric-swap)] 보고 'best_of_9' ≠ 등록 'acc_full_balanced'
       사후 지표 교체 적발. (seal=6c802655ab095e8b)

🪞 Audit: Field 후보5 (제어 시뮬레이션)
   🔴 FAIL
   🔴 [② fair-baseline] Field 0.996 ≈ GRU-ODE 0.998 (Δ+0.002 < 0.01). 동점 — 진짜 우위 없음.
```

데모 직접 실행:

```bash
python examples/quickstart.py    # 정직한 연구자 정상 경로
python examples/demo_zero.py     # ZERO 55.6% 신기루 (우리 프로젝트 자가 폐기)
python examples/demo_field.py    # Field 후보 거짓양성
```

---

## 프로젝트 구조

```
measure-mirror/
├── measure_mirror/
│   ├── mm.py              # 10종 probe + CLI + DB 조회
│   ├── mcp_server.py      # MCP 서버 (pip install .[mcp])
│   └── pytest_plugin.py   # assert_clean() — CI 게이트
├── examples/
│   ├── quickstart.py      # 정상 경로 데모
│   ├── demo_zero.py       # ZERO 거짓양성 (도그푸딩)
│   ├── demo_field.py      # Field 거짓양성 (도그푸딩)
│   └── mcp_example.py     # MCP 도구 사용 참고
├── db/                    # 공유 무결성 데이터베이스 (서버 불요, git 기반)
│   ├── baselines.json         작업별 공정 기준선
│   ├── gaming_patterns.json   알려진 게이밍 패턴
│   ├── reproductions.jsonl    실패한 재현 사례
│   ├── contamination.jsonl    데이터 누설 지문
│   ├── false_negative_guards.jsonl
│   └── self_catches.jsonl     자체 적발 거짓양성
└── tests/test_mm.py       # 28개 테스트, CI 강제
```

---

## 공유 무결성 DB (`db/`)

서버 불요, git 기반. PR로 기여하고, git pull로 받아가세요.  
모델: CVE / 바이러스 백신 시그니처 — 하나의 적발이 미래 사용자 전체를 보호합니다.

자동 조회: `audit()`에 `task="musr"`를 전달하면 등록된 기준선이 자동으로 불러와집니다.

---

## 설계 원칙

- **외부 의존성 없음** — 순수 Python stdlib. 설치할 것도 깨질 것도 없음.
- **양방향 감지** — 거짓 *양성* **과** 거짓 *음성* 모두 잡음. 성급한 음성 종결도 착시임.
- **위변조 감지 사전등록** — 첫 쓰기에 SHA-256 봉인. 재등록은 무시됨. 원장 조작은 매 감사마다 감지됨.
- **독립적 probe** — 각 검사는 독립 함수. 기존 코드 건드리지 않고 새 검사 추가 가능.
- **기본이 의심** — "너무 좋은 결과"는 믿기 전에 먼저 플래그됨.

---

## 기여

새 probe, 거짓양성/음성 사례, 기준선 기여를 환영합니다.

1. Fork → 브랜치 → PR
2. **`db/` 기여**: `source`, `description`, `evidence`를 포함한 JSONL 라인 추가
3. **새 probe**: `mm.py`에 함수 추가 + `tests/test_mm.py`에 테스트 추가
4. CI 녹색 유지: `pytest tests/`

---

## 라이선스

[Apache 2.0](LICENSE)

---

[English README](README.md)
