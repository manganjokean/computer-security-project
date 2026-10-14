# Project Proposal

## Project Title

**Can Abnormal IoT Traffic Be Detected? Behavioral detection of botnet-infected IoT devices using machine learning**

---

## Kaggle Dataset

| Field | Details |
|---|---|
| **Dataset name** | N-BaIoT Dataset to Detect IoT Botnet Attacks |
| **Kaggle URL** | https://www.kaggle.com/datasets/mkashifn/nbaiot-dataset |
| **Description** | Real network traffic captured from nine commercial IoT devices — doorbells, a thermostat, a baby monitor, security cameras, and a webcam — first under normal operation, then after being authentically infected with the **Mirai** and **BASHLITE (Gafgyt)** botnets. Rather than raw packets, each record holds 115 behavioral statistics summarizing packet sizes, packet counts, and packet jitter across five time windows (100 ms, 500 ms, 1.5 s, 10 s, 1 min). |
| **Number of records** | ≈150,000-row stratified sample drawn from the full corpus (555,932 benign instances reported across the nine devices in the original study; exact Kaggle file counts verified when the dataset is loaded) |
| **Number of features** | 115 behavioral features, plus a device identifier that is one-hot encoded during preprocessing |
| **Target variable** | Constructed binary label: `0 = benign`, `1 = malicious` |
| **Important features** | Packet-size mean/variance (outbound), packet count, packet jitter mean/variance/count, and combined inbound/outbound packet-size magnitude, radius, covariance, and correlation — each aggregated by source IP, source MAC-IP, channel, and socket over the five temporal windows |

**Citation:** Kashif, M. (2020). *N-BaIoT Dataset to Detect IoT Botnet Attacks* [Data set]. Kaggle. https://www.kaggle.com/datasets/mkashifn/nbaiot-dataset
Underlying study: Meidan, Y. et al. (2018). *N-BaIoT: Network-based Detection of IoT Botnet Attacks Using Deep Autoencoders*. arXiv:1805.03409.

---

## Security Problem

IoT devices are routinely compromised and conscripted into botnets such as Mirai, which was used to launch some of the largest distributed denial-of-service attacks on record. These devices cannot run endpoint antivirus or host-based agents: they are resource-constrained, physically exposed, frequently left unpatched, and often abandoned by their manufacturers.

The only practical line of defense is therefore **network-side monitoring** — observing a device's traffic behavior from a gateway or intrusion detection system and flagging deviations that indicate it has been compromised. If an infected device can be identified *while it is attacking*, it can be quarantined within seconds rather than days, which stops the botnet from propagating and cuts short outbound attack traffic. Automated, behavior-based detection of compromised IoT devices is consequently a high-value and directly deployable security control.

---

## Research Question

> **Can behavioral network-traffic features accurately distinguish benign IoT traffic from botnet-infected IoT traffic?**

Supporting questions:

1. Which attack types (flooding, scanning, junk traffic) are hardest to detect?
2. Which traffic features are most indicative of a compromised device?
3. What false-positive rate is operationally acceptable in a real detection system?

---

## Proposed Methodology

1. **Data preparation** — Load the per-device benign and attack CSV files from Kaggle, construct the binary `label` column and the `device`/`attack` metadata columns, remove duplicate records, and sample the corpus to a reproducible size.
2. **Exploratory data analysis** — Examine class and per-device distributions, missing values, duplicate records, feature distributions (log-scaled), correlations among high-variance features, and the features that separate benign from malicious traffic most strongly.
3. **Preprocessing** — Remove near-zero-variance features and prune highly correlated features (115 → ~40); median-impute any missing values; one-hot encode the device identifier; standardize features with a scaler fit on training data only; perform a stratified train/test split keyed on `device × label` so that no device is over-represented in one partition; and address class imbalance using balanced class weights.
4. **Modeling (four methods)** — Logistic Regression as an interpretable baseline, Random Forest, XGBoost, and Isolation Forest trained on benign traffic only as an unsupervised anomaly-detection comparison.
5. **Evaluation** — Accuracy, precision, recall, F1-score, ROC-AUC, confusion matrix, and explicit false-positive and false-negative rates, reported both overall and per device, exported as LaTeX tables for the report.
6. **Explainability** — SHAP analysis and feature-importance ranking to identify exactly which traffic statistics signal compromise.

---

## Expected Results

All supervised models are expected to exceed **98–99% accuracy**, with XGBoost and Random Forest performing best; Isolation Forest should catch overt flood attacks but struggle with subtle scanning traffic. Random Forest and SHAP are expected to rank **packet-jitter and packet-count statistics computed over the 1-minute window** as the strongest predictors, indicating that sustained behavioral change — rather than any individual packet — is what exposes a compromised device.

The security-relevant finding is expected to be that **flood attacks (UDP, TCP, ACK, SYN) are detected almost perfectly, while scanning and junk traffic are far harder to catch**, because they resemble ordinary background activity. The report will argue that even a small false-positive rate generates substantial analyst workload at enterprise traffic volume, and that falsely quarantining an active device such as a baby monitor or security camera carries consequences beyond those of a typical IT alert.
