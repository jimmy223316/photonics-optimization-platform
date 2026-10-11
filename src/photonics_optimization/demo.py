"""Reproducible equal-budget demonstration and machine-readable provenance."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
from .objective import default_parameters, synthetic_coupling
from .search import GridSearch, RandomSearch
from .bayesian import BayesianOptimization
from .plotting import plot_convergence

def run_demo(output: Path, seed: int = 42) -> None:
    space = default_parameters()
    results = [GridSearch(space, 11).optimize(synthetic_coupling),
               RandomSearch(space, 121, seed).optimize(synthetic_coupling),
               BayesianOptimization(space, 121, seed=seed).optimize(synthetic_coupling)]
    output.mkdir(parents=True, exist_ok=True)
    plot_convergence(results, output / "convergence.png")
    payload = {"data_kind": "synthetic_analytic_toy", "scientifically_validated": False,
               "objective": "exp(-0.5*((offset_um/0.8)^2+(angle_deg/4)^2))",
               "search_space": [asdict(p) for p in space],
               "results": [asdict(r) for r in results]}
    (output / "results.json").write_text(json.dumps(payload, indent=2) + "\n")

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("examples"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    run_demo(args.output, args.seed)

if __name__ == "__main__":
    main()
