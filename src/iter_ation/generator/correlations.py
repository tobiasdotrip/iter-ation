from iter_ation.physics.parameters import get_parameter


def apply_correlations(values: dict[str, float]) -> dict[str, float]:
    """Apply inter-parameter correlations.

    Correlations are driven by deviations from nominal values.
    Chain: n_e up -> radiated_fraction up -> Te_core down -> Wmhd down.
    """
    result = dict(values)

    n_e_nom = get_parameter("n_e").nominal
    te_nom = get_parameter("Te_core").nominal
    rad_nom = get_parameter("radiated_fraction").nominal
    wmhd_nom = get_parameter("Wmhd").nominal

    n_e_delta = (result.get("n_e", n_e_nom) - n_e_nom) / n_e_nom

    if "radiated_fraction" in result:
        result["radiated_fraction"] += n_e_delta * 0.3 * rad_nom

    rad_delta = (result.get("radiated_fraction", rad_nom) - rad_nom) / rad_nom
    if "Te_core" in result:
        result["Te_core"] += rad_delta * (-0.4) * te_nom

    te_delta = (result.get("Te_core", te_nom) - te_nom) / te_nom
    if "Wmhd" in result:
        result["Wmhd"] += te_delta * 0.5 * wmhd_nom

    return result
