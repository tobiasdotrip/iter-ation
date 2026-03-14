from iter_ation.physics.parameters import PARAMETERS, get_parameter


def test_parameters_count():
    assert len(PARAMETERS) == 13


def test_greenwald_fraction_exists():
    p = get_parameter("greenwald_fraction")
    assert p.nominal == 0.75
    assert p.unit == ""
    assert p.risk_threshold is not None


def test_n_e_nominal():
    p = get_parameter("n_e")
    assert p.nominal == 0.9
    assert p.unit == "1e20 m\u207b\u00b3"
    assert p.noise_sigma_pct == 0.5


def test_all_parameters_have_nominal():
    for p in PARAMETERS:
        assert p.nominal is not None, f"{p.name} has no nominal value"


def test_derived_parameters_have_no_sigma():
    derived = {"greenwald_fraction", "q95"}
    for p in PARAMETERS:
        if p.name in derived:
            assert p.noise_sigma_pct is None, f"{p.name} is derived but has sigma"


def test_beta_n_has_sigma():
    p = get_parameter("beta_n")
    assert p.noise_sigma_pct is not None


def test_zcur_has_absolute_sigma():
    p = get_parameter("zcur")
    assert p.noise_sigma_abs is not None
    assert p.noise_sigma_abs > 0
