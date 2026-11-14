# AI-X-Deeplearning: 툴콜 채점기 (기말 프로젝트)

에이전트가 요청에 맞는 도구를 골랐는지 채점하는 아주 작은 모델을 만드는 실험.

**방식:** 강한 모델(Opus)이 라벨 → 사람 3명이 검수 → 소형 모델이 학습(증류) → CPU에서 채점.
첫 범위는 **도구 고르기**: 한국어/영어 **일상 요청**을 보고 도구 중 맞는 것(또는 "부르지 않음")을 고른다.

자세한 실험 계획은 [docs/plan.md](docs/plan.md).

## 파일

| 파일 | 내용 |
|---|---|
| `tools.json` | 도구 8개 정의 (weather, calendar_list, calendar_create, web_search, map_search, fx, mail_read, none) |
| `labeling-guide.md` | 라벨 기준서 (경계 규칙) |
| `seed-examples.jsonl` | 라벨 예시 45건 |
| `prompts.md` | 문장 생성·라벨 프롬프트 |
| `build_dataset.py` | 생성 문장 → train/val/gold JSONL + 통계 |
| `merge_labels.py` | Opus 라벨 병합·비교 |
| `build_review_sheet.py` | 사람 검수용 엑셀 생성 |
| `dataset/` | 데이터셋 v1 (2,369건: train 1,893 / val 233 / gold 243), 통계 `stats.md` |
| `dataset/labels/` | Opus 라벨, 생성 의도와의 일치 통계 |
| `dataset/review-sheet-v2.xlsx` | 검수 엑셀 (골드 A/B/C 시트 포함) |
| `tools-v2.json` | 도구 18개 정의: 위 8개 + Nous Hermes 기본 툴 기준 10개 (memory, session_search, cronjob, file, web_extract, browser, execute_code, image_generate, vision_analyze, text_to_speech) |
| `labeling-guide-v2.md` | 새 클래스 10개의 경계 규칙 13~23 |
| `seed-examples-v2.jsonl` | 새 클래스 라벨 예시 25건 |
| `gen/v2/` | v2 추가분 생성 원문 |
| `build_v2add.py` | v2 추가분 빌드·라벨 병합 (v1 파일은 건드리지 않음) |
| `dataset/tool-choice-v2add.*` | v2 추가분 528건 (train 420 / val 55 / holdout 53: 평가용, 사람 라벨 전), 통계 `stats-v2add.md`, v1과 충돌 후보 `v2add-v1-conflicts.md` |
| `dataset/labels/v2/`, `labels-v2add.jsonl`, `agreement-v2add.md` | v2 추가분 Opus 라벨과 일치 통계 |

## 범위

일상 요청만 다룬다. Dev·Ops 관련(서버, ssh, 인프라, 코딩, 배포, ML 등) 문장과 `server_status`·`ssh` 클래스는 2026-11-14에 뺐다.

## 용어

**골드 라벨**은 사람이 검수한 라벨만 가리킨다. Opus 라벨과 생성 의도는 골드가 아니다. `gold`/`holdout` 분할은 사람 3명이 라벨을 달기 전까지 "골드 후보"다.

## 진행 상태

- E0 데이터 준비: 완료
- E1 Opus 라벨: 완료 (생성 의도와 96.7% 일치). 사람 검수 대기
- v2 추가분(2026-11-12): Hermes 기본 툴 기준 클래스 10개 추가. Dev·Ops 제외 후 402건, 11-14에 얇은 클래스 4개(file·web_extract·session_search·execute_code)를 126건 보충해 528건, train+val 475건 Opus 라벨. 사람 검수 대기
- E2 학생 모델 학습, E3 프론티어 기준선·CPU 속도: 예정
