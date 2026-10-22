"""Obfuscation transforms for XSS payloads.

These transforms simulate how attackers evade signature-based or regex-based
XSS filters while (in principle) preserving the malicious semantics of the
payload. They are used for two purposes:

1. Robustness evaluation: build a "hard" test set of obfuscated XSS payloads
   and measure how recall changes compared with the clean test set.
2. Training-time augmentation: apply a random transform to positive training
   samples so the deep model sees obfuscated variants during training.

Only positive (XSS) samples are transformed; benign HTML is left untouched
except for the separate benign HTML-entity-encoding false-positive check.
"""

from __future__ import annotations

import random
import re

TRANSFORMS = [
    "mixed_case",
    "html_entity",
    "url_encode",
    "null_bytes",
    "comment_split",
    "whitespace",
    "combined",
]


def mixed_case(payload: str, rng: random.Random) -> str:
    """Randomize the case of alphabetic characters (e.g. <ScRiPt>)."""
    return "".join(
        c.upper() if rng.random() < 0.5 else c.lower() for c in payload
    )


def html_entity(payload: str, rng: random.Random) -> str:
    """Replace ~30% of alphanumeric characters with numeric HTML entities."""
    out = []
    for c in payload:
        if c.isalnum() and rng.random() < 0.3:
            out.append(f"&#{ord(c)};")
        else:
            out.append(c)
    return "".join(out)


def url_encode(payload: str, rng: random.Random) -> str:
    """Percent-encode ~30% of characters (URL-context evasion)."""
    out = []
    for c in payload:
        if c not in " \t" and rng.random() < 0.3:
            out.append("".join(f"%{b:02X}" for b in c.encode("utf-8", "ignore")))
        else:
            out.append(c)
    return "".join(out)


def null_bytes(payload: str, rng: random.Random) -> str:
    """Insert NUL bytes inside tag/keyword-like tokens."""
    parts = re.split(r"(<[^>]*>)", payload)
    out = []
    for part in parts:
        if part.startswith("<"):
            chars = []
            for c in part:
                chars.append(c)
                if c.isalpha() and rng.random() < 0.2:
                    chars.append("\x00")
            out.append("".join(chars))
        else:
            out.append(part)
    return "".join(out)


def comment_split(payload: str, rng: random.Random) -> str:
    """Split tokens with HTML comments (sc<!--x-->ript)."""
    chars = list(payload)
    n = max(1, len(chars) // 10)
    positions = rng.sample(range(1, max(2, len(chars) - 1)), min(n, len(chars) - 2))
    for pos in sorted(positions, reverse=True):
        chars.insert(pos, "<!--x-->")
    return "".join(chars)


def whitespace(payload: str, rng: random.Random) -> str:
    """Replace some spaces/tabs with newlines or tabs (whitespace evasion)."""
    out = []
    for c in payload:
        if c == " " and rng.random() < 0.4:
            out.append(rng.choice(["\n", "\t", "\r\n"]))
        else:
            out.append(c)
    return "".join(out)


def combined(payload: str, rng: random.Random) -> str:
    """Apply 2-3 randomly chosen transforms in sequence."""
    k = rng.randint(2, 3)
    chosen = rng.sample(TRANSFORMS[:-1], k)
    for name in chosen:
        payload = APPLY[name](payload, rng)
    return payload


APPLY = {
    "mixed_case": mixed_case,
    "html_entity": html_entity,
    "url_encode": url_encode,
    "null_bytes": null_bytes,
    "comment_split": comment_split,
    "whitespace": whitespace,
    "combined": combined,
}


def apply_transform(payload: str, name: str, seed: int) -> str:
    """Deterministic transform application (seeded per payload)."""
    rng = random.Random(seed)
    if name == "combined":
        return combined(payload, rng)
    return APPLY[name](payload, rng)


def html_entity_encode_all(payload: str) -> str:
    """HTML-entity-encode every special character of a benign snippet.

    False-positive probe: checks whether a model wrongly flags benign content
    merely because its markup characters were entity-encoded (a common,
    legitimate practice, e.g. escaping user text before rendering).
    """
    return "".join(
        f"&#{ord(c)};" if (not c.isalnum() and c not in " \t\n\r") else c
        for c in payload
    )


def random_transform(payload: str, rng: random.Random) -> str:
    """Pick a random transform (used for training-time augmentation)."""
    name = rng.choice(TRANSFORMS)
    return apply_transform(payload, name, rng.randrange(10**9))
