import pandapower as pp
from typing import Protocol, runtime_checkable, Union, Optional, Tuple, Literal, TypedDict
import pandas as pd

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

class PlantPowerGrid:
    def __init__(self, tension_level) -> None:
        self.net = pp.create_empty_network()
        self.buses_df = pd.DataFrame(columns=["name", "zone", "type", "geodata",
                                               "min_vm_pu", "max_vm_pu", "vn_kv"])
    
    def create_bus(self, vn_kv: Union[str, float, None] = "LV", name: Optional[str] = None, 
                   geodata: Optional[Tuple] = None, type: Optional[str] = "b", 
                   zone: Union[None, int, str] = None,
                   in_service: bool = True, min_vm_pu: Optional[float] = None, 
                   max_vm_pu: Optional[float] = None) -> None:
        
        #TODO Create a logical method of indexing
        
        if isinstance(vn_kv, str):
            vn_map = {"LV": 0.4, "MV": 20.0, "HV": 132.0}
            vn_kv = vn_map.get(vn_kv.upper(), 0.4)  # default 0.4kV

        bus_index = pp.create_bus(self.net, vn_kv=vn_kv, name=name, geodata=geodata,
                                  type=type, zone=zone, in_service=in_service,
                                  min_vm_pu=min_vm_pu, max_vm_pu=max_vm_pu)

        self.buses_df.loc[bus_index] = {
            "name": name,
            "zone": zone,
            "type": type,
            "geodata": geodata,
            "min_vm_pu": min_vm_pu,
            "max_vm_pu": max_vm_pu,
            "vn_kv": vn_kv
        }
    
    def link_buses(self, from_bus:int,to_bus:int, length_km:float, name:str):
        # NOTE use pp.available_std_types(net)["line"] to get aviable line tipe (e.g, for LV "NAYY 4x50 SE")
        pp.create_line(self.net, from_bus=from_bus, to_bus=to_bus, length_km=length_km, name=name)
    
    def add_transformer():
        raise NotImplementedError
    
    def add_switch():
        raise NotImplementedError

    def add_active_element(
        self,
        type: Literal["sgen", "gen", "ext_grid"],
        params: Union[SGenParams, GenParams, ExtGridParams]
    ) -> int:
        if type == "sgen":
            return pp.create_sgen(self.net, **params)
        elif type == "gen":
            return pp.create_gen(self.net, **params)
        elif type == "ext_grid":
            return pp.create_ext_grid(self.net, **params)
        else:
            raise ValueError(f"Unsupported element type: {type}")

    
    def add_passive_element(): # load, shunt, impedance, dcline
        raise NotImplementedError

    def add_sensors(): #control
        raise NotImplementedError
    
    
    

        