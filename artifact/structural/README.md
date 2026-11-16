# Process models and intervention selection

The study asks whether models learned from normal operation preserve the structure and behavior needed to choose a response to overload. It compares capacity increases and reductions in repeated processing, each activated by an observable unfinished-work threshold.

## Design

P0 is a serial reference process. P1–P6 contain combinations of branching, parallel execution, repeated processing and shared resource pools; their complete specifications are in [calibration](calibration). Four mechanisms vary whether service duration, return probability, both, or neither depend on load.

Each of the six families has 12 independent training datasets for each mechanism. Every fitted dataset is evaluated on 48 paired future episodes. The methods share action definitions, costs, thresholds and future arrival schedules. The prepared policy is fixed before evaluation; it has no access to future arrivals when deciding to activate.

## Comparisons

- **Behavior:** static models, predictive component selection, and models retaining service and routing load terms.
- **Structure:** supplied process structure, selected executable discovery, and standard Inductive Miner.
- **Baselines:** no action, every fixed action and threshold, a feedback-strength heuristic, and a planner with the known generator within the same finite action catalogue.
- **Diagnostics:** separate service/routing components, return sites, selector thresholds, resource changes and action-effect assumptions.

## Reading the results

[full_summary.csv](analysis/full_summary.csv) contains cost, severe-overload frequency, activations, lead time, unfinished work and cycle-time summaries. [confirmatory_summary.json](analysis/confirmatory_summary.json) contains the two prespecified aggregate routing-feedback comparisons, each with a two-sided 97.5% interval. The independent unit is a trained dataset; each family's mean has weight one sixth. Other comparisons are secondary or diagnostic.

In file labels, `discovered` denotes selected executable discovery, `legacy_discovered` denotes the standard Inductive Miner baseline, and `known` denotes supplied structure. These labels identify methods. The `fixed`, `service`, `routing` and `combined` fields identify feedback mechanisms. A lower normalized cost is better; a negative paired difference favors the first method.

## Source map

| File | Purpose |
| --- | --- |
| [specifications.py](specifications.py) | Process-family definitions |
| [engine.cpp](engine.cpp), [native.py](native.py) | Event-based execution and Python interface |
| [structure_discovery.py](structure_discovery.py) | Discovery candidates and executable route constraints |
| [learning.py](learning.py) | Service and routing models |
| [campaign.py](campaign.py) | Training, policy preparation and independent evaluation |
| [summarize.py](summarize.py), [confirmatory_summary.py](confirmatory_summary.py) | Per-fit aggregation and paired comparisons |
| [operational_report.py](operational_report.py) | Overload, activation and timing metrics |

For complete frozen protocols, source hashes and raw outcomes, extract the [data packages](../../data/packages.json) using the [reproduction instructions](../../REPRODUCING.md).
