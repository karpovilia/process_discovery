# Preparing Congestion Responses from Pre-Crisis Process Logs

CAiSE2027 research manuscript and reproducibility release, 14 November 2026.

- [English manuscript, v7](papers/CAiSE2027_Preparing_Congestion_Responses_v7_EN.pdf): 13 pages before references.
- [Russian translation, v7](papers/CAiSE2027_Preparing_Congestion_Responses_v7_RU.pdf): 14 pages before references.
- [English supplement](papers/CAiSE2027_Preparing_Congestion_Responses_v7_Supplement_EN.pdf) and [Russian supplement](papers/CAiSE2027_Preparing_Congestion_Responses_v7_Supplement_RU.pdf).
- [Complete package index](releases/v3/packages/packages.json), [fresh-extraction verification](releases/v3/VERIFIED.json).
- [Frozen structural protocol](artifact/structural/PROTOCOL.md) and [aggregate comparisons](artifact/structural/analysis/aggregate.json).

The unchanged serial reference P0 is extended by 288 independent training datasets
across six complex structures and four feedback mechanisms. Known and training-only
discovered control flow are evaluated separately. All 3168 calibration/validation
episodes pass the pre-crisis criterion. Independent arithmetic checks cover 20736
episodes and 200448 policy paths with zero discrepancy.

The structural results are mixed. Under routing feedback with supplied structure,
mean cost reductions relative to predictive component selection are 8.1%, 29.8%, 34.6%
and 26.4% for P1, P2, P5, P6. None excludes zero after correction for six primary
comparisons; P4 instead has a corrected significant increase. The descriptive,
equal-process no-action-normalized routing difference is -0.090 [-0.135, -0.045].
With discovered structure it is 0.001 [-0.037, 0.038]. Strong fixed actions, a feedback
heuristic and a known-generator planner are included; no universal superiority is
claimed. The paper explains how structural and behavioral errors change decisions.

## Reproduce the evidence

Install Git LFS before cloning, or run `git lfs pull` after cloning. PDF and ZIP
objects use LFS; a GitHub source ZIP may contain pointers rather than the objects.
All scientific package hashes and sizes are recorded in packages.json.

Using the Python dependencies recorded in artifact/structural/FREEZE.json, run:

```sh
python artifact/verify_bundle.py releases/v3/packages /path/to/new/verification_directory
```

The destination must not exist. The verifier extracts all packages, checks their
hashes and every member, and regenerates numerical analyses, selector diagnostics,
tables and figures in the new location. It does not regenerate simulations or tune
policies from test outcomes. The resulting VERIFIED.json is written beside packages/.
Resource-heavy work should use the reader's approved compute limits; the supplied
native engine is single-threaded. Linux x86-64 binary and source are both provided.

The browsable artifact directory contains source, manuscripts and compact summaries.
Full fitted parameters, action outcomes and trajectories are in the separate ZIP
parts. The original execution freeze is preserved as SOURCE_FREEZE.json; metadata
relocations are documented in PORTABILITY.json. The superseded development campaign
and technical pilots remain separately labeled and are excluded from inference.

Generative AI assisted implementation, experiment operation, analysis, drafting and
translation; the manuscripts contain the complete disclosure. No GenAI model is
part of the evaluated process simulator.

This is the owner's source repository. Its URL and commit history identify the
owner and must not be used as an anonymous review link. A public anonymous mirror
still needs to be established and checked; the paper has not been submitted here.
