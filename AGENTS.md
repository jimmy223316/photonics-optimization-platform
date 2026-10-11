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
