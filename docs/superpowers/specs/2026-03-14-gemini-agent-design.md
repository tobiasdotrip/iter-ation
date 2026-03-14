# Agent Gemini — Opérateur IA Autonome

## Objectif

Agent IA utilisant Gemini 3.1 Flash Lite qui surveille les paramètres plasma et prend des actions correctives de manière autonome pour prévenir les disruptions.

## Comportement

- **Mode par défaut** : l'app démarre en mode AI (agentique)
- **Input** : les 13 valeurs du PlasmaState (ce que le TUI affiche)
- **Output** : une action parmi GAS_UP, GAS_DOWN, POWER_UP, POWER_DOWN, SPI, SCRAM, NOOP
- **Déclencheur** : l'agent est consulté quand le niveau global atteint WARNING ou DANGER
- **Cooldown** : 500 ms simulés entre deux appels API
- **Affichage** : les décisions apparaissent dans le panneau AI OPERATOR du TUI

## API

- Modèle : `gemini-3.1-flash-lite-preview`
- SDK : `google-genai`
- Clé : fichier `.env` (`GEMINI_API_KEY=xxx`)
- Format : JSON structuré in/out

### Prompt système

```
You are a tokamak plasma operator AI. You monitor 13 plasma parameters
and take actions to prevent disruptions. Respond with a single JSON object:
{"action": "<ACTION>", "reason": "<short explanation>"}

Available actions: GAS_UP, GAS_DOWN, POWER_UP, POWER_DOWN, SPI, SCRAM, NOOP

Rules:
- greenwald_fraction > 0.85: reduce density (GAS_DOWN)
- greenwald_fraction > 1.0: emergency (SPI or SCRAM)
- q95 < 2.5: reduce current (POWER_DOWN)
- radiated_fraction > 0.7: reduce density (GAS_DOWN)
- n1_amplitude > 0.5: magnetic instability, consider SPI
- Only use SPI/SCRAM as last resort when other actions have failed
```

### Payload envoyé

```json
{
  "parameters": {
    "greenwald_fraction": 0.87,
    "n_e": 1.04,
    "Ip": 15.0,
    ...
  },
  "alert_level": "WARNING",
  "triggered_by": ["greenwald_fraction"]
}
```

### Réponse attendue

```json
{"action": "GAS_DOWN", "reason": "fGW at 0.87, approaching Greenwald limit"}
```

## Structure

```
src/iter_ation/agent/
├── __init__.py
├── gemini_client.py    # Appel API Gemini, parsing JSON
└── operator_ai.py      # Logique de déclenchement, cooldown, intégration
```

## Intégration TUI

- L'app démarre en mode AI par défaut
- `on_plasma_update` : si mode AI + alert >= WARNING + cooldown écoulé → appel agent
- L'agent tourne dans un thread (non-bloquant pour le TUI)
- La décision est appliquée au moteur + affichée dans AIPanel
- Modes disponibles : [O] Obs, [I] Inter, [A] AI (défaut)

## Fallback

Si pas de clé API ou erreur réseau → l'app démarre en mode OBS avec un message dans AIPanel : "No API key — AI disabled"
