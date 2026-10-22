# Mitigation probe: NUL-byte obfuscation

Detection rate on the `null_bytes` subset of the obfuscated test set, before and after stripping NUL bytes from the input (input normalization as a defense layer; no retraining).

| input handling   |   E2 Char TF-IDF + LogReg |   E4 TextCNN + augment |
|:-----------------|--------------------------:|-----------------------:|
| raw              |                    0.9991 |                 0.9982 |
| NUL-stripped     |                    0.9991 |                 0.9982 |
