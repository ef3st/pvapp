from pvlib.location import Location
import pandas as pd
import numpy as np
from numpy.typing import NDArray
import pvlib
from typing import Dict, Union, Optional
from tools.logger import get_logger


class Nature:
    """
    Lightweight environment/irradiance simulator built on top of pvlib.

    This class computes:
      - Solar position (zenith, azimuth, apparent elevation)
      - Extra-terrestrial DNI
      - A simple, semi-empirical estimate of GHI/DNI/DHI (synthetic sky model)
      - Plane-of-array (POA) irradiance for arbitrary surface geometry
      - A toy weather time series (air temperature, wind speed)

    Parameters
    ----------
    site : pvlib.location.Location
        Site metadata (latitude, longitude, altitude, timezone).
    times : pandas.DatetimeIndex or pandas.Series or pandas.DataFrame
        Time index (must be timezone-aware) for which the simulation is run.

    Attributes
    ----------
    site : pvlib.location.Location
        As provided.
    times : pandas.DatetimeIndex
        Normalized time index used for all computations.
    solpos : pandas.DataFrame
        Solar position with columns like 'zenith', 'azimuth', 'apparent_elevation'.
        Angles are in degrees.
    dni_extra : pandas.Series
        Extraterrestrial normal irradiance (W/m^2).
    aviable_energy : Dict[str, NDArray[np.float64]]
        Dictionary with synthetic irradiance components:
        - 'GHI' : Global Horizontal Irradiance (W/m^2)
        - 'DNI' : Direct Normal Irradiance (W/m^2)
        - 'DHI' : Diffuse Horizontal Irradiance (W/m^2)

    Notes
    -----
    - The attribute name `aviable_energy` keeps the original (misspelled) key
      for backward compatibility.
    - The sky model here is intentionally simple and not physically rigorous.
      Use pvlib’s transposition and clear-sky models for production-grade work.
    """

    def __init__(
        self, site: Location, times: Union[pd.DataFrame, pd.Series, pd.DatetimeIndex]
    ) -> None:
        self.site = site
        # Ensure we work with a DatetimeIndex (Series/DataFrame index is used if provided)
        self.times = (
            times if isinstance(times, pd.DatetimeIndex) else pd.DatetimeIndex(times)
        )
        self._compute()
        self.logger = get_logger("pvapp")

    def _compute(self) -> None:
        """
        Compute solar position, extraterrestrial DNI, and synthetic irradiance fields.

        This method is called once during initialization. If you need to recompute
        after changing `times` or `site`, call it explicitly.
        """
        # Solar position (degrees). Apparent elevation accounts for refraction.
        self.solpos = self.site.get_solarposition(self.times)

        # Extra-terrestrial DNI (W/m^2)
        self.dni_extra = pvlib.irradiance.get_extra_radiation(self.times)

        # Synthetic horizontal components (W/m^2)
        self.aviable_energy = self._aviableenergy()

    def _aviableenergy(self) -> Dict[str, NDArray[np.float64]]:
        """
        Build a very simple synthetic sky to derive GHI, DNI, and DHI.

        Model
        -----
        - GHI rises with solar apparent elevation: GHI = 1000 * sin(elev), clipped to [0, 1000].
        - Atmospheric transmittance ~ exp(-0.14 * (airmass - 1)); clipped at 1.
        - DNI is derived from GHI and zenith with the transmittance factor:
              DNI = (GHI / cos(zenith)) * transmittance
          and clipped to [0, 1000].
        - DHI is the residual on the horizontal plane:
              DHI = GHI - DNI * cos(zenith)
          and clipped to [0, +inf).

        Returns
        -------
        Dict[str, NDArray[np.float64]]
            Keys: 'GHI', 'DNI', 'DHI'. Values are numpy arrays aligned to `self.times`.
        """
        # Apparent solar elevation in radians (clip negatives to zero: sun below horizon -> 0)
        elev = np.radians(self.solpos["apparent_elevation"].clip(lower=0))

        # Synthetic GHI as a smooth function of elevation; cap at 1000 W/m^2
        ghi = 1000.0 * np.sin(elev)
        ghi = ghi.clip(lower=0.0)

        # Relative airmass (dimensionless); avoid airmass explosion near horizon
        airmass = pvlib.atmosphere.get_relative_airmass(
            self.solpos["zenith"].clip(upper=89.9)
        )

        # Simple atmospheric transmittance decreasing with airmass
        transmittance = np.exp(-0.14 * (airmass - 1.0))
        transmittance = transmittance.clip(upper=1.0)

        # Compute DNI. Clip zenith to avoid cos ~ 0 near the horizon.
        zenith_clipped = self.solpos["zenith"].clip(upper=89.9)
        dni = ghi / np.cos(np.radians(zenith_clipped)) * transmittance
        dni = dni.clip(lower=0.0, upper=1000.0)

        # Compute DHI as horizontal residual; clip negatives to zero
        dhi = ghi - dni * np.cos(np.radians(self.solpos["zenith"]))
        dhi = dhi.clip(lower=0.0)

        return {"GHI": ghi, "DNI": dni, "DHI": dhi}

    def getPOA(self, surface_tilt: float, surface_azimuth: float) -> pd.DataFrame:
        """
        Compute Plane-of-Array (POA) irradiance for a given surface geometry.

        This wraps `pvlib.irradiance.get_total_irradiance` using the internally
        generated synthetic irradiance components and solar position.

        Parameters
        ----------
        surface_tilt : float
            Surface tilt from horizontal in degrees (0 = horizontal, 90 = vertical).
        surface_azimuth : float
            Surface azimuth in degrees (0 = North, 90 = East, 180 = South, 270 = West).

        Returns
        -------
        pandas.DataFrame
            Columns typically include:
              - 'poa_global' (W/m^2)
              - 'poa_direct' (W/m^2)
              - 'poa_diffuse' (W/m^2)
              - 'poa_sky_diffuse' (W/m^2)
              - 'poa_ground_diffuse' (W/m^2)
              - 'aoi' (degrees, angle of incidence)
            Exact columns may vary by pvlib version/model.

        Notes
        -----
        - Uses the 'haydavies' transposition model by default.
        - Inputs/outputs are aligned to `self.times`.
        """
        return pvlib.irradiance.get_total_irradiance(
            surface_tilt=surface_tilt,
            surface_azimuth=surface_azimuth,
            solar_zenith=self.solpos["zenith"],
            solar_azimuth=self.solpos["azimuth"],
            dni=self.aviable_energy["DNI"],
            ghi=self.aviable_energy["GHI"],
            dhi=self.aviable_energy["DHI"],
            dni_extra=self.dni_extra,
            model="haydavies",
        )

    def weather_simulation(
        self,
        temp_air: Optional[np.ndarray],
        wind_speed: Optional[np.ndarray],
        seed: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Create a simple synthetic weather frame aligned to `self.times`.

        The current implementation *ignores* the `temp_air` and `wind_speed`
        inputs and instead generates:
          - A seasonal air temperature (°C):
                T_air = 20 + 10 * sin(2π * (day_of_year - 80) / 365)
          - A random wind speed (m/s):
                wind = 1 + U[0, 1)

        Parameters
        ----------
        temp_air : array-like or None
            Ignored in the current implementation. Kept for future extension.
        wind_speed : array-like or None
            Ignored in the current implementation. Kept for future extension.
        seed : int, optional
            Random seed for reproducible wind-speed samples.

        Returns
        -------
        pandas.DataFrame
            Index: `self.times`.
            Columns:
              - 'ghi' (W/m^2)
              - 'dni' (W/m^2)
              - 'dhi' (W/m^2)
              - 'temp_air' (°C)
              - 'wind_speed' (m/s)

        Notes
        -----
        This weather generator is a toy model intended for testing pipelines.
        Replace it with real measurements or reanalysis data (e.g., TMY/ERA5)
        for realistic simulations.
        """
        if seed is not None:
            np.random.seed(seed)

        # --- Synthetic seasonal temperature profile (°C) ---
        # Peaks around day-of-year ≈ 172 (June) given the phase shift of 80 days.
        temp_air = 20.0 + 10.0 * np.sin(
            2.0 * np.pi * (self.times.dayofyear - 80) / 365.0
        )

        # --- Synthetic wind speed (m/s) ---
        # Uniform random variation around ~1–2 m/s

        # Assemble output DataFrame aligned to times
        return pd.DataFrame(
            {
                "ghi": self.aviable_energy["GHI"],
                "dni": self.aviable_energy["DNI"],
                "dhi": self.aviable_energy["DHI"],
                "temp_air": temp_air,
                "wind_speed": wind_speed,
            },
            index=self.times,
        )
