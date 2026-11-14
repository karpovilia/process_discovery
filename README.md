# Preparing Congestion Responses from Pre-Crisis Process Logs

Research code and experimental data for preparing responses to process congestion. This repository distributes protocols, process specifications, observations, fitted models, policies, independent evaluation trajectories and reproduction scripts.

- [Corrected structural campaign](artifact_v4/README.md): six process structures, four feedback mechanisms, twelve independent training datasets per cell.
- [Frozen protocol](artifact_v4/structural/PROTOCOL.md), [primary comparisons](artifact_v4/structural/analysis/confirmatory_summary.json) and [raw arithmetic audit](artifact_v4/structural/analysis/raw_audit.json).
- [Current archive index](releases/v4/packages/packages.json) and [distribution correction audit](releases/v4/CURATION.json).
- [Earlier structural campaign](artifact/README.md) and [its archive index](releases/v3/packages/packages.json), retained separately from the corrected confirmation.

Costs are normalized within each independently trained model by its no-action cost. The two original aggregate routing-feedback contrasts use equal weights across the six designed processes and two-sided 97.5% paired intervals. All fixed-action baselines, feedback-strength heuristics, known-generator planners and control mechanisms are retained. The processes are not a representative random sample of business processes.

## Reproduction

Install Git LFS and fetch every package in the selected index. GitHub source ZIP downloads can contain LFS pointers. With the recorded Python dependencies, run:

```sh
python artifact_v4/verify_bundle.py releases/v4/packages /path/to/new/verification_directory
```

The destination must not exist. The command verifies package/member hashes and regenerates saved numerical results without fitting models, selecting policies or running new main simulations. Use approved resource limits. Full runtime source, the executed native binary and provenance freezes are included. The compact artifact directories support browsing; complete observations and trajectories are in the release packages.

Manuscript PDFs, full manuscript sources, translations and submission forms are excluded from the current distribution. CURATION.json documents this packaging correction and byte preservation of retained scientific files. Original verification receipts are retained as provenance for the original packages; they are not a claim that curated archives retain their old checksums.

Generative AI assisted implementation, experiment operation and analysis. It is not a component of the evaluated process models. No conference submission is performed by this repository.
