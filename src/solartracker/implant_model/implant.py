from pvlib.pvsystem import PVSystem
from typing import Optional
from .site import Site
import pvlib
from utils.logger import get_logger


class Implant():
   implants_counter = 0
   
   def __init__(self, name:str = None, location:Site = None, owner:Optional[str] = None, description:Optional[str] = None):
      self.id = Implant.implants_counter
      Implant.implants_counter += 1
      
      self.name = name
      self.location = location
      self.owner = owner
      self.description = description
      
      self.implant_setted = False # False until PVSystem is not defined
      self.logger = get_logger('solartracker')
      
   def setimplant(self, module, inverter):
      if self.implant_setted:
         self.logger.warning(f"{self.name}: an implant has been already setted. NO CREATION OF THE IMPLANT WITH {module} and {inverter}")
         return
      self.system = PVSystem(
         module_parameters= module,
         inverter_parameters= inverter,
         surface_tilt=30,
         surface_azimuth=180,
         temperature_model_parameters = pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS['sapm']['open_rack_glass_glass']
      )
      