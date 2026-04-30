# Phase 5A HDF5 payload

The GitHub repository does not include the heavy GWTC-3 HDF5 payload directory:

- data/IGWN-GWTC3-TGR-v2-rin/

This directory is required to rerun the HDF5-level provenance verification, residual computation, and width-matched controls.

The payload is distributed separately via Zenodo.

After downloading it, place or extract it as:

data/IGWN-GWTC3-TGR-v2-rin/

Expected approximate size: 3.1 GB

The Phase 5A scripts expect paths such as:

data/IGWN-GWTC3-TGR-v2-rin/rin/rin_S170104_pyring_DS_1mode_10M.h5
data/IGWN-GWTC3-TGR-v2-rin/rin/rin_S170104_pyring_Kerr_220_0M.h5

Once the payload is in place, rerun the Phase 5A scripts from the repository root.

Zenodo DOI: https://doi.org/10.5281/zenodo.19922361
