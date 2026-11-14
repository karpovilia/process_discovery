# Reproduce the saved evidence

Extract every package at the destinations in packages.json. The compact repository view omits raw trajectories; use the packages for verification. Run scripts sequentially within your approved local resource limits. requirements_analysis.txt records the installed versions used for analysis and plotting; FREEZE.json records the simulation environment and frozen scientific input hashes.

From a fresh extracted artifact, run:

```sh
python structural/summarize.py
python structural/confirmatory_summary.py
python structural/decision_integrity_audit.py
python structural/report_diagnostics.py
python structural/operational_report.py
python structural/render_results.py
python structural/paper_claims.py
python selector/selector_sensitivity.py analyze
```

The provided verify_bundle.py performs these steps in a new directory, checks archive and member hashes, and compares regenerated numerical summaries, tables and figures byte for byte. It also checks the link from each independent fit's PREPARED.json to SOURCE_FREEZE.json. The preparation receipt is written before independent test outcomes and contains the complete candidate-policy scores and selected policies.

The two primary hypotheses and their correction are in PROTOCOL.md. Other-world comparisons, individual process contrasts, selector sweeps, effectiveness shifts and resource replays have their stated secondary or diagnostic status. calibration_audits.json records every pre-crisis violation; those datasets are retained. The primary routing claims require all routing calibration audits to pass. Original P0 and the exposed preceding structural campaign are separate records, not additional independent samples for the new estimates.

# Replicate simulations separately

Copy structural source, calibration files, pilot-validation receipt and freeze files into a new empty working directory. Omit main_v1 and analysis. With the supplied Linux x86-64 engine.so and recorded Python environment, execute `python campaign.py main`. This generates all four mechanisms and all six structures, using twelve fitted datasets per combination, and requires no GPU. Do not overwrite the preserved independent outputs. The selected policies are derived from calibration, validation and planning streams; tests use separate streams.

For a different platform, a possible native rebuild is:

```sh
c++ -O2 -std=c++17 -fPIC -shared engine.cpp -o engine.so
```

This command specifies a new build, not a claim about the original binary's exact compiler flags. Record compiler/version, binary hash and semantic regression checks in a new replication freeze before execution; do not alter the preserved SOURCE_FREEZE.json or claim binary identity without a hash comparison. Python checks native ABI sizes when loading the library.

# Rebuild the documents

The manuscript directory contains the LNCS class, bibliography style, source, generated figures and tables. `python build.py` compiles the two manuscripts and two supplements sequentially using pdfLaTeX for English, XeLaTeX for Russian, and BibTeX. LaTeX must provide the packages and fonts named in the preambles. The saved validation records identify every manuscript input and the resulting PDF hashes.
