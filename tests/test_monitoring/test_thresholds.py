from iter_ation.monitoring.thresholds import evaluate_parameter, evaluate_all, AlertLevel


def test_nominal_greenwald_is_nominal():
    assert evaluate_parameter("greenwald_fraction", 0.75) == AlertLevel.NOMINAL


def test_greenwald_at_risk():
    assert evaluate_parameter("greenwald_fraction", 0.90) == AlertLevel.WARNING


def test_greenwald_at_critical():
    assert evaluate_parameter("greenwald_fraction", 1.05) == AlertLevel.DANGER


def test_q95_below_risk():
    assert evaluate_parameter("q95", 2.3) == AlertLevel.WARNING


def test_q95_below_critical():
    assert evaluate_parameter("q95", 1.8) == AlertLevel.DANGER


def test_te_core_drop_30pct():
    # >30% drop from nominal 20 = value < 14
    assert evaluate_parameter("Te_core", 13.5) == AlertLevel.WARNING


def test_te_core_drop_50pct():
    # >50% drop = value < 10
    assert evaluate_parameter("Te_core", 9.5) == AlertLevel.DANGER


def test_zcur_abs_above_risk():
    assert evaluate_parameter("zcur", -0.15) == AlertLevel.WARNING


def test_zcur_abs_above_critical():
    assert evaluate_parameter("zcur", 0.25) == AlertLevel.DANGER


def test_no_threshold_stays_nominal():
    assert evaluate_parameter("n_e", 999.0) == AlertLevel.NOMINAL


def test_v_loop_spike():
    assert evaluate_parameter("v_loop", 0.5) == AlertLevel.NOMINAL
    assert evaluate_parameter("v_loop", 1.5) == AlertLevel.DANGER


def test_beta_n_above_risk():
    assert evaluate_parameter("beta_n", 3.0) == AlertLevel.WARNING


def test_evaluate_all_returns_max():
    values = {"greenwald_fraction": 0.90, "q95": 1.8, "n_e": 0.9}
    level = evaluate_all(values)
    assert level == AlertLevel.DANGER  # q95 < 2.0
