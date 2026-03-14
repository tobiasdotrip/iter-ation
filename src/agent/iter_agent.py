import os
import google.generativeai as genai

class ITERAgent:
    """Agent IA qui analyse l'état du plasma et prend des décisions."""
    
    def __init__(self):
        # Initialise le client GenAI standard (nécessite GEMINI_API_KEY dans l'environnement)
        try:
            genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
            self.model = genai.GenerativeModel('gemini-2.5-flash')
        except Exception as e:
            print(f"Erreur d'initialisation Gemini: {e}")
            self.model = None

    def analyze_state(self, state_dict: dict) -> str:
        """Envoie l'état courant à Gemini et retourne l'action choisie."""
        if not self.model:
            return "ERROR_NO_CLIENT"

        # On construit un prompt strict pour forcer l'IA à choisir parmi les 5 actions
        prompt = f"""
Tu es l'IA pilote du Tokamak ITER. Analyse les paramètres plasma suivants :
{state_dict}

Constantes machine de référence :
- R_0 = 6.2 m
- a = 2.0 m
- B_T = 5.3 T
- kappa = 1.7
- V_plasma = 830 m³

Seuils d'alertes :
- greenwald_fraction > 0.85 (Urgence : REDUCE_GAS)
- beta_n > 2.8 (Urgence : REDUCE_HEAT) 
- q95 < 2.5 (Urgence : ADJUST_COILS)
- tau_E < 2.0 (Urgence : INCREASE_HEAT)

Si tout est normal, retourne "STABLE".
Si une alerte est détectée, retourne **uniquement** l'une des commandes suivantes :
REDUCE_GAS, REDUCE_HEAT, ADJUST_COILS, INCREASE_HEAT, EMERGENCY_SPI

Ne mets aucun autre texte, juste la commande.
"""
        try:
            response = self.model.generate_content(prompt)
            action = response.text.strip().upper()
            
            # Validation stricte
            allowed = ["STABLE", "REDUCE_GAS", "REDUCE_HEAT", "ADJUST_COILS", "INCREASE_HEAT", "EMERGENCY_SPI"]
            if any(cmd in action for cmd in allowed):
                for cmd in allowed:
                    if cmd in action: return cmd
            return "UNKNOWN_ACTION"
            
        except Exception as e:
            return f"ERROR: {str(e)}"
