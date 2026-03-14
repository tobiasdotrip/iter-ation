import sys
import os

# Ensure src is in the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ui.app import IterActionApp

def main():
    from dotenv import load_dotenv
    # Load .env file from the parent directory of iter-action
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.env"))
    load_dotenv(env_path)

    if "GEMINI_API_KEY" not in os.environ:
        print("ATTENTION: La variable d'environnement GEMINI_API_KEY n'est pas définie.")
        print("L'agent IA ne pourra pas envoyer de décisions.")
        print("Pour l'ajouter: export GEMINI_API_KEY='votre_clé'")
        print("Ou sur Windows (PowerShell): $env:GEMINI_API_KEY='votre_clé'\n")
        
    app = IterActionApp()
    app.run()

if __name__ == "__main__":
    main()
