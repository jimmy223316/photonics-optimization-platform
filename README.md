# Photonics Optimization Platform

A modular Python prototype for maximizing optical coupling objectives with **Grid Search** and **Random Search**. Version 0.1 uses an explicitly synthetic analytic function to exercise the optimization pipeline.

**Scientific scope:** No electromagnetic solver, calibrated device model, or experimental data is included. Efficiencies and plots are toy-function evaluations, not scientific simulation results or predicted device performance.

## Quick start

Requires Python 3.10 or newer. From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt -e .
python -m pytest
python -m photonics_optimization.demo --output examples --seed 42
```

The installed `photonics-demo` command runs the same example. No paid APIs, external services, or API keys are needed to run the project.

## Example output

![Synthetic convergence comparison](examples/convergence.png)

The demo evaluates each algorithm exactly 121 times: an 11×11 Cartesian grid and 121 uniform random samples with seed 42. `examples/results.json` stores all candidates, scores, running best values, search bounds, seed, and the synthetic-data label. The plot is generated from these recorded evaluations. Grid order affects its curve; a single random seed is illustrative and does not establish algorithm superiority. The grid includes the analytically known peak by construction.

## Synthetic objective

```text
eta(offset_um, angle_deg) = exp(-0.5 * ((offset_um / 0.8)^2 + (angle_deg / 4)^2))
offset_um ∈ [-2, 2]; angle_deg ∈ [-10, 10]
```

The arbitrary widths and illustrative unit labels are not fitted to any device. The function lies in [0, 1] and reaches 1 at (0, 0). Both optimizers **maximize** the objective. They also support arbitrary finite scalar scores, including negative values.

## Python API

```python
from photonics_optimization import Parameter, RandomSearch

space = [Parameter("x", -1.0, 1.0)]
result = RandomSearch(space, budget=100, seed=42).optimize(
    lambda point: -(point["x"] - 0.2) ** 2
)
print(result.best.parameters, result.best.score)
```

`Optimizer` defines the shared evaluation contract; implement `candidates()` for new search methods. `Parameter` validates bounds. `OptimizationResult` retains the evaluation history and best candidate. Objectives receive a candidate copy and must return a finite scalar; exceptions propagate. Random Search resets its local NumPy generator per run, making repeated runs with the same configuration reproducible. Grid Search includes both endpoints and lazily enumerates points, but history storage still grows as points-per-dimension raised to the number of parameters. This prototype is intended for small search spaces.

## Repository structure

- `src/photonics_optimization/`: core contracts, search algorithms, synthetic objective, plotting, and CLI.
- `tests/`: bounds, reproducibility, known optima, evaluation history, output provenance, and report status checks.
- `scripts/weekly_report.py`: status reporting from actual pytest JUnit output.
- `.github/workflows/`: push/PR CI and weekly status automation.
- `ROADMAP.md`, `TASK_QUEUE.md`, `PROJECT_STATE.json`, `AGENTS.md`: future development guidance.

## Automation

CI tests Python 3.10–3.13 on pushes and pull requests and uploads test/example artifacts. The weekly workflow runs Mondays at **09:00 Asia/Taipei (01:00 UTC)**, with optional manual dispatch. It runs tests, generates a Markdown report from the actual JUnit counts, adds it to the Actions job summary, and uploads report/test/demo artifacts for 30 days. Failed tests remain failed; absent test output is reported as unknown. Reports do not claim historical progress or scientific validation.

GitHub schedules run from the default branch, so the schedule becomes active only after the workflow is merged. This change does not merge itself. Actions uses standard hosted runners and built-in repository capabilities; no API keys or paid API integrations are configured. Hosting quotas remain subject to the repository's GitHub plan.

## Development and license

Run `python -m pytest` before submitting changes. Keep synthetic and validated data distinct, document objective provenance, and update the handoff files as scope changes. See [ROADMAP.md](ROADMAP.md) for planned solver adapters and validation work. Licensed under the existing MIT [LICENSE](LICENSE).
