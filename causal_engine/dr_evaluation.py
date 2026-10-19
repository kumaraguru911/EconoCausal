"""Doubly robust uplift evaluation using EconML DRTester."""

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from econml.validate import DRTester
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split

from causal_engine.dml_estimator import (
    DEFAULT_DATA,
    FEATURES,
    OUTCOME,
    TREATMENT,
    load_sample,
)

DEFAULT_MODEL = Path("models/criteo_linear_dml.joblib")
DEFAULT_OUTPUT = Path("reports/criteo_dr_uplift.json")
DEFAULT_CURVE = Path("reports/criteo_dr_uplift_summary.csv")


def run_evaluation(
    data_path=DEFAULT_DATA,
    model_path=DEFAULT_MODEL,
    sample_size=100_000,
    seed=42,
    trees=30,
    bootstrap=100,
):
    data = load_sample(Path(data_path), sample_size, seed)

    X = data[FEATURES].to_numpy()
    D = data[TREATMENT].to_numpy()
    y = data[OUTCOME].to_numpy()

    X_train, X_val, D_train, D_val, y_train, y_val = train_test_split(
        X, D, y, test_size=0.25, random_state=seed, stratify=D
    )

    cate = joblib.load(model_path)

    tester = DRTester(
        model_regression=RandomForestRegressor(
            n_estimators=trees,
            min_samples_leaf=100,
            max_features=0.8,
            n_jobs=2,
            random_state=seed,
        ),
        model_propensity=RandomForestClassifier(
            n_estimators=trees,
            min_samples_leaf=100,
            max_features=0.8,
            n_jobs=2,
            random_state=seed,
        ),
        cate=cate,
        cv=2,
    )

    tester.fit_nuisance(
        Xval=X_val,
        Dval=D_val,
        yval=y_val,
        Xtrain=X_train,
        Dtrain=D_train,
        ytrain=y_train,
    )

    result = tester.evaluate_uplift(
        Xval=X_val,
        Xtrain=X_train,
        metric="qini",
        n_bootstrap=bootstrap,
    )

    summary = {
        "dataset": str(data_path),
        "model": str(model_path),
        "sample_rows": int(len(data)),
        "train_rows": int(len(X_train)),
        "validation_rows": int(len(X_val)),
        "seed": seed,
        "nuisance_trees": trees,
        "bootstrap_samples": bootstrap,
        "metric": "EconML DRTester Qini",
        "coefficients": np.asarray(result.params).astype(float).tolist(),
        "standard_errors": np.asarray(result.errs).astype(float).tolist(),
        "p_values": np.asarray(result.pvals).astype(float).tolist(),
        "note": (
            "Criteo advertising-treatment evaluation, not a pricing or "
            "personalized-discount effect. Interpret results cautiously "
            "because conversions are rare."
        ),
    }

    curve = result.summary().reset_index(drop=True)

    Path(DEFAULT_OUTPUT).parent.mkdir(parents=True, exist_ok=True)
    Path(DEFAULT_OUTPUT).write_text(json.dumps(summary, indent=2) + "\n")
    curve.to_csv(DEFAULT_CURVE, index=False)

    print(json.dumps(summary, indent=2))
    print(f"Saved summary: {DEFAULT_OUTPUT}")
    print(f"Saved curve: {DEFAULT_CURVE}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--sample-size", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--trees", type=int, default=30)
    parser.add_argument("--bootstrap", type=int, default=100)
    args = parser.parse_args()

    run_evaluation(
        data_path=args.data,
        model_path=args.model,
        sample_size=args.sample_size,
        seed=args.seed,
        trees=args.trees,
        bootstrap=args.bootstrap,
    )


if __name__ == "__main__":
    main()
