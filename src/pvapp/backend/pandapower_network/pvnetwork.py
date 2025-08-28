import json
from typing import (
    Union,
    Optional,
    Tuple,
    Literal,
    TypedDict,
    List,
)

import pandas as pd
import pandapower as pp
from pandapower import toolbox as tb  # noqa: F401  # kept if you used it elsewhere
from tools.logger import get_logger


# =========================================================
#                       TypedDicts
# =========================================================
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


# =========================================================
#                        Constants
# =========================================================

# Link availability return codes (kept as ints for backward compatibility)
LINK_OK = 0
LINK_ERR_SAME_BUS = 1
LINK_ERR_VOLTAGE_MISMATCH = 2
LINK_ERR_DUPLICATE = 3


# * =========================================================
# *                 PlantPowerGrid (Main Class)
# * =========================================================
class PlantPowerGrid:
    """
    Thin domain wrapper around a pandapowerNet with convenience methods for
    CRUD operations, validation, summaries, and simple simulation helpers.

    Design goals:
      - Keep UI-independent, side-effect-light helpers here.
      - Provide predictable return types and small, composable utilities.
      - Avoid raising on normal "not found" lookups; return None where sensible.
    """

    # ------------------------ Lifecycle / IO ------------------------

    def __init__(self, path: Optional[str] = None) -> None:
        """
        Initialize an empty pandapower network. Optionally load from JSON.

        Args:
            path: Optional path to a .json file previously exported by pandapower.
        """
        self.logger = get_logger("pvapp")
        self.net: pp.pandapowerNet = pp.create_empty_network()
        if path:
            self.load_grid(path)

    def load_grid(self, path: str) -> "PlantPowerGrid":
        """
        Load grid from a pandapower JSON file.

        Args:
            path: File path to pandapower JSON.

        Returns:
            Self for chaining.
        """
        self.net = pp.from_json(path)
        return self

    def save(self, path: str) -> "PlantPowerGrid":
        """
        Persist current grid to disk in pandapower JSON format.

        Args:
            path: Destination file path.

        Returns:
            Self for chaining.
        """
        pp.to_json(self.net, path)
        return self

    # ------------------------ CRUD: Buses & Links ------------------------

    def create_bus(self, bus: BusParams) -> int:
        """
        Create a bus and return its index.

        Note:
            Pandapower assigns the DataFrame index; we return it for later reference.
        """
        return int(pp.create_bus(self.net, **bus))

    def update_bus(self, bus_index: int, bus: BusParams) -> None:
        """
        Update a bus row in-place.

        Args:
            bus_index: Existing bus index (must exist in net.bus.index).
            bus: Fields to update.

        Raises:
            ValueError: If the given bus_index does not exist.
        """
        if bus_index not in self.net.bus.index:
            raise ValueError(f"Bus index {bus_index} does not exist in the network.")
        for k, v in bus.items():
            self.net.bus.at[bus_index, k] = v

    def link_buses(self, line: LineParams) -> int:
        """
        Create a line between two buses.

        Args:
            line: LineParams including
                - from_bus,
                - to_bus,
                - std_type,
                - length_km,
                - name

        Returns:
            The created line index (pandapower line table index).
        """
        return int(pp.create_line(self.net, **line))

    def available_link(self, start_bus: BusParams, end_bus: BusParams) -> int:
        """
        Check whether a link between two buses is allowed by simple rules.

        Rules:
          1) Same-named bus → not allowed (return LINK_ERR_SAME_BUS)
          2) Different nominal voltages → not allowed (return LINK_ERR_VOLTAGE_MISMATCH)
          3) Already connected by any known connector → not allowed (return LINK_ERR_DUPLICATE)

        Args:
            start_bus: A bus record (at least 'name' and 'vn_kv' should be provided).
            end_bus: A bus record.

        Returns:
            int: LINK_OK (0) if available, otherwise an error code (1..3).
        """
        if start_bus["name"] == end_bus["name"]:
            return LINK_ERR_SAME_BUS

        if start_bus["vn_kv"] != end_bus["vn_kv"]:
            return LINK_ERR_VOLTAGE_MISMATCH

        start = self.get_element("bus", name=start_bus["name"], column="index")
        end = self.get_element("bus", name=end_bus["name"], column="index")
        if start is None or end is None:
            # If one of the buses doesn't exist, treat as not linkable here.
            return LINK_ERR_DUPLICATE

        if self.get_bus_links(int(start), int(end)):
            return LINK_ERR_DUPLICATE

        return LINK_OK

    def get_bus_links(self, bus1: int, bus2: int) -> List[str]:
        """
        Return a list of connector types that already join two buses.

        Connector types checked:
          - 'line', 'trafo', 'trafo3w', 'impedance', 'dcline', 'bus_switch'
        """
        links: List[str] = []
        net = self.net

        # Lines
        if not net.line.empty:
            mask = ((net.line["from_bus"] == bus1) & (net.line["to_bus"] == bus2)) | (
                (net.line["from_bus"] == bus2) & (net.line["to_bus"] == bus1)
            )
            if bool(mask.any()):
                links.append("line")

        # 2-winding transformers
        if not net.trafo.empty:
            mask = ((net.trafo["hv_bus"] == bus1) & (net.trafo["lv_bus"] == bus2)) | (
                (net.trafo["hv_bus"] == bus2) & (net.trafo["lv_bus"] == bus1)
            )
            if bool(mask.any()):
                links.append("trafo")

        # 3-winding transformers (if both appear among hv/mv/lv)
        if not net.trafo3w.empty:
            cols = ["hv_bus", "mv_bus", "lv_bus"]
            if bus1 in net.trafo3w[cols].values and bus2 in net.trafo3w[cols].values:
                links.append("trafo3w")

        # Series impedance
        if not net.impedance.empty:
            mask = (
                (net.impedance["from_bus"] == bus1) & (net.impedance["to_bus"] == bus2)
            ) | (
                (net.impedance["from_bus"] == bus2) & (net.impedance["to_bus"] == bus1)
            )
            if bool(mask.any()):
                links.append("impedance")

        # DC lines
        if not net.dcline.empty:
            mask = (
                (net.dcline["from_bus"] == bus1) & (net.dcline["to_bus"] == bus2)
            ) | ((net.dcline["from_bus"] == bus2) & (net.dcline["to_bus"] == bus1))
            if bool(mask.any()):
                links.append("dcline")

        # Bus-bus switch (et == 'b')
        if not net.switch.empty:
            sw_bus = (
                net.switch[net.switch["et"] == "b"]
                if "et" in net.switch.columns
                else net.switch.iloc[0:0]
            )
            if not sw_bus.empty:
                mask = ((sw_bus["bus"] == bus1) & (sw_bus["element"] == bus2)) | (
                    (sw_bus["bus"] == bus2) & (sw_bus["element"] == bus1)
                )
                if bool(mask.any()):
                    links.append("bus_switch")

        return links

    # ------------------------ CRUD: Generators & Others ------------------------

    def add_active_element(
        self,
        type: Literal["sgen", "gen", "ext_grid"],
        params: Union[SGenParams, GenParams, ExtGridParams],
    ) -> int:
        """
        Add an active element (sgen, gen, ext_grid) to the network.

        Args:
            type: Element family to create.
            params: Parameters dictionary for the selected element.

        Returns:
            The created element index within its pandapower table.

        Raises:
            ValueError: If element type is unsupported.
        """
        if type == "sgen":
            return int(pp.create_sgen(self.net, **params))
        if type == "gen":
            return int(pp.create_gen(self.net, **params))
        if type == "ext_grid":
            return int(pp.create_ext_grid(self.net, **params))
        raise ValueError(f"Unsupported element type: {type}")

    def add_transformer(self):  # placeholder
        raise NotImplementedError

    def add_switch(self):  # placeholder
        raise NotImplementedError

    def add_passive_element(self):  # load, shunt, impedance, dcline
        raise NotImplementedError

    def add_sensors(self):  # control
        raise NotImplementedError

    # ------------------------ Lookups & Accessors ------------------------

    def get_element(
        self,
        element: Literal["bus"] = None,
        index: Optional[int] = None,
        name: Optional[str] = None,
        column: Literal[
            "index", "name", "vn_kv", "type", "zone", "in_service", "geo", ""
        ] = "",
    ) -> Union[None, str, pd.Series, int, float]:
        """
        Retrieve a bus (or a field) by name or index.

        Args:
            element: Currently only 'bus' is supported.
            index (int | None): Bus index to select.
            name (str | None): Bus name to select.
            column (str): If empty, returns the full row (as DataFrame slice).
                    If 'index', returns the index int.
                    If a column name (e.g. 'vn_kv'), returns that value.

        Returns:
            The requested value, or None if not found / unsupported.
        """
        if element != "bus":
            return None

        df = self.net.bus

        if name is not None:
            mask = (
                (df["name"] == name)
                if "name" in df.columns
                else pd.Series(False, index=df.index)
            )
            if not mask.any():
                return None
            result = df[mask]
        elif index is not None:
            if index not in df.index:
                return None
            result = df.loc[[index]]
        else:
            return None

        if column == "":
            return result
        if column == "index":
            return int(result.index[0])
        if column in df.columns:
            return result[column].values[0]
        return None

    def get_line_infos(self, std_type: str) -> pd.Series:
        """
        Return the standard type record for a given line std_type.
        """
        return pp.available_std_types(self.net).loc[std_type]

    def get_available_lines(self) -> List[str]:
        """
        List all available line standard types in the current net.
        """
        return list(pp.available_std_types(self.net).index)

    # Backward-compat alias (typo)
    def get_aviable_lines(self) -> List[str]:  # noqa: D401
        """Alias of get_available_lines (kept for backward compatibility)."""
        return self.get_available_lines()

    # ------------------------ Counts / Small summaries ------------------------

    def get_n_nodes_links(self) -> int:
        """Return the number of buses."""
        return int(len(self.net.bus))

    def get_n_active_elements(self) -> int:
        """Return a count of sgen + storage + gen + ext_grid."""
        return int(
            len(self.net.sgen)
            + len(self.net.storage)
            + len(self.net.gen)
            + len(self.net.ext_grid)
        )

    def get_n_passive_elements(self):
        """Placeholder for passive elements count."""
        return None

    def get_sensors_controllers(self):
        """Placeholder for sensors/controllers count."""
        return None

    # ------------------------ Simulation / Plot ------------------------

    def runnet(self, timeseries: bool = False) -> List[str]:
        """
        Run a power flow (or timeseries) if prerequisites are satisfied.

        Args:
            timeseries: If True, run pandapower timeseries; otherwise runpp.

        Returns:
            A list of error strings. Empty list means the run was attempted.
        """
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
                errors.append("Power flow did not converge!")
            except Exception as e:
                self.logger.error(f"[PlantPowerGrid] Error running power flow: {e}")
                errors.append(f"{e}")
        return errors

    def show_grid(self):
        """
        (Placeholder) Build a plotly figure and return (fig, errors).

        Note:
            Current implementation returns (None, errors) unless you enable the plotting code.
        """
        # from pandapower.plotting.plotly import simple_plotly
        # from pandapower.plotting.generic_geodata import create_generic_coordinates
        errors = self.runnet()
        fig = None
        # if not errors:
        #     create_generic_coordinates(self.net, overwrite=True)
        #     fig = simple_plotly(self.net, respect_switches=True, auto_open=False)
        return fig, errors

    def is_plot_ready(self) -> bool:
        """
        Check whether the network has enough data to produce a plot.

        Criteria:
          1) At least one bus AND one link (line or transformer).
          2) 'geo' column exists in bus and has at least one non-null value.
          3) Non-null 'geo' values are valid JSON or a dict-like.
        """
        bus_geo = self.net.bus.get("geo", None)

        if self.net.bus.empty:
            return False
        if self.net.line.empty and self.net.trafo.empty:
            return False
        if bus_geo is None or bus_geo.isnull().all():
            return False

        for val in bus_geo.dropna():
            if isinstance(val, dict):
                continue
            try:
                json.loads(val)
            except Exception:
                return False

        return True

    # ------------------------ Controllers / Profiles ------------------------

    def update_sgen_power(
        self, type: Optional[str] = None, power: Optional[float] = None
    ):
        """
        Set p_mw for all sgens whose 'name' contains a given substring (or for all if type is None).

        Args:
            type: Substring to match in sgen name. If None, update all sgens.
            power: New active power in MW. Must be numeric.

        Raises:
            ValueError, TypeError: On invalid 'power'.
        """
        if power is None:
            raise ValueError(
                "The 'power' parameter must be a numeric value (not None)."
            )
        if not isinstance(power, (int, float)):
            raise TypeError("The 'power' parameter must be a number (int or float).")

        for idx, sgen in self.net.sgen.iterrows():
            name = str(sgen.get("name", "")) if "name" in self.net.sgen.columns else ""
            if type is None or (type and type in name):
                self.net.sgen.at[idx, "p_mw"] = power

    def create_controllers(
        self, element: Literal["sgen"], data_source: pd.DataFrame
    ) -> None:
        """
        Create constant controllers for a given element family using a profile DataFrame.

        Args:
            element: Currently 'sgen' supported.
            data_source: A DataFrame whose columns map element indices and profile names.
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

    # ------------------------ Validation / Readiness ------------------------

    def check_prerequisites(self) -> List[str]:
        """
        Validate minimum conditions to run a power flow.

        Returns:
            List of error messages. Empty list means the network is ready to attempt runpp.
        """
        net = self.net
        errors: List[str] = []

        # 1) There must be buses
        if net.bus.empty:
            errors.append("La rete non contiene bus.")

        # 2) At least one power source
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

        # 3) All buses must have a valid vn_kv
        if "vn_kv" in net.bus.columns and (net.bus.vn_kv <= 0).any():
            errors.append("Alcuni bus hanno vn_kv <= 0 (tensione nominale non valida).")

        # 4) Each element must reference existing buses
        for comp in ["load", "sgen", "gen", "ext_grid", "storage"]:
            df = getattr(net, comp, None)
            if df is not None and not df.empty:
                if "bus" in df.columns:
                    invalid = ~df["bus"].isin(net.bus.index)
                    if invalid.any():
                        errors.append(f"{comp}: riferimenti a bus inesistenti.")

        # Lines must reference existing buses
        if not net.line.empty:
            invalid_from = ~net.line["from_bus"].isin(net.bus.index)
            invalid_to = ~net.line["to_bus"].isin(net.bus.index)
            if invalid_from.any() or invalid_to.any():
                errors.append("Linee collegate a bus inesistenti.")

        # 5) At least one voltage-controlled element (ext_grid/gen) helps initialization
        if net.ext_grid.empty and net.gen.empty:
            errors.append(
                "⚠️ Nessun generatore controllato in tensione (ext_grid/gen): il calcolo potrebbe fallire."
            )

        # 6) Optional: add an isolated-bus check if needed

        return errors

    # ------------------------ Summaries / Projections ------------------------

    def summarize_buses(self) -> pd.DataFrame:
        """
        Build a DataFrame with one row per bus and useful metadata + connected elements.

        Returns:
            DataFrame with columns:
              - name, type, voltage_kv, in_service, min_vm_pu, max_vm_pu
              - elements: list[dict] per bus with {"name","type","index"} for connected elements.
        """
        # ---- Base bus frame ----
        buses = self.net.bus.copy()
        out = pd.DataFrame(index=buses.index)
        out["name"] = buses["name"] if "name" in buses.columns else ""
        out["type"] = buses["type"] if "type" in buses.columns else ""
        out["voltage_kv"] = buses["vn_kv"] if "vn_kv" in buses.columns else pd.NA
        out["in_service"] = (
            buses["in_service"] if "in_service" in buses.columns else True
        )
        out["min_vm_pu"] = buses["min_vm_pu"] if "min_vm_pu" in buses.columns else None
        out["max_vm_pu"] = buses["max_vm_pu"] if "max_vm_pu" in buses.columns else None

        # Prepare connections collector (ordered, no duplicates per (type, index))
        connections = {int(b): [] for b in buses.index}
        seen_keys = {int(b): set() for b in buses.index}

        def add_conn(bus_idx, etype: str, eindex: int, ename: Optional[str]):
            """Attach a connection to a bus, deduplicated by (etype,eindex)."""
            if pd.isna(bus_idx):
                return
            b = int(bus_idx)
            key = (etype, int(eindex))
            if b not in connections:
                connections[b] = []
                seen_keys[b] = set()
            if key in seen_keys[b]:
                return
            label = (
                ename.strip() if (ename and str(ename).strip()) else f"{etype} {eindex}"
            )
            connections[b].append(
                {"name": str(label), "type": str(etype), "index": int(eindex)}
            )
            seen_keys[b].add(key)

        # What to scan: {element_table: [bus_columns]}
        mapping = {
            "line": ["from_bus", "to_bus"],
            "trafo": ["hv_bus", "lv_bus"],
            "trafo3w": ["hv_bus", "mv_bus", "lv_bus"],
            "impedance": ["from_bus", "to_bus"],
            "dcline": ["from_bus", "to_bus"],
            "load": ["bus"],
            "sgen": ["bus"],
            "gen": ["bus"],
            "storage": ["bus"],
            "shunt": ["bus"],
            "ward": ["bus"],
            "xward": ["bus"],
            "motor": ["bus"],
            "ext_grid": ["bus"],
            "switch": ["bus"],
        }

        for etype, bus_cols in mapping.items():
            if not hasattr(self.net, etype):
                continue
            df = getattr(self.net, etype)
            if df is None or len(df) == 0:
                continue

            cols_present = [c for c in bus_cols if c in df.columns]
            if not cols_present:
                continue

            for eindex, row in df.iterrows():
                ename = None
                if "name" in df.columns:
                    val = row.get("name")
                    if pd.notna(val) and str(val).strip():
                        ename = str(val)
                for c in cols_present:
                    add_conn(row[c], etype, eindex, ename)

        out["elements"] = out.index.map(lambda b: connections.get(int(b), []))
        return out

    def bus_connections(
        self,
        *,
        include_out_of_service: bool = True,
        trafo3w_pairs: Tuple[str, ...] = ("hv-mv", "hv-lv"),
        include_bus_bus_switches: bool = True,
        role_suffix_for_trafo3w: bool = True,
    ) -> pd.DataFrame:
        """
        Return a normalized DataFrame of direct bus-to-bus connections.

        Columns:
          - type  : 'line' | 'trafo' | 'trafo3w' | 'dcline' | 'impedance' | 'switch'
          - id    : element index in its pandapower table
          - name  : element display name
          - start : (bus_name, bus_index)
          - end   : (bus_name, bus_index)
        """

        def bus_tuple(bi: int) -> Tuple[str, int]:
            bi = int(bi)
            if "name" in self.net.bus.columns:
                nm = self.net.bus.at[bi, "name"]
                if pd.notna(nm) and str(nm).strip():
                    return (str(nm), bi)
            return (f"bus {bi}", bi)

        def elem_name(df: pd.DataFrame, idx: int, etype: str) -> str:
            if "name" in df.columns:
                val = df.at[idx, "name"]
                if pd.notna(val) and str(val).strip():
                    return str(val)
            return f"{etype} {idx}"

        rows: List[dict] = []

        # Lines
        if hasattr(self.net, "line") and len(self.net.line):
            df = self.net.line
            if not include_out_of_service and "in_service" in df.columns:
                df = df[df["in_service"] == True]
            for idx, r in df.iterrows():
                if "from_bus" in r and "to_bus" in r:
                    rows.append(
                        {
                            "type": "line",
                            "id": int(idx),
                            "name": elem_name(self.net.line, idx, "line"),
                            "start": bus_tuple(r["from_bus"]),
                            "end": bus_tuple(r["to_bus"]),
                        }
                    )

        # DC lines
        if hasattr(self.net, "dcline") and len(self.net.dcline):
            df = self.net.dcline
            if not include_out_of_service and "in_service" in df.columns:
                df = df[df["in_service"] == True]
            for idx, r in df.iterrows():
                if "from_bus" in r and "to_bus" in r:
                    rows.append(
                        {
                            "type": "dcline",
                            "id": int(idx),
                            "name": elem_name(self.net.dcline, idx, "dcline"),
                            "start": bus_tuple(r["from_bus"]),
                            "end": bus_tuple(r["to_bus"]),
                        }
                    )

        # Series impedance
        if hasattr(self.net, "impedance") and len(self.net.impedance):
            df = self.net.impedance
            if not include_out_of_service and "in_service" in df.columns:
                df = df[df["in_service"] == True]
            for idx, r in df.iterrows():
                if "from_bus" in r and "to_bus" in r:
                    rows.append(
                        {
                            "type": "impedance",
                            "id": int(idx),
                            "name": elem_name(self.net.impedance, idx, "impedance"),
                            "start": bus_tuple(r["from_bus"]),
                            "end": bus_tuple(r["to_bus"]),
                        }
                    )

        # 2-winding transformers
        if hasattr(self.net, "trafo") and len(self.net.trafo):
            df = self.net.trafo
            if not include_out_of_service and "in_service" in df.columns:
                df = df[df["in_service"] == True]
            for idx, r in df.iterrows():
                if "hv_bus" in r and "lv_bus" in r:
                    rows.append(
                        {
                            "type": "trafo",
                            "id": int(idx),
                            "name": elem_name(self.net.trafo, idx, "trafo"),
                            "start": bus_tuple(r["hv_bus"]),
                            "end": bus_tuple(r["lv_bus"]),
                        }
                    )

        # 3-winding transformers (expanded to pairs)
        if hasattr(self.net, "trafo3w") and len(self.net.trafo3w):
            df = self.net.trafo3w
            if not include_out_of_service and "in_service" in df.columns:
                df = df[df["in_service"] == True]
            for idx, r in df.iterrows():
                if all(k in r for k in ("hv_bus", "mv_bus", "lv_bus")):
                    base = elem_name(self.net.trafo3w, idx, "trafo3w")
                    hv, mv, lv = int(r["hv_bus"]), int(r["mv_bus"]), int(r["lv_bus"])

                    if "hv-mv" in trafo3w_pairs:
                        nm = f"{base} (hv-mv)" if role_suffix_for_trafo3w else base
                        rows.append(
                            {
                                "type": "trafo3w",
                                "id": int(idx),
                                "name": nm,
                                "start": bus_tuple(hv),
                                "end": bus_tuple(mv),
                            }
                        )
                    if "hv-lv" in trafo3w_pairs:
                        nm = f"{base} (hv-lv)" if role_suffix_for_trafo3w else base
                        rows.append(
                            {
                                "type": "trafo3w",
                                "id": int(idx),
                                "name": nm,
                                "start": bus_tuple(hv),
                                "end": bus_tuple(lv),
                            }
                        )
                    if "mv-lv" in trafo3w_pairs:
                        nm = f"{base} (mv-lv)" if role_suffix_for_trafo3w else base
                        rows.append(
                            {
                                "type": "trafo3w",
                                "id": int(idx),
                                "name": nm,
                                "start": bus_tuple(mv),
                                "end": bus_tuple(lv),
                            }
                        )

        # Bus-bus switches (optional)
        if (
            include_bus_bus_switches
            and hasattr(self.net, "switch")
            and len(self.net.switch)
        ):
            df = self.net.switch
            mask = (
                (df["et"] == "b")
                if "et" in df.columns
                else pd.Series(False, index=df.index)
            )
            if not include_out_of_service and "closed" in df.columns:
                mask = mask & (df["closed"] == True)
            df = df[mask]
            if "bus" in df.columns and "element" in df.columns:
                for idx, r in df.iterrows():
                    rows.append(
                        {
                            "type": "switch",
                            "id": int(idx),
                            "name": elem_name(self.net.switch, idx, "switch"),
                            "start": bus_tuple(r["bus"]),
                            "end": bus_tuple(r["element"]),
                        }
                    )

        return pd.DataFrame(rows, columns=["type", "id", "name", "start", "end"])
