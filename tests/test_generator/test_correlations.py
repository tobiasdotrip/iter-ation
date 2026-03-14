from iter_ation.generator.correlations import apply_correlations
from iter_ation.physics.parameters import PARAMETERS


def _make_nominal() -> dict[str, float]:
    return {
        p.name: p.nominal
        for p in PARAMETERS
        if p.noise_sigma_pct is not None or p.noise_sigma_abs is not None
    }


def test_nominal_values_unchanged():
    nominal = _make_nominal()
    result = apply_correlations(dict(nominal))
    for name, val in result.items():
        assert abs(val - nominal[name]) < 1e-9, f"{name} changed at nominal"


def test_n_e_increase_raises_radiated_fraction():
    values = _make_nominal()
    values["n_e"] = 1.2  # well above nominal 0.9
    result = apply_correlations(values)
    assert result["radiated_fraction"] > _make_nominal()["radiated_fraction"]


def test_n_e_increase_lowers_te_core():
    values = _make_nominal()
    values["n_e"] = 1.2
    result = apply_correlations(values)
    assert result["Te_core"] < _make_nominal()["Te_core"]
