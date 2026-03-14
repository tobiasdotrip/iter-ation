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

        # 6. Detect recovery -> none transition (new pulse)
        if prev_phase == DisruptionPhase.RECOVERY and self._cascade.phase == DisruptionPhase.NONE:
            self.new_pulse_triggered = True
            self._reset_to_nominal()

        # 7. Clamp
        noisy["n_e"] = max(noisy["n_e"], 0.01)
        noisy["Ip"] = max(noisy["Ip"], 0.01)
        noisy["Te_core"] = max(noisy["Te_core"], 0.1)
        noisy["Wmhd"] = max(noisy["Wmhd"], 0.0)
        noisy["radiated_fraction"] = max(0.0, min(noisy["radiated_fraction"], 1.0))
        noisy["li"] = max(noisy["li"], 0.1)
        noisy["n1_amplitude"] = max(noisy["n1_amplitude"], 0.0)
        noisy["v_loop"] = max(noisy["v_loop"], 0.0)
        noisy["p_input"] = max(noisy["p_input"], 0.0)
        noisy["beta_n"] = max(noisy["beta_n"], 0.0)

        # 8. Derived parameters
        fgw = greenwald_fraction(noisy["n_e"], noisy["Ip"], ITER.a)
        q = q95(Ip=noisy["Ip"], li=noisy["li"])

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
