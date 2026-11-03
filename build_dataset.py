"""gen/*.txt → dataset/ (JSONL + 통계).
사용: python3 build_dataset.py [--seed 42]
출력:
  dataset/tool-choice-v1.all.jsonl      전체(생성 의도 라벨 포함)
  dataset/tool-choice-v1.<split>.jsonl  train/val/gold (의도 라벨 포함)
  dataset/labeling-input.jsonl          강한 라벨러 입력(의도 라벨·type 제거)
  dataset/stats.md                      분포 통계
형식(gen/*.txt): lang | type | first | also_ok | confirm | seq | context | request | hint
"""
import json, random, re, sys, collections, pathlib, hashlib

HERE = pathlib.Path(__file__).resolve().parent
GEN, OUT = HERE / "gen", HERE / "dataset"
CLASSES = ["weather","calendar_list","calendar_create","web_search","map_search","fx","mail_read","server_status","ssh","none"]
SPLIT = {"gold": 0.10, "val": 0.10}  # 나머지 train

def parse(path):
    rows = []
    for ln, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 8:
            raise SystemExit(f"{path.name}:{ln}: 칸 수 {len(parts)} < 8 → {line[:60]}")
        lang, typ, first, also, conf, seq, ctx, req = parts[:8]
        hint = parts[8] if len(parts) > 8 else ""
        if first not in CLASSES:
            raise SystemExit(f"{path.name}:{ln}: 알 수 없는 클래스 {first}")
        also_ok = [a for a in also.split(",") if a] if also else []
        for a in also_ok:
            if a not in CLASSES:
                raise SystemExit(f"{path.name}:{ln}: also_ok 오류 {a}")
        if seq:
            sequence = seq.split(",")
        elif first == "none":
            sequence = []
        elif first == "calendar_create" and "calendar_list" in also_ok:
            sequence = ["calendar_list", "calendar_create"]
        else:
            sequence = [first]
        rows.append({
            "lang": lang, "type": typ,
            "context": ctx.replace(" // ", "\n"), "request": req,
            "intended": {"first": first, "also_ok": also_ok, "sequence": sequence,
                         "needs_confirm": conf.lower() == "y", "hint": hint},
            "source_file": path.name,
        })
    return rows

def main(seed=42):
    rows = []
    for f in sorted(GEN.glob("*.txt")):
        rows.extend(parse(f))
    # 중복 제거(요청+맥락 기준)
    seen, uniq = set(), []
    for r in rows:
        key = (r["context"], r["request"].lower())
        if key in seen:
            continue
        seen.add(key); uniq.append(r)
    dups = len(rows) - len(uniq)
    rows = uniq
    # id: 내용 해시 → 재생성해도 안정
    for r in rows:
        h = hashlib.sha1((r["context"] + "\x1f" + r["request"]).encode()).hexdigest()[:8]
        r["id"] = f"tc-{h}"
    # 클래스별 층화 분할
    rng = random.Random(seed)
    by_cls = collections.defaultdict(list)
    for r in rows:
        by_cls[r["intended"]["first"]].append(r)
    for cls, lst in by_cls.items():
        rng.shuffle(lst)
        n = len(lst); ng, nv = round(n * SPLIT["gold"]), round(n * SPLIT["val"])
        for i, r in enumerate(lst):
            r["split"] = "gold" if i < ng else "val" if i < ng + nv else "train"
    rows.sort(key=lambda r: r["id"])
    OUT.mkdir(exist_ok=True)
    def dump(name, lst, strip=False):
        with open(OUT / name, "w", encoding="utf-8") as f:
            for r in lst:
                o = dict(r)
                if strip:
                    o.pop("intended"); o.pop("source_file"); o.pop("type")  # type(cannot/clarify)은 라벨 힌트라 제거
                f.write(json.dumps(o, ensure_ascii=False) + "\n")
    dump("tool-choice-v1.all.jsonl", rows)
    for s in ["train", "val", "gold"]:
        dump(f"tool-choice-v1.{s}.jsonl", [r for r in rows if r["split"] == s])
    dump("labeling-input.jsonl", rows, strip=True)
    # 통계
    C = collections.Counter
    lines = [f"# 데이터셋 v1 통계 (seed={seed})", "", f"- 총 {len(rows)}건 (중복 제거 {dups}건)", ""]
    lines += ["## 클래스 × 분할", "", "| 클래스 | train | val | gold | 합계 |", "|---|---|---|---|---|"]
    for cls in CLASSES:
        c = C(r["split"] for r in rows if r["intended"]["first"] == cls)
        lines.append(f"| {cls} | {c['train']} | {c['val']} | {c['gold']} | {sum(c.values())} |")
    tot = C(r["split"] for r in rows)
    lines.append(f"| **합계** | {tot['train']} | {tot['val']} | {tot['gold']} | {len(rows)} |")
    for title, key in [("언어", lambda r: r["lang"]), ("유형", lambda r: r["type"]),
                       ("맥락 있음", lambda r: "있음" if r["context"] else "없음"),
                       ("확인 필요", lambda r: "예" if r["intended"]["needs_confirm"] else "아니오"),
                       ("also_ok 있음", lambda r: "있음" if r["intended"]["also_ok"] else "없음")]:
        c = C(key(r) for r in rows)
        lines += ["", f"## {title}", ""] + [f"- {k}: {v} ({v/len(rows):.0%})" for k, v in c.most_common()]
    (OUT / "stats.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))

if __name__ == "__main__":
    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 42
    main(seed)
