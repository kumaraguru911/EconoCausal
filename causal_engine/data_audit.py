"""Inspect public datasets without assuming their schema."""

import argparse
import json
from pathlib import Path

import pandas as pd


def load_dataset(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(path, low_memory=False)
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    if suffix in {".json", ".jsonl"}:
        return pd.read_json(path, lines=(suffix == ".jsonl"))

    raise ValueError(
        f"Unsupported file type: {suffix}. "
        "Supported: CSV, Parquet, JSON and JSONL."
    )


def audit_dataset(path: Path) -> dict:
    df = load_dataset(path)

    report = {
        "file": str(path),
        "rows": int(len(df)),
        "columns_count": int(len(df.columns)),
        "columns": [],
        "duplicate_rows": int(df.duplicated().sum()),
        "missing_cells": int(df.isna().sum().sum()),
        "memory_mb": round(
            float(df.memory_usage(deep=True).sum()) / (1024**2), 2
        ),
    }

    for column in df.columns:
        series = df[column]
        item = {
            "name": str(column),
            "dtype": str(series.dtype),
            "missing": int(series.isna().sum()),
            "missing_pct": round(float(series.isna().mean() * 100), 2),
            "unique_values": int(series.nunique(dropna=True)),
        }

        if pd.api.types.is_numeric_dtype(series):
            item["min"] = (
                float(series.min()) if series.notna().any() else None
            )
            item["max"] = (
                float(series.max()) if series.notna().any() else None
            )

        report["columns"].append(item)

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Audit a public dataset's schema and data quality."
    )
    parser.add_argument("path", type=Path, help="Path to a dataset file")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/data_audit.json"),
        help="JSON report output path",
    )
    args = parser.parse_args()

    if not args.path.is_file():
        parser.error(f"File not found: {args.path}")

    report = audit_dataset(args.path)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"File: {report['file']}")
    print(f"Rows: {report['rows']:,}")
    print(f"Columns: {report['columns_count']}")
    print(f"Duplicate rows: {report['duplicate_rows']:,}")
    print(f"Missing cells: {report['missing_cells']:,}")
    print(f"Report saved to: {args.output}")


if __name__ == "__main__":
    main()
