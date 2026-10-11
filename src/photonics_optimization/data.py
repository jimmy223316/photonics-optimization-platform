"""Strict CSV import and descriptive analysis of recorded efficiencies."""
import argparse
import csv
from dataclasses import dataclass
import json
import math
from pathlib import Path
from collections.abc import Sequence
import numpy as np

@dataclass(frozen=True)
class SimulationRecord:
    parameters: dict[str, float]
    coupling_efficiency: float

    def __post_init__(self) -> None:
        if not self.parameters or not all(math.isfinite(v) for v in self.parameters.values()):
            raise ValueError("Record parameters must be nonempty and finite")
        if not math.isfinite(self.coupling_efficiency) or not 0 <= self.coupling_efficiency <= 1:
            raise ValueError("Record efficiency must be a finite fraction in [0, 1]")

@dataclass(frozen=True)
class SimulationDataset:
    parameter_names: tuple[str, ...]
    records: tuple[SimulationRecord, ...]
    source: str
    data_kind: str = "external_unvalidated"

    def __post_init__(self) -> None:
        if not self.parameter_names or len(set(self.parameter_names)) != len(self.parameter_names):
            raise ValueError("Dataset requires unique parameter names")
        if any(not name.strip() for name in self.parameter_names) or not self.records:
            raise ValueError("Dataset requires named parameters and records")
        if self.data_kind not in {"synthetic_analytic_toy", "external_unvalidated", "fdtd_meep_2d_unvalidated"}:
            raise ValueError("Dataset data_kind must not imply scientific validation")
        seen: set[tuple[float, ...]] = set()
        for record in self.records:
            if set(record.parameters) != set(self.parameter_names):
                raise ValueError("Record parameters must match dataset schema")
            key = tuple(record.parameters[name] for name in self.parameter_names)
            if key in seen:
                raise ValueError("Dataset contains duplicate parameter tuples")
            seen.add(key)

    def summary(self) -> dict[str, object]:
        values = np.array([r.coupling_efficiency for r in self.records])
        best = self.records[int(np.argmax(values))]
        return {"source": self.source, "data_kind": self.data_kind,
                "scientifically_validated": False, "count": len(self.records),
                "efficiency_min": float(values.min()), "efficiency_max": float(values.max()),
                "efficiency_mean": float(values.mean()), "efficiency_std_population": float(values.std()),
                "best_parameters": dict(best.parameters),
                "parameter_ranges": {name: [min(r.parameters[name] for r in self.records),
                                             max(r.parameters[name] for r in self.records)]
                                     for name in self.parameter_names}}

def load_simulation_csv(path: Path, parameter_names: Sequence[str],
                        efficiency_column: str = "coupling_efficiency",
                        data_kind: str = "external_unvalidated") -> SimulationDataset:
    """Read explicit parameter columns and efficiency fractions in [0, 1].

    Extra metadata columns are allowed. Duplicate parameter tuples are rejected
    to avoid silently deciding how repeated/noisy measurements should be reduced.
    """
    names = tuple(parameter_names)
    if not names or any(not n.strip() for n in names) or len(set(names)) != len(names):
        raise ValueError("Provide unique, nonempty parameter column names")
    if not efficiency_column or efficiency_column in names:
        raise ValueError("Efficiency column must be distinct from parameter columns")
    if data_kind not in {"synthetic_analytic_toy", "external_unvalidated", "fdtd_meep_2d_unvalidated"}:
        raise ValueError("Unsupported data_kind; importing does not validate scientific accuracy")
    records: list[SimulationRecord] = []
    seen: set[tuple[float, ...]] = set()
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        header = reader.fieldnames
        if not header or len(set(header)) != len(header):
            raise ValueError("CSV requires a header with unique columns")
        if not set((*names, efficiency_column)).issubset(header):
            raise ValueError("CSV is missing required parameter or efficiency columns")
        for row in reader:
            line = reader.line_num
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f"CSV row {line}: inconsistent column count")
            try:
                values = tuple(float(row[n]) for n in names)
                efficiency = float(row[efficiency_column])
            except (ValueError, TypeError) as exc:
                raise ValueError(f"CSV row {line}: required values must be numeric") from exc
            if not all(math.isfinite(v) for v in (*values, efficiency)):
                raise ValueError(f"CSV row {line}: values must be finite")
            if not 0 <= efficiency <= 1:
                raise ValueError(f"CSV row {line}: efficiency must be a fraction in [0, 1]")
            if values in seen:
                raise ValueError(f"CSV row {line}: duplicate parameter tuple")
            seen.add(values)
            records.append(SimulationRecord(dict(zip(names, values)), efficiency))
    if not records:
        raise ValueError("CSV contains no data rows")
    return SimulationDataset(names, tuple(records), str(path), data_kind)

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--parameters", nargs="+", required=True)
    parser.add_argument("--efficiency-column", default="coupling_efficiency")
    parser.add_argument("--data-kind", choices=["external_unvalidated", "synthetic_analytic_toy", "fdtd_meep_2d_unvalidated"], default="external_unvalidated")
    args = parser.parse_args()
    data = load_simulation_csv(args.csv, args.parameters, args.efficiency_column, args.data_kind)
    print(json.dumps(data.summary(), indent=2))

if __name__ == "__main__":
    main()
