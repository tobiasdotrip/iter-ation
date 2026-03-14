"""
Simulation Layer: Isolated Scenarios Generator for ITER-ATION Disruption Monitor.

4 scénarios ISOLÉS — aucun effet de cascade.
Chaque scénario modifie UNE seule variable primaire,
l'IA doit détecter l'anomalie sur la grandeur dérivée correspondante.

Scénario 1 (Greenwald) : n_e ↑  →  greenwald_fraction ↑
Scénario 2 (Beta)       : Wmhd ↑ →  beta_n ↑
Scénario 3 (q95)        : li ↑  →  q95 ↓
Scénario 4 (tau_E)      : tau_E chutera via dégradation du confinement → Wmhd ↓
"""
import time
import threading
import numpy as np
from typing import Callable, Optional

from physics.models import (
    calc_greenwald_fraction,
    calc_beta_n,
    calc_q95,
    calc_tau_E,
)


class TokamakState:
    """État instantané du plasma (1 snapshot par tick)."""

    def __init__(self):
        # --- Variables primaires simulées ---
        self.n_e     = 0.9    # Densité (10²⁰ m⁻³)
        self.Ip      = 15.0   # Courant plasma (MA)
        self.li      = 0.85   # Inductance interne (sans dim.)
        self.Wmhd    = 350.0  # Énergie magnétohydrodynamique (MJ)
        self.p_input = 50.0   # Puissance de chauffage (MW)
        self.p_rad   = 25.0   # Puissance rayonnée (MW)

        # --- Grandeurs dérivées (calculées chaque tick) ---
        self.greenwald_fraction = 0.0
        self.beta_n             = 0.0
        self.q95                = 0.0
        self.tau_E              = 0.0

        self.update_derived()

    def update_derived(self):
        """Recalcule les grandeurs dérivées à partir des variables primaires."""
        self.greenwald_fraction = calc_greenwald_fraction(self.n_e, self.Ip)
        self.beta_n             = calc_beta_n(self.Wmhd, self.Ip)
        self.q95                = calc_q95(self.li)
        self.tau_E              = calc_tau_E(self.Wmhd, self.p_input)


class GeneratorMode:
    STABLE                = 0
    SCENARIO_1_GREENWALD  = 1
    SCENARIO_2_BETA       = 2
    SCENARIO_3_Q95        = 3
    SCENARIO_4_TAUE       = 4


class TokamakGenerator:
    """
    Génère des données synthétiques à un rythme régulier (ticks).

    En mode STABLE : toutes les variables oscillent autour de leurs valeurs nominales.
    En mode SCÉNARIO N : une seule variable primaire est "poussée" vers la zone rouge.
    Quand l'IA envoie la bonne commande, le générateur annule l'anomalie.
    """

    # Valeurs nominales
    NOMINAL = {
        "n_e":     0.9,
        "Wmhd":    350.0,
        "li":      0.85,
        "Ip":      15.0,
        "p_input": 50.0,
        "p_rad":   25.0,
    }

    # Bruit gaussien (sigma) par variable primaire
    SIGMA = {
        "n_e":     0.005,
        "Wmhd":    1.5,
        "li":      0.003,
        "Ip":      0.015,
        "p_input": 0.05,
        "p_rad":   0.25,
    }

    # Valeurs cible lors du déclenchement d'un scénario
    SCENARIO_TARGETS = {
        GeneratorMode.SCENARIO_1_GREENWALD: {"n_e":  1.6},    # fGW → ~1.34 (bien au-dessus de 0.8)
        GeneratorMode.SCENARIO_2_BETA:      {"Wmhd": 600.0},  # beta_n → ~3.1 (> 2.8)
        GeneratorMode.SCENARIO_3_Q95:       {"li":   1.55},   # q95 → ~1.70 (< 2.0)
        GeneratorMode.SCENARIO_4_TAUE:      {},                # Géré spécialement via tau_E_factor
    }

    def __init__(self, tick_rate_hz: int = 10):
        self._tick_rate  = tick_rate_hz
        self._sleep_time = 1.0 / tick_rate_hz
        self._running    = False
        self._thread     = None
        self._rng        = np.random.default_rng()

        self.state = TokamakState()
        self.mode  = GeneratorMode.STABLE

        # Facteur de dégradation du confinement (Scénario 4)
        # 1.0 = normal, ↓ = fuite thermique
        self._tau_E_factor = 1.0

        # Callback déclenché à chaque tick
        self.on_tick: Optional[Callable[[TokamakState], None]] = None

    # ------------------------------------------------------------------
    # Contrôle de session
    # ------------------------------------------------------------------
    def start(self):
        if not self._running:
            self._running = True
            self._thread  = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()

    def set_scenario(self, mode: int):
        """Déclenche un nouveau scénario (remet les variables primaires au nominal d'abord)."""
        self.mode = mode
        # Optionnel : reset du facteur tau_E
        if mode == GeneratorMode.SCENARIO_4_TAUE:
            self._tau_E_factor = 1.0  # part du nominal, descendra dans la loop

    # ------------------------------------------------------------------
    # Actions de l'Agent IA  →  résolution du scénario actif
    # ------------------------------------------------------------------
    def apply_ai_action(self, action: str) -> bool:
        """
        Applique la commande de l'IA.
        Si la commande correspond au scénario actif → scénario annulé → retour stable.
        Retourne True si le scénario a été résolu.
        """
        resolved = False
        if action == "REDUCE_GAS"   and self.mode == GeneratorMode.SCENARIO_1_GREENWALD:
            resolved = True
        elif action == "REDUCE_HEAT" and self.mode == GeneratorMode.SCENARIO_2_BETA:
            resolved = True
        elif action == "ADJUST_COILS" and self.mode == GeneratorMode.SCENARIO_3_Q95:
            resolved = True
        elif action == "INCREASE_HEAT" and self.mode == GeneratorMode.SCENARIO_4_TAUE:
            resolved = True
        elif action == "EMERGENCY_SPI":
            resolved = True  # Joker : résout tout

        if resolved:
            self.mode          = GeneratorMode.STABLE
            self._tau_E_factor = 1.0  # reset fuite thermique

        return resolved

    # ------------------------------------------------------------------
    # Boucle principale (thread de fond)
    # ------------------------------------------------------------------
    def _loop(self):
        while self._running:
            self._tick()
            time.sleep(self._sleep_time)

    def _tick(self):
        """Un pas de simulation : convergence vers la cible + bruit + dérivées."""
        alpha = 0.05  # vitesse de convergence vers la cible (entre 0 et 1)

        # --- Cibles par défaut : nominal ---
        target_n_e  = self.NOMINAL["n_e"]
        target_Wmhd = self.NOMINAL["Wmhd"]
        target_li   = self.NOMINAL["li"]

        # --- Cibles du scénario actif ---
        scenario_targets = self.SCENARIO_TARGETS.get(self.mode, {})
        target_n_e  = scenario_targets.get("n_e",  target_n_e)
        target_Wmhd = scenario_targets.get("Wmhd", target_Wmhd)
        target_li   = scenario_targets.get("li",   target_li)

        # --- Mise à jour des variables primaires (convergence + bruit) ---
        s = self.state

        s.n_e  += (target_n_e  - s.n_e)  * alpha + self._rng.normal(0, self.SIGMA["n_e"])
        s.li   += (target_li   - s.li)   * alpha + self._rng.normal(0, self.SIGMA["li"])
        s.Ip   += (self.NOMINAL["Ip"]    - s.Ip)   * alpha + self._rng.normal(0, self.SIGMA["Ip"])
        s.p_rad += (self.NOMINAL["p_rad"] - s.p_rad) * alpha + self._rng.normal(0, self.SIGMA["p_rad"])

        # Wmhd : en Scénario 4, l'énergie suit la balance thermique dégradée
        if self.mode == GeneratorMode.SCENARIO_4_TAUE:
            # Dégradation progressive du confinement
            self._tau_E_factor = max(0.4, self._tau_E_factor - 0.003)
            # Cible Wmhd selon la balance : W_eq = P_input × τE_degradé
            tau_E_degraded = self.NOMINAL["Wmhd"] / self.NOMINAL["p_input"] * self._tau_E_factor  # ~7s×factor
            target_Wmhd = s.p_input * tau_E_degraded
        s.Wmhd += (target_Wmhd - s.Wmhd) * alpha + self._rng.normal(0, self.SIGMA["Wmhd"])

        # --- Clamp physique ---
        s.n_e     = max(0.01, s.n_e)
        s.li      = max(0.1,  s.li)
        s.Ip      = max(0.1,  s.Ip)
        s.Wmhd    = max(0.0,  s.Wmhd)
        s.p_input = self.NOMINAL["p_input"]  # Fixe (contrôlé par opérateur)
        s.p_rad   = max(0.0,  s.p_rad)

        # --- Grandeurs dérivées (formules du document) ---
        s.update_derived()

        # --- Notification de l'interface ---
        if self.on_tick:
            self.on_tick(s)
