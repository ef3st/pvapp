from ...page import Page
import streamlit as st
import streamlit_antd_components as sac
from pathlib import Path
import pandas as pd
import json
from pandapower_network.pvnetwork import (
    PlantPowerGrid,
    BusParams,
    LineParams,
    GenParams,
    SGenParams,
)
from typing import Optional, Tuple, List, Union, TypedDict
from bidict import bidict


## SGEN Types Definitions
class PVParams(TypedDict):
    module_per_string: int
    strings_per_inverter: int


def sgen_type_detection(obj: Union[PVParams, None]) -> int:
    """Detect the type of SGen based on its name."""
    if obj is None:
        return 1  # Generic SGen
    if (
        isinstance(obj, dict)
        and ("module_per_string" in obj)
        and ("strings_per_inverter" in obj)
    ):
        return 0  # PV SGen
    raise ValueError("Invalid SGen type or parameters provided.")


##################################
class GridManager(Page):
    def __init__(self, subfolder) -> None:
        super().__init__("grid_manager")
        self.grid_file: Path = subfolder / "grid.json"
        if self.grid_file.exists():
            st.session_state["plant_grid"] = PlantPowerGrid(self.grid_file)
        else:
            st.session_state["plant_grid"] = PlantPowerGrid()
        if "arrays_to_add" not in st.session_state:
            st.session_state["arrays_to_add"] = {}

    # ========= RENDERS =======
    def render_setup(self) -> bool:
        if self.grid.net.bus.empty:
            from streamlit_elements import mui, elements

            with elements("grid_error"):
                mui.Alert(
                    f"NO GRID: {self.T("messages.no_grid")}",
                    severity="warning",
                    variant="outlined",
                )

        titles = self.T("tabs")
        tags = {
            "links": self.grid.get_n_nodes_links(),
            "gens": self.grid.get_n_active_elements(),
            "passive": self.grid.get_n_passive_elements(),
            "sensors": self.grid.get_sensors_controllers(),
        }
        tab = sac.tabs(
            [
                sac.TabsItem(label=titles[tab]["title"], tag=f"{tags[tab]}")
                for tab in titles
            ],
            align="center",
            use_container_width=True,
            return_index=True,
        )
        changed = False
        if tab == 0:
            changed |= self.bus_links_manager()
        elif tab == 1:
            changed |= self.gens_manager()
        elif tab == 2:
            changed |= self.passive_manager()
        elif tab == 3:
            changed |= self.sensors_manager()
        # if changed:
        #     st.rerun()
        return changed

    def render_analysis(self): ...

    # ========= SUMUPS =======
    def get_scheme(self): ...
    def get_description(self):
        grid_description = self.grid.net
        sac.divider("Grid Resume", align="center")
        st.text_area(
            "text_area",
            value=grid_description,
            label_visibility="collapsed",
            disabled=True,
            height=153,
        )

    # ========= UTILITIES METHODS =======
    def save(self):
        self.grid.save(self.grid_file)

        if self.pv_arrays:
            arrays = {}
            path: Path = Path(self.grid_file.parent, "arrays.json")
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    arrays = json.load(f)
            arrays.update(self.pv_arrays)
            with open(
                Path(self.grid_file.parent, "arrays.json"), "w", encoding="utf-8"
            ) as f:
                json.dump(arrays, f, indent=4, ensure_ascii=False)
            st.session_state["arrays_to_add"] = {}

    @property
    def grid(self) -> PlantPowerGrid:
        return (
            st.session_state["plant_grid"]
            if "plant_grid" in st.session_state
            else PlantPowerGrid()
        )

    @property
    def pv_arrays(self) -> dict[int, PVParams]:
        """Get the PV arrays from the grid."""
        return st.session_state.get("arrays_to_add", {})

    # --------> SETUP <------

    # ----> Buses and Links Manager <----
    # ---- Main Manager container ----
    def bus_links_manager(self) -> bool:
        labels_root = "tabs.links"
        with st.expander(self.T(f"{labels_root}.new_item"), icon="➕"):
            items = self.T(f"{labels_root}.item")
            item = sac.chip(
                items=[sac.ChipItem(items[i]["name"]) for i in items],
                label=self.T(f"{labels_root}.select_item"),
                index=[0, 2],
                radius="md",
                variant="light",
                return_index=True,
            )
            changed = False
            if item == 0:
                changed |= self.add_bus()
            elif item == 1:
                changed |= self.add_line()
            elif item == 2:
                changed |= self.add_tranformer()
        return changed

    # ---- Add containers ----
    def add_bus(self):
        labels_root = "tabs.links.item.bus"
        new_buses = self.build_buses()
        if st.button(self.T(f"{labels_root}.buttons")[2]):
            for buses in new_buses:
                change_name = True if len(buses) > 1 else False
                bus = buses[1]
                for i in range(0, buses[0]):
                    if change_name:
                        # st.info(f"{i}_{sgens}")
                        bus["name"] = f"{i}_{bus["name"]}"
                    st.session_state["plant_grid"].create_bus(bus)
            return True
        return False

    def add_line(self):
        labels_root = "tabs.links.item.link"
        if len(self.grid.net.bus) == 0:
            st.error(self.T(f"{labels_root}.no_bus_error"))
        else:
            aviable_link, new_links = self.build_line()
            if st.button(self.T(f"{labels_root}.buttons")[2]):
                if aviable_link:
                    for line in new_links:
                        st.session_state["plant_grid"].link_buses(line)
                    return True
                else:
                    st.error("Line Creation Failed")
        return False

    def add_tranformer(self): ...

    # ---- Build Element containers ----
    def build_buses(self, borders: bool = True) -> List[Tuple[int, BusParams]]:
        labels_root = "tabs.links.item.bus.buttons"
        bus_to_add = []
        with st.container(border=borders):
            cols = st.columns(3)
            if "new_bus" not in st.session_state:
                st.session_state["new_bus"] = {"n": 1, "buses": []}
            buses = st.session_state["new_bus"]
            col = 0
            for i in range(buses["n"]):
                if i % 3 == 0:
                    col = 0
                with cols[col]:
                    bus_to_add.append((self.bus_params(id=i)))
                col += 1
            with cols[0]:
                a, b, _ = st.columns([3, 2, 1])
                if a.button(self.T(labels_root)[0]):
                    st.session_state["new_bus"]["n"] += 1
                    st.rerun()
                if b.button(self.T(labels_root)[1]) and (
                    st.session_state["new_bus"]["n"] > 1
                ):
                    st.session_state["new_bus"]["n"] -= 1
                    st.rerun()

        return bus_to_add

    def build_line(self, borders: bool = True) -> Tuple[bool, List[LineParams]]:
        labels_root = "tabs.links.item.link.buttons"
        line_to_add = []
        with st.container(border=borders):
            if "new_line" not in st.session_state:
                st.session_state["new_line"] = {"n": 1, "lines": []}
            lines = st.session_state["new_line"]
            aviable_link = True
            for i in range(lines["n"]):
                line = self.line_params(id=i)
                if line[0]:
                    line_to_add.append(line[1])
                else:
                    aviable_link = False

            a, b, _ = st.columns([1, 1, 8])
            if a.button(self.T(labels_root)[0]):
                st.session_state["new_line"]["n"] += 1
                st.rerun()
            if b.button(self.T(labels_root)[1]) and (
                st.session_state["new_line"]["n"] > 1
            ):
                st.session_state["new_line"]["n"] -= 1
                st.rerun()

        return aviable_link, line_to_add

    # ---- Element Params Manager containers ----
    def bus_params(
        self,
        borders: bool = True,
        id: Union[int, str] = 1,
        quantity=True,
        bus: Optional[BusParams] = None,
    ) -> Tuple[int, BusParams]:
        labels_root = "tabs.links.item.bus"
        n_new_bus = None
        if not bus:
            bus: BusParams = BusParams(
                name="New_Bus", vn_kv=0.230, type="b", in_service="True"
            )
        with st.container(border=borders):
            titles = self.T(f"{labels_root}.titles")
            sectors = st.columns([1, 2])
            with sectors[0]:
                sac.divider(label=titles[0], align="center", key=f"{id}_bus_prop_div")
                bus["name"] = st.text_input(
                    "Name",
                    label_visibility="collapsed",
                    value=bus["name"],
                    key=f"{id}_bus_name",
                )
                type_idx = bidict({"b": 0, "n": 1, "m": 2})
                bus["type"] = type_idx.inv[
                    sac.segmented(
                        items=[
                            sac.SegmentedItem(label=name)
                            for name in self.T(f"{labels_root}.bus_level")
                        ],
                        direction="vertical",
                        color="grey",
                        index=type_idx[bus["type"]],
                        return_index=True,
                        align="center",
                        key=f"{id}_bus_type",
                    )
                ]
                bus["in_service"] = sac.switch(
                    self.T(f"{labels_root}.in_service"),
                    value=bus["in_service"],
                    position="left",
                    align="center",
                    key=f"{id}_bus_on",
                )
                sac.divider("Quantità", key=f"{id}_bus_quantity_div")
                if quantity:
                    n_new_bus = st.number_input(
                        "Quantità",
                        label_visibility="collapsed",
                        step=1,
                        min_value=1,
                        value=1,
                        key=f"{id}_bus_quantity",
                    )

            with sectors[1]:
                sac.divider(label=titles[1], align="center", key=f"{id}_bus_volt_div")
                left, right = st.columns(2)
                with left:
                    st.markdown("")
                    st.markdown("")
                    voltage = sac.segmented(
                        items=[
                            sac.SegmentedItem(label=name)
                            for name in self.T(f"{labels_root}.voltage")
                        ],
                        direction="vertical",
                        color="grey",
                        align="center",
                        return_index=True,
                        key=f"{id}_bus_voltage_str",
                    )
                    voltage_type = bidict({"LV": 0, "MV": 1, "HV": 2, "EHV": 3})
                    voltages = {"LV": 0.250, "MV": 15, "HV": 150, "EHV": 380}
                    labels = self.T(f"{labels_root}.constraints")
                    disabled = not st.checkbox(labels[0], key=f"{id}_bus_set_limits")

                with right:
                    voltage_constraints = {
                        "LV": (0, 1),
                        "MV": (1, 35),
                        "HV": (36, 220),
                        "EHV": (220, 800),
                    }
                    bus["vn_kv"] = st.number_input(
                        labels[1],
                        disabled=True,
                        value=voltages[voltage_type.inv[voltage]],
                        key=f"{id}_bus_volt_int",
                    )
                    contraints = voltage_constraints[voltage_type.inv[voltage]]
                    min = st.number_input(
                        labels[2],
                        value=contraints[0],
                        disabled=disabled,
                        key=f"{id}_bus_min_volt",
                    )
                    max = st.number_input(
                        labels[3],
                        value=contraints[1],
                        disabled=disabled,
                        key=f"{id}_bus_max_volt",
                    )
                    if not disabled:
                        bus["min_vm_pu"] = min
                        bus["max_vm_pu"] = max

        return n_new_bus, bus

    def line_params(
        self,
        borders: bool = True,
        id: Union[int, str] = 1,
        line: Optional[LineParams] = None,
    ) -> Tuple[bool, LineParams]:
        labels_root = "tabs.links.item.link"
        n_new_line = None
        line_types = self.grid.get_aviable_lines()
        if not line:
            line: LineParams = LineParams(
                from_bus=0,
                to_bus=0,
                length_km=0.1,
                name="New_(NAVY 4x50 SE)_0.1km",
                std_type=line_types[0],
            )

        def select_bus(align="start", name=None) -> int:
            """Bus Selection"""
            # columns
            a = None
            b = None
            c = None
            d = None
            if align == "start":
                a, b = st.columns([1, 10])
                c, d = st.columns(2)
            if align == "end":
                b, a = st.columns([10, 1])
                d, c = st.columns(2)
            # a.button("Reset", key=f"{id}_line_{align}_reset", disabled=True)
            with c:
                sac.divider(
                    self.T(f"{labels_root}.bus_identity")[0],
                    align=align,
                    key=f"{id}_line_{align}_bus_name_div",
                )
                name = st.selectbox(
                    label="Bus name",
                    label_visibility="collapsed",
                    options=list(self.grid.net.get("bus")["name"]),
                    key=f"{id}_line_{align}_bus_name",
                )
            with d:
                sac.divider(
                    self.T(f"{labels_root}.bus_identity")[1],
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
            with b:
                map_level = {"b": 0, "n": 1, "m": 2}
                level_index = self.grid.get_element(
                    element="bus", index=index, column="type"
                )
                if level_index:
                    level_index = map_level[level_index]
                sac.segmented(
                    items=[
                        sac.SegmentedItem(name)
                        for name in self.T(f"{labels_root}.bus_level")
                    ],
                    align="center",
                    color="gren",
                    size="sm",
                    key=f"{id}_line_{align}_bus_level",
                    disabled=True,
                    index=level_index,
                )
            return index

        with st.container(border=borders):
            first, link, second = st.columns([1, 2, 1])

            with first:
                sac.divider(
                    self.T(f"{labels_root}.buses")[0],
                    align="center",
                    variant="dashed",
                    key=f"{id}_line_startbus_div",
                )
                start_bus = select_bus(name="1a")
            with second:
                sac.divider(
                    self.T(f"{labels_root}.buses")[1],
                    align="center",
                    variant="dashed",
                    key=f"{id}_line_endbus_div",
                )
                end_bus = select_bus("end", "1b")
            with link:
                label_line_params = self.T(f"{labels_root}.line_params")
                a, b, c = st.columns([2, 1, 2])
                type = a.selectbox(
                    label_line_params[0],
                    options=self.grid.get_aviable_lines(),
                    key=f"{id}_line_type",
                )
                length = b.number_input(
                    label=f"{label_line_params[1]} (km)",
                    value=0.1,
                    key=f"{id}_line_length",
                )
                name = c.text_input(
                    label_line_params[2],
                    value=f"New_({type})_{length}km",
                    key=f"{id}_line_name",
                )
                error_map = self.T(f"{labels_root}.errors")
                color = "green"
                buses = self.grid.net.bus
                link_aviable = True
                error = self.grid.aviable_link(
                    buses.iloc[start_bus], buses.iloc[end_bus]
                )
                if error:
                    color = "red"
                    link_aviable = False
                sac.divider(
                    error_map[error],
                    align="center",
                    size=5,
                    color=color,
                    variant="dotted",
                    key=f"{id}_line_status_div",
                )
                with st.expander(f"ℹ️ {self.T(f"{labels_root}.infos")[0]}"):
                    line, start, end = st.tabs(tabs=self.T(f"{labels_root}.infos")[1:])
                    with start:
                        st.text(f"{self.grid.net.bus.iloc[start_bus]}")
                    with end:
                        st.text(f"{self.grid.net.bus.iloc[end_bus]}")
                    with line:
                        st.text(f"{self.grid.get_line_infos(type)}")
            new_link = LineParams(
                from_bus=start_bus,
                to_bus=end_bus,
                length_km=length,
                name=name,
                std_type=type,
            )

        return link_aviable, new_link

    # ----> Generators Manager <----
    # ---- Main container ----
    def gens_manager(self):
        labels_root = "tabs.gens"
        with st.expander(self.T(f"{labels_root}.new_item"), icon="➕"):
            items = self.T(f"{labels_root}.item")
            item = sac.chip(
                items=[sac.ChipItem(items[i]["name"]) for i in items],
                label=self.T(f"{labels_root}.select_item"),
                index=[0, 2],
                radius="md",
                variant="light",
                return_index=True,
            )
            changed = False
            if item == 0:
                changed |= self.add_sgen()
            elif item == 1:
                changed |= self.add_gen()
            elif item == 2:
                changed |= self.add_storage()
        return changed

    # ---- Add containers ----
    def add_sgen(self):  #! TO CHECK WHEN I'LL WILL WAKE UP
        labels_root = "tabs.gens.item.sgen"
        new_sgens = self.build_sgens()
        if st.button(self.T(f"{labels_root}.buttons")[2]):
            for sgens in new_sgens:
                change_name = True if len(sgens) > 1 else False
                sgen = sgens[1]
                for i in range(0, sgens[0]):
                    if change_name:
                        # st.info(f"{i}_{sgens}")
                        sgen["name"] = f"{i}_{sgen["name"]}"
                    idx = st.session_state["plant_grid"].add_active_element(
                        type="sgen", params=sgen
                    )
                    if sgens[2] is not None:
                        st.session_state["arrays_to_add"][int(idx)] = sgens[2]
            return True
        return False

    def add_gen(self):
        labels_root = "tabs.gens.item.gen"
        new_gens = self.build_gens()
        if st.button(self.T(f"{labels_root}.buttons")[2]):
            for gens in new_gens:
                change_name = True if len(gens) > 1 else False
                gen = gens[1]
                for i in range(0, gens[0]):
                    if change_name:
                        gen["name"] = f"{i}_{gen["name"]}"
                    st.session_state["plant_grid"].add_active_element(
                        type="gen", params=gen
                    )
            return True
        return False

    # ---- Build Element containers ----
    def build_sgens(self, borders: bool = True) -> List[Tuple[int, SGenParams]]:
        labels_root = "tabs.gens.item.sgen.buttons"
        sgens_to_add = []
        with st.container(border=borders):
            cols = st.columns(3)
            if "new_sgen" not in st.session_state:
                st.session_state["new_sgen"] = {"n": 1, "sgens": []}
            sgens = st.session_state["new_sgen"]
            col = 0
            for i in range(sgens["n"]):
                if i % 3 == 0:
                    col = 0
                with cols[col]:
                    sgens_to_add.append((self.sgen_param(id=i)))
                col += 1
            with cols[0]:
                a, b = st.columns([3, 2])
                if a.button(self.T(labels_root)[0]):
                    st.session_state["new_sgen"]["n"] += 1
                    st.rerun()
                if b.button(self.T(labels_root)[1]) and (
                    st.session_state["new_sgen"]["n"] > 1
                ):
                    st.session_state["new_sgen"]["n"] -= 1
                    st.rerun()

        return sgens_to_add

    def build_gens(self, borders: bool = True) -> List[Tuple[int, GenParams]]:
        labels_root = "tabs.gens.item.gen.buttons"
        gens_to_add = []
        with st.container(border=borders):
            cols = st.columns(3)
            if "new_gen" not in st.session_state:
                st.session_state["new_gen"] = {"n": 1, "gens": []}
            gens = st.session_state["new_gen"]
            col = 0
            for i in range(gens["n"]):
                if i % 3 == 0:
                    col = 0
                with cols[col]:
                    gens_to_add.append((self.gen_param(id=i)))
                col += 1
            with cols[0]:
                a, b = st.columns([3, 2])
                if a.button(self.T(labels_root)[0]):
                    st.session_state["new_gen"]["n"] += 1
                    st.rerun()
                if b.button(self.T(labels_root)[1]) and (
                    st.session_state["new_gen"]["n"] > 1
                ):
                    st.session_state["new_gen"]["n"] -= 1
                    st.rerun()

        return gens_to_add

    # ---- Element Params Manager containers ----
    def sgen_param(
        self,
        borders: bool = True,
        id: int = 1,
        sgen: Optional[SGenParams] = None,
        specficProps: Union[PVParams, None] = None,
        quantity=True,
    ) -> Tuple[int, SGenParams, Union[PVParams, None]]:
        labels_root = "tabs.gens.item.sgen"
        aviable_buses_name = list(self.grid.net.get("bus")["name"])
        # Default SGen Params
        n_new_sgen = None
        defaultSpecProp = [PVParams(module_per_string=1, strings_per_inverter=1), None]
        if sgen == None:  # Default Params
            bus = aviable_buses_name[0] if aviable_buses_name else None
            sgen: SGenParams = SGenParams(
                bus=bus, p_mw=0.4, q_mvar=0, name="New_PV", scaling=1, in_service=True
            )
            assert specficProps is None, "specficProps should be None when sgen is None"
            specficProps = defaultSpecProp[0]  # PV specific properties
        inputs = {
            "p_mv": [False, sgen["p_mw"]],
            "q_mvar": [False, sgen["q_mvar"]],
            "scaling": [False, sgen["scaling"]],
        }
        # Set Sgen
        if sgen_type_detection(specficProps) == 0:  # PV
            sgen_type = 0
            inputs["q_mvar"][0] = True

        with st.container(border=borders):
            buttons_labels = self.T(f"{labels_root}.labels")
            a, b = st.columns(2)
            # SGEN GENERAL PROPERTIES SETUP
            with a:
                if quantity:
                    sac.divider(
                        buttons_labels[1],
                        variant="dashed",
                        size="sm",
                        align="center",
                        key=f"{id}_sgen_quantity_div",
                    )
                    n_new_sgen = st.number_input(
                        buttons_labels[1],
                        key=f"{id}_sgen_quantity",
                        value=1,
                        min_value=1,
                        step=1,
                        label_visibility="collapsed",
                    )
                sac.divider(
                    self.T(f"{labels_root}.titles")[0],
                    align="center",
                    key=f"{id}_sgen_prop_div",
                )
                sgen_type = sac.segmented(
                    items=[sac.SegmentedItem("PV"), sac.SegmentedItem("Others")],
                    color="grey",
                    size="sm",
                    key=f"{id}_sgen_type",
                    index=sgen_type,
                    return_index=True,
                )
                sgen["name"] = st.text_input(
                    buttons_labels[0], key=f"{id}_sgen_name", value=sgen["name"]
                )
                sgen["in_service"] = sac.switch(
                    buttons_labels[2], value=sgen["in_service"], key=f"{id}_sgen_on"
                )
            # SGEN VOLTAGE SETUP
            with b:
                sac.divider(
                    self.T(f"{labels_root}.titles")[1],
                    align="center",
                    key=f"{id}_sgen_volt_div",
                )
                sgen["p_mw"] = st.number_input(
                    buttons_labels[3],
                    key=f"{id}_sgen_volt_input",
                    value=inputs["p_mv"][1],
                    disabled=inputs["p_mv"][0],
                )
                sgen["scaling"] = st.number_input(
                    buttons_labels[4],
                    key=f"{id}_sgen_scale_input",
                    value=inputs["scaling"][1],
                    disabled=inputs["scaling"][0],
                )
                sgen["q_mvar"] = st.number_input(
                    buttons_labels[5],
                    key=f"{id}_sgen_qmvar_input",
                    value=inputs["q_mvar"][1],
                    disabled=inputs["q_mvar"][0],
                )
            # SPECIFIC SGEN SETUP
            if not sgen_type == sgen_type_detection(specficProps):
                specficProps = defaultSpecProp[
                    sgen_type
                ]  # Set default specific properties
                st.warning(
                    "⚠️ Specific properties have been reset to default for the selected SGen type."
                )
            # -> PV SETUP
            if sgen_type == 0:  # PV
                with st.expander("⚡ PV Setup"):
                    left, right = st.columns(2)
                    specficProps["module_per_string"] = left.number_input(
                        "module_per_string (Series)",
                        step=1,
                        min_value=1,
                        value=specficProps["module_per_string"],
                        key=f"{id}_sgen_module_per_string",
                    )
                    specficProps["strings_per_inverter"] = right.number_input(
                        "module_per_string (Parallel)",
                        step=1,
                        min_value=1,
                        value=specficProps["strings_per_inverter"],
                        key=f"{id}_sgen_strings",
                    )
            # BUS SELECTION
            sac.divider(
                self.T(f"{labels_root}.titles")[2],
                align="center",
                key=f"{id}_sgen_bus_div",
            )
            bus_cols = st.columns(2)
            bus_name = bus_cols[0].selectbox(
                "Bus",
                options=aviable_buses_name,
                label_visibility="collapsed",
                key=f"{id}_sgen_bus",
            )
            voltage_constraints = {
                "LV": (0, 1),
                "MV": (1, 35),
                "HV": (36, 220),
                "EHV": (220, 800),
            }
            level_names = {
                key: self.T(f"{labels_root}.bus_params.level")[i]
                for i, key in enumerate(["b", "n", "m"])
            }
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
                voltage = "NaN"
                bus_level = "NaN"
                bus_on = "NaN"

            segmenteds = {}
            for voltage_label in ["LV", "MV", "HV", "EHV"]:
                for level_label in [level_names[i] for i in level_names]:
                    for i in ["ON", "OFF"]:
                        key = (voltage_label, level_label, i)
                        items = [sac.SegmentedItem(item) for item in key]
                        segmenteds[key] = {
                            "items": items,
                            "color": "green" if i == "ON" else "red",
                            "index": 2,
                            "bg_color": "#043b41",
                            # "disabled": True,
                            "size": "sm",
                            "key": f"{id}_gen_bus_prop_{key}",
                            "align": "end",
                            "readonly": True,
                        }
            with bus_cols[1]:
                sac.segmented(**segmenteds[(voltage, bus_level, bus_on)])

        return n_new_sgen, sgen, specficProps

    def gen_param(
        self,
        borders: bool = True,
        id: int = 1,
        gen: Optional[GenParams] = None,
        quantity=True,
    ) -> Tuple[int, GenParams]:
        labels_root = "tabs.gens.item.gen"
        aviable_buses_name = list(self.grid.net.get("bus")["name"])
        gen_type = 1
        n_new_gen = None
        if gen == None:
            bus = aviable_buses_name[0] if aviable_buses_name else None
            default_gen: dict[GenParams] = {
                "slack": GenParams(
                    slack=True,
                    bus=bus,
                    vm_pu=1,
                    name="New_Gen_SLACK",
                    in_service=True,
                    p_mw=1.5,
                ),
                "non_slack": GenParams(
                    slack=False,
                    controllable=True,
                    name="New_Gen",
                    bus=bus,
                    p_mw=1.5,
                    vm_pu=1.0,
                    q_mvar=0.0,
                    min_q_mvar=-0.3,
                    max_q_mvar=0.3,
                    sn_mvar=2,
                    scaling=1.0,
                    in_service=True,
                ),
            }

        # if "PV" in gen["name"]:
        #     gen_type = 0
        #     inputs["q_mvar"][0] = True

        with st.container(border=borders):
            buttons_labels = self.T(f"{labels_root}.labels")
            a, b = st.columns([3, 4])
            with a:
                if quantity:
                    sac.divider(
                        buttons_labels[1],
                        variant="dashed",
                        size="sm",
                        align="center",
                        key=f"{id}_gen_quantity_div",
                    )
                    n_new_gen = st.number_input(
                        "Quantity",
                        key=f"{id}_gen_quantity",
                        value=1,
                        min_value=1,
                        step=1,
                        label_visibility="collapsed",
                    )
                sac.divider(
                    self.T(f"{labels_root}.titles")[0],
                    align="center",
                    key=f"{id}_gen_prop_div",
                )
                gen = default_gen["slack"]
                slack = sac.switch(
                    buttons_labels[3], value=gen["slack"], key=f"{id}_gen_slack"
                )
                if not slack:
                    gen = default_gen["non_slack"]
                else:
                    gen = default_gen["slack"]

                gen["name"] = st.text_input(
                    buttons_labels[0], key=f"{id}_gen_name", value=gen["name"]
                )
                gen["in_service"] = sac.switch(
                    buttons_labels[2], value=gen["in_service"], key=f"{id}_gen_on"
                )

                if not slack:
                    gen["controllable"] = sac.switch(
                        buttons_labels[4],
                        value=gen["controllable"],
                        key=f"{id}_gen_controllable",
                    )
                else:
                    sac.switch(
                        buttons_labels[4],
                        value=True,
                        key=f"{id}_gen_controllable",
                        disabled=True,
                    )
            with b:
                sac.divider(
                    self.T(f"{labels_root}.titles")[1],
                    align="center",
                    key=f"{id}_gen_volt_div",
                )
                if slack:
                    st.number_input("vm_pu")
                else:
                    disable_buttons_from_controllable = {  # depending on controllable
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
                    disable_buttons = disable_buttons_from_controllable[
                        gen["controllable"]
                    ]
                    left, right = st.columns([2.5, 1])
                    gen["p_mw"] = left.number_input(
                        buttons_labels[5],
                        key=f"{id}_gen_power",
                        value=gen["p_mw"],
                    )
                    gen["scaling"] = right.number_input(
                        buttons_labels[9], key=f"{id}_gen_scale", value=gen["scaling"]
                    )
                    gen["sn_mvar"] = st.number_input(
                        buttons_labels[8], key=f"{id}_gen_sn", value=gen["sn_mvar"]
                    )
                    gen["vm_pu"] = st.number_input(
                        buttons_labels[6],
                        value=gen["vm_pu"],
                        disabled=disable_buttons["vm_pu"],
                        key=f"{id}_gen_vm",
                    )

                    sac.divider(
                        f"{buttons_labels[7]} (MVAR)",
                        align="start",
                        key=f"{id}_gen_q_div",
                    )
                    gen["q_mvar"] = st.number_input(
                        "Reactive power",
                        value=gen["q_mvar"],
                        label_visibility="collapsed",
                        disabled=disable_buttons["q_mvar"],
                        key=f"{id}_gen_q",
                    )
                    left, right = st.columns(2)
                    gen["min_q_mvar"] = left.number_input(
                        "Min",
                        value=gen["min_q_mvar"],
                        disabled=disable_buttons["min_q_mvar"],
                        key=f"{id}_gen_min_q",
                    )
                    gen["max_q_mvar"] = right.number_input(
                        "Max",
                        value=gen["max_q_mvar"],
                        disabled=disable_buttons["max_q_mvar"],
                        key=f"{id}_gen_max_q",
                    )

            sac.divider(
                self.T(f"{labels_root}.titles")[2],
                align="center",
                key=f"{id}_gen_bus_div",
            )
            bus_cols = st.columns(2)
            bus_name = bus_cols[0].selectbox(
                "Bus",
                options=aviable_buses_name,
                label_visibility="collapsed",
                key=f"{id}_gen_bus",
            )
            voltage_constraints = {
                "LV": (0, 1),
                "MV": (1, 35),
                "HV": (36, 220),
                "EHV": (220, 800),
            }
            level_names = {
                key: self.T(f"{labels_root}.bus_params.level")[i]
                for i, key in enumerate(["b", "n", "m"])
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
                voltage = "NaN"
                bus_level = "NaN"
                bus_on = "NaN"

            segmenteds = {}
            for voltage_label in ["LV", "MV", "HV", "EHV"]:
                for level_label in [level_names[i] for i in level_names]:
                    for i in ["ON", "OFF"]:
                        key = (voltage_label, level_label, i)
                        items = [sac.SegmentedItem(item) for item in key]
                        segmenteds[key] = {
                            "items": items,
                            "color": "green" if i == "ON" else "red",
                            "index": 2,
                            "bg_color": "#043b41",
                            # "disabled": True,
                            "size": "sm",
                            "key": f"{id}_gen_bus_prop_{key}",
                            "align": "end",
                            "readonly": True,
                        }
            with bus_cols[1]:
                sac.segmented(**segmenteds[(voltage, bus_level, bus_on)])

        return n_new_gen, gen

    #! TO IMPLEMENT

    def add_storage(self): ...

    def passive_manager(self):
        st.text("passives")

    def sensors_manager(self):
        st.text("sensors")

    # --------> ANALYSIS <------


# from __future__ import annotations

# from pathlib import Path
# from typing import Any, Dict, List, Optional, Tuple, TypedDict, Union

# import pandas as pd
# import json

# import streamlit as st
# import streamlit_antd_components as sac
# from bidict import bidict

# from ...page import Page
# from pandapower_network.pvnetwork import (
#     BusParams,
#     GenParams,
#     LineParams,
#     PlantPowerGrid,
#     SGenParams,
# )

# # --- Constants ---
# SESSION_GRID_KEY = "plant_grid"
# SESSION_ARRAYS_TO_ADD_KEY = "arrays_to_add"
# SESSION_NEW_PREFIX = "new_"

# # --- SGEN Types Definitions ---
# class PVParams(TypedDict):
#     module_per_string: int
#     strings_per_inverter: int


# def sgen_type_detection(obj: Union[PVParams, None]) -> int:
#     """Detect the type of SGen based on its parameters."""
#     if obj is None:
#         return 1  # Generic SGen
#     if isinstance(obj, dict) and "module_per_string" in obj and "strings_per_inverter" in obj:
#         return 0  # PV SGen
#     raise ValueError("Invalid SGen type or parameters provided.")


# # --- UI Helper Functions ---
# def _render_quantity_input(key_suffix: str, default_quantity: int = 1) -> int:
#     """Renders a number input for quantity and returns its value."""
#     label = "Quantità"
#     return st.number_input(
#         label,
#         label_visibility="collapsed",
#         step=1,
#         min_value=1,
#         value=st.session_state.get(f"{SESSION_NEW_PREFIX}{key_suffix}", {}).get("n", default_quantity),
#         key=f"{key_suffix}_quantity_input"
#     )

# def _render_add_remove_buttons(key_suffix: str) -> None:
#     """Renders add/remove buttons for dynamically adding/removing items."""
#     col1, col2 = st.columns([3, 2])
#     current_n = st.session_state.get(f"{SESSION_NEW_PREFIX}{key_suffix}", {}).get("n", 1)

#     if col1.button("➕", key=f"{key_suffix}_add"):
#         st.session_state[f"{SESSION_NEW_PREFIX}{key_suffix}"]["n"] += 1
#         st.rerun()
#     if col2.button("➖", key=f"{key_suffix}_remove") and current_n > 1:
#         st.session_state[f"{SESSION_NEW_PREFIX}{key_suffix}"]["n"] -= 1
#         st.rerun()

# def _render_section_divider(title: str, align: str = "center", **kwargs) -> None:
#     """Renders a styled divider for section titles."""
#     sac.divider(label=title, align=align, **kwargs)

# def _render_bus_selector(grid: PlantPowerGrid, key_suffix: str, default_bus_name: Optional[str] = None) -> str:
#     """Renders a dropdown to select a bus by name."""
#     available_buses = list(grid.net.bus["name"])
#     if not available_buses:
#         st.error("No buses available. Please add a bus first.")
#         return ""

#     selected_bus = st.selectbox(
#         "Bus",
#         options=available_buses,
#         index=available_buses.index(default_bus_name) if default_bus_name and default_bus_name in available_buses else 0,
#         key=f"{key_suffix}_bus_selector"
#     )
#     return selected_bus

# def _render_text_input(label: str, default_value: str, key_suffix: str) -> str:
#     """Renders a text input."""
#     return st.text_input(label, value=default_value, key=f"{key_suffix}_text_input")

# def _render_number_input(label: str, default_value: Optional[float] = None, key_suffix: str = "", min_value: Optional[float] = None, step: Optional[float] = None) -> float:
#     """Renders a number input."""
#     return st.number_input(label, value=default_value, min_value=min_value, step=step, key=f"{key_suffix}_number_input")

# def _render_switch(label: str, default_value: bool, key_suffix: str) -> bool:
#     """Renders a switch."""
#     return sac.switch(label, value=default_value, key=f"{key_suffix}_switch")

# # --- Parameter Form Classes ---
# class BaseParamForm:
#     """Base class for parameter forms to ensure consistency."""
#     def __init__(self, grid: PlantPowerGrid, labels_root: str):
#         self.grid = grid
#         self.labels_root = labels_root

#     def get_labels(self, key: str) -> Any:
#         """Helper to get translated labels."""
#         return self.T(f"{self.labels_root}.{key}")

#     def T(self, key: str) -> str | list:
#         from ....utils.translation.traslator import translate
#         return translate(f"grid_manager.{key}")

# class BusForm(BaseParamForm):
#     """Form for defining Bus parameters."""
#     def __init__(self, grid: PlantPowerGrid):
#         super().__init__(grid, "tabs.links.item.bus")

#     def render(self, key_suffix: str, bus: Optional[BusParams] = None, quantity: bool = True) -> Tuple[int, BusParams]:
#         if bus is None:
#             bus = BusParams(name="New_Bus", vn_kv=0.230, type="b", in_service=True)

#         with st.container(border=True):
#             _render_section_divider(self.get_labels("titles")[0], align="center")
#             name = _render_text_input("Name", bus["name"], f"{key_suffix}_name")
#             bus_type_map = bidict({"b": 0, "n": 1, "m": 2})
#             bus_type_idx = bus_type_map[bus["type"]]
#             bus_type_labels = [sac.SegmentedItem(label=l) for l in self.get_labels("bus_level")]
#             bus_type = bus_type_map.inv[
#                 sac.segmented(
#                     items=bus_type_labels,
#                     direction="vertical",
#                     color="grey",
#                     index=bus_type_idx,
#                     return_index=True,
#                     key=f"{key_suffix}_type",
#                 )
#             ]
#             in_service = _render_switch(self.get_labels("in_service"), bus["in_service"], f"{key_suffix}_in_service")

#             _render_section_divider("Quantità", align="center")
#             n_new = _render_quantity_input(key_suffix) if quantity else 1

#             _render_section_divider(self.get_labels("titles")[1], align="center")
#             vn_kv = _render_number_input("Vn (kV)", bus["vn_kv"], f"{key_suffix}_vn_kv", min_value=0.001)

#             # Voltage constraints (simplified)
#             labels = self.get_labels("constraints")
#             disabled = not st.checkbox(labels[0], key=f"{key_suffix}_set_limits")
#             min_vm_pu = st.number_input(labels[2], value=0.9, disabled=disabled, key=f"{key_suffix}_min_vm_pu")
#             max_vm_pu = st.number_input(labels[3], value=1.1, disabled=disabled, key=f"{key_suffix}_max_vm_pu")

#         params = BusParams(
#             name=name,
#             vn_kv=vn_kv,
#             type=bus_type,
#             in_service=in_service,
#             min_vm_pu=min_vm_pu if not disabled else None,
#             max_vm_pu=max_vm_pu if not disabled else None,
#         )
#         return n_new, params


# class LineForm(BaseParamForm):
#     """Form for defining Line parameters."""
#     def __init__(self, grid: PlantPowerGrid):
#         super().__init__(grid, "tabs.links.item.link")

#     def render(self, key_suffix: str, line: Optional[LineParams] = None) -> Tuple[bool, LineParams]:
#         if line is None:
#             line = LineParams(from_bus=0, to_bus=0, length_km=0.1, name="New_Line", std_type="NAYY 4x50 SE")

#         available_lines = self.grid.get_aviable_lines()
#         if not available_lines:
#              st.error("No line types available.")
#              return False, line

#         with st.container(border=True):
#             _render_section_divider(self.get_labels("titles")[0], align="center")

#             col1, col2 = st.columns(2)
#             with col1:
#                 from_bus_name = _render_bus_selector(self.grid, f"{key_suffix}_from_bus", self.grid.net.bus.iloc[line["from_bus"]]["name"] if not self.grid.net.bus.empty else None)
#                 from_bus_idx = self.grid.get_element("bus", name=from_bus_name, column="index") if from_bus_name else 0

#             with col2:
#                 to_bus_name = _render_bus_selector(self.grid, f"{key_suffix}_to_bus", self.grid.net.bus.iloc[line["to_bus"]]["name"] if not self.grid.net.bus.empty else None)
#                 to_bus_idx = self.grid.get_element("bus", name=to_bus_name, column="index") if to_bus_name else 0

#             length_km = _render_number_input("Length (km)", line["length_km"], f"{key_suffix}_length_km", min_value=0.001)
#             std_type = st.selectbox("Type", options=available_lines, index=available_lines.index(line["std_type"]) if line["std_type"] in available_lines else 0, key=f"{key_suffix}_std_type")
#             name = _render_text_input("Name", line["name"], f"{key_suffix}_name")

#             link_aviable = True
#             if from_bus_name and to_bus_name:
#                  error = self.grid.aviable_link(
#                     self.grid.net.bus.iloc[from_bus_idx], self.grid.net.bus.iloc[to_bus_idx]
#                 )
#                  if error:
#                     st.error(self.get_labels("errors")[error])
#                     link_aviable = False

#         params = LineParams(
#             from_bus=from_bus_idx,
#             to_bus=to_bus_idx,
#             length_km=length_km,
#             name=name,
#             std_type=std_type,
#         )
#         return link_aviable, params


# class SGenForm(BaseParamForm):
#     """Form for defining SGen parameters."""
#     def __init__(self, grid: PlantPowerGrid):
#         super().__init__(grid, "tabs.gens.item.sgen")

#     def render(self, key_suffix: str, sgen: Optional[SGenParams] = None, specific_setup: Optional[PVParams] = None, quantity: bool = True) -> Tuple[int, SGenParams, Optional[PVParams]]:
#         available_buses_name = list(self.grid.net.get("bus")["name"])
#         n_new_sgen = None
#         default_spec_prop = [PVParams(module_per_string=1, strings_per_inverter=1), None]

#         if sgen is None:
#             bus = available_buses_name[0] if available_buses_name else None
#             sgen:SGenParams = SGenParams(
#                 bus=bus, p_mw=0.4, q_mvar=0, name="New_PV", scaling=1, in_service=True
#             )
#             assert specific_setup is None, "specific_setup should be None when sgen is None"
#             specific_setup = default_spec_prop[0]

#         inputs = {
#             "p_mw": [False, sgen["p_mw"]],
#             "q_mvar": [False, sgen["q_mvar"]],
#             "scaling": [False, sgen["scaling"]],
#         }

#         if sgen_type_detection(specific_setup) == 0:
#             sgen_type = 0
#             inputs["q_mvar"][0] = True
#         else:
#             sgen_type = 1

#         if not available_buses_name:
#             st.error("No buses available. Please add a bus first.")
#             return 1, sgen, specific_setup

#         with st.container(border=True):
#             buttons_labels = self.get_labels("labels")
#             a, b = st.columns(2)

#             with a:
#                 if quantity:
#                     sac.divider(
#                         buttons_labels[1],
#                         variant="dashed",
#                         size="sm",
#                         align="center",
#                         key=f"{key_suffix}_sgen_quantity_div",
#                     )
#                     n_new_sgen = st.number_input(
#                         buttons_labels[1],
#                         key=f"{key_suffix}_sgen_quantity",
#                         value=1,
#                         min_value=1,
#                         step=1,
#                         label_visibility="collapsed",
#                     )
#                 sac.divider(
#                     self.get_labels("titles")[0],
#                     align="center",
#                     key=f"{key_suffix}_sgen_prop_div",
#                 )
#                 sgen_type = sac.segmented(
#                     items=[sac.SegmentedItem("PV"), sac.SegmentedItem("Others")],
#                     color="grey",
#                     size="sm",
#                     key=f"{key_suffix}_sgen_type",
#                     index=sgen_type,
#                     return_index=True,
#                 )
#                 sgen["name"] = st.text_input(
#                     buttons_labels[0], key=f"{key_suffix}_sgen_name", value=sgen["name"]
#                 )
#                 sgen["in_service"] = sac.switch(
#                     buttons_labels[2], value=sgen["in_service"], key=f"{key_suffix}_sgen_on"
#                 )

#             with b:
#                 sac.divider(
#                     self.get_labels("titles")[1],
#                     align="center",
#                     key=f"{key_suffix}_sgen_volt_div",
#                 )
#                 sgen["p_mw"] = st.number_input(
#                     buttons_labels[3],
#                     key=f"{key_suffix}_sgen_volt_input",
#                     value=inputs["p_mw"][1],
#                     disabled=inputs["p_mw"][0],
#                 )
#                 sgen["scaling"] = st.number_input(
#                     buttons_labels[4],
#                     key=f"{key_suffix}_sgen_scale_input",
#                     value=inputs["scaling"][1],
#                     disabled=inputs["scaling"][0],
#                 )
#                 sgen["q_mvar"] = st.number_input(
#                     buttons_labels[5],
#                     key=f"{key_suffix}_sgen_qmvar_input",
#                     value=inputs["q_mvar"][1],
#                     disabled=inputs["q_mvar"][0],
#                 )

#             if not sgen_type == sgen_type_detection(specific_setup):
#                 specific_setup = default_spec_prop[sgen_type]
#                 st.warning(
#                     "⚠️ Specific properties have been reset to default for the selected SGen type."
#                 )

#             if sgen_type == 0:
#                 with st.expander("⚡ PV Setup"):
#                     left, right = st.columns(2)
#                     specific_setup["module_per_string"] = left.number_input(
#                         "module_per_string (Series)",
#                         step=1,
#                         min_value=1,
#                         value=specific_setup["module_per_string"],
#                         key=f"{key_suffix}_sgen_module_per_string",
#                     )
#                     specific_setup["strings_per_inverter"] = right.number_input(
#                         "module_per_string (Parallel)",
#                         step=1,
#                         min_value=1,
#                         value=specific_setup["strings_per_inverter"],
#                         key=f"{key_suffix}_sgen_strings",
#                     )

#             sac.divider(
#                 self.get_labels("titles")[2],
#                 align="center",
#                 key=f"{key_suffix}_sgen_bus_div",
#             )
#             bus_cols = st.columns(2)
#             bus_name = bus_cols[0].selectbox(
#                 "Bus",
#                 options=available_buses_name,
#                 label_visibility="collapsed",
#                 key=f"{key_suffix}_sgen_bus",
#             )
#             voltage_constraints = {
#                 "LV": (0, 1),
#                 "MV": (1, 35),
#                 "HV": (36, 220),
#                 "EHV": (220, 800),
#             }
#             level_names = {
#                 key: self.get_labels("bus_params.level")[i]
#                 for i, key in enumerate(["b", "n", "m"])
#             }
#             if bus_name:
#                 sgen["bus"] = self.grid.get_element(
#                     "bus", name=bus_name, column="index"
#                 )
#                 bus_volt = self.grid.get_element("bus", name=bus_name, column="vn_kv")
#                 bus_level = level_names[
#                     self.grid.get_element("bus", name=bus_name, column="type")
#                 ]
#                 voltage = next(
#                     (
#                         k
#                         for k, (a, b) in voltage_constraints.items()
#                         if a <= bus_volt <= b
#                     ),
#                     None,
#                 )
#                 bus_on = (
#                     "ON"
#                     if self.grid.get_element("bus", name=bus_name, column="in_service")
#                     else "OFF"
#                 )
#             else:
#                 voltage = "NaN"
#                 bus_level = "NaN"
#                 bus_on = "NaN"

#             segmenteds = {}
#             for voltage_label in ["LV", "MV", "HV", "EHV"]:
#                 for level_label in [level_names[i] for i in level_names]:
#                     for i in ["ON", "OFF"]:
#                         key = (voltage_label, level_label, i)
#                         items = [sac.SegmentedItem(item) for item in key]
#                         segmenteds[key] = {
#                             "items": items,
#                             "color": "green" if i == "ON" else "red",
#                             "index": 2,
#                             "bg_color": "#043b41",
#                             # "disabled": True,
#                             "size": "sm",
#                             "key": f"{key_suffix}_gen_bus_prop_{key}",
#                             "align": "end",
#                             "readonly": True,
#                         }
#             with bus_cols[1]:
#                 sac.segmented(**segmenteds[(voltage, bus_level, bus_on)])

#         return n_new_sgen, sgen, specific_setup

# class GenForm(BaseParamForm):
#     """Form for defining Gen parameters."""
#     def __init__(self, grid: PlantPowerGrid):
#         super().__init__(grid, "tabs.gens.item.gen")

#     def render(self, key_suffix: str, gen: Optional[GenParams] = None, quantity: bool = True) -> Tuple[int, GenParams]:
#         if gen is None:
#             gen = GenParams(slack=False, bus=0, p_mw=1.5, vm_pu=1.0, name="New_Gen", in_service=True)

#         available_buses = list(self.grid.net.bus["name"])
#         if not available_buses:
#             st.error("No buses available. Please add a bus first.")
#             return 1, gen

#         with st.container(border=True):
#             _render_section_divider(self.get_labels("titles")[0], align="center")
#             name = _render_text_input("Name", gen["name"], f"{key_suffix}_name")
#             bus_name = _render_bus_selector(self.grid, f"{key_suffix}_bus", self.grid.net.bus.iloc[gen["bus"]]["name"] if not self.grid.net.bus.empty else available_buses[0])
#             bus_idx = self.grid.get_element("bus", name=bus_name, column="index") if bus_name else 0

#             p_mw = _render_number_input("P (MW)", gen["p_mw"], f"{key_suffix}_p_mw")
#             vm_pu = _render_number_input("Vm (pu)", gen["vm_pu"], f"{key_suffix}_vm_pu")
#             slack = _render_switch("Slack", gen["slack"], f"{key_suffix}_slack")
#             in_service = _render_switch("In Service", gen["in_service"], f"{key_suffix}_in_service")

#             n_new = _render_quantity_input(key_suffix) if quantity else 1

#         params = GenParams(
#             slack=slack,
#             bus=bus_idx,
#             p_mw=p_mw,
#             vm_pu=vm_pu,
#             name=name,
#             in_service=in_service,
#         )
#         return n_new, params


# # ===================================
# #!     MAIN GRID MANAGER CLASS
# # ===================================
# class GridManager(Page):
#     def __init__(self, subfolder: Path) -> None:
#         super().__init__("grid_manager")
#         self.grid_file: Path = subfolder / "grid.json"
#         self.arrays_file: Path = subfolder / "arrays.json"

#         if SESSION_GRID_KEY not in st.session_state:
#             if self.grid_file.exists():
#                 st.session_state[SESSION_GRID_KEY] = PlantPowerGrid(self.grid_file)
#             else:
#                 st.session_state[SESSION_GRID_KEY] = PlantPowerGrid()

#         if SESSION_ARRAYS_TO_ADD_KEY not in st.session_state:
#             st.session_state[SESSION_ARRAYS_TO_ADD_KEY] = {}

#     # --- Properties ---
#     @property
#     def grid(self) -> PlantPowerGrid:
#         return st.session_state[SESSION_GRID_KEY]

#     @property
#     def pv_arrays(self) -> dict[int, PVParams]:
#         """Get the PV arrays from the grid."""
#         return st.session_state.get(SESSION_ARRAYS_TO_ADD_KEY, {})

#     # --- Render Methods ---
#     def render_setup(self) -> bool:
#         """Renders the grid setup interface."""
#         if self.grid.net.bus.empty:
#             st.warning(self.T("messages.no_grid"))

#         titles = self.T("tabs")
#         tags = {
#             "links": self.grid.get_n_nodes_links(),
#             "gens": self.grid.get_n_active_elements(),
#             "passive": self.grid.get_n_passive_elements(),
#             "sensors": self.grid.get_sensors_controllers(),
#         }

#         tab_labels = [sac.TabsItem(label=titles[tab]["title"], tag=f"{tags[tab]}") for tab in titles]
#         tab = sac.tabs(tab_labels, align="center", use_container_width=True, return_index=True)

#         changed = False
#         if tab == 0:
#             changed |= self._render_bus_links_manager()
#         elif tab == 1:
#             changed |= self._render_gens_manager()
#         elif tab == 2:
#             changed |= self._render_passive_manager()
#         elif tab == 3:
#             changed |= self._render_sensors_manager()
#         return changed

#     def render_analysis(self) -> None:
#         """Renders the grid analysis interface."""
#         st.text("Analysis section - To be implemented.")

#     # --- Summary Methods ---
#     def get_scheme(self) -> None:
#         """Gets the grid scheme."""
#         st.text("Scheme section - To be implemented.")

#     def get_description(self) -> None:
#         """Gets a description of the grid."""
#         grid_description = str(self.grid.net) # Basic description
#         sac.divider("Grid Resume", align="center")
#         st.text_area(
#             "Grid Description",
#             value=grid_description,
#             label_visibility="collapsed",
#             disabled=True,
#             height=300,
#         )

#     # --- Utility Methods ---
#     def save(self) -> None:
#         """Saves the current grid and PV arrays."""
#         self.grid.save(self.grid_file)

#         if self.pv_arrays:
#             arrays = {}
#             if self.arrays_file.exists():
#                 with open(self.arrays_file, "r", encoding="utf-8") as f:
#                     arrays = json.load(f)
#             arrays.update(self.pv_arrays)
#             with open(self.arrays_file, "w", encoding="utf-8") as f:
#                 json.dump(arrays, f, indent=4, ensure_ascii=False)
#             st.session_state[SESSION_ARRAYS_TO_ADD_KEY] = {}

#     # --- Setup Managers (Refactored) ---
#     def _render_bus_links_manager(self) -> bool:
#         """Manages buses and links."""
#         labels_root = "tabs.links"
#         changed = False
#         with st.expander(self.T(f"{labels_root}.new_item"), icon="➕"):
#             items = self.T(f"{labels_root}.item")
#             item_labels = [items[i]["name"] for i in items]
#             selected_item = sac.chip(
#                 items=[sac.ChipItem(label=l) for l in item_labels],
#                 label=self.T(f"{labels_root}.select_item"),
#                 radius="md",
#                 variant="light",
#                 return_index=True,
#             )
#             if selected_item == 0:
#                 changed |= self._add_bus()
#             elif selected_item == 1:
#                 changed |= self._add_line()
#             elif selected_item == 2:
#                 changed |= self._add_transformer()
#         return changed

#     def _add_bus(self) -> bool:
#         """Adds a new bus."""
#         form = BusForm(self.grid)
#         n_new, params = form.render("bus")
#         if st.button(form.get_labels("buttons")[2]):
#             for i in range(n_new):
#                 bus_params = params.copy()
#                 if n_new > 1:
#                     bus_params["name"] = f"{i}_{params['name']}"
#                 self.grid.create_bus(bus_params)
#             return True
#         return False

#     def _add_line(self) -> bool:
#         """Adds a new line."""
#         if self.grid.net.bus.empty:
#             st.error(self.T("tabs.links.item.link.no_bus_error"))
#             return False

#         form = LineForm(self.grid)
#         link_aviable, params = form.render("line")
#         if link_aviable and st.button(form.get_labels("buttons")[2]):
#             self.grid.link_buses(params)
#             return True
#         return False

#     def _add_transformer(self) -> bool:
#         """Adds a new transformer."""
#         st.text("Transformer addition - To be implemented.")
#         return False

#     def _render_gens_manager(self) -> bool:
#         """Manages generators."""
#         labels_root = "tabs.gens"
#         changed = False
#         with st.expander(self.T(f"{labels_root}.new_item"), icon="➕"):
#             items = self.T(f"{labels_root}.item")
#             item_labels = [items[i]["name"] for i in items]
#             selected_item = sac.chip(
#                 items=[sac.ChipItem(label=l) for l in item_labels],
#                 label=self.T(f"{labels_root}.select_item"),
#                 radius="md",
#                 variant="light",
#                 return_index=True,
#             )
#             if selected_item == 0:
#                 changed |= self._add_sgen()
#             elif selected_item == 1:
#                 changed |= self._add_gen()
#             elif selected_item == 2:
#                 changed |= self._add_storage()
#         return changed

#     def _add_sgen(self) -> bool:
#         """Adds a new static generator."""
#         form = SGenForm(self.grid)
#         n_new, params, pv_params = form.render("sgen")
#         if st.button(form.get_labels("buttons")[2]):
#             for i in range(n_new):
#                 sgen_params = params.copy()
#                 if n_new > 1:
#                     sgen_params["name"] = f"{i}_{params['name']}"
#                 idx = self.grid.add_active_element(type="sgen", params=sgen_params)
#                 if pv_params and idx is not None:
#                     st.session_state[SESSION_ARRAYS_TO_ADD_KEY][int(idx)] = pv_params
#             return True
#         return False

#     def _add_gen(self) -> bool:
#         """Adds a new generator."""
#         form = GenForm(self.grid)
#         n_new, params = form.render("gen")
#         if st.button(form.get_labels("buttons")[2]):
#             for i in range(n_new):
#                 gen_params = params.copy()
#                 if n_new > 1:
#                     gen_params["name"] = f"{i}_{params['name']}"
#                 self.grid.add_active_element(type="gen", params=gen_params)
#             return True
#         return False

#     def _add_storage(self) -> bool:
#         """Adds a new storage."""
#         sac.result(description='Storage addition', label="To be implemented", status='warning')
#         return False

#     def _render_passive_manager(self) -> bool:
#         """Manages passive elements."""
#         sac.result(description='Passive elements management', label="To be implemented", status='warning')
#         return False

#     def _render_sensors_manager(self) -> bool:
#         """Manages sensors and controllers."""
#         sac.result(description='Sensors and controllers management', label="To be implemented", status='warning')
#         return False
