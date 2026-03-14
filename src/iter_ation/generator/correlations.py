from iter_ation.physics.parameters import get_parameter


def apply_correlations(values: dict[str, float]) -> dict[str, float]:
    """Apply inter-parameter correlations.

    Chain: n_e up -> radiated_fraction up -> Te_core down -> Wmhd down.

    Coupling factors are deliberately weak so that anomalies appear
    sequentially rather than simultaneously. This lets the AI agent
    identify the root cause (density) before downstream effects
    (radiation, temperature) become critical.
    """
    result = dict(values)

    n_e_nom = get_parameter("n_e").nominal
    te_nom = get_parameter("Te_core").nominal
    rad_nom = get_parameter("radiated_fraction").nominal
    wmhd_nom = get_parameter("Wmhd").nominal

    n_e_delta = (result.get("n_e", n_e_nom) - n_e_nom) / n_e_nom

    # n_e up -> radiated_fraction up (weak coupling: 0.1)
    if "radiated_fraction" in result:
        result["radiated_fraction"] += n_e_delta * 0.1 * rad_nom

    # radiated_fraction up -> Te_core down (weak coupling: -0.15)
    rad_delta = (result.get("radiated_fraction", rad_nom) - rad_nom) / rad_nom
    if "Te_core" in result:
        result["Te_core"] += rad_delta * (-0.15) * te_nom

    # Te_core down -> Wmhd down (weak coupling: 0.2)
    te_delta = (result.get("Te_core", te_nom) - te_nom) / te_nom
    if "Wmhd" in result:
        result["Wmhd"] += te_delta * 0.2 * wmhd_nom

    return result
