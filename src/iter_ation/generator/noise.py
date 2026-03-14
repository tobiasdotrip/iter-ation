import numpy as np
from iter_ation.physics.parameters import PARAMETERS, get_parameter

GENERATED_PARAMS = [
    p for p in PARAMETERS
    if p.noise_sigma_pct is not None or p.noise_sigma_abs is not None
]

_DRIFT_RATE = 0.002


def apply_noise(
    values: dict[str, float],
    rng: np.random.Generator,
) -> dict[str, float]:
    """Apply Gaussian noise to parameter values."""
    noisy = {}
    for name, value in values.items():
        param = get_parameter(name)
        sigma = param.effective_sigma
        if sigma > 0:
            noisy[name] = value + rng.normal(0, sigma)
        else:
            noisy[name] = value
    return noisy


def apply_drift(
    drift_state: dict[str, float],
    rng: np.random.Generator,
    dt: float,
) -> dict[str, float]:
    """Update drift offsets via random walk."""
    new_drift = {}
    for name, current in drift_state.items():
        param = get_parameter(name)
        sigma = param.effective_sigma
        if sigma > 0:
            step = rng.normal(0, _DRIFT_RATE * max(abs(param.nominal), sigma) * np.sqrt(dt))
            new_drift[name] = current + step
        else:
            new_drift[name] = current
    return new_drift
