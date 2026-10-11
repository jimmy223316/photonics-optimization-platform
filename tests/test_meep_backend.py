"""Contract tests use no solver; real FDTD tests are explicitly opt-in below."""
import importlib
import math
import os
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from photonics_optimization.meep_backend import (
    MeepTaperBackend, MeepUnavailableError, TaperConfig, load_meep, normalized_powers, validate_taper)
from photonics_optimization.meep_sweep import TaperSweep, run_sweep
from photonics_optimization import load_simulation_csv

@pytest.mark.parametrize("kwargs", [{"resolution": 0}, {"resolution": 4.5}, {"resolution": True},
    {"pml_x_um": 0}, {"air_padding_um": -1}, {"wavelength_um": math.nan},
    {"epsilon": 1}, {"decay_threshold": 1}, {"max_time": 10}])
def test_configuration_validation(kwargs):
    with pytest.raises(ValueError):
        TaperConfig(**kwargs)

@pytest.mark.parametrize("point", [{}, {"length": 1, "width": 2},
    {"taper_length_um": 0, "output_width_um": 2},
    {"taper_length_um": 1, "output_width_um": math.inf}])
def test_taper_parameter_validation(point):
    with pytest.raises(ValueError):
        validate_taper(point)

def test_normalization_uses_forward_incident_mode_and_signed_flux():
    powers = normalized_powers(2j, .2, 1.8j, 8, -.08, 6.48)
    assert powers["fundamental_transmission"] == pytest.approx(.81)
    assert powers["fundamental_reflection"] == pytest.approx(.01)
    assert powers["reflected_flux_fraction"] == pytest.approx(.01)
    assert powers["output_flux_fraction"] == pytest.approx(.81)
    assert normalized_powers(1, 0, 1.01, 1, 0, 1)["fundamental_transmission"] > 1

@pytest.mark.parametrize("mode,flux", [(0, 1), (1, 0), (1, -1), (math.nan, 1)])
def test_invalid_incident_normalization(mode, flux):
    with pytest.raises(ValueError):
        normalized_powers(mode, 0, 1, flux, 0, 1)

def test_missing_optional_solver_fails_without_artifacts(tmp_path, monkeypatch):
    def absent(name):
        raise ImportError("PyMeep absent in unit test")
    monkeypatch.setattr(importlib, "import_module", absent)
    with pytest.raises(MeepUnavailableError, match="Conda"):
        run_sweep([1], [2], tmp_path / "missing")
    assert not (tmp_path / "missing").exists()

def test_unrelated_pypi_meep_rejected(monkeypatch):
    monkeypatch.setattr(importlib, "import_module", lambda name: SimpleNamespace())
    with pytest.raises(MeepUnavailableError, match="not PyMeep"):
        load_meep()

@pytest.mark.parametrize("lengths,widths", [([], [2]), ([1, 1], [2]), ([1], [0]), ([math.nan], [2])])
def test_invalid_sweeps(lengths, widths):
    with pytest.raises(ValueError):
        TaperSweep(lengths, widths)

def test_sweep_candidates_and_framework_history():
    result = TaperSweep([1, 4], [1.5, 2.5]).optimize(lambda p: p["taper_length_um"] / 10)
    assert len(result.history) == 4
    assert result.best.score == .4
    assert result.history[0].parameters == {"taper_length_um": 1, "output_width_um": 1.5}

def test_out_of_range_fdtd_objective_rejected_without_clipping(monkeypatch):
    backend = MeepTaperBackend(save_fields=False)
    fixture = {"optimization_acceptable": False, "coupling_efficiency": 1.001}
    monkeypatch.setattr(backend, "solve", lambda p: fixture)
    with pytest.raises(ValueError, match="not clipping"):
        backend.run({"taper_length_um": 1, "output_width_um": 2})

def test_existing_sweep_artifacts_preserved(tmp_path):
    marker = tmp_path / "existing.json"
    marker.write_text("preserve")
    with pytest.raises(FileExistsError):
        run_sweep([1], [2], tmp_path)
    assert marker.read_text() == "preserve"

def test_fdtd_csv_classification(tmp_path):
    path = tmp_path / "record.csv"
    path.write_text("taper_length_um,output_width_um,coupling_efficiency\n1,2,.8\n")
    data = load_simulation_csv(path, ["taper_length_um", "output_width_um"], data_kind="fdtd_meep_2d_unvalidated")
    assert data.summary()["data_kind"] == "fdtd_meep_2d_unvalidated"
    assert data.summary()["scientifically_validated"] is False

@pytest.mark.skipif(os.environ.get("RUN_MEEP_TESTS") != "1", reason="opt-in actual PyMeep integration test")
def test_actual_straight_guide_normalization():
    record = MeepTaperBackend(TaperConfig(resolution=10), save_fields=False).solve(
        {"taper_length_um": 1., "output_width_um": 1.})
    assert record["data_kind"] == "fdtd_meep_2d_unvalidated"
    assert record["powers"]["fundamental_transmission"] == pytest.approx(1, abs=.03)
    assert record["powers"]["fundamental_reflection"] < .01

@pytest.mark.skipif(os.environ.get("RUN_MEEP_TESTS") != "1", reason="opt-in actual PyMeep integration test")
def test_actual_taper_fields_and_csv(tmp_path):
    result = run_sweep([1.], [2.], tmp_path / "fdtd", TaperConfig(resolution=10))
    assert 0 < result.best.score <= 1
    assert (tmp_path / "fdtd/run-0000/fields.png").read_bytes().startswith(b"\x89PNG")
    with np.load(tmp_path / "fdtd/run-0000/fields.npz") as fields:
        assert fields["ez_dft"].shape == (len(fields["x_um"]), len(fields["y_um"]))
        assert np.isfinite(fields["ez_dft"]).all()
    data = load_simulation_csv(tmp_path / "fdtd/sweep.csv", ["taper_length_um", "output_width_um"],
                               data_kind="fdtd_meep_2d_unvalidated")
    assert data.records[0].coupling_efficiency == result.best.score

@pytest.mark.skipif(os.environ.get("RUN_MEEP_TESTS") != "1", reason="opt-in actual PyMeep integration test")
def test_actual_timeout_produces_no_results(tmp_path):
    backend = MeepTaperBackend(TaperConfig(resolution=10, max_time=100), tmp_path / "timeout", False)
    with pytest.raises(RuntimeError, match="did not converge"):
        backend.solve({"taper_length_um": 1., "output_width_um": 2.})
    assert backend.records == []
    assert not (tmp_path / "timeout").exists()


def test_diagnostic_sweep_retains_unphysical_raw_ratio_without_accepting_score(tmp_path, monkeypatch):
    import photonics_optimization.meep_sweep as module
    monkeypatch.setattr(module, "load_meep", lambda: None)
    # Explicit unit-test double, never evidence of a real FDTD calculation.
    class TestDouble:
        def __init__(self, *args):
            self.records = []
        def solve(self, point):
            self.records.append({"parameters": dict(point), "coupling_efficiency": 1.001,
                                 "data_kind": "unit_test_double", "optimization_acceptable": False})
    monkeypatch.setattr(module, "MeepTaperBackend", TestDouble)
    monkeypatch.setattr(module, "plot_sweep", lambda records, path: None)
    captured = {}
    def capture(records, output, result):
        captured.update(records=records, result=result)
    monkeypatch.setattr(module, "export_sweep", capture)
    assert module.run_sweep([1], [2], tmp_path / "unit-test", diagnostics_only=True) is None
    assert captured["result"] is None
    assert captured["records"][0]["coupling_efficiency"] == 1.001
    assert captured["records"][0]["optimization_acceptable"] is False
    assert not (tmp_path / "unit-test").exists()

def test_export_rejects_synthetic_records(tmp_path):
    from photonics_optimization.meep_sweep import export_sweep
    with pytest.raises(ValueError, match="actual Meep"):
        export_sweep([{"data_kind": "synthetic_analytic_toy", "solver": "toy"}], tmp_path)


def test_numerical_diagnostics_are_flagged_not_clipped():
    from photonics_optimization.meep_backend import numerical_warnings
    values = {"fundamental_transmission": .99, "fundamental_reflection": .001,
              "reflected_flux_fraction": -.0065, "output_flux_fraction": 1.0002}
    warnings = numerical_warnings(values)
    assert warnings == ["reflected_flux_fraction lies outside [0,1]", "output_flux_fraction lies outside [0,1]"]
    assert values["reflected_flux_fraction"] == -.0065
