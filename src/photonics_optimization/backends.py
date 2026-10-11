"""Backend contracts, executable synthetic backend, and exact CSV replay."""
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
import math
from pathlib import Path
from .data import SimulationDataset
from .objective import synthetic_coupling

@dataclass(frozen=True)
class SimulationResult:
    parameters: dict[str, float]
    coupling_efficiency: float
    backend: str
    data_kind: str
    source: str
    scientifically_validated: bool = False

    def __post_init__(self) -> None:
        if not self.parameters or not all(math.isfinite(v) for v in self.parameters.values()):
            raise ValueError("Simulation parameters must be nonempty and finite")
        if not math.isfinite(self.coupling_efficiency) or not 0 <= self.coupling_efficiency <= 1:
            raise ValueError("Coupling efficiency must be a finite fraction in [0, 1]")

class SimulationBackend(ABC):
    """Implement run(); instances are scalar objectives usable by every optimizer.

    Backend failures propagate; no retries or invented fallback scores are applied.
    """
    @abstractmethod
    def run(self, parameters: Mapping[str, float]) -> SimulationResult:
        """Return a result with input parameters and explicit provenance."""

    def __call__(self, parameters: Mapping[str, float]) -> float:
        result = self.run(dict(parameters))
        if result.parameters != dict(parameters):
            raise ValueError("Backend result parameters do not match requested parameters")
        return result.coupling_efficiency

class SyntheticBackend(SimulationBackend):
    def run(self, parameters: Mapping[str, float]) -> SimulationResult:
        if set(parameters) != {"offset_um", "angle_deg"}:
            raise ValueError("Synthetic backend requires offset_um and angle_deg")
        return SimulationResult(dict(parameters), synthetic_coupling(parameters),
                                "synthetic", "synthetic_analytic_toy", "analytic Gaussian toy")

class CSVReplayBackend(SimulationBackend):
    """Return only recorded points. No interpolation or extrapolation is performed."""
    def __init__(self, dataset: SimulationDataset) -> None:
        self.dataset = dataset
        self._lookup = {tuple(r.parameters[n] for n in dataset.parameter_names): r
                        for r in dataset.records}

    def run(self, parameters: Mapping[str, float]) -> SimulationResult:
        if set(parameters) != set(self.dataset.parameter_names):
            raise ValueError("Parameters must match the CSV parameter schema")
        key = tuple(parameters[n] for n in self.dataset.parameter_names)
        if key not in self._lookup:
            raise ValueError("No recorded result for this exact parameter tuple")
        record = self._lookup[key]
        return SimulationResult(dict(parameters), record.coupling_efficiency,
                                "csv_replay", self.dataset.data_kind, self.dataset.source)

@dataclass(frozen=True)
class LumericalConfig:
    """Future adapter configuration; paths are design inputs, never executed here."""
    project_path: Path
    parameter_mapping: Mapping[str, str]
    efficiency_result: str

class LumericalAdapter(SimulationBackend):
    """Unimplemented design placeholder. No lumapi import or proprietary dependency.

    A future implementation must open a configured project, apply mapped parameters,
    run the solver, extract a scalar efficiency, record solver/project provenance,
    and close the session on success or failure. Nothing has been validated against
    Lumerical; construction and configuration do not establish solver availability.
    """
    def __init__(self, config: LumericalConfig) -> None:
        if not config.parameter_mapping or not config.efficiency_result:
            raise ValueError("Provide parameter mapping and efficiency result name")
        self.config = config

    def run(self, parameters: Mapping[str, float]) -> SimulationResult:
        raise NotImplementedError("Lumerical adapter is unimplemented and unvalidated; use a free backend")
