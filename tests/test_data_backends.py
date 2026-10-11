from pathlib import Path
import math
import pytest
from photonics_optimization import (load_simulation_csv, CSVReplayBackend, SyntheticBackend,
    SimulationBackend, SimulationResult, GridSearch, default_parameters, LumericalAdapter, LumericalConfig)

@pytest.mark.parametrize("content", [
    "x,coupling_efficiency\n", "x,efficiency\n0,.5\n",
    "x,x,coupling_efficiency\n0,0,.5\n", "x,coupling_efficiency\nno,.5\n",
    "x,coupling_efficiency\n0,nan\n", "x,coupling_efficiency\ninf,.5\n",
    "x,coupling_efficiency\n0,1.1\n", "x,coupling_efficiency\n0,-.1\n",
    "x,coupling_efficiency\n0,\n", "x,coupling_efficiency\n0\n",
    "x,coupling_efficiency\n0,.5,extra\n", "x,coupling_efficiency\n0,.5\n0,.6\n"])
def test_invalid_csv_rejected(tmp_path, content):
    path = tmp_path / "data.csv"
    path.write_text(content)
    with pytest.raises(ValueError):
        load_simulation_csv(path, ["x"])

def test_csv_summary_custom_column_metadata_and_bom(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("\ufeffx,eta,note\n0,.2,first\n1,.8,second\n")
    data = load_simulation_csv(path, ["x"], "eta")
    summary = data.summary()
    assert summary["count"] == 2
    assert summary["efficiency_mean"] == pytest.approx(.5)
    assert summary["efficiency_std_population"] == pytest.approx(.3)
    assert summary["best_parameters"] == {"x": 1}
    assert summary["parameter_ranges"] == {"x": [0, 1]}
    assert summary["scientifically_validated"] is False
    assert data.data_kind == "external_unvalidated"

@pytest.mark.parametrize("names", [[], ["x", "x"], [""]])
def test_invalid_parameter_columns(tmp_path, names):
    with pytest.raises(ValueError):
        load_simulation_csv(tmp_path / "unused.csv", names)

def test_example_csv_matches_synthetic_and_grid_replay():
    path = Path(__file__).parents[1] / "examples/datasets/synthetic_coupling.csv"
    data = load_simulation_csv(path, ["offset_um", "angle_deg"], data_kind="synthetic_analytic_toy")
    replay = CSVReplayBackend(data)
    synthetic = SyntheticBackend()
    for row in data.records:
        assert replay(row.parameters) == pytest.approx(synthetic(row.parameters))
        assert replay.run(row.parameters).scientifically_validated is False
    result = GridSearch(default_parameters(), 3).optimize(replay)
    assert result.best.score == 1
    with pytest.raises(ValueError, match="exact"):
        replay({"offset_um": .1, "angle_deg": 0})
    with pytest.raises(ValueError, match="schema"):
        replay({"offset_um": 0})

def test_custom_free_backend_integrates_with_optimizer():
    class CustomBackend(SimulationBackend):
        def run(self, parameters):
            return SimulationResult(dict(parameters), .25, "custom", "synthetic", "test fixture")
    assert GridSearch(default_parameters(), 2).optimize(CustomBackend()).best.score == .25

def test_backend_rejects_mismatched_result_parameters():
    class InvalidBackend(SimulationBackend):
        def run(self, parameters):
            return SimulationResult({"x": 1}, .25, "custom", "synthetic", "test fixture")
    with pytest.raises(ValueError, match="match"):
        InvalidBackend()({"x": 0})

@pytest.mark.parametrize("efficiency", [-1, 2, math.nan, math.inf])
def test_invalid_backend_efficiency(efficiency):
    with pytest.raises(ValueError):
        SimulationResult({"x": 0}, efficiency, "test", "synthetic", "fixture")

def test_lumerical_is_explicitly_unimplemented(tmp_path):
    adapter = LumericalAdapter(LumericalConfig(tmp_path / "missing.fsp", {"x": "geometry::x"}, "coupling::eta"))
    with pytest.raises(NotImplementedError, match="unvalidated"):
        adapter({"x": 0})
    with pytest.raises(ValueError):
        LumericalAdapter(LumericalConfig(tmp_path / "missing.fsp", {}, ""))


def test_custom_schema_example():
    path = Path(__file__).parents[1] / "examples/datasets/synthetic_width.csv"
    data = load_simulation_csv(path, ["width_nm"], "eta", "synthetic_analytic_toy")
    assert data.summary()["best_parameters"] == {"width_nm": 500}
    assert data.summary()["efficiency_max"] == 1

def test_programmatic_dataset_rejects_empty_duplicate_and_mismatched_records():
    from photonics_optimization.data import SimulationDataset, SimulationRecord
    row = SimulationRecord({"x": 0}, .5)
    for names, records in [(('x',), ()), (('x',), (row, row)), (('y',), (row,))]:
        with pytest.raises(ValueError):
            SimulationDataset(names, records, "fixture")
    with pytest.raises(ValueError):
        SimulationRecord({"x": math.nan}, .5)

def test_analysis_cli(capsys, monkeypatch):
    from photonics_optimization.data import main
    import json
    path = Path(__file__).parents[1] / "examples/datasets/synthetic_width.csv"
    monkeypatch.setattr("sys.argv", ["photonics-analyze", str(path), "--parameters", "width_nm",
                                    "--efficiency-column", "eta", "--data-kind", "synthetic_analytic_toy"])
    main()
    assert json.loads(capsys.readouterr().out)["count"] == 5
