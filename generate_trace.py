import json
import os
import sys

# Ensure src is in the python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from dotenv import load_dotenv
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.env"))
load_dotenv(env_path)

from src.simulation.generator import TokamakGenerator, GeneratorMode
from src.agent.iter_agent import ITERAgent

def generate():
    print("Démarrage de la génération de la trace hors ligne...")
    
    if "GEMINI_API_KEY" not in os.environ:
        print("ATTENTION: La variable d'environnement GEMINI_API_KEY n'est pas définie.")
        print("L'agent ne pourra pas prendre de décision.")
        return

    gen = TokamakGenerator()
    agent = ITERAgent()
    history = []
    
    gen.mode = GeneratorMode.STABLE
    
    # On simule 150 ticks. À T=30 on déclenche un scénario
    scenario_trigger_tick = 30
    scenario_mode = GeneratorMode.SCENARIO_1_GREENWALD
    
    print(f"Génération en cours... Scénario prévu au tick {scenario_trigger_tick}.")
    
    for tick in range(150):
        if tick == scenario_trigger_tick:
            print(f"Tick {tick}: Déclenchement du scénario {scenario_mode}")
            gen.set_scenario(scenario_mode)
            
        gen._tick()
        s = gen.state
        state_dict = {
            "n_e (10^20 m^-3)": round(s.n_e, 3),
            "Ip (MA)": round(s.Ip, 3),
            "Wmhd (MJ)": round(s.Wmhd, 3),
            "p_input (MW)": round(s.p_input, 3),
            "greenwald_fraction": round(s.greenwald_fraction, 3),
            "beta_n": round(s.beta_n, 3),
            "q95": round(s.q95, 3),
            "tau_E (s)": round(s.tau_E, 3)
        }
        
        record = {
            "tick": tick,
            "mode": gen.mode,
            "state": state_dict,
            "ai_action": None,
            "ai_log": None
        }

        # On consulte l'IA si on est en anomalie
        is_stable = (
            state_dict["greenwald_fraction"] < 0.82 and
            state_dict["beta_n"] < 2.5 and
            state_dict["q95"] > 2.3 and
            state_dict["tau_E (s)"] > 2.5
        )
        
        if gen.mode != GeneratorMode.STABLE and not is_stable and tick % 10 == 0:
            print(f"Tick {tick}: Anomalie confirmée, interrogation de l'IA...")
            action = agent.analyze_state(state_dict)
            record["ai_action"] = action
            print(f"Action IA reçue: {action}")
            
            if action != "STABLE" and action != "UNKNOWN_ACTION":
                resolved = gen.apply_ai_action(action)
                if resolved:
                    record["ai_log"] = f"Action {action} efficace. Plasma stabilisé !"
                    print(record["ai_log"])
                else:
                    record["ai_log"] = f"Action {action} inefficace pour ce mode."
                    print(record["ai_log"])

        history.append(record)
        
    output_file = "scenario_trace.json"
    with open(output_file, "w") as f:
        json.dump(history, f, indent=2)
        
    print(f"Génération terminée. Fichier de trace enregistré: {output_file}")

if __name__ == "__main__":
    generate()
