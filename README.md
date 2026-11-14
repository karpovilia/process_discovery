# Preparing Congestion Responses from Pre-Crisis Process Logs

CAiSE 2027: corrected process execution, automatic discovery and manuscript v8.

- [English manuscript](papers/CAiSE2027_Preparing_Congestion_Responses_v8_EN.pdf)
- [Russian translation](papers/CAiSE2027_Preparing_Congestion_Responses_v8_RU.pdf)
- [English supplement](papers/CAiSE2027_Preparing_Congestion_Responses_v8_Supplement_EN.pdf) and [Russian supplement](papers/CAiSE2027_Preparing_Congestion_Responses_v8_Supplement_RU.pdf)
- [Submission fields](submission/CAiSE2027_Preparing_Congestion_Responses_v8_Submission_Fields.html)
- [Full archive index](releases/v4/packages/packages.json) and [fresh-extraction verification](releases/v4/VERIFIED.json)
- [Frozen protocol](artifact_v4/structural/PROTOCOL.md), [primary comparisons](artifact_v4/structural/analysis/confirmatory_summary.json) and [raw arithmetic audit](artifact_v4/structural/analysis/raw_audit.json)

The new campaign contains 288 independent training datasets: six process structures, four mechanisms, twelve fits per cell. Supplied structure, automatically selected structure and standard IM use the same corrected executor and fitted behavior. All original P0 results are unchanged. The earlier structural campaign and manuscript remain in [release v3](releases/v3/packages/packages.json); its exposed outcomes are not pooled into the new confirmatory evaluation.

Two aggregate routing-feedback contrasts were fixed before fresh main outcomes. Costs are normalized within each fit by its no-action cost, then paired differences receive equal weights across the six designed processes. Intervals are two-sided 97.5%, correcting for two hypotheses; they do not describe a representative population of all business processes.

- Retained-load versus predictive selection after automatic discovery: paired normalized cost difference -0.084773, adjusted 97.5% interval [-0.135261, -0.034284].
- Selected discovery versus standard IM, both using retained-load planning: paired normalized cost difference -0.095822, adjusted 97.5% interval [-0.120549, -0.071094].

The complete results include fixed actions, a feedback-strength rule fitted from training data, a planner using the true generator and the same action catalogue, control mechanisms, individual process outcomes, selector sensitivity and uncertainty about intervention effects. The manuscripts delimit which comparisons support a benefit.

## Reproduction

Install Git LFS and download every package in the release index. GitHub source ZIP downloads may contain LFS pointers. Using the Python dependencies recorded in artifact_v4/structural/FREEZE.json:

```sh
python artifact_v4/verify_bundle.py releases/v4/packages /path/to/new/verification_directory
```

The destination must not exist. The verifier checks every package and member, recomputes the primary comparisons from raw saved policy outcomes, and regenerates numerical summaries, tables and figures in the new directory. It also repeats a technical input-isolation check on the excluded pilots. It performs no new main-campaign simulation or test-based policy selection. Native simulation is single-threaded; apply your approved resource limits. Source, executed Linux x86-64 binary, source freeze and metadata relocation records are included. The compact artifact_v4 directory is for browsing; complete models, policies and trajectories are in the ZIP packages.

Generative AI assisted implementation, experiment operation, analysis, drafting and translation. Full disclosure is in the papers. No GenAI model is used in the evaluated process simulator.

This owner-identified GitHub repository is not an anonymous review URL. The exported packages are sanitized; a public anonymous mirror still requires separate access and verification. No EasyChair submission is performed by this release.
