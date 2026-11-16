# Reproducing the numerical results

## Environment and data

The recorded environment is Python 3.14.3 on Linux x86-64. Exact analysis dependencies are listed in [requirements.txt](requirements.txt). The packages also contain the executed native simulator, its C++ source, source hashes, frozen protocols and policy-preparation receipts.

Fetch all packages in [data/packages.json](data/packages.json). They occupy about 5.5 GB in compressed form; allow additional space for extraction. Git LFS is required: a small text file beginning with `version https://git-lfs.github.com/spec/v1` is a pointer, not a ZIP archive. GitHub's source-code ZIP is not a substitute for fetching the data.

From the repository directory:

```sh
git lfs pull --include="data/**" --exclude=""
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python artifact/verify_bundle.py data reproduced
```

The destination `reproduced` must not already exist. The command verifies package bytes, extracts the complete runtime and data, checks every file against the saved hash inventory, and regenerates numerical analyses. It also checks the link between each prepared policy and its frozen source. A successful run prints a receipt and writes `VERIFIED.json` next to the data directory. The command does not run new experiments.

## Finding the outputs

| Extracted location | Contents |
| --- | --- |
| `structural/calibration/` | Process specifications and calibration records |
| Independent-fit folders under `structural/` | Training datasets, models, prepared policies and future outcomes |
| `structural/analysis/` | Summary tables, paired comparisons and operational metrics |
| `selector/selector_results/` | Component-selection sensitivity results |
| `legacy/caise2027_artifact/` | Serial reference study P0, source and saved outputs |
| `development/` | Supporting semantic checks and diagnostic records |

The archive retains the exact execution paths used by the frozen scripts. Run analyses from the extracted directory, not from the compact browser copy in `artifact/`.

## Analysis entry points

The verifier runs these scripts sequentially and compares their numerical outputs with the stored hashes:

```sh
cd reproduced
python structural/summarize.py
python structural/confirmatory_summary.py
python structural/decision_integrity_audit.py
python structural/report_diagnostics.py
python structural/operational_report.py
python structural/render_results.py
python structural/paper_claims.py
python structural/input_isolation_audit.py
python selector/selector_sensitivity.py analyze
```

The main table is `structural/analysis/full_summary.csv`. Primary paired intervals are in `structural/analysis/confirmatory_summary.json`. Individual-process and diagnostic intervals are identified separately in the associated analysis files. The package index records the extraction destination and SHA-256 digest of every archive.
