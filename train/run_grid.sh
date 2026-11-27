#!/bin/bash
# E2 실험 묶음 (차례로 실행, 끝난 run 은 건너뜀). 시험셋 평가는 설정을 고른 뒤 따로.
#   tmux new -d -s grid "bash train/run_grid.sh"     로그: runs/grid.log
cd "$(dirname "$0")/.."
PY=${PY:-/opt/aix/bin/python}
run() {  # run <이름> <옵션...>
  name=$1; shift
  [ -f runs/$name/result.json ] && { echo "skip $name"; return; }
  echo "== $(date '+%m-%d %H:%M') start $name $*"
  $PY train/train.py --name $name "$@" > runs/$name.log 2>&1 && echo "   done $(cat runs/$name/result.json | tr -d '\n ')" || echo "   FAILED $name (runs/$name.log)"
}
mkdir -p runs
{
for s in 42 43 44; do run gold-s$s --labels gold --seed $s; done     # H1 본 결과
for s in 42 43 44; do run opus-s$s --labels opus --seed $s; done     # H2 사람 검수 값어치
run gold-n500-s42  --labels gold --train-size 500  --seed 42          # 데이터 양
run gold-n1200-s42 --labels gold --train-size 1200 --seed 42
run gold-soft-s42  --labels gold --soft-also-ok 0.1 --seed 42         # also_ok 소프트 라벨
run gold-nodaniel-s42 --labels gold --drop-written-by daniel --seed 42
echo "== $(date '+%m-%d %H:%M') all done"
} >> runs/grid.log 2>&1
