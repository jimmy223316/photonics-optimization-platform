# Task queue

## Completed in v0.1

- [x] Build modular Grid Search and Random Search.
- [x] Add explicitly synthetic coupling objective and convergence artifacts.
- [x] Add pytest coverage, push/PR CI, and scheduled status reporting.
- [x] Add README and Codex handoff files.

## Completed in v0.2

- [x] Add Bayesian Optimization with reproducibility and adaptive-feedback tests.
- [x] Import and analyze external CSV records without asserting scientific validation.
- [x] Add synthetic/CSV backend implementations and a future Lumerical interface.
- [x] Document limitations and add reproducible synthetic CSV fixtures.

## Completed in v0.3

- [x] Add optional Meep taper backend with normalization, PML, eigenmode excitation/decomposition, and DFT fields.
- [x] Add actual FDTD length/width sweep export and optimizer integration.
- [x] Add optional Conda environment, unit/solver integration tests, documentation, and manual solver workflow.
- [x] Install serial PyMeep 1.35.0 and execute actual tutorial and sweep cases; all four tutorial reflection values match the executed official script at printed precision.
- [x] Verify 97 default tests (3 solver tests skipped) and all 100 tests in Conda with real solver tests enabled.

## Next tasks (priority order)

1. Investigate raw super-unity and negative-flux diagnostics; vary grid/PML/monitor/time settings and document discrepancies.
2. Add evaluation/memory guards for large Cartesian grids; test rejection before expensive runs.
3. Add repeated-seed benchmark summaries; separate variation from scientific uncertainty.
4. Version and validate persisted result schemas and support loading saved runs.
5. Add CLI configuration of parameter bounds and search budgets.
6. Extend Meep resolution/PML/padding/time convergence checks and independent analytic references before claiming physical validation.
7. Add multi-band output decomposition and mode-identification checks for wider guides.
8. Evaluate full 3D models separately; do not extrapolate 2D taper outputs to device performance.

## Release verification

- PR #2 now rebases its unique v0.2 extensions onto main after PR #1 was squash-merged. All 66 branch tests passed again on 2026-10-12.

- Local test status is recorded in PROJECT_STATE.json after executing pytest.
- Remote CI must be reviewed on the pull request; configured workflows alone are not evidence of a passing remote run.
- Weekly scheduling is activated only on the default branch after an authorized merge.
