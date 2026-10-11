# Task queue

## Completed in v0.1

- [x] Build modular Grid Search and Random Search.
- [x] Add explicitly synthetic coupling objective and convergence artifacts.
- [x] Add pytest coverage, push/PR CI, and scheduled status reporting.
- [x] Add README and Codex handoff files.

## Next tasks (priority order)

1. Add evaluation/memory guards for large Cartesian grids; test rejection before expensive runs.
2. Add repeated-seed benchmark summaries; separate variation from scientific uncertainty.
3. Version and validate persisted result schemas and support loading saved runs.
4. Add CLI configuration of parameter bounds and search budgets.
5. Research an open-source solver adapter and establish analytic validation cases before generating scientific results.

## Release verification

- Local test status is recorded in PROJECT_STATE.json after executing pytest.
- Remote CI must be reviewed on the pull request; configured workflows alone are not evidence of a passing remote run.
- Weekly scheduling is activated only on the default branch after an authorized merge.
