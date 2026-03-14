import numpy as np
from iter_ation.physics.profiles import get_radial_data


def test_returns_correct_keys():
    data = get_radial_data(n_e=0.9, Te_core=20.0, li=0.85)
    assert "r" in data
    assert "n_e_profile" in data
    assert "Te_profile" in data
    assert "alpha_n" in data
    assert "alpha_t" in data


def test_correct_number_of_points():
    data = get_radial_data(n_e=0.9, Te_core=20.0, li=0.85, points=30)
    assert len(data["r"]) == 30
    assert len(data["n_e_profile"]) == 30


def test_profiles_peak_at_center():
    data = get_radial_data(n_e=0.9, Te_core=20.0, li=0.85)
    assert data["n_e_profile"][0] > data["n_e_profile"][-1]
    assert data["Te_profile"][0] > data["Te_profile"][-1]


def test_profiles_zero_at_edge():
    data = get_radial_data(n_e=0.9, Te_core=20.0, li=0.85)
    assert data["n_e_profile"][-1] < 0.01
    assert data["Te_profile"][-1] < 0.01


def test_te_core_matches():
    data = get_radial_data(n_e=0.9, Te_core=20.0, li=0.85)
    assert abs(data["Te_profile"][0] - 20.0) < 0.01


def test_higher_li_sharper_profile():
    nominal = get_radial_data(n_e=0.9, Te_core=20.0, li=0.85)
    peaked = get_radial_data(n_e=0.9, Te_core=20.0, li=1.2)
    # Higher li → higher alpha → normalized profile drops faster at mid-radius
    mid = len(nominal["r"]) // 2
    nom_ratio = nominal["n_e_profile"][mid] / nominal["n_e_profile"][0]
    peak_ratio = peaked["n_e_profile"][mid] / peaked["n_e_profile"][0]
    assert peak_ratio < nom_ratio  # Peaked profile falls off faster
    assert peaked["alpha_n"] > nominal["alpha_n"]


def test_lower_li_flatter_profile():
    nominal = get_radial_data(n_e=0.9, Te_core=20.0, li=0.85)
    flat = get_radial_data(n_e=0.9, Te_core=20.0, li=0.6)
    mid = len(nominal["r"]) // 2
    nom_ratio = nominal["n_e_profile"][mid] / nominal["n_e_profile"][0]
    flat_ratio = flat["n_e_profile"][mid] / flat["n_e_profile"][0]
    assert flat_ratio > nom_ratio  # Flat profile retains more at mid-radius
    assert flat["alpha_n"] < nominal["alpha_n"]
