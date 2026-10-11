# Optional Meep 2D FDTD taper backend

This backend implements the waveguide-taper portion of the [official Meep mode-decomposition tutorial](https://meep.readthedocs.io/en/latest/Python_Tutorials/Mode_Decomposition/#reflectance-of-a-waveguide-taper) and extends it with an output monitor for fundamental-mode transmission. The implementation does not use Lumerical or any proprietary software.

## Install in an isolated Conda environment

Follow Meep's [supported Conda installation guidance](https://meep.readthedocs.io/en/latest/Installation/#conda-packages). Do not `pip install meep`: the similarly named PyPI package is not the FDTD solver.

```bash
conda env create -f environment-meep.yml
conda activate photonics-meep
python -m pip install --no-deps --no-build-isolation -e .
python -c 'import meep; print(meep.__version__)'
```

The environment uses only conda-forge and requests serial `pymeep` plus the project's free dependencies. Keeping numerical libraries in the same channel avoids mixing incompatible BLAS builds. Linux and macOS Conda builds are supported upstream; Windows users should use WSL. If Conda cannot resolve or install PyMeep, retain the ordinary Python installation: all synthetic, CSV, and optimization functions remain available. Calling the optional backend raises `MeepUnavailableError` with installation guidance and generates no substitute data.

## Reproduce the tutorial parameters

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m photonics_optimization.meep_sweep \
  --lengths 1 2 4 8 --widths 2 --resolution 25 --diagnostics-only --output artifacts/meep-tutorial
```

Use a fresh or empty output directory. The official script uses four lengths (1, 2, 4, 8 µm); the page's prose also mentions 16 µm, which is not in its displayed `range(4)` code. We follow the code. Default settings match the tutorial: input width 1 µm, output width 2 µm, straight sections 10 µm, wavelength 6.67 µm, constant relative permittivity 12, air padding 3 µm, x/y PML thicknesses 6/2 µm, and resolution 25 pixels/µm. This is a nondispersive, lossless dielectric model in air, not a calibrated silicon material model.

The source is a Gaussian-pulse eigenmode source launching band 1 in +x with Ez polarization and `ODD_Z + EVEN_Y` parity. Mirror symmetry in y is retained; line flux monitors plus eigenmode decomposition are used as the tutorial prescribes for symmetry.

Each point runs a straight-guide reference and then a taper in the same cell. The reference supplies the incident forward-mode coefficient, incident flux, and stored input-monitor Fourier fields. These are subtracted only at the taper's input reflection monitor. The output monitor in the uniform output section is not subtracted. It is placed 3 µm after the taper end at the default straight length. The monitor spans the non-PML y region to include evanescent tails.

```text
T_fundamental = |alpha_output[band 1, frequency 0, forward]|²
                / |alpha_reference[band 1, frequency 0, forward]|²
R_fundamental = |alpha_subtracted_input[band 1, frequency 0, backward]|²
                / |alpha_reference[band 1, frequency 0, forward]|²
R_flux = -subtracted_input_flux / reference_input_flux
T_flux = output_flux / reference_input_flux
```

Fundamental transmission is not total transmission: a wider output can carry other modes and radiation. Do not infer radiative loss from `1-R_fundamental-T_fundamental`; that also includes unmeasured modes and numerical discrepancies. Flux and mode powers are separate diagnostics and can disagree at finite resolution.

Runs wait for Ez decay at both input and output points. `TaperConfig` exposes decay interval, threshold, and a total simulation-time cap. Exceeding the cap raises an error with no accepted efficiency. This local decay test is not a proof that every possible trapped mode has decayed. Before scientific use, vary resolution, PML thickness, air padding, monitor positions, simulation time/decay settings, and mode resolution. Check mode identification for changed widths/frequencies.

## Fields and provenance

Each completed simulation saves `run-NNNN/result.json`, `fields.npz`, and `fields.png`. DFT arrays contain complex Ez at the source's center frequency and x/y sample coordinates, excluding PML. Plots show real Ez and |Ez|² in source-dependent arbitrary units. |Ez|² is not itself a calibrated power-flux intensity. The plot also shows the waveguide outline. `--no-fields` disables field capture and plotting.

All solver artifacts are tagged `fdtd_meep_2d_unvalidated`, with dimension, solver version, configuration, normalized powers, and explicit `scientifically_validated: false` / `is_full_3d_device: false` flags. Raw numerical ratios are not clipped. `numerical_warnings` identifies out-of-range reflection/total-flux ratios as well. `optimization_acceptable` checks only the fundamental-transmission scalar's range, not physical correctness or convergence; other flux diagnostics can still show numerical problems. Review all powers and warnings before drawing physical conclusions. If transmission lies outside [0,1], the raw per-run artifacts are retained for inspection, but the optimizer rejects the score. Investigate discretization/normalization/convergence instead of silently forcing efficiency into range.

These are actual numerical 2D FDTD outputs when Meep runs. They are not synthetic toy scores, experimental measurements, validated fabrication predictions, or a full 3D silicon photonics device. The model has no vertical confinement, finite silicon thickness, substrate, or out-of-plane loss. No 3D or Lumerical equivalence is claimed.

## Sweeps and optimizer integration

```bash
python -m photonics_optimization.meep_sweep \
  --lengths 1 4 --widths 2 2.5 --output artifacts/meep-width-length
photonics-analyze artifacts/meep-width-length/sweep.csv \
  --parameters taper_length_um output_width_um --data-kind fdtd_meep_2d_unvalidated
```

`TaperSweep` implements the existing `Optimizer` contract for explicit Cartesian value lists. It writes `sweep.csv`, `sweep.json` (full backend records plus optimization history), and `sweep.png` (transmission and reflection diagnostics). By default, optimization-mode sweeps reject efficiencies outside [0,1]. Failures propagate; partial per-run results remain, but a failed optimization sweep does not publish a completed aggregate. `--diagnostics-only` completes a raw-data sweep without accepting any optimizer scores, retaining numerical ratios above 1 plus explicit rejection flags. Use this for tutorial reproduction and convergence diagnosis. Diagnostic CSVs with out-of-range raw ratios deliberately fail the strict efficiency CSV importer; inspect their JSON records or improve convergence before using them as optimization data. The bundled length-8 tutorial run slightly exceeds unity, so it is retained as a diagnostic, never an accepted optimization score. The two explicit parameter lists may include singleton values.

```python
from pathlib import Path
from photonics_optimization import BayesianOptimization, Parameter
from photonics_optimization.meep_backend import MeepTaperBackend, TaperConfig

backend = MeepTaperBackend(TaperConfig(), Path("artifacts/meep-optimization"))
space = [Parameter("taper_length_um", 1, 8), Parameter("output_width_um", 1.5, 2.5)]
result = BayesianOptimization(space, budget=8, initial_points=3, seed=42).optimize(backend)
print(result.best.parameters, result.best.score)
```

Grid and Random Search accept the same backend. Every candidate performs two real simulations, so keep budgets small. Runs are serial and support the serial PyMeep build only. There is no cross-run normalization cache: cell dimensions change with both swept parameters. Generic optimization histories store scalar scores; the backend separately preserves detailed provenance in its artifacts and `records`.

## Testing and CI

Ordinary CI runs configuration/normalization/optional-dependency/provenance/sweep tests without Meep. Three real integration tests are explicitly enabled only inside the Conda environment:

```bash
RUN_MEEP_TESTS=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m pytest
```

They exercise straight-guide normalization, taper transmission/fields/CSV export, and the timeout path. A coarse resolution-10 straight-guide check uses a stated ±0.03 transmission tolerance; it is a smoke/regression check, not a scientific convergence criterion. The manually dispatched `Optional Meep FDTD` Actions workflow installs the Conda environment, runs solver tests, and generates tutorial artifacts. Meep is not installed by ordinary push/PR CI and is not a mandatory package dependency.

See [the bundled run notes](../examples/meep/README.md) for measured execution details and the comparison to the original tutorial script. A comparison with the same tutorial implementation verifies reproduction, not independent physical accuracy.
