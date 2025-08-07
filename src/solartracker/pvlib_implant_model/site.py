from pvlib.location import Location
from typing import Tuple, Optional
from utils.logger import get_logger


class Site:
    def __init__(
        self, name:str, coordinates: Tuple[int, int], altitude: Optional[float], tz: str
    ) -> None:
        self.site: Location = Location(
            latitude=coordinates[0],
            longitude=coordinates[1],
            altitude=altitude,
            tz=tz,
            name=name,
        )
        self.logger = get_logger("solartracker")
    
    @property
    def name(self) -> str:
        if self.site.name:
            return self.site.name
        else:   
            return "Name_Not_Defined"
    @property
    def latitude(self) -> float:
        return self.site.latitude
    @property
    def longitude(self) -> float:
        return self.site.longitude
    @property
    def altitude(self) -> Optional[float]:
        return self.site.altitude
    @property
    def tz(self) -> str:
        return self.site.tz
    
    @property
    def location(self):
        return self.site