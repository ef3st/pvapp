from implant_model.site import Site
import pandas as pd
from implant_model.nature import Nature
from implant_model.implant import Implant
from implant_model.modelchain import BuildModelChain
from pvlib.pvsystem import retrieve_sam 
import matplotlib.pyplot as plt


def main():
    site = Site("NE", coordinates=(45.4642,45.4642), altitude=0, tz='Europe/Rome')
    times = pd.date_range(start='2025-06-01', end='2025-07-01', freq='1h', tz=site.site.tz)
    nature = Nature(site.site, times)
    implant = Implant(name = "PV Implant", location=site)
    implant.setimplant(module=retrieve_sam('CECMod')['Canadian_Solar_Inc__CS5P_220M'], 
                       inverter={'pdc0': 240})
    modelchain = BuildModelChain(system=implant.system,site=site.site)
    
    modelchain.run_model(nature.weather_simulation(temp_air=25, wind_speed=1))
    ac_power = modelchain.results.ac
    
    ac_power.plot(title='AC Power Output [W]') 
    plt.show()
    
if __name__ == "__main__":
    main()