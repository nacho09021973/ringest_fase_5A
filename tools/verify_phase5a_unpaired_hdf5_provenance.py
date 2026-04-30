#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import h5py
import pandas as pd

DEFAULT_DATASET = "GWTC3_rerun_PROD1/posterior_samples"
DS_REQUIRED_FIELDS = ("f_t_0", "tau_t_0")
KERR_REQUIRED_FIELDS = ("Mf", "final_spin")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def inspect_hdf5(path: Path, dataset: str, required_fields: tuple[str, ...]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "file_exists": path.exists(),
        "sha256": None,
        "dataset_path": dataset,
        "dataset_exists": False,
        "dataset_shape": None,
        "dataset_dtype": None,
        "dtype_fields": [],
        "n_samples": None,
        "required_fields": list(required_fields),
        "missing_fields": list(required_fields),
        "fields_verified": False,
        "error": "",
    }

    if not path.exists():
        result["error"] = "missing_file"
        return result

    result["sha256"] = sha256_file(path)

    try:
        with h5py.File(path, "r") as h5:
            if dataset not in h5:
                result["error"] = "missing_dataset"
                return result

            dset = h5[dataset]
            result["dataset_exists"] = True
            result["dataset_shape"] = tuple(int(x) for x in dset.shape)
            result["dataset_dtype"] = str(dset.dtype)
            result["n_samples"] = int(dset.shape[0]) if len(dset.shape) > 0 else None

            fields = list(dset.dtype.names or [])
            result["dtype_fields"] = fields

            missing = [f for f in required_fields if f not in fields]
            result["missing_fields"] = missing
            result["fields_verified"] = len(missing) == 0

            if missing:
                result["error"] = "missing_required_fields"

    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"

    return result


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Verify Phase 5A DS/Kerr HDF5 provenance for unpaired residual inputs."
    )
    ap.add_argument("--cohort-csv", required=True)
    ap.add_argument("--out-csv", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--dataset", default=DEFAULT_DATASET)
    args = ap.parse_args()

    df = pd.read_csv(args.cohort_csv)

    required_cols = {"event_id", "ds_path", "kerr_path"}
    missing_cols = sorted(required_cols - set(df.columns))
    if missing_cols:
        raise SystemExit(f"Missing required columns in cohort CSV: {missing_cols}")

    rows: list[dict[str, Any]] = []

    for _, r in df.iterrows():
        event_id = str(r["event_id"]).strip()
        ds_path = Path(str(r["ds_path"]).strip())
        kerr_path = Path(str(r["kerr_path"]).strip())

        ds = inspect_hdf5(ds_path, args.dataset, DS_REQUIRED_FIELDS)
        kr = inspect_hdf5(kerr_path, args.dataset, KERR_REQUIRED_FIELDS)

        layout_verified = bool(ds["fields_verified"] and kr["fields_verified"])

        rows.append({
            "event_id": event_id,
            "layout_verified": layout_verified,
            "verification_level": "hdf5_structured_dataset_verified" if layout_verified else "layout_blocked",

            "ds_path": ds["path"],
            "ds_file_exists": ds["file_exists"],
            "ds_sha256": ds["sha256"],
            "ds_dataset_path": ds["dataset_path"],
            "ds_dataset_exists": ds["dataset_exists"],
            "ds_dataset_shape": ds["dataset_shape"],
            "ds_n_samples": ds["n_samples"],
            "ds_required_fields": ";".join(ds["required_fields"]),
            "ds_missing_fields": ";".join(ds["missing_fields"]),
            "ds_dtype_fields": ";".join(ds["dtype_fields"]),
            "ds_error": ds["error"],

            "kerr_path": kr["path"],
            "kerr_file_exists": kr["file_exists"],
            "kerr_sha256": kr["sha256"],
            "kerr_dataset_path": kr["dataset_path"],
            "kerr_dataset_exists": kr["dataset_exists"],
            "kerr_dataset_shape": kr["dataset_shape"],
            "kerr_n_samples": kr["n_samples"],
            "kerr_required_fields": ";".join(kr["required_fields"]),
            "kerr_missing_fields": ";".join(kr["missing_fields"]),
            "kerr_dtype_fields": ";".join(kr["dtype_fields"]),
            "kerr_error": kr["error"],
        })

    res = pd.DataFrame(rows)

    out_csv = Path(args.out_csv)
    out_json = Path(args.out_json)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)

    res.to_csv(out_csv, index=False)

    summary = {
        "script": "tools/verify_phase5a_unpaired_hdf5_provenance.py",
        "purpose": "verify data provenance/layout for residual_220_unpaired_composition inputs",
        "cohort_csv": args.cohort_csv,
        "out_csv": args.out_csv,
        "dataset": args.dataset,
        "ds_required_fields": list(DS_REQUIRED_FIELDS),
        "kerr_required_fields": list(KERR_REQUIRED_FIELDS),
        "n_rows": int(len(res)),
        "n_unique_events": int(res["event_id"].nunique()),
        "n_layout_verified": int(res["layout_verified"].sum()),
        "n_layout_blocked": int((~res["layout_verified"]).sum()),
        "blocked_events": res.loc[~res["layout_verified"], "event_id"].tolist(),
        "claim_level": "provenance_only_no_residual_no_physics_claim",
    }

    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("wrote:", out_csv)
    print("wrote:", out_json)
    print("rows:", summary["n_rows"])
    print("unique_events:", summary["n_unique_events"])
    print("layout_verified:", summary["n_layout_verified"])
    print("layout_blocked:", summary["n_layout_blocked"])
    if summary["blocked_events"]:
        print("blocked_events:", ",".join(summary["blocked_events"]))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
