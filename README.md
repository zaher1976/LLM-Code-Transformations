# Structural Complexity and Documentation Loss in Code Transformations by a Large Language Model

Research package archived on Zenodo, version 0.1.1, published 10 October 2026.

GitHub: https://github.com/zaher1976/LLM-Code-Transformations

Archived release DOI: https://doi.org/10.5281/zenodo.23287972

## Authors and affiliations

1. **Sura Salah** — Presidency of Al-Nahrain University, Baghdad, Iraq. Email: sura.salah89@nahrainuniv.edu.iq.
2. **Sama Hayder** — Administrative Technical College, Middle Technical University, Baghdad, Iraq. Email: sama.yaser91@gmail.com.
3. **Zaher Fadhil Raham** — College of Computing and Informatics, Universiti Tenaga Nasional (UNITEN), Selangor 43000, Malaysia; Biomass Department, Al-Nahrain Research Center for Renewable Energy, Al-Nahrain University, Baghdad, Iraq. ORCID: https://orcid.org/0009-0001-4728-806X.

**Corresponding author:** Zaher Fadhil Raham, pt21162@uniten.edu.my (alternative: zahir.raham@gmail.com).

The DOI identifies the previously archived 0.1.1 research package. This repository distributes data and analysis code only. The unpublished manuscript is not included. The manuscript was removed from both Zenodo archives as a correction to unintended inclusion. GitHub releases and tags 0.1.0, 0.1.1 and 0.1.2 were deleted. The main branch history excludes the manuscript; old unreferenced Git objects may require removal by GitHub Support.

## Recorded experiment

Four Python projects supplied 5,331 candidate rows. Seed-42 sampling selected 986 rows; 984 recorded transformations were available, and the final paired pipeline retained 910 pairs after 74 original-extraction failures. The recorded serving model is `gpt-4o-2024-08-06`; temperature 0.2 and top-p 0.1. The initial request used the model alias; the retry and ablation workflow used the snapshot explicitly. AST parsing is syntax validation, not functional-equivalence testing.

Independent remeasurement reproduced the 910 function identifiers, 74 exclusions and all saved numeric main-pipeline fields within absolute tolerance 1e-9. The ablation CSV was independently remeasured from its 100 archived transformations. See `reports/verification.json` and `reports/VERIFICATION.md` for exact checks and remaining limitations.

## Layout

- `data/`: seven authoritative input/result CSVs, unchanged from the uploaded archive.
- `scripts/`: portable remeasurement and verification scripts. They do not call an LLM, clone repositories or execute function bodies from the CSVs.
- `notebooks/`: clean Colab entry point for remeasurement from this package.
- `figures/`: figures supplied with the original final pipeline; their bytes are unchanged.
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

Exactly two final functions have identical source text in different files. Sampling reproduces the full source-row multiset; it does not reconstruct full repository paths or commit identities, which were not recorded. The 119 zero-volume pairs require special care in MI term diagnostics; the sum of the formal terms is not an exact decomposition of reported MI. See the verification report.

## Historical files

Earlier files bearing 823 or 892 in their names, `verified_paired_metrics.csv`, `Figure_Delta_CC_Histogram.png` and the earlier failed-transformation log are retained in the original user archive but excluded here. They are not inputs to the 910-pair analysis. The original full notebook contains exploratory cells, including an early simulated demonstration; those cells are not part of this clean reproduction entry point.

## Publication and permissions

The Zenodo record lists CC BY 4.0. Source snippets retain their upstream ownership and licence terms. Current upstream licence notices are supplied as reference notices; they do not recover the licence headers and source commits omitted during extraction. The deposit licence does not replace applicable third-party licence terms. The omitted original source paths and commit identifiers remain a provenance limitation.

The associated paper is an unpublished manuscript and is not distributed in the current repository or the corrected Zenodo archives.

## Citation

Salah, S., Hayder, S., & Raham, Z. F. (2026). *Structural Complexity and Documentation Loss in Code Transformations by a Large Language Model* (Version 0.1.1) [Research package]. Zenodo. https://doi.org/10.5281/zenodo.23287972

See `CITATION.cff` for machine-readable author and citation metadata.
