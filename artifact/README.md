# Preparing Congestion Responses from Pre-Crisis Process Logs

Anonymous research artifact, version3. Download every package listed in packages.json and extract code_paper_analysis_v7.zip, the six P1–P6 result packages and P4/P5 resource-replay packages into one directory. Extract P0_reference_v2.zip under legacy/. development_record.zip is the preserved development audit trail and is excluded from confirmatory analysis.

Main manuscripts: manuscript/paper_en.pdf and paper_ru.pdf. Supplements retain the full experimental evidence. P0 is unchanged. The new structural campaign uses 288 independent training datasets across six designed structures and four feedback mechanisms, with known and discovered control flow evaluated separately.

Reproduce saved new aggregates with `python structural/summarize.py`; reproduce P0 selector diagnostics with `python selector/selector_sensitivity.py analyze`. The latter reads original P0 action outcomes from legacy/. Dependencies and versions are in structural/FREEZE.json. Run code sequentially within your resource limits. The supplied engine.so is the executed Linux x86-64 build; engine.cpp is its source. A fresh platform build must record its own binary hash and execution receipt.

To replicate new simulations, copy structural code, calibrated specifications and FREEZE.json into a fresh directory without main_v1 or analysis, then run `python campaign.py main`. Never overwrite completed outputs. The portable freeze differs only in relocated metadata; SOURCE_FREEZE.json and PORTABILITY.json preserve the original provenance. Numerical source results remain byte-for-byte unchanged.

Known-generator planning uses planning scenarios, not realized test arrivals. Selector sweeps and auxiliary replays are diagnostic and do not choose policies using test outcomes. Per-fit preparation receipts precede independent tests. Individual trajectories are dependent within a trained model; the inference unit is the independently trained dataset.

Generative AI assisted code, analysis, experiment operation, drafting and translation. The evaluated runtime models are regression, logistic routing and discrete-event process simulation. The manuscripts contain the full disclosure.
