from typing import Optional

from tools.logger import get_logger
from ..pandapower_network.pvnetwork import PlantPowerGrid


# * =============================
# *        PLANT MANAGER
# * =============================
class PlantManager:
    """
    High-level manager for a PV plant configuration.

    Attributes:
        logger: Application logger instance (`get_logger("pvapp")`).
        grid (Optional[PlantPowerGrid]): Power grid model, if configured.

    Methods:
        set_pv: Placeholder for setting PV components.
        set_grid: Placeholder for configuring the grid.

    ---
    Notes:
    - This class is currently a stub; implementation to be completed.
    """

    # * =========================================================
    # *                      LIFECYCLE
    # * =========================================================
    def __init__(self) -> None:
        """
        Initialize the PlantManager with a logger and no grid configured.
        """
        self.logger = get_logger("pvapp")
        self.grid: Optional[PlantPowerGrid] = None

    # * =========================================================
    # *                     PUBLIC API (STUBS)
    # * =========================================================
    def set_pv(self) -> None:
        """
        Configure PV components for the plant.

        Raises:
            NotImplementedError: Always, since this is a placeholder.
        """
        raise NotImplementedError("set_pv() is not implemented yet.")

    def set_grid(self) -> None:
        """
        Configure the power grid for the plant.

        Raises:
            NotImplementedError: Always, since this is a placeholder.
        """
        raise NotImplementedError("set_grid() is not implemented yet.")
