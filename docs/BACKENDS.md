# Backend design

Every backend implements `run(parameters: Mapping[str, float]) -> SimulationResult`. Optimizers can call a backend instance directly; the shared callable contract extracts the scalar coupling efficiency and verifies parameter identity. Backend results attach provenance, while optimization histories retain scores and points. Keep backend results separately when per-run solver provenance must be persisted; the optimizer does not currently archive backend metadata.

## Available implementations

- `SyntheticBackend`: the documented analytic toy objective, explicitly synthetic and unvalidated.
- `CSVReplayBackend`: exact lookup into an imported dataset. No interpolation, extrapolation, solver execution, or implied accuracy.
- `LumericalAdapter`: future design placeholder that always raises `NotImplementedError`.

To add a free simulation solver, subclass `SimulationBackend`, translate named parameters into the solver's units and input representation, and return a `SimulationResult` with a source identifier. Do not silently replace solver failures with zero efficiency. Test with an analytic reference case before making physical accuracy claims.

## Future Lumerical boundary (unimplemented and unvalidated)

`LumericalConfig` holds a project path, a mapping from optimization parameter names to project properties, and an efficiency result identifier. These are design inputs only. Constructing an adapter neither checks software availability nor executes anything.

A future implementation should accept an injectable session factory so ordinary tests can use a fake session without proprietary software. The implementation must open the project, validate parameter mappings and units, set requested values, execute the solver, extract and normalize one scalar coupling efficiency, and close the session even when execution fails. Add explicit timeouts, resource ownership, error types, and per-result project/solver/version provenance before enabling this backend.

Fake-session tests validate integration code only. Actual Lumerical validation would require an independently supplied installation/license and documented reference projects, solver settings, mesh convergence, and independent checks. None of that has occurred here. No Lumerical dependency, API key, license checkout, or paid API call is part of this package.

## Optional Meep backend

`MeepTaperBackend` implements the same contract with actual serial 2D FDTD simulations and separate detailed run artifacts. It loads PyMeep lazily and is installed only through the optional Conda environment. See [MEEP.md](MEEP.md) for normalization, output mode extraction, and model limitations.
