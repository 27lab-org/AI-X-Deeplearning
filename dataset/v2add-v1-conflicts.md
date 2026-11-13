# v1 라벨과 v2 기준이 충돌하는 후보

v1 파일은 고치지 않았다. 20개 클래스로 함께 학습하려면 아래를 사람이 보고 정한다.

## 같은 문장인데 v2 의도가 다른 것 (v2 추가분에서는 제외함)

- `tc-386952df` 알람 7시에 맞춰줘 : v1 none → v2 cronjob
- `tc-351b178f` 타이머 10분 : v1 none → v2 cronjob
- `tc-07b1f719` Set an alarm for 7 : v1 none → v2 cronjob

## v1에서 none인데 규칙 15(cronjob)에 걸릴 수 있는 것

- `tc-07b1f719` (train) Set an alarm for 7
- `tc-351b178f` (train) 타이머 10분
- `tc-386952df` (train) 알람 7시에 맞춰줘
- `tc-813c77bb` (train) alarm 7시
- `tc-e001c2fa` (train) 리마인드 문자 보내줘
