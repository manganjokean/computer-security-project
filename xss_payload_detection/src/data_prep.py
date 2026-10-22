"""Step 1: download, clean, deduplicate, and split the XSS dataset.

Outputs (data/processed/):
  train.csv, val.csv, test.csv          - stratified splits (Sentence, Label)
  test_obfuscated.json                   - hard set: obfuscated XSS payloads (Label=1)
  test_benign_encoded.json               - hard set: entity-encoded benign HTML (Label=0)
  split_summary.json                     - counts and label balance per split

Note: the hard sets are stored as JSON rather than CSV because the NUL-byte
obfuscation inserts "\x00" characters, which pandas silently TRUNCATES on
CSV read (verified: "ab\x00cd" -> "ab"). JSON preserves them exactly.

Rationale:
  * Deduplicate BEFORE splitting. The raw file contains ~3.5k rows whose
    Sentence appears more than once; splitting after deduplication prevents
    identical payloads from leaking across train/test (data leakage).
  * Splits are stratified on Label so class balance is preserved.
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

import config
import obfuscation

HARD_SEED = 1234


def download_raw(force: bool = False) -> Path:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not config.RAW_CSV.exists() or force:
        print(f"Downloading dataset from {config.DATASET_URL}")
        urllib.request.urlretrieve(config.DATASET_URL, config.RAW_CSV)
    else:
        print(f"Using cached raw dataset: {config.RAW_CSV}")
    return config.RAW_CSV


def load_clean(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df[["Sentence", "Label"]].copy()
    df["Sentence"] = df["Sentence"].astype(str).str.strip()
    df["Label"] = df["Label"].astype(int)
    df = df[df["Sentence"].str.len() > 0]
    df = df[df["Label"].isin([0, 1])]
    return df.reset_index(drop=True)


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)
    conflicts = (
        df.groupby("Sentence")["Label"].nunique().gt(1).sum()
    )
    if conflicts:
        raise ValueError(f"{conflicts} sentences carry conflicting labels; investigate.")
    df = df.drop_duplicates(subset="Sentence", keep="first").reset_index(drop=True)
    print(f"Deduplication: {before} -> {len(df)} rows (removed {before - len(df)})")
    return df


def make_splits(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    train_df, temp_df = train_test_split(
        df, test_size=config.TEST_SIZE + config.VAL_SIZE,
        stratify=df["Label"], random_state=config.SEED,
    )
    rel_val = config.VAL_SIZE / (config.TEST_SIZE + config.VAL_SIZE)
    val_df, test_df = train_test_split(
        temp_df, test_size=1 - rel_val,
        stratify=temp_df["Label"], random_state=config.SEED,
    )
    return {
        "train": train_df.reset_index(drop=True),
        "val": val_df.reset_index(drop=True),
        "test": test_df.reset_index(drop=True),
    }


def make_hard_sets(test_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build robustness sets from the held-out test split only."""
    xss = test_df[test_df["Label"] == 1].reset_index(drop=True)
    benign = test_df[test_df["Label"] == 0].reset_index(drop=True)

    rows = []
    for i, row in xss.iterrows():
        for t in obfuscation.TRANSFORMS:
            new = obfuscation.apply_transform(row["Sentence"], t, HARD_SEED + i)
            rows.append({"Sentence": new, "Label": 1, "transform": t})
    test_obf = pd.DataFrame(rows)

    test_ben_enc = benign.copy()
    test_ben_enc["Sentence"] = test_ben_enc["Sentence"].map(
        obfuscation.html_entity_encode_all
    )
    test_ben_enc["transform"] = "html_entity_full"
    return test_obf, test_ben_enc


def load_hard_set(name: str) -> pd.DataFrame:
    """Load a hard robustness set (JSON preferred: preserves NUL bytes)."""
    j = config.PROCESSED_DIR / f"{name}.json"
    if j.exists():
        return pd.DataFrame(json.loads(j.read_text(encoding="utf-8")))
    return pd.read_csv(config.PROCESSED_DIR / f"{name}.csv")


def main() -> None:
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    raw = download_raw()
    df = deduplicate(load_clean(raw))
    print(f"Clean dataset: {len(df)} rows | label balance:\n{df['Label'].value_counts().to_dict()}")

    splits = make_splits(df)
    summary = {"total": len(df), "label_balance": df["Label"].value_counts().to_dict()}
    for name, part in splits.items():
        part.to_csv(config.PROCESSED_DIR / f"{name}.csv", index=False)
        summary[name] = {
            "rows": len(part),
            "xss": int((part["Label"] == 1).sum()),
            "benign": int((part["Label"] == 0).sum()),
        }
        print(f"  {name:>5}: {len(part):>5} rows "
              f"(xss={summary[name]['xss']}, benign={summary[name]['benign']})")

    test_obf, test_ben_enc = make_hard_sets(splits["test"])
    test_obf.to_json(config.PROCESSED_DIR / "test_obfuscated.json",
                     orient="records", force_ascii=False)
    test_ben_enc.to_json(config.PROCESSED_DIR / "test_benign_encoded.json",
                         orient="records", force_ascii=False)
    # remove stale (NUL-truncated) CSV variants if present
    for stale in ("test_obfuscated.csv", "test_benign_encoded.csv"):
        p = config.PROCESSED_DIR / stale
        if p.exists():
            p.unlink()
    summary["test_obfuscated"] = {"rows": len(test_obf),
                                  "per_transform": test_obf["transform"].value_counts().to_dict()}
    summary["test_benign_encoded"] = {"rows": len(test_ben_enc)}
    print(f"  hard sets: {len(test_obf)} obfuscated XSS payloads, "
          f"{len(test_ben_enc)} entity-encoded benign snippets")

    with open(config.PROCESSED_DIR / "split_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Saved splits to {config.PROCESSED_DIR}")


if __name__ == "__main__":
    main()
