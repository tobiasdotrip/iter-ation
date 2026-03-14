from iter_ation.monitoring.alerts import AlertLog
from iter_ation.monitoring.thresholds import AlertLevel


def test_alert_log_starts_empty():
    assert len(AlertLog().entries) == 0


def test_records_level_change():
    log = AlertLog()
    log.update(0.1, AlertLevel.WARNING, {"greenwald_fraction": AlertLevel.WARNING})
    assert len(log.entries) == 1
    assert log.entries[0].level == AlertLevel.WARNING


def test_skips_same_level():
    log = AlertLog()
    log.update(0.1, AlertLevel.WARNING, {"greenwald_fraction": AlertLevel.WARNING})
    log.update(0.2, AlertLevel.WARNING, {"greenwald_fraction": AlertLevel.WARNING})
    assert len(log.entries) == 1


def test_records_return_to_nominal():
    log = AlertLog()
    log.update(0.1, AlertLevel.WARNING, {"greenwald_fraction": AlertLevel.WARNING})
    log.update(0.2, AlertLevel.NOMINAL, {})
    assert len(log.entries) == 2


def test_max_entries():
    log = AlertLog(max_entries=5)
    for i in range(10):
        level = AlertLevel.WARNING if i % 2 == 0 else AlertLevel.NOMINAL
        log.update(float(i), level, {})
    assert len(log.entries) <= 5


def test_force_disruption():
    log = AlertLog()
    entry = log.force_disruption(1.5)
    assert entry.level == AlertLevel.DISRUPTION
    assert len(log.entries) == 1
