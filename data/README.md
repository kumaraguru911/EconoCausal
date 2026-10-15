# Dataset Documentation

## Criteo Uplift Prediction Dataset

Source:
https://ailab.criteo.com/criteo-uplift-prediction-dataset/

Local file:
data/raw/criteo/criteo-research-uplift-v2.1.csv.gz

Columns:
- f0-f11: anonymized features
- treatment: treatment indicator
- conversion: conversion outcome
- visit: visit outcome
- exposure: exposure indicator

Audit results:
- Rows: 13,979,592
- Missing values: 0
- Conversions: 40,774
- Visits: 656,929
- Exposures: 428,212

Important:
This dataset concerns advertising treatment, not discount amounts.
Observed group differences are descriptive and are not automatically
causal effects. Verify the variable definitions and experimental design
before causal estimation.
