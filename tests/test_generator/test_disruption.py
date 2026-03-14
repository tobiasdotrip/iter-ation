from iter_ation.generator.disruption import (
    compute_risk_score,
    DisruptionPhase,
    DisruptionCascade,
)


def test_risk_score_nominal_is_zero():
    score = compute_risk_score(
        greenwald_fraction=0.75, radiated_fraction=0.5,
        n1_amplitude=0.05, q95=3.1,
    )
    assert score == 0.0


def test_risk_score_increases_with_fgw():
    low = compute_risk_score(greenwald_fraction=0.80, radiated_fraction=0.5,
                              n1_amplitude=0.05, q95=3.1)
    high = compute_risk_score(greenwald_fraction=0.95, radiated_fraction=0.5,
                               n1_amplitude=0.05, q95=3.1)
    assert high > low


def test_risk_score_above_greenwald_limit():
    """fGW > 1.0 saturates the Greenwald contribution at 0.7."""
    score = compute_risk_score(greenwald_fraction=1.1, radiated_fraction=0.5,
                                n1_amplitude=0.05, q95=3.1)
    assert score >= 0.7

    # With all parameters critical, score should be near 1.0
    score_all = compute_risk_score(greenwald_fraction=1.1, radiated_fraction=0.95,
                                    n1_amplitude=1.5, q95=1.8)
    assert score_all >= 0.95


def test_cascade_starts_with_precursors():
    cascade = DisruptionCascade()
    assert cascade.phase == DisruptionPhase.NONE
    cascade.trigger()
    assert cascade.phase == DisruptionPhase.PRECURSORS


def test_cascade_advances_through_phases():
    cascade = DisruptionCascade()
    cascade.trigger()
    for _ in range(500):
        cascade.tick(dt=0.001)
    assert cascade.phase in (DisruptionPhase.THERMAL_QUENCH,
                              DisruptionPhase.CURRENT_QUENCH,
                              DisruptionPhase.RECOVERY)


def test_cascade_modifies_values():
    cascade = DisruptionCascade()
    cascade.trigger()
    for _ in range(200):
        cascade.tick(dt=0.001)
    mods = cascade.get_modifications()
    assert "n1_amplitude" in mods


def test_cascade_completes_to_none():
    cascade = DisruptionCascade()
    cascade.trigger()
    for _ in range(2000):
        cascade.tick(dt=0.001)
    assert cascade.phase == DisruptionPhase.NONE


def test_cascade_recovery_ends():
    cascade = DisruptionCascade()
    cascade.trigger()
    was_recovering = False
    recovery_ended = False
    for _ in range(2000):
        prev = cascade.phase
        cascade.tick(dt=0.001)
        if prev == DisruptionPhase.RECOVERY:
            was_recovering = True
        if was_recovering and cascade.phase == DisruptionPhase.NONE:
            recovery_ended = True
            break
    assert recovery_ended
