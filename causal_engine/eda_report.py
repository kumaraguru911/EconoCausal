"""Create an EDA report from the full Criteo dataset in chunks."""

import gzip
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

DATA = Path("data/raw/criteo/criteo-research-uplift-v2.1.csv.gz")
OUT = Path("reports")
CHUNK_SIZE = 200_000

OUT.mkdir(exist_ok=True)

counts = {
    "treatment": {},
    "conversion": {},
    "visit": {},
    "exposure": {},
}
rows = 0

with gzip.open(DATA, "rt", encoding="utf-8") as stream:
    for chunk in pd.read_csv(stream, chunksize=CHUNK_SIZE):
        rows += len(chunk)

        for col in counts:
            values = chunk[col].value_counts().to_dict()
            for value, count in values.items():
                counts[col][int(value)] = (
                    counts[col].get(int(value), 0) + int(count)
                )

print(f"Rows analysed: {rows:,}")

# Save count summaries
summary = pd.DataFrame({
    col: pd.Series(values)
    for col, values in counts.items()
}).fillna(0).astype("int64")
summary.index.name = "value"
summary.to_csv(OUT / "criteo_eda_counts.csv")

# Plot treatment assignment distribution
fig, ax = plt.subplots(figsize=(7, 4))
labels = [str(k) for k in sorted(counts["treatment"])]
values = [counts["treatment"][int(k)] for k in labels]
ax.bar(labels, values)
ax.set_title("Criteo Treatment Assignment Distribution")
ax.set_xlabel("Treatment")
ax.set_ylabel("Number of observations")
fig.tight_layout()
fig.savefig(OUT / "criteo_treatment_distribution.png", dpi=160)
plt.close(fig)

# Plot conversion and visit counts
fig, axes = plt.subplots(1, 2, figsize=(9, 4))
for ax, col in zip(axes, ["conversion", "visit"]):
    labels = [str(k) for k in sorted(counts[col])]
    values = [counts[col][int(k)] for k in labels]
    ax.bar(labels, values)
    ax.set_title(f"{col.title()} outcomes")
    ax.set_xlabel("Outcome value")
    ax.set_ylabel("Number of observations")

fig.tight_layout()
fig.savefig(OUT / "criteo_outcome_distributions.png", dpi=160)
plt.close(fig)

print(f"Saved {OUT / 'criteo_eda_counts.csv'}")
print(f"Saved {OUT / 'criteo_treatment_distribution.png'}")
print(f"Saved {OUT / 'criteo_outcome_distributions.png'}")
