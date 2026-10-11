"""Convergence plots from actual recorded toy-function evaluations."""
from pathlib import Path
from collections.abc import Sequence
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from .core import OptimizationResult

def plot_convergence(results: Sequence[OptimizationResult], path: Path) -> None:
    if not results:
        raise ValueError("At least one result is required")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for result in results:
        ax.plot(range(1, len(result.history) + 1),
                [e.best_so_far for e in result.history], label=result.algorithm)
    ax.set(xlabel="Objective evaluations", ylabel="Best synthetic efficiency",
           title="Synthetic coupling optimization — toy benchmark", ylim=(0, 1.05))
    ax.legend()
    ax.grid(alpha=0.25)
    fig.tight_layout()
    try:
        fig.savefig(path, dpi=160)
    finally:
        plt.close(fig)
