#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

DEFAULT_RESULTS_CSV = (
    "data/phase5a_tables/"
    "phase5a_gwtc3_residual_220_unpaired_expansion_verified20_results.csv"
)
DEFAULT_AUDIT_CSV = (
    "data/phase5a_tables/"
    "phase5a_gwtc3_unpaired_220_outlier_audit.csv"
)
DEFAULT_OUT_CSV = (
    "data/phase5a_tables/"
    "phase5a_gwtc3_unpaired_220_sensitivity_summary.csv"
)
DEFAULT_OUT_JSON = (
    "data/phase5a_tables/"
    "phase5a_gwtc3_unpaired_220_sensitivity_summary.json"
)

CLAIM_LEVEL = "exploratory_sensitivity_only"
RESIDUAL_TYPE = "residual_220_unpaired_composition"
NO_JOINT_RESIDUAL = True
NO_POPULATION_CLAIM = True
DOES_NOT_RECALCULATE_RESIDUALS = True

RESULTS_REQUIRED_COLUMNS = {
    "event_id",
    "residual_q50_hz",
    "p_residual_gt_0",
}

AUDIT_FLAG_COLUMNS = [
    "high_positive_outlier",
    "negative_control",
    "near_zero",
    "broad_DS_frequency",
    "broad_residual_interval",
]
AUDIT_REQUIRED_COLUMNS = {"event_id", *AUDIT_FLAG_COLUMNS}

SUBSET_ORDER = [
    "all_verified20",
    "broad_DS_frequency_true",
    "broad_DS_frequency_false",
    "top5_positive_outliers_removed",
    "audit_clean_core",
    "negative_controls",
    "near_zero",
]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description=(
            "Summarize Phase 5A unpaired 220 sensitivity subsets from existing CSV "
            "summaries only. This script does not open HDF5 files or recalculate residuals."
        )
    )
    ap.add_argument("--results-csv", default=DEFAULT_RESULTS_CSV)
    ap.add_argument("--audit-csv", default=DEFAULT_AUDIT_CSV)
    ap.add_argument("--out-csv", default=DEFAULT_OUT_CSV)
    ap.add_argument("--out-json", default=DEFAULT_OUT_JSON)
    return ap.parse_args()


def require_columns(df: pd.DataFrame, columns: set[str], label: str) -> None:
    missing = sorted(columns - set(df.columns))
    if missing:
        raise SystemExit(f"Missing required columns in {label}: {missing}")


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, np.bool_):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    raise ValueError(f"Cannot parse boolean value: {value!r}")


def load_results(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    require_columns(df, RESULTS_REQUIRED_COLUMNS, "results CSV")
    df["event_id"] = df["event_id"].astype(str).str.strip()
    if df["event_id"].duplicated().any():
        duplicated = sorted(df.loc[df["event_id"].duplicated(), "event_id"].unique())
        raise SystemExit(f"Duplicate event_id rows in results CSV: {duplicated}")
    return df


def load_audit(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    require_columns(df, AUDIT_REQUIRED_COLUMNS, "audit CSV")
    df["event_id"] = df["event_id"].astype(str).str.strip()
    if df["event_id"].duplicated().any():
        duplicated = sorted(df.loc[df["event_id"].duplicated(), "event_id"].unique())
        raise SystemExit(f"Duplicate event_id rows in audit CSV: {duplicated}")
    for col in AUDIT_FLAG_COLUMNS:
        df[col] = df[col].map(parse_bool)
    return df[["event_id", *AUDIT_FLAG_COLUMNS]]


def attach_audit_flags(results: pd.DataFrame, audit: pd.DataFrame) -> pd.DataFrame:
    unknown = sorted(set(audit["event_id"]) - set(results["event_id"]))
    if unknown:
        raise SystemExit(f"Audit CSV contains events absent from results CSV: {unknown}")

    merged = results.merge(audit, on="event_id", how="left")
    for col in AUDIT_FLAG_COLUMNS:
        merged[col] = merged[col].fillna(False).map(parse_bool)
    return merged


def finite_or_nan(value: Any) -> float:
    if pd.isna(value):
        return float("nan")
    return float(value)


def summarize_subset(name: str, df: pd.DataFrame) -> dict[str, Any]:
    n_events = int(len(df))
    events = df["event_id"].tolist()

    row: dict[str, Any] = {
        "subset": name,
        "claim_level": CLAIM_LEVEL,
        "residual_type": RESIDUAL_TYPE,
        "no_joint_residual": NO_JOINT_RESIDUAL,
        "no_population_claim": NO_POPULATION_CLAIM,
        "does_not_recalculate_residuals": DOES_NOT_RECALCULATE_RESIDUALS,
        "n_events": n_events,
        "events": ";".join(events),
    }

    if n_events == 0:
        row.update(
            {
                "positive_median_count": 0,
                "positive_median_fraction": float("nan"),
                "positive_probability_count": 0,
                "positive_probability_fraction": float("nan"),
                "median_of_residual_q50_hz": float("nan"),
                "mean_of_residual_q50_hz": float("nan"),
                "min_residual_q50_hz": float("nan"),
                "max_residual_q50_hz": float("nan"),
                "median_p_residual_gt_0": float("nan"),
                "mean_p_residual_gt_0": float("nan"),
            }
        )
        return row

    positive_median = df["residual_q50_hz"] > 0.0
    positive_probability = df["p_residual_gt_0"] > 0.5
    row.update(
        {
            "positive_median_count": int(positive_median.sum()),
            "positive_median_fraction": float(positive_median.mean()),
            "positive_probability_count": int(positive_probability.sum()),
            "positive_probability_fraction": float(positive_probability.mean()),
            "median_of_residual_q50_hz": finite_or_nan(df["residual_q50_hz"].median()),
            "mean_of_residual_q50_hz": finite_or_nan(df["residual_q50_hz"].mean()),
            "min_residual_q50_hz": finite_or_nan(df["residual_q50_hz"].min()),
            "max_residual_q50_hz": finite_or_nan(df["residual_q50_hz"].max()),
            "median_p_residual_gt_0": finite_or_nan(df["p_residual_gt_0"].median()),
            "mean_p_residual_gt_0": finite_or_nan(df["p_residual_gt_0"].mean()),
        }
    )
    return row


def build_subsets(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    no_audit_flags = ~df[AUDIT_FLAG_COLUMNS].any(axis=1)
    return {
        "all_verified20": df,
        "broad_DS_frequency_true": df.loc[df["broad_DS_frequency"]],
        "broad_DS_frequency_false": df.loc[~df["broad_DS_frequency"]],
        "top5_positive_outliers_removed": df.loc[~df["high_positive_outlier"]],
        "audit_clean_core": df.loc[no_audit_flags],
        "negative_controls": df.loc[df["negative_control"]],
        "near_zero": df.loc[df["near_zero"]],
    }


def nan_to_none(value: Any) -> Any:
    if isinstance(value, float) and np.isnan(value):
        return None
    return value


def row_for_json(row: dict[str, Any]) -> dict[str, Any]:
    out = {key: nan_to_none(value) for key, value in row.items()}
    out["events"] = [] if row["events"] == "" else str(row["events"]).split(";")
    return out


def write_outputs(summary: pd.DataFrame, rows: list[dict[str, Any]], args: argparse.Namespace) -> None:
    out_csv = Path(args.out_csv)
    out_json = Path(args.out_json)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out_csv, index=False)

    by_subset = {row["subset"]: row_for_json(row) for row in rows}
    payload = {
        "script": "tools/summarize_phase5a_unpaired_220_sensitivity.py",
        "results_csv": args.results_csv,
        "audit_csv": args.audit_csv,
        "out_csv": args.out_csv,
        "out_json": args.out_json,
        "claim_level": CLAIM_LEVEL,
        "residual_type": RESIDUAL_TYPE,
        "no_joint_residual": NO_JOINT_RESIDUAL,
        "no_population_claim": NO_POPULATION_CLAIM,
        "does_not_recalculate_residuals": DOES_NOT_RECALCULATE_RESIDUALS,
        "subsets": by_subset,
        "method_caveat": (
            "Exploratory sensitivity summary from existing unpaired residual CSVs only; "
            "audit flags are taken from the outlier audit table and missing audit rows are "
            "treated as unflagged. This is not a joint residual posterior and supports no "
            "population-level physical claim."
        ),
    }
    out_json.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")

    print("wrote:", out_csv)
    print("wrote:", out_json)
    for row in rows:
        print(
            row["subset"] + ":",
            "n_events=" + str(row["n_events"]),
            "positive_median="
            + f"{row['positive_median_count']}/{row['n_events']}",
            "positive_probability="
            + f"{row['positive_probability_count']}/{row['n_events']}",
        )


def main() -> int:
    args = parse_args()
    results = load_results(args.results_csv)
    audit = load_audit(args.audit_csv)
    merged = attach_audit_flags(results, audit)
    subsets = build_subsets(merged)
    rows = [summarize_subset(name, subsets[name]) for name in SUBSET_ORDER]
    summary = pd.DataFrame(rows)
    write_outputs(summary, rows, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
