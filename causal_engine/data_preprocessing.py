
"""Validated, memory-conscious preprocessing for Criteo uplift data."""

from pathlib import Path

import numpy as np
import pandas as pd

FEATURES = [f"f{i}" for i in range(12)]
TREATMENT = "treatment"
OUTCOME = "conversion"

REQUIRED_COLUMNS = FEATURES + [
    TREATMENT,
    OUTCOME,
    "visit",
    "exposure",
]


def validate_frame(data: pd.DataFrame) -> pd.DataFrame:
    """Validate required columns and binary treatment/outcome fields."""
    missing = sorted(set(REQUIRED_COLUMNS) - set(data.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if data.empty:
        raise ValueError("Dataset contains no rows.")

    result = data[REQUIRED_COLUMNS].copy()

    if result.isna().any().any():
        raise ValueError("Dataset contains missing values.")

    for column in FEATURES:
        result[column] = pd.to_numeric(result[column], errors="raise")
        if not np.isfinite(result[column].to_numpy(dtype=np.float64)).all():
            raise ValueError(f"Feature {column} contains non-finite values.")

    for column in [TREATMENT, OUTCOME, "visit", "exposure"]:
        values = set(result[column].unique())
        if not values.issubset({0, 1}):
            raise ValueError(f"{column} must contain only binary 0/1 values.")

    if result[TREATMENT].nunique() != 2:
        raise ValueError("Both treatment groups must be represented.")

    result[FEATURES] = result[FEATURES].astype("float32")
    for column in [TREATMENT, OUTCOME, "visit", "exposure"]:
        result[column] = result[column].astype("int8")

    return result


def load_sample(
    path: str | Path,
    sample_size: int = 100_000,
    seed: int = 42,
    chunksize: int = 100_000,
) -> pd.DataFrame:
    """Reservoir-sample a compressed CSV without loading it all into RAM."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    if sample_size < 1 or chunksize < 1:
        raise ValueError("sample_size and chunksize must be positive.")

    rng = np.random.default_rng(seed)
    reservoir = None
    seen = 0

    for chunk in pd.read_csv(
        path,
        compression="gzip",
        usecols=REQUIRED_COLUMNS,
        chunksize=chunksize,
    ):
        values = chunk.to_numpy()

        if reservoir is None:
            initial_count = min(sample_size, len(values))
            reservoir = values[:initial_count].copy()
            seen = initial_count
            values = values[initial_count:]

        for row in values:
            seen += 1
            j = int(rng.integers(0, seen))
            if j < sample_size:
                reservoir[j] = row

    if reservoir is None or len(reservoir) == 0:
        raise ValueError("No rows were read from the dataset.")

    sample = pd.DataFrame(reservoir, columns=REQUIRED_COLUMNS)
    return validate_frame(sample)


def save_sample(data: pd.DataFrame, output_path: str | Path) -> Path:
    """Save a validated sample to a local CSV file."""
    validated = validate_frame(data)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    validated.to_csv(output_path, index=False)
    return output_path
