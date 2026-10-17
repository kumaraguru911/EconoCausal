
"""Load a saved EconML model and predict advertising treatment effects."""

import argparse
import json
from pathlib import Path

import joblib
import numpy as np

MODEL_PATH = Path("models/criteo_linear_dml.joblib")
METADATA_PATH = Path("models/criteo_linear_dml_metadata.json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--features",
        nargs=12,
        type=float,
        required=True,
        metavar=tuple(f"f{i}" for i in range(12)),
        help="Provide values for f0 through f11 in order.",
    )
    args = parser.parse_args()

    if not MODEL_PATH.exists() or not METADATA_PATH.exists():
        raise FileNotFoundError(
            "Saved model or metadata not found. Run dml_estimator first."
        )

    metadata = json.loads(METADATA_PATH.read_text())
    model = joblib.load(MODEL_PATH)

    features = np.asarray(args.features, dtype=np.float32).reshape(1, -1)
    effect = float(np.asarray(model.effect(features)).reshape(-1)[0])

    print("Model:", metadata["model_type"])
    print("Outcome:", metadata["outcome"])
    print("Treatment:", metadata["treatment"])
    print(f"Estimated treatment effect: {effect:+.8f}")
    print(f"Estimated change in conversion probability: {effect * 100:+.6f} percentage points")
    print(
        "Interpretation: estimated advertising-treatment effect, "
        "not a discount effect."
    )


if __name__ == "__main__":
    main()
