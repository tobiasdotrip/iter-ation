# ITER-ATION Disruption Monitor — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python TUI application that monitors simulated plasma disruptions in a tokamak, with synthetic data generation focused on the Greenwald fraction and interactive operator controls.

**Architecture:** 4-layer architecture (Physics → Generator → Monitoring → TUI). The generator runs in a Textual Worker thread, producing `PlasmaState` dataclass snapshots each tick (1 ms simulated). The TUI consumes these via `post_message` and renders gauges, timeline, and alerts. Operator actions flow back via a thread-safe `queue.Queue`.

**Tech Stack:** Python 3.11+, Textual (TUI), plotext (terminal graphs), numpy (data generation), pytest (tests)

**Spec:** `docs/superpowers/specs/2026-03-14-disruption-monitor-design.md`

**Design notes:**
- `textual-plotext` is **not** used. We use `plotext` directly with `AnsiDecoder` for rendering in a custom widget. This avoids an extra dependency and gives us full control over refresh.
- `Wmhd` critical threshold ("chute > 40% en < 5 ms" in the spec) is **simplified** to a static drop percentage vs nominal. A rate-based threshold would require value history tracking — deferred to v2.
- Operator action **response delays** (10-50 ms simulated in the spec) are not implemented in v1. Actions are applied immediately.

---

## File Map

```
iter-ation/
├── pyproject.toml                          # Package config, deps, entry point
├── src/
│   └── iter_ation/
│       ├── __init__.py                     # Version string
│       ├── __main__.py                     # python -m iter_ation entry
│       ├── cli.py                          # Argument parsing (--mode, --speed)
│       ├── physics/
│       │   ├── __init__.py
│       │   ├── constants.py                # ITER machine constants (R_0, a, B_T, etc.)
│       │   ├── parameters.py               # Parameter definitions: name, unit, nominal, thresholds, sigma
│       │   └── formulas.py                 # Greenwald density, q95 derivation
│       ├── generator/
│       │   ├── __init__.py
│       │   ├── plasma_state.py             # PlasmaState frozen dataclass
│       │   ├── noise.py                    # Gaussian noise + slow drift per parameter
│       │   ├── correlations.py             # Inter-parameter correlations
│       │   ├── disruption.py               # Risk scoring + cascade phases (TQ, CQ, VDE)
│       │   └── engine.py                   # Tick loop: noise → correlations → risk → state
│       ├── monitoring/
│       │   ├── __init__.py
│       │   ├── thresholds.py               # Evaluate alert level per parameter
│       │   ├── alerts.py                   # AlertLevel enum, AlertEntry, AlertLog
│       │   └── operator.py                 # OperatorAction enum, apply action to engine
│       └── tui/
│           ├── __init__.py
│           ├── app.py                      # Main Textual App, Worker, key bindings
│           ├── dashboard.py                # Layout composition (Horizontal/Vertical splits)
│           ├── theme.py                    # Color constants for alert levels
│           └── widgets/
│               ├── __init__.py
│               ├── gauge.py                # Horizontal gauge bar with color thresholds
│               ├── timeline.py             # Plotext-based scrolling time series
│               ├── alert_log.py            # Scrollable alert history
│               └── controls.py             # Footer bar with mode/controls display
└── tests/
    ├── conftest.py                         # Shared fixtures (nominal PlasmaState, etc.)
    ├── test_physics/
    │   ├── __init__.py
    │   ├── test_constants.py
    │   ├── test_parameters.py
    │   └── test_formulas.py
    ├── test_generator/
    │   ├── __init__.py
    │   ├── test_noise.py
    │   ├── test_correlations.py
    │   ├── test_disruption.py
    │   └── test_engine.py
    └── test_monitoring/
        ├── __init__.py
        ├── test_thresholds.py
        ├── test_alerts.py
        └── test_operator.py
```

---

## Chunk 1: Foundation & Physics

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/iter_ation/__init__.py`
- Create: `src/iter_ation/__main__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "iter-ation"
version = "0.1.0"
description = "Tokamak disruption monitor TUI"
requires-python = ">=3.11"
dependencies = [
    "textual>=1.0.0",
    "plotext>=5.3.0",
    "numpy>=1.26.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
]

[project.scripts]
iter-ation = "iter_ation.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/iter_ation"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 2: Create package init and entry point**

`src/iter_ation/__init__.py`:
```python
__version__ = "0.1.0"
```

`src/iter_ation/__main__.py`:
```python
from iter_ation.cli import main

main()
```

- [ ] **Step 3: Create empty conftest and test package inits**

`tests/conftest.py`:
```python
"""Shared test fixtures for iter-ation."""
```

Create empty `__init__.py` in: `tests/test_physics/`, `tests/test_generator/`, `tests/test_monitoring/`.

- [ ] **Step 4: Install project in dev mode and verify**

```bash
pip install -e ".[dev]"
```

Expected: installs successfully, `pytest --co` returns "no tests ran".

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/ tests/
git commit -m "chore: scaffold project with pyproject.toml and package structure"
```

---

### Task 2: Physics — Constants & Parameter Definitions

**Files:**
- Create: `src/iter_ation/physics/__init__.py`
- Create: `src/iter_ation/physics/constants.py`
- Create: `src/iter_ation/physics/parameters.py`
- Create: `tests/test_physics/test_constants.py`
- Create: `tests/test_physics/test_parameters.py`

- [ ] **Step 1: Write tests for constants**

`tests/test_physics/test_constants.py`:
```python
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
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
pytest tests/test_physics/test_constants.py -v
```

Expected: ModuleNotFoundError

- [ ] **Step 3: Implement constants**

`src/iter_ation/physics/__init__.py`: empty file.

`src/iter_ation/physics/constants.py`:
```python
from dataclasses import dataclass


@dataclass(frozen=True)
class MachineConstants:
    """Tokamak machine constants."""
    R_0: float    # Major radius (m)
    a: float      # Minor radius (m)
    B_T: float    # Toroidal field (T)
    kappa: float  # Elongation
    V_plasma: float  # Plasma volume (m³)


ITER = MachineConstants(
    R_0=6.2,
    a=2.0,
    B_T=5.3,
    kappa=1.7,
    V_plasma=830.0,
)
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/test_physics/test_constants.py -v
```

- [ ] **Step 5: Write tests for parameter definitions**

`tests/test_physics/test_parameters.py`:
```python
from iter_ation.physics.parameters import PARAMETERS, get_parameter


def test_parameters_count():
    assert len(PARAMETERS) == 13


def test_greenwald_fraction_exists():
    p = get_parameter("greenwald_fraction")
    assert p.nominal == 0.75
    assert p.unit == ""
    assert p.risk_threshold is not None


def test_n_e_nominal():
    p = get_parameter("n_e")
    assert p.nominal == 0.9
    assert p.unit == "1e20 m⁻³"
    assert p.noise_sigma_pct == 0.5


def test_all_parameters_have_nominal():
    for p in PARAMETERS:
        assert p.nominal is not None, f"{p.name} has no nominal value"


def test_derived_parameters_have_no_sigma():
    """greenwald_fraction and q95 are derived from formulas."""
    derived = {"greenwald_fraction", "q95"}
    for p in PARAMETERS:
        if p.name in derived:
            assert p.noise_sigma_pct is None, f"{p.name} is derived but has sigma"


def test_beta_n_has_sigma():
    """beta_n is generated with noise (not derived from formula in v1)."""
    p = get_parameter("beta_n")
    assert p.noise_sigma_pct is not None


def test_zcur_has_absolute_sigma():
    """zcur (nominal=0) uses noise_sigma_abs for noise amplitude."""
    p = get_parameter("zcur")
    assert p.noise_sigma_abs is not None
    assert p.noise_sigma_abs > 0
```

- [ ] **Step 6: Run tests — expect FAIL**

```bash
pytest tests/test_physics/test_parameters.py -v
```

- [ ] **Step 7: Implement parameter definitions**

`src/iter_ation/physics/parameters.py`:
```python
from dataclasses import dataclass
from enum import Enum


class ThresholdDirection(Enum):
    """How to compare value to threshold."""
    ABOVE = "above"          # value > threshold = alert
    BELOW = "below"          # value < threshold = alert
    ABS_ABOVE = "abs_above"  # |value| > threshold = alert
    DROP_PCT = "drop_pct"    # (nominal - value) / nominal > threshold = alert


@dataclass(frozen=True)
class ParameterDef:
    """Definition of a plasma parameter."""
    name: str
    unit: str
    nominal: float
    noise_sigma_pct: float | None  # % of nominal, None for derived params
    noise_sigma_abs: float | None  # Absolute sigma, for params with nominal=0
    risk_threshold: float | None
    risk_direction: ThresholdDirection | None
    critical_threshold: float | None
    critical_direction: ThresholdDirection | None

    @property
    def effective_sigma(self) -> float:
        """Return the effective noise standard deviation."""
        if self.noise_sigma_abs is not None:
            return self.noise_sigma_abs
        if self.noise_sigma_pct is not None:
            return abs(self.nominal) * self.noise_sigma_pct / 100.0
        return 0.0


PARAMETERS: list[ParameterDef] = [
    ParameterDef(
        name="greenwald_fraction",
        unit="",
        nominal=0.75,
        noise_sigma_pct=None,
        noise_sigma_abs=None,
        risk_threshold=0.85,
        risk_direction=ThresholdDirection.ABOVE,
        critical_threshold=1.0,
        critical_direction=ThresholdDirection.ABOVE,
    ),
    ParameterDef(
        name="n_e",
        unit="1e20 m⁻³",
        nominal=0.9,
        noise_sigma_pct=0.5,
        noise_sigma_abs=None,
        risk_threshold=None,
        risk_direction=None,
        critical_threshold=None,
        critical_direction=None,
    ),
    ParameterDef(
        name="Ip",
        unit="MA",
        nominal=15.0,
        noise_sigma_pct=0.1,
        noise_sigma_abs=None,
        risk_threshold=None,
        risk_direction=None,
        critical_threshold=0.20,
        critical_direction=ThresholdDirection.DROP_PCT,
    ),
    ParameterDef(
        name="q95",
        unit="",
        nominal=3.1,
        noise_sigma_pct=None,
        noise_sigma_abs=None,
        risk_threshold=2.5,
        risk_direction=ThresholdDirection.BELOW,
        critical_threshold=2.0,
        critical_direction=ThresholdDirection.BELOW,
    ),
    ParameterDef(
        name="Te_core",
        unit="keV",
        nominal=20.0,
        noise_sigma_pct=1.0,
        noise_sigma_abs=None,
        risk_threshold=0.30,
        risk_direction=ThresholdDirection.DROP_PCT,
        critical_threshold=0.50,
        critical_direction=ThresholdDirection.DROP_PCT,
    ),
    ParameterDef(
        name="Wmhd",
        unit="MJ",
        nominal=350.0,
        noise_sigma_pct=0.5,
        noise_sigma_abs=None,
        risk_threshold=0.20,
        risk_direction=ThresholdDirection.DROP_PCT,
        # Spec says "chute > 40% en < 5 ms" — simplified to static drop % in v1
        critical_threshold=0.40,
        critical_direction=ThresholdDirection.DROP_PCT,
    ),
    ParameterDef(
        name="radiated_fraction",
        unit="",
        nominal=0.5,
        noise_sigma_pct=1.0,
        noise_sigma_abs=None,
        risk_threshold=0.7,
        risk_direction=ThresholdDirection.ABOVE,
        critical_threshold=0.9,
        critical_direction=ThresholdDirection.ABOVE,
    ),
    ParameterDef(
        name="li",
        unit="",
        nominal=0.85,
        noise_sigma_pct=0.3,
        noise_sigma_abs=None,
        risk_threshold=1.2,
        risk_direction=ThresholdDirection.ABOVE,
        critical_threshold=1.4,
        critical_direction=ThresholdDirection.ABOVE,
    ),
    ParameterDef(
        name="n1_amplitude",
        unit="mT",
        nominal=0.05,
        noise_sigma_pct=2.0,
        noise_sigma_abs=None,
        risk_threshold=0.5,
        risk_direction=ThresholdDirection.ABOVE,
        critical_threshold=1.0,
        critical_direction=ThresholdDirection.ABOVE,
    ),
    ParameterDef(
        name="v_loop",
        unit="V",
        nominal=0.2,
        noise_sigma_pct=0.5,
        noise_sigma_abs=None,
        risk_threshold=None,
        risk_direction=None,
        critical_threshold=1.0,
        critical_direction=ThresholdDirection.ABOVE,
    ),
    ParameterDef(
        name="beta_n",
        unit="",
        nominal=1.8,
        noise_sigma_pct=0.5,  # Generated with noise, not derived from formula
        noise_sigma_abs=None,
        risk_threshold=2.8,
        risk_direction=ThresholdDirection.ABOVE,
        critical_threshold=3.5,
        critical_direction=ThresholdDirection.ABOVE,
    ),
    ParameterDef(
        name="zcur",
        unit="m",
        nominal=0.0,
        noise_sigma_pct=None,    # Can't use % of zero
        noise_sigma_abs=0.002,   # 2 mm noise per tick
        risk_threshold=0.1,
        risk_direction=ThresholdDirection.ABS_ABOVE,
        critical_threshold=0.2,
        critical_direction=ThresholdDirection.ABS_ABOVE,
    ),
    ParameterDef(
        name="p_input",
        unit="MW",
        nominal=50.0,
        noise_sigma_pct=0.1,
        noise_sigma_abs=None,
        risk_threshold=0.30,
        risk_direction=ThresholdDirection.DROP_PCT,
        critical_threshold=0.50,
        critical_direction=ThresholdDirection.DROP_PCT,
    ),
]

_PARAM_INDEX: dict[str, ParameterDef] = {p.name: p for p in PARAMETERS}


def get_parameter(name: str) -> ParameterDef:
    """Get a parameter definition by name. Raises KeyError if not found."""
    return _PARAM_INDEX[name]
```

- [ ] **Step 8: Run tests — expect PASS**

```bash
pytest tests/test_physics/ -v
```

- [ ] **Step 9: Commit**

```bash
git add src/iter_ation/physics/ tests/test_physics/
git commit -m "feat: add ITER constants and parameter definitions"
```

---

### Task 3: Physics — Formulas

**Files:**
- Create: `src/iter_ation/physics/formulas.py`
- Create: `tests/test_physics/test_formulas.py`

- [ ] **Step 1: Write tests for formulas**

`tests/test_physics/test_formulas.py`:
```python
import math
from iter_ation.physics.formulas import greenwald_density, greenwald_fraction, q95
from iter_ation.physics.constants import ITER


def test_greenwald_density_nominal():
    """n_G = Ip / (pi * a^2) = 15 / (pi * 4) ≈ 1.194."""
    n_g = greenwald_density(Ip=15.0, a=ITER.a)
    assert abs(n_g - 15.0 / (math.pi * 4.0)) < 1e-6


def test_greenwald_fraction_nominal():
    """fGW = n_e / n_G = 0.9 / 1.194 ≈ 0.754."""
    fgw = greenwald_fraction(n_e=0.9, Ip=15.0, a=ITER.a)
    expected = 0.9 / (15.0 / (math.pi * 4.0))
    assert abs(fgw - expected) < 1e-6


def test_greenwald_fraction_at_limit():
    """When n_e = n_G, fGW = 1.0."""
    n_g = greenwald_density(Ip=15.0, a=ITER.a)
    fgw = greenwald_fraction(n_e=n_g, Ip=15.0, a=ITER.a)
    assert abs(fgw - 1.0) < 1e-6


def test_q95_nominal():
    """q95 = (5 * a^2 * kappa * B_T) / (R_0 * Ip)."""
    q = q95(a=ITER.a, kappa=ITER.kappa, B_T=ITER.B_T, R_0=ITER.R_0, Ip=15.0)
    expected = (5.0 * 4.0 * 1.7 * 5.3) / (6.2 * 15.0)
    assert abs(q - expected) < 1e-6


def test_q95_decreases_with_higher_ip():
    q_low = q95(a=ITER.a, kappa=ITER.kappa, B_T=ITER.B_T, R_0=ITER.R_0, Ip=10.0)
    q_high = q95(a=ITER.a, kappa=ITER.kappa, B_T=ITER.B_T, R_0=ITER.R_0, Ip=20.0)
    assert q_low > q_high
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
pytest tests/test_physics/test_formulas.py -v
```

- [ ] **Step 3: Implement formulas**

`src/iter_ation/physics/formulas.py`:
```python
import math


def greenwald_density(Ip: float, a: float) -> float:
    """Greenwald density limit: n_G [1e20 m⁻³] = Ip [MA] / (pi * a² [m²])."""
    return Ip / (math.pi * a**2)


def greenwald_fraction(n_e: float, Ip: float, a: float) -> float:
    """Greenwald fraction fGW = n_e / n_G."""
    return n_e / greenwald_density(Ip, a)


def q95(a: float, kappa: float, B_T: float, R_0: float, Ip: float) -> float:
    """Safety factor at 95% flux surface (simplified cylindrical)."""
    return (5.0 * a**2 * kappa * B_T) / (R_0 * Ip)
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/test_physics/ -v
```

- [ ] **Step 5: Commit**

```bash
git add src/iter_ation/physics/formulas.py tests/test_physics/test_formulas.py
git commit -m "feat: add Greenwald density and q95 formulas"
```

---

## Chunk 2: Generator

### Task 4: PlasmaState Dataclass

**Files:**
- Create: `src/iter_ation/generator/__init__.py`
- Create: `src/iter_ation/generator/plasma_state.py`
- Update: `tests/conftest.py`
- Create: `tests/test_generator/test_plasma_state.py`

- [ ] **Step 1: Write tests**

`tests/conftest.py`:
```python
"""Shared test fixtures for iter-ation."""
import pytest
from iter_ation.generator.plasma_state import PlasmaState


@pytest.fixture
def nominal_state() -> PlasmaState:
    return PlasmaState.nominal()
```

`tests/test_generator/test_plasma_state.py`:
```python
from iter_ation.generator.plasma_state import PlasmaState


def test_nominal_state_creates():
    state = PlasmaState.nominal()
    assert state.greenwald_fraction == 0.75
    assert state.n_e == 0.9
    assert state.Ip == 15.0
    assert state.sim_time == 0.0


def test_plasma_state_is_frozen():
    state = PlasmaState.nominal()
    try:
        state.n_e = 1.0
        assert False, "Should not allow mutation"
    except AttributeError:
        pass


def test_plasma_state_values_dict():
    state = PlasmaState.nominal()
    values = state.values()
    assert isinstance(values, dict)
    assert len(values) == 13
    assert "greenwald_fraction" in values
    assert "sim_time" not in values
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
pytest tests/test_generator/test_plasma_state.py -v
```

- [ ] **Step 3: Implement PlasmaState**

`src/iter_ation/generator/__init__.py`: empty.

`src/iter_ation/generator/plasma_state.py`:
```python
from __future__ import annotations
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class PlasmaState:
    """Immutable snapshot of all plasma parameters at a given time."""
    sim_time: float

    greenwald_fraction: float
    n_e: float
    Ip: float
    q95: float
    Te_core: float
    Wmhd: float
    radiated_fraction: float
    li: float
    n1_amplitude: float
    v_loop: float
    beta_n: float
    zcur: float
    p_input: float

    _PARAM_NAMES: ClassVar[tuple[str, ...]] = (
        "greenwald_fraction", "n_e", "Ip", "q95", "Te_core", "Wmhd",
        "radiated_fraction", "li", "n1_amplitude", "v_loop", "beta_n",
        "zcur", "p_input",
    )

    def values(self) -> dict[str, float]:
        """Return parameter name → value dict (excludes sim_time)."""
        return {name: getattr(self, name) for name in self._PARAM_NAMES}

    @classmethod
    def nominal(cls, sim_time: float = 0.0) -> PlasmaState:
        return cls(
            sim_time=sim_time,
            greenwald_fraction=0.75,
            n_e=0.9,
            Ip=15.0,
            q95=3.1,
            Te_core=20.0,
            Wmhd=350.0,
            radiated_fraction=0.5,
            li=0.85,
            n1_amplitude=0.05,
            v_loop=0.2,
            beta_n=1.8,
            zcur=0.0,
            p_input=50.0,
        )
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/test_generator/test_plasma_state.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/iter_ation/generator/ tests/conftest.py tests/test_generator/
git commit -m "feat: add PlasmaState frozen dataclass with nominal factory"
```

---

### Task 5: Noise Model

**Files:**
- Create: `src/iter_ation/generator/noise.py`
- Create: `tests/test_generator/test_noise.py`

- [ ] **Step 1: Write tests**

`tests/test_generator/test_noise.py`:
```python
import numpy as np
from iter_ation.generator.noise import apply_noise, apply_drift


def test_apply_noise_returns_all_keys():
    rng = np.random.default_rng(42)
    values = {"n_e": 0.9, "Ip": 15.0, "Te_core": 20.0}
    noisy = apply_noise(values, rng)
    assert set(noisy.keys()) == set(values.keys())


def test_apply_noise_stays_close_to_nominal():
    rng = np.random.default_rng(42)
    samples = []
    for _ in range(1000):
        noisy = apply_noise({"n_e": 0.9}, rng)
        samples.append(noisy["n_e"])
    mean = sum(samples) / len(samples)
    assert abs(mean - 0.9) < 0.01


def test_apply_noise_zcur_uses_abs_sigma():
    """zcur (nominal=0) should still get noise via noise_sigma_abs."""
    rng = np.random.default_rng(42)
    samples = [apply_noise({"zcur": 0.0}, rng)["zcur"] for _ in range(100)]
    assert any(s != 0.0 for s in samples)


def test_apply_drift_changes_value():
    rng = np.random.default_rng(42)
    drift_state = {"n_e": 0.0}
    new_drift = apply_drift(drift_state, rng, dt=0.001)
    assert "n_e" in new_drift
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
pytest tests/test_generator/test_noise.py -v
```

- [ ] **Step 3: Implement noise model**

`src/iter_ation/generator/noise.py`:
```python
import numpy as np
from iter_ation.physics.parameters import PARAMETERS, get_parameter

# Parameters generated with noise (have sigma defined)
GENERATED_PARAMS = [
    p for p in PARAMETERS
    if p.noise_sigma_pct is not None or p.noise_sigma_abs is not None
]

_DRIFT_RATE = 0.002  # Fraction of nominal per sqrt(second)


def apply_noise(
    values: dict[str, float],
    rng: np.random.Generator,
) -> dict[str, float]:
    """Apply Gaussian noise to parameter values."""
    noisy = {}
    for name, value in values.items():
        param = get_parameter(name)
        sigma = param.effective_sigma
        if sigma > 0:
            noisy[name] = value + rng.normal(0, sigma)
        else:
            noisy[name] = value
    return noisy


def apply_drift(
    drift_state: dict[str, float],
    rng: np.random.Generator,
    dt: float,
) -> dict[str, float]:
    """Update drift offsets via random walk."""
    new_drift = {}
    for name, current in drift_state.items():
        param = get_parameter(name)
        sigma = param.effective_sigma
        if sigma > 0:
            step = rng.normal(0, _DRIFT_RATE * max(abs(param.nominal), sigma) * np.sqrt(dt))
            new_drift[name] = current + step
        else:
            new_drift[name] = current
    return new_drift
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/test_generator/test_noise.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/iter_ation/generator/noise.py tests/test_generator/test_noise.py
git commit -m "feat: add Gaussian noise and random walk drift model"
```

---

### Task 6: Inter-Parameter Correlations

**Files:**
- Create: `src/iter_ation/generator/correlations.py`
- Create: `tests/test_generator/test_correlations.py`

- [ ] **Step 1: Write tests**

`tests/test_generator/test_correlations.py`:
```python
from iter_ation.generator.correlations import apply_correlations
from iter_ation.physics.parameters import get_parameter


def test_n_e_increase_raises_radiated_fraction():
    nominal = {p.name: p.nominal for p in __import__("iter_ation.physics.parameters", fromlist=["PARAMETERS"]).PARAMETERS if p.noise_sigma_pct is not None or p.noise_sigma_abs is not None}
    modified = dict(nominal)
    modified["n_e"] = 1.2  # well above nominal 0.9
    result = apply_correlations(modified)
    assert result["radiated_fraction"] > nominal["radiated_fraction"]


def test_n_e_increase_lowers_te_core():
    from iter_ation.physics.parameters import PARAMETERS
    nominal = {p.name: p.nominal for p in PARAMETERS if p.noise_sigma_pct is not None or p.noise_sigma_abs is not None}
    modified = dict(nominal)
    modified["n_e"] = 1.2
    result = apply_correlations(modified)
    assert result["Te_core"] < nominal["Te_core"]


def test_nominal_values_unchanged():
    from iter_ation.physics.parameters import PARAMETERS
    nominal = {p.name: p.nominal for p in PARAMETERS if p.noise_sigma_pct is not None or p.noise_sigma_abs is not None}
    result = apply_correlations(dict(nominal))
    for name, val in result.items():
        assert abs(val - nominal[name]) < 1e-9, f"{name} changed at nominal"
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
pytest tests/test_generator/test_correlations.py -v
```

- [ ] **Step 3: Implement correlations**

`src/iter_ation/generator/correlations.py`:
```python
from iter_ation.physics.parameters import get_parameter


def apply_correlations(values: dict[str, float]) -> dict[str, float]:
    """Apply inter-parameter correlations.

    Correlations are driven by deviations from nominal values.
    Spec: n_e ↑ → radiated_fraction ↑ → Te_core ↓
    """
    result = dict(values)

    n_e_nom = get_parameter("n_e").nominal
    te_nom = get_parameter("Te_core").nominal
    rad_nom = get_parameter("radiated_fraction").nominal
    wmhd_nom = get_parameter("Wmhd").nominal

    # n_e deviation from nominal
    n_e_delta = (result.get("n_e", n_e_nom) - n_e_nom) / n_e_nom

    # n_e ↑ → radiated_fraction ↑ (coupling factor 0.3)
    if "radiated_fraction" in result:
        result["radiated_fraction"] += n_e_delta * 0.3 * rad_nom

    # radiated_fraction ↑ → Te_core ↓ (coupling factor -0.4)
    rad_delta = (result.get("radiated_fraction", rad_nom) - rad_nom) / rad_nom
    if "Te_core" in result:
        result["Te_core"] += rad_delta * (-0.4) * te_nom

    # Te_core affects Wmhd (thermal energy ~ n * T * V)
    te_delta = (result.get("Te_core", te_nom) - te_nom) / te_nom
    if "Wmhd" in result:
        result["Wmhd"] += te_delta * 0.5 * wmhd_nom

    return result
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/test_generator/test_correlations.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/iter_ation/generator/correlations.py tests/test_generator/test_correlations.py
git commit -m "feat: add inter-parameter correlations (n_e → rad → Te → Wmhd)"
```

---

### Task 7: Disruption Risk & Cascade

**Files:**
- Create: `src/iter_ation/generator/disruption.py`
- Create: `tests/test_generator/test_disruption.py`

- [ ] **Step 1: Write tests**

`tests/test_generator/test_disruption.py`:
```python
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
    score = compute_risk_score(greenwald_fraction=1.1, radiated_fraction=0.5,
                                n1_amplitude=0.05, q95=3.1)
    assert score >= 0.95


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


def test_cascade_signals_recovery_end():
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
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
pytest tests/test_generator/test_disruption.py -v
```

- [ ] **Step 3: Implement disruption model**

`src/iter_ation/generator/disruption.py`:
```python
from __future__ import annotations
import math
from enum import Enum


class DisruptionPhase(Enum):
    NONE = "none"
    PRECURSORS = "precursors"
    THERMAL_QUENCH = "thermal_quench"
    CURRENT_QUENCH = "current_quench"
    RECOVERY = "recovery"


def compute_risk_score(
    greenwald_fraction: float,
    radiated_fraction: float,
    n1_amplitude: float,
    q95: float,
) -> float:
    """Compute disruption risk score in [0, 1]. Dominated by Greenwald fraction."""
    score = 0.0

    if greenwald_fraction > 0.8:
        score += min((greenwald_fraction - 0.8) / 0.2, 1.0) * 0.7

    if radiated_fraction > 0.6:
        score += min((radiated_fraction - 0.6) / 0.3, 1.0) * 0.15

    if n1_amplitude > 0.3:
        score += min((n1_amplitude - 0.3) / 0.7, 1.0) * 0.1

    if q95 < 2.5:
        score += min((2.5 - q95) / 0.5, 1.0) * 0.05

    return min(score, 1.0)


class DisruptionCascade:
    """Temporal evolution of a disruption once triggered."""

    def __init__(self) -> None:
        self.phase = DisruptionPhase.NONE
        self._elapsed: float = 0.0
        self._phase_duration: float = 0.0
        self._precursor_duration: float = 0.3   # 300 ms
        self._tq_duration: float = 0.002         # 2 ms
        self._cq_duration: float = 0.1           # 100 ms
        self._recovery_duration: float = 0.5     # 500 ms

    @property
    def is_active(self) -> bool:
        return self.phase != DisruptionPhase.NONE

    def trigger(self) -> None:
        if self.is_active:
            return
        self.phase = DisruptionPhase.PRECURSORS
        self._elapsed = 0.0
        self._phase_duration = 0.0

    def tick(self, dt: float) -> None:
        if not self.is_active:
            return
        self._elapsed += dt
        self._phase_duration += dt
        self._advance_phase()

    def _advance_phase(self) -> None:
        if self.phase == DisruptionPhase.PRECURSORS:
            if self._phase_duration >= self._precursor_duration:
                self.phase = DisruptionPhase.THERMAL_QUENCH
                self._phase_duration = 0.0
        elif self.phase == DisruptionPhase.THERMAL_QUENCH:
            if self._phase_duration >= self._tq_duration:
                self.phase = DisruptionPhase.CURRENT_QUENCH
                self._phase_duration = 0.0
        elif self.phase == DisruptionPhase.CURRENT_QUENCH:
            if self._phase_duration >= self._cq_duration:
                self.phase = DisruptionPhase.RECOVERY
                self._phase_duration = 0.0
        elif self.phase == DisruptionPhase.RECOVERY:
            if self._phase_duration >= self._recovery_duration:
                self.phase = DisruptionPhase.NONE
                self._elapsed = 0.0
                self._phase_duration = 0.0

    def get_modifications(self) -> dict[str, float]:
        """Return modifiers for plasma parameters.

        Keys without suffix: multiplicative (value *= mod).
        Keys with '_add' suffix: additive (value += mod).
        Special key '_recovery_progress': float 0→1 for ramping back to nominal.
        """
        mods: dict[str, float] = {}
        if self.phase == DisruptionPhase.PRECURSORS:
            growth = math.exp(10.0 * self._phase_duration)
            mods["n1_amplitude"] = growth
            mods["radiated_fraction_add"] = 0.3 * (self._phase_duration / self._precursor_duration)
            mods["li_add"] = 0.2 * (self._phase_duration / self._precursor_duration)

        elif self.phase == DisruptionPhase.THERMAL_QUENCH:
            progress = min(self._phase_duration / self._tq_duration, 1.0)
            mods["Te_core"] = max(1.0 - 0.9 * progress, 0.1)
            mods["Wmhd"] = max(1.0 - 0.9 * progress, 0.1)
            mods["v_loop_add"] = 2.0 * progress

        elif self.phase == DisruptionPhase.CURRENT_QUENCH:
            progress = min(self._phase_duration / self._cq_duration, 1.0)
            mods["Ip"] = max(1.0 - progress, 0.0)
            mods["zcur_add"] = 0.3 * progress

        elif self.phase == DisruptionPhase.RECOVERY:
            mods["_recovery_progress"] = min(
                self._phase_duration / self._recovery_duration, 1.0
            )

        return mods
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/test_generator/test_disruption.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/iter_ation/generator/disruption.py tests/test_generator/test_disruption.py
git commit -m "feat: add disruption risk scoring and cascade phases"
```

---

### Task 8: Simulation Engine

**Files:**
- Create: `src/iter_ation/generator/engine.py`
- Create: `tests/test_generator/test_engine.py`

- [ ] **Step 1: Write tests**

`tests/test_generator/test_engine.py`:
```python
import math
from iter_ation.generator.engine import SimulationEngine


def test_engine_starts_at_nominal():
    engine = SimulationEngine(seed=42)
    state = engine.current_state
    assert abs(state.greenwald_fraction - 0.75) < 0.05
    assert state.sim_time == 0.0


def test_engine_tick_advances_time():
    engine = SimulationEngine(seed=42)
    engine.tick()
    assert engine.current_state.sim_time == 0.001


def test_engine_100_ticks_stays_reasonable():
    engine = SimulationEngine(seed=42)
    for _ in range(100):
        engine.tick()
    state = engine.current_state
    assert 0.5 < state.greenwald_fraction < 1.0
    assert 10 < state.Ip < 20
    assert abs(state.sim_time - 0.1) < 1e-9


def test_engine_greenwald_fraction_is_derived():
    engine = SimulationEngine(seed=42)
    for _ in range(10):
        engine.tick()
    state = engine.current_state
    n_g = state.Ip / (math.pi * 4.0)
    expected_fgw = state.n_e / n_g
    assert abs(state.greenwald_fraction - expected_fgw) < 1e-6


def test_engine_q95_is_derived():
    engine = SimulationEngine(seed=42)
    for _ in range(10):
        engine.tick()
    state = engine.current_state
    expected_q = (5.0 * 4.0 * 1.7 * 5.3) / (6.2 * state.Ip)
    assert abs(state.q95 - expected_q) < 1e-6


def test_engine_beta_n_varies():
    """beta_n should not stay at exactly 1.8 (has noise)."""
    engine = SimulationEngine(seed=42)
    for _ in range(100):
        engine.tick()
    assert engine.current_state.beta_n != 1.8


def test_engine_new_pulse_flag():
    """After a disruption recovery, new_pulse_triggered should be set."""
    engine = SimulationEngine(seed=42)
    engine.cascade.trigger()
    new_pulse = False
    for _ in range(2000):
        state = engine.tick()
        if engine.new_pulse_triggered:
            new_pulse = True
            break
    assert new_pulse
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
pytest tests/test_generator/test_engine.py -v
```

- [ ] **Step 3: Implement engine**

`src/iter_ation/generator/engine.py`:
```python
from __future__ import annotations
import numpy as np
from iter_ation.physics.constants import ITER
from iter_ation.physics.formulas import greenwald_fraction, q95
from iter_ation.physics.parameters import get_parameter
from iter_ation.generator.plasma_state import PlasmaState
from iter_ation.generator.noise import apply_noise, apply_drift, GENERATED_PARAMS
from iter_ation.generator.correlations import apply_correlations
from iter_ation.generator.disruption import (
    compute_risk_score,
    DisruptionCascade,
    DisruptionPhase,
)

DT = 0.001  # 1 ms


class SimulationEngine:
    """Tick-by-tick plasma simulation engine."""

    def __init__(self, seed: int = 0) -> None:
        self._rng = np.random.default_rng(seed)
        self._sim_time: float = 0.0
        self._cascade = DisruptionCascade()
        self.new_pulse_triggered: bool = False

        self._base: dict[str, float] = {
            p.name: p.nominal for p in GENERATED_PARAMS
        }
        self._drift: dict[str, float] = {p.name: 0.0 for p in GENERATED_PARAMS}
        self._current_state = PlasmaState.nominal()

    @property
    def current_state(self) -> PlasmaState:
        return self._current_state

    @property
    def cascade(self) -> DisruptionCascade:
        return self._cascade

    def apply_operator_adjustment(self, param_name: str, delta: float) -> None:
        if param_name in self._base:
            self._base[param_name] += delta

    def tick(self) -> PlasmaState:
        self._sim_time += DT
        self.new_pulse_triggered = False
        prev_phase = self._cascade.phase

        # 1. Drift
        self._drift = apply_drift(self._drift, self._rng, DT)

        # 2. Base + drift
        drifted = {name: self._base[name] + self._drift[name] for name in self._base}

        # 3. Noise
        noisy = apply_noise(drifted, self._rng)

        # 4. Correlations
        noisy = apply_correlations(noisy)

        # 5. Disruption cascade
        if self._cascade.is_active:
            self._cascade.tick(DT)
            mods = self._cascade.get_modifications()
            noisy = self._apply_cascade_mods(noisy, mods)

        # 6. Detect recovery → none transition (new pulse)
        if prev_phase == DisruptionPhase.RECOVERY and self._cascade.phase == DisruptionPhase.NONE:
            self.new_pulse_triggered = True
            self._reset_to_nominal()

        # 7. Derived parameters
        noisy["n_e"] = max(noisy["n_e"], 0.01)
        noisy["Ip"] = max(noisy["Ip"], 0.01)
        fgw = greenwald_fraction(noisy["n_e"], noisy["Ip"], ITER.a)
        q = q95(ITER.a, ITER.kappa, ITER.B_T, ITER.R_0, noisy["Ip"])

        # 8. Clamp
        noisy["Te_core"] = max(noisy["Te_core"], 0.1)
        noisy["Wmhd"] = max(noisy["Wmhd"], 0.0)
        noisy["radiated_fraction"] = max(0.0, min(noisy["radiated_fraction"], 1.0))
        noisy["li"] = max(noisy["li"], 0.1)
        noisy["n1_amplitude"] = max(noisy["n1_amplitude"], 0.0)
        noisy["v_loop"] = max(noisy["v_loop"], 0.0)
        noisy["p_input"] = max(noisy["p_input"], 0.0)
        noisy["beta_n"] = max(noisy["beta_n"], 0.0)

        # 9. Disruption risk check
        if not self._cascade.is_active:
            risk = compute_risk_score(
                greenwald_fraction=fgw,
                radiated_fraction=noisy["radiated_fraction"],
                n1_amplitude=noisy["n1_amplitude"],
                q95=q,
            )
            if self._rng.random() < risk * DT * 10:
                self._cascade.trigger()

        # 10. Build state
        self._current_state = PlasmaState(
            sim_time=self._sim_time,
            greenwald_fraction=fgw,
            n_e=noisy["n_e"],
            Ip=noisy["Ip"],
            q95=q,
            Te_core=noisy["Te_core"],
            Wmhd=noisy["Wmhd"],
            radiated_fraction=noisy["radiated_fraction"],
            li=noisy["li"],
            n1_amplitude=noisy["n1_amplitude"],
            v_loop=noisy["v_loop"],
            beta_n=noisy["beta_n"],
            zcur=noisy["zcur"],
            p_input=noisy["p_input"],
        )

        return self._current_state

    def _reset_to_nominal(self) -> None:
        """Reset base values and drift after recovery."""
        for p in GENERATED_PARAMS:
            self._base[p.name] = p.nominal
            self._drift[p.name] = 0.0

    def _apply_cascade_mods(
        self, values: dict[str, float], mods: dict[str, float]
    ) -> dict[str, float]:
        result = dict(values)
        for key, mod in mods.items():
            if key == "_recovery_progress":
                for name in result:
                    nom = get_parameter(name).nominal
                    result[name] = result[name] + (nom - result[name]) * mod
                continue
            if key.endswith("_add"):
                param_name = key[:-4]
                if param_name in result:
                    result[param_name] += mod
            elif key in result:
                result[key] = result[key] * mod
        return result
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/test_generator/ -v
```

- [ ] **Step 5: Commit**

```bash
git add src/iter_ation/generator/engine.py tests/test_generator/test_engine.py
git commit -m "feat: add simulation engine with correlations and new-pulse detection"
```

---

## Chunk 3: Monitoring

### Task 9: Thresholds & Alerts

**Files:**
- Create: `src/iter_ation/monitoring/__init__.py`
- Create: `src/iter_ation/monitoring/thresholds.py`
- Create: `src/iter_ation/monitoring/alerts.py`
- Create: `tests/test_monitoring/test_thresholds.py`
- Create: `tests/test_monitoring/test_alerts.py`

- [ ] **Step 1: Write tests for thresholds**

`tests/test_monitoring/test_thresholds.py`:
```python
from iter_ation.monitoring.thresholds import evaluate_parameter, AlertLevel


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
    assert evaluate_parameter("Te_core", 14.0) == AlertLevel.WARNING


def test_zcur_abs_above():
    assert evaluate_parameter("zcur", -0.15) == AlertLevel.WARNING


def test_no_threshold_stays_nominal():
    assert evaluate_parameter("n_e", 999.0) == AlertLevel.NOMINAL
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
pytest tests/test_monitoring/test_thresholds.py -v
```

- [ ] **Step 3: Implement thresholds**

`src/iter_ation/monitoring/__init__.py`: empty.

`src/iter_ation/monitoring/thresholds.py`:
```python
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
    param = get_parameter(name)

    if (param.critical_threshold is not None and param.critical_direction is not None):
        if _check_threshold(value, param.critical_threshold, param.critical_direction, param.nominal):
            return AlertLevel.DANGER

    if (param.risk_threshold is not None and param.risk_direction is not None):
        if _check_threshold(value, param.risk_threshold, param.risk_direction, param.nominal):
            return AlertLevel.WARNING

    return AlertLevel.NOMINAL


def evaluate_all(values: dict[str, float]) -> AlertLevel:
    max_level = AlertLevel.NOMINAL
    for name, value in values.items():
        level = evaluate_parameter(name, value)
        if level > max_level:
            max_level = level
    return max_level
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/test_monitoring/test_thresholds.py -v
```

- [ ] **Step 5: Write tests for alert log**

`tests/test_monitoring/test_alerts.py`:
```python
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
```

- [ ] **Step 6: Run tests — expect FAIL**

```bash
pytest tests/test_monitoring/test_alerts.py -v
```

- [ ] **Step 7: Implement alert log**

`src/iter_ation/monitoring/alerts.py`:
```python
from __future__ import annotations
from dataclasses import dataclass
from iter_ation.monitoring.thresholds import AlertLevel


@dataclass(frozen=True)
class AlertEntry:
    sim_time: float
    level: AlertLevel
    triggered_by: dict[str, AlertLevel]
    message: str


def _format_message(level: AlertLevel, triggered_by: dict[str, AlertLevel]) -> str:
    if level == AlertLevel.NOMINAL:
        return "All parameters nominal"
    if level == AlertLevel.DISRUPTION:
        return "DISRUPTION CASCADE IN PROGRESS"
    params = ", ".join(f"{name} [{lvl.name}]" for name, lvl in triggered_by.items())
    return f"{level.name}: {params}"


class AlertLog:
    def __init__(self, max_entries: int = 100) -> None:
        self.entries: list[AlertEntry] = []
        self._max_entries = max_entries
        self._last_level: AlertLevel = AlertLevel.NOMINAL

    def update(
        self, sim_time: float, overall_level: AlertLevel,
        param_levels: dict[str, AlertLevel],
    ) -> AlertEntry | None:
        if overall_level == self._last_level:
            return None

        triggered = {k: v for k, v in param_levels.items() if v > AlertLevel.NOMINAL}
        entry = AlertEntry(
            sim_time=sim_time, level=overall_level,
            triggered_by=triggered, message=_format_message(overall_level, triggered),
        )
        self.entries.append(entry)
        self._last_level = overall_level

        if len(self.entries) > self._max_entries:
            self.entries = self.entries[-self._max_entries:]
        return entry

    def force_disruption(self, sim_time: float) -> AlertEntry:
        entry = AlertEntry(
            sim_time=sim_time, level=AlertLevel.DISRUPTION,
            triggered_by={}, message="DISRUPTION CASCADE IN PROGRESS",
        )
        self.entries.append(entry)
        self._last_level = AlertLevel.DISRUPTION
        return entry
```

- [ ] **Step 8: Run tests — expect PASS**

```bash
pytest tests/test_monitoring/ -v
```

- [ ] **Step 9: Commit**

```bash
git add src/iter_ation/monitoring/ tests/test_monitoring/
git commit -m "feat: add threshold evaluation and alert log"
```

---

### Task 10: Operator Actions

**Files:**
- Create: `src/iter_ation/monitoring/operator.py`
- Create: `tests/test_monitoring/test_operator.py`

- [ ] **Step 1: Write tests**

`tests/test_monitoring/test_operator.py`:
```python
from iter_ation.monitoring.operator import OperatorAction, ACTION_DELTAS


def test_all_basic_actions_in_deltas():
    assert OperatorAction.GAS_UP in ACTION_DELTAS
    assert OperatorAction.GAS_DOWN in ACTION_DELTAS
    assert OperatorAction.POWER_UP in ACTION_DELTAS
    assert OperatorAction.POWER_DOWN in ACTION_DELTAS


def test_spi_and_scram_not_in_deltas():
    """SPI and SCRAM are handled specially, not via simple deltas."""
    assert OperatorAction.SPI not in ACTION_DELTAS
    assert OperatorAction.SCRAM not in ACTION_DELTAS


def test_gas_up_increases_n_e():
    assert ACTION_DELTAS[OperatorAction.GAS_UP]["n_e"] > 0


def test_gas_down_decreases_n_e():
    assert ACTION_DELTAS[OperatorAction.GAS_DOWN]["n_e"] < 0
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
pytest tests/test_monitoring/test_operator.py -v
```

- [ ] **Step 3: Implement operator actions**

`src/iter_ation/monitoring/operator.py`:
```python
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
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/test_monitoring/ -v
```

- [ ] **Step 5: Commit**

```bash
git add src/iter_ation/monitoring/operator.py tests/test_monitoring/test_operator.py
git commit -m "feat: add operator action definitions"
```

---

## Chunk 4: TUI

### Task 11: Theme & Gauge Widget

**Files:**
- Create: `src/iter_ation/tui/__init__.py`
- Create: `src/iter_ation/tui/theme.py`
- Create: `src/iter_ation/tui/widgets/__init__.py`
- Create: `src/iter_ation/tui/widgets/gauge.py`

- [ ] **Step 1: Implement theme**

`src/iter_ation/tui/__init__.py`: empty.
`src/iter_ation/tui/widgets/__init__.py`: empty.

`src/iter_ation/tui/theme.py`:
```python
COLORS = {
    "nominal": "#00cc66",
    "warning": "#ffaa00",
    "danger": "#ff3333",
    "disruption": "#ff0000",
    "background": "#1a1a2e",
    "surface": "#16213e",
    "text": "#e0e0e0",
    "text_dim": "#808080",
    "accent": "#00b4d8",
}
```

- [ ] **Step 2: Implement gauge widget**

`src/iter_ation/tui/widgets/gauge.py`:
```python
from textual.widget import Widget
from textual.reactive import reactive
from iter_ation.monitoring.thresholds import AlertLevel
from iter_ation.tui.theme import COLORS


class Gauge(Widget):
    """Horizontal gauge bar for a single plasma parameter."""

    DEFAULT_CSS = """
    Gauge {
        height: 1;
        width: 1fr;
    }
    """

    value: reactive[float] = reactive(0.0)
    alert_level: reactive[AlertLevel] = reactive(AlertLevel.NOMINAL)

    def __init__(
        self, label: str, unit: str = "",
        min_val: float = 0.0, max_val: float = 1.0, **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._label = label
        self._unit = unit
        self._min_val = min_val
        self._max_val = max_val

    def render(self) -> str:
        width = max(self.size.width - 22, 5)
        fill_ratio = (self.value - self._min_val) / max(self._max_val - self._min_val, 1e-9)
        fill_ratio = max(0.0, min(1.0, fill_ratio))
        filled = int(width * fill_ratio)
        empty = width - filled

        color = COLORS.get(self.alert_level.name.lower(), COLORS["nominal"])
        bar = f"[{color}]{'█' * filled}[/]{'░' * empty}"
        unit_str = f" {self._unit}" if self._unit else ""
        return f" {self._label:<8} {bar} {self.value:>8.3f}{unit_str}"

    def update_value(self, value: float, level: AlertLevel) -> None:
        self.value = value
        self.alert_level = level
```

- [ ] **Step 3: Commit**

```bash
git add src/iter_ation/tui/
git commit -m "feat: add TUI theme and gauge widget"
```

---

### Task 12: Alert Log & Controls Widgets

**Files:**
- Create: `src/iter_ation/tui/widgets/alert_log.py`
- Create: `src/iter_ation/tui/widgets/controls.py`

- [ ] **Step 1: Implement alert log widget**

`src/iter_ation/tui/widgets/alert_log.py`:
```python
from textual.widgets import RichLog
from iter_ation.monitoring.alerts import AlertEntry
from iter_ation.monitoring.thresholds import AlertLevel
from iter_ation.tui.theme import COLORS

_LEVEL_ICONS = {
    AlertLevel.NOMINAL: "[green]●[/]",
    AlertLevel.WARNING: "[yellow]⚠[/]",
    AlertLevel.DANGER: "[red]✖[/]",
    AlertLevel.DISRUPTION: "[bold red blink]◉ DISRUPTION[/]",
}


class AlertLogWidget(RichLog):
    DEFAULT_CSS = """
    AlertLogWidget {
        height: 1fr;
        border: solid $surface;
    }
    """

    def add_alert(self, entry: AlertEntry) -> None:
        icon = _LEVEL_ICONS.get(entry.level, "")
        self.write(f"{icon} [{COLORS['text_dim']}]t={entry.sim_time:.3f}s[/] {entry.message}")
```

- [ ] **Step 2: Implement controls widget**

`src/iter_ation/tui/widgets/controls.py`:
```python
from textual.widgets import Static
from textual.reactive import reactive


class ControlsBar(Static):
    DEFAULT_CSS = """
    ControlsBar {
        dock: bottom;
        height: 2;
        background: $surface;
        padding: 0 1;
    }
    """

    interactive_mode: reactive[bool] = reactive(False)
    paused: reactive[bool] = reactive(False)

    def render(self) -> str:
        mode = "INTER" if self.interactive_mode else "OBS"
        pause_str = " ▶ PAUSED" if self.paused else ""

        line1 = (
            "[dim]\\[↑↓ Gas] [+- Power] [S SPI] [X SCRAM][/]"
            if self.interactive_mode
            else "[dim]Controls disabled in OBS mode[/]"
        )
        line2 = (
            f"[dim]\\[O] Observation  \\[I] Interactive  "
            f"\\[P] Pause  \\[Q] Quit[/]  "
            f"Mode: [bold]{mode}[/]{pause_str}"
        )
        return f"{line1}\n{line2}"
```

- [ ] **Step 3: Commit**

```bash
git add src/iter_ation/tui/widgets/alert_log.py src/iter_ation/tui/widgets/controls.py
git commit -m "feat: add alert log and controls bar widgets"
```

---

### Task 13: Timeline Widget (Plotext)

**Files:**
- Create: `src/iter_ation/tui/widgets/timeline.py`

- [ ] **Step 1: Implement timeline widget**

`src/iter_ation/tui/widgets/timeline.py`:
```python
from __future__ import annotations
from collections import deque
from textual.widget import Widget
from textual.reactive import reactive
from rich.text import Text
from rich.ansi import AnsiDecoder
import plotext as plt


class TimelineWidget(Widget):
    """Scrolling time series plot using plotext."""

    DEFAULT_CSS = """
    TimelineWidget {
        height: 1fr;
        width: 1fr;
    }
    """

    _data_version: reactive[int] = reactive(0)

    def __init__(self, max_points: int = 500, **kwargs) -> None:
        super().__init__(**kwargs)
        self._max_points = max_points
        self._series: dict[str, deque[float]] = {}
        self._times: deque[float] = deque(maxlen=max_points)
        self._decoder = AnsiDecoder()
        self._pulse_markers: list[float] = []

    def add_series(self, name: str) -> None:
        if name not in self._series:
            self._series[name] = deque(maxlen=self._max_points)

    def push(self, sim_time: float, values: dict[str, float]) -> None:
        self._times.append(sim_time)
        for name, series in self._series.items():
            series.append(values.get(name, 0.0))
        self._data_version += 1  # triggers re-render

    def mark_pulse(self, sim_time: float) -> None:
        self._pulse_markers.append(sim_time)

    def render(self) -> Text:
        if len(self._times) < 2:
            return Text("Waiting for data...")

        plt.clf()
        plt.theme("dark")
        plt.plotsize(self.size.width, self.size.height)
        plt.xaxes(1, 0)
        plt.yaxes(1, 0)

        times = list(self._times)
        colors = ["cyan", "yellow", "red", "green", "magenta"]
        for i, (name, series) in enumerate(self._series.items()):
            data = list(series)
            plt.plot(times[:len(data)], data, label=name, color=colors[i % len(colors)])

        for t in self._pulse_markers:
            if t >= times[0]:
                plt.vline(t, "white")

        canvas = plt.build()
        result = Text()
        for i, line in enumerate(self._decoder.decode(canvas)):
            if i > 0:
                result.append("\n")
            result.append(line)
        return result
```

- [ ] **Step 2: Commit**

```bash
git add src/iter_ation/tui/widgets/timeline.py
git commit -m "feat: add plotext-based timeline widget with pulse markers"
```

---

### Task 14: Dashboard Layout & Main App

**Files:**
- Create: `src/iter_ation/tui/dashboard.py`
- Create: `src/iter_ation/tui/app.py`

- [ ] **Step 1: Implement dashboard layout**

`src/iter_ation/tui/dashboard.py`:
```python
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static
from iter_ation.physics.parameters import PARAMETERS
from iter_ation.tui.widgets.gauge import Gauge
from iter_ation.tui.widgets.timeline import TimelineWidget
from iter_ation.tui.widgets.alert_log import AlertLogWidget

_GAUGE_RANGES: dict[str, tuple[float, float]] = {
    "greenwald_fraction": (0.0, 1.5),
    "n_e": (0.0, 2.0),
    "Ip": (0.0, 20.0),
    "q95": (0.0, 6.0),
    "Te_core": (0.0, 30.0),
    "Wmhd": (0.0, 500.0),
    "radiated_fraction": (0.0, 1.0),
    "li": (0.0, 2.0),
    "n1_amplitude": (0.0, 2.0),
    "v_loop": (0.0, 3.0),
    "beta_n": (0.0, 5.0),
    "zcur": (-0.5, 0.5),
    "p_input": (0.0, 80.0),
}


class Dashboard(Static):
    DEFAULT_CSS = """
    Dashboard { height: 1fr; width: 1fr; }
    """

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield TimelineWidget(id="timeline")
            with Vertical(id="right-panel"):
                with Vertical(id="gauges"):
                    for p in PARAMETERS:
                        min_v, max_v = _GAUGE_RANGES.get(p.name, (0.0, 1.0))
                        yield Gauge(
                            label=p.name[:8], unit=p.unit,
                            min_val=min_v, max_val=max_v,
                            id=f"gauge-{p.name}",
                        )
                yield AlertLogWidget(id="alert-log")
```

- [ ] **Step 2: Implement main app**

`src/iter_ation/tui/app.py`:
```python
from __future__ import annotations
import queue
import time
from textual import work
from textual.app import App, ComposeResult
from textual.widgets import Static
from textual.message import Message
from textual.worker import get_current_worker

from iter_ation.generator.engine import SimulationEngine
from iter_ation.generator.disruption import DisruptionPhase
from iter_ation.monitoring.thresholds import evaluate_parameter, evaluate_all, AlertLevel
from iter_ation.monitoring.alerts import AlertLog
from iter_ation.monitoring.operator import OperatorAction, ACTION_DELTAS
from iter_ation.tui.dashboard import Dashboard
from iter_ation.tui.widgets.gauge import Gauge
from iter_ation.tui.widgets.timeline import TimelineWidget
from iter_ation.tui.widgets.alert_log import AlertLogWidget
from iter_ation.tui.widgets.controls import ControlsBar


class PlasmaUpdate(Message):
    def __init__(self, values: dict[str, float], sim_time: float,
                 alert_level: AlertLevel, param_levels: dict[str, AlertLevel],
                 new_pulse: bool) -> None:
        super().__init__()
        self.values = values
        self.sim_time = sim_time
        self.alert_level = alert_level
        self.param_levels = param_levels
        self.new_pulse = new_pulse


class IterApp(App):
    """ITER-ATION Disruption Monitor."""

    CSS = """
    Screen { background: #1a1a2e; }
    #header-bar { dock: top; height: 1; background: #16213e; color: #e0e0e0; text-align: center; }
    #right-panel { width: 40; }
    #gauges { height: 2fr; }
    #timeline { width: 1fr; }
    #alert-log { height: 1fr; }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("p", "toggle_pause", "Pause"),
        ("o", "mode_observation", "Observation"),
        ("i", "mode_interactive", "Interactive"),
        ("up", "gas_up", "Gas +"),
        ("down", "gas_down", "Gas -"),
        ("+", "power_up", "Power +"),
        ("-", "power_down", "Power -"),
        ("s", "spi", "SPI"),
        ("x", "scram", "SCRAM"),
    ]

    def __init__(self, speed: int = 100, interactive: bool = False) -> None:
        super().__init__()
        self._speed = speed
        self._interactive = interactive
        self._paused = False
        self._action_queue: queue.Queue[OperatorAction] = queue.Queue()
        self._alert_log = AlertLog()
        self._engine = SimulationEngine()

    def compose(self) -> ComposeResult:
        yield Static(
            f"ITER-ATION -- Disruption Monitor    t=0.000s  x{self._speed}",
            id="header-bar",
        )
        yield Dashboard()
        yield ControlsBar(id="controls")

    def on_mount(self) -> None:
        timeline = self.query_one("#timeline", TimelineWidget)
        timeline.add_series("greenwald_fraction")
        timeline.add_series("radiated_fraction")
        timeline.add_series("q95")
        self.query_one("#controls", ControlsBar).interactive_mode = self._interactive
        self._run_simulation()

    @work(thread=True)
    def _run_simulation(self) -> None:
        worker = get_current_worker()
        ticks_per_frame = max(1, self._speed // 10)
        frame_interval = 1.0 / 30

        while not worker.is_cancelled:
            if self._paused:
                time.sleep(0.05)
                continue

            while not self._action_queue.empty():
                self._handle_action(self._action_queue.get_nowait())

            new_pulse = False
            for _ in range(ticks_per_frame):
                state = self._engine.tick()
                if self._engine.new_pulse_triggered:
                    new_pulse = True

            values = state.values()
            param_levels = {name: evaluate_parameter(name, val) for name, val in values.items()}

            if self._engine.cascade.is_active and self._engine.cascade.phase != DisruptionPhase.RECOVERY:
                overall = AlertLevel.DISRUPTION
            else:
                overall = evaluate_all(values)

            self.post_message(PlasmaUpdate(
                values=values, sim_time=state.sim_time,
                alert_level=overall, param_levels=param_levels,
                new_pulse=new_pulse,
            ))
            time.sleep(frame_interval)

    def on_plasma_update(self, event: PlasmaUpdate) -> None:
        self.query_one("#header-bar", Static).update(
            f"ITER-ATION -- Disruption Monitor    t={event.sim_time:.3f}s  x{self._speed}"
        )

        for name, value in event.values.items():
            try:
                gauge = self.query_one(f"#gauge-{name}", Gauge)
                gauge.update_value(value, event.param_levels.get(name, AlertLevel.NOMINAL))
            except Exception:
                pass

        timeline = self.query_one("#timeline", TimelineWidget)
        timeline.push(event.sim_time, event.values)

        if event.new_pulse:
            timeline.mark_pulse(event.sim_time)

        entry = self._alert_log.update(event.sim_time, event.alert_level, event.param_levels)
        if entry:
            self.query_one("#alert-log", AlertLogWidget).add_alert(entry)

    def _handle_action(self, action: OperatorAction) -> None:
        engine = self._engine
        if action == OperatorAction.SPI:
            engine.apply_operator_adjustment("n_e", engine.current_state.n_e * 2)
            engine.apply_operator_adjustment("Te_core", -engine.current_state.Te_core * 0.8)
            engine.apply_operator_adjustment("radiated_fraction", 0.45)
            engine.apply_operator_adjustment("v_loop", 1.5)
        elif action == OperatorAction.SCRAM:
            engine.apply_operator_adjustment("Ip", -engine.current_state.Ip * 0.95)
        elif action in ACTION_DELTAS:
            for param, delta in ACTION_DELTAS[action].items():
                engine.apply_operator_adjustment(param, delta)

    def action_toggle_pause(self) -> None:
        self._paused = not self._paused
        self.query_one("#controls", ControlsBar).paused = self._paused

    def action_mode_observation(self) -> None:
        self._interactive = False
        self.query_one("#controls", ControlsBar).interactive_mode = False

    def action_mode_interactive(self) -> None:
        self._interactive = True
        self.query_one("#controls", ControlsBar).interactive_mode = True

    def action_gas_up(self) -> None:
        if self._interactive:
            self._action_queue.put(OperatorAction.GAS_UP)

    def action_gas_down(self) -> None:
        if self._interactive:
            self._action_queue.put(OperatorAction.GAS_DOWN)

    def action_power_up(self) -> None:
        if self._interactive:
            self._action_queue.put(OperatorAction.POWER_UP)

    def action_power_down(self) -> None:
        if self._interactive:
            self._action_queue.put(OperatorAction.POWER_DOWN)

    def action_spi(self) -> None:
        if self._interactive:
            self._action_queue.put(OperatorAction.SPI)

    def action_scram(self) -> None:
        if self._interactive:
            self._action_queue.put(OperatorAction.SCRAM)
```

- [ ] **Step 3: Commit**

```bash
git add src/iter_ation/tui/dashboard.py src/iter_ation/tui/app.py
git commit -m "feat: add dashboard layout and main Textual app with SPI/SCRAM"
```

---

### Task 15: CLI Entry Point

**Files:**
- Create: `src/iter_ation/cli.py`

- [ ] **Step 1: Implement CLI**

`src/iter_ation/cli.py`:
```python
import argparse
from iter_ation.tui.app import IterApp


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="iter-ation",
        description="ITER-ATION: Tokamak Disruption Monitor",
    )
    parser.add_argument(
        "--mode", choices=["observation", "interactive"],
        default="observation",
        help="Start in observation or interactive mode (default: observation)",
    )
    parser.add_argument(
        "--speed", type=int, default=100,
        help="Simulation speed multiplier (default: 100)",
    )
    args = parser.parse_args()
    IterApp(speed=args.speed, interactive=(args.mode == "interactive")).run()
```

- [ ] **Step 2: Verify help**

```bash
python -m iter_ation --help
```

Expected: shows help with `--mode` and `--speed`.

- [ ] **Step 3: Commit**

```bash
git add src/iter_ation/cli.py
git commit -m "feat: add CLI argument parsing and entry point"
```

---

### Task 16: Integration — Full Test Suite & Smoke Test

- [ ] **Step 1: Run all tests**

```bash
pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 2: Smoke test observation mode**

```bash
python -m iter_ation --speed 1000
```

Expected: TUI launches, gauges update, timeline scrolls. Press `Q` to quit.

- [ ] **Step 3: Smoke test interactive mode**

```bash
python -m iter_ation --mode interactive --speed 100
```

Expected: press `I` for interactive, `↑`/`↓` adjust gas, `S` triggers SPI. Press `Q` to quit.

- [ ] **Step 4: Fix any integration issues and commit**

```bash
pytest tests/ -v && git add -A && git commit -m "fix: integration fixes from smoke testing"
```
