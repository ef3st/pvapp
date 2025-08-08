import pandapower as pp
import json

# import pandapower.plotting as plot
# import matplotlib.pyplot as plt

from typing import (
    Protocol,
    runtime_checkable,
    Union,
    Optional,
    Tuple,
    Literal,
    TypedDict,
    List,
)
import pandas as pd
from utils.logger import get_logger


# ===============================
#!   TypedDict for Grid Elements
# ===============================
class SGenParams(TypedDict, total=False):
    bus: int
    p_mw: float
    q_mvar: Optional[float]
    name: Optional[str]
    scaling: float
    in_service: bool
    type: Optional[str]


class LineParams(TypedDict, total=False):
    from_bus: int
    to_bus: int
    length_km: float
    name: str
    std_type: str


class BusParams(TypedDict, total=False):
    vn_kv: Union[str, float, None]
    name: Optional[str]
    geodata: Optional[Tuple]
    type: Optional[Literal["b", "n", "m"]]
    zone: Union[None, int, str]
    in_service: bool
    min_vm_pu: Optional[float]
    max_vm_pu: Optional[float]


class GenParams(TypedDict, total=False):
    bus: int
    p_mw: Optional[float]
    vm_pu: float
    name: Optional[str]
    q_mvar: Optional[float]
    min_q_mvar: Optional[float]
    max_q_mvar: Optional[float]
    sn_mva: Optional[float]
    slack: Optional[bool]
    scaling: Optional[float]
    in_service: bool
    controllable: Optional[bool]


class ExtGridParams(TypedDict, total=False):
    bus: int
    vm_pu: float
    va_degree: float
    name: Optional[str]
    in_service: bool


class StorageParam(TypedDict, total=False):
    bus: int
    p_mw: float
    max_e_mwh: float
    soc_percent: float
    min_e_mwh: float
    q_mvar: float
    sn_mva: float
    controllable: bool
    name: str
    in_service: bool
    type: str
    scaling: float


# ===================================
#!   CLASS FOR POWER GRID MANAGEMENT
# ===================================
class PlantPowerGrid:

    def __init__(self, path=None) -> None:
        self.logger = get_logger("solartracker")
        self.net: pp.pandapowerNet = pp.create_empty_network()
        if path:
            self.load_grid(path)

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

    def load_grid(self, path):
        self.net = pp.from_json(path)
        return self

    def save(self, path):
        pp.to_json(self.net, path)
        return self

    def create_bus(self, bus: BusParams) -> None:
        # TODO Create a logical method of indexing
        bus_index = pp.create_bus(self.net, **bus)

        # for k in bus.keys():
        #     if k not in self.buses_df.columns:
        #         self.buses_df[k] = None

        # self.buses_df.loc[bus_index] = pd.Series(bus)

    def link_buses(self, line: LineParams):
        # NOTE use pp.available_std_types(net)["line"] to get aviable line tipe (e.g, for LV "NAYY 4x50 SE")
        pp.create_line(self.net, **line)

    def aviable_link(self, start_bus: BusParams, end_bus: BusParams) -> int:
        if start_bus["name"] == end_bus["name"]:
            return 1
        if start_bus["vn_kv"] != end_bus["vn_kv"]:
            return 2
        start = self.get_element("bus", name=start_bus["name"], column="index")
        end = self.get_element("bus", name=end_bus["name"], column="index")
        if self.get_bus_links(start, end):
            return 3

        return 0

    def get_bus_links(self, bus1: int, bus2: int) -> list[str]:
        links = []
        net = self.net
        # Line
        if any(
            ((net.line["from_bus"] == bus1) & (net.line["to_bus"] == bus2))
            | ((net.line["from_bus"] == bus2) & (net.line["to_bus"] == bus1))
        ):
            links.append("line")

        # Transformer
        if any(
            ((net.trafo["hv_bus"] == bus1) & (net.trafo["lv_bus"] == bus2))
            | ((net.trafo["hv_bus"] == bus2) & (net.trafo["lv_bus"] == bus1))
        ):
            links.append("trafo")

        # Transformer 3-winding
        if (
            bus1 in net.trafo3w[["hv_bus", "mv_bus", "lv_bus"]].values
            and bus2 in net.trafo3w[["hv_bus", "mv_bus", "lv_bus"]].values
        ):
            links.append("trafo3w")

        # Impedance
        if any(
            ((net.impedance["from_bus"] == bus1) & (net.impedance["to_bus"] == bus2))
            | ((net.impedance["from_bus"] == bus2) & (net.impedance["to_bus"] == bus1))
        ):
            links.append("impedance")

        # DC Line
        if any(
            ((net.dcline["from_bus"] == bus1) & (net.dcline["to_bus"] == bus2))
            | ((net.dcline["from_bus"] == bus2) & (net.dcline["to_bus"] == bus1))
        ):
            links.append("dcline")

        # Bus-bus Switch
        sw_bus = net.switch[net.switch["et"] == "b"]
        if any(
            ((sw_bus["bus"] == bus1) & (sw_bus["element"] == bus2))
            | ((sw_bus["bus"] == bus2) & (sw_bus["element"] == bus1))
        ):
            links.append("bus_switch")

        return links

    def get_line_infos(self, type):
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

    def get_element(
        self,
        element: Literal["bus"] = None,
        index: Optional[int] = None,
        name: Optional[str] = None,
        column: Literal[
            "index", "name", "vn_kv", "type", "zone", "in_service", "geo", ""
        ] = "",
    ) -> str | pd.Series:
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
        return (
            len(self.net.sgen)
            + len(self.net.storage)
            + len(self.net.gen)
            + len(self.net.ext_grid)
        )

    def get_n_passive_elements(self):
        return None

    def get_sensors_controllers(self):
        return None

    def show_grid(self):
        from pandapower.plotting.plotly import simple_plotly

        # import plotly.graph_objects as go
        errors = self.runnet()
        from pandapower.plotting.generic_geodata import create_generic_coordinates

        # Usa plotly invece di matplotlib
        fig = None
        # if not errors:
        #     create_generic_coordinates(self.net, overwrite=True)
        #     fig = simple_plotly(self.net, respect_switches=True, auto_open=False)

        return fig, errors

    def runnet(self, timeseries: bool = False) -> List[str]:
        errors = self.check_prerequisites()
        if not errors:
            try:
                if timeseries:
                    from pandapower.timeseries import run_timeseries

                    run_timeseries(self.net)
                else:
                    pp.runpp(self.net)
            except pp.LoadflowNotConverged:
                self.logger.warning("[PlantPowerGrid] Power flow did not converge!")
            except Exception as e:
                self.logger.error(f"[PlantPowerGrid] Error running power flow: {e}")
        return errors

    def check_prerequisites(self) -> bool:
        """
        Verifica le condizioni minime per eseguire pp.runpp(net).
        Ritorna True se la rete è pronta, altrimenti solleva eccezioni.
        """
        net = self.net
        errors = []
        # 1. Verifica che ci siano bus
        if net.bus.empty:
            errors.append("La rete non contiene bus.")

        # 2. Verifica presenza di una fonte di tensione (ext_grid, gen, sgen, storage)
        has_power_source = (
            not net.ext_grid.empty
            or not net.gen.empty
            or not net.sgen.empty
            or not net.storage.empty
        )
        if not has_power_source:
            errors.append(
                "Nessuna fonte di potenza presente (ext_grid/gen/sgen/storage)."
            )

        # 3. Verifica che tutti i bus abbiano vn_kv valido
        if (net.bus.vn_kv <= 0).any():
            errors.append("Alcuni bus hanno vn_kv <= 0 (tensione nominale non valida).")

        # 4. Verifica che tutti i componenti siano collegati a bus esistenti
        for comp in ["load", "sgen", "gen", "ext_grid", "storage"]:
            if not getattr(net, comp).empty:
                invalid = ~getattr(net, comp)["bus"].isin(net.bus.index)
                if invalid.any():
                    errors.append(f"{comp}: riferimenti a bus inesistenti.")

        if not net.line.empty:
            invalid_from = ~net.line["from_bus"].isin(net.bus.index)
            invalid_to = ~net.line["to_bus"].isin(net.bus.index)
            if invalid_from.any() or invalid_to.any():
                errors.append("Linee collegate a bus inesistenti.")

        # 5. Verifica che ci sia almeno un elemento con vm_pu definito (per inizializzazione)
        if net.ext_grid.empty and net.gen.empty:
            errors.append(
                "⚠️ Nessun generatore controllato in tensione (ext_grid/gen): il calcolo potrebbe fallire."
            )

        # 6. Verifica che non ci siano bus isolati
        # (opzionale: controlla se ci sono nodi disconnessi)
        # --> si può aggiungere in base al livello di dettaglio desiderato

        return errors  # rete pronta

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

    # Power from PV module
    def update_sgen_power(self, type=None, power=None):
        if power is None:
            raise ValueError(
                "The 'power' parameter must be a numeric value (not None)."
            )
        if not isinstance(power, (int, float)):
            raise TypeError("The 'power' parameter must be a number (int or float).")

        for idx, sgen in self.net.sgen.iterrows():
            if type is None or type in sgen["name"]:
                self.net.sgen.at[idx, "p_mw"] = power

    def create_controllers(
        self, element: Literal["sgen"], data_source: pd.DataFrame
    ) -> None:
        """
        Create controllers for the grid elements.
        """
        from pandapower.control import ConstControl

        ConstControl(
            self.net,
            element=element,
            variable="p_mw",
            element_index=data_source.columns,
            profile_name=data_source.columns,
            drop_same_existing_ctrl=True,
        )
