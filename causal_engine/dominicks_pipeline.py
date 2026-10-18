"""Consolidated, chunked pipeline for Dominick's Cereals data.

Run from repository root:
  python -m causal_engine.dominicks_pipeline audit
  python -m causal_engine.dominicks_pipeline validate-join
  python -m causal_engine.dominicks_pipeline prepare
  python -m causal_engine.dominicks_pipeline build-panel
  python -m causal_engine.dominicks_pipeline analyze
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/dominicks_cereals"
MOVEMENT = RAW / "wcer.csv"
PRODUCTS = RAW / "upccer.csv"
CLEAN = ROOT / "data/processed/dominicks_cereals_clean.csv"
PANEL = ROOT / "data/processed/dominicks_cereals_panel.csv"
AUDIT_REPORT = ROOT / "reports/dominicks_cereals_audit.json"
PREP_REPORT = ROOT / "reports/dominicks_cereals_preprocessing.json"
PANEL_REPORT = ROOT / "reports/dominicks_panel_summary.json"
PRICE_CSV = ROOT / "reports/dominicks_price_variation.csv"
PRICE_JSON = ROOT / "reports/dominicks_price_variation.json"
CHUNK_SIZE = 200_000


def require_files(*paths: Path) -> None:
    missing = [str(p) for p in paths if not p.is_file()]
    if missing:
        raise FileNotFoundError("Required input file(s) not found:\n  " + "\n  ".join(missing))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_products() -> pd.DataFrame:
    require_files(PRODUCTS)
    df = pd.read_csv(PRODUCTS, dtype={"UPC": "string"}, encoding="latin-1")
    df["UPC"] = df["UPC"].str.strip()
    return df


def audit() -> None:
    require_files(MOVEMENT, PRODUCTS)
    totals = {k: 0 for k in ["rows", "zero_price_positive_move", "zero_price_zero_move", "positive_price_positive_move", "positive_price_zero_move", "ok_not_1"]}
    for chunk in pd.read_csv(MOVEMENT, chunksize=CHUNK_SIZE, dtype={"UPC": "string", "SALE": "string"}):
        price = pd.to_numeric(chunk["PRICE"], errors="coerce")
        move = pd.to_numeric(chunk["MOVE"], errors="coerce")
        totals["rows"] += len(chunk)
        masks = {
            "zero_price_positive_move": (price == 0) & (move > 0),
            "zero_price_zero_move": (price == 0) & (move == 0),
            "positive_price_positive_move": (price > 0) & (move > 0),
            "positive_price_zero_move": (price > 0) & (move == 0),
            "ok_not_1": chunk["OK"] != 1,
        }
        for key, mask in masks.items():
            totals[key] += int(mask.sum())
    products = load_products()
    totals.update({"product_rows": int(len(products)), "unique_product_upcs": int(products["UPC"].nunique()), "duplicate_product_upc_rows": int(products["UPC"].duplicated().sum())})
    write_json(AUDIT_REPORT, totals)
    print("Dominick's Cereals audit")
    for key, value in totals.items(): print(f"{key}: {value}")
    print(f"\nReport saved to: {AUDIT_REPORT}")


def validate_join() -> None:
    require_files(MOVEMENT, PRODUCTS)
    product_upcs = set(load_products()["UPC"].dropna())
    total = matched = unmatched = 0
    movement_upcs: set[str] = set()
    for chunk in pd.read_csv(MOVEMENT, chunksize=CHUNK_SIZE, dtype={"UPC": "string", "SALE": "string"}):
        upcs = chunk["UPC"].str.strip()
        hits = upcs.isin(product_upcs)
        total += len(chunk); matched += int(hits.sum()); unmatched += int((~hits).sum())
        movement_upcs.update(upcs.dropna().unique().tolist())
    print("Movement rows:", total)
    print("Unique movement UPCs:", len(movement_upcs))
    print("Product lookup UPCs:", len(product_upcs))
    print("Matched movement rows:", matched)
    print("Unmatched movement rows:", unmatched)
    print("Unique movement UPCs missing from lookup:", len(movement_upcs - product_upcs))


def prepare() -> None:
    require_files(MOVEMENT, PRODUCTS)
    products = load_products().drop_duplicates(subset=["UPC"])
    CLEAN.parent.mkdir(parents=True, exist_ok=True)
    stats: dict[str, Any] = {k: 0 for k in ["input_rows", "output_rows", "invalid_price_rows", "invalid_qty_rows", "unmatched_product_rows", "ok_zero_rows_retained", "zero_price_rows_retained"]}
    first = True
    for chunk in pd.read_csv(MOVEMENT, chunksize=CHUNK_SIZE, dtype={"UPC": "string", "SALE": "string"}):
        stats["input_rows"] += len(chunk)
        chunk["UPC"] = chunk["UPC"].str.strip()
        for col in ["MOVE", "QTY", "PRICE", "PROFIT", "OK"]:
            chunk[col] = pd.to_numeric(chunk[col], errors="coerce")
        valid_qty = chunk["QTY"].notna() & (chunk["QTY"] > 0)
        valid_price = chunk["PRICE"].notna() & (chunk["PRICE"] > 0)
        stats["invalid_qty_rows"] += int((~valid_qty).sum())
        stats["invalid_price_rows"] += int((~valid_price).sum())
        stats["ok_zero_rows_retained"] += int((chunk["OK"] == 0).sum())
        stats["zero_price_rows_retained"] += int((chunk["PRICE"] == 0).sum())
        chunk["UNIT_PRICE"] = chunk["PRICE"].where(valid_price) / chunk["QTY"].where(valid_qty)
        chunk = chunk.merge(products[["UPC", "DESCRIP", "SIZE", "COM_CODE"]], on="UPC", how="left", validate="many_to_one", indicator=True)
        stats["unmatched_product_rows"] += int((chunk["_merge"] != "both").sum())
        chunk = chunk.drop(columns=["_merge"])
        stats["output_rows"] += len(chunk)
        chunk.to_csv(CLEAN, index=False, mode="w" if first else "a", header=first)
        first = False
    stats["unit_price_definition"] = "PRICE / QTY when PRICE > 0 and QTY > 0"
    stats["zero_price_and_OK_zero_rows_retained"] = True
    stats["raw_rows_removed"] = stats["input_rows"] - stats["output_rows"]
    write_json(PREP_REPORT, stats)
    print("Dominick's preprocessing complete")
    for key, value in stats.items(): print(f"{key}: {value}")
    print(f"\nOutput: {CLEAN}\nReport: {PREP_REPORT}")


def build_panel() -> None:
    require_files(CLEAN)
    PANEL.parent.mkdir(parents=True, exist_ok=True)
    stats = {k: 0 for k in ["input_rows", "positive_price_rows", "excluded_zero_or_missing_price_rows", "ok_zero_rows_in_panel"]}
    first = True
    for chunk in pd.read_csv(CLEAN, chunksize=CHUNK_SIZE, usecols=["STORE", "UPC", "WEEK", "MOVE", "QTY", "PRICE", "UNIT_PRICE", "OK", "DESCRIP"], dtype={"UPC": "string"}):
        stats["input_rows"] += len(chunk)
        chunk["UNIT_PRICE"] = pd.to_numeric(chunk["UNIT_PRICE"], errors="coerce")
        chunk["MOVE"] = pd.to_numeric(chunk["MOVE"], errors="coerce")
        valid = chunk["UNIT_PRICE"] > 0
        stats["positive_price_rows"] += int(valid.sum())
        stats["excluded_zero_or_missing_price_rows"] += int((~valid).sum())
        panel = chunk.loc[valid].copy()
        stats["ok_zero_rows_in_panel"] += int((panel["OK"] == 0).sum())
        panel.to_csv(PANEL, index=False, mode="w" if first else "a", header=first)
        first = False
    write_json(PANEL_REPORT, stats)
    print("Panel build complete")
    for key, value in stats.items(): print(f"{key}: {value}")
    print("Panel:", PANEL, "\nReport:", PANEL_REPORT)


def analyze() -> None:
    require_files(CLEAN)
    groups: dict[tuple[Any, Any], list[float | int]] = {}
    for chunk in pd.read_csv(CLEAN, usecols=["STORE", "UPC", "WEEK", "UNIT_PRICE"], chunksize=CHUNK_SIZE, dtype={"UPC": "string"}):
        chunk["UNIT_PRICE"] = pd.to_numeric(chunk["UNIT_PRICE"], errors="coerce")
        chunk = chunk[chunk["UNIT_PRICE"] > 0]
        summary = chunk.groupby(["STORE", "UPC"])["UNIT_PRICE"].agg(min_price="min", max_price="max", mean_sum="sum", observations="count")
        for (store, upc), row in summary.iterrows():
            key = (store, upc)
            if key not in groups:
                groups[key] = [float(row["min_price"]), float(row["max_price"]), float(row["mean_sum"]), int(row["observations"])]
            else:
                item = groups[key]
                item[0] = min(item[0], float(row["min_price"]))
                item[1] = max(item[1], float(row["max_price"]))
                item[2] += float(row["mean_sum"])
                item[3] += int(row["observations"])
    records = [{"STORE": store, "UPC": upc, "min_price": lo, "max_price": hi, "mean_price": total / count, "observations": count, "price_varies": hi > lo} for (store, upc), (lo, hi, total, count) in groups.items()]
    columns = ["STORE", "UPC", "min_price", "max_price", "mean_price", "observations", "price_varies"]
    result = pd.DataFrame(records, columns=columns)
    if not result.empty: result = result.sort_values(["STORE", "UPC"])
    PRICE_CSV.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(PRICE_CSV, index=False)
    varied = int(result["price_varies"].sum()) if not result.empty else 0
    pairs = len(result)
    report = {"store_product_pairs": int(pairs), "pairs_with_price_variation": varied, "pairs_with_one_observed_price": int(pairs - varied), "share_with_price_variation": float(result["price_varies"].mean()) if pairs else 0.0, "note": "Descriptive analysis of positive observed prices only. Price variation does not establish causal identification."}
    write_json(PRICE_JSON, report)
    print("Store-product pairs:", report["store_product_pairs"])
    print("Pairs with price variation:", report["pairs_with_price_variation"])
    print("Pairs with one observed price:", report["pairs_with_one_observed_price"])
    print("Share with price variation:", round(report["share_with_price_variation"], 4))
    print("Saved:", PRICE_CSV, "\nSaved:", PRICE_JSON)


def main() -> None:
    parser = argparse.ArgumentParser(description="Memory-conscious Dominick's Cereals data pipeline")
    parser.add_argument("command", choices=["audit", "validate-join", "prepare", "build-panel", "analyze"])
    args = parser.parse_args()
    {"audit": audit, "validate-join": validate_join, "prepare": prepare, "build-panel": build_panel, "analyze": analyze}[args.command]()

if __name__ == "__main__":
    main()
