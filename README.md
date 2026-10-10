# Structural Complexity and Documentation Loss in Code Transformations by a Large Language Model

Research archive candidate, version 0.1.0. Prepared 10 October 2026. GitHub repository: https://github.com/zaher1976/LLM-Code-Transformations . No Zenodo DOI has been assigned.

Authors: Sura Salah, Sama Hayder, Zaher Fadhil Raham. Corresponding author: pt21162@uniten.edu.my. ORCID for Zaher: https://orcid.org/0009-0001-4728-806X.

## Recorded experiment

Four Python projects supplied 5,331 candidate rows. Seed-42 sampling selected 986 rows; 984 recorded transformations were available, and the final paired pipeline retained 910 pairs after 74 original-extraction failures. The recorded serving model is `gpt-4o-2024-08-06`; temperature 0.2 and top-p 0.1. The initial request used the model alias; the retry and ablation workflow used the snapshot explicitly. AST parsing is syntax validation, not functional-equivalence testing.

Independent remeasurement reproduced the 910 function identifiers, 74 exclusions and all saved numeric main-pipeline fields within absolute tolerance 1e-9. The ablation CSV was independently remeasured from its 100 archived transformations. See `reports/verification.json` and `reports/VERIFICATION.md` for exact checks and remaining limitations.

## Layout

- `data/`: seven authoritative input/result CSVs, unchanged from the uploaded archive.
- `scripts/`: portable remeasurement and verification scripts. They do not call an LLM, clone repositories or execute function bodies from the CSVs.
- `notebooks/`: clean Colab entry point for remeasurement from this package.
- `figures/`: figures supplied with the original final pipeline; their bytes are unchanged.
- `manuscript/`: corrected manuscript with unresolved author declarations retained.
- `reports/`: verification results, environment and scope notes.
- `LICENSES/`: current upstream project notices and provenance notes.

## Reproduce

Use Python 3.11 or later. The verified runtime is recorded in `reports/environment.json`; pins describe this verification, not the undocumented original generation environment.

```bash
python -m pip install -r requirements.txt
python scripts/recompute_pipeline.py
python scripts/recompute_ablation.py
python scripts/verify_archive.py
```

Generated files go to `outputs/`, leaving `data/` unchanged. To use another location, supply `--data-dir` and `--output-dir`. Verification exits with a nonzero status if its assertions fail.

## Measurement limits

CC uses Radon's total complexity; NLOC uses `raw.analyze().sloc`. Comment percentage includes multiline strings and may exceed 100 because its denominator is source lines. MI0 sets the MI comment input to zero on the same code; documentation can still affect logical-line counts. The cognitive metric is a custom AST score adapted from Campbell and has not been validated as equivalent to SonarSource. Its code is preserved for reproducibility; it is not silently corrected to a different metric.

Exactly two final functions have identical source text in different files. Sampling reproduces the full source-row multiset; it does not reconstruct full repository paths or commit identities, which were not recorded. The 119 zero-volume pairs require special care in MI term diagnostics; the sum of the formal terms is not an exact decomposition of reported MI. See the corrected manuscript and verification report.

## Historical files

Earlier files bearing 823 or 892 in their names, `verified_paired_metrics.csv`, `Figure_Delta_CC_Histogram.png` and the earlier failed-transformation log are retained in the original user archive but excluded here. They are not inputs to the 910-pair analysis. The original full notebook contains exploratory cells, including an early simulated demonstration; those cells are not part of this clean reproduction entry point.

## Publication and permissions

No blanket licence is assigned by this preparation. Source snippets retain their upstream ownership and licence terms. Current upstream licence notices are supplied as reference notices; they do not recover the licence headers and source commits omitted during extraction. Authors should complete source attribution and choose licences for their original scripts, metrics and manuscript before a public release. This candidate does not assert that all third-party attribution requirements have been resolved.

The author-contribution, funding and competing-interest fields in the manuscript still require author confirmation. Keep the paper labelled as a manuscript/preprint rather than a peer-reviewed publication until accepted.

## GitHub and Zenodo

1. This package is deposited in the GitHub repository linked above, with the folder structure preserved.
2. Confirm authorship, upstream attribution, public visibility and licences; update the release metadata with the repository URL.
3. Link GitHub to Zenodo and enable this repository **before** creating the release.
4. Publish a tagged GitHub release. Zenodo can archive it and assign a DOI; replace the candidate citation metadata with the actual DOI afterwards.

Official instructions: https://help.zenodo.org/docs/github/enable-repository/ and https://help.zenodo.org/docs/github/archive-software/github-upload/ . A separate Zenodo preprint record can describe the manuscript, with a related identifier pointing to the data/software record.
