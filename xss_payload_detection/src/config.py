"""Shared configuration: paths, seeds, and experiment constants."""

from pathlib import Path

# Project root (parent of src/)
ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = ROOT / "data"
RAW_CSV = DATA_DIR / "XSS_dataset.csv"
PROCESSED_DIR = DATA_DIR / "processed"

RESULTS_DIR = ROOT / "results"
MODEL_DIR = RESULTS_DIR / "models"
FIGURE_DIR = RESULTS_DIR / "figures"

# Raw dataset URL (Hugging Face, no login required)
DATASET_URL = (
    "https://huggingface.co/datasets/AmirAliGharesoufloo/XSS/resolve/main/XSS_dataset.csv"
)

# Reproducibility
SEED = 42

# Stratified split ratios (train / val / test)
TEST_SIZE = 0.15
VAL_SIZE = 0.15  # fraction of the FULL dataset (val is carved out of the remaining 85%)

# Character-level deep learning settings (CPU friendly)
MAX_SEQ_LEN = 300   # truncate/pad all payloads to 300 characters
EMBED_DIM = 64
NUM_FILTERS = 128
KERNEL_SIZES = (3, 4, 5)
DROPOUT = 0.5
BATCH_SIZE = 64
LEARNING_RATE = 1e-3
MAX_EPOCHS = 12
PATIENCE = 3        # early stopping on validation F1
AUG_PROB = 0.5      # probability of applying an obfuscation to a positive training sample

# Metric threshold for converting probabilities to class labels
THRESHOLD = 0.5
