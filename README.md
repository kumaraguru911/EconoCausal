
# EconoCausal — Dynamic Pricing via Double Machine Learning

EconoCausal is an internship project exploring causal machine
learning for marketing decisions and budget-aware personalization.

## Week 1 progress

- Created the Python project structure and virtual environment.
- Downloaded and audited the Criteo Uplift Prediction dataset.
- Processed 13,979,592 rows in chunks; the audit found no missing values.
- Generated descriptive treatment-group analysis and EDA artifacts.
- Created an initial, provisional causal graph.
- Built a React + TypeScript dashboard using Vite and Plotly.
- Implemented campaign CSV upload, validation, KPI updates,
  campaign visualizations and a marketing-budget input.

## Dataset

Criteo Uplift Prediction Dataset:
https://ailab.criteo.com/criteo-uplift-prediction-dataset/

The dataset contains 12 anonymized features, treatment, conversion,
visit and exposure variables.

Important: this dataset concerns advertising treatment, not
discount amounts. Observed treatment-group differences are
descriptive until the experimental design and causal assumptions
have been verified.

## Dashboard

Run locally:

```bash
cd frontend
npm install
npm run dev
```

The dashboard's default campaign figures are illustrative demo data.
Uploaded campaign CSVs must contain:

- campaign
- impressions
- visits
- conversions
- spend

## Week 1 limitations

- The causal graph is provisional.
- No validated causal-effect estimates are claimed.
- The budget field is a configuration input, not an optimizer.
- Discount allocation, DML training, uplift evaluation and API
  integration remain future work.

## Planned work

Week 2: Double Machine Learning, treatment-effect evaluation,
uplift/Qini curves and causal refutation tests.

Week 3: budget-constrained optimization and discount allocation.

Week 4: REST API, drift detection and final integration.
