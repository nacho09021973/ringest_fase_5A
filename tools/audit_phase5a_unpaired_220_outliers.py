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
DEFAULT_PROVENANCE_CSV = (
    "data/phase5a_tables/"
    "phase5a_gwtc3_expansion_verified20_hdf5_provenance.csv"
)
DEFAULT_OUT_CSV = (
    "data/phase5a_tables/"
    "phase5a_gwtc3_unpaired_220_outlier_audit.csv"
)
DEFAULT_OUT_JSON = (
    "data/phase5a_tables/"
    "phase5a_gwtc3_unpaired_220_outlier_audit_summary.json"
)

CLAIM_LEVEL = "exploratory_audit_only"
TOP_N = 5
NEAR_ZERO_ABS_HZ = 5.0
BROAD_DS_FREQUENCY_THRESHOLD = 0.5
BROAD_RESIDUAL_INTERVAL_THRESHOLD = 5.0

BASE_COLUMNS = [
    "event_id",
    "f_obs_q05_hz",
    "f_obs_q50_hz",
    "f_obs_q95_hz",
    "f_kerr_q05_hz",
    "f_kerr_q50_hz",
    "f_kerr_q95_hz",
    "residual_q05_hz",
    "residual_q50_hz",
    "residual_q95_hz",
    "p_residual_gt_0",
    "tau_q05_s",
    "tau_q50_s",
    "tau_q95_s",
    "Mf_q05_msun",
    "Mf_q50_msun",
    "Mf_q95_msun",
    "chi_q05",
    "chi_q50",
    "chi_q95",
    "ds_n_samples",
    "kerr_n_samples",
]

OUTPUT_COLUMNS = [
    "event_id",
    "audit_role",
    "f_obs_q05_hz",
    "f_obs_q50_hz",
    "f_obs_q95_hz",
    "f_kerr_q05_hz",
    "f_kerr_q50_hz",
    "f_kerr_q95_hz",
    "residual_q05_hz",
    "residual_q50_hz",
    "residual_q95_hz",
    "p_residual_gt_0",
    "tau_q05_s",
    "tau_q50_s",
    "tau_q95_s",
    "Mf_q05_msun",
    "Mf_q50_msun",
    "Mf_q95_msun",
    "chi_q05",
    "chi_q50",
    "chi_q95",
    "ds_n_samples",
    "kerr_n_samples",
    "f_obs_width_hz",
    "f_kerr_width_hz",
    "residual_width_hz",
    "relative_f_obs_width",
    "relative_residual_width",
    "high_positive_outlier",
    "negative_control",
    "near_zero",
    "broad_DS_frequency",
    "broad_residual_interval",
]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description=(
            "Audit Phase 5A exploratory unpaired 220 residual outliers from the "
            "already computed results CSV. This script does not recalculate residuals."
        )
    )
    ap.add_argument("--results-csv", default=DEFAULT_RESULTS_CSV)
    ap.add_argument("--provenance-csv", default=DEFAULT_PROVENANCE_CSV)
    ap.add_argument(
        "--no-provenance",
        action="store_true",
        help="Skip optional provenance consistency checks.",
    )
    ap.add_argument("--out-csv", default=DEFAULT_OUT_CSV)
    ap.add_argument("--out-json", default=DEFAULT_OUT_JSON)
    ap.add_argument("--top-n", type=int, default=TOP_N)
    ap.add_argument("--near-zero-abs-hz", type=float, default=NEAR_ZERO_ABS_HZ)
    ap.add_argument(
        "--broad-ds-frequency-threshold",
        type=float,
        default=BROAD_DS_FREQUENCY_THRESHOLD,
    )
    ap.add_argument(
        "--broad-residual-interval-threshold",
        type=float,
        default=BROAD_RESIDUAL_INTERVAL_THRESHOLD,
    )
    return ap.parse_args()


def require_columns(df: pd.DataFrame, columns: list[str] | set[str], label: str) -> None:
    missing = sorted(set(columns) - set(df.columns))
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
    require_columns(df, BASE_COLUMNS, "results CSV")
    if df["event_id"].duplicated().any():
        duplicated = sorted(df.loc[df["event_id"].duplicated(), "event_id"].astype(str).unique())
        raise SystemExit(f"Duplicate event_id rows in results CSV: {duplicated}")
    df["event_id"] = df["event_id"].astype(str).str.strip()
    return df


def check_provenance(results: pd.DataFrame, path: str | None) -> dict[str, Any]:
    if path is None:
        return {"checked": False}

    prov_path = Path(path)
    if not prov_path.exists():
        raise SystemExit(f"Provenance CSV not found: {path}")

    prov = pd.read_csv(prov_path)
    require_columns(prov, {"event_id", "layout_verified"}, "provenance CSV")
    prov["event_id"] = prov["event_id"].astype(str).str.strip()
    if prov["event_id"].duplicated().any():
        duplicated = sorted(prov.loc[prov["event_id"].duplicated(), "event_id"].unique())
        raise SystemExit(f"Duplicate event_id rows in provenance CSV: {duplicated}")

    missing = sorted(set(results["event_id"]) - set(prov["event_id"]))
    if missing:
        raise SystemExit(f"Results events missing from provenance CSV: {missing}")

    prov_by_event = prov.set_index("event_id")
    unverified = [
        event_id
        for event_id in results["event_id"]
        if not parse_bool(prov_by_event.loc[event_id, "layout_verified"])
    ]
    if unverified:
        raise SystemExit(f"Provenance has layout_verified=False for results events: {unverified}")

    path_mismatches: list[str] = []
    for path_col in ("ds_path", "kerr_path"):
        if path_col in results.columns and path_col in prov.columns:
            for row in results[["event_id", path_col]].itertuples(index=False):
                if str(getattr(row, path_col)).strip() != str(prov_by_event.loc[row.event_id, path_col]).strip():
                    path_mismatches.append(f"{row.event_id}: {path_col}")
    if path_mismatches:
        raise SystemExit(f"Results/provenance path mismatches: {path_mismatches}")

    return {
        "checked": True,
        "path": path,
        "layout_verified_events": int(len(results)),
    }


def role_text(row: pd.Series) -> str:
    roles: list[str] = []
    if bool(row["high_positive_outlier"]):
        roles.append("top_positive_outlier")
    if bool(row["negative_control"]):
        roles.append("negative_control")
    if bool(row["near_zero"]):
        roles.append("near_zero")
    return ";".join(roles)


def build_audit(results: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    top_events = (
        results.sort_values("residual_q50_hz", ascending=False)
        .head(args.top_n)["event_id"]
        .tolist()
    )
    selected_events = set(top_events)
    selected_events.update(results.loc[results["residual_q50_hz"] <= 0.0, "event_id"].tolist())
    selected_events.update(
        results.loc[results["residual_q50_hz"].abs() <= args.near_zero_abs_hz, "event_id"].tolist()
    )

    audit = results.loc[results["event_id"].isin(selected_events), BASE_COLUMNS].copy()
    audit["f_obs_width_hz"] = audit["f_obs_q95_hz"] - audit["f_obs_q05_hz"]
    audit["f_kerr_width_hz"] = audit["f_kerr_q95_hz"] - audit["f_kerr_q05_hz"]
    audit["residual_width_hz"] = audit["residual_q95_hz"] - audit["residual_q05_hz"]
    audit["relative_f_obs_width"] = audit["f_obs_width_hz"] / audit["f_obs_q50_hz"].abs()
    audit["relative_residual_width"] = audit["residual_width_hz"] / audit["residual_q50_hz"].abs().clip(lower=1.0)
    audit["high_positive_outlier"] = audit["event_id"].isin(top_events)
    audit["negative_control"] = audit["residual_q50_hz"] <= 0.0
    audit["near_zero"] = audit["residual_q50_hz"].abs() <= args.near_zero_abs_hz
    audit["broad_DS_frequency"] = audit["relative_f_obs_width"] > args.broad_ds_frequency_threshold
    audit["broad_residual_interval"] = audit["relative_residual_width"] > args.broad_residual_interval_threshold
    audit["audit_role"] = audit.apply(role_text, axis=1)

    role_rank = {
        "top_positive_outlier": 0,
        "negative_control": 1,
        "near_zero": 2,
    }
    audit["_role_rank"] = audit["audit_role"].str.split(";").str[0].map(role_rank).fillna(99)
    audit = audit.sort_values(["_role_rank", "residual_q50_hz"], ascending=[True, False])
    return audit[OUTPUT_COLUMNS].reset_index(drop=True)


def event_list(audit: pd.DataFrame, mask_col: str) -> list[str]:
    return audit.loc[audit[mask_col], "event_id"].tolist()


def write_outputs(audit: pd.DataFrame, provenance_check: dict[str, Any], args: argparse.Namespace) -> None:
    out_csv = Path(args.out_csv)
    out_json = Path(args.out_json)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    audit.to_csv(out_csv, index=False)

    broad_ds = audit.loc[audit["broad_DS_frequency"], "event_id"].tolist()
    broad_residual = audit.loc[audit["broad_residual_interval"], "event_id"].tolist()
    summary = {
        "script": "tools/audit_phase5a_unpaired_220_outliers.py",
        "results_csv": args.results_csv,
        "provenance": provenance_check,
        "out_csv": args.out_csv,
        "out_json": args.out_json,
        "claim_level": CLAIM_LEVEL,
        "n_events_audited": int(len(audit)),
        "top_n": int(args.top_n),
        "near_zero_abs_hz": float(args.near_zero_abs_hz),
        "thresholds": {
            "broad_DS_frequency": f"relative_f_obs_width > {args.broad_ds_frequency_threshold}",
            "broad_residual_interval": (
                f"relative_residual_width > {args.broad_residual_interval_threshold}"
            ),
        },
        "top_positive_outliers": event_list(audit, "high_positive_outlier"),
        "negative_controls": event_list(audit, "negative_control"),
        "near_zero": event_list(audit, "near_zero"),
        "n_broad_DS_frequency": int(audit["broad_DS_frequency"].sum()),
        "broad_DS_frequency_events": broad_ds,
        "n_broad_residual_interval": int(audit["broad_residual_interval"].sum()),
        "broad_residual_interval_events": broad_residual,
        "method_caveat": (
            "Exploratory audit of already computed unpaired same-event residual summaries only; "
            "no residuals are recalculated, no plots are made, and this is not a joint posterior "
            "or population-level physical claim."
        ),
    }
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("wrote:", out_csv)
    print("wrote:", out_json)
    print("events_audited:", summary["n_events_audited"])
    print("top_positive_outliers:", ",".join(summary["top_positive_outliers"]))
    print("negative_controls:", ",".join(summary["negative_controls"]))
    print("near_zero:", ",".join(summary["near_zero"]))
    print("broad_DS_frequency:", summary["n_broad_DS_frequency"])
    print("broad_residual_interval:", summary["n_broad_residual_interval"])


def main() -> int:
    args = parse_args()
    results = load_results(args.results_csv)
    provenance_path = None if args.no_provenance else args.provenance_csv
    provenance_check = check_provenance(results, provenance_path)
    audit = build_audit(results, args)
    write_outputs(audit, provenance_check, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
