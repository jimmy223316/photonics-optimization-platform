import math
import numpy as np
import pytest
from photonics_optimization import Parameter, GridSearch, RandomSearch, synthetic_coupling, default_parameters
from photonics_optimization.demo import run_demo
import json

@pytest.mark.parametrize("bounds", [(0, 0), (2, 1), (float("nan"), 1), (0, float("inf"))])
def test_invalid_bounds(bounds):
    with pytest.raises(ValueError):
        Parameter("x", *bounds)

@pytest.mark.parametrize("space", [[], [Parameter("x", 0, 1), Parameter("x", 2, 3)]])
def test_invalid_space(space):
    with pytest.raises(ValueError):
        GridSearch(space)

@pytest.mark.parametrize("value", [0, -1, 1.5, True])
def test_invalid_budget(value):
    with pytest.raises(ValueError):
        RandomSearch(default_parameters(), value)
    with pytest.raises(ValueError):
        GridSearch(default_parameters(), value)

def test_grid_visits_cartesian_endpoints_and_known_peak():
    result = GridSearch(default_parameters(), 3).optimize(synthetic_coupling)
    assert len(result.history) == 9
    assert len({tuple(e.parameters.values()) for e in result.history}) == 9
    assert result.history[0].parameters == {"offset_um": -2, "angle_deg": -10}
    assert result.history[-1].parameters == {"offset_um": 2, "angle_deg": 10}
    assert result.best.parameters == {"offset_um": 0, "angle_deg": 0}
    assert result.best.score == 1

def test_random_reproducibility_bounds_and_seed_difference():
    space = default_parameters()
    optimizer = RandomSearch(space, 50, 7)
    first = optimizer.optimize(synthetic_coupling)
    assert first == optimizer.optimize(synthetic_coupling)
    assert first != RandomSearch(space, 50, 8).optimize(synthetic_coupling)
    assert len(first.history) == 50
    for evaluation in first.history:
        for parameter in space:
            assert parameter.lower <= evaluation.parameters[parameter.name] <= parameter.upper

@pytest.mark.parametrize("optimizer", [GridSearch, RandomSearch])
def test_running_best_matches_actual_scores(optimizer):
    result = optimizer(default_parameters()).optimize(synthetic_coupling)
    scores = [e.score for e in result.history]
    assert np.allclose([e.best_so_far for e in result.history], np.maximum.accumulate(scores))
    assert result.best.score == max(scores)

@pytest.mark.parametrize("score", [math.nan, math.inf, -math.inf])
def test_nonfinite_objective_rejected(score):
    with pytest.raises(ValueError, match="non-finite"):
        RandomSearch(default_parameters(), 1).optimize(lambda _: score)

def test_arbitrary_objective_and_mutation_isolation():
    def objective(point):
        value = point["x"]
        point.clear()
        return -value
    result = GridSearch([Parameter("x", 1, 3)], 3).optimize(objective)
    assert result.best.score == -1
    assert result.best.parameters == {"x": 1}

def test_synthetic_objective_symmetry_and_peak():
    assert synthetic_coupling({"offset_um": 0, "angle_deg": 0}) == 1
    positive = synthetic_coupling({"offset_um": 1, "angle_deg": 3})
    assert 0 < positive < 1
    assert positive == synthetic_coupling({"offset_um": -1, "angle_deg": -3})
    with pytest.raises(ValueError):
        synthetic_coupling({"offset_um": math.nan, "angle_deg": 0})

def test_demo_generates_real_artifacts_with_provenance(tmp_path):
    run_demo(tmp_path)
    assert (tmp_path / "convergence.png").read_bytes().startswith(b"\x89PNG")
    payload = json.loads((tmp_path / "results.json").read_text())
    assert payload["scientifically_validated"] is False
    assert payload["data_kind"] == "synthetic_analytic_toy"
    for result in payload["results"]:
        assert len(result["history"]) == 121
        for item in result["history"]:
            assert item["score"] == synthetic_coupling(item["parameters"])
