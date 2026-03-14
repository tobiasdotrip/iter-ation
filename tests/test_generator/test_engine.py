import math
from iter_ation.generator.engine import SimulationEngine


def test_engine_starts_at_nominal():
    engine = SimulationEngine(seed=42)
    state = engine.current_state
    assert abs(state.greenwald_fraction - 0.75) < 0.05
    assert state.sim_time == 0.0


def test_engine_tick_advances_time():
    engine = SimulationEngine(seed=42)
    engine.tick()
    assert engine.current_state.sim_time == 0.001


def test_engine_100_ticks_stays_reasonable():
    engine = SimulationEngine(seed=42)
    for _ in range(100):
        engine.tick()
    state = engine.current_state
    assert 0.5 < state.greenwald_fraction < 1.0
    assert 10 < state.Ip < 20
    assert abs(state.sim_time - 0.1) < 1e-9


def test_engine_greenwald_fraction_is_derived():
    engine = SimulationEngine(seed=42)
    for _ in range(10):
        engine.tick()
    state = engine.current_state
    n_g = state.Ip / (math.pi * 4.0)
    expected_fgw = state.n_e / n_g
    assert abs(state.greenwald_fraction - expected_fgw) < 1e-6


def test_engine_q95_is_derived():
    engine = SimulationEngine(seed=42)
    for _ in range(10):
        engine.tick()
    state = engine.current_state
    expected_q = 3.1 * (15.0 / state.Ip) * (0.85 / state.li)
    assert abs(state.q95 - expected_q) < 1e-6


def test_engine_beta_n_varies():
    engine = SimulationEngine(seed=42)
    for _ in range(100):
        engine.tick()
    assert engine.current_state.beta_n != 1.8


def test_engine_new_pulse_flag():
    engine = SimulationEngine(seed=42)
    engine.cascade.trigger()
    new_pulse = False
    for _ in range(2000):
        engine.tick()
        if engine.new_pulse_triggered:
            new_pulse = True
            break
    assert new_pulse
