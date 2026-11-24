# E2 학생 모델 학습

사전학습 인코더에 분류 헤드(18클래스)를 붙여 전체 미세조정한다. PyTorch Lightning 사용.
수업 연결: Lightning(9주), BERT 분류(10주), 전이학습(11주).

## 준비

```bash
python -m venv .venv
.venv/Scripts/python -m pip install torch --index-url https://download.pytorch.org/whl/cu126
.venv/Scripts/python -m pip install -r train/requirements.txt
```

## 1. 데이터 내보내기

```bash
python train/prepare_data.py --gold-dir ../aix-review-export-20261124
```

- 문장·분할·Opus 라벨은 저장소 `dataset/`, 사람 골드는 검수 결과 내보내기 폴더에서 읽는다.
- 결과는 `data/` (정답이 들어 있어 `.gitignore`). 건수·분포는 `data/summary.md`.
- 분할: train 2,313 (골드 2,294) / val 288 (골드 283) / test 243 (3명 다수결 237) / holdout 53 (라벨 없음).
- 검증·시험 평가는 언제나 **사람 골드**로 한다. Opus 라벨은 학습 라벨로만 쓸 수 있다(H2 비교).

## 2. 기준선 (CPU, 수 초)

```bash
python train/baseline_tfidf.py              # 골드 라벨로 학습
python train/baseline_tfidf.py --labels opus
```

## 3. 학생 모델

```bash
# 파이프라인 확인 (64건, 8배치)
python train/train.py --smoke

# 본 학습: laya-ko 인코더 + 골드 라벨
python train/train.py --backbone laya:2nugu/laya-ko --labels gold

# 다른 인코더
python train/train.py --backbone jhu-clsp/mmBERT-base
```

- `--backbone laya:<repo>`: [laya-ko](https://huggingface.co/2nugu/laya-ko)(mmBERT-base 기반 결정 모델, 322M)에서 인코더 가중치만 꺼내고 헤드는 새로 붙인다.
  다른 값은 Hugging Face `AutoModel` 이름.
- 입력: `이전 대화\n요청` (맥락 없으면 요청만), 최대 128토큰, 평균 풀링.
- 주요 옵션: `--labels gold|opus`, `--train-size 500` (데이터 양 실험), `--soft-also-ok 0.1` (also_ok 소프트 라벨),
  `--drop-written-by daniel`, `--seed`, `--lr 2e-5`, `--epochs 5` (val macro-F1 조기 종료).
- 결과: `runs/<이름>/` 에 `result.json`(val acc·loose acc·macro-F1), `val_predictions.jsonl`, `metrics.csv`, `best.ckpt`.
- `--eval-test` 는 설정을 다 고른 뒤 마지막에 한 번만.

## 주의

- 검수 A 칸에 관리자(daniel) 링크로 단 답이 섞여 있다(골드 train 42, val 2, 시험셋 투표 2). 별도 스레드에서 정리 중이라 데이터는 그대로 두고 `written_by` 로 표시만 했다.
- 시험셋 6건은 다수결이 안 나와 평가에서 빠진다.
