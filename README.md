# Can Abnormal IoT Traffic Be Detected?

**Behavioral Detection of Botnet-Infected IoT Devices using Machine Learning**

Computer Security Project — data-driven security analysis of IoT botnet traffic.

---

## Dataset

| Field | Value |
|---|---|
| **Name** | N-BaIoT Dataset to Detect IoT Botnet Attacks |
| **Kaggle URL** | https://www.kaggle.com/datasets/mkashifn/nbaiot-dataset |
| **Description** | Real network traffic from nine commercial IoT devices (doorbells, thermostat, baby monitor, security cameras, webcam) captured first under normal operation, then after authentic infection with the **Mirai** and **BASHLITE (Gafgyt)** botnets. Each record holds 115 behavioral statistics — packet size, packet count, and packet jitter — aggregated across five time windows (100 ms, 500 ms, 1.5 s, 10 s, 1 min). |
| **Target** | Constructed binary label: `0 = benign`, `1 = malicious` |

**Cite the dataset:** Kashif, M. (2020). *N-BaIoT Dataset to Detect IoT Botnet Attacks* [Data set]. Kaggle.

---

## Security problem

IoT devices are routinely compromised and conscripted into botnets such as Mirai. They cannot run endpoint security software, so the only scalable control is **network-side monitoring** — observing traffic behavior from a gateway or IDS and flagging deviation from a device's own baseline.

**Research question:** *Can behavioral network-traffic features accurately distinguish benign IoT traffic from botnet-infected IoT traffic?*

---

## Repository contents

```
Computer Security Project/
├── proposal.md                 # Deliverable A — 1-page project proposal
├── iot_botnet_detection.ipynb  # Deliverable B — analysis notebook (run on Google Colab)
├── README.md                   # this file
├── requirements.txt            # Python dependencies
├── data/                       # N-BaIoT CSVs (not in git — download from Releases)
├── report/
│   └── report.tex              # Deliverable C — final report (LaTeX, for Overleaf)
└── presentation/
    └── presentation_outline.md # Deliverable D — 10–15 min talk outline + Q&A
```

The final report is written in LaTeX on Overleaf; the notebook exports
ready-to-paste LaTeX tables from every evaluation section.

---

## Running the project

### Step 0 — Get the dataset (once)

**Option A — this repository's release** (no login, fastest):
<https://github.com/manganjokean/computer-security-project/releases/tag/nbaiot-data>
Nine `.tar.gz` archives — one per device — plus the dataset's own
description file: **1.77 GB compressed** (7.58 GB extracted). Extract all
nine next to the notebook; each unpacks straight into its device folder:

```bash
tar -xzf Danmini_Doorbell.tar.gz     # macOS / Linux / Windows 10+ (tar is built in)
```

**Option B — Kaggle** (free account required):
<https://www.kaggle.com/datasets/mkashifn/nbaiot-dataset> → **Download**

**Option C — UCI mirror** (no login, identical data):
```
https://archive.ics.uci.edu/static/public/442/detection+of+iot+botnet+attacks+n+baiot.zip
```

> ⚠️ **The UCI archive ships the attack traffic inside `.rar` files**, not as
> CSVs. Extract each `mirai_attacks.rar` and `gafgyt_attacks.rar` into a
> subfolder named after the botnet inside its device folder — keeping them in
> *separate* subfolders matters, because both botnets ship a file called
> `scan.csv`:
>
> ```
> data/
>   Danmini_Doorbell/
>     benign_traffic.csv
>     mirai/    ack.csv scan.csv syn.csv udp.csv udpplain.csv
>     gafgyt/   combo.csv junk.csv scan.csv tcp.csv udp.csv
> ```
>
> The finished folder holds ~90 CSVs across 9 device folders (≈7.6 GB). The
> notebook detects an un-extracted archive and tells you what to do rather than
> silently loading only benign traffic.

### Option A — Google Colab (recommended)

1. Go to <https://colab.research.google.com/> → **File → Upload notebook** →
   select `iot_botnet_detection.ipynb`.
2. Put the extracted `data/` folder somewhere reachable (Drive mount is easiest).
   If you skip this, the notebook prompts you to upload the zip when it runs.
3. **Runtime → Run all.** CPU runtime is sufficient — no GPU needed.
4. Expect **roughly 10–20 minutes** for the full 7.6 GB corpus.

### Option B — Local Jupyter

```bash
pip install -r requirements.txt
jupyter notebook iot_botnet_detection.ipynb
```

Place the extracted dataset in a folder named `data/`, `nbaiot-dataset/`,
`N-BaIoT/`, `dataset/`, or next to the notebook — the loader searches all of
them automatically.

### Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `No usable CSV files found` | Dataset isn't in a searched folder — use the upload prompt or rename your folder `data` |
| `AssertionError: No attack CSVs found…` | The `.rar` archives were never extracted |
| `Dataset not found — upload nbaiot-dataset.zip` | The upload box appeared; select your zip |
| `jinja2` / `to_latex` error | `pip install jinja2` (preinstalled on Colab) |

### Reproducibility

Every random seed is fixed at `SEED = 42`. Sampling, train/test split, model
initialization, and the SHAP subsample are all deterministic, so re-running
produces identical metrics.

---

## What the notebook does

| § | Rubric step | Contents |
|---|---|---|
| 1 | Select a Kaggle Dataset | Dataset metadata, file inventory, feature descriptions |
| 2 | Define a Security Problem | Mirai/BASHLITE threat model, research question |
| 3 | Data Exploration | Class/device distributions, missing values, duplicates, log-scaled feature distributions, correlation heatmap, effect-size ranking |
| 4 | Data Preprocessing | Deduplication, stratified split, variance + correlation pruning, median imputation, one-hot encoding, standardization, class weighting — each justified in place |
| 5 | Security Analysis / ML | Logistic Regression, Random Forest, XGBoost, Isolation Forest (trained on benign only) |
| 6 | Model Evaluation | Accuracy, precision, recall, F1, ROC-AUC, confusion matrices, **FPR/FNR**, per-device and per-attack breakdowns, operational alert-volume translation |
| 7 | Security Interpretation | What is detected, which attacks are missed, FP/FN consequences, deployment design, limitations |
| 8 | Advanced component | SHAP summary plot + feature importance + single-flow explanations |
| 9 | Conclusion & References | Answer to the research question, citations |

### Methods and why they were chosen

- **Logistic Regression** — interpretable baseline; each coefficient is a signed
  weight on a traffic statistic.
- **Random Forest** — captures non-linear and interaction effects; built-in
  feature importance; robust to skewed input.
- **XGBoost** — strongest tabular performance; exposes SHAP values for
  explainability.
- **Isolation Forest** — *unsupervised anomaly detection* trained on **benign
  traffic only**, so it never sees an attack. This is the closest analogue to a
  real IDS that cannot enumerate every future attack signature.

---

## Results (summary)

Sampled 150,304 of **7,062,606** records · 115 → **36** features after pruning ·
120,166 train / 30,042 test (**2,416 benign / 27,626 malicious**) · `SEED = 42`

| Model | Acc | Prec | Recall | F1 | ROC-AUC | **FPR** | **FNR** |
|---|---|---|---|---|---|---|---|
| Logistic Regression | 0.9992 | 0.9996 | 0.9996 | 0.9996 | 0.9989 | 0.0046 | 0.0004 |
| Random Forest | 0.9999 | 1.0000 | 0.9999 | 1.0000 | 1.0000 | 0.0000 | 0.0001 |
| **XGBoost** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **0.0000** | **0.0000** |
| Isolation Forest | 0.2978 | 0.9706 | 0.2438 | 0.3897 | 0.8835 | 0.0844 | 0.7562 |

**Headline findings**

1. **Supervised detection works across the fleet.** XGBoost F1 = 1.0000 on
   eight of nine devices (0.9999 on the Ecobee); Random Forest ≥ 0.9998
   everywhere; Logistic Regression dips only to 0.9982.
2. **Unsupervised anomaly detection fails on the attacks that matter most.**
   The Isolation Forest detected `mirai_scan` and `mirai_syn` **0%** of the
   time and `gafgyt_scan` at 2.3% — the propagation phase — while catching only
   the three highest-rate Mirai floods (~0.65). Overall it missed **3 of every
   4 attack instances**.
3. **The signal is volume and burstiness, not payload.** `MI_dir_L0.1_weight`
   averages 14.5 benign vs **3,689.6** infected (**254×**); the top two
   features, `HpHp_L0.01_radius` (0.6898) and `HH_L0.01_pcc` (0.1829), carry
   **87%** of XGBoost's total gain — both are socket/channel statistics over
   the shortest, 10 ms window.
4. **Accuracy is the wrong headline metric.** At 1,000,000 benign flows/day the
   measured FPRs translate to **4,553 false alerts/day** (Logistic Regression)
   and **84,437/day** (Isolation Forest) — while the latter also misses
   ~7,562 attacks/day.
5. **The "zero" FPR is not certified.** Only 2,416 benign flows reached the test
   set, so by the rule of three the true FPR is only bounded to ≲0.124% (95%
   CI) — up to ~1,242 alerts/day. Combined with a corpus that is 91.9%
   malicious (**11.4 : 1**, the inverse of production), every precision figure
   here is optimistic.

Full interpretation: notebook §7 and report §Security Analysis.

---

## Academic integrity

- The dataset is cited above and in the notebook's References section.
- The original N-BaIoT paper (Meidan et al., arXiv:1805.03409) is cited.
- All code, analysis, and visualizations in this repository were written for
  this project. No external Kaggle notebook was reproduced.
- Libraries used: scikit-learn, XGBoost, SHAP, pandas, NumPy, Matplotlib, Seaborn.
