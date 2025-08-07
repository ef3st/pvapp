from pvlib.modelchain import ModelChain
from pvlib.location import Location
from pvlib.pvsystem import PVSystem
from typing import Optional

def BuildModelChain(
    system: Optional[PVSystem], site: Optional[Location], dc_model: str = "cec", ac_model: str = "pvwatts"
):
    """Returns a model chain with the system and the site

    Args:
        system (PVSystem): _description_
        site (Location): _description_
    """
    if system is None or site is None:
        raise ValueError(f"System and/or site must be defined to build a model chain.")
    return ModelChain(
        system,
        site,
        dc_model=dc_model,  # it is using CEC parameters to compute power generated from module in dc
        ac_model=ac_model,  # simplifyed conversion from DC to AC based on typical efficienc
        aoi_model="ashrae",  # empiric model for the loss due to incidence angle
        spectral_model="no_loss",  # effects of changed in the solar spectrum on rendimento (e.g. cloudly condition)
        temperature_model="sapm",  # effect of temperature on the tension/current producted
    )
