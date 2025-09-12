from typing import Optional

from pvlib.modelchain import ModelChain
from pvlib.location import Location
from pvlib.pvsystem import PVSystem


# * =============================
# *         MODEL CHAIN
# * =============================
def BuildModelChain(
    system: Optional[PVSystem],
    site: Optional[Location],
    dc_model: str = "cec",
    ac_model: str = "pvwatts",
) -> ModelChain:
    """
    Build and return a pvlib ModelChain for the given PV system and site.

    Args:
        system (Optional[PVSystem]): Configured PV system. Must not be None.
        site (Optional[Location]): Geographic site (pvlib Location). Must not be None.
        dc_model (str): DC model identifier (default: "cec").
        ac_model (str): AC model identifier (default: "pvwatts").

    Returns:
        ModelChain: Configured pvlib model chain.

    Raises:
        ValueError: If either `system` or `site` is None.

    ---
    Notes:
    - AOI losses are computed using the empirical "ashrae" model.
    - Spectral effects are disabled ("no_loss").
    - Temperature effects use the "sapm" model.
    """
    if system is None or site is None:
        raise ValueError("System and/or site must be defined to build a model chain.")

    return ModelChain(
        system,
        site,
        dc_model=dc_model,  # DC output from module (using CEC parameters)
        ac_model=ac_model,  # Conversion DC→AC with pvwatts (simplified efficiency)
        aoi_model="ashrae",  # Loss due to angle of incidence
        spectral_model="no_loss",  # Ignore spectral effects (e.g., cloudy conditions)
        temperature_model="sapm",  # Temperature effects on voltage/current product
    )
