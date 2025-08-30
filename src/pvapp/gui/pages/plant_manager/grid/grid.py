from __future__ import annotations

from pathlib import Path
from typing import (
    Optional,
    Tuple,
    List,
    Union,
    TypedDict,
    Dict,
    Any,
    Literal,
    Callable,
    Iterable,
)

import json
import re
import streamlit as st
import streamlit_antd_components as sac
from streamlit.errors import StreamlitAPIException
from bidict import bidict

from ...page import Page
from backend.pandapower_network.pvnetwork import (
    PlantPowerGrid,
    BusParams,
    LineParams,
    GenParams,
    SGenParams,
)
from tools.logger import get_logger
import pandas as pd
from analysis.plantanalyser import PlantAnalyser
import pydeck as pdk
from ....utils.plots import plots


# TODO :
# - Change name of ***_manager method in ***_tab exept for bus_links_manager that became bus_links_tab
# - Move _element_role_for_bus in Pandapower manager
# - Dialog Class
# NOTE:
#! BUG SEVERE:
# BUG:

# * ======== GLOBAL CONFIG VARIABLES ========
# ? Map of element types -> bus reference fields in pandapower
# TODO: take/move this from/to pvnetwork.py (there is the same in summarize_buses method)
EL_BUS_FIELDS: Dict[str, List[str]] = {
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

# ? Bootstrap icons for each element
ICON_MAP: Dict[str, str] = {
    "bus": "crosshair",
    "line": "arrow-left-right",
    "trafo": "bezier2",
    "trafo3w": "bezier",
    "impedance": "slash-circle",
    "dcline": "arrows-fullscreen",
    "load": "download",
    "sgen": "lightning-charge",
    "gen": "lightning-charge",
    "storage": "battery-charging",
    "shunt": "node-plus",
    "ward": "collection",
    "xward": "collection-fill",
    "motor": "gear",
    "ext_grid": "plug-fill",
    "switch": "toggle2-on",
}
# ? List of element names that represent a connection among buses
# TODO: move this in pvnetwork.py
CONNECTION_ELEMENTS = [
    "line",
    "trafo",
    "trafo3w",
    "dcline",
    "impedance",
    "switch",
]

# // -----------------------------------------------------------------------------------------------------------------------


# * ==============================
# *          Utilities
# * ==============================
def normalize_element_spec(
    el: Union[Tuple[str, int], Dict[str, Any], str],
) -> Tuple[str, Optional[int], Optional[str]]:
    """
    Normalize different element spec shapes to (etype, eid, label_hint).

    Args:
        el (tuple[str,int] | dict[str,Any] | str): element parameters in an accepted format

    Returns:
        Tuple[str,Optional[int],Optional[str]]:
            - element type (e.g. "line", "bus"...)
            - element index in the relative pd.Dataframe from pandapower (e.g. from net.bus if it is a bus)
            - element name
    ----
    Note:
    Accepted input per element in `elements` list:
    - ('line', 5)
    - {'type': 'line', 'index': 5, 'name': 'L5'}
    - {'table': 'line', 'idx': 5}
    - 'line:5'  (etype:index)
    - 'line'    (no id)

    """
    if isinstance(el, tuple) and len(el) >= 2:
        return str(el[0]), int(el[1]), None
    if isinstance(el, dict):
        etype = str(el.get("type") or el.get("table") or el.get("elem_type") or "")
        eid = el.get("index", el.get("idx", el.get("id")))
        name = el.get("name")
        return etype, (int(eid) if eid is not None else None), name
    if isinstance(el, str):
        if ":" in el:
            etype, eid = el.split(":", 1)
            try:
                return etype.strip(), int(eid.strip()), None
            except ValueError:
                return etype.strip(), None, eid.strip()
        return el.strip(), None, None
    # Fallback
    return "", None, None


def element_role_for_bus(
    net: Any, etype: str, eid: Optional[int], bus_idx: int
) -> Optional[str]:
    """
    If `net` is provided and element ID (eid) is known, this returns which bus field(s)
    of the element match this bus (e.g., 'from_bus', 'lv_bus').
    -----
    TODO: move this in PlantPowerGrid class in pvnetwork.py
    """
    try:
        fields = EL_BUS_FIELDS.get(etype, [])
        if not fields or eid is None:
            return None
        table = getattr(net, etype, None)
        if table is None:  # or len(table) <= eid:
            return None
        row = table.loc[eid] if eid in table.index else None
        if row is None:
            return None
        hits = [f for f in fields if f in row.index and int(row[f]) == int(bus_idx)]
        if not hits:
            return None
        return "/".join(hits)
    except Exception as e:
        get_logger("pvapp").warning(
            f"[element_role_for_bus] Something wrong in this function: {e}"
        )
        return None


def status_badge(key_prefix: str, voltage: str, level: str, onoff: str) -> None:
    """Render a read-only segmented status badge of a bus with voltage level + bus level + in service state
    Args:
        voltage (str): bus operation voltage (typically `LV`,`MV`,`HV`,`EHV`)
        level (str): grid level of the bus (typycally `Main`,`Auxiliary` or `Moff`)
        onoff (str): bus activated or not string (`ON`,`OFF`)
    """
    items = [sac.SegmentedItem(x) for x in (voltage, level, onoff)]
    sac.segmented(
        items=items,
        color="green" if onoff == "ON" else "red",
        index=2,
        bg_color="#043b41",
        size="sm",
        key=f"{key_prefix}_{voltage}_{level}_{onoff}",
        align="end",
        readonly=True,
    )


def build_sac_tree_from_bus_df(
    bus_df: pd.DataFrame,
    *,
    bus_name_col: str = "name",
    bus_index_col: str = None,  # if None, use DataFrame index as bus index
    elements_col: str = "elements",
    net: Any = None,  # optional pandapower net to annotate roles
    open_all: bool = True,
    show_line: bool = True,
    checkbox: bool = False,
    show_connectors: bool = True,
    index: Optional[int] = None,
    return_index: bool = False,
    childrend_disabled=True,
    with_meta: bool = True,
) -> Dict[str, Any] | Tuple[Dict[str, Any], Dict[int, Dict[str, Any]]]:
    """
    Create `sac.tree` kwargs (items + sensible defaults) from a bus DataFrame
    that includes an "elements" column (each cell: list of connected elements).

    Args:
        bus_df (pandas.DataFrame): Rielaborated bus DataFrame from
            `pandapowerNet["bus"]`, with an "elements" column listing the elements
            connected to each bus.
        bus_name_col (str): Column label for bus names.
        bus_index_col (str): Column label for bus indices. If None, the DataFrame
            index is used as the bus index.
        elements_col (str): Column label for connected elements
            ("elements" by default).
        net (pandapowerNet): Network object used to identify bus roles.
        open_all (bool): Whether to expand all tree nodes initially. Defaults to True
            (see `sac.Tree` params).
        show_line (bool): Whether to display lines. Defaults to True (see `sac.Tree` params).
        checkbox (bool): Whether to display checkboxes. Defaults to False.
        show_connectors (bool): If True, also include connectors such as lines,
            transformers, switches, etc.
        index (int): Default selected tree element index.
        return_index (bool): Whether to return the index instead of the value.
            Defaults to False (see `sac.Tree` params).

    Returns:
        dict: Dictionary ready to be unpacked into `sac.tree(**result)`.

    Raises:
        ValueError:
            - if `bus_name_col` or `elements_col` not in `bus_df`
    ------
    Note:

        Expected DataFrame columns:
            - `bus_name_col`: Display name of the bus.
            - `bus_index_col`: (optional) Numeric bus index; if None, use row index.
            - `elements_col`: List of element specs per bus. Each spec can be:
                ('line', 5)
                {'type': 'line', 'index': 5, 'name': 'L5'}
                {'table': 'line', 'idx': 5}
                'line:5'
                'line'

        Icons are assigned based on `ICON_MAP`. Unknown types fall back to a generic
        icon. If `net` is provided, the element label includes the matching bus
        role(s).
    """
    if bus_name_col not in bus_df.columns:
        raise ValueError(f"'{bus_name_col}' column not found in bus_df")
    if elements_col not in bus_df.columns:
        raise ValueError(f"'{elements_col}' column not found in bus_df")
    items: List[sac.TreeItem] = []
    meta: Dict[int, Dict[str, Any]] = (
        {}
    )  # preorder index -> {"type": str, "index": int, "label": str}
    running_idx = 0  # preorder counter aligned to sac.tree

    def _label_for_element(
        etype: str, eid: Optional[int], name_hint: Optional[str], role: Optional[str]
    ) -> str:
        base = name_hint or (f"{etype} {eid}" if eid is not None else etype)
        return f"{base} ({role})" if role else base

    # helper per creare TreeItem + aggiornare meta con indice preorder
    def _make_item(
        label: str,
        icon: str,
        payload: Optional[Tuple[str, Optional[int]]],
        children: Optional[List[sac.TreeItem]] = None,
        disabled: bool = False,
    ) -> sac.TreeItem:
        nonlocal running_idx, meta
        node = sac.TreeItem(
            label, icon=sac.BsIcon(icon), children=children or [], disabled=disabled
        )
        # registra meta solo se richiesto
        if with_meta:
            etype, eid = payload or (None, None)
            meta[running_idx] = {"type": etype, "index": eid, "label": label}
        running_idx += 1
        return node

    for _, row in bus_df.reset_index(drop=True).iterrows():
        bus_idx = int(row[bus_index_col]) if bus_index_col else int(row.name)
        bus_label = f"[{bus_idx}]  -  {row[bus_name_col]}"
        icon_bus = ICON_MAP.get("bus", "diagram-3")
        children: List[sac.TreeItem] = []
        for el in row[elements_col] or []:
            etype, eid, name_hint = normalize_element_spec(el)
            if not etype:
                continue
            if not show_connectors and etype in CONNECTION_ELEMENTS:
                continue
            role = (
                element_role_for_bus(net, etype, eid, bus_idx)
                if net is not None
                else None
            )
            label = _label_for_element(etype, eid, name_hint, role)
            icon = ICON_MAP.get(etype, "box")
            # child payload = (etype, eid)
            child_item = _make_item(
                label, icon, (etype, eid), children=None, disabled=childrend_disabled
            )
            children.append(child_item)
        # bus payload = ("bus", bus_idx)
        items.append(
            _make_item(
                str(bus_label),
                icon_bus,
                ("bus", bus_idx),
                children=children,
                disabled=False,
            )
        )
    kwargs = dict(
        items=items,
        open_all=open_all,
        show_line=show_line,
        checkbox=checkbox,
        format_func=None,
        return_index=return_index,
        index=index,
    )
    return (kwargs, meta) if with_meta else kwargs


def resolve_tree_selection(
    tree_output: Union[int, str, None],
    meta: Dict[int, Dict[str, Any]],
    *,
    return_index: bool,
) -> Optional[Tuple[str, int]]:
    """
    Translate sac.tree() selection into (etype, eid).

    Parameters
    ----------
    tree_output : int | str | None
        The value returned by sac.tree(...). If return_index=True -> int (preorder position).
        If return_index=False -> str (label of the selected node).
        Can be None if nothing selected.
    meta : dict
        Meta map produced by `build_sac_tree_from_bus_df(..., with_meta=True)`.
        Keys are preorder indices; values include {"type","index","label"}.
    return_index : bool
        Must match the 'return_index' you used for sac.tree.

    Returns
    -------
    (etype, eid) | None
        - etype: "bus", "line", "sgen", "trafo", ...
        - eid:   integer index of the element in pp net tables
        None if selection is empty or cannot be resolved.
    """
    if tree_output is None:
        return None

    if return_index:
        # tree_output è l'indice preorder
        info = meta.get(int(tree_output))
        if not info or info["type"] is None or info["index"] is None:
            return None
        return (str(info["type"]), int(info["index"]))

    # return_index == False: tree_output è un'etichetta
    selected_label = str(tree_output)
    for _, info in meta.items():
        if (
            info.get("label") == selected_label
            and info.get("type") is not None
            and info.get("index") is not None
        ):
            return (str(info["type"]), int(info["index"]))
    return None


# ================  SGEN TYPES =================
class PVParams(TypedDict):
    module_per_string: int
    strings_per_inverter: int


def sgen_type_detection(obj: Union[PVParams, None]) -> int:
    """Return the SGen type index.
    0 -> Photovoltaic (PV)
    1 -> Generic SGen (others)
    """
    if obj is None:
        return 1
    if isinstance(obj, dict) and (
        ("module_per_string" in obj) and ("strings_per_inverter" in obj)
    ):
        return 0
    raise ValueError("Invalid SGen type or parameters provided.")


# // -----------------------------------------------------------------------------------------------------------------------
# * =============================
# *        Grid Manager UI
# * =============================
class GridManager(Page):
    """
    Interactive UI controller for creating, editing, and analyzing electrical grids
    in a PlantPowerGrid model within a Streamlit application.

    This class implements a multi-tab interface for managing different categories of
    grid elements (links, generators, passive components, sensors) and provides
    reusable UI primitives to streamline the addition, configuration, and persistence
    of elements. It also handles state management between UI sessions, validation,
    and file persistence of grid and PV array configurations.

    Parameters
    ----------
    subfolder : pathlib.Path
        Path to the plant data directory. This directory must contain or will be used
        to create the `grid.json` file representing the PlantPowerGrid configuration.

    Attributes
    ----------
    grid_file : pathlib.Path
        Full path to the `grid.json` file inside the plant's subfolder.

    grid : PlantPowerGrid (property)
        Instance of the current grid model loaded from `grid_file`, or a new
        empty PlantPowerGrid if no file exists.

    pv_arrays : dict[int, PVParams] (property)
        Mapping from SGen element indices (in the Pandapower `sgen` DataFrame)
        to PV array configuration parameters (`PVParams`) staged for persistence.

    Notes
    -----
    **UI Structure**
        - Tab 0: **Links**
            Buses, lines, transformers, and switches.
        - Tab 1: **Generators**
            Static generators (`sgen`), synchronous generators (`gen`), and storage.
        - Tab 2: **Passive elements**
            Placeholder for future passive element management.
        - Tab 3: **Sensors & controllers**
            Placeholder for measurement and control devices.

    **Design Considerations**
        - All session state keys are prefixed to avoid collisions.
        - Provides modular "parameter editor" functions (e.g. `bus_params`, `line_params`)
          to render consistent editors for each element type.
        - Uses helper builders (e.g. `__build_items`) for dynamic, repeatable UI patterns.
        - Integrates with `PlantPowerGrid` for CRUD operations.

    Methods
    -------
    render_setup() -> bool
        Render the main setup UI with tabs for each element category. Returns True if
        changes were made to the grid.

    render_analysis() -> None
        Render placeholder analysis UI.

    get_scheme() -> None
        Show schematic placeholder of the grid.

    get_description() -> None
        Display textual summary of the grid.

    save() -> None
        Save the current grid and any staged PV arrays to the plant's data folder.

    render_tab_bus_links() -> bool
        Render the Links tab, including UI for adding and managing buses, lines, and transformers.

    paramsUI_bus(...)
        Render and return the editor for a bus element.

    paramsUI_line(...)
        Render and return the editor for a line element.

    _bus_links_manager()
        Display tree view of buses and connected elements, plus connection table.

    _manager_buses()
        Manage bus properties and show connected elements via a tree structure.

    _manager_connections()
        Manage and display all bus-to-bus connections with color-coded voltage levels.

    _add_bus() / _add_line() / _add_transformer()
        UI handlers for creating new buses, lines, or transformers.

    _build_buses() / _build_line()
        Builder functions returning data from their respective parameter editors.

    render_tab_active_elements() -> bool
        Render the Generators tab with controls for SGen, Gen, and Storage.

    paramsUI_sgen(...)
        Render and return the editor for a static generator element (SGen) and optional PV properties.

    paramsUI_gen(...)
        Render and return the editor for a synchronous generator element (Gen).

    _add_sgen() / _add_gen() / _add_storage()
        UI handlers for creating new SGen, Gen, or Storage elements.

    _build_sgens() / _build_gens()
        Builder functions returning data from their respective parameter editors.

    passive_manager()
        Placeholder UI for managing passive components.

    sensors_manager()
        Placeholder UI for managing sensors and controllers.

    __build_items(...)
        Generic dynamic UI builder for repeating parameter editors in a grid layout.

    __batch_add_with_auto_name(...)
        Batch-create elements with automatic name disambiguation.

    _change_element(...)
        Generic dialog for editing either bus or line elements depending on provided parameters.
    -----

    TODO
    -----
    - Change logic in state variable "arrays_to_add"
    """

    # ========== LIFECYCLE ==========
    def __init__(self, subfolder: Path) -> None:
        """
        Args:
            subfolder: path of the Plant data directory
        """
        super().__init__("grid_manager")
        self.grid_file: Path = subfolder / "grid.json"

        # ? STATE VARIABLE "plant_grid": to save the current PlantPowerGrid selected in PlantManager Page
        # ? - empty PlantPowerGrid() if the relative file is absent
        if self.grid_file.exists():
            st.session_state["plant_grid"] = PlantPowerGrid(self.grid_file)
        else:
            st.session_state["plant_grid"] = PlantPowerGrid()
        # ? STATE VARIABLE "arrays_to_add": PV arrays pending to be save
        st.session_state["arrays_to_add"] = {}

    # ========== PROPERTIES ==========
    @property
    def grid(self) -> PlantPowerGrid:
        """PlantPowerGrid class for the selected plant"""
        return st.session_state.get("plant_grid", PlantPowerGrid())

    @property
    def pv_arrays(self) -> Dict[int, PVParams]:
        """PV arrays staged for persistence (keyed by the index of SGen pandas.DataFrame (from panpapowernet managed by PlantPowerGrid class))."""
        if "arrays_to_add" not in st.session_state:
            self.logger.debug(
                f"[GridManager] `arrays_to_add` not defined, so {{}} has been returned "
            )
        return st.session_state.get("arrays_to_add", {})

    # =============== RENDERS ============
    def render_setup(self) -> bool:
        """Render setup UI. `True` is returned if the grid changed: this is verified when some buttons related to changes are pressed

        Returns:
            bool: `True` if something changed in the PlanPowerGrid class, `False` otherwise

        ----
        TODO: Add message to show if and which element(s) is(are) missing to have an available grid
        """
        if not self.grid_file.exists():
            # Inline import to avoid hard dependency when not needed.
            from streamlit_elements import mui, elements

            with elements("grid_error"):
                mui.Alert(
                    f"NO GRID: {self.T('messages.no_grid')}",
                    severity="warning",
                    variant="outlined",
                )

        titles: Dict[str, Dict[str, Any]] = self.T("tabs")
        tags = {
            "links": self.grid.get_n_nodes_links(),
            "gens": self.grid.get_n_active_elements(),
            "passive": self.grid.get_n_passive_elements(),
            "sensors": self.grid.get_sensors_controllers(),
        }
        tab = sac.tabs(
            [
                sac.TabsItem(label=titles[key]["title"], tag=f"{tags[key]}")
                for key in titles
            ],
            align="center",
            use_container_width=True,
            return_index=True,
            color="orange",
        )

        placeholder = st.empty()
        with placeholder.container():
            changed = False
            # -----
            # NOTE Tabs rendering with errors controls
            # -----
            # ? Map of the tab index with relative method and a label for errors
            tab_funcs = {
                0: ("bus/links tab", self.render_tab_bus_links),
                1: ("active elements tab", self.render_tab_active_elements),
                2: ("passive elements tab", self.passive_manager),
                3: ("sensors tab", self.sensors_manager),
            }
            # ? Tab rendering selection
            tab_name, func = tab_funcs.get(tab, (None, None))
            if func is not None:
                # inline fct to handle try/except
                def run_tab():
                    try:
                        return func()
                    except StreamlitAPIException as e:
                        self.logger.error(
                            f"[Gridmanager] Something wrong in RENDERING {tab_name}: {e}"
                        )
                        st.toast(
                            f"⚠️ Something wrong in RENDERING {tab_name}: look at Logs Page"
                        )
                        return False
                    except Exception as e:
                        self.logger.error(
                            f"[Gridmanager] Something wrong in {tab_name}: {e}"
                        )
                        st.toast(f"❌ Something wrong in {tab_name}: look at Logs Page")
                        return False

                changed |= run_tab()

        return changed

    def render_analysis(self):
        path: Path = self.grid_file.parent / "simulation.csv"
        if path.exists():
            kwargs, meta = build_sac_tree_from_bus_df(
                self.grid.summarize_buses(),
                bus_name_col="name",
                elements_col="elements",
                net=self.grid.net,
                childrend_disabled=False,
                with_meta=True,
            )
            selected = sac.tree(key="analysis_tree", **kwargs)
            picked = resolve_tree_selection(
                selected, meta, return_index=kwargs["return_index"]
            )
            if picked:
                etype, eid = picked
                # st.write(f"Selected: {etype} #{eid}")
                analyser = PlantAnalyser(self.grid_file.parent)
                periodic_report: pd.DataFrame = analyser.periodic_report(
                    etype=etype, idx=eid
                )
                if periodic_report is None or periodic_report.empty:
                    st.warning("No data available for the selected element")
                else:
                    plots.seasonal_plot(periodic_report, "plant_performance")
                numeric = analyser.numeric_dataframe(etype=etype, idx=eid)
                if numeric is None or numeric.empty:
                    st.warning("No numeric data available for the selected element")
                else:
                    plots.time_plot(numeric, page="plant_performance")
            else:
                st.write("No valid selection")

        else:
            st.warning("⚠️ Simulation not performed")

    def render_data(self):
        path: Path = self.grid_file.parent / "simulation.csv"
        if path.exists():
            analyser = PlantAnalyser(self.grid_file.parent)
            st.dataframe(analyser.grid)
        else:
            st.warning("⚠️ Simulation not performed")

    # =========== SUMMARIES ==========
    def get_scheme(self):
        sac.alert(
            "Scheme info",
            "Scheme not yet available. Take a coffee in the meanwhile",
            size="md",
            variant="quote",
            icon=True,
        )

    def get_description(self) -> None:
        """Show a compact textual resume of the grid."""
        sac.divider("Grid Resume", align="center")
        st.text_area(
            "text_area",
            value=str(self.grid.net),
            label_visibility="collapsed",
            disabled=True,
            height=153,
        )

    # ============ GENERIC COMMANDS ===========
    def save(self) -> None:
        """Save the grid and any staged PV arrays to plant data dir"""
        try:
            self.grid.save(self.grid_file)
        except Exception as e:
            self.logger.error(
                f"[GridManager] Something wrong in saving grid in dir /{self.grid_file}: {e}"
            )
            st.toast("❌ Grid saving doesn't went well. Look at the Logs page")
        if self.pv_arrays:
            try:
                arrays: Dict[str, Any] = {}
                path = self.grid_file.parent / "arrays.json"
                if path.exists():
                    with path.open("r", encoding="utf-8") as f:
                        arrays = json.load(f)
                # ? Update and write back
                arrays.update({str(k): v for k, v in self.pv_arrays.items()})
                with path.open("w", encoding="utf-8") as f:
                    json.dump(arrays, f, indent=4, ensure_ascii=False)
                # ? Empty the state variable that saves new pv arrays
                st.session_state["arrays_to_add"] = {}
            except Exception as e:
                self.logger.error(
                    f"[GridManager] Something wrong in saving PV arrays in dir /{self.grid_file}: {e}"
                )
                st.toast("❌ PV Arrays saving doesn't went well. Look at the Logs page")

    # =========================================================
    #                         TABS
    # =========================================================

    # ============= LINKS (BUSES / LINES / TX) TAB ===============
    # -------------> Tab Content <--------
    def render_tab_bus_links(self) -> bool:
        """
        TODO:
            - check below `grid_modified` state variable
            - once an adder is used, delete the created element from the adders
        """
        # ? Translator semplifier
        labels_root = "tabs.links"

        def T(key):
            return self.T(f"{labels_root}.{key}")

        changed = False
        # ------ Adder -----
        with st.expander(T("new_item"), icon="➕"):
            try:
                items = T("item")
                item = sac.chip(
                    items=[sac.ChipItem(items[i]["name"]) for i in items],
                    label=T("select_item"),
                    index=[0, 2],
                    radius="md",
                    variant="light",
                    return_index=True,
                )
            except Exception as e:
                self.logger.warning(f"Something wrong here: {e}")
            with st.container():
                try:
                    if item == 0:
                        changed |= self._add_bus()
                    elif item == 1:
                        changed |= self._add_line()
                    elif item == 2:
                        changed |= self._add_transformer()
                except Exception as e:
                    self.logger.error(
                        f"[GridManager] Something wrong in adding item {item} (0=bus,1=line,2=transformer): {e}"
                    )
                    st.toast("❌ Something wrong in ADDERS. Look at the Log page")

        # ------ Manager -----
        with st.container():
            # ? STATE VARIABLE "grid_modified": to check if some grid element in buses/links tab. If True, something changed
            # TODO: maybe this will be managed upper in che code flux
            if "grid_modified" not in st.session_state:
                st.session_state["grid_modified"] = False
            changed |= st.session_state["grid_modified"]
            if st.session_state["grid_modified"]:
                st.session_state["grid_modified"] = False
            try:
                self._bus_links_manager()
            except Exception as e:
                self.logger.error(
                    f"[GridManager] Something wrong in manager Buses or links: {e}"
                )
                st.toast(
                    "❌ Something wrong working with BUSES and LINKS. Look at the Log page"
                )
        return changed

    # -------------> Parameter editors <-------------
    def paramsUI_bus(
        self,
        borders: bool = True,
        id: Union[int, str] = 1,
        quantity: bool = True,
        bus: Optional[BusParams] = None,
    ) -> Tuple[int, BusParams]:
        """
        Render the editor for a Bus and return the selected configuration.

        If `quantity` is `True`, a `streamlit.number_input` is displayed and its
        value is included in the return tuple together with the chosen bus parameters.

        Args:
            id (int): Bus identifier (typically the index in the buses DataFrame).
                Must be unique for each call, since it is used to create state
                variables and allow multiple parameter UIs in the same session.
            bus (BusParams, optional): Existing bus setup to pre-populate the UI.
                If provided, its values are shown in the editor.
            quantity (bool, optional): Defaults to `True`. If `True`, a
                `streamlit.number_input` is shown and its value returned.
                Used in the bus-adder workflow.
            borders (bool, optional): If `True`, the UI is wrapped inside a
                `streamlit.container` with borders.

        Returns:
            Tuple[int,BusParams]:
                - `int`: the value from `streamlit.number_input` if `quantity=True`,
                  otherwise the constant 1.
                - `BusParams`: the configuration dictionary with the selected bus
                  parameters.
        """
        # ? Translator semplifier
        labels_root = "tabs.links.item.bus"

        def T(key):
            return self.T(f"{labels_root}.{key}")

        # Default BusParams if None is passed
        if bus is None:
            bus = BusParams(name="New_Bus", vn_kv=0.230, type="b", in_service=True)

        n_new_bus: Optional[int] = 1

        with st.container(border=borders):
            titles = T("titles")
            left, right = st.columns([1, 2])

            with left:  # GENERIC PROPERTIES OF THE BUS
                sac.divider(label=titles[0], align="center", key=f"{id}_bus_prop_div")
                bus["name"] = st.text_input(
                    "Name",
                    label_visibility="collapsed",
                    value=bus["name"],
                    key=f"{id}_bus_name",
                )

                # ? sac.segmented to choose bus level in the grid by name (e.g. "Principal" or "Auxiliary")
                type_idx = bidict({"b": 0, "n": 1, "m": 2})
                idx = sac.segmented(
                    items=[sac.SegmentedItem(label) for label in T("bus_level")],
                    direction="vertical",
                    color="grey",
                    index=type_idx[bus["type"]],
                    return_index=True,
                    align="center",
                    key=f"{id}_bus_type",
                )
                bus["type"] = type_idx.inv[idx]

                bus["in_service"] = sac.switch(
                    T("in_service"),
                    value=bool(bus["in_service"]),
                    position="left",
                    align="center",
                    key=f"{id}_bus_on",
                )

                if quantity:
                    sac.divider("Quantity", key=f"{id}_bus_quantity_div")
                    n_new_bus = st.number_input(
                        "Quantity",
                        label_visibility="collapsed",
                        step=1,
                        min_value=1,
                        value=1,
                        key=f"{id}_bus_quantity",
                    )

            with right:  # VOLTAGE PROPERTIES OF THE BUS
                sac.divider(label=titles[1], align="center", key=f"{id}_bus_volt_div")
                simple_selection_col, value_selection_col = st.columns(2)

                voltage_contraints = {
                    "LV": (0.0, 1.0),
                    "MV": (1.0, 35.0),
                    "HV": (36.0, 220.0),
                    "EHV": (220.0, 800.0),
                }
                voltage_type = bidict({"LV": 0, "MV": 1, "HV": 2, "EHV": 3})
                voltages = {"LV": 0.250, "MV": 15.0, "HV": 150.0, "EHV": 380.0}
                with simple_selection_col:
                    #! To check if it works well
                    idx = next(
                        (
                            voltage_type[i]
                            for i, (a, b) in voltage_contraints.items()
                            if a <= bus["vn_kv"] <= b
                        ),
                        0,
                    )
                    # ? sac.segmented to choose bus voltage level by words (e.g. "Low", "Hight" voltage)
                    voltage_idx = sac.segmented(
                        items=[sac.SegmentedItem(label) for label in T("voltage")],
                        direction="vertical",
                        color="grey",
                        index=idx,
                        align="center",
                        return_index=True,
                        key=f"{id}_bus_voltage_str",
                    )
                    labels = T("constraints")
                    # ? checkbox to enable voltage contraints
                    enable_limits = st.checkbox(labels[0], key=f"{id}_bus_set_limits")

                with value_selection_col:
                    constraints = voltage_contraints[voltage_type.inv[voltage_idx]]
                    # * currently disable, this is the input to set the bus voltage.
                    # the selection occurs via voltage_idx variable and voltages dict
                    bus["vn_kv"] = st.number_input(
                        labels[1],
                        disabled=True,
                        value=voltages[voltage_type.inv[voltage_idx]],
                        key=f"{id}_bus_volt_int",
                    )
                    # ---- VOLTAGE CONSTRAINTS  ----
                    min_vm = st.number_input(
                        labels[2],
                        value=float(constraints[0]),
                        disabled=not enable_limits,
                        key=f"{id}_bus_min_volt",
                    )
                    max_vm = st.number_input(
                        labels[3],
                        value=float(constraints[1]),
                        disabled=not enable_limits,
                        key=f"{id}_bus_max_volt",
                    )
                    if enable_limits:
                        bus["min_vm_pu"] = min_vm
                        bus["max_vm_pu"] = max_vm

        return int(n_new_bus or 1), bus

    def paramsUI_line(
        self,
        borders: bool = True,
        id: Union[int, str] = 1,
        line: Optional[LineParams] = None,
        horizontal: bool = True,
    ) -> Tuple[bool, LineParams]:
        """
        Render the editor for a Line and return the selected configuration.

        If `horizontal` is `True`, the UI is larger with some bus selection params closer. Otherwise, bus params are one under the other

        Args:
            id (int): Line identifier (typically the index in the Lines DataFrame).
                Must be unique for each call, since it is used to create state
                variables and allow multiple parameter UIs in the same session.
            bus (LineParams, optional): Existing bus setup to pre-populate the UI.
                If provided, its values are shown in the editor.
            borders (bool, optional): If `True`, the UI is wrapped inside a
                `streamlit.container` with borders.

        Returns:
            Tuple[bool,LineParams]:
                - `bool`: `True` if the line is available for the creation, `False` otherwise
                - `LineParams`: the configuration dictionary with the selected line
                  parameters.

        ----
        TODO: modify available_line check also for manager and not only for the creation
        """
        # ? Translator semplifier
        labels_root = "tabs.links.item.link"

        def T(key):
            return self.T(f"{labels_root}.{key}")

        line_types = self.grid.get_available_lines()

        # Default LineParams if None is passed
        if line is None:
            line = LineParams(
                from_bus=0,
                to_bus=0,
                length_km=0.1,
                name="New_(NAVY 4x50 SE)_0.1km",
                std_type=line_types[0] if line_types else "",
            )

        def select_bus(
            align: Literal["start", "end"] = "start", bus_id: Optional[int] = None
        ) -> int:
            """Render a bus selector and return the chosen index."""
            a = b = c = d = st.container()
            if horizontal:
                if align == "start":
                    a, b = st.columns([1, 10])  # noqa: F841 - reserved
                    c, d = st.columns(2)
                else:
                    b, a = st.columns([10, 1])  # noqa: F841 - reserved
                    d, c = st.columns(2)

            with c:  # Bus selection by name
                sac.divider(
                    T("bus_identity")[0],
                    align=align,
                    key=f"{id}_line_{align}_bus_name_div",
                )
                if bus_id is None:
                    bus_id = 0
                name = st.selectbox(
                    label="Bus name",
                    label_visibility="collapsed",
                    options=list(
                        self.grid.net.get("bus")["name"]
                    ),  # ? Takes the options from the names of buses saved in the current PowerPlantGrid
                    index=bus_id,
                    key=f"{id}_line_{align}_bus_name",
                )
            with d:  # Bus index (Currently selection is not available)
                sac.divider(
                    T("bus_identity")[1],
                    align=align,
                    key=f"{id}_line_{align}_bus_index_div",
                )
                index = st.number_input(
                    label="Bus Index",
                    label_visibility="collapsed",
                    disabled=True,
                    value=self.grid.get_element("bus", name=name, column="index"),
                    key=f"{id}_line_{align}_bus_index",
                )

            with b:  # sac.segmented to check the bus level by words (e.g. "Auxiliary")
                level_map = {"b": 0, "n": 1, "m": 2}
                level_val = self.grid.get_element("bus", index=index, column="type")
                level_idx = level_map.get(level_val, None)
                sac.segmented(
                    items=[sac.SegmentedItem(lbl) for lbl in T("bus_level")],
                    align="center",
                    color="cyan",
                    size="sm",
                    key=f"{id}_line_{align}_bus_level",
                    index=level_idx,
                    direction=("horizontal" if horizontal else "vertical"),
                    readonly=True,
                )
            return int(index)

        with st.container(border=borders):
            first, line_box, second = st.columns([1, 2, 1])

            with first:  # STARTING BUS
                sac.divider(
                    T("buses")[0],
                    align="center",
                    variant="dashed",
                    key=f"{id}_line_startbus_div",
                )
                start_bus = select_bus("start", line["from_bus"])

            with second:  # END BUS
                sac.divider(
                    T("buses")[1],
                    align="center",
                    variant="dashed",
                    key=f"{id}_line_endbus_div",
                )
                end_bus = select_bus("end", line["to_bus"])

            with line_box:  # LINE
                labels = T("line_params")
                a = b = c = st.container()
                if horizontal:
                    a, b, c = st.columns([2, 1, 2])
                std_type = a.selectbox(
                    labels[0], options=line_types, key=f"{id}_line_type"
                )
                length = b.number_input(
                    f"{labels[1]} (km)",
                    value=float(line["length_km"]),
                    key=f"{id}_line_length",
                )
                name = c.text_input(
                    labels[2],
                    value=f"New_({std_type})_{length}km",
                    key=f"{id}_line_name",
                )

                # ----- LINE AVIABILITY CHECK  -----
                # ? error_map list of errors in the selected language
                # 0 - Link available (The line is achievable, the message is here just for convenience)
                # - ERRORS -
                # 1 - Same bus connected
                # 2 - Different buses voltage
                # 3 - Link already present
                error_map = T("errors")
                color = "green"
                buses_df = self.grid.net.bus
                line_available = True
                error_code = self.grid.available_link(
                    buses_df.iloc[start_bus], buses_df.iloc[end_bus]
                )
                if error_code:
                    color = "red"
                    line_available = False

                sac.divider(
                    error_map[error_code],
                    align="center",
                    size=5,
                    color=color,
                    variant="dotted",
                    key=f"{id}_line_status_div",
                )
                # ---- LINE/BUS INFO DISPLAY ----
                with st.expander(f"ℹ️ {T('infos')[0]}"):
                    line_tab, start_tab, end_tab = st.tabs(tabs=T("infos")[1:])
                    with start_tab:
                        st.text(f"{self.grid.net.bus.iloc[start_bus]}")
                    with end_tab:
                        st.text(f"{self.grid.net.bus.iloc[end_bus]}")
                    with line_tab:
                        st.text(f"{self.grid.get_line_infos(std_type)}")

            new_line = LineParams(
                from_bus=int(start_bus),
                to_bus=int(end_bus),
                length_km=float(length),
                name=str(name),
                std_type=str(std_type),
            )

        return line_available, new_line

    # -------------> Manager <--------
    # ----  Manage elements ----
    @st.fragment
    def _bus_links_manager(self):

        # ? Translator semplifier
        labels_root = "tabs.links.manager"

        def T(key):
            return self.T(f"{labels_root}.{key}")

        # --- BUS SUMUP IN A DATAFRAME SECTION ---
        df = self.grid.summarize_buses()  # pandas.DataFrame to show
        left, right = st.columns([3, 2])
        # Title
        with left:
            sac.alert(
                label=T("bus_df.title"),
                size=20,
                variant="quote-light",
                color="gray",
                icon=False,
            )
        # Legend
        legend_labels = T("bus_df.legend")
        legend_title = legend_labels[0]
        with right.expander(legend_title, icon="ℹ️"):
            labels = legend_labels[1]
            st.text(f"name: {labels[0]}")
            types = ["b", "n", "m"]
            types_legend = ""
            for i, j in zip(types, labels[1][1:]):
                types_legend += f"\n  - {i} = {j}"
            st.text(f"type: {labels[1][0]}{types_legend}")
            st.text(f"voltage_kv: {labels[2]} (kV)")
            st.text(f"in_service: {labels[3]}")
            st.text(f"min_vm_pu: {labels[4]}")
            st.text(f"max_vm_pu: {labels[5]}")

        st.dataframe(df.drop(columns=["elements"]))

        # --- MANAGER SECTION ---
        a, b = st.columns([1, 3])
        # Title
        with a:
            sac.alert(
                label=T("title"),
                size=20,
                variant="quote-light",
                color="gray",
                icon=False,
            )
        # Legend
        icons_labels = T("icon_label")
        with b.expander(icons_labels[0], icon="ℹ️"):
            icon_cols = st.columns(4)
            col = 0
            for i, icon in enumerate(ICON_MAP):
                if col == 4:
                    col = 0
                with icon_cols[col]:
                    sac.segmented(
                        items=[
                            sac.SegmentedItem(icon=ICON_MAP[icon]),
                            sac.SegmentedItem(icons_labels[1][icon]),
                        ],
                        index=None,
                        color="grey",
                        readonly=True,
                        size="sm",
                        bg_color="#043b41",
                    )
                col += 1
        # Managers
        tree_bus, connection = st.columns([2, 5])
        with connection:
            self._manager_connections()
        with tree_bus:
            self._manager_buses()

    @st.fragment
    def _manager_buses(self):
        """A streamlit_antd_components.tree is used to modify buses and see connected elements

        ----
        BUG: You can't choose the same bus with two consecutive selections
        """
        # ? Translator semplifier
        labels_root = "tabs.links.manager"

        def T(key):
            return self.T(f"{labels_root}.{key}")

        df = self.grid.summarize_buses().copy()
        # ? From this toggle it's possible avoid their print in the UI
        # -> Connectors are usually repeted and and useless in many cases.
        show_connectors = st.toggle(
            T("tree_connectors"), key="bus_tree_show_connectors"
        )
        with st.empty():
            kwargs = build_sac_tree_from_bus_df(
                self.grid.summarize_buses(),
                bus_name_col="name",
                elements_col="elements",
                net=self.grid.net,
                show_connectors=show_connectors,
                with_meta=False,
            )
            selected = sac.tree(key="original_tree", **kwargs)

            # ? STATE VARIABLE "tree_selected_bus": used to avoid repetitions due to sac elements
            if "tree_selected_bus" not in st.session_state:
                st.session_state["tree_selected_bus"] = selected

            # BUG: You can't choose the same bus with two consecutive selections
            if (
                selected and st.session_state["tree_selected_bus"] != selected
            ):  # when a new bus is selected
                st.session_state["tree_selected_bus"] = selected

                match = re.match(r"\[(\d+)\]", selected)
                if match:
                    bus_id = int(match.group(1))
                    bus = self.grid.net.bus.loc[bus_id].to_dict()
                    try:
                        self._change_element(
                            bus_id=bus_id,
                            params=BusParams(**bus),
                            connected_elements=df.loc[bus_id, "elements"],
                            type="bus",
                        )
                    except StreamlitAPIException as e:
                        self.logger.error(
                            f"[GridManagerPage] Streamlit error in bus change dialog: {e}"
                        )
                        st.toast(f"❌ Error in streamlit from MANAGER BUS: {e}")
                    except Exception as e:
                        self.logger.error(f"[GridManagerPage] Error in changing bus")
                        st.toast(f"❌ Error in changing bus: \n {e}", icon="❌")

    def _manager_connections(self):
        """
        Links are shown by their names and buses name at witch they are connected.
        Different switches are shown with different icons, while the buses voltage levels
        are printed with different colors

        NOTE:
            - Colors for bus voltage levels are choosen following a non-official color-graduation
        ----
        TODO:
            - make the print in the app faster
            - move values_contraints
        """
        # ? check to open a dialog with the selceted line params
        open_dialog = None

        # --- Legend ----
        values_contraints = {
            "LV": (0.0, 1.0),
            "MV": (1.0, 35.0),
            "HV": (36.0, 220.0),
            "EHV": (220.0, 800.0),
        }
        colors = {"LV": "#6E6E6E", "MV": "#2E7D32", "HV": "#1565C0", "EHV": "#C62828"}
        legend = st.columns([1, 1, 1, 1, 5])
        for col, i in enumerate(colors):
            with legend[col]:
                sac.divider(i, color=colors[i])
        sac.divider(
            variant="dotted",
        )
        # -------------

        def get_color(bus_idx):
            try:
                v = self.grid.net.bus["vn_kv"].iloc[bus_idx]
            except Exception as e:
                st.error(
                    f"❌ Error in uploading buses in get_color function of _manager_connections method: {e}"
                )
            # Check constriants
            for i in values_contraints:
                if v > values_contraints[i][0] and v < values_contraints[i][1]:
                    return colors[i]

        # ---  SHOW LINKS ---
        # [START BUS NAME]------(link_icon)----- *LINK NAME* ----(link_icon)----[END BUS NAME]
        # ? the only interactive part is the LINK_NAME that is actually a streamlit.button
        for row in self.grid.bus_connections().itertuples(index=False):
            cols = st.columns([2, 1.3, 2])
            # Starting bus
            with cols[0]:
                a, b = st.columns([1.5, 2])
                color = (get_color(row.start[1]),)
                with a:
                    sac.divider(
                        row.start[0],
                        variant="dashed",
                        align="start",
                        color=color,
                        key=f"left_div_{row.id}_{row.type}_{row.name}",
                    )
                with b:
                    sac.divider(
                        " ",
                        icon=sac.BsIcon(name=ICON_MAP[row.type], size="sm"),
                        color=color,
                        key=f"start_connection_{row.id}_{row.type}_{row.name}",
                    )

            # if a button of a link is pressed, open_dialog catch the ID of the connector to show the dialog
            if cols[1].button(
                row.name,
                type="tertiary",
                key=f"connection_{row.type}_{row.name}_{row.id}",
                use_container_width=True,
            ):
                connector = self.grid.net[row.type].loc[row.id].to_dict()
                open_dialog = connector

            # Ending bus
            with cols[2]:
                a, b = st.columns([2, 1.5])
                color = get_color(row.end[1])
                with a:
                    sac.divider(
                        " ",
                        icon=sac.BsIcon(name=ICON_MAP[row.type], size="sm"),
                        color=color,
                        align="end",
                        key=f"end_connection_{row.id}_{row.type}_{row.name}",
                    )
                with b:
                    sac.divider(
                        row.end[0],
                        variant="dashed",
                        align="end",
                        color=color,
                        key=f"right_div_{row.id}_{row.type}_{row.name}",
                    )

        # --- LINK MANAGER DIALOG ---
        if open_dialog:
            try:
                self._change_element(
                    params=LineParams(**open_dialog), line_id=None, type="line"
                )
            except StreamlitAPIException as e:
                self.logger.error(
                    f"[GridManagerPage] Streamlit error in connection change dialog: {e}"
                )
                st.toast(f" ❌ Error in streamlit for connection dialog: {e}")
            except NotImplementedError:
                st.toast(
                    "⚠️ This function is not implemented yet: you can't change lines for now"
                )

    # -------------> Adders <-------------
    def _add_bus(self) -> bool:
        """Bus adder UI. The output is a bool used to check if something has been added

        Returns:
            bool: `True` if add button is pressed
        """
        labels_root = "tabs.links.item.bus"
        new_buses = self._build_buses()
        if st.button(self.T(f"{labels_root}.buttons")[2]):
            for n_to_create, bus in new_buses:
                self.__batch_add_with_auto_name(
                    count=int(n_to_create),
                    obj=bus,
                    create_fn=lambda b: st.session_state["plant_grid"].create_bus(b),
                )
            return True
        return False

    def _add_line(self) -> bool:
        """Line adder UI. The output is a bool used to check if something has been added

        Returns:
            bool: `True` if add button is pressed and all lines are availables (checked in the `paramsUI_line`). `False` otherwise
        """
        labels_root = "tabs.links.item.link"
        # ? Check if it possible to build lines.
        # If there is no bus, lines are not achievable
        if len(self.grid.net.bus) == 0:
            st.error(self.T(f"{labels_root}.no_bus_error"))
            return False
        available, new_links = self._build_line()
        if st.button(self.T(f"{labels_root}.buttons")[2]):
            if available:
                for line in new_links:
                    st.session_state["plant_grid"].link_buses(line)
                return True
            st.error("Line creation failed.")
        return False

    def _add_transformer(self) -> bool:
        # TODO: Implement transformer creation UI
        sac.result("Transformer creation coming soon.", status="warning")
        return False

    # ------------- Builders --------
    def _build_buses(self, borders: bool = True) -> List[Tuple[int, BusParams]]:
        labels_root = "tabs.links.item.bus.buttons"
        # each bus editor returns (quantity, BusParams)
        _, items = self.__build_items(
            state_key="gm_new_bus",
            n_cols=3,
            render_param_fn=lambda i: self.paramsUI_bus(id=i),
            add_label=self.T(labels_root)[0],
            remove_label=self.T(labels_root)[1],
            borders=borders,
        )
        return items  # type: ignore[return-value]

    def _build_line(self, borders: bool = True) -> Tuple[bool, List[LineParams]]:
        labels_root = "tabs.links.item.link.buttons"
        all_valid, items = self.__build_items(
            state_key="gm_new_line",
            n_cols=1,  # line editors are wide; keeped one per row
            render_param_fn=lambda i: self.paramsUI_line(id=i),
            add_label=self.T(labels_root)[0],
            remove_label=self.T(labels_root)[1],
            borders=borders,
        )
        # filter and unwrap only the LineParams from (ok, LineParams)
        lines_to_add: List[LineParams] = [lp for ok, lp in items if ok]
        return all_valid, lines_to_add

    # ============= GENERATORS (ACTIVE) TAB ===============
    # -------------> Tab Content <--------
    def render_tab_active_elements(self) -> bool:
        # ? Translator semplifier
        labels_root = "tabs.gens"

        def T(key):
            return self.T(f"{labels_root}.{key}")

        with st.expander(T("new_item"), icon="➕"):
            items = T("item")
            item = sac.chip(
                items=[sac.ChipItem(items[i]["name"]) for i in items],
                label=T("select_item"),
                index=[0, 2],
                radius="md",
                variant="light",
                return_index=True,
            )
            changed = False
            if item == 0:
                changed |= self._add_sgen()
            elif item == 1:
                changed |= self._add_gen()
            elif item == 2:
                changed |= self._add_storage()
            return changed

    # -------------> Parameter editors <-------------
    def paramsUI_sgen(
        self,
        borders: bool = True,
        id: Union[int, str] = 1,
        sgen: Optional[SGenParams] = None,
        specficProps: Union[PVParams, None] = None,
        quantity: bool = True,
    ) -> Tuple[int, SGenParams, Union[PVParams, None]]:
        """Render the editor for a Static Generator (SGen) and return the selected configuration with possibily additional setup params for specific generators like PVs

        If `quantity` is `True`, a `streamlit.number_input` is displayed and its
        value is included in the return tuple together with the chosen sgen parameters.

        Args:
            id (int): SGen identifier (typically the index in the sgen DataFrame).
                Must be unique for each call, since it is used to create state
                variables and allow multiple parameter UIs in the same session.
            sgen (SGenParams, optional): Existing sgen setup to pre-populate the UI.
                If provided, its values are shown in the editor.
            quantity (bool, optional): Defaults to `True`. If `True`, a
                `streamlit.number_input` is shown and its value returned.
                Used in the sgen-adder workflow.
            borders (bool, optional): If `True`, the UI is wrapped inside a
                `streamlit.container` with borders.

        Returns:
            Tuple[int,SGenParams,Union[PVParams,None]]:
                - `int`: the value from `streamlit.number_input` if `quantity=True`,
                  otherwise the constant 1.
                - `SGenParams`: the configuration dictionary with the selected sgen
                  parameters.
                - `None` | `PVParams`: if necessary, specific params of the static generator are returned
                                    Currently only PV arrays used as SGen need
                                    n° of modules per string and  n° of strings, setted with `st.number_input`
                                    and saved in a predefined TypedDict

        ----
        TODO: Move voltage_constraints
        """
        # ? Translator semplifier
        labels_root = "tabs.gens.item.sgen"

        def T(key):
            return self.T(f"{labels_root}.{key}")

        bus_names = (
            list(self.grid.net.get("bus")["name"])
            if not self.grid.net.bus.empty
            else []
        )

        # Default SGenParams and PVParams if None is passed
        if sgen is None:
            bus_name = bus_names[0] if bus_names else None
            sgen = SGenParams(
                bus=bus_name,
                p_mw=0.4,
                q_mvar=0.0,
                name="New_PV",
                scaling=1.0,
                in_service=True,
            )
            if not specficProps is None:
                self.logger.warning("specficProps should be None when sgen is None")
                st.toast("⚠️ Look at Logs page")
            specficProps = PVParams(module_per_string=1, strings_per_inverter=1)
        # Input toggles and values defaults
        inputs = {
            "p_mw": [False, float(sgen["p_mw"])],
            "q_mvar": [False, float(sgen.get("q_mvar", 0.0))],
            "scaling": [False, float(sgen.get("scaling", 1.0))],
        }

        # Determine current SGen type from specific props
        current_type = sgen_type_detection(specficProps)

        with st.container(border=borders):
            labels = T("labels")
            a, b = st.columns(2)

            with a:  # --- SGEN GENERIC PROPERTIES ---
                if quantity:
                    sac.divider(
                        labels[1],
                        variant="dashed",
                        size="sm",
                        align="center",
                        key=f"{id}_sgen_quantity_div",
                    )
                    n_new_sgen = st.number_input(
                        labels[1],
                        key=f"{id}_sgen_quantity",
                        value=1,
                        min_value=1,
                        step=1,
                        label_visibility="collapsed",
                    )
                else:
                    n_new_sgen = 1

                # SGen type selection
                sac.divider(
                    T("titles")[0],
                    align="center",
                    key=f"{id}_sgen_prop_div",
                )
                sgen_type_idx = sac.segmented(
                    items=[sac.SegmentedItem("PV"), sac.SegmentedItem("Others")],
                    color="grey",
                    size="sm",
                    key=f"{id}_sgen_type",
                    index=current_type,
                    return_index=True,
                )
                sgen["name"] = st.text_input(
                    labels[0], key=f"{id}_sgen_name", value=sgen["name"]
                )
                sgen["in_service"] = sac.switch(
                    labels[2], value=bool(sgen["in_service"]), key=f"{id}_sgen_on"
                )

            with b:  # --- SGEN SETUP PARAMETERS ---
                sac.divider(
                    T("titles")[1],
                    align="center",
                    key=f"{id}_sgen_volt_div",
                )
                sgen["p_mw"] = st.number_input(
                    labels[3],
                    key=f"{id}_sgen_pmw_input",
                    value=inputs["p_mw"][1],
                    disabled=inputs["p_mw"][0],
                )
                sgen["scaling"] = st.number_input(
                    labels[4],
                    key=f"{id}_sgen_scale_input",
                    value=inputs["scaling"][1],
                    disabled=inputs["scaling"][0],
                )

                # * For PV we keep q_mvar disabled by default
                disable_q = sgen_type_idx == 0
                sgen["q_mvar"] = st.number_input(
                    labels[5],
                    key=f"{id}_sgen_qmvar_input",
                    value=inputs["q_mvar"][1],
                    disabled=disable_q,
                )

            # * --- SPECIFIC PROPERTIES SECTION ---
            if sgen_type_idx != current_type:
                specficProps = (
                    PVParams(module_per_string=1, strings_per_inverter=1)
                    if sgen_type_idx == 0
                    else None
                )
                st.toast(
                    "⚠️ Specific properties have been reset for the selected SGen type."
                )

            if sgen_type_idx == 0:  # if one want create a PV array
                with st.expander("⚡ PV Setup"):
                    left, right = st.columns(2)
                    specficProps = specficProps or PVParams(
                        module_per_string=1, strings_per_inverter=1
                    )
                    specficProps["module_per_string"] = left.number_input(
                        "module_per_string (Series)",
                        step=1,
                        min_value=1,
                        value=int(specficProps["module_per_string"]),
                        key=f"{id}_sgen_module_per_string",
                    )
                    specficProps["strings_per_inverter"] = right.number_input(
                        "strings_per_inverter (Parallel)",
                        step=1,
                        min_value=1,
                        value=int(specficProps["strings_per_inverter"]),
                        key=f"{id}_sgen_strings",
                    )
            else:
                specficProps = None

            # --- BUS SELECTION ---
            sac.divider(
                T("titles")[2],
                align="center",
                key=f"{id}_sgen_bus_div",
            )
            bus_cols = st.columns(2)
            bus_name = bus_cols[0].selectbox(
                "Bus",
                options=bus_names,
                label_visibility="collapsed",
                key=f"{id}_sgen_bus",
            )
            # TODO Move this
            voltage_constraints = {
                "LV": (0.0, 1.0),
                "MV": (1.0, 35.0),
                "HV": (36.0, 220.0),
                "EHV": (220.0, 800.0),
            }
            level_names = {
                key: T("bus_params.level")[i] for i, key in enumerate(["b", "n", "m"])
            }  # ? In the bus pd.DataFrame the types are identified with:
            # b = Main bus
            # n = auxiliary bus
            # m = Moff bus

            if bus_name:
                sgen["bus"] = self.grid.get_element(
                    "bus", name=bus_name, column="index"
                )
                bus_volt = self.grid.get_element("bus", name=bus_name, column="vn_kv")
                bus_level = level_names[
                    self.grid.get_element("bus", name=bus_name, column="type")
                ]
                voltage = next(
                    (
                        k
                        for k, (a, b) in voltage_constraints.items()
                        if a <= bus_volt <= b
                    ),
                    None,
                )
                bus_on = (
                    "ON"
                    if self.grid.get_element("bus", name=bus_name, column="in_service")
                    else "OFF"
                )
            else:
                voltage, bus_level, bus_on = "NaN", "NaN", "NaN"

            #! I don't remember why this was here
            # // segmenteds: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
            # // for v_label in ["LV", "MV", "HV", "EHV"]:
            # //     for lvl_label in [level_names[i] for i in level_names]:
            # //         for state in ["ON", "OFF"]:
            # //             key = (v_label, lvl_label, state)
            # //             segmenteds[key] = {
            # //                 "items": [sac.SegmentedItem(item) for item in key],
            # //                 "color": "green" if state == "ON" else "red",
            # //                 "index": 2,
            # //                 "bg_color": "#043b41",
            # //                 "size": "sm",
            # //                 "key": f"{id}_sgen_bus_prop_{v_label}_{lvl_label}_{state}",
            # //                 "align": "end",
            # //                 "readonly": True,
            # //             }

            with bus_cols[1]:  # BUS PROPERTIES
                status_badge(
                    key_prefix=f"{id}_bus_prop",
                    voltage=voltage,
                    level=bus_level,
                    onoff=bus_on,
                )

        return int(n_new_sgen), sgen, specficProps

    def paramsUI_gen(
        self,
        borders: bool = True,
        id: int = 1,
        gen: Optional[GenParams] = None,
        quantity: bool = True,
    ) -> Tuple[int, GenParams]:
        """Render the editor for a Static Generator (SGen) and return the selected configuration with possibily additional setup params for specific generators like PVs

        If `quantity` is `True`, a `streamlit.number_input` is displayed and its
        value is included in the return tuple together with the chosen sgen parameters.

        Args:
            id (int): Gen identifier (typically the index in the gen DataFrame).
                Must be unique for each call, since it is used to create state
                variables and allow multiple parameter UIs in the same session.
            gen (GenParams, optional): Existing gen setup to pre-populate the UI.
                If provided, its values are shown in the editor.
            quantity (bool, optional): Defaults to `True`. If `True`, a
                `streamlit.number_input` is shown and its value returned.
                Used in the gen-adder workflow.
            borders (bool, optional): If `True`, the UI is wrapped inside a
                `streamlit.container` with borders.

        Returns:
            Tuple[int,GenParams]:
                - `int`: the value from `streamlit.number_input` if `quantity=True`,
                  otherwise the constant 1.
                - `GenParams`: the configuration dictionary with the selected gen
                  parameters.

        ----
        TODO: Move voltage_constraints
        """

        # ? Translator semplifier
        labels_root = "tabs.gens.item.gen"

        def T(key):
            return self.T(f"{labels_root}.{key}")

        bus_names = (
            list(self.grid.net.get("bus")["name"])
            if not self.grid.net.bus.empty
            else []
        )

        n_new_gen: int
        # Default GenParams if None is passed
        if gen is None:
            bus_name = bus_names[0] if bus_names else None
            default_gen: Dict[str, GenParams] = {
                "slack": GenParams(
                    slack=True,
                    bus=bus_name,
                    vm_pu=1.0,
                    name="New_Gen_SLACK",
                    in_service=True,
                    p_mw=1.5,
                ),
                "non_slack": GenParams(
                    slack=False,
                    controllable=True,
                    name="New_Gen",
                    bus=bus_name,
                    p_mw=1.5,
                    vm_pu=1.0,
                    q_mvar=0.0,
                    min_q_mvar=-0.3,
                    max_q_mvar=0.3,
                    sn_mvar=2.0,
                    scaling=1.0,
                    in_service=True,
                ),
            }
            gen = default_gen["slack"]
        else:
            default_gen = {"slack": gen, "non_slack": gen}

        with st.container(border=borders):
            labels = T("labels")
            a, b = st.columns([3, 4])
            with a:  # --- GEN GENERIC PROPERTIES ---
                if quantity:
                    sac.divider(
                        labels[1],
                        variant="dashed",
                        size="sm",
                        align="center",
                        key=f"{id}_gen_quantity_div",
                    )
                    n_new_gen = int(
                        st.number_input(
                            "Quantity",
                            key=f"{id}_gen_quantity",
                            value=1,
                            min_value=1,
                            step=1,
                            label_visibility="collapsed",
                        )
                    )
                else:
                    n_new_gen = 1
                sac.divider(
                    T("titles")[0],
                    align="center",
                    key=f"{id}_gen_prop_div",
                )
                slack = sac.switch(
                    labels[3],
                    value=bool(gen.get("slack", False)),
                    key=f"{id}_gen_slack",
                )
                gen = default_gen["non_slack"] if not slack else default_gen["slack"]
                gen["name"] = st.text_input(
                    labels[0], key=f"{id}_gen_name", value=gen["name"]
                )
                gen["in_service"] = sac.switch(
                    labels[2], value=bool(gen["in_service"]), key=f"{id}_gen_on"
                )
                if not slack:
                    gen["controllable"] = sac.switch(
                        labels[4],
                        value=bool(gen.get("controllable", True)),
                        key=f"{id}_gen_controllable",
                    )
                else:
                    sac.switch(
                        labels[4],
                        value=True,
                        key=f"{id}_gen_controllable",
                        disabled=True,
                    )

            with b:  # --- GEN SETUP PARAMETERS ---
                sac.divider(
                    T("titles")[1],
                    align="center",
                    key=f"{id}_gen_volt_div",
                )

                if slack:
                    # For slack generators only voltage is usually controlled; keep simple placeholder control
                    st.number_input("vm_pu", value=float(gen.get("vm_pu", 1.0)))
                else:
                    disable_map = {
                        True: {
                            "vm_pu": False,
                            "q_mvar": True,
                            "min_q_mvar": False,
                            "max_q_mvar": False,
                        },
                        False: {
                            "vm_pu": True,
                            "q_mvar": False,
                            "min_q_mvar": True,
                            "max_q_mvar": True,
                        },
                    }
                    disabled = disable_map[bool(gen.get("controllable", True))]

                    left, right = st.columns([2.5, 1])
                    gen["p_mw"] = left.number_input(
                        labels[5], key=f"{id}_gen_power", value=float(gen["p_mw"])
                    )
                    gen["scaling"] = right.number_input(
                        labels[9],
                        key=f"{id}_gen_scale",
                        value=float(gen.get("scaling", 1.0)),
                    )
                    gen["sn_mvar"] = st.number_input(
                        labels[8],
                        key=f"{id}_gen_sn",
                        value=float(gen.get("sn_mvar", 2.0)),
                    )
                    gen["vm_pu"] = st.number_input(
                        labels[6],
                        value=float(gen.get("vm_pu", 1.0)),
                        disabled=disabled["vm_pu"],
                        key=f"{id}_gen_vm",
                    )

                    sac.divider(
                        f"{labels[7]} (MVAR)", align="start", key=f"{id}_gen_q_div"
                    )
                    gen["q_mvar"] = st.number_input(
                        "Reactive power",
                        value=float(gen.get("q_mvar", 0.0)),
                        label_visibility="collapsed",
                        disabled=disabled["q_mvar"],
                        key=f"{id}_gen_q",
                    )
                    left2, right2 = st.columns(2)
                    gen["min_q_mvar"] = left2.number_input(
                        "Min",
                        value=float(gen.get("min_q_mvar", -0.3)),
                        disabled=disabled["min_q_mvar"],
                        key=f"{id}_gen_min_q",
                    )
                    gen["max_q_mvar"] = right2.number_input(
                        "Max",
                        value=float(gen.get("max_q_mvar", 0.3)),
                        disabled=disabled["max_q_mvar"],
                        key=f"{id}_gen_max_q",
                    )

            # --- BUS SELECTION ---
            sac.divider(
                T("titles")[2],
                align="center",
                key=f"{id}_gen_bus_div",
            )
            bus_cols = st.columns(2)
            bus_name = bus_cols[0].selectbox(
                "Bus",
                options=bus_names,
                label_visibility="collapsed",
                key=f"{id}_gen_bus",
            )
            # TODO Move this
            voltage_constraints = {
                "LV": (0.0, 1.0),
                "MV": (1.0, 35.0),
                "HV": (36.0, 220.0),
                "EHV": (220.0, 800.0),
            }
            level_names = {
                key: T("bus_params.level")[i] for i, key in enumerate(["b", "n", "m"])
            }

            if bus_name:
                gen["bus"] = self.grid.get_element("bus", name=bus_name, column="index")
                bus_volt = self.grid.get_element("bus", name=bus_name, column="vn_kv")
                bus_level = level_names[
                    self.grid.get_element("bus", name=bus_name, column="type")
                ]
                voltage = next(
                    (
                        k
                        for k, (a, b) in voltage_constraints.items()
                        if a <= bus_volt <= b
                    ),
                    None,
                )
                bus_on = (
                    "ON"
                    if self.grid.get_element("bus", name=bus_name, column="in_service")
                    else "OFF"
                )
            else:
                voltage, bus_level, bus_on = "NaN", "NaN", "NaN"

            #! I don't remember why this was here
            # // segmenteds: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
            # // for v_label in ["LV", "MV", "HV", "EHV"]:
            # //     for lvl_label in [level_names[i] for i in level_names]:
            # //         for state in ["ON", "OFF"]:
            # //             key = (v_label, lvl_label, state)
            # //             segmenteds[key] = {
            # //                 "items": [sac.SegmentedItem(item) for item in key],
            # //                 "color": "green" if state == "ON" else "red",
            # //                 "index": 2,
            # //                 "bg_color": "#043b41",
            # //                 "size": "sm",
            # //                 "key": f"{id}_gen_bus_prop_{v_label}_{lvl_label}_{state}",
            # //                 "align": "end",
            # //                 "readonly": True,
            # //             }

            with bus_cols[1]:
                status_badge(
                    key_prefix=f"{id}_bus_prop",
                    voltage=voltage,
                    level=bus_level,
                    onoff=bus_on,
                )

        return n_new_gen, gen

    # -------------> Adders <--------
    def _add_sgen(self) -> bool:
        """SGen adder UI. The output is a bool used to check if something has been added

        Returns:
            bool: `True` if add button is pressed
        """
        labels_root = "tabs.gens.item.sgen"
        new_sgens = self._build_sgens()
        if st.button(self.T(f"{labels_root}.buttons")[2]):
            for n_to_create, sgen, spec in new_sgens:
                results = self.__batch_add_with_auto_name(
                    count=int(n_to_create),
                    obj=sgen,
                    create_fn=lambda params: st.session_state[
                        "plant_grid"
                    ].add_active_element(type="sgen", params=params),
                )
                if spec is not None:
                    for idx in results:
                        st.session_state["arrays_to_add"][
                            int(idx)
                        ] = spec  # store PV meta
            return True
        return False

    def _add_gen(self) -> bool:
        """Gen adder UI. The output is a bool used to check if something has been added

        Returns:
            bool: `True` if add button is pressed
        """
        labels_root = "tabs.gens.item.gen"
        new_gens = self._build_gens()
        if st.button(self.T(f"{labels_root}.buttons")[2]):
            for n_to_create, gen in new_gens:
                self.__batch_add_with_auto_name(
                    count=int(n_to_create),
                    obj=gen,
                    create_fn=lambda params: st.session_state[
                        "plant_grid"
                    ].add_active_element(type="gen", params=params),
                )
            return True
        return False

    def _add_storage(self) -> bool:
        # TODO: Implement storage UI and creation
        sac.result("Storage creation coming soon.", status="warning")
        return False

    # ------------- Builders --------
    def _build_sgens(
        self, borders: bool = True
    ) -> List[Tuple[int, SGenParams, Union[PVParams, None]]]:
        labels_root = "tabs.gens.item.sgen.buttons"
        _, items = self.__build_items(
            state_key="gm_new_sgen",
            n_cols=3,
            render_param_fn=lambda i: self.paramsUI_sgen(id=i),
            add_label=self.T(labels_root)[0],
            remove_label=self.T(labels_root)[1],
            borders=borders,
        )
        return items  # type: ignore[return-value]

    def _build_gens(self, borders: bool = True) -> List[Tuple[int, GenParams]]:
        labels_root = "tabs.gens.item.gen.buttons"
        _, items = self.__build_items(
            state_key="gm_new_gen",
            n_cols=3,
            render_param_fn=lambda i: self.paramsUI_gen(id=i),
            add_label=self.T(labels_root)[0],
            remove_label=self.T(labels_root)[1],
            borders=borders,
        )
        return items  # type: ignore[return-value]

    # =========================================================
    #           PASSIVE / SENSORS TABS PLACEHOLDERS
    # =========================================================
    def passive_manager(self) -> bool:
        sac.result("Passives elements coming soon", status="warning")
        return False

    def sensors_manager(self) -> bool:
        sac.result("Sensors elements coming soon", status="warning")
        return False

    # ========== UTILITIES METHOS ============

    # ----------> Builders <----------
    def __build_items(
        self,
        state_key: str,
        n_cols: int,
        render_param_fn,
        add_label: str,
        remove_label: str,
        borders: bool = True,
    ) -> tuple[bool, list]:
        """
        Generic builder that renders N element creators in a grid.

        Args:
            state_key (str): session_state key used to store the number of items ("n").
            n_cols (int): number of columns in the grid layout.
            render_param_fn (Callable[[int], Any]): function that renders a single editor and returns its data.
                If it returns a tuple where the first element is a bool, it is treated as a validity flag
                and aggregated across items.
            add_label (str): label for the "+" button (usually from i18n via self.T).
            remove_label (str): label for the "−" button (usually from i18n via self.T).
            borders (bool): whether to show a bordered container.

        Returns:
            tuple[bool, list]:
                - all_valid (bool): True if all editors returned a truthy validity flag (when present).
                - items (list): list of return values from each editor.
        -----
        Note:

            This function dynamically renders a grid of editors based on the number stored in
            `session_state[state_key]`. It aggregates validation flags if provided by each editor.
        """

        all_valid = True
        items: list = []

        with st.container(border=borders):
            cols = st.columns(n_cols)
            if state_key not in st.session_state:
                st.session_state[state_key] = {"n": 1}
            n = int(st.session_state[state_key]["n"])  # number of editors
            for i in range(n):
                with cols[i % n_cols]:
                    out = render_param_fn(i)
                    items.append(out)
                    # If first element is a boolean, treat as validity flag
                    if isinstance(out, tuple) and out and isinstance(out[0], bool):
                        all_valid = all_valid and bool(out[0])

            # controls (place them in first column for consistency)
            with cols[0]:
                add_col, rem_col = st.columns([3, 2])
                if add_col.button(add_label):
                    st.session_state[state_key]["n"] = n + 1
                    st.rerun()
                if rem_col.button(remove_label) and n > 1:
                    st.session_state[state_key]["n"] = n - 1
                    st.rerun()

        return all_valid, items

    def __batch_add_with_auto_name(
        self, count: int, obj: dict, create_fn, name_key: str = "name"
    ) -> list[Any]:
        """Repeat creation `count` times, auto-prefixing names on duplicates to avoid elements with same params and names
        Returns a list of results produced by `create_fn`.
        """
        results = []
        change_name = count > 1 and name_key in obj
        for i in range(count):
            if change_name:
                obj[name_key] = f"{i}_" + str(obj[name_key])
            results.append(create_fn(obj))
        return results

    # ----------> Managers <----------

    @st.dialog("Edit grid element", width="large")
    def _change_element(
        self,
        params: Union[BusParams, LineParams],
        *,
        # opzionali: per aggiornare nel grid model se ti servono gli ID
        bus_id: Optional[int] = None,
        line_id: Optional[int] = None,
        connected_elements=None,
        # in caso di dubbio sulle chiavi puoi forzare:
        type: Optional[Literal["bus", "line"]] = None,
    ) -> bool:
        """
        Dialog used to manage grid elements changes.
        Decide the flux on the base of `type` parameter passed.
        Returns:
            bool: `True` if save button has been pressed, `False` otherwise

        ---
        TODO: This will be moved in a separated class that will handle the different dialogs
        """
        updated = False

        # --- Dispatch: auto o forzato ---
        if type == "line" or (type is None):
            # === LINE FLOW (ex-change_connection) ===
            link_available, new_line = self.paramsUI_line(line=params, horizontal=False)

            if st.button("Save changes", key="save_line"):
                try:
                    # Se nel tuo modello serve l'ID: self.grid.update_line(line_id, new_line)
                    # Altrimenti:
                    raise NotImplementedError
                    # self.grid.update_line(new_line)  # <-- adatta al tuo metodo reale
                except Exception as e:
                    self.logger.error(f"[GridManagerPage] Error updating line: {e}")
                    raise Exception(
                        f"Error updating line{' ' + str(line_id) if line_id is not None else ''}: {e}"
                    )
                st.session_state["grid_modified"] = True
                st.toast(
                    f"Line{f' {line_id}' if line_id is not None else ''} updated successfully.",
                    icon="✅",
                )
                updated = True
                st.rerun(scope="fragment")

        else:
            # === BUS FLOW (ex-change_bus) ===
            # bus_id is required for the update
            _, new_bus = self.paramsUI_bus(
                id=f"manager_{bus_id if bus_id is not None else 'unknown'}",
                quantity=False,
                bus=params,
                borders=False,
            )

            elements_rows = []
            for el in connected_elements:
                etype, eid, name_hint = normalize_element_spec(el)
                elements_rows.append(
                    {"type": etype, "element ID": eid, "name": name_hint}
                )

            # If there are connected elements i'll show them in a st.dataframe
            if elements_rows and any("element ID" in r for r in elements_rows):
                df_elements = pd.DataFrame(elements_rows).set_index("element ID")
                sac.divider(
                    "Connected elements", icon=sac.BsIcon("diagram-3"), align="center"
                )
                st.dataframe(df_elements)
            else:
                sac.alert(
                    label="No elements connected",
                    variant="quote-light",
                    icon=sac.BsIcon(name="ban", size=15, color="red"),
                    closable=True,
                    color="orange",
                )

            if st.button("Save changes", key="save_bus"):
                try:
                    if bus_id is None:
                        raise ValueError("Missing 'bus_id' for bus update.")
                    self.grid.update_bus(bus_id, new_bus)
                except Exception as e:
                    self.logger.error(f"[GridManagerPage] Error updating bus: {e}")
                    raise Exception(
                        f"Error updating bus {bus_id if bus_id is not None else ''}: {e}"
                    )
                st.session_state["grid_modified"] = True
                st.toast(f"Bus {bus_id} updated successfully.", icon="✅")
                updated = True
                st.rerun(scope="fragment")

        return updated


# // -----------------------------------------------------------------------------------------------------------------------


# TODO BEGIN ---------------------------------------------------------------------
# --------------------------------------------------------------------------------------
# Generic, reusable dialog to edit/create a network element (e.g., bus, line, generator)
# --------------------------------------------------------------------------------------
# Design goals
# - Decouple UI rendering from business logic: pass callbacks for save/delete.
# - Strongly-typed field specs with sensible defaults.
# - Minimal state handling via st.session_state to open/close the dialog.
# - Works for create and edit flows (initial_values optional).
# - Simple validation hook.
# --------------------------------------------------------------------------------------


ValidateFn = Callable[[dict[str, Any]], tuple[bool, Optional[str]]]
SaveFn = Callable[[dict[str, Any]], None]
DeleteFn = Callable[[dict[str, Any]], None]


class DialogManager:
    """Reusable modal dialog to change a network element.
    ---
    Example:
        mgr = DialogManager()
        mgr.open("edit_line")  # somewhere in a button callback
        mgr.change_element_dialog(
            title="Edit Line",
            schema=[...],
            initial_values=line_dict,
            on_save=save_fn,
            on_delete=delete_fn,
            width="large",
            state_key="edit_line",
        )
    """

    def open(self, state_key: str):
        """Open the dialog by setting the state flag."""
        st.session_state[state_key] = True

    def close(self, state_key: str):
        st.session_state[state_key] = False

    def change_element_dialog(
        self,
        *,
        title: str,
        corefn: Callable,
        on_save: SaveFn = None,
        on_delete: Optional[DeleteFn] = None,
        validate: Optional[ValidateFn] = None,
        width: Literal["small", "large"] = "small",
        state_key: str = "change_element_dialog",
        save_label: str = "Save",
        delete_label: str = "Delete",
        cancel_label: str = "Cancel",
    ) -> None:
        """Render the dialog when state flag is True.

        If the dialog is closed (state flag False), nothing is rendered.
        """
        if not st.session_state.get(state_key):
            return
        logger = get_logger("pvapp")

        # Define the modal dialog with Streamlit's decorator.
        @st.dialog(title, width=width)
        def _dialog():
            # We use a form so Save triggers a single rerun.
            try:
                new_element = corefn
            except Exception as e:
                logger.error(f"[DialogManager] Something wrong with grid dialog : {e}")
                st.toast(f"Something wrong with grid dialog : {e}")

            # Inline validation (optional)
            error_box = st.empty()
            # Action buttons
            st.divider()
            cols = st.columns([1, 1, 1]) if on_delete else st.columns([1, 1])
            if st.button(save_label):
                errors = None
                if validate is not None:
                    errors = validate(new_element)
                if not errors:
                    ...

        # Render the dialog now
        _dialog()


# TODO END ---------------------------------------------------------------------
