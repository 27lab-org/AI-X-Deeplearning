# 라벨 기준서 v2 추가분: Hermes 기본 툴 클래스 (2026-11-12)

[labeling-guide.md](labeling-guide.md) (1~3절, 경계 규칙 1~12)은 그대로 쓴다. 이 문서는 **Nous Hermes Agent에 기본으로 들어 있는 툴**을 기준으로 클래스 10개를 더하고, 그 경계 규칙 13~23을 정한다. 도구 정의는 [tools-v2.json](tools-v2.json), 예시는 [seed-examples-v2.jsonl](seed-examples-v2.jsonl).

> **범위(2026-11-14, Daniel):** 이 데이터셋은 일상 요청만 다룬다. Dev·Ops 관련(서버, ssh, 인프라, 코딩, 배포, ML 등)은 문장과 클래스 모두 뺐다. `server_status`·`ssh` 클래스는 없다.

## 1. 클래스 18개
기존 8개: `weather` `calendar_list` `calendar_create` `web_search` `map_search` `fx` `mail_read` `none`

새 10개 (괄호는 Hermes 네이티브 툴):

| 클래스 | 툴 | 언제 |
|---|---|---|
| `memory` | memory | 사실·선호를 다음 대화에도 쓰게 저장·수정·삭제·조회 |
| `session_search` | session_search | 이전 대화 내용 찾기 |
| `cronjob` | cronjob_manage | 알람·타이머·리마인더·반복 실행 예약과 그 관리 |
| `file` | read_file, write_file, patch, search_files | Hermes가 도는 머신의 파일 읽기·쓰기·검색 |
| `web_extract` | web_extract | URL이 주어진 페이지 읽기 |
| `browser` | browser_exec 등 | 클릭·입력·로그인이 필요한 페이지 조작 |
| `execute_code` | execute_code | 정확한 계산·데이터 집계 |
| `image_generate` | image_generate | 이미지 생성·편집 |
| `vision_analyze` | vision_analyze | 주어진 이미지 분석 |
| `text_to_speech` | text_to_speech | 글을 음성으로 |

출처: Hermes 공식 문서 tools-reference, toolsets-reference(기본 `hermes-cli` 툴셋, 2026-11-12 확인).

클래스로 만들지 않은 기본 툴: `terminal`·`process_manage`(Dev·Ops라 제외), `clarify`(되묻기 = `none`), `skill_view`·`skills_list`·`skill_manage`(앞에 붙어도 무시), `todo_list`·`delegate_task`·`process_manage`(에이전트가 일을 나누고 관리하는 내부 툴이라 사용자 요청 한 건과 1:1로 대응하지 않음), `computer_use`·`kanban_*`(조건부 등록), `video_*`·`x_search`(기본 꺼짐).

## 2. 경계 규칙 13~23
13. **memory:** "기억해 둬", "앞으로는", "다음부터"처럼 **다음 대화에도 남아야 하는** 사실·선호 = `memory`. "이번 대화에서만" = `none`. 저장된 것 삭제는 `needs_confirm = 예`.
14. **session_search:** 답이 **이전 대화**에 있으면 `session_search`. 지금 대화(context)에 있으면 `none`. 메일·일정의 지난 기록은 각자 도구(`mail_read`, `calendar_list`).
15. **cronjob:** 시각·주기가 붙은 "알려줘/해줘"(알람, 타이머, 리마인더, 매일 브리핑, 주기 점검) = `cronjob`. 예약 삭제는 `needs_confirm = 예`. "캘린더에"라고 명시하거나 약속·회의 등록이면 `calendar_create`. **v1에서 `none`(못 함)이던 알람·타이머는 v2에서 `cronjob`이다.**
16. **cronjob 안의 도구:** "매일 아침 날씨 알려줘"는 first=`cronjob`, sequence에도 `cronjob`만 적는다(날씨 조회는 예약된 작업이 나중에 한다). "지금 확인하고 앞으로도 매시간"처럼 지금 할 일이 같이 있으면 규칙 10(먼저 언급된 쪽).
17. **file:** 메모·문서·자료 파일(`~/notes/…`, `~/Documents/…`) 읽기·쓰기·찾기 = `file`. 파일을 읽어 **계산·집계**까지 해야 하면 first=`execute_code`, also_ok=`file`.
18. **web_extract ↔ web_search:** URL이 요청이나 앞 대화에 있으면 `web_extract`. 없으면 `web_search`(찾은 뒤 읽기는 sequence에 `web_search → web_extract`).
19. **browser:** 읽기만이면 `web_extract`, 클릭·입력·로그인·스크롤·스크린샷이 필요하면 `browser`. 결제·제출·예약 확정은 `needs_confirm = 예`. **사이트를 지정하지 않은** "식당 예약해줘", "택시 불러줘"는 v1대로 `none`.
20. **execute_code:** 암산 한두 단계 = `none`. 큰 수·날짜·통계·시뮬레이션·파일 집계 = `execute_code`. "코드 써줘"는 실행 요청이 아니므로 `none`. 환율처럼 조회가 먼저면 조회 도구가 first(규칙 8).
21. **image_generate ↔ vision_analyze:** 새로 만들거나 고치면 `image_generate`, 주어진 이미지에 대해 묻거나 읽으면 `vision_analyze`. 이미지가 없는데 "이 사진"이라고 하면 `none`(되묻기). 이미지 첨부는 context에 `[이미지 첨부: 파일명]`으로 적는다.
22. **text_to_speech:** "음성으로", "오디오로", "소리 내서"처럼 음성을 명시할 때만. "메일 읽어줘"는 `mail_read`. 조회한 내용을 음성으로 달라면 조회 도구가 first, sequence 끝에 `text_to_speech`.
23. **메일·문자·메신저 보내기, 기기 제어, 음악 재생**은 v2에서도 `none`(못 한다고 답). Hermes 기본 툴에 사용자 대신 임의 수신자에게 보내는 툴이 없다.

## 3. v1 데이터와의 관계
- v1 3,491건의 라벨은 **건드리지 않았다.** v2 추가분은 별도 파일(`dataset/tool-choice-v2add.*`)이다.
- 18개 클래스로 함께 학습하려면 v1의 `none` 중 규칙 15에 걸리는 알람·타이머 문장(예: "알람 7시에 맞춰줘", "타이머 10분", "Set an alarm for 7")을 `cronjob`으로 바꿔야 한다. `dataset/v2add-v1-conflicts.md`에 후보 목록.
- **"골드 라벨"은 사람이 검수한 라벨만 가리킨다**(Daniel 2026-11-13). 모델(Opus) 라벨, 생성 의도는 골드가 아니다.
- 평가용 분할: v2 추가분의 10%(51건)를 `holdout`으로 떼어 두었고 모델 라벨을 달지 않았다. 사람 3명이 독립으로 라벨을 달고 다수결을 낸 뒤에야 골드가 된다. (v1의 `gold` 분할과 `tool-choice-v1.gold.jsonl`도 같은 뜻의 "골드 후보"다. 파일 이름은 아직 그대로다.)
- 검수용 파일에는 검수 품질을 재기 위한 항목이 섞여 있다. 학습에는 `tool-choice-v2add.labeled.jsonl`이나 검수 결과만 쓴다.
