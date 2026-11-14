# Opus 5.5 라벨러 지시문 (2026-10-21, 배치 20개에 동일하게 사용)

> 기록용: 라벨을 달 당시(10개 클래스)의 지시문이다. 2026-11-14에 Dev·Ops 문장과 `server_status`·`ssh` 클래스를 뺐으므로, 다시 라벨을 달 때는 현재 tools 파일과 기준서의 클래스 목록을 쓴다.

너는 Hermes 에이전트의 도구 선택을 채점하기 위한 정답 라벨을 다는 라벨러다. 아래 파일을 먼저 읽고 기준을 엄격히 따른다. 모든 경로는 /mnt/project-files/plans/tool-call-grader/ 아래다.

읽을 파일
1. tools.json — 도구 10개 정의(when / not_when / Hermes 호출 형태)
2. labeling-guide.md — 라벨 기준서. 특히 1~3절(무엇을 라벨하나, Hermes 기준, 경계 규칙 12개)
3. seed-examples.jsonl — 라벨 예시 45건
4. dataset/labels/opus/batch-NN.input.jsonl — 라벨할 입력(한 줄에 한 건: id, context=이전 대화(없으면 ""), request=사용자 요청)

절대 열지 말 것(생성 의도가 들어 있어 라벨이 오염된다): gen/ 폴더 전체, dataset/tool-choice-v1.*.jsonl, dataset/labeling-input.jsonl, dataset/stats.md, dataset/review-sheet*.xlsx, dataset/labels/opus/ 의 다른 batch 파일, prompts.md, 상위 폴더의 tool-call-grader.md. 웹 검색·서버 접속 등 다른 도구도 쓰지 않는다.

출력: dataset/labels/opus/batch-NN.jsonl — 입력과 같은 순서로, 한 건당 JSON 한 줄:
{"id": "...", "first": "<10개 중 하나>", "also_ok": [...], "sequence": [...], "needs_confirm": true|false, "rule": <근거가 된 경계 규칙 번호(정수) 또는 null>, "confidence": <0~1 소수>, "note": "<애매하면 한 줄, 아니면 빈 문자열>"}

10개 클래스: weather, calendar_list, calendar_create, web_search, map_search, fx, mail_read, server_status, ssh, none

라벨 규칙 요약(기준서 원문이 우선)
- first = Hermes가 처음 불러야 할 도구의 기능 클래스. 단어가 아니라 필요한 행동으로 고른다.
- also_ok = 첫 도구로 이것도 정답으로 인정할 것. 없으면 [].
- sequence = 끝까지 필요한 도구 순서. none이면 [].
- 일정 등록·변경·취소 요청은 first=calendar_create, also_ok=["calendar_list"], sequence=["calendar_list","calendar_create"].
- needs_confirm = 재시작·삭제·설치·설정 변경·일정 삭제처럼 실행 전 사용자 확인이 필요하면 true, 조회만이면 false.
- 되묻기가 필요한 것, 못 하는 일(메일 발송, 과거 날씨 등은 기준서 참고), 일반 지식·잡담, 사내 정보 = none.
- context가 있으면 반드시 반영한다. 앞 대화에 대상이 있으면 그걸 쓰고, 없으면 none(되묻기).
- 판단이 갈리면 confidence를 0.7 아래로 낮추고 note에 이유를 한 줄 쓴다.

작업 방식
1. 기준 파일 3개와 입력 파일을 읽는다.
2. 모든 건에 라벨을 단다. 한 건도 빼지 않고, 입력 순서를 지킨다.
3. Write 도구로 출력 파일을 한 번에 쓴다(JSONL, 마지막 줄 끝에 개행).
4. Bash(python3)로 검증한다: 출력 줄 수가 입력과 같은지, id 집합이 같은지, first가 10개 중 하나인지, 모든 줄이 JSON으로 파싱되는지, also_ok·sequence가 리스트인지. 틀리면 고친 뒤 다시 검증한다.
5. 최종 보고는 3줄 이내: 총 건수, confidence<0.7 건수, 클래스별 first 개수. 개별 라벨 내용은 보고에 쓰지 않는다.
