from iter_ation.monitoring.operator import OperatorAction, ACTION_DELTAS


def test_all_basic_actions_in_deltas():
    assert OperatorAction.GAS_UP in ACTION_DELTAS
    assert OperatorAction.GAS_DOWN in ACTION_DELTAS
    assert OperatorAction.POWER_UP in ACTION_DELTAS
    assert OperatorAction.POWER_DOWN in ACTION_DELTAS


def test_spi_and_scram_not_in_deltas():
    assert OperatorAction.SPI not in ACTION_DELTAS
    assert OperatorAction.SCRAM not in ACTION_DELTAS


def test_gas_up_increases_n_e():
    assert ACTION_DELTAS[OperatorAction.GAS_UP]["n_e"] > 0


def test_gas_down_decreases_n_e():
    assert ACTION_DELTAS[OperatorAction.GAS_DOWN]["n_e"] < 0
