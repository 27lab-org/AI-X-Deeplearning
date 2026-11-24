"""기준선: 글자 n-gram TF-IDF + 로지스틱 회귀 (CPU, 수 초). 학생 모델이 이보다 나아야 의미가 있다.

    python train/baseline_tfidf.py [--labels gold|opus] [--eval-test]
"""
import argparse
import json
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score

ROOT = Path(__file__).resolve().parent.parent


def rows(p, key):
    rs = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    return [r for r in rs if r[key]]


def text(r):
    return f"{r['context']}\n{r['request']}" if r.get("context") else r["request"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data"))
    ap.add_argument("--labels", choices=["gold", "opus"], default="gold")
    ap.add_argument("--eval-test", action="store_true")
    a = ap.parse_args()
    d = Path(a.data)
    labels = json.load(open(d / "labels.json", encoding="utf-8"))
    tr = rows(d / "train.jsonl", a.labels)
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(1, 4), sublinear_tf=True, min_df=2)
    X = vec.fit_transform([text(r) for r in tr])
    clf = LogisticRegression(max_iter=3000, C=10, class_weight="balanced").fit(X, [r[a.labels] for r in tr])
    splits = ["val"] + (["test"] if a.eval_test else [])
    res = {}
    for s in splits:
        ev = rows(d / f"{s}.jsonl", "gold")
        pred = clf.predict(vec.transform([text(r) for r in ev]))
        y = [r["gold"] for r in ev]
        loose = [p == r["gold"] or p in (r.get("gold_also_ok") or []) for p, r in zip(pred, ev)]
        res[s] = {"n": len(ev), "acc": round(accuracy_score(y, pred), 4),
                  "loose_acc": round(sum(loose) / len(ev), 4),
                  "macro_f1": round(f1_score(y, pred, average="macro", labels=labels, zero_division=0), 4)}
    print(json.dumps({"train_labels": a.labels, "train_n": len(tr), **res}, indent=1))


if __name__ == "__main__":
    main()
