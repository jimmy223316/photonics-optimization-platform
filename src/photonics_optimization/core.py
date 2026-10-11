"""Shared contracts and validated evaluation history (maximization)."""
from abc import ABC, abstractmethod
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
    """Implement candidates; shared optimize evaluates and records every point."""
    def __init__(self, parameters: Sequence[Parameter]) -> None:
        self.parameters = tuple(parameters)
        if not self.parameters or len({p.name for p in self.parameters}) != len(self.parameters):
            raise ValueError("Search space must be nonempty with unique names")

    @abstractmethod
    def candidates(self) -> Iterable[dict[str, float]]:
        """Yield candidates within the search space."""

    def optimize(self, objective: Objective) -> OptimizationResult:
        history: list[Evaluation] = []
        best = -math.inf
        for point in self.candidates():
            # Objective receives a copy so mutations cannot corrupt recorded candidates.
            score = float(objective(dict(point)))
            if not math.isfinite(score):
                raise ValueError("Objective returned a non-finite score")
            best = max(best, score)
            history.append(Evaluation(dict(point), score, best))
        if not history:
            raise ValueError("Optimizer generated no candidates")
        return OptimizationResult(type(self).__name__, tuple(history), getattr(self, "seed", None))
