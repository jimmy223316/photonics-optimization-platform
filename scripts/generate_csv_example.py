"""Generate an explicitly synthetic CSV fixture from actual toy evaluations."""
import csv
import math
from pathlib import Path
from photonics_optimization import GridSearch, default_parameters, synthetic_coupling

def main() -> None:
    target = Path("examples/datasets/synthetic_coupling.csv")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["offset_um", "angle_deg", "coupling_efficiency"])
        writer.writeheader()
        result = GridSearch(default_parameters(), 3).optimize(synthetic_coupling)
        for evaluation in result.history:
            writer.writerow({**evaluation.parameters, "coupling_efficiency": evaluation.score})

    with Path("examples/datasets/synthetic_width.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["width_nm", "eta", "data_kind"])
        for width in (300, 400, 500, 600, 700):
            writer.writerow([width, math.exp(-0.5 * ((width - 500) / 100) ** 2), "synthetic_analytic_toy"])

if __name__ == "__main__":
    main()
