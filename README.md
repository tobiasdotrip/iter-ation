# ITER-ation

**ITER-ation** is an AI-powered disruption monitor for nuclear fusion reactors. It simulates and monitors the plasma inside a Tokamak in real time, using **Google Gemini** as an autonomous operator to prevent disruptions.

Built during the **Google Antigravity Hackathon**.

## The Problem

In a fusion reactor, the plasma can become unstable in milliseconds. Humans are too slow to react. Traditional control software is too rigid to handle the complexity of plasma dynamics.

## Our Solution: The Agentic Loop

We built an autonomous AI operator that runs in a continuous loop:

1. **Watch** — A physics engine generates realistic plasma data (density, current, temperature, radial profiles) based on ITER-scale parameters.
2. **Think** — Gemini analyzes the plasma state, evaluates proximity to stability limits (Greenwald, beta, q-profile), and decides on corrective actions.
3. **Act** — The AI sends control commands (adjust heating power, modify magnetic field, trigger emergency shutdown) that feed back into the simulation.

## Physics

The simulation uses real parameters from **ITER**, the world's largest fusion project:

- **Major Radius:** 6.2 m
- **Minor Radius:** 2.0 m
- **Magnetic Field:** 5.3 T

Key stability limits tracked:
- **Greenwald Limit** — density ceiling based on plasma current ($n_G = I_p / \pi a^2$)
- **Beta Limit** — ratio of plasma pressure to magnetic pressure
- **Safety Factor (q)** — MHD stability threshold

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Operator | Google Gemini |
| Terminal UI | Textual |
| Charts | plotext |
| Physics | numpy |
| Platform | Google Antigravity |

## How to Run

```bash
git clone git@github.com:tobiasdotrip/iter-ation.git
cd iter-ation
pip install -e .
iter-ation
```

## The Team

Built by 3 students from **42 Paris** and 1 student from **Oteria Cyber School**.
