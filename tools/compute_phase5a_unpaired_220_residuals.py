#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import pandas as pd

DEFAULT_DATASET = "GWTC3_rerun_PROD1/posterior_samples"
DEFAULT_SEED = 42
DEFAULT_N_DRAW = 50_000
DEFAULT_NEAR_ZERO_ABS_HZ = 5.0

CLAIM_LEVEL = "exploratory_only"
RESIDUAL_TYPE = "residual_220_unpaired_composition"
JOINTNESS = "unpaired_same_event"
NO_JOINT_RESIDUAL = True
NO_POPULATION_CLAIM = True
FORMULA = "Momega_R=1.5251-1.1568*(1-chi)^0.1292; f_Hz=32314*Momega_R/Mf"

DS_REQUIRED_FIELDS = ("f_t_0", "tau_t_0")
KERR_REQUIRED_FIELDS = ("Mf", "final_spin")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description=(
            "Compute Phase 5A exploratory unpaired 220 residuals from DS_1mode_10M "
            "and Kerr_220_0M HDF5 posteriors."
        )
    )
    ap.add_argument("--cohort-csv", required=True)
    ap.add_argument("--out-csv", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--provenance-csv")
    ap.add_argument(
        "--require-layout-verified",
        action="store_true",
        help="Require provenance rows with layout_verified=True for every cohort event.",
    )
    ap.add_argument("--dataset", default=DEFAULT_DATASET)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--n-draw", type=int, default=DEFAULT_N_DRAW)
    ap.add_argument("--near-zero-abs-hz", type=float, default=DEFAULT_NEAR_ZERO_ABS_HZ)
    return ap.parse_args()


def require_columns(df: pd.DataFrame, columns: set[str], label: str) -> None:
    missing = sorted(columns - set(df.columns))
    if missing:
        raise SystemExit(f"Missing required columns in {label}: {missing}")


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (np.bool_,)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    raise ValueError(f"Cannot parse boolean value: {value!r}")


def load_provenance(path: str | None, require_layout_verified: bool) -> pd.DataFrame | None:
    if path is None:
        if require_layout_verified:
            raise SystemExit("--require-layout-verified needs --provenance-csv")
        return None

    prov = pd.read_csv(path)
    require_columns(prov, {"event_id", "layout_verified", "ds_path", "kerr_path"}, "provenance CSV")
    prov["event_id"] = prov["event_id"].astype(str).str.strip()

    if prov["event_id"].duplicated().any():
        duplicated = sorted(prov.loc[prov["event_id"].duplicated(), "event_id"].unique())
        raise SystemExit(f"Duplicate event_id rows in provenance CSV: {duplicated}")

    if require_layout_verified:
        bad = [event_id for event_id, value in zip(prov["event_id"], prov["layout_verified"]) if not as_bool(value)]
        if bad:
            raise SystemExit(f"Provenance has layout_verified=False for events: {bad}")

    return prov


def verify_against_provenance(cohort: pd.DataFrame, provenance: pd.DataFrame | None, require_layout_verified: bool) -> None:
    if provenance is None:
        return

    prov_by_event = provenance.set_index("event_id")
    missing_events = sorted(set(cohort["event_id"]) - set(prov_by_event.index))
    if missing_events:
        raise SystemExit(f"Events missing from provenance CSV: {missing_events}")

    blocked: list[str] = []
    path_mismatches: list[str] = []
    for row in cohort.itertuples(index=False):
        prov = prov_by_event.loc[row.event_id]
        if require_layout_verified and not as_bool(prov["layout_verified"]):
            blocked.append(row.event_id)
        if str(row.ds_path).strip() != str(prov["ds_path"]).strip():
            path_mismatches.append(f"{row.event_id}: ds_path")
        if str(row.kerr_path).strip() != str(prov["kerr_path"]).strip():
            path_mismatches.append(f"{row.event_id}: kerr_path")

    if blocked:
        raise SystemExit(f"Provenance has layout_verified=False for cohort events: {blocked}")
    if path_mismatches:
        raise SystemExit(f"Cohort/provenance path mismatches: {path_mismatches}")


def read_fields(path: Path, dataset: str, fields: tuple[str, ...]) -> dict[str, np.ndarray]:
    if not path.exists():
        raise FileNotFoundError(path)

    with h5py.File(path, "r") as h5:
        if dataset not in h5:
            raise KeyError(f"{path}: missing dataset {dataset!r}")

        dset = h5[dataset]
        names = set(dset.dtype.names or [])
        missing = sorted(set(fields) - names)
        if missing:
            raise KeyError(f"{path}: missing fields {missing} in {dataset!r}")

        return {field: np.asarray(dset.fields(field)[:], dtype=float) for field in fields}


def clean_ds(fields: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    f_obs = fields["f_t_0"]
    tau = fields["tau_t_0"]
    keep = np.isfinite(f_obs) & np.isfinite(tau)
    return f_obs[keep], tau[keep]


def clean_kerr(fields: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mf = fields["Mf"]
    chi = fields["final_spin"]
    keep = np.isfinite(mf) & np.isfinite(chi) & (mf > 0.0) & ((1.0 - chi) >= 0.0)
    mf = mf[keep]
    chi = chi[keep]
    momega_r = 1.5251 - 1.1568 * np.power(1.0 - chi, 0.1292)
    f_kerr = 32314.0 * momega_r / mf
    keep_finite = np.isfinite(f_kerr)
    return mf[keep_finite], chi[keep_finite], f_kerr[keep_finite]


def q(values: np.ndarray, quantile: float) -> float:
    return float(np.quantile(values, quantile))


def compute_event(row: Any, rng: np.random.Generator, dataset: str, n_draw: int) -> dict[str, Any]:
    event_id = str(row.event_id).strip()
    ds_path = Path(str(row.ds_path).strip())
    kerr_path = Path(str(row.kerr_path).strip())

    ds_raw = read_fields(ds_path, dataset, DS_REQUIRED_FIELDS)
    kerr_raw = read_fields(kerr_path, dataset, KERR_REQUIRED_FIELDS)

    ds_n_samples = int(len(ds_raw["f_t_0"]))
    kerr_n_samples = int(len(kerr_raw["Mf"]))

    f_obs, tau = clean_ds(ds_raw)
    mf, chi, f_kerr = clean_kerr(kerr_raw)

    if len(f_obs) == 0:
        raise ValueError(f"{event_id}: no finite DS samples")
    if len(f_kerr) == 0:
        raise ValueError(f"{event_id}: no finite Kerr samples")

    ds_idx = rng.integers(0, len(f_obs), size=n_draw)
    kerr_idx = rng.integers(0, len(f_kerr), size=n_draw)

    f_obs_draw = f_obs[ds_idx]
    tau_draw = tau[ds_idx]
    mf_draw = mf[kerr_idx]
    chi_draw = chi[kerr_idx]
    f_kerr_draw = f_kerr[kerr_idx]
    residual = f_obs_draw - f_kerr_draw

    return {
        "event_id": event_id,
        "claim_level": CLAIM_LEVEL,
        "cohort_role": str(getattr(row, "cohort_role", "")).strip(),
        "residual_type": RESIDUAL_TYPE,
        "jointness": JOINTNESS,
        "no_joint_residual": NO_JOINT_RESIDUAL,
        "no_population_claim": NO_POPULATION_CLAIM,
        "formula": FORMULA,
        "seed": int(getattr(row, "seed", DEFAULT_SEED)) if hasattr(row, "seed") else None,
        "n_draw": n_draw,
        "ds_n_samples": ds_n_samples,
        "kerr_n_samples": kerr_n_samples,
        "f_obs_q05_hz": q(f_obs_draw, 0.05),
        "f_obs_q50_hz": q(f_obs_draw, 0.50),
        "f_obs_q95_hz": q(f_obs_draw, 0.95),
        "tau_q05_s": q(tau_draw, 0.05),
        "tau_q50_s": q(tau_draw, 0.50),
        "tau_q95_s": q(tau_draw, 0.95),
        "Mf_q05_msun": q(mf_draw, 0.05),
        "Mf_q50_msun": q(mf_draw, 0.50),
        "Mf_q95_msun": q(mf_draw, 0.95),
        "chi_q05": q(chi_draw, 0.05),
        "chi_q50": q(chi_draw, 0.50),
        "chi_q95": q(chi_draw, 0.95),
        "f_kerr_q05_hz": q(f_kerr_draw, 0.05),
        "f_kerr_q50_hz": q(f_kerr_draw, 0.50),
        "f_kerr_q95_hz": q(f_kerr_draw, 0.95),
        "residual_q05_hz": q(residual, 0.05),
        "residual_q50_hz": q(residual, 0.50),
        "residual_q95_hz": q(residual, 0.95),
        "p_residual_gt_0": float(np.mean(residual > 0.0)),
        "ds_path": str(ds_path),
        "kerr_path": str(kerr_path),
    }


def event_records(df: pd.DataFrame, mask: pd.Series) -> list[dict[str, Any]]:
    return [
        {
            "event_id": str(row.event_id),
            "residual_q50_hz": float(row.residual_q50_hz),
            "p_residual_gt_0": float(row.p_residual_gt_0),
        }
        for row in df.loc[mask].itertuples(index=False)
    ]


def write_outputs(results: pd.DataFrame, args: argparse.Namespace) -> None:
    out_csv = Path(args.out_csv)
    out_json = Path(args.out_json)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)

    results.to_csv(out_csv, index=False)

    positive_median = results["residual_q50_hz"] > 0.0
    p_gt_half = results["p_residual_gt_0"] > 0.5
    negative = results["residual_q50_hz"] < 0.0
    near_zero = results["residual_q50_hz"].abs() <= args.near_zero_abs_hz
    largest_positive_row = results.sort_values("residual_q50_hz", ascending=False).iloc[0]

    summary = {
        "script": "tools/compute_phase5a_unpaired_220_residuals.py",
        "cohort_csv": args.cohort_csv,
        "provenance_csv": args.provenance_csv,
        "require_layout_verified": bool(args.require_layout_verified),
        "out_csv": args.out_csv,
        "out_json": args.out_json,
        "dataset": args.dataset,
        "residual_type": RESIDUAL_TYPE,
        "jointness": JOINTNESS,
        "claim_level": CLAIM_LEVEL,
        "no_joint_residual": NO_JOINT_RESIDUAL,
        "no_population_claim": NO_POPULATION_CLAIM,
        "formula": FORMULA,
        "seed": args.seed,
        "n_draw": args.n_draw,
        "near_zero_abs_hz": args.near_zero_abs_hz,
        "n_rows": int(len(results)),
        "n_unique_events": int(results["event_id"].nunique()),
        "positive_median": {
            "count": int(positive_median.sum()),
            "denominator": int(len(results)),
            "events": results.loc[positive_median, "event_id"].tolist(),
        },
        "p_residual_gt_0_gt_0p5": {
            "count": int(p_gt_half.sum()),
            "denominator": int(len(results)),
            "events": results.loc[p_gt_half, "event_id"].tolist(),
        },
        "negative_events": event_records(results, negative),
        "near_zero_events": event_records(results, near_zero),
        "largest_positive_outlier": {
            "event_id": str(largest_positive_row["event_id"]),
            "residual_q50_hz": float(largest_positive_row["residual_q50_hz"]),
            "p_residual_gt_0": float(largest_positive_row["p_residual_gt_0"]),
        },
        "method_caveat": (
            "Exploratory unpaired same-event composition only: DS f_t_0/tau_t_0 and "
            "Kerr Mf/final_spin are sampled from separate posteriors, so this is not a "
            "joint sample-by-sample residual posterior and supports no population claim."
        ),
    }

    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("wrote:", out_csv)
    print("wrote:", out_json)
    print("rows:", summary["n_rows"])
    print("unique_events:", summary["n_unique_events"])
    print(
        "positive_median:",
        f"{summary['positive_median']['count']} / {summary['positive_median']['denominator']}",
    )
    print(
        "P(residual_f > 0) > 0.5:",
        f"{summary['p_residual_gt_0_gt_0p5']['count']} / {summary['p_residual_gt_0_gt_0p5']['denominator']}",
    )


def main() -> int:
    args = parse_args()
    cohort = pd.read_csv(args.cohort_csv)
    require_columns(cohort, {"event_id", "ds_path", "kerr_path"}, "cohort CSV")
    cohort["event_id"] = cohort["event_id"].astype(str).str.strip()

    provenance = load_provenance(args.provenance_csv, args.require_layout_verified)
    verify_against_provenance(cohort, provenance, args.require_layout_verified)

    rng = np.random.default_rng(args.seed)
    rows = [compute_event(row, rng, args.dataset, args.n_draw) for row in cohort.itertuples(index=False)]
    results = pd.DataFrame(rows)
    results["seed"] = args.seed
    write_outputs(results, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
