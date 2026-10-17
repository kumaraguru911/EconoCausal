"""Memory-conscious Double Machine Learning for Criteo uplift data."""

import argparse
import json
from pathlib import Path
import joblib

import numpy as np
import pandas as pd
from econml.dml import LinearDML
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split

FEATURES = [f"f{i}" for i in range(12)]
TREATMENT = "treatment"
OUTCOME = "conversion"
DEFAULT_DATA = Path("data/raw/criteo/criteo-research-uplift-v2.1.csv.gz")
REPORT_DIR = Path("reports")


def load_sample(path: Path, sample_size: int, seed: int) -> pd.DataFrame:
    """Reservoir-sample rows from a compressed CSV using bounded memory."""
    required = FEATURES + [TREATMENT, OUTCOME]
    rng = np.random.default_rng(seed)
    reservoir = None
    seen = 0

    for chunk in pd.read_csv(
        path, compression="gzip", usecols=required, chunksize=100_000
    ):
        values = chunk.to_numpy()

        if reservoir is None:
            reservoir = values[:sample_size].copy()
            seen = len(reservoir)
            values = values[len(reservoir):]

        for row in values:
            seen += 1
            j = int(rng.integers(0, seen))
            if j < sample_size:
                reservoir[j] = row

    if reservoir is None or len(reservoir) < 100:
        raise ValueError("Dataset is empty or too small.")

    sample = pd.DataFrame(reservoir, columns=required)
    sample[FEATURES] = sample[FEATURES].astype("float32")
    sample[TREATMENT] = sample[TREATMENT].astype("int8")
    sample[OUTCOME] = sample[OUTCOME].astype("int8")
    return sample


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--sample-size", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--trees", type=int, default=50)
    parser.add_argument("--test-size", type=float, default=0.25)
    args = parser.parse_args()

    if not args.data.exists():
        raise FileNotFoundError(f"Dataset not found: {args.data}")
    if args.sample_size < 1000:
        raise ValueError("--sample-size must be at least 1000")

    print(f"Sampling up to {args.sample_size:,} rows from {args.data}...")
    data = load_sample(args.data, args.sample_size, args.seed)

    X = data[FEATURES]
    T = data[TREATMENT]
    Y = data[OUTCOME]

    if T.nunique() != 2 or Y.nunique() != 2:
        raise ValueError("Sample must contain both treatment groups and outcomes.")

    X_train, X_test, T_train, T_test, Y_train, Y_test = train_test_split(
        X, T, Y, test_size=args.test_size, random_state=args.seed, stratify=T
    )

    print(f"Sample rows: {len(data):,}")
    print(f"Train rows: {len(X_train):,}; test rows: {len(X_test):,}")
    print(f"Treatment rate: {T.mean():.4f}")
    print(f"Conversion rate: {Y.mean():.6f}")
    print("Fitting LinearDML. Random Forest training may take a while...")

    model = LinearDML(
        model_y=RandomForestRegressor(
            n_estimators=args.trees, min_samples_leaf=100,
            max_features=0.8, n_jobs=2, random_state=args.seed
        ),
        model_t=RandomForestClassifier(
            n_estimators=args.trees, min_samples_leaf=100,
            max_features=0.8, n_jobs=2, random_state=args.seed
        ),
        discrete_treatment=True,
        cv=2,
        random_state=args.seed,
        mc_iters=1,
    )

    model.fit(Y_train.to_numpy(), T_train.to_numpy(), X=X_train.to_numpy())


    # Save the fitted estimator for later reuse.
    model_dir = Path("models")
    model_dir.mkdir(parents=True, exist_ok=True)

    model_path = model_dir / "criteo_linear_dml.joblib"
    joblib.dump(model, model_path, compress=3)

    metadata = {
        "model_type": "EconML LinearDML",
        "outcome": OUTCOME,
        "treatment": TREATMENT,
        "features": FEATURES,
        "sample_rows": int(len(data)),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "seed": args.seed,
        "trees_per_nuisance_model": args.trees,
        "dataset": str(args.data),
        "interpretation": (
            "Advertising-treatment effect on conversion; "
            "not a personalized discount effect."
        ),
    }

    metadata_path = model_dir / "criteo_linear_dml_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")

    print(f"Saved fitted model: {model_path}")
    print(f"Saved model metadata: {metadata_path}")

    # Estimate heterogeneous treatment effects for held-out observations.
    effects = model.effect(X_test.to_numpy())
    effects = np.asarray(effects).reshape(-1)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    effects_path = REPORT_DIR / "dml_test_effects.csv"
    pd.DataFrame({
        "treatment": T_test.to_numpy(),
        "conversion": Y_test.to_numpy(),
        "estimated_treatment_effect": effects,
    }).to_csv(effects_path, index=False)

    try:
        ate_interval = model.ate_interval(X_test.to_numpy(), alpha=0.05)
        ate_ci = [float(ate_interval[0]), float(ate_interval[1])]
    except Exception as exc:
        print(f"ATE confidence interval unavailable: {exc}")
        ate_ci = None

    summary = {
        "dataset": str(args.data),
        "outcome": OUTCOME,
        "treatment": TREATMENT,
        "features": FEATURES,
        "sample_rows": int(len(data)),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "seed": args.seed,
        "trees_per_nuisance_model": args.trees,
        "treatment_rate": float(T.mean()),
        "conversion_rate": float(Y.mean()),
        "estimated_ate": float(np.mean(effects)),
        "estimated_ate_95pct_interval": ate_ci,
        "effect_std": float(np.std(effects)),
        "effect_quantiles": {
            "p10": float(np.quantile(effects, 0.10)),
            "p50": float(np.quantile(effects, 0.50)),
            "p90": float(np.quantile(effects, 0.90)),
        },
        "interpretation": (
            "Estimated effect of Criteo advertising treatment on conversion; "
            "not a discount effect. Validate model assumptions and uncertainty "
            "before using for decisions."
        ),
        "effects_file": str(effects_path),
    }

    summary_path = REPORT_DIR / "dml_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")

    print("\nDML run complete.")
    print(f"Estimated average treatment effect: {summary['estimated_ate']:.8f}")
    print(f"Effect standard deviation: {summary['effect_std']:.8f}")
    print(f"Saved summary: {summary_path}")
    print(f"Saved held-out effects: {effects_path}")


if __name__ == "__main__":
    main()
