"""Deep learning models for character-level XSS payload classification.

XSS payloads are not natural language: they are short strings of HTML tags,
event-handler names, JavaScript fragments, and obfuscation noise. Characters
are therefore the natural modeling unit. We implement:

  TextCNN  (proposed) - multi-kernel 1-D convolutions over the character
           sequence capture local patterns such as `<script`, `onerror=`,
           `javascript:` at several lengths simultaneously. Cheap on CPU.

  BiLSTM   (optional comparison) - a bidirectional LSTM models longer-range
           sequential structure. Slower on CPU; run with --include-bilstm.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

import config


class CharVocab:
    """Character <-> id mapping built from the training split only."""

    PAD, UNK = 0, 1

    def __init__(self, chars: list[str]):
        self.itos = [self.PAD, "__UNK__"] + chars
        self.stoi = {c: i for i, c in enumerate(self.itos) if i > 1}

    @classmethod
    def build(cls, texts, min_freq: int = 1) -> "CharVocab":
        from collections import Counter
        counts = Counter()
        for t in texts:
            counts.update(str(t))
        chars = [c for c, n in counts.most_common() if n >= min_freq]
        return cls(chars)

    def encode(self, text: str, max_len: int) -> list[int]:
        ids = [self.stoi.get(c, self.UNK) for c in str(text)[:max_len]]
        return ids + [self.PAD] * (max_len - len(ids))

    def __len__(self):
        return len(self.itos)

    def save(self, path) -> None:
        import json
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.itos, f, ensure_ascii=False)

    @classmethod
    def load(cls, path) -> "CharVocab":
        import json
        with open(path, encoding="utf-8") as f:
            itos = json.load(f)
        v = cls.__new__(cls)
        v.itos = itos
        v.stoi = {c: i for i, c in enumerate(itos) if i > 1}
        return v


class TextCNN(nn.Module):
    def __init__(self, vocab_size: int, embed_dim: int = config.EMBED_DIM,
                 num_classes: int = 2, kernel_sizes: tuple = config.KERNEL_SIZES,
                 num_filters: int = config.NUM_FILTERS,
                 dropout: float = config.DROPOUT):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.convs = nn.ModuleList([
            nn.Conv1d(embed_dim, num_filters, k, padding=k - 1) for k in kernel_sizes
        ])
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(num_filters * len(kernel_sizes), num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        emb = self.embedding(x).transpose(1, 2)          # (B, E, L)
        pooled = [F.relu(conv(emb)).max(dim=2).values for conv in self.convs]
        out = torch.cat(pooled, dim=1)                   # (B, F * K)
        return self.fc(self.dropout(out))


class BiLSTM(nn.Module):
    def __init__(self, vocab_size: int, embed_dim: int = 64, hidden: int = 64,
                 num_classes: int = 2, dropout: float = 0.5):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.lstm = nn.LSTM(embed_dim, hidden, num_layers=1, batch_first=True,
                            bidirectional=True, dropout=0.0)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden * 2, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        emb = self.embedding(x)
        out, _ = self.lstm(emb)                          # (B, L, 2H)
        pooled = out.max(dim=1).values                   # max-pool over time
        return self.fc(self.dropout(pooled))


def build_model(name: str, vocab_size: int) -> nn.Module:
    name = name.lower()
    if name == "textcnn":
        return TextCNN(vocab_size)
    if name == "bilstm":
        return BiLSTM(vocab_size)
    raise ValueError(f"Unknown model: {name}")
