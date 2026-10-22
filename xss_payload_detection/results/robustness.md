# Obfuscation robustness: detection rate per transform

|               |   E3 TextCNN |   E4 TextCNN + augment |
|:--------------|-------------:|-----------------------:|
| combined      |       0.9427 |                 1      |
| comment_split |       0.9864 |                 1      |
| html_entity   |       0.9791 |                 1      |
| mixed_case    |       0.9973 |                 1      |
| null_bytes    |       0.9955 |                 0.9982 |
| url_encode    |       0.9809 |                 1      |
| whitespace    |       0.9982 |                 0.9991 |