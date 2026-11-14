"""Opus 배치 라벨 병합 + 생성 의도와 비교 + 검수 우선순위.
사용: python3 merge_labels.py
입력: dataset/labels/opus/batch-*.jsonl, dataset/tool-choice-v1.all.jsonl
출력: dataset/labels/opus-labels-v1.jsonl   (id별 Opus 라벨, 병합본)
      dataset/tool-choice-v1.labeled.jsonl  (train/val 원본 + label + 비교 + 우선순위)
      dataset/labels/agreement-v1.md        (의도 vs Opus 일치 통계)
"""
import json, glob, collections, random, pathlib, sys
HERE = pathlib.Path(__file__).resolve().parent
DS = HERE / "dataset"; LB = DS / "labels"
CLASSES = ["weather","calendar_list","calendar_create","web_search","map_search","fx","mail_read","none"]

def load(p): return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]

def main():
    labels, bad = {}, []
    for f in sorted(glob.glob(str(LB / "opus" / "batch-[0-9][0-9].jsonl"))):
        for i, l in enumerate(open(f, encoding="utf-8"), 1):
            if not l.strip(): continue
            try: o = json.loads(l)
            except Exception as e: bad.append(f"{f}:{i} JSON 오류 {e}"); continue
            if o.get("first") not in CLASSES: bad.append(f"{f}:{i} first 오류 {o.get('first')}"); continue
            o["also_ok"] = [a for a in (o.get("also_ok") or []) if a in CLASSES and a != o["first"]]
            o["sequence"] = [a for a in (o.get("sequence") or []) if a in CLASSES]
            o["needs_confirm"] = bool(o.get("needs_confirm"))
            try: o["confidence"] = float(o.get("confidence", 0))
            except Exception: o["confidence"] = 0.0
            o["note"] = o.get("note") or ""
            o["rule"] = o.get("rule")
            o["batch"] = pathlib.Path(f).stem
            if o["id"] in labels: bad.append(f"{f}:{i} 중복 id {o['id']}")
            labels[o["id"]] = o
    rows = [r for r in load(DS / "tool-choice-v1.all.jsonl") if r["split"] != "gold"]
    missing = [r["id"] for r in rows if r["id"] not in labels]
    extra = set(labels) - {r["id"] for r in rows}
    print(f"라벨 {len(labels)}건, 대상 {len(rows)}건, 누락 {len(missing)}, 대상 외 {len(extra)}, 형식 오류 {len(bad)}")
    for b in bad[:20]: print("  ", b)
    if missing: print("  누락 예:", missing[:10])
    with open(LB / "opus-labels-v1.jsonl", "w", encoding="utf-8") as f:
        for k in sorted(labels): f.write(json.dumps(labels[k], ensure_ascii=False) + "\n")

    rng = random.Random(7)
    out = []
    for r in rows:
        lb = labels.get(r["id"])
        if not lb: continue
        it = r["intended"]
        strict = lb["first"] == it["first"]
        loose = strict or lb["first"] in it["also_ok"] or it["first"] in lb["also_ok"]
        conf_ok = lb["needs_confirm"] == it["needs_confirm"]
        if lb["confidence"] < 0.7: pr, why = 1, "라벨러 확신 낮음"
        elif not loose: pr, why = 2, "생성 의도와 다름"
        elif not strict: pr, why = 3, "also_ok로만 일치"
        elif not conf_ok: pr, why = 3, "확인필요 불일치"
        else: pr, why = 4, ""
        o = dict(r); o["label"] = {k: lb[k] for k in ["first","also_ok","sequence","needs_confirm","rule","confidence","note"]}
        o["cmp"] = {"strict": strict, "loose": loose, "confirm_ok": conf_ok, "priority": pr, "why": why}
        o["_rnd"] = rng.random()
        out.append(o)
    out.sort(key=lambda o: (o["cmp"]["priority"], o["_rnd"]))
    with open(DS / "tool-choice-v1.labeled.jsonl", "w", encoding="utf-8") as f:
        for o in out:
            o2 = dict(o); o2.pop("_rnd"); f.write(json.dumps(o2, ensure_ascii=False) + "\n")

    # 통계
    C = collections.Counter; n = len(out)
    def rate(lst, key): 
        return f"{sum(1 for o in lst if key(o))}/{len(lst)} ({sum(1 for o in lst if key(o))/max(1,len(lst)):.1%})"
    L = [f"# 생성 의도 vs Opus 5.5 라벨 일치 (v1, {n}건: train+val)", ""]
    L += [f"- first 완전 일치: {rate(out, lambda o: o['cmp']['strict'])}",
          f"- also_ok 포함 일치: {rate(out, lambda o: o['cmp']['loose'])}",
          f"- needs_confirm 일치: {rate(out, lambda o: o['cmp']['confirm_ok'])}",
          f"- Opus confidence < 0.7: {sum(1 for o in out if o['label']['confidence'] < 0.7)}건",
          f"- 검수 우선순위: " + ", ".join(f"{k}순위 {v}건" for k, v in sorted(C(o['cmp']['priority'] for o in out).items())),
          "  (1=확신 낮음, 2=의도와 다름, 3=also_ok로만 일치·확인필요 불일치, 4=일치)", ""]
    L += ["## 클래스별(생성 의도 기준) first 일치", "", "| 의도 클래스 | 건수 | 완전 일치 | also_ok 포함 |", "|---|---|---|---|"]
    for c in CLASSES:
        sub = [o for o in out if o["intended"]["first"] == c]
        L.append(f"| {c} | {len(sub)} | {rate(sub, lambda o: o['cmp']['strict'])} | {rate(sub, lambda o: o['cmp']['loose'])} |")
    for title, key in [("유형", lambda o: o["type"]), ("언어", lambda o: o["lang"]), ("맥락", lambda o: "있음" if o["context"] else "없음")]:
        L += ["", f"## {title}별 first 완전 일치", ""]
        for k in sorted({key(o) for o in out}):
            sub = [o for o in out if key(o) == k]
            L.append(f"- {k}: {rate(sub, lambda o: o['cmp']['strict'])}")
    L += ["", "## 혼동 행렬 (행=생성 의도, 열=Opus first)", "", "| 의도\\Opus | " + " | ".join(CLASSES) + " |", "|---|" + "---|"*len(CLASSES)]
    for a in CLASSES:
        cnt = C(o["label"]["first"] for o in out if o["intended"]["first"] == a)
        L.append(f"| {a} | " + " | ".join(str(cnt.get(b, 0)) if cnt.get(b, 0) else "·" for b in CLASSES) + " |")
    L += ["", "## Opus first 분포", ""] + [f"- {k}: {v}" for k, v in C(o["label"]["first"] for o in out).most_common()]
    L += ["", "## 불일치 예시 (2순위 중 무작위 20건)", ""]
    for o in [o for o in out if o["cmp"]["priority"] == 2][:20]:
        ctx = (" [맥락: " + o["context"].replace("\n", " / ") + "]") if o["context"] else ""
        L.append(f"- `{o['id']}` {o['request']}{ctx} → 의도 {o['intended']['first']} / Opus {o['label']['first']} ({o['label']['confidence']:.2f}) {o['label']['note']}")
    (LB / "agreement-v1.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:12]))

if __name__ == "__main__":
    main()
