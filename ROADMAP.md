# Roadmap

## v0.1 — working synthetic prototype

- Modular maximization contracts and finite parameter bounds.
- Grid Search and seeded Random Search with full evaluation histories.
- Reproducible synthetic example, plots, tests, CI, and weekly reporting.

## v0.2 — completed extensions

- Seeded Gaussian-process Bayesian Optimization with expected improvement.
- Strict external CSV import, descriptive analysis, and synthetic example datasets.
- Modular backend contract, executable synthetic backend, exact CSV replay.
- Unimplemented and unvalidated future Lumerical adapter configuration/interface.

## Next — optimization usability

- Per-parameter grid resolution and explicit evaluation/memory limits.
- Multiple-seed comparisons with uncertainty and equal evaluation budgets.
- Stable versioned result schema, export/import, and configurable CLI search spaces.

## v0.3 — optional Meep integration

- Add serial PyMeep 2D taper simulations with tutorial geometry, reference normalization, input reflection, output fundamental-mode transmission, and DFT Ez plots.
- Add Cartesian taper-length/output-width sweeps and existing-optimizer integration.
- Use a separate supported Conda environment and an opt-in solver test workflow.
- Retain explicit 2D/unvalidated provenance. Reproduction of the tutorial is not full physical validation.

## Next — solver development

- Define solver adapters without coupling search methods to any solver.
- Evaluate an open-source optical solver and document installation, units, geometry, wavelength, and assumptions.
- Add caching, timeouts, and explicit failed-evaluation policies before expensive runs.

## v0.4 — scientific validation

- Compare against documented analytic reference cases and convergence studies.
- Record solver versions, mesh settings, materials, and independent reference provenance.
- Introduce measurement comparisons only when real datasets are available and attributable.

No scientific accuracy or device-performance claims are planned until validation evidence exists.
