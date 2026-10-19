import pandas as pd
import pytest

from causal_engine.evaluation import evaluate_effects


def test_evaluate_effects_returns_expected_structure():
    data = pd.DataFrame({
        "treatment": [0, 1, 0, 1, 0, 1, 0, 1],
        "conversion": [0, 1, 0, 0, 1, 1, 0, 0],
        "estimated_treatment_effect": [
            0.01, 0.08, 0.02, 0.07, 0.03, 0.06, 0.04, 0.05
        ],
    })

    results, curve = evaluate_effects(data, n_bins=2)

    assert results["rows_evaluated"] == 8
    assert results["treatment_propensity_estimate"] == pytest.approx(0.5)
    assert len(results["rank_bins"]) == 2
    assert len(curve) == 8
    assert {
        "fraction_targeted",
        "cumulative_gain",
        "random_baseline",
        "qini_difference",
    }.issubset(curve.columns)


def test_evaluate_effects_rejects_invalid_treatment():
    data = pd.DataFrame({
        "treatment": [0, 1, 2, 1],
        "conversion": [0, 1, 0, 0],
        "estimated_treatment_effect": [0.1, 0.2, 0.3, 0.4],
    })

    with pytest.raises(ValueError, match="Treatment must contain only 0/1"):
        evaluate_effects(data)


def test_evaluate_effects_rejects_invalid_bin_count():
    data = pd.DataFrame({
        "treatment": [0, 1, 0, 1],
        "conversion": [0, 1, 0, 0],
        "estimated_treatment_effect": [0.1, 0.2, 0.3, 0.4],
    })

    with pytest.raises(ValueError, match="n_bins"):
        evaluate_effects(data, n_bins=1)

def test_qini_curve_ends_at_zero_difference():
    data = pd.DataFrame({
        "treatment": [0, 1, 0, 1, 0, 1, 0, 1],
        "conversion": [0, 1, 0, 0, 1, 1, 0, 0],
        "estimated_treatment_effect": [
            0.01, 0.08, 0.02, 0.07, 0.03, 0.06, 0.04, 0.05
        ],
    })

    results, curve = evaluate_effects(data, n_bins=2)

    # At 100% targeting, model and random baselines must coincide.
    assert curve.iloc[-1]["qini_difference"] == pytest.approx(0.0)
    assert curve.iloc[-1]["cumulative_gain"] == pytest.approx(
        results["total_ipw_gain"]
    )
