"""Inference-time normalization probe (mitigation experiment).

Security problem:  NUL-byte injection (`sc\x00ript`, `on\x00error=`) breaks
                   character patterns inside tags, so both the TF-IDF baseline
                   and the TextCNN miss ~90% of these payloads.

Security control:  INPUT NORMALIZATION as a pre-processing defense layer
                   (strip NUL bytes, then re-evaluate).

Expected mitigation: detection of NUL-obfuscated payloads is restored without
retraining, demonstrating the classic lesson that input validation /
sanitization complements detection models.

Runs entirely on saved artifacts (results/models/) - no retraining needed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import joblib
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
import data_prep
import train_dl
from models import CharVocab
from predict import load_textcnn, textcnn_prob


def normalize(s: str) -> str:
    """The mitigation: strip NUL bytes (a legitimate, safe normalization)."""
    return s.replace("\x00", "")


def main() -> None:
    obf = data_prep.load_hard_set("test_obfuscated")
    null_set = obf[obf["transform"] == "null_bytes"].reset_index(drop=True)
    print(f"null_bytes subset: {len(null_set)} payloads")

    char_pipe = joblib.load(config.MODEL_DIR / "baseline_char_tfidf.joblib")
    model, vocab = load_textcnn("textcnn_aug")

    rows = []
    for label, fn in [("raw", lambda s: s), ("NUL-stripped", normalize)]:
        texts = null_set["Sentence"].map(fn).tolist()
        base_flagged = (char_pipe.predict_proba(texts)[:, 1] >= config.THRESHOLD).mean()
        cnn_flagged = sum(textcnn_prob(model, vocab, t) >= config.THRESHOLD
                          for t in texts) / len(texts)
        rows.append({
            "input handling": label,
            "E2 Char TF-IDF + LogReg": base_flagged,
            "E4 TextCNN + augment": cnn_flagged,
        })

    table = pd.DataFrame(rows).set_index("input handling")
    print("\nDetection rate on NUL-obfuscated XSS payloads:")
    print(table.round(4).to_string())
    out = config.RESULTS_DIR / "normalization_probe.md"
    out.write_text(
        "# Mitigation probe: NUL-byte obfuscation\n\n"
        "Detection rate on the `null_bytes` subset of the obfuscated test set, "
        "before and after stripping NUL bytes from the input (input "
        "normalization as a defense layer; no retraining).\n\n"
        + table.round(4).to_markdown() + "\n", encoding="utf-8")
    print(f"\nSaved {out}")


if __name__ == "__main__":
    main()
