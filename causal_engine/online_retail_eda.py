"""Exploratory product-price analysis for UCI Online Retail II.

This is descriptive analysis, not causal price-effect estimation.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

INPUT = Path("data/processed/online_retail_ii_clean.csv")
SUMMARY = Path("reports/online_retail_ii_product_summary.csv")
VARIATION = Path("reports/online_retail_ii_price_variation.csv")
REPORT = Path("reports/online_retail_ii_eda.json")

# Known service, postage, fee, adjustment, and manual-entry codes.
NON_PRODUCT_CODES = {
    "POST", "DOT", "M", "AMAZONFEE", "ADJUST", "BANK CHARGES",
    "CRUK", "D", "C2", "S", "PADS", "B", "GIFT",
}


def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"Missing cleaned dataset: {INPUT}")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(INPUT, dtype={"Invoice": "string", "StockCode": "string"},
                     low_memory=False)

    initial_rows = len(df)
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    df["StockCode"] = df["StockCode"].str.strip()
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
    df["LineRevenue"] = df["Quantity"] * df["Price"]

    valid = (
        df["StockCode"].notna()
        & df["InvoiceDate"].notna()
        & df["Quantity"].gt(0)
        & df["Price"].gt(0)
    )
    df = df.loc[valid].copy()

    df["StockCodeUpper"] = df["StockCode"].str.upper()
    ordinary_product = ~df["StockCodeUpper"].isin(NON_PRODUCT_CODES)
    # Codes consisting only of letters are treated as non-standard codes.
    ordinary_product &= ~df["StockCodeUpper"].str.fullmatch(r"[A-Z]+", na=False)

    product_df = df.loc[ordinary_product].copy()
    product_df.drop(columns=["StockCodeUpper"], inplace=True)

    # Keep summaries interpretable; do not delete extreme rows from source data.
    product_summary = product_df.groupby("StockCode", as_index=False).agg(
        records=("StockCode", "size"),
        description=("Description", "first"),
        distinct_prices=("Price", "nunique"),
        min_price=("Price", "min"),
        median_price=("Price", "median"),
        mean_price=("Price", "mean"),
        max_price=("Price", "max"),
        total_units=("Quantity", "sum"),
        total_revenue=("LineRevenue", "sum"),
        first_seen=("InvoiceDate", "min"),
        last_seen=("InvoiceDate", "max"),
    )

    # Price-variation table only includes products with at least 20 observations.
    eligible = product_summary.loc[product_summary["records"] >= 20].copy()
    eligible["price_range"] = eligible["max_price"] - eligible["min_price"]
    eligible["price_ratio_max_min"] = (
        eligible["max_price"] / eligible["min_price"].replace(0, np.nan)
    )
    eligible["has_price_variation"] = eligible["distinct_prices"] > 1
    eligible.sort_values(
        ["has_price_variation", "records"], ascending=[False, False], inplace=True
    )

    product_summary.to_csv(SUMMARY, index=False)
    eligible.to_csv(VARIATION, index=False)

    report = {
        "input": str(INPUT),
        "initial_rows": int(initial_rows),
        "valid_transaction_rows": int(len(df)),
        "ordinary_product_rows": int(len(product_df)),
        "excluded_nonstandard_code_rows": int(len(df) - len(product_df)),
        "unique_ordinary_products": int(product_df["StockCode"].nunique()),
        "products_with_at_least_20_records": int(len(eligible)),
        "eligible_products_with_multiple_prices": int(
            eligible["has_price_variation"].sum()
        ),
        "eligible_products_with_one_price": int(
            (~eligible["has_price_variation"]).sum()
        ),
        "price_quantiles": {
            str(q): float(product_df["Price"].quantile(q))
            for q in [0.5, 0.9, 0.99, 0.999]
        },
        "quantity_quantiles": {
            str(q): float(product_df["Quantity"].quantile(q))
            for q in [0.5, 0.9, 0.99, 0.999]
        },
        "nonstandard_codes_excluded": sorted(NON_PRODUCT_CODES),
        "limitations": [
            "Transaction data is observational; price associations are not automatically causal.",
            "Only recorded purchases are observed; zero-purchase opportunities are absent.",
            "Promotions, seasonality, product mix, and demand may confound price-sales relationships.",
            "Non-standard codes are excluded from primary product analysis using a documented heuristic.",
            "Extreme values are retained; quantiles are reported to support later sensitivity checks.",
        ],
        "outputs": [str(SUMMARY), str(VARIATION), str(REPORT)],
    }

    with REPORT.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(json.dumps(report, indent=2))
    print("\nSaved product summary:", SUMMARY)
    print("Saved price variation:", VARIATION)
    print("Saved EDA report:", REPORT)


if __name__ == "__main__":
    main()
