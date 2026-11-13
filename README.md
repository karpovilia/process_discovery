# Preparing Congestion Responses from Pre-Crisis Process Logs

Research artifact for the CAiSE2027 manuscript. The method prepares an intervention and an observable activation rule from pre-crisis process logs and a specified stress library.

## Current state

The frozen structural extension is running: six process structures, four feedback mechanisms, twelve independent training datasets per combination (288 total). Known and train-only discovered structures are evaluated separately. Code and protocol are available here; complete verified results and revised manuscripts will be added when the run finishes. No new cost advantage is claimed before the complete analysis.

`experiments/caise2027_structural_20261113/v2/PROTOCOL.md` defines the experiment. `FREEZE.json` records the exact executed source and generator hashes. The preceding implementation was superseded after a pre-outcome loss-definition audit; `AMENDMENT.json` records this correction. No generator constants were selected using method performance.

## Implementation

- `specifications.py`: six process families, resource pools, generating laws and interventions.
- `engine.cpp` / `native.py`: single-thread workflow execution and paired counter-based randomness.
- `learning.py`: behavioral calibration and training-only process discovery.
- `campaign.py`: preparation receipts followed by independent test evaluation.
- `summarize.py`: paired independent-fit inference; no policy selection from test outcomes.

Dependencies and exact versions are recorded in `FREEZE.json`. The checked-in shared library is the executed Linux x86-64 build. To rebuild on another environment, use `g++ -std=c++17 -O3 -shared -fPIC engine.cpp -o engine.so`, record the new binary hash and treat this as a separate replication build. Do not silently change a completed experiment's freeze receipt.

The original serial-process experiment P0 remains unchanged. The source study uses synthetic operational data, not private organizational logs. Generative AI assisted implementation, analysis, drafting and translation; the manuscript includes the required usage statement.

The GitHub repository is the author's source repository. It is not itself an anonymous review link. A separately checked anonymous artifact is being prepared.
