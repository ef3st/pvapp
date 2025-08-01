from ....pages.page import Page
import streamlit as st
import streamlit_antd_components as sac
from pathlib import Path
import pandas as pd
import json
from pandapower_network.pvnetwork import PlantPowerGrid, BusParams, LineParams
from typing import Optional, Tuple
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
    def grid(self) -> Optional[PlantPowerGrid]:
        return st.session_state.plant_grid if "plant_grid" in st.session_state else None

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
            with rr:
                sac.result(
                    label="NO GRID",
                    description=self.T("messages.no_grid"),
                    status="empty",
                )
                if "plant_grid" not in st.session_state:
                    st.session_state["plant_grid"] = PlantPowerGrid()
        else:
            if "plant_grid" not in st.session_state:
                st.session_state["plant_grid"] = PlantPowerGrid(grid_file)

            st.markdown(f"{self.grid.net}")
        # Manage elements
        self.tabs()

        if ll.button(self.T("buttons.save_grid"), icon="💾"):
            self.grid.save(grid_file)
        st.markdown(f"{self.grid.net}")

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

    # -------- ELEMENTS MANAGER --------
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
            self.links_manager()
        elif tab == 1:
            self.gens_manager()
        elif tab == 2:
            self.passive_manager()
        elif tab == 3:
            self.sensors_manager()

    # ---- Links Manager ----

    def links_manager(self):
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

    def add_bus(self):
        labels_root = "tabs.links.item.bus"
        new_bus = self.bus_params()
        buttons_cols = st.columns([1, 1, 8])
        n_new_bus = buttons_cols[0].number_input(
            "n", label_visibility="collapsed", step=1, value=1, min_value=1
        )
        if buttons_cols[1].button(self.T(f"{labels_root}.add")):
            grid: PlantPowerGrid = self.grid
            n_bus = len(list(self.grid.net.bus["name"]))
            name = new_bus["name"]
            for i in range(0, n_new_bus):
                new_bus["name"] = f"{name}" + (f"_{n_bus+i}" if n_new_bus > 1 else "")
                grid.create_bus(new_bus)
            st.session_state["plant_grid"] = grid

    def add_line(self):
        labels_root = "tabs.links.item.link"

        aviable_link, new_links = self.build_links()
        if st.button(self.T(f"{labels_root}.add")):
            if aviable_link:
                st.session_state["plant_grid"].link_buses(new_links)
            else:
                st.error("Line Creation Failed")

    def add_tranformer(self): ...

    def bus_params(self, borders: bool = True, bus: Optional[BusParams] = None):
        labels_root = "tabs.links.item.bus"
        if not bus:
            bus: BusParams = BusParams(
                name="New_Bus", vn_kv=0.230, type="b", in_service="True"
            )
        with st.container(border=borders):
            titles = self.T(f"{labels_root}.titles")
            sectors = st.columns([1, 2, 6])
            with sectors[0]:
                sac.divider(label=titles[0], align="center")
                bus["name"] = st.text_input(
                    "Name", label_visibility="collapsed", value=bus["name"]
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
                    )
                ]
                bus["in_service"] = sac.switch(
                    self.T(f"{labels_root}.in_service"),
                    value=bus["in_service"],
                    position="left",
                    align="center",
                )

            with sectors[1]:
                sac.divider(label=titles[1], align="center")
                left, right = st.columns(2)
                with left:
                    voltage = sac.segmented(
                        items=[
                            sac.SegmentedItem(label=name)
                            for name in self.T(f"{labels_root}.voltage")
                        ],
                        direction="vertical",
                        color="grey",
                        align="center",
                        return_index=True,
                    )
                    voltage_type = bidict({"LV": 0, "MV": 1, "HV": 2, "EHV": 3})
                    voltages = {"LV": 0.250, "MV": 15, "HV": 150, "EHV": 380}
                    bus["vn_kv"] = st.number_input(
                        "Test",
                        label_visibility="collapsed",
                        disabled=True,
                        value=voltages[voltage_type.inv[voltage]],
                    )

                with right:
                    voltage_constraints = {
                        "LV": (0, 1),
                        "MV": (1, 35),
                        "HV": (36, 220),
                        "EHV": (220, 800),
                    }
                    contraints = voltage_constraints[voltage_type.inv[voltage]]
                    names = self.T(f"{labels_root}.constraints")
                    disabled = not st.checkbox(names[0])
                    min = st.number_input(
                        names[1], value=contraints[0], disabled=disabled
                    )
                    max = st.number_input(
                        names[2], value=contraints[1], disabled=disabled
                    )
                    if not disabled:
                        bus["min_vm_pu"] = min
                        bus["max_vm_pu"] = max

        return bus

    def build_links(
        self, borders: bool = True, bus: Optional[BusParams] = None
    ) -> Tuple[bool, LineParams]:
        labels_root = "tabs.links.item.link"
        with st.container(border=borders):
            first, link, second = st.columns([1, 2, 1])

            def select_bus(align="start", name=None):
                a = None
                b = None
                if align == "start":
                    a, b = st.columns([1, 3.5])
                    c, d = st.columns(2)
                if align == "end":
                    b, a = st.columns([3.5, 1])
                    d, c = st.columns(2)
                a.button("Reset", key=f"{name}_Reset", disabled=True)
                cols = st.columns(2)
                with c:
                    sac.divider(self.T(f"{labels_root}.bus_identity")[0], align=align)
                    name = st.selectbox(
                        label="Bus name",
                        label_visibility="collapsed",
                        options=list(self.grid.net.get("bus")["name"]),
                        key=f"{align}_{name}Bus name",
                    )
                with d:
                    sac.divider(self.T(f"{labels_root}.bus_identity")[1], align=align)
                    index = st.number_input(
                        label="Bus Index",
                        label_visibility="collapsed",
                        disabled=True,
                        value=self.grid.get_element("bus", name=name, column="index"),
                        key=f"{align}_{name}Bus Index",
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
                        key=f"{align}_{name}_level_bus",
                        disabled=True,
                        index=level_index,
                    )
                return index

            with first:
                sac.divider(
                    self.T(f"{labels_root}.buses")[0], align="center", variant="dashed"
                )
                start_bus = select_bus(name="1a")
            with second:
                sac.divider(
                    self.T(f"{labels_root}.buses")[1], align="center", variant="dashed"
                )
                end_bus = select_bus("end", "1b")
            with link:
                label_line_params = self.T(f"{labels_root}.line_params")
                a, b, c = st.columns([2, 1, 2])
                type = a.selectbox(
                    label_line_params[0], options=self.grid.get_aviable_lines()
                )
                length = b.number_input(label=f"{label_line_params[1]} (km)", value=0.1)
                name = c.text_input(
                    label_line_params[2], value=f"New_({type})_{length}km"
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
                )
                with st.expander(f"ℹ️ {self.T(f"{labels_root}.infos")[0]}"):
                    start, end, line = st.tabs(tabs=self.T(f"{labels_root}.infos")[1:])
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

    def gens_manager(self):
        st.text("gens")

    def passive_manager(self):
        st.text("passives")

    def sensors_manager(self):
        st.text("sensors")
