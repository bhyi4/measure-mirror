# augmentation_reinjects_holdout — 증강이 홀드아웃을 재주입

> Train-time data augmentation maps training items onto held-out classes, silently re-injecting "unseen" compositions into training.

- **증상(시그니처)**: 조합/구성 일반화(compositional holdout) 점수가 기대보다 높다. held-out을 누출 여부로 분해하면 정확도가 누출 강도 순으로 정렬된다(암기>간접>clean). 홀드아웃 정의가 "표기" 기준인데 증강 변환이 표기를 바꾼다(순서 뒤집기·대칭·역라벨).
- **기전**: 홀드아웃은 원본 데이터 기준으로 떼지만, 증강은 **훈련 시점에** 항목을 변환한다. 변환의 상(image)이 홀드아웃 집합과 교차하면 — 예: 역할반전 증강 (a,b,r)→(b,a,INV r) — held 조합이 훈련 라벨로 그대로 들어간다. 같은 물리 인스턴스의 거울(같은 두 물체, 역순)은 문자 그대로 동일 임베딩쌍이라 순수 암기 경로가 열린다. 파생형: 홀드아웃 단위가 표기(ordered triple)인데 과제 의미는 대칭(하나의 물리적 사실이 두 표기)이면 증강 없이도 "미견" 주장 자체가 과대.
- **실사례**: 옹알이 A1 관계 게이트(2026-07-20 seal cbadf9d1, held 74.5% PASS) — split은 (cls_a,cls_b,pred) 삼중항만 홀드아웃, hardneg 역할반전 증강이 (b,a,INV r) 훈련쌍을 뒤집어 held 조합을 재주입. 사후 분해(07-21): held 10,169쌍 중 인스턴스거울 24%(acc 93.1%=암기)·조합거울 39%(76.2%)·clean 37%(60.4%). 거울닫힘 재측정 A1-R = 62.6%(3시드) — 질적 PASS 생존·수치 ~12%p 부풀림. 원장: prereg 91869901ae414b75 → amendment d9c8c6f3f2f94198. 같은 구조가 D0 기질에도 존재(held 60.9% 오염)했으나 분해 결과 그쪽 마진은 누출 무관(clean 마진이 더 큼) — **같은 오염이 지표를 부풀릴 수도(A1), 안 부풀릴 수도(D0), 심지어 대조 베이스라인을 부풀려 거짓 KILL을 만들 수도(D1 재심 중)** 있다. 출처: db/curated/contamination.jsonl — augmentation_reinjects_holdout · 원장 seal cbadf9d1.
- **탐지법**: ①홀드아웃 직후 기계 leak-check: 증강 변환의 상(image)과 held 집합의 교집합=0 assert(인스턴스 키에 클래스 포함 — 좌표만 매칭하면 타 이미지 우연충돌 오탐). ②held를 "거울이 train에 있나"로 분해해 정확도 기울기 확인(정렬되면 누출 실재). ③홀드아웃 단위를 변환-닫힘(orbit)으로 정의: (a,b,r)을 떼면 mirror도 동반 홀드아웃.
- **오적용 주의**: 증강 자체는 죄가 없다(과제 압력 장치·거울닫힘 후엔 안전). 누출 발견=자동 철회도 아니다 — A1은 분해·재측정 후 질적 결론이 생존했고 수치만 교정됐다. 반대로 "clean 부분 정확도가 높으니 괜찮다"로 재측정을 생략하는 것도 금물(공정 베이스라인·floor도 clean 기준으로 다시 재야 함). 대칭 과제가 아닌 증강(크롭·색 지터 등)은 홀드아웃과 교차할 상이 없어 해당 없음.
