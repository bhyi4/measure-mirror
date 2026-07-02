# empty_space_trivial — 빈공간 자명 baseline

> "Success" that is the trivial consequence of a sparse or mostly-empty output space.

- **증상(시그니처)**: 높아 보이는 성공률이 실은 희소/빈공간에서 "아무것도 안 함"이 정답이라 자명하게 달성됨.
- **기전**: 대부분이 빈칸/음성인 공간에서는 전부 빈칸으로 예측해도 정확도가 높다. 지표가 클래스 불균형을 보정하지 않으면 자명 baseline이 만드는 착시를 실력으로 오인한다.
- **실사례**: 5-C 세포 메타인지가 빈공간 87%에서 '성공'으로 보였으나 자명 baseline의 산물(FAIL). 출처: db/curated/gaming_patterns.json — ["5-C 메타인지 빈공간 87%"]
- **탐지법**: ③ fair-baseline에 "전부 다수클래스/빈칸" 자명 baseline을 넣어 격차 확인. 불균형 지표(precision/recall·balanced acc)로 재계산. self-catch ⑦로 "이렇게 쉽게 87%?"를 의심.
- **오적용 주의**: 희소 공간에서도 자명 baseline을 유의하게 상회하면 실력이다. "빈공간이라 무효"가 아니라 "자명 baseline 대비 초과분이 있는가"가 기준. 초과분이 있으면 이 라벨을 붙이지 말 것.
