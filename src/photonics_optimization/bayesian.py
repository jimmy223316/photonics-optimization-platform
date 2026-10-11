"""Sequential Gaussian-process Bayesian maximization with expected improvement."""
from collections.abc import Iterable, Sequence
import math
import numpy as np
from scipy.special import ndtr
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern
from .core import Evaluation, Objective, Optimizer, Parameter
from .search import positive_integer, RandomSearch

def expected_improvement(mean: np.ndarray, std: np.ndarray, best: float, xi: float) -> np.ndarray:
    """Expected positive improvement for maximization; deterministic improvement at zero variance."""
    improvement = mean - best - xi
    z = np.divide(improvement, std, out=np.zeros_like(mean), where=std > 0)
    ei = improvement * ndtr(z) + std * np.exp(-0.5 * z ** 2) / math.sqrt(2 * math.pi)
    return np.where(std > 0, np.maximum(ei, 0), np.maximum(improvement, 0))

class BayesianOptimization(Optimizer):
    """Fit a GP after initial random points; maximize EI over a random candidate pool.

    Fixed Matern kernel hyperparameters avoid unstable small-data fitting. The
    surrogate is an optimizer aid, not a validated physical model.
    """
    def __init__(self, parameters: Sequence[Parameter], budget: int = 30,
                 initial_points: int = 5, candidate_pool: int = 512,
                 seed: int | None = 42, xi: float = 0.01) -> None:
        super().__init__(parameters)
        RandomSearch(parameters, budget, seed)  # Shared budget/seed validation.
        positive_integer(initial_points, "initial_points")
        positive_integer(candidate_pool, "candidate_pool")
        if initial_points > budget:
            raise ValueError("initial_points cannot exceed budget")
        if not math.isfinite(xi) or xi < 0:
            raise ValueError("xi must be finite and nonnegative")
        self.budget, self.initial_points = budget, initial_points
        self.candidate_pool, self.seed, self.xi = candidate_pool, seed, xi

    def evaluations(self, objective: Objective) -> Iterable[Evaluation]:
        rng = np.random.default_rng(self.seed)
        lower = np.array([p.lower for p in self.parameters])
        width = np.array([p.upper - p.lower for p in self.parameters])
        samples: list[np.ndarray] = []
        scores: list[float] = []
        best = -math.inf
        for index in range(self.budget):
            if index < self.initial_points:
                sample = rng.random(len(self.parameters))
            else:
                gp = GaussianProcessRegressor(
                    kernel=ConstantKernel(1.0) * Matern(length_scale=0.25, nu=2.5),
                    alpha=1e-8, normalize_y=True, optimizer=None)
                gp.fit(np.array(samples), np.array(scores))
                pool = rng.random((self.candidate_pool, len(self.parameters)))
                # Exclude already evaluated points; do not spend budget on repeats.
                fresh = np.array([not any(np.array_equal(p, s) for s in samples) for p in pool])
                pool = pool[fresh]
                if len(pool) == 0:
                    raise RuntimeError("Candidate pool exhausted")
                mean, std = gp.predict(pool, return_std=True)
                sample = pool[int(np.argmax(expected_improvement(mean, std, best, self.xi)))]
            point = {p.name: float(v) for p, v in zip(self.parameters, lower + sample * width)}
            evaluation = self.evaluate(point, objective, best)
            best = evaluation.best_so_far
            samples.append(sample)
            scores.append(evaluation.score)
            yield evaluation
