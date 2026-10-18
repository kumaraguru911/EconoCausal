# EconoCausal — Dataset Strategy

## Objective
Estimate price-related demand responses using Double Machine Learning (DML),
then use defensible estimates for revenue/profit-oriented pricing decisions.

## Dataset roles

### 1. Criteo Uplift Prediction Dataset
Status: Existing baseline
Role: Benchmark the DML training and treatment-effect evaluation pipeline.
Treatment: Advertising exposure.
Outcome: Conversion.
Limitation: This is not a price-treatment dataset. Results must not be
reported as price elasticity or personalized discount effects.

Source: https://ailab.criteo.com/criteo-uplift-prediction-dataset/

### 2. Dominick's Finer Foods scanner data
Status: Primary pricing-data candidate; acquisition and schema audit pending.
Role: Product/store/week-level price, unit sales, and promotion analysis.
Potential treatment: Price, defined carefully for a specific product/store/time.
Outcome: Units sold.
Potential controls: Product, store, week, promotions, and other available
pre-treatment variables.
Limitation: Observational price changes may be confounded. Use randomized
pricing experiments where identifiable; otherwise state identification
assumptions and avoid unsupported causal claims.

Source: https://www.chicagobooth.edu/research/kilts/research-data/dominicks

### 3. UCI Online Retail II
Status: Secondary dataset; acquisition and schema audit pending.
Role: Exploratory analysis of unit price, quantity, product, and time.
Limitation: Transaction records are observational and include only recorded
transactions. They do not independently identify the causal effect of price.

Source: https://archive.ics.uci.edu/dataset/502/online+retail

## Integration policy
Do not concatenate these datasets into one training table.
They have different units of observation, treatments, outcomes, and schemas.
Build separate preprocessing pipelines and reports for each dataset.
Compare results only where the estimands and assumptions are compatible.

## Planned workflow
1. Audit available files and dataset access.
2. Download permitted raw data into data/raw/; never commit raw data.
3. Validate schema, units, missing values, price variation, and outcome quality.
4. Create a cleaned product-store-time panel for pricing analysis.
5. Estimate and evaluate DML effects with explicit uncertainty checks.
6. Use price-response estimates in a constrained revenue/profit optimizer.
7. Keep the Criteo advertising benchmark clearly separated from pricing results.
