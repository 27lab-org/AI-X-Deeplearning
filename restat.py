"""문장을 지우거나 고친 뒤 통계 파일만 다시 만든다(id·분할·라벨은 건드리지 않음).
사용: python3 restat.py
출력: dataset/stats.md, dataset/labels/agreement-v1.md, dataset/stats-v2add.md
v2 추가분의 일치 통계는 python3 build_v2add.py merge 로 다시 만든다.
"""
import json, collections, pathlib
HERE = pathlib.Path(__file__).resolve().parent; DS = HERE / "dataset"
C = collections.Counter
def load(p): return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
def classes(p): return [c["id"] for c in json.load(open(HERE / p, encoding="utf-8"))["classes"]]
def rate(lst, key):
    k = sum(1 for o in lst if key(o)); return f"{k}/{len(lst)} ({k/max(1,len(lst)):.1%})"

def stats(rows, CL, title, splits, new=()):
    n = len(rows)
    L = [title, "", f"- 총 {n}건", "", "## 클래스 × 분할", "", "| 클래스 | " + " | ".join(splits) + " | 합계 |", "|---|" + "---|" * (len(splits) + 1)]
    for c in CL:
        k = C(r["split"] for r in rows if r["intended"]["first"] == c)
        if sum(k.values()): L.append(f"| {c}{' (새)' if c in new else ''} | " + " | ".join(str(k[s]) for s in splits) + f" | {sum(k.values())} |")
    t = C(r["split"] for r in rows); L.append("| **합계** | " + " | ".join(str(t[s]) for s in splits) + f" | {n} |")
    for name, key in [("언어", lambda r: r["lang"]), ("유형", lambda r: r["type"]), ("맥락 있음", lambda r: "있음" if r["context"] else "없음"),
                      ("확인 필요", lambda r: "예" if r["intended"]["needs_confirm"] else "아니오"), ("also_ok 있음", lambda r: "있음" if r["intended"]["also_ok"] else "없음")]:
        k = C(key(r) for r in rows); L += ["", f"## {name}", ""] + [f"- {a}: {b} ({b/n:.0%})" for a, b in k.most_common()]
    return "\n".join(L) + "\n"

def agreement(out, CL, title):
    L = [title, "", f"- first 완전 일치: {rate(out, lambda o: o['cmp']['strict'])}", f"- also_ok 포함 일치: {rate(out, lambda o: o['cmp']['loose'])}",
         f"- needs_confirm 일치: {rate(out, lambda o: o['cmp']['confirm_ok'])}", f"- Opus confidence < 0.7: {sum(1 for o in out if o['label']['confidence'] < 0.7)}건",
         "- 검수 우선순위: " + ", ".join(f"{k}순위 {v}건" for k, v in sorted(C(o['cmp']['priority'] for o in out).items())),
         "  (1=확신 낮음, 2=의도와 다름, 3=also_ok로만 일치·확인필요 불일치, 4=일치)", "",
         "## 클래스별(생성 의도 기준) first 일치", "", "| 의도 클래스 | 건수 | 완전 일치 | also_ok 포함 |", "|---|---|---|---|"]
    for c in CL:
        sub = [o for o in out if o["intended"]["first"] == c]
        L.append(f"| {c} | {len(sub)} | {rate(sub, lambda o: o['cmp']['strict'])} | {rate(sub, lambda o: o['cmp']['loose'])} |")
    for name, key in [("유형", lambda o: o["type"]), ("언어", lambda o: o["lang"]), ("맥락", lambda o: "있음" if o["context"] else "없음")]:
        L += ["", f"## {name}별 first 완전 일치", ""]
        for k in sorted({key(o) for o in out}): L.append(f"- {k}: {rate([o for o in out if key(o) == k], lambda o: o['cmp']['strict'])}")
    L += ["", "## 혼동 행렬 (행=생성 의도, 열=Opus first)", "", "| 의도\\Opus | " + " | ".join(CL) + " |", "|---|" + "---|" * len(CL)]
    for a in CL:
        cnt = C(o["label"]["first"] for o in out if o["intended"]["first"] == a)
        L.append(f"| {a} | " + " | ".join(str(cnt.get(b, 0)) if cnt.get(b, 0) else "·" for b in CL) + " |")
    L += ["", "## Opus first 분포", ""] + [f"- {k}: {v}" for k, v in C(o["label"]["first"] for o in out).most_common()]
    L += ["", "## 불일치 예시 (2순위)", ""]
    for o in [o for o in out if o["cmp"]["priority"] == 2][:20]:
        ctx = (" [맥락: " + o["context"].replace("\n", " / ") + "]") if o["context"] else ""
        L.append(f"- `{o['id']}` {o['request']}{ctx} → 의도 {o['intended']['first']} / Opus {o['label']['first']} ({o['label']['confidence']:.2f}) {o['label']['note']}")
    return "\n".join(L) + "\n"

if __name__ == "__main__":
    c1, c2 = classes("tools.json"), classes("tools-v2.json")
    (DS / "stats.md").write_text(stats(load(DS / "tool-choice-v1.all.jsonl"), c1, "# 데이터셋 v1 통계 (일상 요청만, Dev·Ops 제외)", ["train", "val", "gold"]), encoding="utf-8")
    out = load(DS / "tool-choice-v1.labeled.jsonl")
    (DS / "labels" / "agreement-v1.md").write_text(agreement(out, c1, f"# 생성 의도 vs Opus 5.5 라벨 일치 (v1, {len(out)}건: train+val)"), encoding="utf-8")
    (DS / "stats-v2add.md").write_text(stats(load(DS / "tool-choice-v2add.all.jsonl"), c2, "# v2 추가분 통계 (Hermes 기본 툴 클래스, 일상 요청만)", ["train", "val", "holdout"], new=[c for c in c2 if c not in c1]), encoding="utf-8")
    print(open(DS / "labels" / "agreement-v1.md", encoding="utf-8").read()[:300])
