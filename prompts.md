# 강한 모델 프롬프트 (Claude Opus 5.5 / Fable)

두 개: ① 문장 생성 ② 라벨 달기. 생성과 라벨은 **다른 호출**로 한다(생성할 때 의도한 정답을 라벨러가 보지 않게). 가능하면 생성은 Fable, 라벨은 Opus 5.5처럼 서로 다른 모델로 해서 같은 버릇이 겹치지 않게 한다.

공통: temperature 0(라벨) / 1.0(생성), 출력은 JSONL 한 줄에 한 건. 시스템 프롬프트에 tools.json과 labeling-guide.md 3절을 그대로 넣는다(프롬프트 캐시 대상).

---

## ① 문장 생성

```
너는 개인 비서 에이전트(Hermes)의 사용자 요청 예시를 만드는 사람이다.
아래 도구 목록과 경계 규칙을 참고해서, 사용자가 실제로 보낼 법한 요청을 만들어라.

[도구 목록]
{tools.json}

[경계 규칙]
{labeling-guide.md 3절}

[참고: 실제 사용 패턴 요약]
{Hermes 사용 로그를 사람이 요약한 패턴 목록. 실명·주소·번호 없음}

조건:
- 이번 묶음: 목표 클래스 = {class}, 유형 = {easy|tricky|none_or_cannot}, 언어 = {ko|en|mix}, {n}건
- tricky는 경계 규칙 {rule_no}번을 건드리는 문장으로.
- 같은 문형 반복 금지. 길이·말투(반말/존댓말/짧은 메모체/오타)를 섞는다.
- 실제 사람 이름·주소·전화·메일 주소 금지. 가상의 이름을 쓴다.
- 20%는 context(이전 대화 1~3줄)를 붙인다.
출력: {"lang":..., "type":..., "context":..., "request":..., "intended_first":...} JSONL
```

`intended_first`는 생성 의도일 뿐 라벨이 아니다. 라벨러와 다를 때가 오히려 검수 우선 대상.

## ② 라벨 달기

```
너는 Hermes 에이전트의 도구 선택을 채점하기 위한 정답 라벨을 단다.
아래 도구 목록과 라벨 기준서를 엄격히 따른다.

[도구 목록]
{tools.json}

[라벨 기준서]
{labeling-guide.md 1~3절}

요청 하나마다 아래 JSON 한 줄로만 답한다:
{"id": ..., "first": <클래스 중 하나>, "also_ok": [...], "sequence": [...],
 "needs_confirm": true|false, "rule": <근거가 된 경계 규칙 번호 또는 null>,
 "confidence": <0~1>, "note": <애매하면 한 줄, 아니면 "">}

규칙:
- 단어가 아니라 필요한 행동으로 고른다.
- 판단이 갈리면 confidence를 0.7 아래로 낮추고 note에 이유를 쓴다.
```

## 검수 우선순위
1. confidence < 0.7
2. 생성 의도(intended_first)와 라벨(first)이 다른 것
3. 나머지는 무작위 순서로
