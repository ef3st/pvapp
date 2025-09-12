from typing import Optional

from pvlib.location import Location

from tools.logger import get_logger


# * =============================
# *             SITE
# * =============================
class Site:
    """
    Representation of a PV site with location metadata.

    Attributes:
        site (Location): pvlib `Location` object with coordinates, altitude, tz, and name.
        logger: Application logger instance (`get_logger("pvapp")`).

    Methods:
        name: Return the site name or a default placeholder.
        latitude: Return site latitude.
        longitude: Return site longitude.
        altitude: Return site altitude.
        tz: Return site timezone.
        location: Return the underlying pvlib `Location` object.

    ---
    Notes:
    - Wrapping pvlib's `Location` allows consistent logging and extension with app-specific methods.
    """

    # * =========================================================
    # *                      LIFECYCLE
    # * =========================================================
    def __init__(
        self,
        name: str,
        coordinates: tuple[float, float],
        altitude: Optional[float],
        tz: str,
    ) -> None:
        """
        Initialize a site wrapper around pvlib's `Location`.

        Args:
            name (str): Site name.
            coordinates (tuple[float, float]): Latitude and longitude in decimal degrees.
            altitude (Optional[float]): Altitude above sea level in meters.
            tz (str): Timezone string (e.g. 'Europe/Rome').
        """
        self.site: Location = Location(
            latitude=coordinates[0],
            longitude=coordinates[1],
            altitude=altitude,
            tz=tz,
            name=name,
        )
        self.logger = get_logger("pvapp")

    # * =========================================================
    # *                        PROPERTIES
    # * =========================================================
    @property
    def name(self) -> str:
        """
        Return the site name, or "Name_Not_Defined" if not set.

        Returns:
            str: Site name.
        """
        return self.site.name if self.site.name else "Name_Not_Defined"

    @property
    def latitude(self) -> float:
        """
        Return site latitude in decimal degrees.

        Returns:
            float: Latitude value.
        """
        return self.site.latitude

    @property
    def longitude(self) -> float:
        """
        Return site longitude in decimal degrees.

        Returns:
            float: Longitude value.
        """
        return self.site.longitude

    @property
    def altitude(self) -> Optional[float]:
        """
        Return site altitude.

        Returns:
            Optional[float]: Altitude in meters, or None if not provided.
        """
        return self.site.altitude

    @property
    def tz(self) -> str:
        """
        Return site timezone.

        Returns:
            str: Timezone string.
        """
        return self.site.tz

    @property
    def location(self) -> Location:
        """
        Return the underlying pvlib Location object.

        Returns:
            Location: pvlib Location instance.
        """
        return self.site
