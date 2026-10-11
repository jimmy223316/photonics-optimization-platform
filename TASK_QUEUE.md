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

## Next tasks (priority order)

1. Add evaluation/memory guards for large Cartesian grids; test rejection before expensive runs.
2. Add repeated-seed benchmark summaries; separate variation from scientific uncertainty.
3. Version and validate persisted result schemas and support loading saved runs.
4. Add CLI configuration of parameter bounds and search budgets.
5. Research an open-source solver adapter and establish analytic validation cases before generating scientific results.

## Release verification

- PR #2 now rebases its unique v0.2 extensions onto main after PR #1 was squash-merged. All 66 branch tests passed again on 2026-10-12.

- Local test status is recorded in PROJECT_STATE.json after executing pytest.
- Remote CI must be reviewed on the pull request; configured workflows alone are not evidence of a passing remote run.
- Weekly scheduling is activated only on the default branch after an authorized merge.
