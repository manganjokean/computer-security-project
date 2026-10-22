"""Shared evaluation utilities for all models.

For a security problem with (roughly) balanced classes but asymmetric costs,
we report more than accuracy:
  * Recall (attack detection rate) and False Positive Rate are the operationally
    critical numbers for an XSS filter.
  * PR-AUC summarizes precision/recall trade-offs and is robust to how the
    decision threshold is chosen.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

import config


def compute_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = config.THRESHOLD,
) -> dict:
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    y_pred = (y_prob >= threshold).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    fpr = fp / (fp + tn) if (fp + tn) else 0.0

    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "pr_auc": average_precision_score(y_true, y_prob),
        "roc_auc": roc_auc_score(y_true, y_prob) if len(np.unique(y_true)) > 1 else float("nan"),
        "fpr": fpr,
        "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
    }


def format_metrics_table(rows: list[dict], cols: list[str]) -> str:
    """Render a list of metric dicts as a GitHub-flavored markdown table."""
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    lines = [header, sep]
    for r in rows:
        cells = []
        for c in cols:
            v = r.get(c, "")
            if isinstance(v, float):
                cells.append(f"{v:.4f}" if np.isfinite(v) else "n/a")
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)
