from enum import IntEnum
from iter_ation.physics.parameters import get_parameter, ThresholdDirection


class AlertLevel(IntEnum):
    NOMINAL = 0
    WARNING = 1
    DANGER = 2
    DISRUPTION = 3


def _check_threshold(
    value: float, threshold: float, direction: ThresholdDirection, nominal: float,
) -> bool:
    if direction == ThresholdDirection.ABOVE:
        return value > threshold
    elif direction == ThresholdDirection.BELOW:
        return value < threshold
    elif direction == ThresholdDirection.ABS_ABOVE:
        return abs(value) > threshold
    elif direction == ThresholdDirection.DROP_PCT:
        if nominal == 0:
            return False
        return (nominal - value) / abs(nominal) > threshold
    return False


def evaluate_parameter(name: str, value: float) -> AlertLevel:
    """Evaluate the alert level for a single parameter."""
    param = get_parameter(name)

    if (param.critical_threshold is not None and param.critical_direction is not None):
        if _check_threshold(value, param.critical_threshold, param.critical_direction, param.nominal):
            return AlertLevel.DANGER

    if (param.risk_threshold is not None and param.risk_direction is not None):
        if _check_threshold(value, param.risk_threshold, param.risk_direction, param.nominal):
            return AlertLevel.WARNING

    return AlertLevel.NOMINAL


def evaluate_all(values: dict[str, float]) -> AlertLevel:
    """Return the highest alert level across all parameters."""
    max_level = AlertLevel.NOMINAL
    for name, value in values.items():
        level = evaluate_parameter(name, value)
        if level > max_level:
            max_level = level
    return max_level
