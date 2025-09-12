from typing import Dict, Optional, Union

import numpy as np
import pandas as pd
import pvlib
from numpy.typing import NDArray
from pvlib.location import Location

from tools.logger import get_logger


# * =============================
# *            NATURE
# * =============================
class Nature:
    """
    Lightweight environment/irradiance simulator built on top of pvlib.

    Attributes:
        site (Location): Site metadata (latitude, longitude, altitude, timezone).
        times (pd.DatetimeIndex): Normalized time index used for computations.
        solpos (pd.DataFrame): Solar position ('zenith', 'azimuth', 'apparent_elevation'), degrees.
        dni_extra (pd.Series): Extraterrestrial normal irradiance (W/m^2).
        aviable_energy (Dict[str, NDArray[np.float64]]): Synthetic horizontal irradiance:
            - 'GHI' (W/m^2) Global Horizontal Irradiance
            - 'DNI' (W/m^2) Direct Normal Irradiance
            - 'DHI' (W/m^2) Diffuse Horizontal Irradiance

    Methods:
        getPOA: Compute plane-of-array irradiance for a given surface geometry.
        weather_simulation: Produce a toy weather time series aligned to `times`.

    ---
    Notes:
    - The attribute name `aviable_energy` (sic) is preserved for backward compatibility.
    - This sky model is intentionally simple and not physically rigorous; use pvlib’s
      transposition and clear-sky models for production scenarios.
    """

    # * =========================================================
    # *                      LIFECYCLE
    # * =========================================================
    def __init__(
        self,
        site: Location,
        times: Union[pd.DataFrame, pd.Series, pd.DatetimeIndex],
    ) -> None:
        """
        Initialize the synthetic environment around a site and time index.

        Args:
            site (Location): pvlib site/location data.
            times (Union[pd.DataFrame, pd.Series, pd.DatetimeIndex]): Time base
                (must be timezone-aware). If a Series/DataFrame is provided, its
                index is used.

        Raises:
            ValueError: If `times` cannot be converted to a `pd.DatetimeIndex`.
        """
        self.site: Location = site
        # ? Ensure we have a DatetimeIndex (Series/DataFrame index is used if provided)
        self.times: pd.DatetimeIndex = (
            times if isinstance(times, pd.DatetimeIndex) else pd.DatetimeIndex(times)
        )
        self._compute()
        self.logger = get_logger("pvapp")

    # * =========================================================
    # *                    CORE COMPUTATIONS
    # * =========================================================
    def _compute(self) -> None:
        """
        Compute solar position, extraterrestrial DNI, and synthetic irradiance fields.

        Notes:
        - Called during initialization. Re-call after changing `site` or `times`.
        """
        # Solar position (degrees). Apparent elevation accounts for refraction.
        self.solpos: pd.DataFrame = self.site.get_solarposition(self.times)

        # Extra-terrestrial DNI (W/m^2)
        self.dni_extra: pd.Series = pvlib.irradiance.get_extra_radiation(self.times)

        # Synthetic horizontal components (W/m^2)
        self.aviable_energy: Dict[str, NDArray[np.float64]] = self._aviableenergy()

    def _aviableenergy(self) -> Dict[str, NDArray[np.float64]]:
        """
        Build a very simple synthetic sky to derive GHI, DNI, and DHI.

        Model
        -----
        - GHI rises with solar apparent elevation: GHI = 1000 * sin(elev), clipped to [0, 1000].
        - Atmospheric transmittance ~ exp(-0.14 * (airmass - 1)); clipped at 1.
        - DNI = (GHI / cos(zenith)) * transmittance, clipped to [0, 1000].
        - DHI = GHI - DNI * cos(zenith), clipped to [0, +inf).

        Returns:
            Dict[str, NDArray[np.float64]]: Keys 'GHI', 'DNI', 'DHI', arrays aligned to `self.times`.
        """
        # Apparent solar elevation in radians (clip negatives to zero: sun below horizon -> 0)
        elev = np.radians(self.solpos["apparent_elevation"].clip(lower=0.0))

        # Synthetic GHI as a smooth function of elevation; cap at 1000 W/m^2
        ghi = (1000.0 * np.sin(elev)).clip(lower=0.0)

        # Relative airmass (dimensionless); avoid airmass explosion near horizon
        airmass = pvlib.atmosphere.get_relative_airmass(
            self.solpos["zenith"].clip(upper=89.9)
        )

        # Simple atmospheric transmittance decreasing with airmass
        transmittance = np.exp(-0.14 * (airmass - 1.0)).clip(upper=1.0)

        # Compute DNI. Clip zenith to avoid cos ~ 0 near the horizon.
        zenith_clipped = self.solpos["zenith"].clip(upper=89.9)
        dni = (ghi / np.cos(np.radians(zenith_clipped))) * transmittance
        dni = dni.clip(lower=0.0, upper=1000.0)

        # Compute DHI as horizontal residual; clip negatives to zero
        dhi = (ghi - dni * np.cos(np.radians(self.solpos["zenith"]))).clip(lower=0.0)

        return {"GHI": ghi.to_numpy(), "DNI": dni.to_numpy(), "DHI": dhi.to_numpy()}

    # * =========================================================
    # *                       PUBLIC API
    # * =========================================================
    def getPOA(self, surface_tilt: float, surface_azimuth: float) -> pd.DataFrame:
        """
        Compute Plane-of-Array (POA) irradiance for a given surface geometry.

        Args:
            surface_tilt (float): Surface tilt from horizontal in degrees (0 = horizontal, 90 = vertical).
            surface_azimuth (float): Surface azimuth in degrees (0 = North, 90 = East, 180 = South, 270 = West).

        Returns:
            pd.DataFrame: Typical columns:
                - 'poa_global', 'poa_direct', 'poa_diffuse',
                  'poa_sky_diffuse', 'poa_ground_diffuse', 'aoi'.

        Notes:
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
        temp_air: Optional[Union[float, NDArray[np.float64]]],
        wind_speed: Optional[Union[float, NDArray[np.float64]]],
        seed: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Create a simple synthetic weather frame aligned to `self.times`.

        The current implementation *ignores* the `temp_air` and `wind_speed` inputs
        and instead generates:
          - A seasonal air temperature (°C):
                T_air = 20 + 10 * sin(2π * (day_of_year - 80) / 365)
          - A (placeholder) wind speed column taken from the input if provided,
            otherwise left as-is (may be `None`).

        Args:
            temp_air (Optional[Union[float, NDArray[np.float64]]]): Ignored (kept for future extension).
            wind_speed (Optional[Union[float, NDArray[np.float64]]]): Ignored (kept for future extension).
            seed (Optional[int]): Random seed (reserved for future use).

        Returns:
            pd.DataFrame: Index `self.times`, columns:
                'ghi', 'dni', 'dhi', 'temp_air', 'wind_speed'.

        ---
        Notes:
        - This is a toy generator for testing pipelines. Replace with real data
          (TMY/ERA5) for realistic simulations.
        """
        #! Seed is reserved for future stochastic components
        if seed is not None:
            np.random.seed(seed)

        # -------------> Seasonal Temperature Profile <--------
        temp_series = 20.0 + 10.0 * np.sin(
            2.0 * np.pi * (self.times.dayofyear - 80) / 365.0
        )

        # -------------> Assemble Output <--------
        return pd.DataFrame(
            {
                "ghi": self.aviable_energy["GHI"],
                "dni": self.aviable_energy["DNI"],
                "dhi": self.aviable_energy["DHI"],
                "temp_air": temp_series,
                "wind_speed": wind_speed,
            },
            index=self.times,
        )
