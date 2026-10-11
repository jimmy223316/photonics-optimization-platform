"""Toy analytic response, not a validated optical or electromagnetic simulation."""
from collections.abc import Mapping
import math
from .core import Parameter

def default_parameters() -> tuple[Parameter, ...]:
    return (Parameter("offset_um", -2.0, 2.0), Parameter("angle_deg", -10.0, 10.0))

def synthetic_coupling(parameters: Mapping[str, float]) -> float:
    """Gaussian toy efficiency: exp(-0.5*((offset/0.8)^2+(angle/4)^2)).

    Labels use illustrative units only. Peak is exactly 1 at zero offset/angle.
    No device geometry, wavelength, solver, measurement, or calibration is involved.
    """
    offset, angle = parameters["offset_um"], parameters["angle_deg"]
    if not math.isfinite(offset) or not math.isfinite(angle):
        raise ValueError("Objective parameters must be finite")
    return math.exp(-0.5 * ((offset / 0.8) ** 2 + (angle / 4.0) ** 2))
