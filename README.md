# ITER-ation

**ITER-ation** is an AI-powered control system for nuclear fusion. It monitors the plasma inside a Tokamak and prevents accidents using Google's **Gemini 3**.

## The Problem
In a fusion reactor, the plasma can become unstable in milliseconds. Humans are too slow to react. Traditional software is too rigid.

## Our Solution: The Agentic Loop
We built a "Smart Supervisor" that:
1. **Watches:** It looks at plasma data (Density, Current, Graphs).
2. **Thinks:** It uses Gemini 3 to understand if the plasma is reaching a dangerous limit.
3. **Acts:** It sends a command to a fast **C++ module** to adjust the magnets and save the reactor.

## Physics Power
Our system uses real data scale from **ITER** (the world's largest fusion project):
- **Major Radius:** 6.2 m
- **Minor Radius:** 2.0 m
- **Magnetic Field:** 5.3 T

We track the **Greenwald Limit** ($n_G = I_p / \pi a^2$). If the density gets too high (above 80%), the AI triggers an emergency correction.

## Tech Stack
- **Brain:** Google Gemini 3
- **Logic:** Google Antigravity
- **Speed:** C++ (Actuator)
- **Interface:** Streamlit (Python Dashboard)

## How to Run
1. **Clone:** `git clone git@github.com:tobiasdotrip/iter-ation.git`
2. **Install:** `pip install -r requirements.txt`
3. **Launch:** `streamlit run app.py`

## The Team
Built by students from **42 Paris**. Combining Physics and Code to power the future.
