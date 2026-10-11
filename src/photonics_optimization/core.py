"""Shared contracts and validated evaluation history (maximization)."""
from abc import ABC
from dataclasses import dataclass
from collections.abc import Callable, Iterable, Mapping, Sequence
import math

Objective = Callable[[Mapping[str, float]], float]

@dataclass(frozen=True)
class Parameter:
    name: str
    lower: float
    upper: float

    def __post_init__(self) -> None:
        if not self.name or not math.isfinite(self.lower) or not math.isfinite(self.upper):
            raise ValueError("Parameters require a name and finite bounds")
        if self.lower >= self.upper:
            raise ValueError("Lower bound must be smaller than upper bound")

@dataclass(frozen=True)
class Evaluation:
    parameters: dict[str, float]
    score: float
    best_so_far: float

@dataclass(frozen=True)
class OptimizationResult:
    algorithm: str
    history: tuple[Evaluation, ...]
    seed: int | None = None

    @property
    def best(self) -> Evaluation:
        return max(self.history, key=lambda item: item.score)

class Optimizer(ABC):
    """Implement static candidates or adaptive evaluations; optimize records history."""
    def __init__(self, parameters: Sequence[Parameter]) -> None:
        self.parameters = tuple(parameters)
        if not self.parameters or len({p.name for p in self.parameters}) != len(self.parameters):
            raise ValueError("Search space must be nonempty with unique names")

    def candidates(self) -> Iterable[dict[str, float]]:
        """Yield static candidates; adaptive optimizers implement evaluations instead."""
        raise NotImplementedError("This optimizer requires objective feedback")

    @staticmethod
    def evaluate(point: Mapping[str, float], objective: Objective, best: float) -> Evaluation:
        score = float(objective(dict(point)))
        if not math.isfinite(score):
            raise ValueError("Objective returned a non-finite score")
        return Evaluation(dict(point), score, max(best, score))

    def evaluations(self, objective: Objective) -> Iterable[Evaluation]:
        best = -math.inf
        for point in self.candidates():
            evaluation = self.evaluate(point, objective, best)
            best = evaluation.best_so_far
            yield evaluation

    def optimize(self, objective: Objective) -> OptimizationResult:
        history = tuple(self.evaluations(objective))
        if not history:
            raise ValueError("Optimizer generated no candidates")
        return OptimizationResult(type(self).__name__, history, getattr(self, "seed", None))
