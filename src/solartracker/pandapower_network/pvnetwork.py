import pandapower as pp
import pandapower.plotting as plot
import json

from typing import (
    Protocol,
    runtime_checkable,
    Union,
    Optional,
    Tuple,
    Literal,
    TypedDict,
    List
)
import pandas as pd
from utils.logger import get_logger


# ===============================
#   TypedDict for Grid Elements
# ===============================
class LineParams(TypedDict, total=False):
    from_bus: int
    to_bus: int
    length_km: float
    name: str
    std_type:str



class BusParams(TypedDict, total=False):
    vn_kv: Union[str, float, None]
    name: Optional[str]
    geodata: Optional[Tuple]
    type: Optional[Literal["b", "n", "m"]]
    zone: Union[None, int, str]
    in_service: bool
    min_vm_pu: Optional[float]
    max_vm_pu: Optional[float]




class SGenParams(TypedDict, total=False):
    bus: int
    p_mw: float
    q_mvar: float
    name: Optional[str]
    scaling: float
    in_service: bool
    type: Optional[str]


class GenParams(TypedDict, total=False):
    bus: int
    p_mw: float
    vm_pu: float
    name: Optional[str]
    min_q_mvar: float
    max_q_mvar: float
    sn_mva: Optional[float]
    slack: Optional[bool]
    scaling: float
    in_service: bool


class ExtGridParams(TypedDict, total=False):
    bus: int
    vm_pu: float
    va_degree: float
    name: Optional[str]
    in_service: bool

# ===================================
#   CLASS FOR POWER GRID MANAGEMENT
# ===================================
class PlantPowerGrid:
    
    def __init__(self, path = None) -> None:
        self.logger = get_logger("solartracker")
        self.net:pp.pandapowerNet = pp.create_empty_network()
        if path:
            self.net = self.load_grid(path)
        
        # self.buses_df = pd.DataFrame(
        #     columns=[
        #         "name",
        #         "zone",
        #         "type",
        #         "geodata",
        #         "min_vm_pu",
        #         "max_vm_pu",
        #         "vn_kv",
        #     ]
        # )
    
    def load_grid(self,path):
        self.net = pp.from_json(path)

    def create_bus(self, bus:BusParams) -> None:
        # TODO Create a logical method of indexing
        bus_index = pp.create_bus(
            self.net,
            **bus
        )

        # for k in bus.keys():
        #     if k not in self.buses_df.columns:
        #         self.buses_df[k] = None

        # self.buses_df.loc[bus_index] = pd.Series(bus)

    def link_buses(self, line:LineParams):
        # NOTE use pp.available_std_types(net)["line"] to get aviable line tipe (e.g, for LV "NAYY 4x50 SE")
        pp.create_line(self.net, **line)
    
    def aviable_link(self, start_bus:BusParams, end_bus:BusParams) -> int:
        if start_bus["name"] == end_bus["name"]:
            return 1
        if start_bus["vn_kv"] != end_bus["vn_kv"]:
            return 2 
        start = self.get_element("bus",name=start_bus["name"],column="index")
        end = self.get_element("bus",name=end_bus["name"],column="index")
        if self.get_bus_links(start,end):
            return 3    
        
        return 0
    
    def get_bus_links(self, bus1: int, bus2: int) -> list[str]:
        links = []
        net = self.net
        # Line
        if any(
            ((net.line["from_bus"] == bus1) & (net.line["to_bus"] == bus2)) |
            ((net.line["from_bus"] == bus2) & (net.line["to_bus"] == bus1))
        ):
            links.append("line")

        # Transformer
        if any(
            ((net.trafo["hv_bus"] == bus1) & (net.trafo["lv_bus"] == bus2)) |
            ((net.trafo["hv_bus"] == bus2) & (net.trafo["lv_bus"] == bus1))
        ):
            links.append("trafo")

        # Transformer 3-winding
        if bus1 in net.trafo3w[["hv_bus", "mv_bus", "lv_bus"]].values and \
           bus2 in net.trafo3w[["hv_bus", "mv_bus", "lv_bus"]].values:
            links.append("trafo3w")

        # Impedance
        if any(
            ((net.impedance["from_bus"] == bus1) & (net.impedance["to_bus"] == bus2)) |
            ((net.impedance["from_bus"] == bus2) & (net.impedance["to_bus"] == bus1))
        ):
            links.append("impedance")

        # DC Line
        if any(
            ((net.dcline["from_bus"] == bus1) & (net.dcline["to_bus"] == bus2)) |
            ((net.dcline["from_bus"] == bus2) & (net.dcline["to_bus"] == bus1))
        ):
            links.append("dcline")

        # Bus-bus Switch
        sw_bus = net.switch[net.switch["et"] == "b"]
        if any(
            ((sw_bus["bus"] == bus1) & (sw_bus["element"] == bus2)) |
            ((sw_bus["bus"] == bus2) & (sw_bus["element"] == bus1))
        ):
            links.append("bus_switch")

        return links


    
    def get_line_infos(self,type):
        return pp.available_std_types(self.net).loc[type]
        
    def get_aviable_lines(self):
        return list(pp.available_std_types(self.net).index)

    def add_transformer():
        raise NotImplementedError

    def add_switch():
        raise NotImplementedError

    def add_active_element(
        self,
        type: Literal["sgen", "gen", "ext_grid"],
        params: Union[SGenParams, GenParams, ExtGridParams],
    ) -> int:
        if type == "sgen":
            return pp.create_sgen(self.net, **params)
        elif type == "gen":
            return pp.create_gen(self.net, **params)
        elif type == "ext_grid":
            return pp.create_ext_grid(self.net, **params)
        else:
            raise ValueError(f"Unsupported element type: {type}")

    def add_passive_element():  # load, shunt, impedance, dcline
        raise NotImplementedError

    def add_sensors():  # control
        raise NotImplementedError

    def get_element(self, element:Literal["bus"] = None,index:Optional[int] = None, name:Optional[str] = None, 
                    column:Literal["index","name","vn_kv","type","zone","in_service","geo",""] = "") -> str | pd.Series:
        if element == "bus":
            df = self.net.bus

            # Se è fornito un nome, crea una maschera booleana
            if name is not None:
                mask = df["name"] == name
                if not mask.any():
                    return None
                result = df[mask]
            # Se è fornito un indice, usa direttamente loc
            elif index is not None:
                if index not in df.index:
                    return None
                result = df.loc[[index]]
            else:
                return None

            # Restituisce tutto, un campo, o l'indice
            if column == "":
                return result
            elif column == "index":
                return result.index[0]
            elif column in df.columns:
                return result[column].values[0]
            else:
                return None      
                
                
        return None
    
    def get_n_nodes_links(self):
        return len(self.net.bus)
        
    def get_n_active_elements(self):
        return None
    def get_n_passive_elements(self):
        return None
    def get_sensors_controllers(self):
        return None
    
    def show_grid(self):
        self.runnet()
        if self.is_plot_ready():
            plot.simple_plot(self.net)
    
        
        
    def runnet(self):
        pp.runpp(self.net)
        
    def is_plot_ready(self) -> bool:
        bus_geo = self.net.bus.get("geo", None)

        # 1. At least a bus and a line
        if self.net.bus.empty:
            return False
        if self.net.line.empty and self.net.trafo.empty:
            return False

        # 2. Geo column
        if bus_geo is None or bus_geo.isnull().all():
            return False

        # 3. valid geo data
        for val in bus_geo.dropna():
            if isinstance(val, dict):
                continue
            try:
                json.loads(val)
            except Exception:
                return False

        return True
    
    def save(self, path):
        pp.to_json(self.net, path)  