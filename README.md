# Preparing Congestion Responses from Pre-Crisis Process Logs

Research artifact for the CAiSE2027 manuscript. The method prepares an intervention and an observable activation rule from pre-crisis process logs and a specified stress library.

## Checked manuscript revision v7

- [English paper](artifact/manuscript/paper_en.pdf), 13 main-text LNCS pages.
- [Russian translation](artifact/manuscript/paper_ru.pdf), 14 main-text pages.
- [English supplement](artifact/manuscript/supplement_en.pdf).
- [Russian supplement](artifact/manuscript/supplement_ru.pdf).

All 288 structural fits completed; all 3168 calibration/validation episodes pass
the pre-crisis criterion. Independent arithmetic checks cover 200448 policy paths
with zero discrepancy. Source/PDF consistency, numeric translation parity, references
and anonymous PDF metadata passed automated checks; selected pages were also
visually inspected. The original P0 evidence remains unchanged.

The new primary results are mixed: no per-structure improvement passes correction
for six comparisons, and P4 worsens. Secondary routing/combined averages favor
retention with supplied structure, but the routing aggregate benefit disappears
with discovered structure. The paper and supplement report strong comparators,
selector sensitivity and structural failures alongside the supported benefits.

The complete trajectory archive is being packaged and verified in a fresh location.
It has not yet been uploaded. PDFs use Git LFS; install LFS and run `git lfs pull`
if a downloaded file is a text pointer. This owner repository is not an anonymous
review link; a separate anonymous mirror is still required.

## Implementation

- `specifications.py`: six process families, resource pools, generating laws and interventions.
- `engine.cpp` / `native.py`: single-thread workflow execution and paired counter-based randomness.
- `learning.py`: behavioral calibration and training-only process discovery.
- `campaign.py`: preparation receipts followed by independent test evaluation.
- `summarize.py`: paired independent-fit inference; no policy selection from test outcomes.

Dependencies and exact versions are recorded in `FREEZE.json`. The checked-in shared library is the executed Linux x86-64 build. To rebuild on another environment, use `g++ -std=c++17 -O3 -shared -fPIC engine.cpp -o engine.so`, record the new binary hash and treat this as a separate replication build. Do not silently change a completed experiment's freeze receipt.

The original serial-process experiment P0 remains unchanged. The source study uses synthetic operational data, not private organizational logs. Generative AI assisted implementation, analysis, drafting and translation; the manuscript includes the required usage statement.

The GitHub repository is the author's source repository. It is not itself an anonymous review link. A separately checked anonymous artifact is being prepared.
