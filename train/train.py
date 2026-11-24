"""학생 모델 학습 (PyTorch Lightning): 사전학습 인코더 + 분류 헤드 18클래스 전체 미세조정

수업 연결: Lightning(9주) · BERT 분류(10주) · 전이학습(11주)

예:
    # 스모크 테스트 (몇 배치만, 파이프라인 확인용)
    python train/train.py --smoke
    # 본 학습: laya-ko 인코더 + 사람 골드 라벨
    python train/train.py --backbone laya:2nugu/laya-ko --labels gold --epochs 5
    # H2 비교: 같은 설정, Opus 라벨로 학습 (평가는 항상 골드)
    python train/train.py --backbone laya:2nugu/laya-ko --labels opus
    # 최종 시험셋 평가 (설정 확정 후 한 번만)
    python train/train.py ... --eval-test

입력 문장: "[이전 대화]\n[요청]" (맥락 없으면 요청만). 검증 지표: acc, macro-F1, loose acc(also_ok 포함).
결과: runs/<이름>/ (체크포인트, metrics.csv, val_predictions.jsonl, config.json)
"""
import argparse
import json
import random
import time
from pathlib import Path

import lightning as L
import torch
import torch.nn as nn
import torch.nn.functional as F
from lightning.pytorch.callbacks import EarlyStopping, ModelCheckpoint
from lightning.pytorch.loggers import CSVLogger
from torch.utils.data import DataLoader, Dataset

ROOT = Path(__file__).resolve().parent.parent
torch.set_float32_matmul_precision("high")


# ---------- 인코더 불러오기 ----------
def load_backbone(spec: str):
    """spec:
    - 'laya:<repo>'  laya 결정 모델(mmBERT/ModernBERT 인코더 + 결정 헤드)에서 인코더 가중치만 꺼냄
    - 그 밖         Hugging Face AutoModel 이름 (예: jhu-clsp/mmBERT-base, klue/roberta-base)
    반환: (encoder, tokenizer)
    """
    from transformers import AutoConfig, AutoModel, AutoTokenizer
    if spec.startswith("laya:"):
        from huggingface_hub import snapshot_download
        from safetensors.torch import load_file
        repo = spec[5:]
        d = Path(snapshot_download(repo, allow_patterns=["encoder/*", "tokenizer/*", "model.safetensors"]))
        cfg = AutoConfig.from_pretrained(d / "encoder")
        enc = AutoModel.from_config(cfg)
        sd = load_file(d / "model.safetensors")
        sd = {k[len("encoder."):]: v.float() for k, v in sd.items() if k.startswith("encoder.")}
        missing, unexpected = enc.load_state_dict(sd, strict=False)
        if unexpected or [m for m in missing if "rotary" not in m]:
            raise RuntimeError(f"laya 인코더 가중치 불일치: missing={missing[:5]} unexpected={unexpected[:5]}")
        tok = AutoTokenizer.from_pretrained(d / "tokenizer")
        return enc, tok
    return AutoModel.from_pretrained(spec), AutoTokenizer.from_pretrained(spec)


# ---------- 데이터 ----------
def read_jsonl(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def text_of(r):
    return f"{r['context']}\n{r['request']}" if r.get("context") else r["request"]


class ToolDS(Dataset):
    def __init__(self, rows, lab2id, label_key, soft_also_ok):
        self.rows, self.lab2id, self.key, self.soft = rows, lab2id, label_key, soft_also_ok

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        r = self.rows[i]
        y = self.lab2id[r[self.key]]
        n = len(self.lab2id)
        t = torch.zeros(n)
        also = [self.lab2id[a] for a in r.get(f"{self.key}_also_ok") or [] if a in self.lab2id and a != r[self.key]]
        if self.soft > 0 and also:  # also_ok 에 확률을 조금 나눠 줌 (소프트 라벨)
            t[also] = self.soft / len(also)
            t[y] = 1 - self.soft
        else:
            t[y] = 1.0
        loose = torch.zeros(n, dtype=torch.bool)
        loose[y] = True
        for a in r.get("gold_also_ok") or []:
            if a in self.lab2id:
                loose[self.lab2id[a]] = True
        return {"text": text_of(r), "y": y, "target": t, "loose": loose, "idx": i}


class ToolDM(L.LightningDataModule):
    def __init__(self, args, tokenizer):
        super().__init__()
        self.a, self.tok = args, tokenizer
        self.labels = json.load(open(Path(args.data) / "labels.json", encoding="utf-8"))
        self.lab2id = {c: i for i, c in enumerate(self.labels)}

    def setup(self, stage=None):
        a = self.a
        d = Path(a.data)
        tr = [r for r in read_jsonl(d / "train.jsonl") if r[a.labels]]
        if a.drop_written_by:
            tr = [r for r in tr if r.get("written_by") != a.drop_written_by]
        if a.train_size and a.train_size < len(tr):  # 데이터 양 실험 (500/1200/2400)
            tr = random.Random(a.seed).sample(tr, a.train_size)
        va = [r for r in read_jsonl(d / "val.jsonl") if r["gold"]]  # 검증·평가는 항상 사람 골드
        te = [r for r in read_jsonl(d / "test.jsonl") if r["gold"]]
        if a.smoke:
            tr, va, te = tr[:64], va[:32], te[:32]
        self.train_rows, self.val_rows, self.test_rows = tr, va, te
        self.train_ds = ToolDS(tr, self.lab2id, a.labels, a.soft_also_ok)
        self.val_ds = ToolDS(va, self.lab2id, "gold", 0)
        self.test_ds = ToolDS(te, self.lab2id, "gold", 0)

    def collate(self, batch):
        enc = self.tok([b["text"] for b in batch], padding=True, truncation=True,
                       max_length=self.a.max_len, return_tensors="pt")
        enc["y"] = torch.tensor([b["y"] for b in batch])
        enc["target"] = torch.stack([b["target"] for b in batch])
        enc["loose"] = torch.stack([b["loose"] for b in batch])
        enc["idx"] = torch.tensor([b["idx"] for b in batch])
        return enc

    def _dl(self, ds, shuffle):
        return DataLoader(ds, batch_size=self.a.batch_size, shuffle=shuffle,
                          collate_fn=self.collate, num_workers=0)

    def train_dataloader(self):
        return self._dl(self.train_ds, True)

    def val_dataloader(self):
        return self._dl(self.val_ds, False)

    def test_dataloader(self):
        return self._dl(self.test_ds, False)


# ---------- 모델 ----------
class ToolClassifier(L.LightningModule):
    def __init__(self, encoder, n_classes, args):
        super().__init__()
        self.save_hyperparameters(ignore=["encoder"])
        self.encoder = encoder
        h = encoder.config.hidden_size
        self.head = nn.Sequential(nn.Dropout(args.dropout), nn.Linear(h, n_classes))
        self.a = args
        self._val = []

    def forward(self, input_ids, attention_mask):
        out = self.encoder(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state
        m = attention_mask.unsqueeze(-1).to(out.dtype)
        pooled = (out * m).sum(1) / m.sum(1).clamp(min=1)  # 평균 풀링
        return self.head(pooled)

    def _loss(self, logits, target):
        return F.cross_entropy(logits, target, label_smoothing=self.a.label_smoothing)

    def training_step(self, b, _):
        logits = self(b["input_ids"], b["attention_mask"])
        loss = self._loss(logits.float(), b["target"])
        self.log("train_loss", loss, prog_bar=True)
        return loss

    def _eval_step(self, b):
        logits = self(b["input_ids"], b["attention_mask"]).float()
        loss = F.cross_entropy(logits, b["y"])
        self._val.append((logits.softmax(-1).cpu(), b["y"].cpu(), b["loose"].cpu(), b["idx"].cpu()))
        return loss

    def validation_step(self, b, _):
        self.log("val_loss", self._eval_step(b), prog_bar=True)

    def test_step(self, b, _):
        self.log("test_loss", self._eval_step(b))

    def _eval_end(self, prefix):
        from sklearn.metrics import f1_score
        if not self._val:
            return
        p = torch.cat([x[0] for x in self._val])
        y = torch.cat([x[1] for x in self._val])
        loose = torch.cat([x[2] for x in self._val])
        idx = torch.cat([x[3] for x in self._val])
        pred = p.argmax(-1)
        acc = (pred == y).float().mean().item()
        lacc = loose[torch.arange(len(pred)), pred].float().mean().item()
        f1 = f1_score(y.numpy(), pred.numpy(), average="macro", labels=list(range(p.shape[1])), zero_division=0)
        self.log_dict({f"{prefix}_acc": acc, f"{prefix}_loose_acc": lacc, f"{prefix}_macro_f1": f1}, prog_bar=True)
        self.last_eval = (prefix, p, pred, idx)
        self._val = []

    def on_validation_epoch_end(self):
        self._eval_end("val")

    def on_test_epoch_end(self):
        self._eval_end("test")

    def configure_optimizers(self):
        a = self.a
        nd = ["bias", "norm", "LayerNorm"]
        groups = [
            {"params": [p for n, p in self.encoder.named_parameters() if not any(x in n for x in nd)],
             "lr": a.lr, "weight_decay": a.weight_decay},
            {"params": [p for n, p in self.encoder.named_parameters() if any(x in n for x in nd)],
             "lr": a.lr, "weight_decay": 0.0},
            {"params": self.head.parameters(), "lr": a.lr_head, "weight_decay": a.weight_decay},
        ]
        opt = torch.optim.AdamW(groups)
        total = self.trainer.estimated_stepping_batches
        warm = max(1, int(total * a.warmup))
        # 선형 warmup 후 선형 감소
        sched = torch.optim.lr_scheduler.LambdaLR(
            opt, lambda s: (s + 1) / warm if s < warm else max(0.0, (total - s) / max(1, total - warm)))
        return {"optimizer": opt, "lr_scheduler": {"scheduler": sched, "interval": "step"}}


def dump_predictions(path, rows, labels, last_eval):
    _, p, pred, idx = last_eval
    with open(path, "w", encoding="utf-8") as f:
        for prob, pr, i in zip(p, pred, idx):
            r = rows[int(i)]
            top = prob.topk(3)
            f.write(json.dumps({
                "id": r["id"], "lang": r["lang"], "request": r["request"], "gold": r["gold"],
                "pred": labels[int(pr)], "conf": round(float(prob[pr]), 4),
                "top3": [[labels[int(j)], round(float(v), 4)] for v, j in zip(top.values, top.indices)],
            }, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data"))
    ap.add_argument("--backbone", default="laya:2nugu/laya-ko")
    ap.add_argument("--labels", choices=["gold", "opus"], default="gold", help="학습 라벨 (평가는 항상 골드)")
    ap.add_argument("--drop-written-by", default=None, help="예: daniel (관리자가 단 골드 빼기)")
    ap.add_argument("--train-size", type=int, default=0)
    ap.add_argument("--soft-also-ok", type=float, default=0.0, help="also_ok 에 나눠 줄 확률 (예 0.1)")
    ap.add_argument("--label-smoothing", type=float, default=0.0)
    ap.add_argument("--max-len", type=int, default=128)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--lr-head", type=float, default=1e-3)
    ap.add_argument("--weight-decay", type=float, default=0.01)
    ap.add_argument("--warmup", type=float, default=0.1)
    ap.add_argument("--dropout", type=float, default=0.1)
    ap.add_argument("--patience", type=int, default=2)
    ap.add_argument("--precision", default="bf16-mixed")
    ap.add_argument("--devices", default="1")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--name", default=None)
    ap.add_argument("--eval-test", action="store_true", help="학습 후 시험셋 평가 (설정 확정 후에만)")
    ap.add_argument("--smoke", action="store_true", help="64건 1에폭, 파이프라인 확인용")
    a = ap.parse_args()
    if a.smoke:
        a.epochs, a.batch_size = 1, 8
    if not torch.cuda.is_available() and a.precision.startswith("bf16"):
        a.precision = "32-true"

    L.seed_everything(a.seed, workers=True)
    name = a.name or f"{a.backbone.split('/')[-1]}-{a.labels}-s{a.seed}-{time.strftime('%m%d-%H%M')}"
    out = ROOT / "runs" / name
    out.mkdir(parents=True, exist_ok=True)
    json.dump(vars(a), open(out / "config.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    t0 = time.time()
    enc, tok = load_backbone(a.backbone)
    dm = ToolDM(a, tok)
    dm.setup()
    print(f"train {len(dm.train_rows)} / val {len(dm.val_rows)} / test {len(dm.test_rows)}  "
          f"classes {len(dm.labels)}  encoder params {sum(p.numel() for p in enc.parameters()) / 1e6:.0f}M")
    model = ToolClassifier(enc, len(dm.labels), a)

    ckpt = ModelCheckpoint(dirpath=out, filename="best", monitor="val_macro_f1", mode="max", save_top_k=1)
    trainer = L.Trainer(
        max_epochs=a.epochs, precision=a.precision, devices=a.devices if torch.cuda.is_available() else 1,
        accelerator="auto", logger=CSVLogger(out, name="", version=""),
        callbacks=[ckpt, EarlyStopping("val_macro_f1", mode="max", patience=a.patience)],
        log_every_n_steps=10, deterministic=False, gradient_clip_val=1.0,
        limit_train_batches=8 if a.smoke else 1.0, num_sanity_val_steps=0,
    )
    trainer.fit(model, datamodule=dm)

    best = ckpt.best_model_path
    if best:
        model.load_state_dict(torch.load(best, map_location="cpu", weights_only=False)["state_dict"])
    res = trainer.validate(model, datamodule=dm, verbose=False)[0]
    dump_predictions(out / "val_predictions.jsonl", dm.val_rows, dm.labels, model.last_eval)
    if a.eval_test:
        res.update(trainer.test(model, datamodule=dm, verbose=False)[0])
        dump_predictions(out / "test_predictions.jsonl", dm.test_rows, dm.labels, model.last_eval)
    res["minutes"] = round((time.time() - t0) / 60, 2)
    json.dump(res, open(out / "result.json", "w"), indent=1)
    print(json.dumps(res, indent=1))
    if a.smoke and best:  # 스모크 체크포인트는 크니 지움
        Path(best).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
