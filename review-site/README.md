# 라벨 검수 사이트

휴대폰에서 라벨을 넘기며 검수하는 한 페이지 웹앱. 왼쪽으로 밀면 맞음, 오른쪽으로 밀면 틀림.

- 현재 운영본(claude.ai 아티팩트, 비공개): https://claude.ai/artifact/JNNfWt4N3JSypS5yUDRxZB
- 소스: `index.src.html` (HTML·CSS·JS 한 파일, `__DATA__` 자리에 데이터가 들어감)
- 빌드: `python3 review-site/build.py` → `review-site/dist/index.html`

## 화면

| 탭 | 내용 |
|---|---|
| 검수 | 이름·학번 입력 후 카드 스와이프. 맞음/틀림/보류, 되돌리기 |
| 틀림 고치기 | 틀림·보류로 넘긴 건에 맞는 도구를 고름 |
| 시험셋 | v1 시험셋 243건을 라벨 없이 3명이 각자 처음부터 |
| 현황 | 진행률, 골드 라벨 수, 시험셋 일치도(Fleiss·Cohen κ), 검수 신뢰도(편집자만), 내보내기 |
| 기준 | 경계 규칙, 도구 18개 설명과 예시 |

**골드 라벨**은 사람이 맞다고 했거나 고친 라벨, 그리고 시험셋에서 2명 이상 같은 답을 낸 것만이다 (모델 라벨은 골드가 아님).

## 데이터

범위는 일상 요청만이다(2026-11-14, Dev·Ops 문장과 `ssh`·`server_status` 클래스 제외). 예시 문장은 지금 데이터에 남은 seed·학습 문장만 쓰고, 2개가 안 되는 클래스는 `build.py`의 `MANUAL`에 직접 쓴 문장으로 채운다(v2 학습 문장은 모두 검수 카드로 나가므로 예시로 쓰면 정답이 샌다).

| 들어가는 것 | 출처 | 공개 저장소에 |
|---|---|---|
| v1 Opus 라벨 2,126건 | `dataset/tool-choice-v1.labeled.jsonl` | 있음 |
| v1 시험셋 243건(라벨 없음) | `dataset/tool-choice-v1.gold.jsonl` | 있음 |
| v2 검수용 361건(심은 오답 48 + 대조군 48 포함) | 프로젝트 파일 `tool-call-grader/review-v2add/review-items.jsonl` | **없음, 올리지 말 것** |
| 정답표 96건 | 프로젝트 파일 `tool-call-grader/review-v2add/KEY-planted.jsonl` | **없음, 올리지 말 것** |
| 클래스 18개, 규칙, 예시 | `tools-v2.json`, `labeling-guide*.md`, `seed-examples*.jsonl` | 있음 |

- 배정: v1은 우선순위(확신 낮은 것부터) 순서로 A/B/C에 번갈아. v2의 `audience: all` 96건은 3명 모두, 나머지는 번갈아. 1인 약 893건. v2 카드는 v1 순서 사이에 무작위로 섞임(seed 20261113).
- `dist/index.html`에는 심은 오답 라벨이 표시 없이 들어간다. 그래서 커밋하지 않는다. 저장소의 `dataset/labels/labels-v2add.jsonl`(깨끗한 라벨)과 비교하면 심은 건이 드러나므로, 배포본은 검수자만 보게 비공개로 둔다.

## 저장소(백엔드)

claude.ai 아티팩트 런타임의 공유 문서 DB(`await window.claude.use("db")`)와 `user`, `downloads` 기능을 쓴다. 다른 곳에 배포하려면 아래 문서 구조를 그대로 주는 저장소 어댑터로 바꾸면 된다(`boot()`, `write()`, `remove()`, `save()` 네 곳).

| 경로 | 내용 | 읽기/쓰기 |
|---|---|---|
| `rv_A`, `rv_B`, `rv_C` / `{id}` | 검수 결과 `{v: ok\|bad\|hold, first?, also?, nc?, memo, issue, uid, at, ms, from?}` | 검수자 |
| `gold_A`, `gold_B`, `gold_C` / `{id}` | 시험셋 라벨 `{first, also, nc, hold, memo, uid, at}` | 검수자 |
| `config/reviewers` | `{A, B, C, A_sid, B_sid, C_sid}` 이름·학번 | 검수자 |
| `data/answerkey/items/planted` | 정답표 `{ids: {id: {p: 1이면 심은 오답, t: 정답 first, nc}}}` | **편집자·소유자만** |

- `first`, `also`는 클래스 인덱스(`tools-v2.json` 순서, 0~17).
- 정답표는 빌드에 넣지 않고 배포 후 DB에 따로 넣는다(아티팩트에서는 규칙 `{path: "data/answerkey", read: "admin", write: "admin"}`). `KEY-planted.jsonl`에서 만드는 법:
  ```python
  ids = {x["id"]: {"p": 0 if x["label_is_correct"] else 1, "t": x["correct"]["first"], "nc": x["correct"]["needs_confirm"]} for x in rows}
  ```
- 검수자에게 정답표 읽기 권한을 주면 안 된다. 아티팩트에서는 Editor 권한이 정답표를 읽으므로 검수자는 Contributor로 초대한다.

## 검수 신뢰도

정답을 아는 96건(심은 오답 48 + 대조군 48)만으로 계산한다. 양성 = 라벨이 맞음.

- TP 맞는 라벨을 맞음 · TN 심은 오답을 틀림 · FP 심은 오답을 맞음 · FN 맞는 라벨을 틀림 (보류 제외)
- 민감도 TP/(TP+FN), 특이도 TN/(TN+FP), 정밀도 TP/(TP+FP), 정확도 (TP+TN)/전체
- 현황 탭의 "신뢰도 JSON"으로 검수자별·전체 값과 시험셋 κ를 받는다.

## 내보내기 파일

| 파일 | 내용 |
|---|---|
| `gold-labels-v1.jsonl` | 골드 라벨만(`source`: human_confirmed / human_corrected / human_majority). 심은 오답을 맞음으로 넘긴 건은 빠짐(편집자로 열어야 걸러짐) |
| `review-log-v1.jsonl` | 검수 기록 전체(보여 준 라벨, 판정, 사람이 고친 값) |
| `testset-human-v1.jsonl` | 시험셋 3명 라벨과 다수결 |
| `review-reliability-v1.json` | TP/TN/FP/FN, 민감도·특이도·정밀도·정확도, κ |
| `holds-v1.csv` | 보류 목록(회의 안건) |
