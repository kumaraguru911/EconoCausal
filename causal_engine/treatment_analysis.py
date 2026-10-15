"""Compare observed outcomes across Criteo treatment groups."""

import gzip
from pathlib import Path

import pandas as pd

DATA = Path("data/raw/criteo/criteo-research-uplift-v2.1.csv.gz")
CHUNK_SIZE = 200_000

columns = ["treatment", "conversion", "visit", "exposure"]
counts = {}

with gzip.open(DATA, "rt", encoding="utf-8") as stream:
    for chunk in pd.read_csv(
        stream, usecols=columns, chunksize=CHUNK_SIZE
    ):
        grouped = (
            chunk.groupby("treatment")
            .agg(
                rows=("conversion", "size"),
                conversions=("conversion", "sum"),
                visits=("visit", "sum"),
                exposures=("exposure", "sum"),
            )
        )

        for treatment, row in grouped.iterrows():
            if treatment not in counts:
                counts[treatment] = row.copy()
            else:
                counts[treatment] += row

result = pd.DataFrame.from_dict(counts, orient="index")
result.index.name = "treatment"

result["conversion_rate_pct"] = (
    result["conversions"] / result["rows"] * 100
)
result["visit_rate_pct"] = result["visits"] / result["rows"] * 100
result["exposure_rate_pct"] = result["exposures"] / result["rows"] * 100

print("\nObserved outcomes by treatment group")
print(result.to_string(float_format=lambda x: f"{x:,.4f}"))

if set(result.index) == {0, 1}:
    difference = (
        result.loc[1, "conversion_rate_pct"]
        - result.loc[0, "conversion_rate_pct"]
    )
    print(f"\nRaw conversion-rate difference: {difference:.6f} percentage points")
    print("This is an observed association, not yet a validated causal effect.")

Path("reports").mkdir(exist_ok=True)
result.to_csv("reports/treatment_analysis.csv")
print("\nSaved reports/treatment_analysis.csv")
