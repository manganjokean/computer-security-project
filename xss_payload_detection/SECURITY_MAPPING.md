# Security Problem → Security Control → Mitigation → Security Improvement

This file documents the assignment's required security chain for the XSS
detection project, grounded in the experiments in `src/` and the artifacts in
`results/`.

> **Note:** Final measured numbers are summarized in `results/metrics.md`,
> `results/robustness.md`, `results/seed_stability.md`, and
> `results/normalization_probe.md` (regenerate any time with
> `python src/run_experiments.py`).

## 1. Security Problem

**Untrusted input reaches the browser.** Any string a user submits (comment,
profile field, search box, URL parameter) can contain a Cross-Site Scripting
payload such as `<img src=x onerror=alert(1)>`. If the application reflects
that input without validation or encoding, the attacker's script executes in
the victim's session.

Attackers do not send textbook payloads — they **obfuscate** to evade
signature/keyword filters:

| Evasion technique | Example effect |
|---|---|
| Mixed case | `<ScRiPt>` defeats case-sensitive keyword rules |
| HTML entities | `&lt;img ... onerror&alert(1)&gt;` hides angle brackets |
| URL encoding | `%3Cimg%20src=x%20onerror=...` hides the whole tag |
| NUL-byte injection | `on\x00error=` breaks character-level patterns inside tags |
| Comment splitting | `sc<!--x-->ript` splits keywords |
| Whitespace tricks | newlines/tabs inside tags evade regexes |
| Multi-stage combinations | two or three of the above chained |

## 2. Security Control

Defense in depth for user-generated content (the controls this assignment
investigates):

1. **Input validation** — reject or escape input that does not match an
   expected schema (length caps, character allow-lists).
2. **Output encoding/escaping** — HTML-entity-encode untrusted text before
   rendering, so markup can never be interpreted (`<` → `&lt;`).
3. **Secure handling of user-generated content** — Context-Security-Policy
   headers, sanitization of rich content, HttpOnly cookies.
4. **Detection layer (this project)** — an ML classifier over raw input that
   flags likely payloads as an *additional* signal before they reach a
   rendering path; it complements, never replaces, controls 1–3.

## 3. Mitigation

The project implements and tests two candidate mitigations — and measures both
honestly:

- **E4 — training-time obfuscation augmentation (the winner).** Positive
  training samples are randomly transformed (case, entities, URL-encoding,
  NUL, comments, whitespace, combinations), so the detector learns attack
  semantics rather than surface form. Detection of obfuscated payloads rises
  from E3's 0.9896 ± 0.0066 to **0.9995 ± 0.0001** (3 seeds), with clean-set
  F1 unchanged (see `results/robustness.md`, `results/seed_stability.md`).
  Biggest single gain: multi-stage `combined` obfuscation, 0.943 → 1.000.
- **Inference-time input normalization (measured, and NOT needed here).**
  The probe strips NUL bytes from input before classification. Detection on
  NUL-obfuscated payloads was already 0.999 for both the baseline and the
  augmented model, and stripping changed nothing
  (see `results/normalization_probe.md`). Conclusion: for these models the
  robustness comes from augmentation, not from normalization — normalization
  remains good practice generally, but it is not what closes this gap.
- **Data-integrity control (a lesson of its own).** An early version of the
  pipeline stored the obfuscated hard set as CSV; pandas silently truncates
  strings at NUL bytes on CSV read, which understated obfuscated-payload
  robustness by ~17 percentage points. Storing the hard sets as JSON
  (`data_prep.load_hard_set`) fixed the measurement. In a security project,
  verifying that your measurement pipeline preserves hostile input byte-for-
  byte is itself a control.

The lesson demonstrated: **augmentation, not normalization, supplies the
robustness here** — and a detector's robustness claim is only as trustworthy
as the pipeline that measures it.

## 4. Security Improvement

Measured on the held-out test split and the obfuscated hard sets
(`results/`):

- **Robustness:** obfuscated-payload detection improves from 0.9896 ± 0.0066
  (E3) to **0.9995 ± 0.0001** (E4) across three seeds, and E4 detects 100%
  of the payloads under six of the seven obfuscation transforms.
- **Clean performance:** unchanged (F1 0.9991 ± 0.0005, FPR ≈ 0 on the clean
  test set) — robustness was gained for free on clean input.
- **False-positive cost (the honest part):** FPR on *entity-encoded benign
  HTML* rises from 0.009 (E3) to 0.062 ± 0.033 (E4). An augmented model is
  more sensitive to entity-encoded content — precisely what escaped user
  text looks like — so deployment needs threshold tuning or encoding-aware
  validation instead of one global threshold.
- **Baseline comparison:** even the char TF-IDF baseline reaches only 0.9705
  on obfuscated payloads and the length-only model 0.7693, so the deep,
  augmented detector provides measurable value precisely in the adversarial
  regime where clean-set scores are already saturated.

**Takeaway for the application:** pair output encoding (primary control) with
training-time augmentation for the detection layer, and re-measure false
positives on *escaped* benign content — not only on raw text — before
deployment.
