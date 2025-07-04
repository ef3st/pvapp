from implant_model.site import Site
import pandas as pd
from implant_model.nature import Nature
from implant_model.implant import Implant
from implant_model.modelchain import BuildModelChain
from utils.implant_results_visualizer import show_results
from pvlib.pvsystem import retrieve_sam 
from utils.logger import setup_logger, get_logger

def set_logger():
    setup_logger('solartracker', log_level='DEBUG', use_queue=True)
    return get_logger('solartracker')

def main():
    logger = set_logger()
    site = Site("NE", coordinates=(45.4642,45.4642), altitude=0, tz='Europe/Rome')
    times = pd.date_range(start='2025-07-01', end='2025-07-02', freq='1h', tz=site.site.tz)
    nature = Nature(site.site, times)
    implant = Implant(name = "PV Implant", location=site)
    module = retrieve_sam('CECMod')['Canadian_Solar_Inc__CS5P_220M']
    inverter = {'pdc0': 240}
    implant.setimplant(module=module, 
                       inverter=inverter)
    logger.info(f"Implant {implant.name} built with: \n - module: {module} \n - inverter: {inverter}")
    modelchain = BuildModelChain(system=implant.system,site=site.site)
    
    modelchain.run_model(nature.weather_simulation(temp_air=25, wind_speed=1))
    ac_power = modelchain.results.ac
    show_results(ac_power)

    
if __name__ == "__main__":
    main()