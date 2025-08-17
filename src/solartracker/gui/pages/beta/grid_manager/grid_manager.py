#! DEPRECAETED
# This file is deprecated and will be removed in future versions.
# Use the new grid manager implementation instead.


from ....pages.page import Page
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
from typing import Optional, Tuple, List, Union
from bidict import bidict


def load_all_implants(folder: Path = Path("data/")) -> pd.DataFrame:
    data = []
    for subfolder in sorted(folder.iterdir()):
        if subfolder.is_dir():
            site_file = subfolder / "site.json"
            implant_file = subfolder / "implant.json"
            if site_file.exists() and implant_file.exists():
                try:
                    site = json.load(site_file.open())
                    implant = json.load(implant_file.open())
                    data.append(
                        {
                            "site_name": site.get("name", "Unknown"),
                            "implant_name": implant.get("name", "Unnamed"),
                            "subfolder": subfolder,
                        }
                    )
                except Exception as e:
                    st.error(f"Error reading {subfolder.name}: {e}")
    return pd.DataFrame(data)


class GridManager(Page):
    def __init__(self) -> None:
        super().__init__("grid_manager")

    @property
    def grid(self) -> PlantPowerGrid:
        return (
            st.session_state.plant_grid
            if "plant_grid" in st.session_state
            else PlantPowerGrid()
        )

    # ------ RENDER -------

    def render(self):
        st.title("🖥️ " + self.T("title"))
        ll, rr = st.columns([3, 1])
        # Select Plant
        with ll:
            with st.expander(f" 🔎 {self.T("subtitle.search_implant")}", expanded=True):
                subfolder = self.select_plant()
                grid_file = subfolder / "grid.json"
        # Resume data
        if not grid_file.exists():
            if "plant_grid" not in st.session_state:
                st.session_state["plant_grid"] = PlantPowerGrid()
        else:
            if "plant_grid" not in st.session_state:
                st.session_state["plant_grid"] = PlantPowerGrid(grid_file)
        with rr:
            grid_description = self.grid.net
            if self.grid.net.bus.empty:
                sac.result(
                    label="NO GRID",
                    description=self.T("messages.no_grid"),
                    status="empty",
                )
            else:
                # st.markdown(f"{self.grid.net}")
                sac.divider("Grid Resume", align="center")
                st.text_area(
                    "text_area",
                    value=grid_description,
                    label_visibility="collapsed",
                    disabled=True,
                    height=153,
                )

        plot_grid, plot_grid_error = self.grid.show_grid()
        if plot_grid_error:
            for i in plot_grid_error:
                st.warning(i)
        else:
            st.plotly_chart(plot_grid, use_container_width=True)
        # Manage elements
        self.tabs()
        a, b = ll.columns([1, 6])
        if a.button(self.T("buttons.save_grid"), icon="💾"):
            st.session_state["plant_grid"] = self.grid.save(grid_file)
            st.rerun()
        with b.expander("⚡ REFERENCE BUS"):
            st.badge("ciao")

    def select_plant(self):
        implants_df = load_all_implants()
        if implants_df.empty:
            st.warning("No valid implant folders found.")
            return

        col1, col2 = st.columns(2)
        selected_site = col1.selectbox(
            f"🌍 {self.T("subtitle.site")}", sorted(implants_df["site_name"].unique())
        )
        filtered = implants_df[implants_df["site_name"] == selected_site]
        selected_implant = col2.selectbox(
            f"⚙️ {self.T("subtitle.implant")}", filtered["implant_name"]
        )

        selected_row = filtered[filtered["implant_name"] == selected_implant].iloc[0]
        return selected_row["subfolder"]

    # =========== ELEMENTS MANAGER ===========
    def tabs(self):
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
        if tab == 0:
            self.bus_links_manager()
        elif tab == 1:
            self.gens_manager()
        elif tab == 2:
            self.passive_manager()
        elif tab == 3:
            self.sensors_manager()

    # ----> Buses and Links Manager <----
    # ---- Main Manager container ----
    def bus_links_manager(self):
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
            if item == 0:
                self.add_bus()
            elif item == 1:
                self.add_line()
            elif item == 2:
                self.add_tranformer()

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
            st.rerun()

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
                    st.rerun()
                else:
                    st.error("Line Creation Failed")

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
                a, b = st.columns([1, 3.5])
                c, d = st.columns(2)
            if align == "end":
                b, a = st.columns([3.5, 1])
                d, c = st.columns(2)
            a.button("Reset", key=f"{id}_line_{align}_reset", disabled=True)
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
                error = self.grid.available_link(
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
            if item == 0:
                self.add_sgen()
            elif item == 1:
                self.add_gen()
            elif item == 2:
                self.add_storage()

    # ---- Add containers ----
    def add_sgen(self):
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
                    st.session_state["plant_grid"].add_active_element(
                        type="sgen", params=sgen
                    )
            st.rerun()

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
            st.rerun()

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
                a, b, _ = st.columns([3, 2, 1])
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
                a, b, _ = st.columns([3, 2, 1])
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
        quantity=True,
    ) -> Tuple[int, SGenParams]:
        labels_root = "tabs.gens.item.sgen"
        aviable_buses_name = list(self.grid.net.get("bus")["name"])
        sgen_type = 1
        n_new_sgen = None
        if sgen == None:
            bus = aviable_buses_name[0] if aviable_buses_name else None
            sgen: SGenParams = SGenParams(
                bus=bus, p_mw=0.4, q_mvar=0, name="New_PV", scaling=1, in_service=True
            )

        inputs = {
            "p_mv": [False, sgen["p_mw"]],
            "q_mvar": [False, sgen["q_mvar"]],
            "scaling": [False, sgen["scaling"]],
        }
        if "PV" in sgen["name"]:
            sgen_type = 0
            inputs["q_mvar"][0] = True

        with st.container(border=borders):
            buttons_labels = self.T(f"{labels_root}.labels")
            a, b = st.columns(2)
            # MAIN PROPERTIES
            with a:
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
                )
                if quantity:
                    n_new_sgen = st.number_input(
                        buttons_labels[1],
                        key=f"{id}_sgen_quantity",
                        value=1,
                        min_value=1,
                        step=1,
                    )
                sgen["name"] = st.text_input(
                    buttons_labels[0], key=f"{id}_sgen_name", value=sgen["name"]
                )
                sgen["in_service"] = sac.switch(
                    buttons_labels[2], value=sgen["in_service"], key=f"{id}_sgen_on"
                )
            # VOLTAGE PROPERTIES
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
            # PV SETUP
            with st.expander("⚡ PV Setup"):
                left, right = st.columns(2)
                fr = left.number_input(
                    buttons_labels[6],
                    key=f"{id}_sgen_sn_input",
                    value=sgen["sn_mvar"],
                )
                fr = right.number_input(
                    buttons_labels[7],
                    key=f"{id}_sgen_vm_input",
                    value=sgen["vm_pu"],
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

            with bus_cols[1]:
                sac.segmented(
                    items=[
                        sac.SegmentedItem(voltage),
                        sac.SegmentedItem(bus_level),
                        sac.SegmentedItem(bus_on),
                    ],
                    index=None,
                    color="lime",
                    disabled=True,
                    size="sm",
                    key=f"{id}_sgen_bus_prop",
                    align="end",
                )

        return n_new_sgen, sgen

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
                sac.divider(
                    self.T(f"{labels_root}.titles")[0],
                    align="center",
                    key=f"{id}_gen_prop_div",
                )
                if quantity:
                    n_new_gen = st.number_input(
                        buttons_labels[1],
                        key=f"{id}_gen_quantity",
                        value=1,
                        min_value=1,
                        step=1,
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

            with bus_cols[1]:
                sac.segmented(
                    items=[
                        sac.SegmentedItem(voltage),
                        sac.SegmentedItem(bus_level),
                        sac.SegmentedItem(bus_on),
                    ],
                    index=None,
                    color="lime",
                    disabled=True,
                    size="sm",
                    key=f"{id}_gen_bus_prop",
                    align="end",
                )

        return n_new_gen, gen

    #! TO IMPLEMENT

    def add_storage(self): ...

    def passive_manager(self):
        st.text("passives")

    def sensors_manager(self):
        st.text("sensors")

    # ----> Passive Elements Manager <----
    # ---- Main container ----
    # ---- Build Element containers ----
    # ---- Element Params Manager containers ----

    # ----> Sensors, Controls and Limits Manager <----
    # ---- Main container ----
    # ---- Build Element containers ----
    # ---- Element Params Manager containers ----


# -------------------------------------------------------------------------------------------------------------------------------


# def build_links_old(
#     self, borders: bool = True, bus: Optional[BusParams] = None
# ) -> Tuple[bool, LineParams]:
#     labels_root = "tabs.links.item.link"
#     with st.container(border=borders):
#         first, link, second = st.columns([1, 2, 1])

#         def select_bus(align="start", name=None):
#             a = None
#             b = None
#             if align == "start":
#                 a, b = st.columns([1, 3.5])
#                 c, d = st.columns(2)
#             if align == "end":
#                 b, a = st.columns([3.5, 1])
#                 d, c = st.columns(2)
#             a.button("Reset", key=f"{name}_Reset", disabled=True)
#             cols = st.columns(2)
#             with c:
#                 sac.divider(self.T(f"{labels_root}.bus_identity")[0], align=align)
#                 name = st.selectbox(
#                     label="Bus name",
#                     label_visibility="collapsed",
#                     options=list(self.grid.net.get("bus")["name"]),
#                     key=f"{align}_{name}Bus name",
#                 )
#             with d:
#                 sac.divider(self.T(f"{labels_root}.bus_identity")[1], align=align)
#                 index = st.number_input(
#                     label="Bus Index",
#                     label_visibility="collapsed",
#                     disabled=True,
#                     value=self.grid.get_element("bus", name=name, column="index"),
#                     key=f"{align}_{name}Bus Index",
#                 )
#             with b:
#                 map_level = {"b": 0, "n": 1, "m": 2}
#                 level_index = self.grid.get_element(
#                     element="bus", index=index, column="type"
#                 )
#                 if level_index:
#                     level_index = map_level[level_index]
#                 sac.segmented(
#                     items=[
#                         sac.SegmentedItem(name)
#                         for name in self.T(f"{labels_root}.bus_level")
#                     ],
#                     align="center",
#                     color="gren",
#                     size="sm",
#                     key=f"{align}_{name}_level_bus",
#                     disabled=True,
#                     index=level_index,
#                 )
#             return index

#         with first:
#             sac.divider(
#                 self.T(f"{labels_root}.buses")[0], align="center", variant="dashed"
#             )
#             start_bus = select_bus(name="1a")
#         with second:
#             sac.divider(
#                 self.T(f"{labels_root}.buses")[1], align="center", variant="dashed"
#             )
#             end_bus = select_bus("end", "1b")
#         with link:
#             label_line_params = self.T(f"{labels_root}.line_params")
#             a, b, c = st.columns([2, 1, 2])
#             type = a.selectbox(
#                 label_line_params[0], options=self.grid.get_aviable_lines()
#             )
#             length = b.number_input(label=f"{label_line_params[1]} (km)", value=0.1)
#             name = c.text_input(
#                 label_line_params[2], value=f"New_({type})_{length}km"
#             )
#             error_map = self.T(f"{labels_root}.errors")
#             color = "green"
#             buses = self.grid.net.bus
#             link_aviable = True
#             error = self.grid.aviable_link(
#                 buses.iloc[start_bus], buses.iloc[end_bus]
#             )
#             if error:
#                 color = "red"
#                 link_aviable = False
#             sac.divider(
#                 error_map[error],
#                 align="center",
#                 size=5,
#                 color=color,
#                 variant="dotted",
#             )
#             with st.expander(f"ℹ️ {self.T(f"{labels_root}.infos")[0]}"):
#                 start, end, line = st.tabs(tabs=self.T(f"{labels_root}.infos")[1:])
#                 with start:
#                     st.text(f"{self.grid.net.bus.iloc[start_bus]}")
#                 with end:
#                     st.text(f"{self.grid.net.bus.iloc[end_bus]}")
#                 with line:
#                     st.text(f"{self.grid.get_line_infos(type)}")
#         new_link = LineParams(
#             from_bus=start_bus,
#             to_bus=end_bus,
#             length_km=length,
#             name=name,
#             std_type=type,
#         )

#     return link_aviable, new_link
