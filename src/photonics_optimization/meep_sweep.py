"""Optional actual FDTD Cartesian sweeps integrated with Optimizer history."""
import argparse
from collections.abc import Iterable, Sequence
from dataclasses import asdict
from itertools import product
import csv
import json
import math
from pathlib import Path
from .core import Optimizer, Parameter, OptimizationResult
from .meep_backend import MeepTaperBackend, TaperConfig, load_meep

class TaperSweep(Optimizer):
    def __init__(self, lengths: Sequence[float], widths: Sequence[float]) -> None:
        self.lengths, self.widths = tuple(lengths), tuple(widths)
        for values in (self.lengths, self.widths):
            if not values or len(set(values)) != len(values) or any(not math.isfinite(v) or v <= 0 for v in values):
                raise ValueError("Sweep values must be unique, nonempty, finite and positive")
        # Singleton lists are valid sweeps; bounds merely provide search metadata.
        super().__init__([Parameter("taper_length_um", min(self.lengths)/2, max(self.lengths)*2),
                          Parameter("output_width_um", min(self.widths)/2, max(self.widths)*2)])

    def candidates(self) -> Iterable[dict[str, float]]:
        for length, width in product(self.lengths, self.widths):
            yield {"taper_length_um": length, "output_width_um": width}

def export_sweep(records: list[dict], output: Path, result: OptimizationResult | None = None) -> None:
    """Serialize completed real solver records, retaining raw numerical violations."""
    if not records:
        raise ValueError("No completed solver records to export")
    if any(r.get("data_kind") != "fdtd_meep_2d_unvalidated" or r.get("solver") != "Meep" for r in records):
        raise ValueError("Only actual Meep run records can be exported as FDTD sweep data")
    if result is not None and any(not r["optimization_acceptable"] for r in records):
        raise ValueError("Cannot attach accepted optimization history to rejected raw scores")
    output.mkdir(parents=True, exist_ok=True)
    payload = {"data_kind": "fdtd_meep_2d_unvalidated", "scientifically_validated": False,
               "optimization": asdict(result) if result is not None else None,
               "optimization_rejected_points": [r["parameters"] for r in records if not r["optimization_acceptable"]],
               "runs": records}
    (output / "sweep.json").write_text(json.dumps(payload, indent=2) + "\n")
    with (output / "sweep.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["taper_length_um", "output_width_um", "coupling_efficiency", "data_kind", "optimization_acceptable"])
        writer.writeheader()
        for record in records:
            writer.writerow({**record["parameters"], "coupling_efficiency": record["coupling_efficiency"],
                             "data_kind": record["data_kind"], "optimization_acceptable": record["optimization_acceptable"]})
    plot_sweep(records, output / "sweep.png")

def run_sweep(lengths: Sequence[float], widths: Sequence[float], output: Path,
              config: TaperConfig | None = None, save_fields: bool = True,
              diagnostics_only: bool = False) -> OptimizationResult | None:
    sweep = TaperSweep(lengths, widths)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Sweep output directory must be empty to preserve run provenance")
    load_meep()  # Fail before creating any artifacts if the optional solver is absent.
    backend = MeepTaperBackend(config, output, save_fields)
    if diagnostics_only:
        for point in sweep.candidates():
            backend.solve(point)
        result = None
    else:
        result = sweep.optimize(backend)
    export_sweep(backend.records, output, result)
    return result

def plot_sweep(records: list[dict], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    for width in sorted({r["parameters"]["output_width_um"] for r in records}):
        runs = sorted((r for r in records if r["parameters"]["output_width_um"] == width),
                      key=lambda r: r["parameters"]["taper_length_um"])
        lengths = [r["parameters"]["taper_length_um"] for r in runs]
        axes[0].plot(lengths, [r["powers"]["fundamental_transmission"] for r in runs], "o-", label=f"width {width:g} µm")
        for key, style in (("fundamental_reflection", "o-"), ("reflected_flux_fraction", "x--")):
            axes[1].plot(lengths, [r["powers"][key] for r in runs], style, label=f"{width:g} µm {key}")
    axes[0].set(ylabel="Raw fundamental-mode transmission ratio")
    axes[1].set(ylabel="Raw reflection (mode / flux)", xscale="log")
    if any(r["powers"]["reflected_flux_fraction"] <= 0 for r in records):
        axes[1].set_yscale("symlog", linthresh=1e-6)
    else:
        axes[1].set_yscale("log")
    for ax in axes:
        ax.set_xlabel("Taper length (µm)")
        ax.legend(fontsize=7)
        ax.grid(alpha=.3)
    fig.suptitle("Actual Meep FDTD — 2D, no 3D device validation")
    try:
        fig.savefig(path, dpi=150)
    finally:
        plt.close(fig)

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lengths", nargs="+", type=float, default=[1, 2, 4, 8])
    parser.add_argument("--widths", nargs="+", type=float, default=[2])
    parser.add_argument("--resolution", type=int, default=25)
    parser.add_argument("--output", type=Path, default=Path("artifacts/meep"))
    parser.add_argument("--no-fields", action="store_true")
    parser.add_argument("--diagnostics-only", action="store_true", help="Record raw solver ratios without accepting optimization scores")
    args = parser.parse_args()
    result = run_sweep(args.lengths, args.widths, args.output, TaperConfig(resolution=args.resolution), not args.no_fields, args.diagnostics_only)
    if result is None:
        print("Actual 2D FDTD diagnostic sweep complete; inspect raw powers and optimization_acceptable flags")
        return
    print(f"Best actual 2D FDTD transmission: {result.best.score}; parameters: {result.best.parameters}")

if __name__ == "__main__":
    main()
