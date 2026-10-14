# Presentation Outline — Deliverable D

**Talk length:** 10–15 minutes (≈12 min of content + Q&A)
**Slides recommended:** 10–12
**Deck to build in:** PowerPoint, Google Slides, or LaTeX Beamer

> **Rubric requirement:** the presentation must cover Problem · Dataset ·
> Methodology · Results · Security implications · Conclusion.

---

## Timing plan

| # | Slide | Section | Time |
|---|---|---|---|
| 1 | Title | — | 0:30 |
| 2–3 | The problem | **Problem** | 2:00 |
| 4 | The dataset | **Dataset** | 1:30 |
| 5–7 | How we built it | **Methodology** | 3:00 |
| 8–9 | What we found | **Results** | 3:00 |
| 10–11 | What it means | **Security implications** | 2:30 |
| 12 | Closing | **Conclusion** | 1:00 |
| | **Total** | | **≈13:30** + Q&A |

---

## Slide 1 — Title (0:30)

**Can Abnormal IoT Traffic Be Detected?**
*Behavioral Detection of Botnet-Infected IoT Devices*

- Your name, course, instructor, date
- Dataset credit line: *N-BaIoT, Kaggle (Kashif, 2020)*

> Speaker note: "I'll answer one question: can we tell from network traffic
> alone that an IoT device has been compromised — and can we do it without
> ever touching the device itself?"

---

## SECTION: PROBLEM

### Slide 2 — Why IoT security is different (1:00)

Three constraints that rule out normal defenses:

1. **No endpoint agent possible** — not enough storage, memory, or power
2. **Rarely patched** — vendors abandon devices; users never update
3. **Physically exposed** — same Wi-Fi as laptops; default credentials

**Result:** the only control that scales is *network-side monitoring*.

> Visual: photo/collage of a doorbell camera, thermostat, baby monitor with
> "cannot install antivirus" crossed out.

### Slide 3 — The threat + research question (1:00)

- **Mirai / BASHLITE lifecycle:** propagate → infect → C&C → **execute attacks**
- Mirai powered some of the largest DDoS attacks on record
- We target the **execution stage** — the stage that causes external harm

> **Research question:**
> *Can behavioral network-traffic features accurately distinguish benign IoT
> traffic from botnet-infected IoT traffic?*

---

## SECTION: DATASET

### Slide 4 — N-BaIoT (1:30)

| | |
|---|---|
| **Source** | Kaggle — `kaggle.com/datasets/mkashifn/nbaiot-dataset` |
| **Size** | **7,062,606 records** → **150,304 sampled** (stratified, proportional) |
| **Devices** | 9 commercial devices: doorbells, thermostat, baby monitor, cameras, webcam |
| **Capture** | Real traffic before **and after** authentic infection with Mirai + BASHLITE |
| **Features** | 115 behavioral statistics — 23 stats × 5 time windows (100ms → 1min) |
| **Target** | `0 = benign` · `1 = malicious` |
| **Mix** | **8.1% benign / 91.9% malicious — 11.4 : 1** (inverse of production) |
| **Attacks** | 10 types: Mirai (ACK/Scan/SYN/UDP/UDP-plain) + Gafgyt (Combo/Junk/Scan/TCP/UDP) |

> **Say out loud:** "Not simulated, not emulated — nine real devices were
> actually infected in a lab. And note the class mix: 92% attack traffic.
> That inversion is the biggest caveat in this whole project — I'll come back
> to it."

> Visual: class-distribution bar chart + per-device stacked bar.

---

## SECTION: METHODOLOGY

### Slide 5 — Preprocessing (1:00)

Flow diagram left → right:

**Load → Deduplicate (−96 rows) → Stratified split (`device × label`, 120,166 / 30,042) → Variance/correlation pruning (115 → 36) → Median impute (0 missing) → One-hot encode → Standardize → Class weighting**

Three "why" callouts (pick the ones you're asked about most):
- **Dedupe before split** — flood generators emit identical rows (96 found, 0.06%); otherwise they leak into the test set
- **Correlation pruning** — 334 feature pairs had |r| > 0.95; kept 36 of 115 to avoid redundant collinear inputs
- **Class weighting** — 92% of training rows are malicious; accuracy would reward guessing the majority class

### Slide 6 — Four methods, two assumptions (1:00)

| Model | Type | Why it's here |
|---|---|---|
| Logistic Regression | Supervised, linear | Interpretable baseline |
| Random Forest | Supervised, ensemble | Non-linear interactions + importance |
| XGBoost | Supervised, boosting | Best tabular performance + SHAP |
| **Isolation Forest** | **Unsupervised anomaly detection** | **Trained on benign only — never sees an attack** |

> **Key line:** "Isolation Forest is the only model that behaves like a real
> IDS — it can't enumerate attacks it's never seen, so it learns what *normal*
> looks like."

### Slide 7 — Evaluation design (1:00)

Metrics: Accuracy · Precision · Recall · F1 · ROC-AUC · Confusion Matrix · **FPR** · **FNR**

> **Framing sentence:** *"For security, accuracy is not the objective.
> A false negative leaves a device attacking from inside your network.
> A false positive can take a safety-critical camera offline."*

---

## SECTION: RESULTS

### Slide 8 — Headline metrics (1:30)

| Model | Acc | Prec | Recall | F1 | AUC | **FPR** | **FNR** |
|---|---|---|---|---|---|---|---|
| Logistic Regression | 0.9992 | 0.9996 | 0.9996 | 0.9996 | 0.9989 | 0.0046 | 0.0004 |
| Random Forest | 0.9999 | 1.0000 | 0.9999 | 1.0000 | 1.0000 | 0.0000 | 0.0001 |
| **XGBoost** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **0.0000** | **0.0000** |
| Isolation Forest | 0.2978 | 0.9706 | 0.2438 | 0.3897 | 0.8835 | 0.0844 | 0.7562 |

- Overlay the **ROC curve figure** with AUC values
- Best model: **XGBoost** (F1 1.0000); Random Forest ties on AUC

> **Accuracy = 1.0000 · F1 = 1.0000 · ROC-AUC = 1.0000** *(XGBoost)*
>
> ⚠️ **Immediately under-cut it yourself:** *"Zero false positives on only
> 2,416 benign test flows. By the rule of three, the 95% upper bound is
> 0.124% — up to 1,242 false alerts/day. I can't certify a zero FPR from
> this test set, and neither can anyone else with 2,416 samples."*

### Slide 9 — Where it succeeds and where it fails (1:30)

- **Confusion matrix** figure (best model)
- **Detection rate by attack type** table

| Attack | RF | XGBoost | Isolation Forest |
|---|---|---|---|
| mirai_udpplain / udp / ack | 1.0000 | 1.0000 | 0.65 |
| gafgyt_junk | 1.0000 | 1.0000 | **0.0274** |
| gafgyt_scan | 1.0000 | 1.0000 | **0.0226** |
| gafgyt_combo | 1.0000 | 1.0000 | **0.0024** |
| gafgyt_tcp · mirai_scan · mirai_syn | 0.9997–1.0000 | 1.0000 | **0.0000** |

- **Per-device F1:** XGBoost 1.0000 on 8/9 devices (0.9999 on Ecobee); Isolation Forest **0.0015 on Ennio Doorbell and Samsung webcam** — worse than random

> **The sentence that earns marks:** "Supervised models caught 9 of 10 attack
> types at 1.0000. **The anomaly detector scored 0.0000 on scanning** — and
> scanning is the propagation phase, so a miss means the botnet keeps growing.
> Overall it missed three out of every four attacks."

---

## SECTION: SECURITY IMPLICATIONS

### Slide 10 — False positives vs false negatives (1:15)

Two-column slide:

| **False positive** — measured | **False negative** — measured |
|---|---|
| Logistic Regression: 11 FP on 2,416 benign → **4,553 false alerts/day** | Isolation Forest: **20,890 missed attacks** → ~**7,562 missed/day** |
| Isolation Forest: 204 FP → **84,437 false alerts/day** | Logistic Regression: 12 · Random Forest: 2 · XGBoost: 0 |
| RF / XGBoost: 0 FP — but only bounded to ≲0.124% (2,416 samples) | Missed device keeps **scanning → botnet grows** |
| Auto-quarantine takes a **baby monitor offline** = safety & privacy outage | Device keeps DDoS-ing third parties → legal/reputational exposure |
| | Inside foothold for lateral movement + exfiltration |

> **Bottom line:** *"Missed detection is far more damaging than a false
> alarm — which is why we report FNR, not accuracy, as the headline. And note
> the asymmetry: the cheapest failure for an operator is 4,553 false alerts a
> day; the expensive one is a device quietly inside your network."*

### Slide 11 — Feature importance + deployment (1:15)

**Top features (XGBoost gain) — top two = 87% of total:**

| Feature | Importance | Means |
|---|---|---|
| `HpHp_L0.01_radius` | **0.6898** | burstiness on one socket, last 10 ms |
| `HH_L0.01_pcc` | **0.1829** | correlation of source/dest rates, last 10 ms |
| `HH_jit_L5_mean` | 0.0442 | channel jitter, last 5 s |

- **SHAP confirms:** `HH_jit_L5_mean` contributed **+6.75** to the example malicious flow (all others ≤ +0.54); `MI_dir_L0.01_weight` contributed **−5.05** to the benign one
- Interpret physically: an infected device moves **254× more packets in 0.1 s** (14.5 → 3,689.6). Compromise is a **sustained behavioural shift**, not one bad packet
- **Deployment:** edge gateway / access point · pooled **supervised** model works fleet-wide, **anomaly** model must be per-device · tiered thresholds (auto-quarantine vs. analyst) · periodic re-baselining

---

## SECTION: CONCLUSION

### Slide 12 — Closing (1:00)

**Answer:** *Can abnormal IoT traffic be detected?* → **Yes — with caveats.**
_XGBoost F1 = 1.0000 · ROC-AUC = 1.0000, and it holds across all nine devices
(F1 = 1.0000 on eight, 0.9999 on the Ecobee thermostat)._

Four takeaways:
1. **Network-side detection works for devices that can't protect themselves** — no agent, no patch, no vendor cooperation
2. **Floods easy, scanning hard — and it's the anomaly detector that fails it** (0.0000 on `mirai_scan`/`mirai_syn`)
3. Signal is **volume + socket burstiness at the 10 ms window**, not malware content (14.5 → 3,689.6 packets/0.1 s)
4. **Accuracy is the wrong metric for security** — FPR and FNR are what operators feel

**Limitations (say at least two):** lab vs. production traffic · **inverted class prior (92% malicious)** · **only 2,416 benign test flows → true FPR only bounded to ≲0.124%** · random rather than chronological split · no adversarial testing · two botnet families only.

---

## Likely Q&A — and how to answer

**Q: Your accuracy is ~99%. Isn't this a solved problem?**
> "On this benchmark, yes. But that's exactly why the rubric says accuracy
> isn't the goal. Three caveats: the corpus is **92% attack traffic** — 11.4
> malicious records per benign one — which is the inverse of production, so
> precision will collapse under a realistic prior; we split randomly rather
> than chronologically, so near-identical consecutive flow snapshots may
> straddle the split; and with only 2,416 benign test flows, a measured zero
> false-positive rate only bounds the true rate to about 0.124%. All three
> inflate the number."

**Q: The Isolation Forest only got F1 = 0.39. Does that mean anomaly detection is useless?**
> "No — it means *this configuration* of it is. One pooled model, default
> contamination, no per-device baseline, no threshold tuning, no voting
> window. The original N-BaIoT paper reached 100% TPR with one deep
> autoencoder **per device** and thresholds optimised on held-out benign
> traffic. The gap is the security lesson: anomaly detection is extremely
> sensitive to per-device baselining, and a naively configured detector can be
> worse than useless. That's also why our per-device results show it collapsing
> to 0.0015 F1 on two devices while a pooled supervised model stays at 1.0000."

**Q: Why four models instead of two?**
> "The rubric requires two. I used four because Isolation Forest answers a
> fundamentally different question — it's trained on benign data only and never
> sees an attack, which is the only realistic setting when a new botnet appears.
> Comparing it to supervised models quantifies what's lost without labels."

**Q: Wouldn't this be defeated by an attacker who knows your features?**
> "Possibly — that's limitation #4. An attacker who rate-limits and pads jitter
> could blend in. We did no adversarial testing, and that's the honest
> limitation. It's also a strong argument for periodic re-baselining."

**Q: Why not just put an agent on the device?**
> "That's the central constraint of IoT security: no storage, no compute
> budget, no vendor patches. Network-side monitoring is the only approach that
> scales and requires zero cooperation from the device."

**Q: Is 150k rows enough?**
> "It's a proportional stratified sample of the full **7,062,606-row** corpus,
> chosen so the notebook runs in minutes on a free Colab instance. Sampling is
> proportional across every device and all ten traffic types, and all seeds are
> fixed for reproducibility. What is *not* big enough is the benign class — 2,416
> benign test flows is the real statistical weakness, not the total row count."

**Q: What would you do differently?**
> "Chronological splitting to remove leakage, an adversarial robustness
> evaluation, and a streaming harness to measure detection latency — the
> original paper reports ~174ms, which is the number a real IDS needs."

---

## Presentation checklist

- [ ] All six required sections present (Problem, Dataset, Methodology, Results, Security implications, Conclusion)
- [ ] Total runtime 10–15 min — **rehearse with a timer**
- [ ] Dataset cited on the dataset slide (academic integrity)
- [ ] FPR **and** FNR stated explicitly, not just accuracy
- [ ] At least one chart (confusion matrix / ROC / SHAP)
- [ ] Limitations spoken aloud, not just on a slide
- [ ] All `[fill]` numbers replaced with real results
