"""v2 추가분(Hermes 기본 툴 클래스) 빌드·라벨 병합. v1 파일은 건드리지 않는다.
용어: "골드 라벨"은 사람이 검수한 라벨만 가리킨다. 평가용으로 떼어 둔 분할은 사람 라벨이 붙기 전까지 holdout이라 부른다.
사용:
  python3 build_v2add.py build   gen/v2/*.txt → dataset/tool-choice-v2add.{all,train,val,holdout}.jsonl,
                                 dataset/labeling-input-v2add.jsonl, dataset/labels/v2/batch-NN.input.jsonl,
                                 dataset/stats-v2add.md, dataset/v2add-v1-conflicts.md
  python3 build_v2add.py add gen/v2/<새 파일>.txt
                                 기존 id·분할은 그대로 두고 새 문장만 덧붙인다(이미 있는 문장은 건너뜀).
                                 dataset/labels/v2/batch-NN.input.jsonl 을 다음 번호로 하나 더 만든다.
  python3 build_v2add.py merge   dataset/labels/v2/batch-NN.jsonl → dataset/labels/labels-v2add.jsonl,
                                 dataset/tool-choice-v2add.labeled.jsonl, dataset/labels/agreement-v2add.md
"""
import json, random, re, sys, collections, pathlib, hashlib, glob
import build_dataset as bd

HERE = pathlib.Path(__file__).resolve().parent
GEN, DS = HERE / "gen" / "v2", HERE / "dataset"
LB = DS / "labels"; LBV2 = LB / "v2"
CLASSES = [c["id"] for c in json.load(open(HERE / "tools-v2.json", encoding="utf-8"))["classes"]]
NEW = [c for c in CLASSES if c not in bd.CLASSES]
bd.CLASSES = CLASSES  # parse()가 v2 클래스 전체를 받게
BATCH = 4
C = collections.Counter

def load(p): return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
def dump(p, rows):
    with open(p, "w", encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")

def build(seed=42):
    rows = []
    for f in sorted(GEN.glob("*.txt")):
        for r in bd.parse(f):
            r["source_file"] = "v2/" + r["source_file"]; rows.append(r)
    v1 = load(DS / "tool-choice-v1.all.jsonl")
    v1keys = {(r["context"], r["request"].lower()): r for r in v1}
    seen, uniq, dup_in, dup_v1 = set(), [], 0, []
    for r in rows:
        key = (r["context"], r["request"].lower())
        if key in seen: dup_in += 1; continue
        seen.add(key)
        if key in v1keys: dup_v1.append((r, v1keys[key])); continue
        uniq.append(r)
    rows = uniq
    for r in rows:
        r["id"] = "tc-" + hashlib.sha1((r["context"] + "\x1f" + r["request"]).encode()).hexdigest()[:8]
    rng = random.Random(seed)
    by = collections.defaultdict(list)
    for r in rows: by[r["intended"]["first"]].append(r)
    for cls in CLASSES:
        lst = by.get(cls, []); rng.shuffle(lst)
        ng, nv = round(len(lst) * 0.10), round(len(lst) * 0.10)
        for i, r in enumerate(lst):
            r["split"] = "holdout" if i < ng else "val" if i < ng + nv else "train"
    rows.sort(key=lambda r: r["id"])
    dump(DS / "tool-choice-v2add.all.jsonl", rows)
    for s in ["train", "val", "holdout"]:
        dump(DS / f"tool-choice-v2add.{s}.jsonl", [r for r in rows if r["split"] == s])
    strip = lambda r: {k: v for k, v in r.items() if k not in ("intended", "source_file", "type")}
    dump(DS / "labeling-input-v2add.jsonl", [strip(r) for r in rows])
    # 라벨러 입력: holdout(평가용, 사람 라벨 전) 제외, 무작위 순서로 배치 분할(id·context·request만)
    tgt = [r for r in rows if r["split"] != "holdout"]; rng.shuffle(tgt)
    LBV2.mkdir(parents=True, exist_ok=True)
    for b in range(BATCH):
        dump(LBV2 / f"batch-{b+1:02d}.input.jsonl",
             [{"id": r["id"], "context": r["context"], "request": r["request"]} for r in tgt[b::BATCH]])
    # 통계
    n = len(rows)
    L = [f"# v2 추가분 통계 (Hermes 기본 툴 클래스, seed={seed})", "",
         f"- 총 {n}건 (추가분 안 중복 {dup_in}건, v1과 같은 문장 {len(dup_v1)}건 제외)",
         f"- 새 클래스 10개가 정답인 문장 {sum(1 for r in rows if r['intended']['first'] in NEW)}건, "
         f"기존 클래스·none이 정답인 경계 문장 {sum(1 for r in rows if r['intended']['first'] not in NEW)}건", "",
         "## 클래스 × 분할", "", "| 클래스 | train | val | holdout | 합계 |", "|---|---|---|---|---|"]
    for cls in CLASSES:
        c = C(r["split"] for r in rows if r["intended"]["first"] == cls)
        if sum(c.values()):
            L.append(f"| {cls}{' (새)' if cls in NEW else ''} | {c['train']} | {c['val']} | {c['holdout']} | {sum(c.values())} |")
    t = C(r["split"] for r in rows)
    L.append(f"| **합계** | {t['train']} | {t['val']} | {t['holdout']} | {n} |")
    for title, key in [("언어", lambda r: r["lang"]), ("유형", lambda r: r["type"]),
                       ("맥락 있음", lambda r: "있음" if r["context"] else "없음"),
                       ("확인 필요", lambda r: "예" if r["intended"]["needs_confirm"] else "아니오"),
                       ("also_ok 있음", lambda r: "있음" if r["intended"]["also_ok"] else "없음")]:
        c = C(key(r) for r in rows)
        L += ["", f"## {title}", ""] + [f"- {k}: {v} ({v/n:.0%})" for k, v in c.most_common()]
    (DS / "stats-v2add.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    # v1과 충돌 후보: 같은 문장인데 의도가 다른 것 + v1 none 중 알람·타이머·리마인더
    pat = re.compile(r"알람|타이머|리마인|알려\s*줘.*(마다|뒤에|후에)|alarm|timer|remind", re.I)
    M = ["# v1 라벨과 v2 기준이 충돌하는 후보", "",
         "v1 파일은 고치지 않았다. 18개 클래스로 함께 학습하려면 아래를 사람이 보고 정한다.", "",
         "## 같은 문장인데 v2 의도가 다른 것 (v2 추가분에서는 제외함)", ""]
    for r, o in dup_v1:
        if r["intended"]["first"] != o["intended"]["first"]:
            M.append(f"- `{o['id']}` {o['request']} : v1 {o['intended']['first']} → v2 {r['intended']['first']}")
    M += ["", "## v1에서 none인데 규칙 15(cronjob)에 걸릴 수 있는 것", ""]
    for o in v1:
        if o["intended"]["first"] == "none" and pat.search(o["request"]):
            M.append(f"- `{o['id']}` ({o['split']}) {o['request']}")
    (DS / "v2add-v1-conflicts.md").write_text("\n".join(M) + "\n", encoding="utf-8")
    print("\n".join(L[:32])); print("라벨 대상", len(tgt), "/ v1 중복", len(dup_v1))

def add(path, seed=43):
    """기존 행은 건드리지 않고 gen 파일 하나의 새 문장만 덧붙인다. build를 다시 돌리면 id·분할이 바뀌므로 보충은 이걸로 한다."""
    old = load(DS / "tool-choice-v2add.all.jsonl")
    seen = {(r["context"], r["request"].lower()) for r in old + load(DS / "tool-choice-v1.all.jsonl")}
    ids = {r["id"] for r in old}; new = []
    for r in bd.parse(pathlib.Path(path)):
        key = (r["context"], r["request"].lower())
        if key in seen: continue
        seen.add(key); r["source_file"] = "v2/" + r["source_file"]
        r["id"] = "tc-" + hashlib.sha1((r["context"] + "\x1f" + r["request"]).encode()).hexdigest()[:8]
        assert r["id"] not in ids, r["id"]; ids.add(r["id"]); new.append(r)
    if not new: print("새 문장 없음"); return
    rng = random.Random(seed); by = collections.defaultdict(list)
    for r in new: by[r["intended"]["first"]].append(r)
    for cls in CLASSES:
        lst = by.get(cls, []); rng.shuffle(lst)
        ng, nv = round(len(lst) * 0.10), round(len(lst) * 0.10)
        for i, r in enumerate(lst): r["split"] = "holdout" if i < ng else "val" if i < ng + nv else "train"
    rows = sorted(old + new, key=lambda r: r["id"])
    dump(DS / "tool-choice-v2add.all.jsonl", rows)
    for s in ["train", "val", "holdout"]:
        dump(DS / f"tool-choice-v2add.{s}.jsonl", [r for r in rows if r["split"] == s])
    strip = lambda r: {k: v for k, v in r.items() if k not in ("intended", "source_file", "type")}
    dump(DS / "labeling-input-v2add.jsonl", [strip(r) for r in rows])
    tgt = [r for r in new if r["split"] != "holdout"]; rng.shuffle(tgt)
    nb = len(glob.glob(str(LBV2 / "batch-[0-9][0-9].input.jsonl"))) + 1
    dump(LBV2 / f"batch-{nb:02d}.input.jsonl", [{"id": r["id"], "context": r["context"], "request": r["request"]} for r in tgt])
    print(f"새 문장 {len(new)}건 (분할 {dict(C(r['split'] for r in new))}), 라벨 대상 {len(tgt)}건 → batch-{nb:02d}.input.jsonl, 전체 {len(rows)}건")

def merge():
    rows = [r for r in load(DS / "tool-choice-v2add.all.jsonl") if r["split"] != "holdout"]
    labels, bad = {}, []
    for f in sorted(glob.glob(str(LBV2 / "batch-[0-9][0-9].jsonl"))):
        for i, l in enumerate(open(f, encoding="utf-8"), 1):
            if not l.strip(): continue
            try: o = json.loads(l)
            except Exception as e: bad.append(f"{f}:{i} {e}"); continue
            if o.get("first") not in CLASSES: bad.append(f"{f}:{i} first {o.get('first')}"); continue
            o["also_ok"] = [a for a in (o.get("also_ok") or []) if a in CLASSES and a != o["first"]]
            o["sequence"] = [a for a in (o.get("sequence") or []) if a in CLASSES]
            o["needs_confirm"] = bool(o.get("needs_confirm"))
            try: o["confidence"] = float(o.get("confidence", 0))
            except Exception: o["confidence"] = 0.0
            o["note"] = o.get("note") or ""; o["rule"] = o.get("rule"); o["batch"] = pathlib.Path(f).stem
            if o["id"] in labels: bad.append(f"{f}:{i} 중복 {o['id']}")
            labels[o["id"]] = o
    missing = [r["id"] for r in rows if r["id"] not in labels]
    extra = set(labels) - {r["id"] for r in rows}
    print(f"라벨 {len(labels)}건, 대상 {len(rows)}건, 누락 {len(missing)}, 대상 외 {len(extra)}, 형식 오류 {len(bad)}")
    for b in bad[:20]: print("  ", b)
    dump(LB / "labels-v2add.jsonl", [labels[k] for k in sorted(labels)])
    rng = random.Random(7); out = []
    for r in rows:
        lb = labels.get(r["id"])
        if not lb: continue
        it = r["intended"]; strict = lb["first"] == it["first"]
        loose = strict or lb["first"] in it["also_ok"] or it["first"] in lb["also_ok"]
        cok = lb["needs_confirm"] == it["needs_confirm"]
        if lb["confidence"] < 0.7: pr, why = 1, "라벨러 확신 낮음"
        elif not loose: pr, why = 2, "생성 의도와 다름"
        elif not strict: pr, why = 3, "also_ok로만 일치"
        elif not cok: pr, why = 3, "확인필요 불일치"
        else: pr, why = 4, ""
        o = dict(r); o["label"] = {k: lb[k] for k in ["first", "also_ok", "sequence", "needs_confirm", "rule", "confidence", "note"]}
        o["cmp"] = {"strict": strict, "loose": loose, "confirm_ok": cok, "priority": pr, "why": why}
        out.append((pr, rng.random(), o))
    out = [o for _, _, o in sorted(out, key=lambda x: x[:2])]
    dump(DS / "tool-choice-v2add.labeled.jsonl", out)
    n = len(out)
    def rate(lst, key):
        k = sum(1 for o in lst if key(o)); return f"{k}/{len(lst)} ({k/max(1,len(lst)):.1%})"
    L = [f"# 생성 의도 vs 라벨러 일치 (v2 추가분, {n}건: train+val)", "",
         f"- first 완전 일치: {rate(out, lambda o: o['cmp']['strict'])}",
         f"- also_ok 포함 일치: {rate(out, lambda o: o['cmp']['loose'])}",
         f"- needs_confirm 일치: {rate(out, lambda o: o['cmp']['confirm_ok'])}",
         f"- 라벨러 confidence < 0.7: {sum(1 for o in out if o['label']['confidence'] < 0.7)}건",
         "- 검수 우선순위: " + ", ".join(f"{k}순위 {v}건" for k, v in sorted(C(o['cmp']['priority'] for o in out).items())),
         "  (1=확신 낮음, 2=의도와 다름, 3=also_ok로만 일치·확인필요 불일치, 4=일치)", "",
         "## 클래스별(생성 의도 기준) first 일치", "", "| 의도 클래스 | 건수 | 완전 일치 | also_ok 포함 |", "|---|---|---|---|"]
    for c in CLASSES:
        sub = [o for o in out if o["intended"]["first"] == c]
        if sub: L.append(f"| {c} | {len(sub)} | {rate(sub, lambda o: o['cmp']['strict'])} | {rate(sub, lambda o: o['cmp']['loose'])} |")
    for title, key in [("유형", lambda o: o["type"]), ("언어", lambda o: o["lang"]), ("맥락", lambda o: "있음" if o["context"] else "없음")]:
        L += ["", f"## {title}별 first 완전 일치", ""]
        for k in sorted({key(o) for o in out}):
            L.append(f"- {k}: {rate([o for o in out if key(o) == k], lambda o: o['cmp']['strict'])}")
    L += ["", "## 라벨러 first 분포", ""] + [f"- {k}: {v}" for k, v in C(o["label"]["first"] for o in out).most_common()]
    L += ["", "## 의도와 다른 건 (1~3순위 중 first 불일치 전부)", ""]
    for o in out:
        if not o["cmp"]["strict"]:
            ctx = (" [맥락: " + o["context"].replace("\n", " / ") + "]") if o["context"] else ""
            L.append(f"- `{o['id']}` {o['request']}{ctx} → 의도 {o['intended']['first']} / 라벨 {o['label']['first']} ({o['label']['confidence']:.2f}) {o['label']['note']}")
    (LB / "agreement-v2add.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:9]))

if __name__ == "__main__":
    {"build": build, "merge": merge, "add": lambda: add(sys.argv[2])}[sys.argv[1]]()
