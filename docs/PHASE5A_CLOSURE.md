# RINGEST Phase 5A — Closure Note

## Status

PHASE5A_CLOSED_AS_PRIOR_SHAPE_CONTROL

## Scope

This phase audited an apparent positive frequency residual in GWTC-3 ringdown data using an unpaired posterior-level comparison:

- DS side: pyRing DS_1mode_10M, free frequency f_t_0
- Kerr side: pyRing Kerr_220_0M, remnant samples Mf, final_spin
- Residual: residual_f = f_DS - f_Kerr_220(Mf, final_spin)

This is not a joint posterior residual.

## Verified cohort

- Source: GWTC-3 TGR pyRing local HDF5 files
- Expansion cohort: 24 events after excluding smoke events
- Locally verified: 20 events
- Blocked: 4 events due to missing expected local files

Blocked events:
- S190421ar
- S190503bf
- S190630ag
- S200208q

## Permanent scripts

- tools/verify_phase5a_unpaired_hdf5_provenance.py
- tools/compute_phase5a_unpaired_220_residuals.py
- tools/audit_phase5a_unpaired_220_outliers.py
- tools/summarize_phase5a_unpaired_220_sensitivity.py
- tools/phase5a_control_widthmatched_residual.py

## Main initial result

In the verified N=20 expansion cohort:
- positive_median = 18 / 20
- P(residual_f > 0) > 0.5 = 18 / 20

## Sensitivity result

- all_verified20: 18/20 positive
- broad_DS_frequency_false: 13/13 positive
- top5_positive_outliers_removed: 13/15 positive
- audit_clean_core: 9/9 positive

## Width-matched control

The apparent positive asymmetry is mostly explained by posterior-width / prior-shape mismatch.

Key diagnostics:
- median sigma_DS / sigma_Kerr ≈ 3.70
- median CDF_DS(f_kerr_median) ≈ 0.174
- FULL median residual: +26.69 Hz
- DS in KERR 90% band median: +2.60 Hz

By DS-width bucket:
- narrow (<100 Hz): n=8, positive=8, negative=0, median≈+5.13 Hz
- moderate (100–300 Hz): n=1, positive=0, negative=1, median≈−38.83 Hz
- wide (300–600 Hz): n=3, positive=2, negative=1, median≈+17.14 Hz
- prior-dominated (>600 Hz): n=8, positive=8, negative=0, median≈+187.86 Hz

## Interpretation

The initial 18/20 positive sign asymmetry is reproducible, but its magnitude is dominated by DS posterior/prior width. In the informative DS regime, the remaining offset is small, around a few Hz, and is compatible with methodological scatter.

## Final conclusion

Phase 5A does not provide evidence for Kerr violation or new QNM physics.

It does provide a reproducible methodological audit showing that unpaired DS-vs-Kerr ringdown frequency residuals can acquire an apparent positive sign asymmetry when the DS free-frequency posterior is much broader than the Kerr reference posterior.

## Forbidden claims

- Do not claim Kerr violation.
- Do not claim new physics.
- Do not claim a joint posterior residual.
- Do not claim a population detection.
- Do not mix with O4 or DS_2mode without separate audit.
- Do not mix smoke events into the main verified20 result except as a separate methodological check.

## Local data dependency

This snapshot uses a local symlink for the GWTC-3 HDF5 payloads:

- `data/IGWN-GWTC3-TGR-v2-rin -> /home/ignac/laboratorio_ringest/data/IGWN-GWTC3-TGR-v2-rin`

The scripts and phase5a tables are contained in this snapshot, but full HDF5 reproducibility requires that local payload directory or an equivalent copy.

## Payload policy

This snapshot includes the GWTC-3 HDF5 payload directory required by the Phase 5A scripts:

- `data/IGWN-GWTC3-TGR-v2-rin`

Therefore the snapshot is intended to be self-contained for reproducing the Phase 5A verified20 provenance, residual, outlier, sensitivity, and width-matched controls, subject to the public-data terms of the original GWTC-3 TGR release.


## Zenodo payload DOI

The heavy GWTC-3 HDF5 payload required for full HDF5-level reproduction is archived at:

https://doi.org/10.5281/zenodo.19922361
