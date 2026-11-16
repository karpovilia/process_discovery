# From Process Logs to Overload Decisions: Modeling and Controlled Stress Probing

Research artifact for preparing responses to overload in process-oriented information systems. Executable process models represent resource competition, service times and repeated processing. Candidate interventions are selected before independent future workloads, and activate from observed unfinished work.

## Start here

| What to inspect | Where to go |
| --- | --- |
| Process definitions and experimental design | [Study guide](artifact/structural/README.md) |
| Costs, overload events, activations and lead times | [Results table](artifact/structural/analysis/full_summary.csv) |
| Paired comparisons and confidence intervals | [Primary comparisons](artifact/structural/analysis/confirmatory_summary.json) |
| Predictive component-selection diagnostics | [Selector results](artifact/structural/analysis/selector_summary.csv) |
| Executable model, discovery and analysis code | [Source files](artifact/structural) |
| Complete observations, fitted models, policies and trajectories | [Data index](data/packages.json) |
| Reproduce numerical results from saved outputs | [Reproduction instructions](REPRODUCING.md) |

The data include the serial reference process P0 and six process families P1–P6. The six-family study uses four feedback mechanisms and 12 independently trained models per combination, for 288 fits. Policies are prepared using training, validation and planning data; future evaluation uses separate random streams.

Cost combines accumulated unfinished work and intervention charges. Normalized cost divides each trained model's mean evaluation cost by its corresponding no-action cost. The results retain fixed-action baselines, a feedback-strength heuristic, a known-generator planner and component ablations. The two primary comparisons use routing feedback, equal weights across P1–P6 and paired 97.5% confidence intervals.

## Reproduce

Install [Git LFS](https://git-lfs.com/) before downloading the large data files. From the repository directory:

```sh
git lfs pull --include="data/**" --exclude=""
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python artifact/verify_bundle.py data reproduced
```

Use a new destination directory. The verifier checks package and extracted-file hashes, then regenerates numerical summaries from saved outputs. It does not train models, choose new policies or simulate new workloads. See [REPRODUCING.md](REPRODUCING.md) for the environment, disk requirements and extracted layout.

## Repository layout

```text
artifact/          browsable scientific code and numerical summaries
data/              complete data packages and their checksum index
REPRODUCING.md     environment and reproduction commands
requirements.txt   recorded Python dependencies
```
