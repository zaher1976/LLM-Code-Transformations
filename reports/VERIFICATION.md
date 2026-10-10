# Archive verification

Independent checks passed on 10 October 2026. Main and ablation remeasurement have maximum absolute numeric error **0.0** against the supplied CSVs in the recorded verification runtime. This does not establish correctness of the underlying metric definitions or functional equivalence.

- The pool has 5,331 rows; the curated sample has 986, transformations 984, final metrics 910, exclusions 74, ablation transformations/results 100 each.
- Function IDs are unique within each identified table. The final metrics and exclusions form disjoint sets that partition all 984 transformation IDs.
- Stratified pandas sampling with seed 42 reproduces the exact 986-row multiset including source code. The ablation seed 20261001 reproduces all 100 selected IDs.
- No complete curated source rows are duplicated. FUNC_0261 (`sag_pool.py`, `reset_parameters`) and FUNC_0268 (`top_k.py`, `reset_parameters`) have identical normalized source text and both enter the 910-pair analysis. Removing either produces the sensitivity means in verification.json; these are diagnostics, not replacement results.
- All saved delta columns equal post minus pre. Recomputed exclusion IDs, domains and stages match; version-specific exception wording is not required to match.
- Documentation was present in 550 original functions; 218 lost it completely. The prompt-ablation loss counts are 45 and 13.
- Zero Halstead volume occurs in 81 originals and 105 transformed functions; 119 pairs have it on at least one side. The positive-volume subset contains 791 pairs. Formal term sum -4.068405762230475; observed MI mean change -4.108953410668764. Full-sample term contributions use a zero-log substitute and are not an exact MI decomposition.

Remaining scientific limits: no execution of the function bodies or functional tests; a custom, unvalidated cognitive score; no original dependency manifest, repository commit hashes, full source paths or line coordinates; no repeated-generation assessment; no modelling of project-level dependence. Author declarations and a public repository/DOI are not inferred.

The requirements pins identify this successful independent verification environment, not the historical Colab package versions. The package omits exploratory/simulated cells and obsolete 823/892-pair outputs, while leaving original final data bytes unchanged.
