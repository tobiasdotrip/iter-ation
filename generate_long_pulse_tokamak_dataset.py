import pandas as pd
import numpy as np

print("Generating the 3-minute long pulse... Please wait.")

# ---------------------------------------------------------
# 1. LONG PULSE PARAMETERS
# ---------------------------------------------------------
duration_seconds = 180 # 3 minutes of plasma
sampling_rate = 1000 # 1 sample per millisecond (1 kHz)
num_rows = duration_seconds * sampling_rate # 180,000 ms

# Create the time axis

# ---------------------------------------------------------
# 2. STABLE PHASE GENERATION (The first 179.5 seconds)
# ---------------------------------------------------------
# Generate constant signals with realistic background noise (Gaussian noise)
ip_MA = np.random.normal(2.0, 0.01, num_rows)     # Stable plasma current at 2 MA
mirnov_V = np.random.normal(0, 0.05, num_rows)    # Magnetic background noise
bolo_MW = np.random.normal(5.0, 0.1, num_rows)    # Stable radiated power
dens_e19 = np.random.normal(4.0, 0.05, num_rows)  # Stable density
disruption_label = np.zeros(num_rows, dtype=int)  # 0 = Normal state

# ---------------------------------------------------------
# 3. THE DISRUPTION (The last 500 milliseconds)
# ---------------------------------------------------------
# This is where everything goes wrong (at t = 179,500 ms)
t_problem_start = num_rows - 500
t_warning = num_rows - 100 # We want the AI to trigger the alarm 100ms before the end
t_crash = num_rows - 20    # The current quench starts 20ms before the absolute end

# Precursors (density rises, radiation spikes, Mirnov oscillates)
precursor_window = t_crash - t_problem_start
dens_e19[t_problem_start:t_crash] += np.linspace(0, 3.0, precursor_window)
bolo_MW[t_problem_start:t_crash] += np.linspace(0, 25.0, precursor_window)

# Mirnov signal goes out of control (growing instability)
oscillations = np.sin(np.arange(precursor_window) * 0.5) * np.linspace(0, 3.0, precursor_window)
mirnov_V[t_problem_start:t_crash] += oscillations

# The Crash (Current Quench)
crash_window = num_rows - t_crash
ip_MA[t_crash:] = np.linspace(2.0, 0.1, crash_window)
bolo_MW[t_crash:] = np.random.normal(20, 5, crash_window) # Chaotic radiation

# ---------------------------------------------------------
# 4. LABELING FOR MACHINE LEARNING
# ---------------------------------------------------------
# Indicate that the critical zone (to be predicted) starts at t_warning
disruption_label[t_warning:] = 1


df_long_pulse = pd.DataFrame({
    'ip_MA': ip_MA,
    'mirnov_V': mirnov_V,
    'bolo_MW': bolo_MW,
    'dens_e19': dens_e19,
    'disruption_label': disruption_label
})

# Write the file to the hard drive
df_long_pulse.to_csv('long_pulse_tokamak.csv', index=False)

print(f"Success! File 'long_pulse_tokamak.csv' created with {num_rows} rows.")
print(f"Estimated file size: ~10-15 MB.")