"""Train and evaluate the deep models (E3/E4/E5).

  E3  TextCNN, no augmentation            - proposed architecture, plain training
  E4  TextCNN + obfuscation augmentation  - PROPOSED IMPROVEMENT: at training
      time, positive samples are randomly obfuscated so the model learns
      invariance to case changes, HTML entities, NUL bytes, etc.
  E5  BiLSTM (optional, --include-bilstm) - sequential comparison model

Each model trains on the train split with early stopping on validation F1
(patience from config), then the best epoch is evaluated ONCE on the test
split and on the two hard robustness sets.
"""

from __future__ import annotations

import random
import time

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

import config
import evaluate
import obfuscation
from models import CharVocab, build_model


class PayloadDataset(Dataset):
    """Encodes payloads as character-id sequences.

    If ``augment_pos`` is True, positive (XSS) samples are randomly obfuscated
    before encoding. Augmentation is applied ONLY to training data and ONLY
    to the positive class, since entity-encoding benign text does not make it
    malicious.
    """

    def __init__(self, df: pd.DataFrame, vocab: CharVocab, augment_pos: bool = False,
                 seed: int = config.SEED):
        self.texts = df["Sentence"].astype(str).tolist()
        self.labels = df["Label"].astype(int).to_numpy()
        self.vocab = vocab
        self.augment_pos = augment_pos
        self.rng = random.Random(seed)

    def __len__(self) -> int:
        return len(self.texts)

    def __getitem__(self, idx: int):
        text = self.texts[idx]
        if self.augment_pos and self.labels[idx] == 1 and self.rng.random() < config.AUG_PROB:
            text = obfuscation.random_transform(text, self.rng)
        ids = self.vocab.encode(text, config.MAX_SEQ_LEN)
        return (torch.tensor(ids, dtype=torch.long),
                torch.tensor(self.labels[idx], dtype=torch.long))


def train_one_epoch(model, loader, optimizer, criterion, device):
    model.train()
    total_loss, correct, n = 0.0, 0, 0
    for xb, yb in loader:
        xb, yb = xb.to(device), yb.to(device)
        optimizer.zero_grad()
        logits = model(xb)
        loss = criterion(logits, yb)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * len(yb)
        correct += (logits.argmax(1) == yb).sum().item()
        n += len(yb)
    return total_loss / n, correct / n


@torch.no_grad()
def predict_probs(model, texts: list[str], vocab: CharVocab, device) -> np.ndarray:
    model.eval()
    probs = []
    for i in range(0, len(texts), config.BATCH_SIZE):
        batch = texts[i:i + config.BATCH_SIZE]
        xb = torch.tensor([vocab.encode(t, config.MAX_SEQ_LEN) for t in batch],
                          dtype=torch.long, device=device)
        p = torch.softmax(model(xb), dim=1)[:, 1]
        probs.append(p.cpu().numpy())
    return np.concatenate(probs) if probs else np.array([])


def train_model(model_name: str, augment: bool, splits: dict,
                vocab: CharVocab, tag: str, device: str = "cpu",
                seed: int = config.SEED) -> dict:
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)

    train_ds = PayloadDataset(splits["train"], vocab, augment_pos=augment, seed=seed)
    val_ds = PayloadDataset(splits["val"], vocab, augment_pos=False)
    train_loader = DataLoader(train_ds, batch_size=config.BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=config.BATCH_SIZE)

    model = build_model(model_name, len(vocab)).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=config.LEARNING_RATE)

    best_f1, best_state, best_epoch = -1.0, None, -1
    history = {"epoch": [], "train_loss": [], "train_acc": [], "val_f1": []}
    epochs_without_improvement = 0
    t_start = time.time()

    for epoch in range(1, config.MAX_EPOCHS + 1):
        loss, acc = train_one_epoch(model, train_loader, optimizer, criterion, device)
        val_prob = predict_probs(model, val_ds.texts, vocab, device)
        val_f1 = evaluate.compute_metrics(val_ds.labels, val_prob)["f1"]
        history["epoch"].append(epoch)
        history["train_loss"].append(loss)
        history["train_acc"].append(acc)
        history["val_f1"].append(val_f1)
        print(f"  [{tag}] epoch {epoch:2d}  loss {loss:.4f}  train_acc {acc:.4f}  val_f1 {val_f1:.4f}")

        if val_f1 > best_f1:
            best_f1, best_epoch = val_f1, epoch
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= config.PATIENCE:
                print(f"  [{tag}] early stop at epoch {epoch} (best epoch {best_epoch})")
                break

    train_time = time.time() - t_start
    if best_state is not None:
        model.load_state_dict(best_state)

    config.MODEL_DIR.mkdir(parents=True, exist_ok=True)
    torch.save({"model_state": best_state, "model_name": model_name,
                "vocab_size": len(vocab), "best_epoch": best_epoch},
               config.MODEL_DIR / f"{tag}.pt")
    return {"model": model, "train_time_s": train_time, "best_epoch": best_epoch,
            "best_val_f1": best_f1, "n_params": n_params, "history": history}


def evaluate_trained(trained: dict, name: str, vocab: CharVocab,
                     splits: dict, test_obf: pd.DataFrame,
                     test_ben_enc: pd.DataFrame) -> dict:
    model = trained["model"]
    y_prob = predict_probs(model, splits["test"]["Sentence"].astype(str).tolist(), vocab, "cpu")
    metrics = evaluate.compute_metrics(splits["test"]["Label"], y_prob)

    obf_prob = predict_probs(model, test_obf["Sentence"].astype(str).tolist(), vocab, "cpu")
    ben_prob = predict_probs(model, test_ben_enc["Sentence"].astype(str).tolist(), vocab, "cpu")

    obf_by_t = (test_obf.assign(p=obf_prob >= config.THRESHOLD)
                .groupby("transform")["p"].mean())
    return {
        "model": name,
        "train_time_s": trained["train_time_s"],
        "n_params": trained["n_params"],
        "best_val_f1": trained["best_val_f1"],
        "clean": metrics,
        "obf_recall": float((obf_prob >= config.THRESHOLD).mean()),
        "ben_fpr": float((ben_prob >= config.THRESHOLD).mean()),
        "obf_by_transform": obf_by_t.to_dict(),
        "history": trained["history"],
    }


def run_deep_models(splits: dict, test_obf: pd.DataFrame, test_ben_enc: pd.DataFrame,
                    include_bilstm: bool = False, seeds: list[int] | None = None):
    """Train E3/E4 (+ optional E5), possibly repeated over several seeds.

    Returns (results list, histories dict, stability rows). With multiple
    seeds the first seed's checkpoints keep the canonical names (used by
    predict.py); additional seeds get a ``_s<seed>`` suffix. Stability rows
    report mean/std of the key metrics across seeds.
    """
    seeds = seeds or [config.SEED]
    vocab = CharVocab.build(splits["train"]["Sentence"].astype(str).tolist())
    config.MODEL_DIR.mkdir(parents=True, exist_ok=True)
    vocab.save(config.MODEL_DIR / "char_vocab.json")
    print(f"Char vocab size: {len(vocab)} | max_len {config.MAX_SEQ_LEN}")

    plans = [("E3 TextCNN", "textcnn", False, "textcnn_clean"),
             ("E4 TextCNN + augment", "textcnn", True, "textcnn_aug")]
    if include_bilstm:
        plans.append(("E5 BiLSTM", "bilstm", False, "bilstm"))

    results, histories, runs = [], {}, []
    for name, mname, aug, base_tag in plans:
        for si, seed in enumerate(seeds):
            tag = base_tag if si == 0 else f"{base_tag}_s{seed}"
            print(f"Training {name} (seed {seed})")
            t = train_model(mname, augment=aug, splits=splits, vocab=vocab,
                            tag=tag, seed=seed)
            r = evaluate_trained(t, name, vocab, splits, test_obf, test_ben_enc)
            r["seed"] = seed
            runs.append(r)
            if si == 0:
                results.append(r)
                histories[name] = t["history"]
            print(f"  -> F1={r['clean']['f1']:.4f} obf_recall={r['obf_recall']:.4f} "
                  f"ben_fpr={r['ben_fpr']:.4f} ({r['train_time_s']:.0f}s)")

    stability = []
    for name, *_ in plans:
        rs = [r for r in runs if r["model"] == name]
        row = {"model": name, "n_seeds": len(rs)}
        for key, getter in [
            ("clean_f1", lambda r: r["clean"]["f1"]),
            ("clean_pr_auc", lambda r: r["clean"]["pr_auc"]),
            ("clean_fpr", lambda r: r["clean"]["fpr"]),
            ("obf_recall", lambda r: r["obf_recall"]),
            ("ben_fpr", lambda r: r["ben_fpr"]),
        ]:
            vals = np.array([getter(r) for r in rs])
            row[f"{key}_mean"] = float(vals.mean())
            row[f"{key}_std"] = float(vals.std(ddof=1)) if len(vals) > 1 else 0.0
        stability.append(row)

    return results, histories, stability
