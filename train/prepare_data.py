"""학습용 데이터 내보내기: 문장(저장소) + Opus 라벨(저장소) + 사람 검수 골드(로컬 내보내기) → data/*.jsonl

사용:
    python train/prepare_data.py --gold-dir ../aix-review-export-20261124

출력 (data/ 는 .gitignore, 정답이 들어 있어 커밋하지 않는다):
    data/train.jsonl, val.jsonl, test.jsonl, holdout.jsonl
    data/labels.json   클래스 18개 순서 (tools-v2.json 순서)
    data/summary.md    건수·분포·주의사항

한 줄 형식:
    id, split, lang, type, context, request,
    gold        사람 골드 first (없으면 null)
    gold_also_ok, gold_source, gold_votes, written_by, reviewer
    opus        Opus first (train/val만), opus_also_ok, opus_conf

split 이름: 저장소의 gold → test 로 바꾼다 (사람 3명 다수결 시험셋).
"""
import argparse
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read_jsonl(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold-dir", default=str(ROOT.parent / "aix-review-export-20261124"),
                    help="검수 결과 내보내기 폴더 (gold-labels-v1.jsonl 이 있는 곳)")
    ap.add_argument("--out", default=str(ROOT / "data"))
    args = ap.parse_args()

    labels = [c["id"] for c in json.load(open(ROOT / "tools-v2.json", encoding="utf-8"))["classes"]]

    items = read_jsonl(ROOT / "dataset/tool-choice-v1.all.jsonl") + \
        read_jsonl(ROOT / "dataset/tool-choice-v2add.all.jsonl")
    opus = {x["id"]: x["label"] for x in
            read_jsonl(ROOT / "dataset/tool-choice-v1.labeled.jsonl") +
            read_jsonl(ROOT / "dataset/tool-choice-v2add.labeled.jsonl")}
    gold = {x["id"]: x for x in read_jsonl(Path(args.gold_dir) / "gold-labels-v1.jsonl")}

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = collections.defaultdict(list)
    seen = set()
    for it in items:
        if it["id"] in seen:
            raise SystemExit(f"중복 id {it['id']}")
        seen.add(it["id"])
        split = "test" if it["split"] == "gold" else it["split"]
        g = gold.get(it["id"])
        o = opus.get(it["id"])
        if g and g["split"] != split:
            raise SystemExit(f"분할 불일치 {it['id']}: {split} vs {g['split']}")
        gl = g["label"] if g else {}
        r = {
            "id": it["id"], "split": split, "lang": it["lang"], "type": it.get("type"),
            "context": it.get("context", ""), "request": it["request"],
            "gold": gl.get("first"),
            "gold_also_ok": gl.get("also_ok", []),
            "gold_source": gl.get("source"),
            "gold_votes": gl.get("votes"),
            "reviewer": g.get("reviewer") if g else None,
            "written_by": g.get("written_by") if g else None,
            "opus": o["first"] if o else None,
            "opus_also_ok": o.get("also_ok", []) if o else [],
            "opus_conf": o.get("confidence") if o else None,
        }
        for k in ("gold", "opus"):
            if r[k] is not None and r[k] not in labels:
                raise SystemExit(f"모르는 클래스 {r[k]} ({it['id']})")
        rows[split].append(r)

    for split, rs in rows.items():
        rs.sort(key=lambda r: r["id"])
        with open(out / f"{split}.jsonl", "w", encoding="utf-8") as f:
            for r in rs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    json.dump(labels, open(out / "labels.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 요약
    L = ["# 학습 데이터 요약 (prepare_data.py 생성)", "",
         "| split | 전체 | 골드 있음 | Opus 있음 | 관리자(daniel) 작성 골드 |", "|---|---|---|---|---|"]
    for s in ("train", "val", "test", "holdout"):
        rs = rows.get(s, [])
        L.append(f"| {s} | {len(rs)} | {sum(r['gold'] is not None for r in rs)} | "
                 f"{sum(r['opus'] is not None for r in rs)} | {sum(r['written_by'] == 'daniel' for r in rs)} |")
    L += ["", "## 골드 클래스 분포 (train / val / test)", "", "| 클래스 | train | val | test |", "|---|---|---|---|"]
    cnt = {s: collections.Counter(r["gold"] for r in rows.get(s, []) if r["gold"]) for s in ("train", "val", "test")}
    for c in labels:
        L.append(f"| {c} | {cnt['train'][c]} | {cnt['val'][c]} | {cnt['test'][c]} |")
    tr = [r for r in rows["train"] if r["gold"] and r["opus"]]
    agree = sum(r["gold"] == r["opus"] for r in tr)
    L += ["", f"train에서 골드 = Opus first: {agree}/{len(tr)} ({agree / max(len(tr), 1):.1%})", "",
          "## 주의", "",
          "- test 6건은 3명 다수결이 안 나와 골드가 없다 (평가에서 빠짐).",
          "- holdout 53건은 사람 라벨이 없다.",
          "- 검수 A 칸에 관리자(daniel) 링크로 단 답이 섞여 있다(`written_by`). 시험셋 3명 라벨 중 2건도 해당.",
          "  수정은 별도 스레드에서 진행 중이라 여기서는 표시만 하고, 학습에서 빼려면 `--drop-written-by daniel`.",
          ]
    (out / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:8]))


if __name__ == "__main__":
    main()
