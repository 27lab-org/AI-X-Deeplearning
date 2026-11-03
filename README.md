# aix

AI 실습 과제 모음. 원래 HERO LXC 3920 (aix-hw, 10.27.10.220) `/root` 에서 작업.

- `03-exercise-checkpoint/` : 이미지 스타일 변환 (fast-style-transfer 체크포인트로 추론)
- `05-2-exercise-medical-image/` : 의료 영상(NIfTI) 정상/비정상 분류 모델 학습
- `setup.sh` : uv 로 Python 3.10 venv + TensorFlow 2.15 설치
- `readpdf.py`, `readpdf.sh` : 과제 PDF 텍스트/이미지 추출

의료 영상 원본 데이터(`medical-images/`, 약 1GB)와 개인 사진은 저장소에 넣지 않음.
