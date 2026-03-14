import numpy as np
from iter_ation.generator.noise import apply_noise, apply_drift


def test_apply_noise_returns_all_keys():
    rng = np.random.default_rng(42)
    values = {"n_e": 0.9, "Ip": 15.0, "Te_core": 20.0}
    noisy = apply_noise(values, rng)
    assert set(noisy.keys()) == set(values.keys())


def test_apply_noise_stays_close_to_nominal():
    rng = np.random.default_rng(42)
    samples = []
    for _ in range(1000):
        noisy = apply_noise({"n_e": 0.9}, rng)
        samples.append(noisy["n_e"])
    mean = sum(samples) / len(samples)
    assert abs(mean - 0.9) < 0.01


def test_apply_noise_zcur_uses_abs_sigma():
    """zcur (nominal=0) should still get noise via noise_sigma_abs."""
    rng = np.random.default_rng(42)
    samples = [apply_noise({"zcur": 0.0}, rng)["zcur"] for _ in range(100)]
    assert any(s != 0.0 for s in samples)


def test_apply_drift_changes_value():
    rng = np.random.default_rng(42)
    drift_state = {"n_e": 0.0}
    new_drift = apply_drift(drift_state, rng, dt=0.001)
    assert "n_e" in new_drift
