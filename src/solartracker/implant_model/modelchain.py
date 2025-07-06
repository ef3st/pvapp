from pvlib.modelchain import ModelChain
from pvlib.location import Location
from pvlib.pvsystem import PVSystem


def BuildModelChain(system: PVSystem, site: Location,dc_model:str="cec",ac_model:str="pvwatts"):
    """Returns a model chain with the system and the site

    Args:
        system (PVSystem): _description_
        site (Location): _description_
    """
    return ModelChain(
        system,
        site,
        dc_model="cec",  # it is using CEC parameters to compute power generated from module in dc
        ac_model="pvwatts",  # simplifyed conversion from DC to AC based on typical efficienc
        aoi_model="ashrae",  # empiric model for the loss due to incidence angle
        spectral_model="no_loss",  # effects of changed in the solar spectrum on rendimento (e.g. cloudly condition)
        temperature_model="sapm",  # effect of temperature on the tension/current producted
    )
