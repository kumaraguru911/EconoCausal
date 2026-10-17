
"""Evaluate held-out Criteo DML treatment-effect predictions."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

DEFAULT_INPUT = Path("reports/dml_test_effects.csv")
DEFAULT_OUTPUT = Path("reports/dml_evaluation.json")


def evaluate_effects(data: pd.DataFrame, n_bins: int = 10) -> dict:
    required = {
        "treatment",
        "conversion",
        "estimated_treatment_effect",
    }
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    data = data[list(required)].copy()
    data = data.replace([np.inf, -np.inf], np.nan).dropna()

    if data.empty:
        raise ValueError("No valid evaluation rows found.")
    if not set(data["treatment"].unique()).issubset({0, 1}):
        raise ValueError("Treatment must be binary (0/1).")
    if not set(data["conversion"].unique()).issubset({0, 1}):
        raise ValueError("Conversion must be binary (0/1).")

    effects = data["estimated_treatment_effect"].to_numpy(dtype=float)
    ate = float(np.mean(effects))
    ate_se = float(np.std(effects, ddof=1) / np.sqrt(len(effects)))
    z = norm.ppf(0.975)

    # Sort observations from lowest to highest predicted treatment effect.
    data = data.sort_values("estimated_treatment_effect").reset_index(drop=True)
    data["effect_rank_bin"] = pd.qcut(
        np.arange(len(data)),
        q=min(n_bins, len(data)),
        labels=False,
        duplicates="drop",
    ) + 1

    bins = []
    for rank, group in data.groupby("effect_rank_bin", observed=True):
        treated = group[group["treatment"] == 1]["conversion"]
        control = group[group["treatment"] == 0]["conversion"]

        treated_rate = float(treated.mean()) if len(treated) else None
        control_rate = float(control.mean()) if len(control) else None

        bins.append({
            "rank_bin": int(rank),
            "rows": int(len(group)),
            "treated_rows": int(len(treated)),
            "control_rows": int(len(control)),
            "treated_conversion_rate": treated_rate,
            "control_conversion_rate": control_rate,
            "observed_rate_difference": (
                treated_rate - control_rate
                if treated_rate is not None and control_rate is not None
                else None
            ),
            "mean_predicted_effect": float(
                group["estimated_treatment_effect"].mean()
            ),
        })

    return {
        "rows_evaluated": int(len(data)),
        "predicted_effect_mean": ate,
        "predicted_effect_std": float(np.std(effects, ddof=1)),
        "predicted_effect_min": float(np.min(effects)),
        "predicted_effect_max": float(np.max(effects)),
        "mean_effect_normal_approximation_interval": [
            float(ate - z * ate_se),
            float(ate + z * ate_se),
        ],
        "rank_bins": bins,
        "caveat": (
            "The interval above describes uncertainty in the mean of predicted "
            "effects, not a valid causal ATE confidence interval. The rank-bin "
            "differences are descriptive unless evaluated with appropriate "
            "randomization-aware uncertainty and design checks."
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--bins", type=int, default=10)
    args = parser.parse_args()

    if not 2 <= args.bins <= 20:
        raise ValueError("--bins must be between 2 and 20.")

    data = pd.read_csv(args.input)
    results = evaluate_effects(data, n_bins=args.bins)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2) + "\n")

    print(f"Evaluated rows: {results['rows_evaluated']:,}")
    print(f"Mean predicted effect: {results['predicted_effect_mean']:.8f}")
    print(f"Predicted effect std: {results['predicted_effect_std']:.8f}")
    print(f"Saved evaluation: {args.output}")
    print("\nObserved conversion differences by predicted-effect rank:")
    for item in results["rank_bins"]:
        print(
            f"Bin {item['rank_bin']:>2}: "
            f"predicted={item['mean_predicted_effect']:+.6f}, "
            f"observed_difference={item['observed_rate_difference']}"
        )


if __name__ == "__main__":
    main()
