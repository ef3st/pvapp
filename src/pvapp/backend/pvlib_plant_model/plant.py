from typing import Optional, Any

import pvlib
from pvlib.pvsystem import PVSystem, Array, FixedMount, SingleAxisTrackerMount

from tools.logger import get_logger
from .site import Site
from pvapp.backend.mount.developement import custommount as dev
from pvapp.backend.mount.validated import custommount as valid


# * =============================
# *       PV SYSTEM MANAGER
# * =============================
class PVSystemManager:
    """
    Manager class for handling the creation and configuration of PV systems.

    Attributes:
        plants_counter (int): Class-level counter for assigning unique plant IDs.
        id (int): Unique identifier of the PV system instance.
        name (str): Name of the PV system.
        location (Optional[Site]): Geographic site information of the PV system.
        owner (Optional[str]): Name of the plant owner.
        description (Optional[str]): Description of the PV system.
        system (Optional[PVSystem]): The actual PVSystem object from pvlib.
        logger: Logger instance for logging messages.

    Methods:
        set_pv_components: Define and create a PVSystem with given components.
        getplant: Retrieve the configured PVSystem.
        delete_inplant: Delete the configured PVSystem.
    """

    plants_counter: int = 0  # Counter used to assign unique IDs to plants

    # * =========================================================
    # *                      LIFECYCLE
    # * =========================================================
    def __init__(
        self,
        name: str = "",
        location: Optional[Site] = None,
        owner: Optional[str] = None,
        description: Optional[str] = None,
        id: Optional[int] = None,
    ) -> None:
        """
        Initialize a PVSystemManager instance.

        Args:
            name (str): Name of the PV system.
            location (Optional[Site]): Location object containing site information.
            owner (Optional[str]): Owner of the PV system.
            description (Optional[str]): Description of the PV system.
            id (Optional[int]): Unique plant ID. If None, an ID will be assigned automatically.
        """
        self.logger = get_logger("pvapp")

        # Assign ID (automatic if not provided)
        if id is None:
            self.id = PVSystemManager.plants_counter
            PVSystemManager.plants_counter += 1
        else:
            self.id = id

        # Plant metadata
        self.name: str = name
        self.location: Optional[Site] = location
        self.owner: Optional[str] = owner
        self.description: Optional[str] = description

        # Placeholder for the pvlib PVSystem object
        self.system: Optional[PVSystem] = None

    # * =========================================================
    # *                      PUBLIC API
    # * =========================================================
    def set_pv_components(
        self,
        module: Optional[dict[str, Any]] = None,
        inverter: Optional[dict[str, Any]] = None,
        mount_type: str = "FixedMount",
        params: dict[str, Any] = {},
        modules_per_string: int = 1,
        strings: int = 1,
    ) -> None:
        """
        Define and create a PVSystem with the given components.

        Args:
            module (Optional[dict[str, Any]]): Module parameters (from pvlib database or custom definition).
            inverter (Optional[dict[str, Any]]): Inverter parameters (from pvlib database or custom definition).
            mount_type (str): Type of mounting system
                ("FixedMount", "SingleAxisTrackerMount", "ValidatedMount", "DevelopementMount").
            params (dict[str, Any]): Parameters specific to the mount type.
            modules_per_string (int): Number of modules per string.
            strings (int): Number of parallel strings.

        ---
        Notes:
        - If a system is already set, the method logs a warning and exits without overwriting.
        - Custom mounts ("ValidatedMount", "DevelopementMount") are supported via external modules.
        """
        if self.system:
            self.logger.warning(
                f"{self.name}: A plant is already defined. "
                f"NO CREATION of a new plant with {module} and {inverter}."
            )
            return

        # Select the correct mount type
        mount = None
        if mount_type == "FixedMount":
            mount = FixedMount(**params)
        elif mount_type == "SingleAxisTrackerMount":
            mount = SingleAxisTrackerMount(**params)
        elif mount_type == "ValidatedMount":
            mount = valid.CustomMount(**params)
        elif mount_type == "DevelopementMount":
            mount = dev.CustomMount(**params)
        else:
            self.logger.error(f"Mount type {mount_type} does NOT exist")

        # Create the PV array
        array = Array(
            mount=mount,
            module_parameters=module,
            temperature_model_parameters=pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS[
                "sapm"
            ]["open_rack_glass_glass"],
            modules_per_string=modules_per_string,
            strings=strings,
        )

        # Create the complete PV system
        self.system = PVSystem(
            arrays=array,
            module_parameters=module,
            inverter_parameters=inverter,
        )

    def getplant(self) -> Optional[PVSystem]:
        """
        Retrieve the configured PVSystem.

        Returns:
            Optional[PVSystem]: The pvlib PVSystem object if defined, otherwise None.
        """
        if self.system:
            return self.system
        else:
            self.logger.warning(f"{self.name}: Plant not defined")
            return None

    def delete_inplant(self) -> None:
        """
        Delete the configured PVSystem.

        Notes:
        - This resets the system to None and logs the deletion.
        """
        self.system = None
        self.logger.info(
            f"[PVSystemManager] {self.name}: Plant configuration deleted successfully"
        )
