from pvlib.location import Location
import pandas as pd
import pvlib
from typing import Dict
from utils.logger import get_logger


class Nature:
    def __init__(self, site:Location, times:pd.DataFrame) -> None:
        self.site = site
        self.times = times
        self._compute()
        self.logger = get_logger('solartracker')
    
    
    def _compute(self):
        # Solar position
        self.solpos = self.site.get_solarposition(self.times)
        
        # Irradiance simulation
        self.dni_extra = pvlib.irradiance.get_extra_radiation(self.times)
        
        self.aviable_energy = self._aviableenergy()
        
    def _aviableenergy(self):
        """
        This method compute the GHI, DNI, DHI values returning a dict with the respective values.
        At this moment it is used a very simple simulation. 
        - GHI (Global Horizontal Irradiance): If sun is over the horizon, on the ground we have 1000 W/m^2, 0 otherwise
        - DNI (Direct Normal Irradiance): assumed as 80% of GHI
        - DHI:(Diffuse Horizontal Irradiance) remaining diffuse irradiation -> dhi = ghi - dni
        """
        ghi = 1000 * (self.solpos['apparent_elevation'] > 0)  # simple estimate
        dni = ghi * 0.8
        dhi = ghi - dni
        
        
        av_energy:Dict[str,float] = {
            "GHI": ghi, 
            "DNI": dni, 
            "DHI": dhi  
        }
        return av_energy
    def getPOA(self, surface_tilt, surface_azimuth):
        """
        This function calculates the total solar irradiance on the module plane (Plane of Array Photovoltaic, POA), 
        i.e. the amount of solar energy that actually reaches the PV panel considering 
        its inclination and orientation.

        Args:
            surface_tilt (_type_): _description_
            surface_azimuth (_type_): _description_

        Returns:
            _type_: _description_
        """
        return pvlib.irradiance.get_total_irradiance(
                surface_tilt,
                surface_azimuth,
                self.solpos['zenith'],
                self.solpos['azimuth'],
                self.aviable_energy["DNI"],
                self.aviable_energy["GHI"],
                self.aviable_energy["DHI"],
                dni_extra=self.dni_extra,
                model='haydavies'
            )
    
    def weather_simulation(self,temp_air, wind_speed) -> pd.DataFrame:
        return pd.DataFrame({
                'ghi': self.aviable_energy["GHI"],
                'dni': self.aviable_energy["DNI"],
                'dhi': self.aviable_energy["DHI"],
                'temp_air': temp_air, # This is the temperature of the air
                'wind_speed': wind_speed, # This is the wind speed
            }, index=self.times)