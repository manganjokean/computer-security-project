# Assignment 6 — XSS Payload Detection with Deep Learning

A research-oriented machine learning project on **Cross-Site Scripting (XSS)
detection**: classify untrusted user input as malicious XSS or benign HTML,
and investigate whether a **character-level deep learning model with
obfuscation augmentation** is more *robust* to evasive payloads than strong
traditional-ML baselines.

---

## 1. Research problem

**Research topic.** Cross-Site Scripting (XSS) attack detection on untrusted
web input (ties directly to this assignment's XSS security theme: untrusted
input → input validation / output encoding → mitigation).

**Problem statement.** Signature- and keyword-based XSS filters are evaded by
obfuscation (mixed case, HTML entities, NUL bytes, comment splitting,
whitespace tricks). Classic ML detectors trained on *clean* payloads may
likewise learn spurious surface features and lose accuracy on obfuscated
variants — the variants attackers actually use.

**Research question.**
> Can a character-level TextCNN trained with *obfuscation augmentation*
> detect obfuscated XSS payloads more reliably than TF-IDF + Logistic
> Regression baselines, without sacrificing performance on clean input?

**Research objective.** Measure and improve the **robustness** (recall on
obfuscated payloads) and **false-positive safety** (FPR on entity-encoded
benign HTML) of XSS detectors, not just clean-set accuracy.

**Dataset.** [XSS dataset (Hugging Face: AmirAliGharesoufloo/XSS)](https://huggingface.co/datasets/AmirAliGharesoufloo/XSS)
— 13,686 labeled HTML snippets (`Sentence`, `Label` ∈ {0 benign, 1 XSS}),
public, no login. Benign examples are Wikipedia-style HTML fragments; XSS
examples are payloads with event handlers / script vectors. Downloaded
automatically by `src/data_prep.py`.

## 2. Why this method (and the baselines)

| Model | Role | Rationale |
|---|---|---|
| E0 Length-only LogReg | sanity baseline | exposes the dataset's length confound (benign ≈ 160 chars vs XSS ≈ 62) |
| E1 Word TF-IDF + LogReg | classic baseline | standard text classification reference |
| E2 Char n-gram TF-IDF + LogReg | strong baseline | characters are the natural unit for payloads; hard to beat |
| E3 TextCNN | proposed architecture | multi-kernel convs learn local patterns (`<script`, `onerror=`, `javascript:`) at several lengths; CPU-friendly |
| E4 **TextCNN + obfuscation augmentation** | **proposed improvement** | training-time exposure to transformed payloads teaches invariance to the evasions the baselines rely on surface form for |
| E5 BiLSTM (optional) | DL comparison | sequential model; run with `--include-bilstm` (slower on CPU) |

**Proposed improvement (E4).** Address the limitation "models learn surface
features, not attack semantics" by applying random obfuscation transforms
(mixed case, HTML entities, URL-encoding, NUL bytes, comment splitting,
whitespace) to **positive training samples only**, with probability 0.5.
Expected effect: detection rate on obfuscated test payloads improves, with
little clean-set cost. Tested against E3 (identical model, no augmentation) —
a clean ablation of the augmentation component.

## 3. Experimental design

- **Split:** stratified 70/15/15 train/val/test, `seed=42`, done **after**
  deduplication (2,716 duplicate payloads removed → 10,854 unique rows) to
  prevent identical payloads leaking across splits.
- **Cleaning:** whitespace-only snippets removed (they made the task trivial).
- **Model selection:** `C` for LR is chosen on the **validation** split;
  TextCNN uses early stopping on validation F1 (patience 3, max 12 epochs).
  The test split is touched **once**, at the end.
- **Robustness sets (built from the held-out test split only):**
  - `test_obfuscated.json` — every XSS test payload × 7 transforms (7,693 samples)
  - `test_benign_encoded.json` — benign test HTML with all special characters
    entity-encoded (530 samples) → false-positive probe
  - *Stored as JSON, not CSV: pandas silently truncates strings at NUL bytes
    when reading CSV, which corrupted an early version of the null_bytes
    evaluation (`ab\x00cd` → `ab`). The bug was caught by the mitigation
    probe and is documented here as a reproducibility lesson.*
- **Metrics:** Accuracy, Precision, **Recall**, **F1**, **PR-AUC**, **FPR** +
  confusion counts; robustness = detection rate per obfuscation transform.
  Accuracy alone is not trusted for a security problem.
- **Compute:** CPU-only, char sequences padded/truncated to 300 chars,
  batch 64, Adam (lr 1e-3). Full suite runs in minutes on a laptop.

## 4. Results

Clean held-out test set (seed 42; `results/metrics.md` for all runs):

| Model | Acc | Prec | Recall | F1 | PR-AUC | FPR |
|---|---|---|---|---|---|---|
| E0 Length-only LogReg | 0.7581 | 0.7613 | 0.9345 | 0.8391 | 0.8345 | 0.6075 |
| E1 Word TF-IDF + LogReg | 0.9982 | 0.9973 | 1.0000 | 0.9986 | 1.0000 | 0.0057 |
| E2 Char n-gram TF-IDF + LogReg | 0.9994 | 1.0000 | 0.9991 | 0.9995 | 1.0000 | **0.0000** |
| E3 TextCNN | 0.9982 | 1.0000 | 0.9973 | 0.9986 | 1.0000 | **0.0000** |
| **E4 TextCNN + augment** | 0.9988 | 1.0000 | 0.9982 | 0.9991 | 1.0000 | **0.0000** |

**The clean test set does not separate the models — the robustness sets do**
(this is the research finding):

| Model | Obfuscated-XSS detection | FPR on encoded benign | Train time |
|---|---|---|---|
| E0 Length-only | 0.7693 | 0.1283 | <1 s |
| E1 Word TF-IDF + LogReg | 0.9457 | 0.0075 | <1 s |
| E2 Char TF-IDF + LogReg | 0.9705 | 0.0057 | 3 s |
| E3 TextCNN | 0.9828 | 0.0075 | 56 s |
| **E4 TextCNN + augment** | **0.9996** | **0.0906** | 100 s |

Per-transform detection (E3 → E4, `results/robustness.md`):
`combined` 0.943 → **1.000**, `html_entity` 0.979 → **1.000**, `url_encode`
0.981 → **1.000**, `mixed_case` 0.997 → **1.000**, `comment_split` 0.986 →
**1.000**, `null_bytes` 0.995 → 0.998.

**Seed stability** (3 seeds, `results/seed_stability.md`):
obfuscated detection E3 = 0.9896 ± 0.0066 vs E4 = **0.9995 ± 0.0001** —
the augmentation wins on every seed and is also *less* variable.
Clean F1 is statistically tied (0.9991 ± 0.0005 both).

**Honest limitations**

1. **Clean-set scores are saturated** (~0.999 for every serious model); this
   dataset separates easily, so the meaningful differences appear only under
   obfuscation. The E0 row shows a real length confound (FPR 0.61) that the
   other models largely avoid.
2. **Trade-off:** augmentation raises the false-positive rate on
   *entity-encoded benign HTML* (E4 mean 0.062 vs E3 0.009). An augmented
   model is more sensitive to entity-encoded content — exactly what escaped
   user text looks like. In deployment this argues for threshold tuning or
   encoding-aware validation rather than a single global threshold.
3. **A data-integrity bug mattered:** an early pipeline stored hard sets as
   CSV, where pandas truncates strings at NUL bytes, understating robustness
   by ~17 points. The fixed (JSON) pipeline and the mitigation probe
   (`results/normalization_probe.md`) show models handle NUL payloads
   directly, so input normalization adds nothing here — augmentation is what
   buys the robustness.
4. Single dataset, synthetic benign/attack provenance; results should be
   replicated on real request logs before operational conclusions.

Figures: `results/figures/fig_clean_metrics.png`,
`fig_robustness.png`, `fig_training_curves.png`.

---

## 5. How to reproduce

```bash
# 1. environment (Python 3.10+)
pip install -r requirements.txt          # CPU torch wheel is fine

# 2. download + clean + split data (auto-downloads the CSV)
python src/data_prep.py

# 3. run everything: E0-E4 baselines + deep models, tables, figures
python src/run_experiments.py

# optional variants
python src/run_experiments.py --seeds 42,43,44  # seed-stability repeat (~9 min)
python src/run_experiments.py --include-bilstm  # also train the BiLSTM (slower)

# 4. try it on your own payloads
python src/predict.py "<script>alert(1)</script>"
python src/predict.py "<a href='#'>hello</a>"
```

Outputs land in `results/`:

| File | Contents |
|---|---|
| `metrics.md`, `metrics.csv` | clean-test comparison of all models |
| `robustness.md`, `robustness_per_transform.csv` | detection rate per obfuscation transform |
| `seed_stability.md`, `.csv` | mean ± std across seeds (E3/E4) |
| `normalization_probe.md` | NUL-byte mitigation probe (inference only) |
| `figures/fig_clean_metrics.png` | F1 / PR-AUC / Recall / FPR bar chart |
| `figures/fig_robustness.png` | robustness by transform |
| `figures/fig_training_curves.png` | training loss & validation F1 (E3 vs E4) |
| `experiments.json` | raw results for downstream analysis |
| `models/` | trained TextCNN checkpoints, vocab, saved LR pipelines |

## 6. Project layout

```
├── data/                    # raw CSV + processed splits (generated)
├── src/
│   ├── config.py            # paths, seeds, hyperparameters
│   ├── data_prep.py         # download, clean, dedup, stratified split, hard sets
│   ├── obfuscation.py       # 7 XSS obfuscation transforms + augmentation helper
│   ├── baseline.py          # E0/E1/E2 traditional-ML baselines
│   ├── models.py            # CharVocab, TextCNN, BiLSTM (PyTorch)
│   ├── train_dl.py          # training loop, early stopping, augmentation
│   ├── evaluate.py          # metrics shared by all models
│   ├── run_experiments.py   # orchestrator: tables + figures
│   ├── normalization_probe.py # NUL-byte mitigation probe
│   └── predict.py           # classify arbitrary input with saved models
└── results/                 # generated tables, figures, checkpoints
```

## 7. Security note

The payloads in this dataset are **inert strings used for research**; the
project does not execute them. Detection is only one layer of defense — the
assignment's core controls (**input validation, output/HTML encoding,
CSP, secure handling of user-generated content**) remain the primary
mitigation; an ML detector is a complementary signal, not a replacement.
