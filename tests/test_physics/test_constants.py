from iter_ation.physics.constants import ITER


def test_iter_major_radius():
    assert ITER.R_0 == 6.2


def test_iter_minor_radius():
    assert ITER.a == 2.0


def test_iter_toroidal_field():
    assert ITER.B_T == 5.3


def test_iter_elongation():
    assert ITER.kappa == 1.7


def test_iter_plasma_volume():
    assert ITER.V_plasma == 830.0
