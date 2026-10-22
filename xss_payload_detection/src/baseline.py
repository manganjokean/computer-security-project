"""Baselines: traditional ML for XSS payload classification.

Three baselines of increasing strength, all fast on CPU:

  E0  length-only Logistic Regression  - sanity check. The raw dataset has a
      length confound (benign HTML averages ~160 chars, XSS payloads ~60);
      if a length-only model scores well, part of the signal is spurious.
  E1  word TF-IDF + Logistic Regression - classic text classification baseline.
  E2  character n-gram TF-IDF + Logistic Regression - the strongest realistic
      baseline for payload data; characters, not words, are the natural unit.

C (regularization) is tuned on the VALIDATION split only (grid of 3 values,
selected by F1). The test split is never used for model selection.
"""

from __future__ import annotations

import time

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

import config
import evaluate

C_GRID = [0.1, 1.0, 10.0]


def load_splits() -> dict[str, pd.DataFrame]:
    return {
        name: pd.read_csv(config.PROCESSED_DIR / f"{name}.csv")
        for name in ("train", "val", "test")
    }


def _predict_proba(pipeline, texts: pd.Series) -> np.ndarray:
    return pipeline.predict_proba(texts)[:, 1]


def run_length_baseline(splits: dict, test_obf: pd.DataFrame,
                        test_ben_enc: pd.DataFrame) -> dict:
    """Sanity check: can payload LENGTH alone predict the label?"""
    def feats(df):
        lens = np.log1p(df["Sentence"].astype(str).str.len().to_numpy())
        return lens.reshape(-1, 1)

    clf = LogisticRegression(random_state=config.SEED)
    t0 = time.time()
    clf.fit(feats(splits["train"]), splits["train"]["Label"])
    train_time = time.time() - t0

    y_prob = clf.predict_proba(feats(splits["test"]))[:, 1]
    metrics = evaluate.compute_metrics(splits["test"]["Label"], y_prob)
    obf_prob = clf.predict_proba(feats(test_obf))[:, 1]
    ben_prob = clf.predict_proba(feats(test_ben_enc))[:, 1]
    return {
        "model": "E0 Length-only LogReg",
        "train_time_s": train_time,
        "clean": metrics,
        "obf_recall": float((obf_prob >= config.THRESHOLD).mean()),
        "ben_fpr": float((ben_prob >= config.THRESHOLD).mean()),
    }


def _build_pipeline(vectorizer_kwargs: dict, C: float) -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(**vectorizer_kwargs)),
        ("clf", LogisticRegression(C=C, max_iter=1000, random_state=config.SEED)),
    ])


def run_tfidf_baseline(splits: dict, test_obf: pd.DataFrame,
                       test_ben_enc: pd.DataFrame,
                       name: str, vectorizer_kwargs: dict) -> tuple[dict, Pipeline]:
    """Tune C on validation F1, then evaluate the chosen pipeline on the test set."""
    best_C, best_f1, best_pipe = None, -1.0, None
    for C in C_GRID:
        pipe = _build_pipeline(vectorizer_kwargs, C)
        pipe.fit(splits["train"]["Sentence"], splits["train"]["Label"])
        val_prob = _predict_proba(pipe, splits["val"]["Sentence"])
        val_f1 = evaluate.compute_metrics(splits["val"]["Label"], val_prob)["f1"]
        if val_f1 > best_f1:
            best_C, best_f1, best_pipe = C, val_f1, pipe

    # Retrain on train+val with the selected C (test remains untouched).
    train_full = pd.concat([splits["train"], splits["val"]]).reset_index(drop=True)
    t0 = time.time()
    best_pipe.fit(train_full["Sentence"], train_full["Label"])
    train_time = time.time() - t0

    y_prob = _predict_proba(best_pipe, splits["test"]["Sentence"])
    metrics = evaluate.compute_metrics(splits["test"]["Label"], y_prob)
    obf_prob = _predict_proba(best_pipe, test_obf["Sentence"])
    ben_prob = _predict_proba(best_pipe, test_ben_enc["Sentence"])
    result = {
        "model": name,
        "C": best_C,
        "val_f1": best_f1,
        "train_time_s": train_time,
        "clean": metrics,
        "obf_recall": float((obf_prob >= config.THRESHOLD).mean()),
        "ben_fpr": float((ben_prob >= config.THRESHOLD).mean()),
    }
    return result, best_pipe


def run_baselines(splits: dict, test_obf: pd.DataFrame, test_ben_enc: pd.DataFrame):
    """Returns (list of result dicts, dict of saved pipelines)."""
    results = [run_length_baseline(splits, test_obf, test_ben_enc)]

    word_res, word_pipe = run_tfidf_baseline(
        splits, test_obf, test_ben_enc,
        name="E1 Word TF-IDF + LogReg",
        vectorizer_kwargs=dict(
            analyzer="word", ngram_range=(1, 2), min_df=2, max_features=20000,
            lowercase=True,
        ),
    )
    results.append(word_res)

    char_res, char_pipe = run_tfidf_baseline(
        splits, test_obf, test_ben_enc,
        name="E2 Char n-gram TF-IDF + LogReg",
        vectorizer_kwargs=dict(
            analyzer="char", ngram_range=(3, 5), min_df=2, max_features=60000,
            lowercase=True,
        ),
    )
    results.append(char_res)

    config.MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(word_pipe, config.MODEL_DIR / "baseline_word_tfidf.joblib")
    joblib.dump(char_pipe, config.MODEL_DIR / "baseline_char_tfidf.joblib")
    return results, {"word": word_pipe, "char": char_pipe}


if __name__ == "__main__":
    splits = load_splits()
    test_obf = pd.read_csv(config.PROCESSED_DIR / "test_obfuscated.csv")
    test_ben_enc = pd.read_csv(config.PROCESSED_DIR / "test_benign_encoded.csv")
    res, _ = run_baselines(splits, test_obf, test_ben_enc)
    cols = ["model", "accuracy", "precision", "recall", "f1", "pr_auc", "fpr"]
    rows = [{**r, **r["clean"]} for r in res]
    print(evaluate.format_metrics_table(rows, cols))
