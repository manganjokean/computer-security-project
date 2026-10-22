# Seed stability (E3/E4 repeated over several random seeds)

Mean ± std across seeds; higher is better except FPR columns.

| model                |   n_seeds | clean_f1_mean   | clean_pr_auc_mean   | clean_fpr_mean   | obf_recall_mean   | ben_fpr_mean    |
|:---------------------|----------:|:----------------|:--------------------|:-----------------|:------------------|:----------------|
| E3 TextCNN           |         3 | 0.9991 ± 0.0005 | 1.0000 ± 0.0000     | 0.0000 ± 0.0000  | 0.9896 ± 0.0066   | 0.0088 ± 0.0022 |
| E4 TextCNN + augment |         3 | 0.9988 ± 0.0005 | 1.0000 ± 0.0000     | 0.0006 ± 0.0011  | 0.9995 ± 0.0001   | 0.0616 ± 0.0325 |