from tools.logger import get_logger
from ..pandapower_network.pvnetwork import PlantPowerGrid


class PlantManager:
    def __init__(self) -> None:
        self.logger = get_logger("pvapp")
        self.grid = None

    def set_pv():
        raise NotImplementedError

    def set_grid():
        raise NotImplementedError
