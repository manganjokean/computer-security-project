"""Demo: classify arbitrary input strings with the trained models.

Examples:
  python src/predict.py "<script>alert(1)</script>"
  python src/predict.py "<a href='#'>hello world</a>" --payload "<img src=x onerror=alert(1)>"
  python src/predict.py "some text" --file payload.txt

Loads the saved char TF-IDF baseline (E2) and the augmented TextCNN (E4).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import joblib
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from models import CharVocab, build_model


def load_textcnn(tag: str = "textcnn_aug"):
    ckpt = torch.load(config.MODEL_DIR / f"{tag}.pt", map_location="cpu", weights_only=False)
    vocab = CharVocab.load(config.MODEL_DIR / "char_vocab.json")
    model = build_model(ckpt["model_name"], ckpt["vocab_size"])
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    return model, vocab


def textcnn_prob(model, vocab, text: str) -> float:
    ids = torch.tensor([vocab.encode(text, config.MAX_SEQ_LEN)], dtype=torch.long)
    with torch.no_grad():
        return float(torch.softmax(model(ids), dim=1)[0, 1])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("payload", nargs="?", help="input string to classify")
    ap.add_argument("--file", help="read input from a file instead")
    ap.add_argument("--tag", default="textcnn_aug",
                    choices=["textcnn_clean", "textcnn_aug"], help="TextCNN checkpoint")
    args = ap.parse_args()

    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    elif args.payload:
        text = args.payload
    else:
        ap.error("provide a payload or --file")

    char_pipe = joblib.load(config.MODEL_DIR / "baseline_char_tfidf.joblib")
    word_pipe = joblib.load(config.MODEL_DIR / "baseline_word_tfidf.joblib")
    model, vocab = load_textcnn(args.tag)

    baseline_char = float(char_pipe.predict_proba([text])[0, 1])
    baseline_word = float(word_pipe.predict_proba([text])[0, 1])
    deep = textcnn_prob(model, vocab, text)

    verdict = lambda p: "XSS (flagged)" if p >= config.THRESHOLD else "benign (allowed)"
    print(f"Input: {text[:120]!r}")
    print(f"  E1 word TF-IDF + LogReg : p={baseline_word:.4f}  -> {verdict(baseline_word)}")
    print(f"  E2 char TF-IDF + LogReg : p={baseline_char:.4f}  -> {verdict(baseline_char)}")
    print(f"  E4 TextCNN + augment    : p={deep:.4f}  -> {verdict(deep)}")


if __name__ == "__main__":
    main()
