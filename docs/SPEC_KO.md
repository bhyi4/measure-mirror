# MIRROR-SPEC v1.1 — 미러스택 원장 포맷 & 검증 프로토콜

> **⚠️ 이 문서는 참고용 한국어 번역이다. 규범 정본(normative)은 영어판
> [SPEC.md](SPEC.md)이며, 두 판이 다르면 영어판이 옳다.**

**Status: v1.0, 2026-07-02 비준(ratified).** §9에 따라 동결(frozen) — 규범
문장은 변경되지 않으며, 해명(clarification)은 정오표(errata)로 덧붙는다.
비준 기준: 클린룸 상호운용성 라운드 2회 통과 (이 문서만 받은 에이전트가
바이트 단위로 동일한 봉인 재현, 블라인드 벡터 판정 5/5, amendment를 포함한
유효 원장 생산을 달성).

이 문서는 미러스택 원장 포맷의 **규범 명세(normative specification)**다.
Python 패키지들(`measure-mirror`, `action-mirror`, `provenance-mirror`)은
이 명세의 **참조 구현(reference implementation)**이지, 명세의 정의가 아니다.
어떤 언어로든 이 문서에 부합하는 원장을 생산하거나 검증하는 시스템은 모두
미러스택 구현이다.

키워드 MUST, MUST NOT, SHOULD, SHOULD NOT, MAY는 RFC 2119에 기술된 대로
해석한다.

---

## 1. 목적과 정직한 범위

미러스택 원장은 정직을 **강제하지 않고, 증명 가능하게** 만든다. 보장하는 것:

- **무결성(Integrity)** — 과거 엔트리의 수정·삭제·삽입·재배열은 모두
  탐지 가능하다 (§6).
- **비소거성(Non-erasability)** — 음성 결과·철회·amendment는 덧붙기만 하고
  절대 제거되지 않는다; 원장이 없다는 사실 자체가 신호다.
- **반증가능성(Falsifiability)** — 주장은 결과가 존재하기 *전에* kill
  condition과 함께 봉인된다.
- **검증가능성(Verifiability)** — 위 보장 전부를 제3자가 원장 바이트만으로,
  의존성 제로로 확인할 수 있다.

보장하지 않는 것:

- **내용의 진실.** 봉인된 거짓말도 여전히 거짓말이다; 봉인이 증명하는 것은
  그 말이 *언제* 되었고 몰래 편집되지 않았다는 것뿐이다.
- **독립성.** 한 운영자의 통제 안에 있는 증인들은 독립 심판이 아니다.
  독립성은 사회적 속성이며 포맷 안에 만들어 넣을 수 없다.
- 비트코인 앵커링(§6.5)이 증명하는 것은 **소급조작 불가(no-backdating)뿐** —
  원장 헤드가 특정 블록 이전에 존재했다는 것 — 내용이 옳다는 것은 절대
  아니다.

## 2. 용어

| 용어 | 뜻 |
|---|---|
| **원장(ledger)** | append-only UTF-8 JSONL 파일; 한 줄에 JSON 객체("엔트리") 하나. |
| **엔트리(entry)** | 원장 안의 JSON 객체 하나. |
| **봉인(seal)** | 엔트리 내용을 결속하는 16자 hex 다이제스트 (§4). |
| **체인(chain)** | `prev_seal`을 통한 엔트리 간 연결 (§5). |
| **헤드(head)** | 원장 마지막 엔트리의 `seal`. |
| **앵커(anchor)** | 원장 상태의 원장-외부 스냅샷 (§6.4, §6.5). |
| **피어 증인(peer witness)** | 원장 A 안에서 원장 B의 헤드를 고정(pin)하는 엔트리 (§6.3). |

## 3. 원장 파일 포맷

1. 원장은 개행으로 구분된 JSON 객체들의 UTF-8 인코딩 파일(JSONL)이어야
   한다(MUST). 빈 줄(공백뿐인 줄 포함)은 검증기가 무시해야 한다(MUST).
   비어 있지 않은 줄이 JSON으로는 파싱되지만 객체가 아닌 경우(예: `42`,
   `[1,2]`)는 파싱 불가 JSON과 똑같이 원장을 malformed로 만든다
   (§6.1 2단계). UTF-8로 디코딩되지 않는 바이트도 마찬가지로 읽기 불가
   파일이 아니라 malformed 내용이다 (§6.1 2단계). 한 줄에 중복 키가 있으면
   마지막 출현이 이긴다(일반 파서 동작; 재계산되는 봉인이 달라지므로 여기에
   고정한다).
2. 엔트리는 오직 덧붙이기(append)만 해야 한다(MUST). 구현은 기존 줄을
   재작성·재배열·삭제해서는 안 된다(MUST NOT).
3. 모든 엔트리는 `seal`(문자열)과 `prev_seal`(문자열) 필드를 포함해야
   하고(MUST), ISO 8601 타임스탬프 필드(`ts`, 커맨드 증인의 경우
   `ts_start`/`ts_end`)를 포함해야 한다(SHOULD). 검증기는 `seal` 또는
   `prev_seal`이 없으면 빈 문자열로 취급해야 하고(MUST), 존재하지만
   문자열이 아닌 값은 십진/JSON 문자열 형태로 취급해야 한다(`42` → `"42"`);
   어느 쪽이든 이후 §6 비교가 자연스럽게 실패하며, 검증기는 크래시해서는
   안 된다(MUST NOT).
4. 타임스탬프는 명시적 `Z` 접미사가 붙은 UTC여야 한다(SHOULD). 검증기는
   타임존 접미사 없는 타임스탬프를 수용해야 한다(MUST) (레거시 엔트리가
   존재한다).
5. 원장 줄의 바이트가 §4의 정준(canonical) 직렬화일 필요는 없다 — 디스크
   상의 키 순서와 공백은 제약이 없다. 정준화하는 것은 봉인 *계산*뿐이다.
   생산자는 줄을 LF(`\n`)로 끝내야 한다(SHOULD); CRLF↔LF 변환을 포함한
   어떤 바이트 수준 변경도 L3 앵커(§6.4–§6.5)가 쓰는 파일 전체 해시를
   바꾼다는 점에 유의 — 이는 의도된 설계다.

## 4. 봉인 알고리즘 (규범)

엔트리 객체 `E`가 주어지면:

```
body       = E with the keys "seal" and "sig" removed
serialized = canonical-JSON(body)          # §4.1, byte-exact
seal       = lowercase hex SHA-256 of serialized (UTF-8 bytes), truncated to
             the first 16 characters
```

### 4.1 정준 JSON (규범, 바이트 단위 일치)

정준 직렬화는 Python의 `json.dumps(body, sort_keys=True, ensure_ascii=False)`
출력이다. 봉인은 바이트를 결속하므로, 교차 언어 구현은 이 바이트를 정확히
재현해야 한다(MUST). 풀어 쓰면:

1. **키 순서** — 객체 키를 유니코드 코드포인트 순으로 정렬, **모든 중첩
   수준에서 재귀적으로**.
2. **구분자** — 배열/객체 멤버 사이는 `", "`, 키와 값 사이는 `": "`
   (콤마와 콜론 뒤에 공백 하나, 앞에는 없음).
3. **문자열** — 비ASCII 문자는 raw UTF-8로 출력(`\uXXXX` 아님).
   필수 이스케이프 둘은 `\"`와 `\\`; 제어문자 U+0000–1F는 정의된 곳에서는
   `\b \f \n \r \t`, 그 외에는 `\u00XX`.
4. **숫자** — 정수는 소수점·지수 없이(`120`); 실수는 **같은 IEEE-754
   double로 왕복(round-trip)하는 가장 짧은 문자열**(`0.5`이지 절대
   `0.50`이 아님; `1`과 `1.0`은 *서로 다른 값이며 직렬화도 다르다*).
   최단-왕복 표기가 언어마다 다른 경우(예: 지수 표기 임계값: Python은
   `1e+16`, JavaScript는 `10000000000000000`), **Python의 `repr` 출력이
   규범이다**. 생산자는 비유한(non-finite) 실수를 피해야 하고
   (`NaN`/`Infinity`는 상호운용 가능한 JSON이 아니다)(SHOULD), 지수 표기가
   발동하는 크기대를 피해야 한다(SHOULD).
5. **리터럴** — `true`, `false`, `null`.

적합성 벡터 `valid_04_numbers.jsonl`이 이 바이트들을 고정한다(중첩 키,
실수, 정수, 유니코드, 불리언, null); 봉인이 이 벡터와 일치하는 구현은
정준화를 올바르게 한 것이다.

규칙:

1. 키 `seal`과 `sig`는 봉인 대상 body에서 제외해야 한다(MUST). `prev_seal`을
   포함한 그 외 모든 키는 포함해야 한다(MUST).
2. 직렬화는 §4.1을 바이트 단위로 정확히 따라야 한다(MUST).
3. 봉인은 전체 64자 소문자 hex 다이제스트여야 한다(MUST). *(v1.1 — v1.0은 16자
   절단이었다. 검증기는 정확히 16자인 봉인을 재계산 다이제스트의 앞 16자와
   비교해 수용해야 한다(MUST): 레거시 수용. 그 외 길이는 무효.)*
4. 엔트리는 추가로 Ed25519 서명을 실을 수 있다(MAY). `sig`는 **저장된 그대로의
   봉인 문자열의 UTF-8 바이트**(64-hex; v1.0 원장은 16-hex — raw 다이제스트가 아님)에 대한
   소문자-hex Ed25519 서명이고; `pubkey`는 소문자-hex 32바이트 raw 공개키다.
   `pubkey`는 봉인 대상 body의 일부이고(IS); `sig`는 아니다.
5. 봉인은 유일성을 보장하지 않는다: 동일한 엔트리는 동일한 봉인을 만든다
   (그리고 v1.0 레거시 64비트 절단은 원리적으로 충돌을 허용한다). 검증기는 봉인 중복을
   검사하지 않는다; 엔트리의 정체성은 봉인 값이 아니라 체인 위치(§5)다.

*봉인 폭에 관한 주(v1.1):* v1.0의 16자(64비트) 절단은 변조-증거 체크섬일
뿐이었다: **부정직한 봉인자**는 생일 탐색(~2^32 해시, GPU 수 분)으로 같은
절단 봉인을 공유하는 서로 다른 두 엔트리를 준비해 봉인 후 바꿔치기할 수
있다. v1.1은 전체 256비트 다이제스트로 봉인해 체인 층의 이 틈을 닫는다.
파일 전체 SHA-256(§6.4, §6.5)은 그대로 파일 층 커밋먼트다. 레거시 16자
봉인은 프리픽스로 검증된다 — 원래의(더 약한) 강도는 변하지 않는다.

## 5. 체인 규칙

1. 원장의 첫 엔트리는 `prev_seal`이 `"genesis"`와 같아야 하며(MUST),
   비교는 ASCII 대소문자 무시로 한다.
2. 이후의 모든 엔트리는 `prev_seal`이 바로 앞 엔트리의 `seal`과 같아야
   한다(MUST) (정확한 문자열 일치).
3. 없는 원장이나 빈 원장에 덧붙이는 생산자는 이전 봉인을 `"genesis"`로
   취급해야 한다(MUST).

## 6. 검증 레벨

### 6.1 L1 — 연결 검사(linkage check) (포맷 불문)

입력: 원장 경로. 출력: `(ok, message, entries)`.

적합한 L1 검증기는 다음을 순서대로 평가해야 한다(MUST):

1. 파일 읽기 불가 → FAIL (`entries = null`)
2. 비어 있지 않은 줄 중 JSON **객체**로 파싱되지 않는 것 → FAIL
   (`entries = null`; `42`나 `[1,2]` 같은 비객체 JSON은 malformed, §3.1)
3. 엔트리 0개 → FAIL (`entries = []`)
4. 첫 엔트리의 `prev_seal` ≠ `"genesis"` (대소문자 무시) → FAIL
5. `i > 0`인 엔트리 중 선언된 `prev_seal` ≠ 엔트리 `i−1`의 선언된 `seal`
   → FAIL, 처음 깨진 인덱스를 보고
6. 그 외 → OK, 엔트리 수와 헤드 봉인을 보고

인덱스는 0-기반 엔트리 위치(빈 줄 제외)이지, 파일 줄 번호가 아니다.
`seal`/`prev_seal` 필드 누락은 `""`로 읽혀(§3.3) 4–5단계에서 자연스럽게
실패한다. 4/5단계 실패 시 `entries`는 파싱된 리스트다(1–2단계만 `null`을
반환). 적합성(§8)은 OK/FAIL 판정과, FAIL의 경우 어느 단계가 발화했는지로
판단한다; 사람이 읽는 메시지 텍스트는 정보 제공용(informative)일 뿐이다.

L1은 **선언된** 봉인만 비교한다; 레코드 타입 지식을 요구해서는 안
되므로(MUST NOT), §3–§5를 따르는 어떤 원장에도 동작한다.

탐지하는 것: `seal` 기대값을 어긋나게 하는 모든 필드의 제자리 변조, 삭제,
삽입, 재배열, malformed 파일.
탐지하지 못하는 것: 일관된 파일 전체 교체 (내부 체인이 유효한 재작성 원장은
L1을 통과한다 — 이것은 L2/L3의 일이다).

### 6.2 L1+ — 봉인 재계산

재계산 검증기(예: `verify_chain`)는 추가로 각 엔트리의 봉인을 §4에 따라
재계산하고 불일치 시 FAIL해야 한다(SHOULD). L1+는 L1이 OK를 반환했을 때만
실행한다(깨졌거나 malformed인 체인은 이미 FAIL; 재계산이 더할 것이 없다).
이는 레코드 타입 지식이 필요 없다 — §4는 모든 타입에 균일하다. 첫 불일치를
보고하는 것으로 충분하다. 이는 선언된 체인은 일관되게 유지하면서 봉인된
내용을 바꾸는 편집을 잡는다.

### 6.3 L2 — 피어 증인 (교차 원장)

원장 A 안의 **peer_witness** 엔트리는 원장 B의 상태를 기록한다(스키마 §7).
A의 증인들을 현재의 B에 대해 검증할 때는 증인별로 다음을 검사해야 한다(MUST):

1. `len(B) ≥ peer_entries`, 아니면 **TRUNCATED** → FAIL
2. `B[peer_entries − 1].seal == peer_head_seal`, 아니면 **REWRITTEN** → FAIL
3. 해당 피어에 대한 증인 엔트리가 하나도 없음 → WARN (검증 불가)
4. 고정된 헤드가 모두 일관됨 → OK

이 위치-고정(position-pinned) 검사는 원장 전체 교체와 절단(truncation)을
탐지한다 — L1이 볼 수 없는 공격들이다. 그러면 역사를 지우려면 **모든**
증인 원장을 동시에 재작성해야 한다.

### 6.4 L3a — 로컬 앵커

**anchor** 아티팩트(스키마 §7)는 원장을 스냅샷한다. 검증:

```
if SHA256(ledger bytes) == anchor_hash            → "intact"   (OK)
elif len(ledger) ≥ entry_count
     and ledger[entry_count − 1].seal == head_seal → "extended" (OK, append-only)
else                                               → "REPLACED?" (FAIL)
```

앵커는 원장 바깥에 저장해야 한다(MUST) (별도 파일, 외부 서비스).

### 6.5 L3b — 비트코인 앵커 (OpenTimestamps)

원장 해시와 헤드를 나열한 매니페스트(스키마 §7)를 OTS로 스탬프한다.
검증은 `.ots` 증명에서 비트코인 블록 높이와 머클 루트를 추출하고, 그 머클
루트를 **독립적인 공개 블록 익스플로러**(증명자 자신의 노드가 아님)와
대조해야 한다(MUST). 일치 → 매니페스트, 따라서 원장 헤드들이 그 블록의
시각 이전에 존재했다. 범위: 소급조작 불가(no-backdating)만 (§1).

### 6.6 스택 오케스트레이션

풀스택 검증(`verify_all`)은 다음을 실행해야 한다(SHOULD): 각 원장에
L1/L1+ → 각 앵커에 L3a → 각 증인 관계에 L2. 판정은 어떤 검사도 FAIL하지
않았을 때, 그리고 그때에만(iff) **ALL OK**다; WARN(예: 증인 없음)은
보고해야 하지만(MUST) 판정을 깨지 않는다.

## 7. 레코드 타입

모든 타입은 §3–§5(`seal`, `prev_seal`, 타임스탬프)를 공유한다. (opt) 표시
필드는 선택이다. 검증기는 모르는 추가 필드를 무시해야 한다(MUST)
(전방 호환성); 생산자는 예약된 이름에 새 의미를 발명해서는 안 된다
(SHOULD NOT).

### 7.1 원장 상주 타입

**preregister** — 결과가 존재하기 전에 주장을 봉인. 식별은 형태(shape)로
한다(`claim_id` + `metric` + `pass_threshold` 보유), `_type`으로 하지
않는다: 레거시 엔트리에는 `_type` 필드가 없다. 생산자는
`_type: "preregister"`를 추가할 수 있다(MAY); 검증기와 감사 도구는 두 형태
모두 수용해야 한다(MUST).
`ts, claim_id, metric, min_n, baseline, pass_threshold` + (opt)
`kill_condition`(사람이 읽는 반증 기준), `kill_threshold`
(객체; 예약 키 `metric`, `threshold`, `direction`:"below"|"above" —
그 외 키는 구현 정의), `depends_on`(claim_id 리스트, 철회 cascade를
가능케 함), `metric_range`([lo,hi] 또는 "unbounded"), `chance`(float).
`kill_condition`/`kill_threshold`는 함께 존재해야 한다(SHOULD); 둘 다 없는
사전등록은 반증 불가능하며 감사 도구가 플래그해야 한다(SHOULD).

**amendment** — **최상위 `amends_seal`**(수정 대상 엔트리의 봉인)을 실은
preregister 형태의 엔트리 — 그것이 규범적이며 유일한 식별 마커다
(`_type`은, 있다면, `"preregister"` 또는 `"amendment"`일 수 있다(MAY);
검증기는 이에 의존해서는 안 된다(MUST NOT)). 실제 원장에는 레거시 관례가
둘 더 존재하며 허용해야 한다(MUST) (생산할 필요는 없다):
`kill_threshold` 안에 중복된 `amends_seal`과 `change` 요약을 넣는 것, 그리고
`metric`에 `"[AMENDMENT to seal …]"` 접두사를 붙이는 것. amendment는 kill
condition을 *보이게* 바꾼다; 체인이 금지하는 것은 침묵 편집이다.

**retraction** — `_type: "retraction"`, `ts, claim_id, reason`. 주장이
반증/철회되었음을 표시. 덧붙여야 하며(MUST), 삭제의 대용이 되어서는 안
된다. `claim_id`가 이전 사전등록과 일치하는지는 감사 계층의 관심사
(certificate/반증가능성 도구)로, L1/L1+ 범위 밖이다.

**witness** (커맨드 실행) — `_type: "witness"`, `ts_start, ts_end,
claim_id, command`(argv 리스트), `returncode`,
`run_status`:"ok"|"timeout"|"error", `output_hash` =
`"{returncode}\n{stdout}\n{stderr}"`에 대한 SHA-256 전체 64 hex *(v1.0: 첫 16자 — 레거시 수용)*.

**action** — `_type: "action"`, `ts, agent, action` + (opt) `target`(경로,
claim_id, 티켓…; 행동을 주장에 결속하려면 `target = <claim_id>`로 설정),
`content_hash`(아티팩트 바이트의 64-hex SHA-256; v1.0: 16-hex — 레거시 수용), `payload`(자유 JSON —
**검증기에게 불투명(opaque)**), `pubkey` + `sig`(§4 규칙 4).

**peer_witness** — `_type: "peer_witness"`, `ts, peer, peer_entries,
peer_head_seal, peer_anchor`(증인 시점 피어 파일의 16-hex SHA-256; 포렌식
전용 — 정당한 append도 이 값을 바꾸므로, 검증은 위치-고정 헤드를 쓴다,
§6.3).

**verdict** (출처) — `_type: "verdict"`, `ts, file_hash`(전체 64-hex),
`origin`(string|null), `verdict`는 우선순위
`TAMPERED > SYNTHETIC > CONFLICTING > AUTHENTIC-SIGNED > UNVERIFIED`
(UNVERIFIED = "쓸 만한 신호 없음"으로, 위조의 증거가 명시적으로 아니다),
`signals`(프로브 id → 결과 매핑 객체; 프로브 id ①…⑤ =
c2pa-manifest, generator-meta, ai-watermark, tamper-anchor,
format-integrity).

**distribution** — `_type: "distribution"`, `ts, doc_id, recipient,
clean_hash, marked_hash`(유출 추적용 지문 찍힌 사본).

### 7.2 원장 외부 아티팩트

**anchor** — `_type: "anchor"`, `ts, ledger_path, entry_count, head_seal`
(원장이 없으면 "empty"), `anchor_hash`(원장 바이트의 전체 SHA-256),
`chain_ok`(bool). 체인에 연결되지 않음; 외부에 저장.

**ots_anchor_manifest** — `_type: "ots_anchor_manifest"`, `ts, purpose,
ledger_count, ledgers`(`{ledger, path, bytes, sha256, head_seal}` 리스트),
바이너리 `.ots` 증명이 동반됨.

**certificate** — `_type: "certificate"`, `ts, claim_id, verdict`
(`REJECTED`|`UNVERIFIED`|`CERTIFIED-WITH-WARNINGS`|`CERTIFIED`) + (opt)
`prereg_seal, prereg_seal_ok, cascade, chain_ok, ledger_entries, anchor_hash,
findings {ok, warn, fail}`. 증명(attestation) 아티팩트; 원장에는 덧붙이지
않는다.

## 8. 적합성

**생산자(Producer)** 적합성: §3–§5와 §7에 따라 엔트리를 배출한다; 역사를
절대 재작성하지 않는다; amendment와 retraction을 append로 기록한다.

**검증기(Verifier)** 적합성: 최소 L1(§6.1)을 정확한 평가 순서로 구현한다;
풀스택 검증기는 §6.2–§6.6을 구현한다. 검증기는 SHA-256, JSON, 파일 I/O
외의 의존성이 없어야 한다(MUST) (L3b는 추가로 OTS 파서와 공개 블록
익스플로러가 필요하다).

**테스트 벡터:** `spec/vectors/`에 기대 판정이 딸린 유효/무효 원장들이
있다. 벡터는 이 명세와 함께 배포되는 동반 아티팩트(같은 저장소)이지, 규범
텍스트의 일부가 아니다: 텍스트만으로 구현에 충분하며, 벡터 실행은 적합성을
*주장*할 때만 요구된다. 구현은 모든 기대 판정을 재현할 때, 그리고 그때에만
(iff) 적합하다. (시드 스위트: `tests/test_linkage_check.py`,
mirror-stack-mcp `tests/test_linkage_conformance.py`.)

## 9. 버전 관리

v1.0은 비준되면 **동결(frozen)**된다: 여기의 규범 문장은 변경되지 않는다.
해명은 정오표(errata)로 덧붙일 수 있다. 파괴적 변경(예: 사전등록의 `_type`
의무화, UTC 타임스탬프 의무화)은 미래의 v2에 속한다. v1에서 유효한 원장은
영원히 검증 가능하다 — 옛 기록의 검증가능성이 포맷의 우아함보다 우선한다.

## 10. 알려진 레거시 편차 (규범적 수용)

검증기는 다음을 경고 없이 수용해야 한다(MUST):

1. `_type`이 없는 `preregister`/`amendment` 엔트리 (§7.1).
2. 타임존 접미사 없는 타임스탬프 (§3.4).
3. 아무 대소문자로나 쓰인 `genesis` (§5.1).
4. 이질적인 `kill_threshold`/`payload` 형태 (예약 키 밖은 불투명).

## 11. 개정(Amendments) (§9에 따라 덧붙임; 위의 v1.0 규범 본문은 불변)

### A1 — `preregister` 접지 선언 선택 필드 (2026-07-08)

`preregister` 타입(§7.1)에 **선택(optional)** 생산자 필드 두 개를 추가한다:

- `anchor_basis` (문자열, 선택) — 주장의 양성대조(positive-control) 앵커의 근거.
  권장 어휘: `"dynamics-measured"` | `"structural-argument"`.
- `threshold_source` (문자열, 선택) — 통과/킬 문턱의 출처.
  권장 어휘: `"external-fixed"` | `"observed-distribution"`.

근거: 상호 접지(mutual-grounding) 아크가 봉인한 두 실패 법칙 — 정적 "구조적으로
보장됨" 논증에 앵커된 양성대조는 기질 자신의 동역학에 의해 반증될 수 있고,
관측 분포에서 재유도되는 문턱은 자기캘리브레이션(공격자가 끌어내릴 수 있음)이다.
둘을 봉인 시점에 선언하면 연산을 쓰기 전에 검사 가능해진다; 감사 도구
(measure-mirror 프로브 ㉑/㉒)가 필드를 되읽어 자동으로 평가한다.

호환성: 비파괴적. 검증기는 이미 알 수 없는 추가 필드를 무시해야 한다(MUST, §7);
L1/L1+ 의미론은 건드리지 않는다(필드는 다른 엔트리 바이트처럼 봉인된다).
소비는 감사 계층의 관심사다. 생산자는 두 필드 모두 생략할 수 있다(MAY);
포맷 수준에서 어휘를 강제하지 않는다(감사 도구는 미인식 값을 fail-closed
권고로 다룬다).

### A2 — `preregister` 앵커 규율 + 교락 선택 필드 (2026-07-09)

`preregister` 타입(§7.1)에 **선택(optional)** 생산자 필드 세 개를 추가한다:

- `anchor_cell` (문자열, 선택) — 양성대조 앵커 셀의 위치.
  권장 어휘: `"deep-regime"` | `"threshold-cell"`.
- `anchor_line_source` (문자열, 선택) — 앵커선의 출처.
  권장 어휘: `"separator-aligned"` | `"copied-from-other-cell"`.
- `known_confounds` (문자열 배열, 선택) — 결과 관측 **전에** 선언한 교락.

근거: `anchor_cell`·`anchor_line_source`는 A1의 `anchor_basis`와 함께 앵커 규율
3종을 완성한다 — 봉인된 `anchor-reproduction-failure` 세 아형(다른 셀에서 복사한
앵커선·문턱에 앉은 앵커 셀·정적 구조 보장 논증이 모두 재현 실패). 감사 도구
(프로브 ㉔/㉕)가 앞의 둘을 자동 평가한다. `known_confounds`는 결과 전 선언한
교락을 기록한다 — 사전 선언된 교락은 후속 귀속 사이클을 정당화하지만 사후 발견은
그렇지 않다; 감사는 이를 INFO(판정이 아니라 선언)로 표면화한다.

호환성: A1과 동일 — 비파괴적, 검증기는 미지 필드 무시(§7), L1/L1+ 불변,
소비는 감사 계층, 생산자 생략 가능(MAY), 포맷 수준 어휘 미강제.

---

*참조 구현:* `measure-mirror`(정본 `linkage_check`), `action-mirror`,
`provenance-mirror`, `mirror-stack-mcp`(MCP 노출).
*이 명세가 진실의 원천(source of truth)이다; v1.0 비준 이후 코드와 명세가
다르면, 틀린 것은 코드다.*
