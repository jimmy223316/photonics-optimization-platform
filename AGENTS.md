# Development instructions

- Read README.md, PROJECT_STATE.json, ROADMAP.md, and TASK_QUEUE.md before modifying this repository.
- Preserve the modular objective/optimizer/result interface and Python 3.10 compatibility.
- Run `python -m pip install -r requirements.txt -e .` and `python -m pytest`.
- Regenerate examples with `python -m photonics_optimization.demo --output examples --seed 42` when changing the objective, algorithm, or output schema.
- Never present synthetic scores as validated optical simulations or experimental results. Preserve provenance labels in generated data and figures.
- Keep local execution free of paid APIs and API keys; do not commit secrets.
- Use feature branches and pull requests. Do not merge into main unless explicitly authorized.
- Update PROJECT_STATE.json and TASK_QUEUE.md with completed work and verified test results; distinguish local checks from remote CI.
- Avoid unrequested changes to existing user work.

- Regenerate CSV fixtures with `python scripts/generate_csv_example.py`. Never rename synthetic examples as external solver results.
- LumericalAdapter is an unimplemented, unvalidated design boundary; do not add proprietary dependencies to the default installation.
- Keep exact CSV replay distinct from any future interpolation or surrogate backend.

- Keep PyMeep optional, installed through environment-meep.yml rather than pip. Never replace unavailable FDTD runs with synthetic results.
- Run real Meep tests only with RUN_MEEP_TESTS=1 in the Conda environment. Record opt-in solver checks separately from default tests.
- Preserve raw FDTD powers and 2D/unvalidated provenance. Do not clip numerical efficiencies or claim full 3D device accuracy.
