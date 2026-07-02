# anti_signal — anti-signal

> On a large sample the model performs below chance — a real but negative signal masked by cherry-picked wins.

- **증상(시그니처)**: 대표본 전체 평가에서 chance 미만. 소표본 승리 몇 건 뒤에 숨은 음의 신호.
- **기전**: 작은 표본의 우연한 성공만 보고하면 전체 분포가 chance 아래인 것을 놓친다. below-chance는 단순 무능이 아니라 체계적 오정렬(라벨 반전·프레이밍 오류 등)일 수 있어 방향까지 봐야 한다.
- **실사례**: ZERO full_eval에서 0.385로 chance(0.5) 미만. 대표본에서 anti-signal. 출처: db/curated/gaming_patterns.json — ["ZERO full_eval 0.385 < 0.5"]
- **탐지법**: ④a로 방향(direction) 검사 — baseline 배제만 보고 방향을 누락하지 말 것. 전체 표본 평가 강제 후 chance 대비 부호 확인. self-catch: 측정거울 MVP가 0.385를 'OK'로 판정했다 방향 누락을 자가적발한 사례 참조.
- **오적용 주의**: 소표본에서의 below-chance는 그냥 잡음일 수 있다(small_n 참조). 대표본에서 CI가 chance 아래로 분리될 때만 anti-signal로 확정. 또한 이진 태스크가 아니면 chance 기준선을 재정의해야 한다.
