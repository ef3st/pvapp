from pvlib.location import Location
import pandas as pd
import numpy as np
import pvlib
from typing import Dict
from utils.logger import get_logger


class Nature:
    def __init__(self, site: Location, times: pd.DataFrame) -> None:
        self.site = site
        self.times = times
        self._compute()
        self.logger = get_logger("solartracker")

    def _compute(self):
        # Solar position
        self.solpos = self.site.get_solarposition(self.times)

        # Irradiance simulation
        self.dni_extra = pvlib.irradiance.get_extra_radiation(self.times)

        self.aviable_energy = self._aviableenergy()

    def _aviableenergy(self) -> Dict[str, float]:
        """
        Compute GHI, DNI, DHI values using a semi-empirical model based on solar elevation.
        - GHI (Global Horizontal Irradiance): modeled as 1000 * sin(elevation), max 1000
        - DNI (Direct Normal Irradiance): depends on elevation, air mass effect (simplified)
        - DHI (Diffuse Horizontal Irradiance): GHI - DNI * cos(zenith)
        """

        # Elevazione solare apparente in radianti
        elev = np.radians(self.solpos["apparent_elevation"].clip(lower=0))

        # GHI aumentata gradualmente con l'elevazione del sole
        ghi = 1000 * np.sin(elev)
        ghi = ghi.clip(lower=0)

        # Stima semplificata del fattore atmosferico
        airmass = pvlib.atmosphere.get_relative_airmass(
            self.solpos["zenith"].clip(upper=89.9)
        )
        transmittance = np.exp(-0.14 * (airmass - 1))  # decresce con l'airmass
        transmittance = transmittance.clip(upper=1)

        # DNI = GHI / cos(zenith), corretta per l’atmosfera
        dni = (
            ghi
            / np.cos(np.radians(self.solpos["zenith"].clip(upper=89.9)))
            * transmittance
        )
        dni = dni.clip(lower=0, upper=1000)

        # DHI = GHI - DNI * cos(zenith)
        dhi = ghi - dni * np.cos(np.radians(self.solpos["zenith"]))
        dhi = dhi.clip(lower=0)

        return {"GHI": ghi, "DNI": dni, "DHI": dhi}

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
            self.solpos["zenith"],
            self.solpos["azimuth"],
            self.aviable_energy["DNI"],
            self.aviable_energy["GHI"],
            self.aviable_energy["DHI"],
            dni_extra=self.dni_extra,
            model="haydavies",
        )

    def weather_simulation(self, temp_air, wind_speed) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "ghi": self.aviable_energy["GHI"],
                "dni": self.aviable_energy["DNI"],
                "dhi": self.aviable_energy["DHI"],
                "temp_air": temp_air,  # This is the temperature of the air
                "wind_speed": wind_speed,  # This is the wind speed
            },
            index=self.times,
        )
