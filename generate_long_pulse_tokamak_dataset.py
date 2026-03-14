"""Generate a synthetic ITER long-pulse dataset with a Greenwald-driven disruption.

Produces a CSV with all 13 monitored parameters at 1 kHz over a 3-minute pulse.
The disruption is triggered by density approaching the Greenwald limit (fGW → 1),
with proper cascade phases: precursors → thermal quench → current quench + VDE.

Uses the project's physics module for constants and formulas.
"""
import math
import numpy as np
import pandas as pd

from iter_ation.physics.constants import ITER
from iter_ation.physics.formulas import greenwald_density, greenwald_fraction, q95
from iter_ation.physics.parameters import PARAMETERS, get_parameter

print("Generating ITER 3-minute long pulse with disruption... Please wait.")

# ---------------------------------------------------------
# 1. PULSE PARAMETERS
# ---------------------------------------------------------
duration_seconds = 180
sampling_rate = 1000  # 1 kHz = 1 sample per ms
num_rows = duration_seconds * sampling_rate  # 180,000
rng = np.random.default_rng(42)

# Time axis in seconds
time_s = np.linspace(0, duration_seconds, num_rows, endpoint=False)

# Greenwald density for ITER: n_G = Ip / (pi * a^2)
n_G = greenwald_density(Ip=15.0, a=ITER.a)  # ~1.194 x10^20 m^-3

# ---------------------------------------------------------
# 2. STABLE PHASE (first 179.2 seconds)
#    All parameters at ITER nominal with realistic noise
# ---------------------------------------------------------

def gen_stable(nominal: float, sigma: float, n: int) -> np.ndarray:
    """Generate stable signal with Gaussian noise around nominal."""
    return rng.normal(nominal, sigma, n)


# Direct parameters (with noise from spec)
ip_MA       = gen_stable(15.0,  get_parameter("Ip").effective_sigma, num_rows)
n_e         = gen_stable(0.9,   get_parameter("n_e").effective_sigma, num_rows)
Te_core     = gen_stable(20.0,  get_parameter("Te_core").effective_sigma, num_rows)
Wmhd        = gen_stable(350.0, get_parameter("Wmhd").effective_sigma, num_rows)
rad_frac    = gen_stable(0.5,   get_parameter("radiated_fraction").effective_sigma, num_rows)
li          = gen_stable(0.85,  get_parameter("li").effective_sigma, num_rows)
n1_amp      = np.abs(gen_stable(0.05, get_parameter("n1_amplitude").effective_sigma, num_rows))
v_loop      = gen_stable(0.2,   get_parameter("v_loop").effective_sigma, num_rows)
beta_n      = gen_stable(1.8,   get_parameter("beta_n").effective_sigma, num_rows)
zcur        = gen_stable(0.0,   get_parameter("zcur").effective_sigma, num_rows)
p_input     = gen_stable(50.0,  get_parameter("p_input").effective_sigma, num_rows)

# Add slow drift to density (the driver of the disruption)
# n_e drifts upward over the pulse, approaching the Greenwald limit
drift_start = 60_000   # drift begins at t=60s
drift_end = 179_200     # disruption triggers at t=179.2s
drift_window = drift_end - drift_start
n_e[drift_start:drift_end] += np.linspace(0, 0.25, drift_window)
# n_e goes from 0.9 → ~1.15, so fGW goes from 0.75 → ~0.96

# Correlations during stable phase:
# n_e ↑ → radiated_fraction ↑
n_e_delta = (n_e - 0.9) / 0.9
rad_frac += n_e_delta * 0.15  # coupling factor
# radiated_fraction ↑ → Te_core ↓
rad_delta = (rad_frac - 0.5) / 0.5
Te_core += rad_delta * (-0.4) * 20.0  # ~-8 keV at max radiation
# Te_core ↓ → Wmhd ↓
te_delta = (Te_core - 20.0) / 20.0
Wmhd += te_delta * 0.5 * 350.0

# ---------------------------------------------------------
# 3. THE DISRUPTION (t=179.2s to t=180.0s = 800 ms)
#    Driven by Greenwald fraction exceeding limit
# ---------------------------------------------------------

# Phase timing (in samples = ms)
t_precursor_start = 179_200  # fGW ~0.96, precursors begin
t_tq_start = 179_500         # thermal quench at t=179.5s (300 ms of precursors)
t_cq_start = 179_502         # TQ lasts 2 ms
t_end_cq = 179_600           # CQ lasts ~100 ms

# --- PRECURSORS (300 ms): n1 grows, li rises, rad_frac climbs ---
prec_len = t_tq_start - t_precursor_start  # 300 ms
t_prec = np.arange(prec_len)

# n1_amplitude: exponential growth (locked mode forming)
n1_growth = 0.05 * np.exp(t_prec / prec_len * 6)  # grows to ~0.05 * e^6 ≈ 20
n1_amp[t_precursor_start:t_tq_start] = np.minimum(n1_growth, 2.0)

# li increases (current profile peaking)
li[t_precursor_start:t_tq_start] += np.linspace(0, 0.5, prec_len)
# li goes from 0.85 → ~1.35

# radiated_fraction climbs toward 0.9
rad_frac[t_precursor_start:t_tq_start] += np.linspace(0, 0.35, prec_len)

# Density keeps rising (past Greenwald limit)
n_e[t_precursor_start:t_tq_start] += np.linspace(0, 0.1, prec_len)
# n_e reaches ~1.25, fGW ~1.05

# Te_core starts dropping (confinement degradation)
Te_core[t_precursor_start:t_tq_start] -= np.linspace(0, 5.0, prec_len)

# v_loop starts fluctuating
v_loop[t_precursor_start:t_tq_start] += rng.normal(0, 0.1, prec_len)

# --- THERMAL QUENCH (2 ms): Te crashes, Wmhd collapses, v_loop spikes ---
tq_len = t_cq_start - t_tq_start  # 2 ms
tq_progress = np.linspace(0, 1, tq_len)

Te_core[t_tq_start:t_cq_start] = 20.0 * (1 - 0.9 * tq_progress)  # drops to 2 keV
Wmhd[t_tq_start:t_cq_start] = 350.0 * (1 - 0.9 * tq_progress)    # drops to 35 MJ
v_loop[t_tq_start:t_cq_start] = 0.2 + 2.5 * tq_progress           # spikes to 2.7 V
rad_frac[t_tq_start:t_cq_start] = 0.95                             # max radiation
n1_amp[t_tq_start:t_cq_start] = 2.0                                # saturated

# --- CURRENT QUENCH + VDE (100 ms): Ip crashes, zcur drifts ---
cq_len = t_end_cq - t_cq_start  # 100 ms
cq_progress = np.linspace(0, 1, cq_len)

ip_MA[t_cq_start:t_end_cq] = 15.0 * (1 - cq_progress)      # 15 MA → 0
zcur[t_cq_start:t_end_cq] = 0.3 * cq_progress               # VDE: vertical drift to 0.3 m
Te_core[t_cq_start:t_end_cq] = 2.0 * (1 - 0.5 * cq_progress)  # continues dropping
Wmhd[t_cq_start:t_end_cq] = 35.0 * (1 - cq_progress)        # → 0
v_loop[t_cq_start:t_end_cq] = 2.7 * (1 - cq_progress)       # decays
rad_frac[t_cq_start:t_end_cq] = 0.95 - 0.3 * cq_progress    # chaotic
n1_amp[t_cq_start:t_end_cq] = 2.0 * (1 - cq_progress)       # decays with current
beta_n[t_cq_start:t_end_cq] = 1.8 * (1 - cq_progress)       # drops with pressure
p_input[t_cq_start:t_end_cq] = 50.0 * (1 - 0.5 * cq_progress)  # heating trips

# Post-CQ (last 400 ms): plasma is dead
post_start = t_end_cq
ip_MA[post_start:] = rng.normal(0.1, 0.05, num_rows - post_start)
Te_core[post_start:] = rng.normal(0.5, 0.1, num_rows - post_start)
Wmhd[post_start:] = 0.0
v_loop[post_start:] = rng.normal(0.0, 0.05, num_rows - post_start)
n1_amp[post_start:] = rng.normal(0.0, 0.01, num_rows - post_start)
zcur[post_start:] = rng.normal(0.3, 0.02, num_rows - post_start)
rad_frac[post_start:] = rng.normal(0.1, 0.05, num_rows - post_start)
beta_n[post_start:] = 0.0
p_input[post_start:] = 0.0

# ---------------------------------------------------------
# 4. DERIVED PARAMETERS
# ---------------------------------------------------------

# Clamp values to physical bounds
ip_MA = np.clip(ip_MA, 0.0, None)
n_e = np.clip(n_e, 0.01, None)
Te_core = np.clip(Te_core, 0.0, None)
Wmhd = np.clip(Wmhd, 0.0, None)
rad_frac = np.clip(rad_frac, 0.0, 1.0)
li = np.clip(li, 0.1, None)
n1_amp = np.clip(n1_amp, 0.0, None)
v_loop = np.clip(v_loop, 0.0, None)
beta_n = np.clip(beta_n, 0.0, None)
p_input = np.clip(p_input, 0.0, None)

# Greenwald fraction: fGW = n_e / n_G, where n_G depends on Ip
fGW = np.zeros(num_rows)
for i in range(num_rows):
    if ip_MA[i] > 0.01:
        fGW[i] = greenwald_fraction(n_e[i], ip_MA[i], ITER.a)
    else:
        fGW[i] = 0.0

# q95 = q_cyl * (li_ref / li), coupled to both Ip and li
q95_arr = np.zeros(num_rows)
li_ref = get_parameter("li").nominal  # 0.85
for i in range(num_rows):
    if ip_MA[i] > 0.01:
        q95_arr[i] = q95(Ip=ip_MA[i], li=li[i], li_ref=li_ref)
    else:
        q95_arr[i] = 0.0

# ---------------------------------------------------------
# 5. LABELING FOR MACHINE LEARNING
#    4 levels matching our monitoring system:
#    0 = NOMINAL, 1 = WARNING, 2 = DANGER, 3 = DISRUPTION
# ---------------------------------------------------------
alert_level = np.zeros(num_rows, dtype=int)

for i in range(num_rows):
    level = 0

    # Greenwald fraction (central metric)
    if fGW[i] > 1.0:
        level = max(level, 2)
    elif fGW[i] > 0.85:
        level = max(level, 1)

    # q95
    if q95_arr[i] > 0 and q95_arr[i] < 2.0:
        level = max(level, 2)
    elif q95_arr[i] > 0 and q95_arr[i] < 2.5:
        level = max(level, 1)

    # radiated_fraction
    if rad_frac[i] > 0.9:
        level = max(level, 2)
    elif rad_frac[i] > 0.7:
        level = max(level, 1)

    # n1_amplitude (locked mode)
    if n1_amp[i] > 1.0:
        level = max(level, 2)
    elif n1_amp[i] > 0.5:
        level = max(level, 1)

    # li
    if li[i] > 1.4:
        level = max(level, 2)
    elif li[i] > 1.2:
        level = max(level, 1)

    # |zcur|
    if abs(zcur[i]) > 0.2:
        level = max(level, 2)
    elif abs(zcur[i]) > 0.1:
        level = max(level, 1)

    # v_loop spike
    if v_loop[i] > 1.0:
        level = max(level, 2)

    # Te_core (drop % vs nominal 20 keV)
    te_drop = (20.0 - Te_core[i]) / 20.0
    if te_drop > 0.50:
        level = max(level, 2)
    elif te_drop > 0.30:
        level = max(level, 1)

    # Wmhd (drop % vs nominal 350 MJ)
    wmhd_drop = (350.0 - Wmhd[i]) / 350.0
    if wmhd_drop > 0.40:
        level = max(level, 2)
    elif wmhd_drop > 0.20:
        level = max(level, 1)

    # Ip (drop % vs nominal 15 MA)
    ip_drop = (15.0 - ip_MA[i]) / 15.0
    if ip_drop > 0.20:
        level = max(level, 2)

    # p_input (drop % vs nominal 50 MW)
    p_drop = (50.0 - p_input[i]) / 50.0
    if p_drop > 0.50:
        level = max(level, 2)
    elif p_drop > 0.30:
        level = max(level, 1)

    # beta_n
    if beta_n[i] > 3.5:
        level = max(level, 2)
    elif beta_n[i] > 2.8:
        level = max(level, 1)

    alert_level[i] = level

# Override to DISRUPTION (3) during active cascade phases
alert_level[t_tq_start:] = np.maximum(alert_level[t_tq_start:], 3)

# ---------------------------------------------------------
# 6. BUILD DATAFRAME AND EXPORT
# ---------------------------------------------------------
df = pd.DataFrame({
    "time_s": time_s,
    "greenwald_fraction": fGW,
    "n_e": n_e,
    "Ip": ip_MA,
    "q95": q95_arr,
    "Te_core": Te_core,
    "Wmhd": Wmhd,
    "radiated_fraction": rad_frac,
    "li": li,
    "n1_amplitude": n1_amp,
    "v_loop": v_loop,
    "beta_n": beta_n,
    "zcur": zcur,
    "p_input": p_input,
    "alert_level": alert_level,
})

df.to_csv("long_pulse_iter.csv", index=False)

# Summary
n_nominal = int((alert_level == 0).sum())
n_warning = int((alert_level == 1).sum())
n_danger = int((alert_level == 2).sum())
n_disruption = int((alert_level == 3).sum())

print(f"Done! 'long_pulse_iter.csv' created — {num_rows:,} rows, {len(df.columns)} columns.")
print(f"  NOMINAL:    {n_nominal:>7,} samples ({n_nominal/num_rows*100:.1f}%)")
print(f"  WARNING:    {n_warning:>7,} samples ({n_warning/num_rows*100:.1f}%)")
print(f"  DANGER:     {n_danger:>7,} samples ({n_danger/num_rows*100:.1f}%)")
print(f"  DISRUPTION: {n_disruption:>7,} samples ({n_disruption/num_rows*100:.1f}%)")
