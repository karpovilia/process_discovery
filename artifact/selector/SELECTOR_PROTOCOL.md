# P0 selector sensitivity: post-confirmation diagnostic

Frozen before new planning calculations on 2026-11-13. Original P0 test outcomes were already inspected in the preceding research. This is a diagnostic sensitivity study, never a new confirmatory evaluation.

Return-gain thresholds: 0, 0.001, 0.0025, 0.005, 0.01; duration threshold fixed at 0.01.
Duration-gain thresholds: 0, 0.0025, 0.005, 0.01, 0.02; return threshold fixed at 0.005.
Strict greater-than retention, as in the original code. Also report all four fixed behavioral component masks (neither/service/routing/both). Use original 48 fits (4 mechanisms x 12 seeds), original fitted coefficients, original planning library/random streams/catalog/costs, and original test trajectories. No refitting and no new test generation.

Reuse existing planning outcomes whenever the component mask matches a saved model. Calculate only missing masks with the previously verified counter-draw cache, keeping original simulator semantics. Save choices before loading test results in this diagnostic execution. Do not choose a preferred threshold from test cost.

For each setting and mechanism report duration/return retention, action/policy agreement with the existing known-generator planner, test cost and normalized cost, excess cost over that planner, and severe-event rate. Uncertainty: paired independent training seeds, descriptive 95% Student-t intervals. Preserve per-seed choices, reused/new planning rows, parameters, hashes and source manifests. Original E7 outputs are read-only.
