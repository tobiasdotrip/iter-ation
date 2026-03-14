import math
from iter_ation.physics.formulas import greenwald_density, greenwald_fraction, q95
from iter_ation.physics.constants import ITER


def test_greenwald_density_nominal():
    """n_G = Ip / (pi * a^2) = 15 / (pi * 4) ~ 1.194."""
    n_g = greenwald_density(Ip=15.0, a=ITER.a)
    assert abs(n_g - 15.0 / (math.pi * 4.0)) < 1e-6


def test_greenwald_fraction_nominal():
    """fGW = n_e / n_G = 0.9 / 1.194 ~ 0.754."""
    fgw = greenwald_fraction(n_e=0.9, Ip=15.0, a=ITER.a)
    expected = 0.9 / (15.0 / (math.pi * 4.0))
    assert abs(fgw - expected) < 1e-6


def test_greenwald_fraction_at_limit():
    """When n_e = n_G, fGW = 1.0."""
    n_g = greenwald_density(Ip=15.0, a=ITER.a)
    fgw = greenwald_fraction(n_e=n_g, Ip=15.0, a=ITER.a)
    assert abs(fgw - 1.0) < 1e-6


def test_q95_nominal():
    """At nominal Ip=15 and li=0.85, q95 = 3.1."""
    q = q95(Ip=15.0, li=0.85)
    assert abs(q - 3.1) < 1e-6


def test_q95_decreases_with_higher_ip():
    q_low = q95(Ip=10.0)
    q_high = q95(Ip=20.0)
    assert q_low > q_high


def test_q95_decreases_with_higher_li():
    """When li increases (peaked current), q95 drops toward q=2."""
    q_nominal = q95(Ip=15.0, li=0.85)
    q_peaked = q95(Ip=15.0, li=1.2)
    assert q_peaked < q_nominal
    # li=1.2 -> q95 = 3.1 * (0.85/1.2) = 2.196
    assert abs(q_peaked - 3.1 * (0.85 / 1.2)) < 1e-6
    assert q_peaked < 2.5


def test_q95_at_ref_gives_ref():
    """When Ip=Ip_ref and li=li_ref, q95 = q95_ref exactly."""
    q = q95(Ip=15.0, li=0.85, Ip_ref=15.0, li_ref=0.85, q95_ref=3.1)
    assert abs(q - 3.1) < 1e-6
