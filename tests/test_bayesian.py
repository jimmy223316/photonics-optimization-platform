import math
import numpy as np
import pytest
from photonics_optimization import BayesianOptimization, Parameter, SyntheticBackend, default_parameters
from photonics_optimization.bayesian import expected_improvement

@pytest.mark.parametrize("kwargs", [{"budget": 0}, {"budget": True}, {"initial_points": 0},
    {"initial_points": 6, "budget": 5}, {"candidate_pool": 0}, {"seed": -1},
    {"xi": -1}, {"xi": math.nan}])
def test_invalid_configuration(kwargs):
    with pytest.raises(ValueError):
        BayesianOptimization(default_parameters(), **kwargs)

def test_expected_improvement_analytic_values():
    ei = expected_improvement(np.array([1., 1., 0.]), np.array([0., 1., 1.]), 1., 0.)
    assert ei[0] == 0
    assert expected_improvement(np.array([2.]), np.array([0.]), 1., 0.)[0] == 1
    assert ei[1] == pytest.approx(1 / math.sqrt(2 * math.pi))
    assert 0 < ei[2] < ei[1]

def test_reproducibility_bounds_history_and_no_repeats():
    space = default_parameters()
    optimizer = BayesianOptimization(space, budget=12, candidate_pool=64, seed=17)
    result = optimizer.optimize(SyntheticBackend())
    assert result == optimizer.optimize(SyntheticBackend())
    assert len(result.history) == 12
    assert len({tuple(e.parameters.values()) for e in result.history}) == 12
    for evaluation in result.history:
        assert all(p.lower <= evaluation.parameters[p.name] <= p.upper for p in space)
    assert np.allclose([e.best_so_far for e in result.history],
                       np.maximum.accumulate([e.score for e in result.history]))

def test_adaptive_proposals_depend_on_observed_scores():
    optimizer = BayesianOptimization([Parameter("x", 0, 1)], budget=8,
                                    initial_points=3, candidate_pool=128, seed=7)
    positive = optimizer.optimize(lambda p: p["x"])
    negative = optimizer.optimize(lambda p: -p["x"])
    assert positive.history[:3][0].parameters == negative.history[:3][0].parameters
    assert [e.parameters for e in positive.history[3:]] != [e.parameters for e in negative.history[3:]]

def test_improves_simple_off_center_objective():
    result = BayesianOptimization([Parameter("x", 0, 1)], budget=15, initial_points=3,
                                  candidate_pool=128, seed=7).optimize(lambda p: -(p["x"] - .73)**2)
    assert result.best.score > max(e.score for e in result.history[:3])
    assert abs(result.best.parameters["x"] - .73) < .08

@pytest.mark.parametrize("score", [math.nan, math.inf])
def test_nonfinite_scores_rejected(score):
    with pytest.raises(ValueError, match="non-finite"):
        BayesianOptimization(default_parameters(), budget=5).optimize(lambda _: score)

def test_constant_objective_and_small_budget():
    result = BayesianOptimization([Parameter("x", 0, 1)], budget=6, initial_points=2,
                                  candidate_pool=16).optimize(lambda _: -.5)
    assert len(result.history) == 6
    assert all(e.score == -.5 for e in result.history)
