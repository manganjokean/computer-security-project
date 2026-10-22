# Experimental results

## Clean held-out test set (stratified 70/15/15 split, seed 42)

| model | accuracy | precision | recall | f1 | pr_auc | fpr |
| --- | --- | --- | --- | --- | --- | --- |
| E0 Length-only LogReg | 0.7581 | 0.7613 | 0.9345 | 0.8391 | 0.8345 | 0.6075 |
| E1 Word TF-IDF + LogReg | 0.9982 | 0.9973 | 1.0000 | 0.9986 | 1.0000 | 0.0057 |
| E2 Char n-gram TF-IDF + LogReg | 0.9994 | 1.0000 | 0.9991 | 0.9995 | 1.0000 | 0.0000 |
| E3 TextCNN | 0.9982 | 1.0000 | 0.9973 | 0.9986 | 1.0000 | 0.0000 |
| E4 TextCNN + augment | 0.9988 | 1.0000 | 0.9982 | 0.9991 | 1.0000 | 0.0000 |

## Robustness summary

`obf_recall` = fraction of obfuscated XSS payloads still detected (mean over 7 transforms); `ben_fpr` = false positive rate on entity-encoded benign HTML.

| model | train_time_s | obf_recall | ben_fpr |
| --- | --- | --- | --- |
| E0 Length-only LogReg | 0.0667 | 0.7693 | 0.1283 |
| E1 Word TF-IDF + LogReg | 0.4665 | 0.9457 | 0.0075 |
| E2 Char n-gram TF-IDF + LogReg | 2.6342 | 0.9705 | 0.0057 |
| E3 TextCNN | 55.8936 | 0.9828 | 0.0075 |
| E4 TextCNN + augment | 100.4714 | 0.9996 | 0.0906 |