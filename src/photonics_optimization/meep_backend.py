"""Optional actual 2D Meep FDTD taper simulation; never falls back to toy data."""
from collections.abc import Mapping
from dataclasses import asdict, dataclass
import importlib
import math
from numbers import Integral
from pathlib import Path
import json
from typing import Any
import numpy as np
from .backends import SimulationBackend, SimulationResult

TUTORIAL = "https://meep.readthedocs.io/en/latest/Python_Tutorials/Mode_Decomposition/#reflectance-of-a-waveguide-taper"

class MeepUnavailableError(ImportError):
    """PyMeep/MPB is not available in the active environment."""

def load_meep() -> Any:
    try:
        mp = importlib.import_module("meep")
    except (ImportError, OSError) as exc:
        raise MeepUnavailableError("Install PyMeep with environment-meep.yml using Conda; no synthetic fallback is provided") from exc
    if not all(hasattr(mp, name) for name in ("Simulation", "EigenModeSource", "Prism")):
        raise MeepUnavailableError("The imported meep module is not PyMeep; use the conda-forge pymeep package")
    return mp

@dataclass(frozen=True)
class TaperConfig:
    """Tutorial defaults. Length unit is micrometers; c=1 and f=1/wavelength."""
    resolution: int = 25
    input_width_um: float = 1.0
    straight_length_um: float = 10.0
    air_padding_um: float = 3.0
    pml_x_um: float = 6.0
    pml_y_um: float = 2.0
    wavelength_um: float = 6.67
    epsilon: float = 12.0
    decay_interval: float = 50.0
    decay_threshold: float = 1e-9
    max_time: float = 4000.0

    def __post_init__(self) -> None:
        if isinstance(self.resolution, bool) or not isinstance(self.resolution, Integral) or self.resolution < 4:
            raise ValueError("resolution must be an integer >= 4")
        for name, value in asdict(self).items():
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if self.epsilon <= 1 or self.decay_threshold >= 1:
            raise ValueError("Require epsilon > 1 and decay_threshold < 1")
        if self.max_time <= self.decay_interval:
            raise ValueError("max_time must exceed decay_interval")

def validate_taper(parameters: Mapping[str, float]) -> tuple[float, float]:
    if set(parameters) != {"taper_length_um", "output_width_um"}:
        raise ValueError("Provide taper_length_um and output_width_um")
    length, width = float(parameters["taper_length_um"]), float(parameters["output_width_um"])
    if not all(math.isfinite(v) and v > 0 for v in (length, width)):
        raise ValueError("Taper length and output width must be finite and positive")
    return length, width

def normalized_powers(incident: complex, reflected: complex, transmitted: complex,
                      incident_flux: float, reflected_flux: float, output_flux: float) -> dict[str, float]:
    denominator = abs(incident) ** 2
    if not math.isfinite(denominator) or denominator <= 0 or not math.isfinite(incident_flux) or incident_flux <= 0:
        raise ValueError("Normalization run must have finite positive input mode power and flux")
    values = {"incident_mode_power": denominator, "incident_flux": incident_flux,
              "fundamental_transmission": abs(transmitted) ** 2 / denominator,
              "fundamental_reflection": abs(reflected) ** 2 / denominator,
              "reflected_flux_fraction": -reflected_flux / incident_flux,
              "output_flux_fraction": output_flux / incident_flux}
    if not all(math.isfinite(v) for v in values.values()):
        raise ValueError("Nonfinite mode decomposition or flux result")
    # Do not clamp numerical power ratios; raw values belong in the run record.
    return values

def numerical_warnings(powers: Mapping[str, float]) -> list[str]:
    """Flag physical-range violations without modifying measured numerical ratios."""
    keys = ("fundamental_transmission", "fundamental_reflection", "reflected_flux_fraction", "output_flux_fraction")
    return [f"{key} lies outside [0,1]" for key in keys if not 0 <= powers[key] <= 1]

class MeepTaperBackend(SimulationBackend):
    """Serial, lossless 2D Ez taper with a straight-waveguide reference per point.

    Every solve records actual FDTD provenance. A numerical efficiency outside
    [0,1] is retained in raw artifacts but rejected as an optimization objective.
    """
    def __init__(self, config: TaperConfig | None = None, artifact_dir: Path | None = None,
                 save_fields: bool = True) -> None:
        self.config = config or TaperConfig()
        self.artifact_dir, self.save_fields = artifact_dir, save_fields
        self.last_record: dict[str, Any] | None = None
        self.records: list[dict[str, Any]] = []

    def solve(self, parameters: Mapping[str, float]) -> dict[str, Any]:
        length, width = validate_taper(parameters)
        mp = load_meep()
        if mp.count_processors() != 1:
            raise RuntimeError("This backend supports serial PyMeep only")
        if self.artifact_dir is not None and (self.artifact_dir / f"run-{len(self.records):04d}").exists():
            raise FileExistsError("Run artifacts already exist; select a fresh output directory")
        c = self.config
        sx = 2 * c.pml_x_um + 2 * c.straight_length_um + length
        sy = 2 * c.pml_y_um + 2 * c.air_padding_um + max(c.input_width_um, width)
        span = sy - 2 * c.pml_y_um
        left = -sx / 2 + c.pml_x_um
        source_x = left + .2 * c.straight_length_um
        input_x = left + .7 * c.straight_length_um
        output_x = length / 2 + .3 * c.straight_length_um
        fcen = 1 / c.wavelength_um
        parity = mp.ODD_Z + mp.EVEN_Y
        material = mp.Medium(epsilon=c.epsilon)

        def simulation(reference: bool) -> Any:
            w1 = c.input_width_um
            if reference:
                xy = [(-sx / 2 - 1, w1 / 2), (sx / 2 + 1, w1 / 2),
                      (sx / 2 + 1, -w1 / 2), (-sx / 2 - 1, -w1 / 2)]
            else:
                xy = [(-sx / 2 - 1, w1 / 2), (-length / 2, w1 / 2),
                      (length / 2, width / 2), (sx / 2 + 1, width / 2),
                      (sx / 2 + 1, -width / 2), (length / 2, -width / 2),
                      (-length / 2, -w1 / 2), (-sx / 2 - 1, -w1 / 2)]
            return mp.Simulation(
                dimensions=2, resolution=c.resolution, cell_size=mp.Vector3(sx, sy),
                geometry=[mp.Prism([mp.Vector3(x, y) for x, y in xy], height=mp.inf, material=material)],
                boundary_layers=[mp.PML(c.pml_x_um, direction=mp.X), mp.PML(c.pml_y_um, direction=mp.Y)],
                sources=[mp.EigenModeSource(mp.GaussianSource(fcen, fwidth=.2 * fcen),
                         center=mp.Vector3(source_x), size=mp.Vector3(y=span),
                         direction=mp.X, eig_band=1, eig_match_freq=True, eig_parity=parity)],
                symmetries=[mp.Mirror(mp.Y)])

        def monitor(sim: Any, x: float) -> Any:
            return sim.add_flux(fcen, 0, 1, mp.FluxRegion(center=mp.Vector3(x), size=mp.Vector3(y=span)))

        def finish(sim: Any) -> None:
            checks = [mp.stop_when_fields_decayed(c.decay_interval, mp.Ez, mp.Vector3(x), c.decay_threshold)
                      for x in (input_x, output_x)]
            def stop(current: Any) -> bool:
                if current.meep_time() >= c.max_time:
                    raise RuntimeError("FDTD decay did not converge before max_time; no efficiency accepted")
                flags = [check(current) for check in checks]
                return all(flags)
            sim.run(until_after_sources=stop)

        reference = simulation(True)
        try:
            input_monitor = monitor(reference, input_x)
            finish(reference)
            incident = complex(reference.get_eigenmode_coefficients(input_monitor, [1], eig_parity=parity).alpha[0, 0, 0])
            incident_flux = float(mp.get_fluxes(input_monitor)[0])
            incident_data = reference.get_flux_data(input_monitor)
            reference_time = float(reference.meep_time())
        finally:
            reference.reset_meep()

        # Reject invalid normalization before spending time on the taper run.
        normalized_powers(incident, 0, 0, incident_flux, 0, 0)
        sim = simulation(False)
        field_data: dict[str, np.ndarray] | None = None
        try:
            reflection_monitor = monitor(sim, input_x)
            sim.load_minus_flux_data(reflection_monitor, incident_data)
            transmission_monitor = monitor(sim, output_x)
            if self.save_fields:
                field_monitor = sim.add_dft_fields([mp.Ez], fcen, 0, 1,
                    center=mp.Vector3(), size=mp.Vector3(sx - 2 * c.pml_x_um, span))
            finish(sim)
            reflected = complex(sim.get_eigenmode_coefficients(reflection_monitor, [1], eig_parity=parity).alpha[0, 0, 1])
            transmitted = complex(sim.get_eigenmode_coefficients(transmission_monitor, [1], eig_parity=parity).alpha[0, 0, 0])
            powers = normalized_powers(incident, reflected, transmitted, incident_flux,
                                      float(mp.get_fluxes(reflection_monitor)[0]),
                                      float(mp.get_fluxes(transmission_monitor)[0]))
            simulation_time = float(sim.meep_time())
            if self.save_fields:
                x, y, _, _ = sim.get_array_metadata(dft_cell=field_monitor)
                field_data = {"ez_dft": np.asarray(sim.get_dft_array(field_monitor, mp.Ez, 0)),
                              "x_um": np.asarray(x), "y_um": np.asarray(y)}
        finally:
            sim.reset_meep()

        record = {"data_kind": "fdtd_meep_2d_unvalidated", "scientifically_validated": False,
                  "model_dimension": 2, "is_full_3d_device": False,
                  "solver": "Meep", "solver_version": str(mp.__version__), "tutorial": TUTORIAL,
                  "parameters": dict(parameters), "configuration": asdict(c),
                  "polarization": "Ez; ODD_Z + EVEN_Y", "mode_band": 1,
                  "reference_time": reference_time, "simulation_time": simulation_time,
                  "powers": powers, "coupling_efficiency": powers["fundamental_transmission"],
                  "optimization_acceptable": 0 <= powers["fundamental_transmission"] <= 1,
                  "numerical_warnings": numerical_warnings(powers)}
        if self.artifact_dir is not None:
            target = self.artifact_dir / f"run-{len(self.records):04d}"
            target.mkdir(parents=True, exist_ok=False)
            (target / "result.json").write_text(json.dumps(record, indent=2) + "\n")
            if field_data is not None:
                np.savez_compressed(target / "fields.npz", **field_data)
                plot_fields(field_data, record, target / "fields.png")
        self.last_record = record
        self.records.append(record)
        return record

    def run(self, parameters: Mapping[str, float]) -> SimulationResult:
        record = self.solve(parameters)
        if not record["optimization_acceptable"]:
            raise ValueError("Raw FDTD transmission is outside [0,1]; inspect artifacts and improve convergence, not clipping")
        return SimulationResult(dict(parameters), record["coupling_efficiency"], "meep_taper_2d",
                                record["data_kind"], f"Meep {record['solver_version']}; {TUTORIAL}")

def plot_fields(fields: dict[str, np.ndarray], record: dict[str, Any], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    x, y, ez = fields["x_um"], fields["y_um"], fields["ez_dft"]
    fig, axes = plt.subplots(2, 1, figsize=(10, 6), constrained_layout=True)
    for ax, values, label, cmap in zip(axes, (ez.real, np.abs(ez)**2),
                                      ("Re(Ez DFT)", "|Ez DFT|²"), ("RdBu_r", "inferno")):
        im = ax.pcolormesh(x, y, values.T, shading="auto", cmap=cmap)
        length, width = validate_taper(record["parameters"])
        w1 = record["configuration"]["input_width_um"]
        outline_x = [x.min(), -length / 2, length / 2, x.max()]
        for sign in (-1, 1):
            ax.plot(outline_x, np.array([w1, w1, width, width]) * sign / 2, "k-", linewidth=.7)
        ax.set(xlabel="x (µm)", ylabel="y (µm)", title=label + " — source-dependent arbitrary units")
        fig.colorbar(im, ax=ax)
    fig.suptitle("Actual Meep FDTD — 2D Ez taper, not a full 3D device")
    try:
        fig.savefig(path, dpi=150)
    finally:
        plt.close(fig)
