from pvlib.location import Location 
from typing import Tuple, Optional



class Site:
    def __init__(self, name, coordinates:Tuple[int,int],altitude:Optional[float], tz:str) -> None:
        self.site:Location = Location(latitude = coordinates[0], 
                             longitude = coordinates[1],
                             altitude = altitude,
                             tz = tz,
                             name = name
                             )
        