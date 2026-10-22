"""Orchestrate the full experiment suite and write results.

Usage:
  python src/run_experiments.py                 # E0-E4 (fast, CPU)
  python src/run_experiments.py --include-bilstm # also train E5 BiLSTM (slower)
  python src/run_experiments.py --seeds 42,43,44 # seed-stability repeat of E3/E4

Outputs (results/):
  metrics.csv, metrics.md       - per-model comparison tables
  robustness.md                 - per-transform obfuscation recall / FPR
  seed_stability.md, .csv       - mean/std of key metrics across seeds
  normalization_probe.md        - NUL-byte mitigation probe (inference only)
  figures/fig_clean_metrics.png - F1 / PR-AUC / Recall / FPR comparison
  figures/fig_robustness.png    - recall by obfuscation transform
  figures/fig_training_curves.png - TextCNN training dynamics (with/without aug)
  experiments.json              - full raw results for reproducibility
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
import evaluate

CLEAN_COLS = ["model", "accuracy", "precision", "recall", "f1", "pr_auc", "fpr"]
SUMMARY_COLS = ["model", "train_time_s", "obf_recall", "ben_fpr"]


def ensure_data() -> None:
    needed = ["train.csv", "val.csv", "test.csv", "test_obfuscated.json",
              "test_benign_encoded.json"]
    if all((config.PROCESSED_DIR / f).exists() for f in needed):
        return
    print("Processed splits not found -> running data_prep ...")
    import data_prep
    data_prep.main()


def flatten(results: list[dict]) -> list[dict]:
    return [{**{k: v for k, v in r.items() if k not in ("clean", "history", "obf_by_transform")},
             **r["clean"]} for r in results]


def write_tables(results: list[dict]) -> None:
    rows = flatten(results)
    df = pd.DataFrame(rows)
    df.to_csv(config.RESULTS_DIR / "metrics.csv", index=False)

    clean_rows = [{k: r[k] for k in CLEAN_COLS} for r in rows]
    summary_rows = [{k: r[k] for k in SUMMARY_COLS} for r in rows]
    md = ["# Experimental results\n",
          "## Clean held-out test set (stratified 70/15/15 split, seed 42)\n",
          evaluate.format_metrics_table(clean_rows, CLEAN_COLS),
          "\n## Robustness summary\n",
          "`obf_recall` = fraction of obfuscated XSS payloads still detected "
          "(mean over 7 transforms); `ben_fpr` = false positive rate on "
          "entity-encoded benign HTML.\n",
          evaluate.format_metrics_table(summary_rows, SUMMARY_COLS)]
    (config.RESULTS_DIR / "metrics.md").write_text("\n".join(md), encoding="utf-8")

    # Per-transform robustness table (deep models only have this detail)
    per_t = [r for r in results if "obf_by_transform" in r]
    if per_t:
        df_t = pd.DataFrame({
            r["model"]: pd.Series(r["obf_by_transform"]) for r in per_t
        }).sort_index()
        lines = ["# Obfuscation robustness: detection rate per transform\n",
                 df_t.round(4).to_markdown()]
        (config.RESULTS_DIR / "robustness.md").write_text("\n".join(lines), encoding="utf-8")
        df_t.to_csv(config.RESULTS_DIR / "robustness_per_transform.csv")


def fig_clean_metrics(results: list[dict]) -> None:
    rows = flatten(results)
    labels = [r["model"].replace(" + ", "\n+") for r in rows]
    metrics = ["f1", "pr_auc", "recall", "fpr"]
    x = np.arange(len(rows))
    width = 0.2
    fig, ax = plt.subplots(figsize=(10, 5))
    for i, m in enumerate(metrics):
        vals = [r[m] for r in rows]
        bars = ax.bar(x + (i - 1.5) * width, vals, width, label=m)
        ax.bar_label(bars, fmt="%.3f", fontsize=6, padding=1)
    ax.set_xticks(x, labels, fontsize=8)
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("score")
    ax.set_title("Clean test set: baseline vs. proposed deep models")
    ax.legend(ncols=4, fontsize=8)
    ax.axhline(1.0, color="gray", lw=0.5, ls=":")
    fig.tight_layout()
    fig.savefig(config.FIGURE_DIR / "fig_clean_metrics.png", dpi=150)
    plt.close(fig)


def fig_robustness(results: list[dict]) -> None:
    per_t = [r for r in results if "obf_by_transform" in r]
    if not per_t:
        return
    df = pd.DataFrame({r["model"]: pd.Series(r["obf_by_transform"]) for r in per_t})
    # Add baselines' single aggregate value as a flat reference line
    for r in results:
        if "obf_by_transform" not in r:
            df[r["model"]] = r["obf_recall"]
    df = df.sort_index()
    ax = df.plot(kind="bar", figsize=(11, 5), rot=30)
    ax.set_ylabel("detection rate on obfuscated XSS payloads")
    ax.set_ylim(0, 1.08)
    ax.set_title("Robustness: detection rate by obfuscation transform")
    ax.legend(fontsize=8, loc="lower right")
    for container in ax.containers:
        ax.bar_label(container, fmt="%.2f", fontsize=6, padding=1)
    fig = ax.get_figure()
    fig.tight_layout()
    fig.savefig(config.FIGURE_DIR / "fig_robustness.png", dpi=150)
    plt.close(fig)


def fig_training_curves(histories: dict) -> None:
    if not histories:
        return
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    for name, h in histories.items():
        ax1.plot(h["epoch"], h["train_loss"], marker="o", ms=3, label=name)
        ax2.plot(h["epoch"], h["val_f1"], marker="o", ms=3, label=name)
    ax1.set_xlabel("epoch"); ax1.set_ylabel("training loss"); ax1.set_title("Training loss")
    ax2.set_xlabel("epoch"); ax2.set_ylabel("validation F1"); ax2.set_title("Validation F1 (early stopping)")
    for ax in (ax1, ax2):
        ax.legend(fontsize=8); ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(config.FIGURE_DIR / "fig_training_curves.png", dpi=150)
    plt.close(fig)


def write_stability(stability: list[dict]) -> None:
    if not stability:
        return
    df = pd.DataFrame(stability)
    df.to_csv(config.RESULTS_DIR / "seed_stability.csv", index=False)
    show = df.copy()
    for c in show.columns:
        if c.endswith("_mean"):
            base = c[:-5]
            if f"{base}_std" in show.columns:
                show[c] = show[c].map("{:.4f}".format) + " ± " + \
                    show[f"{base}_std"].map("{:.4f}".format)
                show = show.drop(columns=[f"{base}_std"])
    lines = ["# Seed stability (E3/E4 repeated over several random seeds)\n",
             "Mean ± std across seeds; higher is better except FPR columns.\n",
             show.to_markdown(index=False)]
    (config.RESULTS_DIR / "seed_stability.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the XSS detection experiments")
    parser.add_argument("--include-bilstm", action="store_true",
                        help="also train the optional BiLSTM (E5; slower on CPU)")
    parser.add_argument("--seeds", default="42",
                        help="comma-separated seeds for E3/E4 repeats (e.g. 42,43,44)")
    args = parser.parse_args()
    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]

    for d in (config.RESULTS_DIR, config.FIGURE_DIR, config.MODEL_DIR):
        d.mkdir(parents=True, exist_ok=True)

    ensure_data()
    import data_prep
    splits = {n: pd.read_csv(config.PROCESSED_DIR / f"{n}.csv")
              for n in ("train", "val", "test")}
    test_obf = data_prep.load_hard_set("test_obfuscated")
    test_ben_enc = data_prep.load_hard_set("test_benign_encoded")
    print(f"train={len(splits['train'])} val={len(splits['val'])} "
          f"test={len(splits['test'])} obf={len(test_obf)} ben_enc={len(test_ben_enc)}")

    t_all = time.time()
    print("\n=== Baselines (E0-E2) ===")
    import baseline
    base_results, _ = baseline.run_baselines(splits, test_obf, test_ben_enc)
    for r in base_results:
        c = r["clean"]
        print(f"  {r['model']:<30} F1={c['f1']:.4f} PR-AUC={c['pr_auc']:.4f} "
              f"Recall={c['recall']:.4f} FPR={c['fpr']:.4f} obf_recall={r['obf_recall']:.4f}")

    print("\n=== Deep models (E3-E4{}) ===".format(", E5" if args.include_bilstm else ""))
    import train_dl
    deep_results, histories, stability = train_dl.run_deep_models(
        splits, test_obf, test_ben_enc, include_bilstm=args.include_bilstm,
        seeds=seeds)
    for r in deep_results:
        c = r["clean"]
        print(f"  {r['model']:<30} F1={c['f1']:.4f} PR-AUC={c['pr_auc']:.4f} "
              f"Recall={c['recall']:.4f} FPR={c['fpr']:.4f} obf_recall={r['obf_recall']:.4f} "
              f"({r['train_time_s']:.0f}s)")

    results = base_results + deep_results
    write_tables(results)
    write_stability(stability)
    fig_clean_metrics(results)
    fig_robustness(results)
    fig_training_curves(histories)

    with open(config.RESULTS_DIR / "experiments.json", "w", encoding="utf-8") as f:
        json.dump(flatten(results), f, indent=2, default=str)

    print("\n=== Mitigation probe (NUL-byte normalization) ===")
    try:
        import normalization_probe
        normalization_probe.main()
    except Exception as exc:  # pragma: no cover - probe is supplementary
        print(f"  probe skipped: {exc}")

    print(f"\nAll done in {time.time() - t_all:.0f}s. See {config.RESULTS_DIR}")


if __name__ == "__main__":
    main()
