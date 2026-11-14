# 생성 의도 vs 라벨러 일치 (v2 추가분, 456건: train+val)

- first 완전 일치: 451/456 (98.9%)
- also_ok 포함 일치: 456/456 (100.0%)
- needs_confirm 일치: 452/456 (99.1%)
- 라벨러 confidence < 0.7: 12건
- 검수 우선순위: 1순위 12건, 3순위 8건, 4순위 436건
  (1=확신 낮음, 2=의도와 다름, 3=also_ok로만 일치·확인필요 불일치, 4=일치)

## 클래스별(생성 의도 기준) first 일치

| 의도 클래스 | 건수 | 완전 일치 | also_ok 포함 |
|---|---|---|---|
| weather | 4 | 4/4 (100.0%) | 4/4 (100.0%) |
| calendar_list | 4 | 4/4 (100.0%) | 4/4 (100.0%) |
| calendar_create | 5 | 5/5 (100.0%) | 5/5 (100.0%) |
| web_search | 12 | 12/12 (100.0%) | 12/12 (100.0%) |
| map_search | 1 | 1/1 (100.0%) | 1/1 (100.0%) |
| fx | 2 | 2/2 (100.0%) | 2/2 (100.0%) |
| mail_read | 6 | 6/6 (100.0%) | 6/6 (100.0%) |
| server_status | 3 | 3/3 (100.0%) | 3/3 (100.0%) |
| ssh | 8 | 6/8 (75.0%) | 8/8 (100.0%) |
| memory | 36 | 35/36 (97.2%) | 36/36 (100.0%) |
| session_search | 34 | 34/34 (100.0%) | 34/34 (100.0%) |
| cronjob | 36 | 36/36 (100.0%) | 36/36 (100.0%) |
| file | 36 | 36/36 (100.0%) | 36/36 (100.0%) |
| web_extract | 33 | 33/33 (100.0%) | 33/33 (100.0%) |
| browser | 34 | 34/34 (100.0%) | 34/34 (100.0%) |
| execute_code | 35 | 35/35 (100.0%) | 35/35 (100.0%) |
| image_generate | 35 | 35/35 (100.0%) | 35/35 (100.0%) |
| vision_analyze | 35 | 35/35 (100.0%) | 35/35 (100.0%) |
| text_to_speech | 32 | 32/32 (100.0%) | 32/32 (100.0%) |
| none | 65 | 63/65 (96.9%) | 65/65 (100.0%) |

## 유형별 first 완전 일치

- cannot: 9/9 (100.0%)
- clarify: 14/14 (100.0%)
- easy: 76/76 (100.0%)
- tricky: 352/357 (98.6%)

## 언어별 first 완전 일치

- en: 121/122 (99.2%)
- ko: 240/243 (98.8%)
- mix: 90/91 (98.9%)

## 맥락별 first 완전 일치

- 없음: 307/310 (99.0%)
- 있음: 144/146 (98.6%)

## 라벨러 first 분포

- none: 63
- execute_code: 36
- cronjob: 36
- file: 36
- memory: 35
- vision_analyze: 35
- image_generate: 35
- session_search: 34
- browser: 34
- web_extract: 33
- text_to_speech: 32
- web_search: 13
- server_status: 6
- ssh: 6
- mail_read: 6
- calendar_create: 5
- weather: 4
- calendar_list: 4
- fx: 2
- map_search: 1

## 의도와 다른 건 (1~3순위 중 first 불일치 전부)

- `tc-054577e0` gpu-a에서 nvidia-smi 돌려봐 → 의도 ssh / 라벨 server_status (0.65) GPU 상태 조회지만 nvidia-smi는 정해진 조회 목록 밖이라 ssh로도 볼 수 있음
- `tc-4b3110ae` 3월 9일이면 무슨 요일이야 내년에 [맥락: 사용자: 민서 생일이 3월 9일이래] → 의도 none / 라벨 execute_code (0.75) 
- `tc-661b6f2a` Run df -h on nas01 → 의도 ssh / 라벨 server_status (0.75) 명령을 직접 지정했지만 df는 정해진 상태 조회
- `tc-42745764` 응. 그리고 내가 서버 얘기하면 기본은 node02라고 기억해 [맥락: 비서: node02 상태를 확인할까요?] → 의도 memory / 라벨 server_status (0.80) 
- `tc-7603a4a7` reminder app 추천해줘 → 의도 none / 라벨 web_search (0.85) 
