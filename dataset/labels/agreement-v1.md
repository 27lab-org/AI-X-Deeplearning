# 생성 의도 vs Opus 5.5 라벨 일치 (v1, 3128건: train+val)

- first 완전 일치: 2983/3128 (95.4%)
- also_ok 포함 일치: 3114/3128 (99.6%)
- needs_confirm 일치: 3118/3128 (99.7%)
- Opus confidence < 0.7: 361건
- 검수 우선순위: 1순위 361건, 2순위 8건, 3순위 25건, 4순위 2734건
  (1=확신 낮음, 2=의도와 다름, 3=also_ok로만 일치·확인필요 불일치, 4=일치)

## 클래스별(생성 의도 기준) first 일치

| 의도 클래스 | 건수 | 완전 일치 | also_ok 포함 |
|---|---|---|---|
| weather | 293 | 290/293 (99.0%) | 293/293 (100.0%) |
| calendar_list | 285 | 278/285 (97.5%) | 284/285 (99.6%) |
| calendar_create | 248 | 239/248 (96.4%) | 246/248 (99.2%) |
| web_search | 323 | 309/323 (95.7%) | 323/323 (100.0%) |
| map_search | 281 | 272/281 (96.8%) | 281/281 (100.0%) |
| fx | 247 | 243/247 (98.4%) | 247/247 (100.0%) |
| mail_read | 262 | 257/262 (98.1%) | 262/262 (100.0%) |
| server_status | 301 | 289/301 (96.0%) | 301/301 (100.0%) |
| ssh | 326 | 283/326 (86.8%) | 319/326 (97.9%) |
| none | 562 | 523/562 (93.1%) | 558/562 (99.3%) |

## 유형별 first 완전 일치

- cannot: 107/109 (98.2%)
- clarify: 77/79 (97.5%)
- easy: 1118/1131 (98.9%)
- tricky: 1681/1809 (92.9%)

## 언어별 first 완전 일치

- en: 711/732 (97.1%)
- ko: 1892/2008 (94.2%)
- mix: 380/388 (97.9%)

## 맥락별 first 완전 일치

- 없음: 2582/2701 (95.6%)
- 있음: 401/427 (93.9%)

## 혼동 행렬 (행=생성 의도, 열=Opus first)

| 의도\Opus | weather | calendar_list | calendar_create | web_search | map_search | fx | mail_read | server_status | ssh | none |
|---|---|---|---|---|---|---|---|---|---|---|
| weather | 290 | 1 | · | 1 | · | · | · | · | · | 1 |
| calendar_list | · | 278 | · | · | · | · | · | · | · | 7 |
| calendar_create | · | 1 | 239 | · | · | · | · | · | · | 8 |
| web_search | 1 | · | · | 309 | 2 | 1 | · | · | · | 10 |
| map_search | · | · | · | 9 | 272 | · | · | · | · | · |
| fx | · | · | · | 4 | · | 243 | · | · | · | · |
| mail_read | · | 1 | · | · | · | · | 257 | · | · | 4 |
| server_status | · | · | · | · | · | · | · | 289 | 11 | 1 |
| ssh | · | · | · | · | · | · | · | 13 | 283 | 30 |
| none | · | 7 | · | 11 | 5 | 3 | 3 | 2 | 8 | 523 |

## Opus first 분포

- none: 584
- web_search: 334
- server_status: 304
- ssh: 302
- weather: 291
- calendar_list: 288
- map_search: 279
- mail_read: 260
- fx: 247
- calendar_create: 239

## 불일치 예시 (2순위)

- `tc-939e1f59` iptables 규칙 추가 → 의도 ssh / Opus none (0.75) 호스트·규칙 미지정 → 되묻기
- `tc-ce80ef41` 타임아웃 60초로 → 의도 ssh / Opus none (0.80) 무엇의 타임아웃인지 불명 → 되묻기
- `tc-8e4002e2` 데이터셋 삭제 → 의도 ssh / Opus none (0.75) 대상 데이터셋·호스트 불명 → 되묻기, 삭제는 확인 필수
- `tc-35301bfe` TrueNAS VM ID 뭐야? → 의도 none / Opus server_status (0.70) qm list로 조회; 기억으로 답하면 none
- `tc-31a99852` 헤더 확인해줘 curl -I → 의도 ssh / Opus none (0.70) curl -I 대상 URL이 없어 되묻기
- `tc-06b23cb5` 둘 다 온라인이었나? [맥락: 비서: 오늘 일정은 회의 2개예요] → 의도 none / Opus calendar_list (0.85) 
- `tc-bd376cb7` 그 일정 아직 유효해? → 의도 calendar_list / Opus none (0.85) 
- `tc-1b140eca` 컨테이너 삭제 → 의도 ssh / Opus none (0.75) 어느 컨테이너인지 불명확 → 되묻기. 삭제라 실행 시 확인 필요
