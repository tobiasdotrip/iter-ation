from iter_ation.generator.plasma_state import PlasmaState


def test_nominal_state_creates():
    state = PlasmaState.nominal()
    assert state.greenwald_fraction == 0.75
    assert state.n_e == 0.9
    assert state.Ip == 15.0
    assert state.sim_time == 0.0


def test_plasma_state_is_frozen():
    state = PlasmaState.nominal()
    try:
        state.n_e = 1.0
        assert False, "Should not allow mutation"
    except AttributeError:
        pass


def test_plasma_state_values_dict():
    state = PlasmaState.nominal()
    values = state.values()
    assert isinstance(values, dict)
    assert len(values) == 13
    assert "greenwald_fraction" in values
    assert "sim_time" not in values
