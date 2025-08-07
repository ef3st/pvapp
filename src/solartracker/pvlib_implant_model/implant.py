from typing import Optional, List
from .site import Site
import pvlib
from pvlib.pvsystem import PVSystem, Array, FixedMount, SingleAxisTrackerMount
from utils.logger import get_logger
from mount.developement import custommount as dev
from mount.validated import custommount as valid


class PVSystemManager:
    implants_counter = 0

    def __init__(
        self,
        name: str = "",
        location: Optional[Site] = None,
        owner: Optional[str] = None,
        description: Optional[str] = None,
        id: Optional[int] = None,
    ):
        self.logger = get_logger("solartracker")
        if id is None:
            self.id = PVSystemManager.implants_counter
            PVSystemManager.implants_counter += 1
        else:
            self.id = id

        self.name = name
        self.location = location
        self.owner = owner
        self.description = description

        self.system = None

    def setimplant(
        self,
        module=None,
        inverter=None,
        mount_type: str = "FixedMount",
        params: dict = {},
    ):
        if self.system:
            self.logger.warning(
                f"{self.name}: an implant has been already setted. NO CREATION OF THE IMPLANT WITH {module} and {inverter}"
            )
            return

        mount = None
        if mount_type == "FixedMount":
            mount = FixedMount(
                **params
                # surface_tilt=30,  # module inclination
                # surface_azimuth=90,  # (180 = South)
            )
        elif mount_type == "SingleAxisTrackerMount":
            mount = SingleAxisTrackerMount(
                **params
                # axis_tilt=0,  # asse orizzontale (es. parallelo al terreno)
                # axis_azimuth=270,  # direzione dell'asse (180 = asse Nord-Sud)
                # max_angle=45,  # massimo angolo di rotazione (es. ±45°)
                # backtrack=True,  # abilitare backtracking (evita ombreggiamento)
                # gcr=0.35,  # ground coverage ratio (densità pannelli)
            )
        elif mount_type == "ValidatedMount":
            mount = valid.CustomMount(
                **params
                # axis_tilt=0,  # asse orizzontale (es. parallelo al terreno)
                # axis_azimuth=180,  # direzione dell'asse (180 = asse Nord-Sud)
                # max_angle=45,  # massimo angolo di rotazione (es. ±45°)
                # backtrack=False,  # abilitare backtracking (evita ombreggiamento)
                # gcr=0.35,  # ground coverage ratio (densità pannelli)
            )
        elif mount_type == "DevelopementMount":
            mount = dev.CustomMount(
                **params
                # axis_tilt=0,  # asse orizzontale (es. parallelo al terreno)
                # axis_azimuth=180,  # direzione dell'asse (180 = asse Nord-Sud)
                # max_angle=45,  # massimo angolo di rotazione (es. ±45°)
                # backtrack=True,  # abilitare backtracking (evita ombreggiamento)
                # gcr=0.35,  # ground coverage ratio (densità pannelli)
            )
        else:
            self.logger.error(f"mount type {mount_type} does NOT exist")

        array = Array(
            mount=mount,
            module_parameters=module,
            temperature_model_parameters=pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS[
                "sapm"
            ]["open_rack_glass_glass"],
            modules_per_string=5,
        )

        self.system = PVSystem(
            arrays=array,
            module_parameters=module,
            inverter_parameters=inverter,
        )

    def getimplant(self) -> Optional[PVSystem]:
        """Returns the implant if it exists, otherwise None"""
        if self.system:
            return self.system
        else:
            self.logger.warning(f"{self.name}: Implant not setted")
            return None

    def delete_inplant(self):
        self.system = None
        self.logger.info(f"{self.name}: Implant deleted")
