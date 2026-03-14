from enum import Enum


class OperatorAction(Enum):
    GAS_UP = "gas_up"
    GAS_DOWN = "gas_down"
    POWER_UP = "power_up"
    POWER_DOWN = "power_down"
    SPI = "spi"
    SCRAM = "scram"


ACTION_DELTAS: dict[OperatorAction, dict[str, float]] = {
    OperatorAction.GAS_UP: {"n_e": 0.02},
    OperatorAction.GAS_DOWN: {"n_e": -0.02},
    OperatorAction.POWER_UP: {"p_input": 2.0},
    OperatorAction.POWER_DOWN: {"p_input": -2.0},
}
