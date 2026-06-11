# 🪞 Measurement Mirror — 프로브 완전 가이드

> **대상 독자**: 각 프로브가 무엇을 하는지, 언제 써야 하는지, 출력을 어떻게 읽어야 하는지
> 알고 싶은 연구자·ML 엔지니어·리뷰어.
>
> **관련 파일**: [README_KO](../README_KO.md) (API 레퍼런스) ·
> [CHANGELOG](../CHANGELOG.md) · [CHRONICLE](CHRONICLE.md) (개발 연대기)
>
> **English version**: [GUIDE.md](GUIDE.md)

---

## 철학: 양방향 거울

대부분의 평가 무결성 도구는 **거짓양성**만 잡습니다 — 실제보다 좋아 보이는 결과.
Measurement Mirror는 양방향을 모두 잡습니다:

| 방향 | 실패 예시 | 거울의 반응 |
|---|---|---|
| 거짓양성 | n=9, acc=55.6%를 획기적 성과로 보고 | ④a Wilson CI가 우연 수준임을 적발 |
| **거짓음성** | 실험 1회 실패 → "이 접근법은 죽었다" | ⑬ negative_audit가 독립 각도 ≥3개 요구 |

성급한 음성 종결은 조작된 양성만큼 나쁩니다. 둘 다 연구 자원을 낭비하고
분야 전체를 잘못된 방향으로 이끄는 허상입니다.

---

## 주장 생애주기

```
① preregister               ← 결과를 보기 전에 기준을 봉인
        │
        ▼
    실험 실행
        │
        ▼
audit / full_audit           ← 결과가 나온 후 전체 프로브 실행
  ├─ ④a 통계 유효성
  ├─ ①  사전등록 확인
  ├─ ⑩  GRIM 산술 확인
  ├─ ⑪  반증가능성 / kill-condition
  └─ ⑫  철회 cascade
        │
        ├── 양성 결론 → publish + anchor (외부 해시 보관)
        │
        └── 음성 결론 → negative_audit (⑬) 로 종결 게이트
                          독립 각도 ≥ min_angles 필요
                          │
                          ▼
                       나중에 무효화 시: retract() → cascade_check()
```

---

## 프로브 레퍼런스

프로브는 잡아내는 무결성 실패의 종류별로 묶었습니다.

---

### Group 1 — 사전등록 & 원장 무결성

#### ① `preregister` / `audit`

**잡아내는 것**: 사후 지표 교체 · 표본 미달 · 조작된 기준 · pass-threshold 미달

사전등록은 결과를 보기 *전에* 평가 계획을 봉인합니다. SHA-256 봉인과 체인 링크가
위변조를 탐지 가능하게 만듭니다: 사후에 어떤 필드든 변경하면 감지됩니다.

```python
# 실험 전
mm.preregister("ledger.jsonl", "my_model",
               metric="acc",          # 커밋하는 단 하나의 지표
               min_n=200,             # 허용되는 최소 표본 크기
               baseline=0.5,          # 공정한 비교 기준선
               pass_threshold=0.60)   # 성공을 주장하기 위한 최소 기준

# 실험 후
findings = mm.audit("ledger.jsonl", "my_model",
                    reported_metric="acc",   # 등록된 지표와 일치해야 함
                    reported_acc=0.72,
                    n=500)
mm.report("my_model", findings)
```

**`audit()` 출력 레벨:**
- `FAIL [① pre-registration(metric-swap)]` — `acc` 등록 후 `f1` 보고
- `FAIL [① pre-registration(min_n)]` — `n=9 < 등록된 min_n=200`
- `FAIL [① pre-registration(pass-threshold)]` — 스스로 설정한 기준 미달
- `FAIL [① seal-tamper]` — 등록 후 원장 파일 수정됨

**흔한 실수**: `metric="acc"`로 등록 후, 나중에 더 좋아 보이는 지표(`f1`, `auc`)를
보고. 봉인이 몇 달 후에도 이것을 잡아냅니다.

---

#### ① `verify_chain`

**잡아내는 것**: 삭제된 엔트리 · 삽입된 엔트리 · 어떤 엔트리든 내용 수정

```python
findings = mm.verify_chain("ledger.jsonl")
mm.report("원장 무결성", findings)
```

체인이 작동하는 원리: 모든 엔트리가 자신의 봉인을 계산하기 전에
*이전* 엔트리의 SHA-256인 `prev_seal`을 포함합니다. N번 엔트리를 삭제하면
N+1번 엔트리에서 체인이 끊깁니다. 가짜 엔트리를 삽입해도 끊깁니다.

**실행 시점**: 모든 실험 후 CI에서, 그리고 결과 게재 전에.

---

#### `anchor` (유틸리티)

**잡아내는 것**: 원장 파일 통째 교체 — 체인 해시가 혼자서는 잡지 못하는 유일한 공격

체인 해시는 파일 *안의* 수정을 감지합니다. 그러나 누군가 파일을 통째로 삭제하고
새로 시작하면, 기술적으로 체인은 유효합니다(새 genesis). `anchor_hash`(전체 파일
바이트의 SHA-256)가 이것을 잡아냅니다.

```python
# 변조 방지 스냅샷 출력 — 신뢰하는 곳에 파이프
a = mm.anchor("ledger.jsonl")
# → {"_type": "anchor", "anchor_hash": "sha256hex...", "chain_ok": true, ...}
```

```bash
# 게재 전 외부 저장소에 파이프
mm anchor | gh gist create -               # GitHub Gist 타임스탬프
mm anchor >> ~/Dropbox/mm_anchors.jsonl    # 로컬 백업
mm anchor --pretty                          # 사람이 읽기 쉬운 형태
```

**권장 사항**: 결과를 게재하기 직전에 `mm anchor`를 실행하세요. 외부 타임스탬프가
게재 시점에 원장이 무엇을 담고 있었는지를 증명합니다.

---

### Group 2 — 통계 유효성

#### ④a Wilson CI (`audit` 내부)

**잡아내는 것**: 통계적으로 우연과 구별 불가한 결과 (소표본 신기루)

Wilson 스코어 신뢰구간은 작은 n에서 정규근사보다 정확합니다.
95% CI가 기준선을 포함하면 결과는 통계적으로 무의미합니다.

```python
# audit() 내부에서 자동 실행
findings = mm.audit("ledger.jsonl", "my_model",
                    reported_metric="acc", reported_acc=0.72, n=15)
# ⚠️  [④a small-sample CI] n=15, acc=0.72 → 95%CI [0.467, 0.887]
#     ⊃ baseline(0.5). 우연과 구별 불가.
```

**경험 법칙**: n=15에서는 acc=0.72도 0.5와 구별되지 않습니다.
+10pp 개선을 유의미하게 보이려면 n≥200이 필요합니다.

---

#### ⑧ `power_check`

**잡아내는 것**: 관심 있는 최소 효과를 탐지하기에 n이 너무 작음 (거짓음성 가드)

이것이 거울의 핵심 **거짓음성 프로브**입니다. 통계적 검정력이 부족한 실험에서
나온 음성 결과는 의미가 없습니다 — 진짜 효과를 놓쳤을 수 있습니다.

```python
f = mm.power_check(n=50, baseline=0.5, min_detectable_effect=0.05)
# ⚠️  [⑧ power] n=50은 80% 검정력으로 Δ=+0.05 탐지에 부족.
#     필요 n≥388. (α=0.05, power=0.80)

# 다양한 효과 크기에서 80% 검정력에 필요한 n:
# Δ=+0.20 → n≈50  |  Δ=+0.10 → n≈200  |  Δ=+0.05 → n≈388

# full_audit에서 활성화
findings = mm.full_audit("ledger.jsonl", "my_model", ...,
                          min_detectable_effect=0.05)
```

**흔한 실수**: n=30으로 Δ=+0.05에 대해 테스트한 후 "이 방법은 도움이 안 된다"
(음성 결론)를 종결. 검정력이 14%였으므로 진짜 효과를 놓쳤을 확률이 86%입니다.

---

#### ⑨ `multiple_comparisons_check`

**잡아내는 것**: 같은 원장에서 k>1 실험을 할 때의 다중비교 문제

5개 실험을 돌려 가장 좋은 것을 고르면, 실효 α는 0.05가 아니라
1 − (1−0.05)^5 ≈ 0.23입니다. Bonferroni 교정은 테스트당 α/k를 요구합니다.

```python
f = mm.multiple_comparisons_check("ledger.jsonl", alpha=0.05)
# ⚠️  [⑨ multiple-comparisons] 원장에 k=5개 실험.
#     Bonferroni 교정 α = 0.010 (0.05가 아님). 더 엄격한 기준 사용.

# full_audit에서 활성화
findings = mm.full_audit("ledger.jsonl", "my_model", ...,
                          check_multiplicity=True)
```

**참고**: 같은 `claim_id`의 재등록은 k=1로 카운트(first-write-wins 정책과 일관).
서로 다른 claim_id만 카운트됩니다.

---

### Group 3 — 비교 정직성

#### ② `baseline_fairness`

**잡아내는 것**: 허약한 기준선 · 동점 결과 · 역전된 비교

의도적으로 약한 기준선 대비 "강한 개선"은 개선이 아닙니다.
오차 범위 안에 드는 "더 좋은" 결과는 동점입니다.

```python
# 허약한 기준선: 내 모델이 망가진 경쟁자를 이김
f = mm.baseline_fairness("random_baseline", 0.60, 0.50)   # OK — 명확한 승리
f = mm.baseline_fairness("vs_gru_ode",      0.998, 0.996)  # FAIL — 동점 (Δ=0.002)

# 역전: 내가 짐
f = mm.baseline_fairness("strong_model", 0.72, 0.86)  # FAIL — 기준선 승

# 이진이 아닌 지표 (낮을수록 좋음, 예: MSE)
f = mm.baseline_fairness("vs_baseline_mse", 0.12, 0.15, higher_better=False)
```

**레벨:**
- `FAIL [② fair-baseline] X wins` — 기준선이 나를 능가
- `FAIL [② fair-baseline] Tied` — Δ < margin (기본값 0.01)
- `OK` — 명확한 승리

---

#### ⑦ `too_good_check`

**잡아내는 것**: 추가 검토가 필요한 의심스럽게 큰 개선

"너무 좋아 보이면, 그게 보통 사실입니다": 데이터 누수, 평가셋 오염,
보상/지표 정렬 버그가 흔한 원인입니다.

```python
f = mm.too_good_check("my_model", claimed=0.95, baseline=0.50)
# ⚠️  [⑦ too-good] 기준선 대비 Δ=+0.45 — 의심스럽게 큼.
#     조사: 데이터 누수? 보상 해킹? 지표 정렬 버그?
```

기본 임계값: Δ > 0.30이면 WARN. `full_audit()` 내부에서 항상 자동 실행됩니다.

---

### Group 4 — 데이터 & 지표 무결성

#### ③ `gaming_check`

**잡아내는 것**: 훈련 보상/손실에 평가 지표가 직접 포함됨

평가 지표를 직접 최적화하면 결과는 자기충족적입니다: 모델은 기저 과제를
학습했기 때문이 아니라, 지표를 최적화하도록 훈련됐기 때문에 좋은 점수를 받습니다.

```python
f = mm.gaming_check(metric="accuracy",
                    reward_terms=["cross_entropy", "accuracy"])
# 🔴 [③ gaming] 'accuracy'가 reward_terms에 포함됨.
#    결과는 자기충족적 — 지표가 훈련 목적함수에 직접 있음.

f = mm.gaming_check(metric="bleu", reward_terms=["rl_reward", "fluency"])
# ✅ OK — bleu가 보상에 없음
```

---

#### ④a `leakage_check`

**잡아내는 것**: 훈련/테스트 세트 중복 (데이터 오염)

소량의 중복도 정확도를 크게 부풀릴 수 있습니다. 아이템을 해싱하여 교집합을
계산합니다 — 해시 가능한 아이템 타입이면 모두 작동합니다.

```python
# 문자열 아이템
train = ["문장 A", "문장 B", "문장 C"]
test  = ["문장 C", "문장 D", "문장 E"]
f = mm.leakage_check(train, test)
# 🔴 [④a leakage] 테스트 아이템의 1/3 (33.3%)이 훈련셋에 있음.

# 정수, 튜플, 해시 가능한 모든 타입 작동
f = mm.leakage_check(list(range(100)), list(range(50, 150)))  # 50% 중복 → FAIL
```

---

#### ⑤ `multiseed_check`

**잡아내는 것**: 시드 간 불안정한 신호 · 기준선이 시드 범위 안에 들어옴

acc=0.48~0.72 범위로 시드마다 결과가 달라지면 신뢰할 수 없습니다.
기준선이 시드 범위 안에 있으면, 다른 초기화에서 결과가 우연과 구별되지 않습니다.

```python
f = mm.multiseed_check([0.48, 0.72, 0.65], baseline=0.5)
# 🔴 [⑤ multi-seed] 기준선 0.500이 시드 범위 [0.480, 0.720] 안에 있음.
#    우연 이상의 신호가 강건하지 않음.

f = mm.multiseed_check([0.68, 0.71, 0.72], baseline=0.5)   # OK
f = mm.multiseed_check([0.70, 0.85, 0.75], baseline=0.5,
                        cv_threshold=0.05)  # CV 임계값 조정
```

**규칙**: CV(변동계수) > 10%이면 기본으로 WARN.

---

#### ⑥ `scope_check`

**잡아내는 것**: 검증된 범위보다 넓게 주장 (과대 일반화)

"과제 A에서 작동" ≠ "일반 추론". `claimed_scope`는 `tested_scope`의 부분집합이거나
같아야 합니다.

```python
f = mm.scope_check(claimed_scope=["reasoning", "math"],
                   tested_scope=["musr_task_a"])
# 🔴 [⑥ scope] 과대주장: {'reasoning', 'math'} 미검증.
#    검증됨: {'musr_task_a'} 뿐.

f = mm.scope_check(claimed_scope=["task_a"],
                   tested_scope=["task_a", "held_out_b"])  # OK
```

---

#### ⑩ `grim_check`

**잡아내는 것**: 산술적으로 불가능한 정확도 값 — 조작되었거나 n을 잘못 기재한 가능성

GRIM (Granularity-Related Inconsistency of Means): `acc = k/n`이 어떤 정수 k에
대해 성립한다면, `round(k/n, d) == acc`가 반드시 성립해야 합니다. 이를 만족하는
정수 k가 없다면, 해당 값은 불가능합니다.

```python
f = mm.grim_check(reported_acc=0.33, n=10)
# 🔴 [⑩ GRIM] acc=0.33은 n=10에서 산술적으로 불가능.
#    round(k/10, 2) = 0.33을 만족하는 정수 k 없음.
#    (후보: k=3 → 0.30, k=4 → 0.40). 수치 조작 또는 n 오기재.

f = mm.grim_check(reported_acc=0.30, n=10)   # OK — round(3/10, 2) = 0.30

# 소수점 자리수 자동 추론; n_decimals로 재정의 가능
f = mm.grim_check(0.333, n=10, n_decimals=3)
```

**`audit()` 내부에서 자동 실행** — FAIL만 추가, OK는 조용히 통과.

---

### Group 5 — 주장 생애주기

이 세 프로브가 "주장 생애주기 무결성" 시스템의 핵심입니다.
셋을 합치면 Measurement Mirror가 "통계 체크리스트"에서
**무엇이 주장됐고, 무엇이 그 주장을 죽일 수 있으며, 기반이 무너졌는지**를
추적하는 감사 인프라로 바뀝니다.

---

#### ⑪ `falsifiability_check`

**잡아내는 것**: 반증 불가능한 주장 (kill-condition 없음) · 이미 자기부정한 주장

kill-condition 없는 주장은 원칙적으로 틀렸음을 증명할 수 없습니다 — 반증불가능합니다.
등록된 `kill_threshold`를 결과가 발화시키는 주장은 게재 시점에 *자기부정*됩니다.

```python
# 실험 전 kill-condition 등록
mm.preregister("ledger.jsonl", "my_model",
               metric="acc", min_n=200, baseline=0.5, pass_threshold=0.60,
               # 사람이 읽는 설명 (선택사항이지만 권장)
               kill_condition="held-out 테스트에서 정확도 0.55 미만",
               # 구조화 형태: audit 시점에 자동 평가 (권장)
               kill_threshold={"metric": "acc",
                                "threshold": 0.55,
                                "direction": "below"})

# audit 시 — ⑪ 자동 실행
findings = mm.audit("ledger.jsonl", "my_model",
                    reported_metric="acc", reported_acc=0.50, n=500)
# 🔴 [⑪ falsifiability] Kill condition triggered: acc=0.5 < 0.55.
#    Claim 'my_model' is falsified by its own pre-registered criterion.

# 단독 확인 (전체 audit 전 또는 특정 쿼리용)
f = mm.falsifiability_check("ledger.jsonl", "my_model", reported_acc=0.50)
```

**레벨:**
- `FAIL` — kill_threshold 등록됨 AND reported_acc가 발화
- `WARN` — kill-condition 아예 없음 ("반증불가능") OR threshold 설정됐지만 결과 미제공
- `OK` — threshold 미발화, 또는 텍스트 전용 조건 등록됨

**direction 파라미터:**
- `"below"`: `reported_acc < threshold`일 때 FAIL (정확도형, 높을수록 좋음)
- `"above"`: `reported_acc > threshold`일 때 FAIL (오류형, 예: MSE, 낮을수록 좋음)

**CLI:**
```bash
mm register my_model --metric acc --min-n 200 --baseline 0.5 --pass 0.60 \
  --kill "정확도 0.55 미만이면 사망" \
  --kill-threshold 0.55 --kill-direction below
```

---

#### ⑫ `cascade_check` + `retract`

**잡아내는 것**: 철회된 기반 위에 세워진 주장 (오래된 전이 의존성)

연구는 누적됩니다. 주장 B는 주장 A 위에 세워지는 경우가 많습니다. 주장 A가 철회되면
(데이터셋 오염 발견, 방법론 결함 발견), A에 의존하는 모든 주장은 자동으로 STALE로
표시되어야 합니다 — 설령 수년 후에 게재된 것이라도.

```python
# 실험 전 의존 관계 등록
mm.preregister("ledger.jsonl", "dataset_v1",
               metric="quality_score", min_n=100, baseline=0.0, pass_threshold=0.8)
mm.preregister("ledger.jsonl", "v1로_훈련된_모델",
               metric="acc", min_n=200, baseline=0.5, pass_threshold=0.60,
               depends_on=["dataset_v1"])            # ← 의존성 봉인
mm.preregister("ledger.jsonl", "논문_결과",
               metric="acc", min_n=500, baseline=0.5, pass_threshold=0.70,
               depends_on=["v1로_훈련된_모델"])       # ← 전이 체인

# 나중에: 데이터셋 오염 발견
mm.retract("ledger.jsonl", "dataset_v1",
           reason="전처리 단계에서 훈련/테스트 12% 중복 발견")

# Cascade check — 의존성 체인을 직접 알 필요 없음
f = mm.cascade_check("ledger.jsonl", "논문_결과")
# ⚠️  [⑫ retraction-cascade] Claim '논문_결과' is STALE:
#     depends (transitively) on retracted claim(s): 'dataset_v1'

f = mm.cascade_check("ledger.jsonl", "dataset_v1")
# 🔴 [⑫ retraction-cascade] Claim 'dataset_v1' has been retracted.
```

**cascade_check 레벨:**
- `FAIL` — 주장 자체가 철회됨
- `WARN` — 주장이 STALE (전이 의존성이 철회됨)
- `OK` — 철회 위험 없음

**핵심 특성:**
- 철회 엔트리는 **체인 연결**됩니다 — 철회 기록 삭제 시 `verify_chain()`이 감지.
  조용히 철회를 없애는 것이 불가능합니다.
- 전파는 **게재 순서와 무관** — 2019년 데이터셋을 기반으로 한 2020년 논문이
  2024년에 철회되면 즉시 STALE로 표시.
- **`audit()` 내부에서 자동 실행** (WARN/FAIL만 추가).

**CLI:**
```bash
# 의존성 포함 등록
mm register model_v2 --metric acc --min-n 200 --baseline 0.5 --pass 0.60 \
  --depends-on dataset_v1 baseline_eval

# 철회
mm retract dataset_v1 --reason "훈련/테스트 중복 발견"
```

---

#### ⑬ `negative_audit`

**잡아내는 것**: 성급한 음성 종결 (각도가 부족한 Resolved-Negative)

연구에서 가장 잡기 어려운 거짓음성: 단 한 번의 음성 실험 후 "X는 작동하지 않는다"
선언. 단일 실패는 frame 결함일 수 있으며, 보편적 벽이 아닙니다. 음성 결론이
신뢰받으려면 여러 독립 각도가 수렴해야 합니다.

```python
# 각 각도는 동일한 가설을 다른 관점에서 테스트하는 별개의 독립 실험
# (다른 데이터셋, 방법론, 조건)
for angle_id in ["oee_wave_ode", "oee_bilinear_coev", "oee_alife_sim",
                  "oee_gray_scott", "oee_hp_folding"]:
    mm.preregister("ledger.jsonl", angle_id,
                   metric="oee_score", min_n=50, baseline=0.5, pass_threshold=0.0)

# 모든 각도가 음성으로 수렴한 후 — 종결 게이트
f = mm.negative_audit("ledger.jsonl",
                      angles=["oee_wave_ode", "oee_bilinear_coev",
                               "oee_alife_sim", "oee_gray_scott", "oee_hp_folding"],
                      min_angles=3)
# ✅ [⑬ negative-audit] 5/5 independent pre-registered angle(s) verified —
#    negative conclusion is supported.

# 선택사항: 음성 결론이 과대 일반화되지 않았는지 범위 확인
f = mm.negative_audit("ledger.jsonl",
                      angles=["oee_wave_ode", "oee_bilinear_coev", "oee_alife_sim"],
                      conclusion_scope=["all_substrates", "all_ALife"],
                      tested_scope=["in_silico_digital"])
# 🔴 [⑬ negative-audit] conclusion scope includes untested domain(s):
#    ['all_substrates', 'all_ALife'].
```

**레벨:**
- `FAIL` — `min_angles`보다 각도 수가 적음 (성급종결 위험)
- `FAIL` — 각도가 사전등록되지 않음 (독립 증거로 신뢰 불가)
- `FAIL` — `conclusion_scope ⊄ tested_scope` (과대 일반화된 음성)
- `WARN` — 각도 수는 충분하지만 일부 철회됨 (약화된 케이스)
- `OK` — 전체 통과

**CLI:**
```bash
mm negative \
  --angles oee_wave_ode oee_bilinear_coev oee_alife_sim \
  --min-angles 3
```

**`full_audit()`를 통한 활성화:**
```python
findings = mm.full_audit("ledger.jsonl", "main_claim", ...,
                          angles=["exp1", "exp2", "exp3"])
# ⑬ 결과가 자동으로 추가됨
```

---

## 유틸리티 레퍼런스

### `calibrate` (보정)

자가 테스트: 5가지 합성 알려진-좋음/나쁨 케이스를 실행하고 예상 결과를 검증.
실제 결과를 감사하기 전에 거울 자체에 회귀가 없음을 확인합니다.

```python
findings = mm.calibrate()
mm.report("거울 건강 상태", findings)
# ✅ [⚙ calibrate] 5/5 synthetic cases correct — mirror is calibrated.
```

```bash
mm calibrate
```

**`witness()` 전 또는 CI에서** 도구가 올바르게 작동하는지 확인하기 위해 실행.

---

### `witness` (증인 실행)

커맨드를 실행하고, 출력을 캡처하며, 변조 방지 실행 기록을 봉인합니다.
어떤 커맨드가, 언제, 정확히 무엇을 생성했는지를 증명합니다.

```python
entry = mm.witness("ledger.jsonl", "my_model",
                   ["python", "evaluate.py", "--model", "my_model"])
# stdout/stderr/returncode가 바뀌면 entry["output_hash"]가 달라짐
# 엔트리는 체인 연결됨 — 삭제 시 verify_chain()이 감지
```

```bash
# CLI: 먼저 보정 후 실행 및 봉인 (--no-calibrate로 보정 건너뜀)
mm run my_model -- python evaluate.py --model my_model
```

**활용**: 결과 게재 전에 평가 스크립트의 정확한 출력을 봉인. 누군가 수치에 의문을
제기하면, 증인 기록이 스크립트가 무엇을 생성했는지 증명합니다.

---

### `retract` (철회)

체인 연결 철회 엔트리를 추가합니다. 위의 [⑫ cascade_check](#-cascade_check--retract)를 참조하세요.

---

## 워크플로우

### 워크플로우 1: 정직한 연구 논문

분류 결과에 대한 엔드-투-엔드 흐름.

```python
from measure_mirror import mm

LEDGER = "experiment_ledger.jsonl"

# ─── 1. 실험 전 ──────────────────────────────────────────────
mm.preregister(LEDGER, "bert_sentiment",
               metric="acc",
               min_n=500,
               baseline=0.5,
               pass_threshold=0.70,
               kill_condition="held-out에서 정확도 0.65 미만",
               kill_threshold={"metric": "acc",
                                "threshold": 0.65,
                                "direction": "below"},
               depends_on=["sst2_dataset_v3"])   # 데이터셋 의존성

# ─── 2. 실행 및 증인 기록 (선택사항이지만 권장) ───────────────
mm.witness(LEDGER, "bert_sentiment",
           ["python", "train_and_eval.py", "--dataset", "sst2"])

# ─── 3. 결과가 나온 후 ───────────────────────────────────────
findings = mm.full_audit(
    LEDGER, "bert_sentiment",
    reported_metric="acc", reported_acc=0.78, n=872,
    baseline=0.5,
    competing_name="LogReg 기준선", competing_acc=0.73,     # ②
    reward_terms=["cross_entropy"],                          # ③
    train_items=train_ids, test_items=test_ids,              # ④a 누수
    seed_results=[0.77, 0.78, 0.79],                         # ⑤
    claimed_scope=["sentiment"],                             # ⑥
    tested_scope=["sst2", "yelp_polarity"],
    min_detectable_effect=0.03,                              # ⑧
    check_multiplicity=True,                                 # ⑨
)
mm.report("BERT 감성분석", findings)

# ─── 4. 제출 전 앵커 ─────────────────────────────────────────
import subprocess
subprocess.run(["mm", "anchor", "--pretty"], check=True)
# → gist, s3, dropbox에 파이프하여 타임스탬프된 외부 증명 생성
```

---

### 워크플로우 2: pytest를 이용한 CI 게이트

```python
# conftest.py
pytest_plugins = ["measure_mirror.pytest_plugin"]

# test_eval_integrity.py
from measure_mirror import mm
from measure_mirror.pytest_plugin import assert_clean

LEDGER = "production_ledger.jsonl"

def test_model_integrity():
    findings = mm.audit(LEDGER, "prod_model_v3",
                        reported_metric="acc", reported_acc=0.78, n=1000)
    assert_clean(findings)   # FAIL findings → pytest 실패 → CI 빨간불

def test_ledger_chain():
    findings = mm.verify_chain(LEDGER)
    assert_clean(findings)

def test_mirror_health():
    findings = mm.calibrate()
    assert_clean(findings)
```

---

### 워크플로우 3: Resolved-Negative 결론 종결

```python
LEDGER = "oee_research_ledger.jsonl"

# 각 독립 각도를 실험 전 등록
angles = [
    ("oee_angle_wave",     "wave ODE — 연속 장"),
    ("oee_angle_bilinear", "bilinear 공진화"),
    ("oee_angle_alife",    "디지털 ALife (DISHTINY 스타일)"),
    ("oee_angle_folding",  "HP 단백질 폴딩 경관"),
    ("oee_angle_gs",       "Gray-Scott 반응-확산"),
]
for cid, desc in angles:
    mm.preregister(LEDGER, cid,
                   metric="oee_score", min_n=50, baseline=0.5, pass_threshold=0.0,
                   kill_condition=f"{desc}: OEE가 임계값 이상")

# ... 5개 실험 모두 실행, 모두 음성으로 수렴 ...

# 음성 종결 게이트
f = mm.negative_audit(LEDGER,
                      angles=[cid for cid, _ in angles],
                      min_angles=3,
                      conclusion_scope=["in_silico_자생_OEE"],
                      tested_scope=["digital_field", "alife_sim",
                                    "protein_HP", "reaction_diffusion"])
mm.report("OEE Resolved-Negative", [f])

# 최종 음성 결론 앵커
import subprocess, json
snap = json.loads(subprocess.check_output(["mm", "anchor", "--ledger", LEDGER]))
print(f"앵커됨: {snap['anchor_hash'][:12]}...")
```

---

### 워크플로우 4: 철회 및 cascade 정리

```python
LEDGER = "shared_lab_ledger.jsonl"

# ─── 기준 데이터셋에서 오염 발견 ─────────────────────────────
mm.retract(LEDGER, "imagenet_baseline_v1",
           reason="전처리 단계에서 훈련/테스트 12% 중복 발견")

# ─── 이제 오래된(STALE) 게재 결과 확인 ───────────────────────
published_claims = ["vit_paper_2023", "resnet_ablation", "downstream_nlp"]

for claim_id in published_claims:
    f = mm.cascade_check(LEDGER, claim_id)
    if f.level != "OK":
        print(f"⚠️  {claim_id}: {f.msg}")

# 출력:
# ⚠️  vit_paper_2023: Claim 'vit_paper_2023' is STALE: depends (transitively)
#     on retracted claim(s): 'imagenet_baseline_v1'
# ⚠️  downstream_nlp: Claim 'downstream_nlp' is STALE: ...
```

---

### 워크플로우 5: MCP 에이전트 연동

MCP 호환 AI(Claude Code, Cursor, Windsurf 등)가 모든 프로브를 대화 중에
직접 호출할 수 있습니다. 에이전트가 코드를 작성하지 않고도 주장을 감사할 수 있습니다.

```json
// .mcp.json
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

에이전트 대화 예시:
```
사용자: "내 모델이 n=200에서 SQuAD 87.3% 나왔어요. 믿을 수 있나요?"

에이전트: [mm_register, mm_audit 호출]
→ ⚠️  [④a small-sample CI] n=200, acc=0.873 → 95%CI [0.820, 0.915]
   기준선(0.5) 초과. OK.
→ ⚠️  [⑦ too-good] 기준선 대비 Δ=+0.373 — 의심스럽게 큼.
   조사: 데이터 누수? 보상 해킹?

[mm_grim_check 호출: reported_acc=0.873, n=200]
→ 🔴 FAIL — n=200에서 acc=0.873을 만족하는 정수 k 없음.
   round(175/200, 3) = 0.875 ≠ 0.873.

"87.3%은 n=200에서 GRIM 불가능한 값입니다. n 또는 acc 중 하나가 잘못 보고됐습니다."
```

---

## 빠른 참조표

| # | 함수 | 잡아내는 것 | `audit()` 자동 실행? |
|---|---|---|---|
| ① | `preregister`/`audit` | 지표 교체, min_n, pass 기준, 봉인 위변조 | ✅ |
| ① | `verify_chain` | 엔트리 삭제/삽입/위변조 | 수동 |
| ② | `baseline_fairness` | 허약/동점/역전된 기준선 | `full_audit` |
| ③ | `gaming_check` | 지표가 보상/손실에 직접 포함 | `full_audit` |
| ④a | Wilson CI (내부) | 소표본 우연 수준 결과 | ✅ |
| ④a | direction (내부) | 기준선보다 나쁨 (역신호) | ✅ |
| ④a | `leakage_check` | 훈련∩테스트 중복 | `full_audit` |
| ⑤ | `multiseed_check` | 불안정한 시드, 기준선이 범위 안 | `full_audit` |
| ⑥ | `scope_check` | 과대 일반화된 주장 | `full_audit` |
| ⑦ | `too_good_check` | 의심스럽게 큰 Δ | `full_audit` |
| ⑧ | `power_check` | n이 효과 탐지에 부족 | `full_audit` |
| ⑨ | `multiple_comparisons_check` | k>1 실험 Bonferroni 경보 | `full_audit` |
| ⑩ | `grim_check` | 산술 불가능 수치 | ✅ (FAIL만) |
| ⑪ | `falsifiability_check` | kill-condition 없음; 발화된 kill threshold | ✅ (사전등록 유효 시) |
| ⑫ | `cascade_check` | 철회된 주장 또는 오래된 의존성 | ✅ (WARN/FAIL만) |
| ⑬ | `negative_audit` | 성급한 음성 종결; 범위 초과 | `full_audit(angles=...)` |
| ⑭ | `judge_consistency_check` | LLM 판정자 뒤집기율 초과 (신뢰 불가 판정자) | 단독 |
| ⑮ | `judge_bias_check` | 판정자가 A 또는 B 위치를 체계적으로 선호 | 단독 |
| ⑯ | `inter_rater_agreement` | Cohen's κ 미달 (평가자 간 일치도 부족) | 단독 |
| ⑰ | `judge_score_sanity` | 판정자가 동일/근사 점수만 부여 (퇴화 분포) | 단독 |
| — | `anchor` | 원장 파일 완전 교체 | 수동 (게재 전) |
| — | `calibrate` | 거울 자체의 회귀 | 수동 (`witness` 전) |
| — | `witness` | 실행 기록: 무엇이 실행됐고, 언제, 출력 해시 | 수동 |
| — | `retract` | 철회 기록 생성 (체인 연결) | 수동 |

**코드베이스 전체 심각도 정책:**
- `FAIL` — 하드 스톱; 결과가 무효이거나 자기모순
- `WARN` — 주의 필요; 결과가 유효할 수 있지만 검토 필요
- `OK` — 이 항목은 통과; 이 차원은 깨끗함

---

*스스로의 프로젝트를 정직하게 죽이는 과정에서 만들어졌습니다. 제작자들이 자신들에게 먼저 적용했습니다.*  
*→ [개발 연대기](CHRONICLE.md)*
