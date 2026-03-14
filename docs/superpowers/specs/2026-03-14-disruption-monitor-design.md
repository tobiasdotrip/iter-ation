# ITER-ATION — Disruption Monitor

Application console TUI en Python pour monitorer des disruptions plasma simulées dans un tokamak type ITER.

## Objectif

Dashboard temps réel affichant des données synthétiques réalistes de paramètres plasma, avec détection de disruptions et mode opérateur interactif.

## Stack

- Python >= 3.11
- Textual (TUI framework)
- textual-plotext (graphes terminaux)
- numpy (génération de données)
- Packaging : pyproject.toml, entry point CLI

## Constantes machine ITER

| Constante | Valeur | Description |
|---|---|---|
| `R_0` | 6.2 m | Rayon majeur |
| `a` | 2.0 m | Rayon mineur |
| `B_T` | 5.3 T | Champ toroïdal |
| `kappa` | 1.7 | Élongation |
| `V_plasma` | 830 m³ | Volume plasma |

## Architecture — 4 couches

```
CLI → TUI (Textual) → Monitoring (seuils, alertes, actions) → Generator (engine, bruit, disruption) → Physics (paramètres, corrélations, formules)
```

Chaque couche communique vers le bas via des interfaces claires. Le générateur peut tourner sans le TUI (tests, debug).

### Communication inter-couches

- Le générateur tourne dans un **Worker Textual** (thread dédié)
- À chaque tick, il produit un `PlasmaState` (dataclass frozen) posté via `post_message`
- Les actions opérateur sont envoyées au générateur via une `queue.Queue` thread-safe
- `PlasmaState` contient les 13 valeurs + timestamp simulé + niveau d'alerte courant

## Paramètres monitorés (13)

Focus sur la **Greenwald fraction** comme métrique centrale.

| # | Paramètre | Unité | Nominal | Seuil risque | Seuil critique | Bruit σ (%) |
|---|---|---|---|---|---|---|
| 1 | `greenwald_fraction` | sans dim. | 0.75 | > 0.85 | > 1.0 | dérivé |
| 2 | `n_e` (densité électronique) | 10²⁰ m⁻³ | 0.9 | — | — | 0.5 |
| 3 | `Ip` (courant plasma) | MA | 15 | — | chute > 20% vs nominal | 0.1 |
| 4 | `q95` (facteur de sécurité) | sans dim. | 3.1 | < 2.5 | < 2.0 | dérivé |
| 5 | `Te_core` (température coeur) | keV | 20 | chute > 30% vs nominal | chute > 50% vs nominal | 1.0 |
| 6 | `Wmhd` (énergie stockée) | MJ | 350 | chute > 20% vs nominal | chute > 40% en < 5 ms | 0.5 |
| 7 | `radiated_fraction` | sans dim. | 0.5 | > 0.7 | > 0.9 | 1.0 |
| 8 | `li` (inductance interne) | sans dim. | 0.85 | > 1.2 | > 1.4 | 0.3 |
| 9 | `n1_amplitude` (mode n=1) | mT | 0.05 | > 0.5 | > 1.0 | 2.0 |
| 10 | `v_loop` (tension de boucle) | V | 0.2 | — | spike > 1.0 | 0.5 |
| 11 | `beta_n` (beta normalisé) | sans dim. | 1.8 | > 2.8 | > 3.5 | dérivé |
| 12 | `zcur` (position verticale) | m | 0.0 | |z| > 0.1 | |z| > 0.2 | 0.2 |
| 13 | `p_input` (puissance injectée) | MW | 50 | chute > 30% vs nominal | chute > 50% vs nominal | 0.1 |

Les seuils "chute > X% vs nominal" comparent la valeur courante à la valeur nominale du paramètre (colonne "Nominal").

### Formules clés

> **TODO (à vérifier)** : les valeurs nominales et seuils ci-dessus sont des approximations basées sur la documentation ITER publique. À revalider par l'utilisateur.

- Greenwald density : `n_G [10²⁰ m⁻³] = Ip [MA] / (π × a² [m²])`
- Beta normalisé : généré directement avec bruit + drift (la formule `β_n = β_T × a × B_T / Ip` est une référence physique, `β_T` n'est pas un paramètre monitoré)
- Facteur de sécurité (calibré ITER, corrigé par li) : `q95 = q95_ref × (Ip_ref / Ip) × (li_ref / li)` avec `q95_ref = 3.1`, `Ip_ref = 15 MA`, `li_ref = 0.85`. La formule cylindrique simplifiée `(5a²κBT)/(R₀Ip)` donne ~1.94 pour ITER (corrections de forme manquantes), on calibre donc sur la valeur connue. Quand `li` augmente (profil de courant piqué), `q95` chute vers q=2 même si `Ip` est stable

## Modèle de génération de données

### Boucle tick-by-tick (dt = 1 ms simulé)

1. **Bruit gaussien** : amplitude réaliste par paramètre (ex: ±0.5% sur n_e, ±0.1% sur Ip)
2. **Corrélations** : si `n_e` monte → `fGW` monte → `radiated_fraction` tend à monter → `Te_core` tend à baisser
3. **Dérive lente** : random walk sur chaque paramètre, simulant l'évolution naturelle d'un pulse plasma

### Probabilité de disruption

Score de risque composite à chaque tick, dominé par `fGW` :

- `fGW ∈ [0.8, 1.0]` → risque croissant linéairement
- `fGW > 1.0` → disruption quasi-certaine
- Pondération additionnelle par `radiated_fraction`, `n1_amplitude`, proximité de `q95` vers 2

### Cascade de disruption (quand déclenchée)

| Phase | Durée simulée | Effets |
|---|---|---|
| Précurseurs | 100-500 ms | `n1_amplitude` croît exponentiellement, `li` varie, `radiated_fraction` monte |
| Quench thermique (TQ) | 1-3 ms | `Te_core` chute ~90%, `Wmhd` s'effondre, spike `v_loop` |
| Current quench + VDE | 50-150 ms | `Ip` chute à 0, `zcur` dérive |

Après une disruption, le système revient à l'état nominal via une rampe progressive (~500 ms simulés), avec un marqueur vertical "NEW PULSE" sur le graphe timeline. L'historique du graphe est continu (pas d'effacement).

### Vitesse de simulation

Facteur d'accélération configurable : ×1, ×10, ×100, ×1000. Défaut : ×100.

## Monitoring & alertes

### Niveaux d'alerte

- **NOMINAL** (vert) : tous les paramètres dans la plage nominale
- **WARNING** (jaune) : un ou plusieurs paramètres dans la zone de risque
- **DANGER** (rouge) : un ou plusieurs paramètres au seuil critique
- **DISRUPTION** (rouge clignotant) : cascade en cours

### Log d'alertes

Historique horodaté des changements de niveau, scrollable.

## Actions opérateur (mode interactif)

| Action | Effet physique | Touche | Délai de réponse |
|---|---|---|---|
| Ajuster injection de gaz (±) | Modifie `n_e` → `fGW` | `↑` / `↓` | ~10-50 ms simulés |
| Ajuster puissance de chauffage (±) | Modifie `p_input` → `Te_core`, `Wmhd`, `beta_n` | `+` / `-` | ~10-50 ms simulés |
| Déclencher SPI | `n_e` ×3, `Te_core` chute ~80%, `radiated_fraction` spike à 0.95, `v_loop` spike. Transforme une disruption non-contrôlée en disruption mitigée (forces réduites) | `S` | ~10 ms simulé |
| SCRAM (arrêt d'urgence) | Rampe de `Ip` vers 0 en ~200 ms simulés. Arrêt propre, pas une disruption. Tous les paramètres convergent vers 0/nominal | `X` | immédiat |

## Layout TUI

```
┌─────────────────────────────────────────────────────────┐
│  ITER-ATION — Disruption Monitor    t=12.450s  ×100    │
├────────────────────────┬────────────────────────────────┤
│                        │  ██████████░░ fGW    0.84     │
│   Graphe temporel      │  ████████░░░░ Prad   0.50     │
│   (fGW + paramètres    │  █████░░░░░░░ q95    3.10     │
│    sélectionnés)       │  ██░░░░░░░░░░ n1     0.05 mT  │
│                        │  ... (jauges colorées)         │
│                        ├────────────────────────────────┤
│                        │  ALERTES                       │
│                        │  ⚠ fGW approaching 0.90       │
│                        │  ● Nominal operation           │
├────────────────────────┴────────────────────────────────┤
│ [↑↓ Gaz] [+- Puissance] [S SPI] [X SCRAM]  Mode: OBS  │
│ [O] Observation  [I] Interactif  [P] Pause  [Q] Quit   │
└─────────────────────────────────────────────────────────┘
```

- **Gauche** : graphe temporel scrollant (textual-plotext) des métriques sélectionnées
- **Droite haut** : jauges horizontales avec couleur dynamique (vert → jaune → rouge)
- **Droite bas** : log d'alertes horodatées
- **Barre bas** : contrôles opérateur + mode actif

## Structure du projet

```
iter-ation/
├── pyproject.toml
├── src/
│   └── iter_ation/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── physics/
│       │   ├── parameters.py
│       │   ├── correlations.py
│       │   └── formulas.py
│       ├── generator/
│       │   ├── engine.py
│       │   ├── noise.py
│       │   └── disruption.py
│       ├── monitoring/
│       │   ├── thresholds.py
│       │   ├── alerts.py
│       │   └── operator.py
│       └── tui/
│           ├── app.py
│           ├── dashboard.py
│           ├── widgets/
│           │   ├── gauge.py
│           │   ├── timeline.py
│           │   ├── alert_log.py
│           │   └── controls.py
│           └── theme.py
└── tests/
    ├── test_physics/
    ├── test_generator/
    └── test_monitoring/
```

## CLI

```
iter-ation                     # mode observation, vitesse ×100
iter-ation --mode interactive  # mode opérateur
iter-ation --speed 1000        # vitesse ×1000
iter-ation --speed 1           # temps réel
```

## Hors scope v1

- Sauvegarde/chargement de session
- Export des données (CSV, JSON)
- Replay d'une disruption passée
