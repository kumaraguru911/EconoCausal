"""Memory-efficient profiling for the Criteo uplift dataset."""

import gzip
import json
from collections import Counter
from pathlib import Path

import pandas as pd

DATA = Path("data/raw/criteo/criteo-research-uplift-v2.1.csv.gz")
OUT = Path("reports/criteo_profile.json")
CHUNK_SIZE = 200_000

if not DATA.is_file():
    raise FileNotFoundError(f"Dataset not found: {DATA}")

expected = [f"f{i}" for i in range(12)] + [
    "treatment", "conversion", "visit", "exposure"
]

rows = 0
missing = Counter()
value_counts = {c: Counter() for c in expected[12:]}
feature_sums = Counter()
feature_counts = Counter()
feature_mins = {}
feature_maxs = {}
sample_rows = []

with gzip.open(DATA, "rt", encoding="utf-8") as stream:
    reader = pd.read_csv(stream, chunksize=CHUNK_SIZE)

    for chunk in reader:
        if list(chunk.columns) != expected:
            raise ValueError(
                f"Unexpected columns: {list(chunk.columns)}"
            )

        rows += len(chunk)

        for col in chunk.columns:
            missing[col] += int(chunk[col].isna().sum())

        for col in value_counts:
            value_counts[col].update(
                chunk[col].value_counts(dropna=False).to_dict()
            )

        for col in expected[:12]:
            series = chunk[col].dropna()
            if not series.empty:
                feature_sums[col] += float(series.sum())
                feature_counts[col] += int(series.count())
                feature_mins[col] = min(
                    feature_mins.get(col, float("inf")),
                    float(series.min()),
                )
                feature_maxs[col] = max(
                    feature_maxs.get(col, float("-inf")),
                    float(series.max()),
                )

        if len(sample_rows) < 10:
            sample_rows.extend(
                chunk.head(10 - len(sample_rows)).to_dict("records")
            )

        print(f"Processed {rows:,} rows", end="\r")

profile = {
    "dataset": str(DATA),
    "rows": rows,
    "columns": expected,
    "missing_values": dict(missing),
    "categorical_counts": {
        col: {str(k): int(v) for k, v in counts.items()}
        for col, counts in value_counts.items()
    },
    "feature_statistics": {
        col: {
            "mean": feature_sums[col] / feature_counts[col],
            "min": feature_mins[col],
            "max": feature_maxs[col],
        }
        for col in expected[:12]
        if feature_counts[col]
    },
    "sample_rows": sample_rows,
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(profile, indent=2), encoding="utf-8")

print(f"\nTotal rows: {rows:,}")
print(f"Missing values: {sum(missing.values()):,}")
print("\nTreatment and outcome counts:")
for col, counts in value_counts.items():
    print(f"\n{col}:")
    for value, count in counts.most_common():
        print(f"  {value}: {count:,}")

print(f"\nFull report saved to {OUT}")
