# overclaim — 증거 너머 과대선언

> Declaring a universal conclusion from a stage/scope the experiment never actually reached.

- **증상(시그니처)**: 미도달 단계인데 결론을 보편으로 선언. 검증범위와 결론범위가 불일치("이 조건서 음성"→"보편적으로 음성").
- **기전**: 실제로 통과한 단계보다 넓게 주장하면, 미측정 영역을 측정된 것처럼 위장하게 된다. 특히 음성 결론을 "언제나/보편"으로 확장하면 자기모순(미구현·미도달인데 부재 선언)이 생긴다.
- **실사례**: latent_oee가 S1'~S3' 미도달인데 OEE 음성을 선언(자기모순). trilemma의 비보편 결과를 보편으로 선언. 출처: db/curated/gaming_patterns.json — ["latent_oee S1'~S3' 미도달 OEE음성 선언", "trilemma 비보편을 보편으로"]
- **탐지법**: ⑥ mm_verify(claimed_scope, tested_scope) — 주장범위≤검증범위 강제. mm_negative_audit로 음성결론의 각도 등록·범위 초과 검출. "닫은 것/안 닫은 것"을 명시.
- **오적용 주의**: 여러 독립 각도가 수렴한 강한 음성은 정당하게 넓은 결론을 지지할 수 있다(성급종결과 구분). overclaim은 *증거가 도달하지 못한* 범위로 확장할 때만. 검증범위 안의 결론은 과대가 아니다.
