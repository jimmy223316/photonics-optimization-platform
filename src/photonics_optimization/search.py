"""Lazy Cartesian grids and reproducible uniform random search."""
from collections.abc import Iterable, Sequence
from itertools import product
from numbers import Integral
import numpy as np
from .core import Optimizer, Parameter

def positive_integer(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, Integral) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")

class GridSearch(Optimizer):
    def __init__(self, parameters: Sequence[Parameter], points_per_dimension: int = 11) -> None:
        super().__init__(parameters)
        positive_integer(points_per_dimension, "points_per_dimension")
        if points_per_dimension < 2:
            raise ValueError("Grid requires at least two points per dimension")
        self.points_per_dimension = points_per_dimension

    def candidates(self) -> Iterable[dict[str, float]]:
        axes = [np.linspace(p.lower, p.upper, self.points_per_dimension) for p in self.parameters]
        for values in product(*axes):
            yield {p.name: float(v) for p, v in zip(self.parameters, values)}

class RandomSearch(Optimizer):
    def __init__(self, parameters: Sequence[Parameter], budget: int = 121, seed: int | None = 42) -> None:
        super().__init__(parameters)
        positive_integer(budget, "budget")
        if seed is not None and (isinstance(seed, bool) or not isinstance(seed, Integral) or seed < 0):
            raise ValueError("seed must be a nonnegative integer or None")
        self.budget, self.seed = budget, seed

    def candidates(self) -> Iterable[dict[str, float]]:
        rng = np.random.default_rng(self.seed)
        for _ in range(self.budget):
            yield {p.name: float(rng.uniform(p.lower, p.upper)) for p in self.parameters}
