"""Shared test fixtures for iter-ation."""
import pytest
from iter_ation.generator.plasma_state import PlasmaState


@pytest.fixture
def nominal_state() -> PlasmaState:
    return PlasmaState.nominal()
