from ..page import Page
import json
from pathlib import Path
import streamlit as st
import pandas as pd
import streamlit_antd_components as sac
from .module.module import ModuleManager
from .grid.grid import GridManager
from .site.site import SiteManager
from typing import Union, Optional


class PlantManager(Page):
    def __init__(self) -> None:
        super().__init__("plant_manager")
        if "change" not in st.session_state:
            st.session_state["change"] = [False, False, False]

    def load_all_implants(self, folder: Path = Path("data/")) -> pd.DataFrame:
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

    def select_plant(self):
        implants_df = self.load_all_implants()
        if implants_df.empty:
            st.warning("No valid implant folders found.")
            return

        col1, col2 = st.columns(2)
        selected_site = col1.selectbox(
            f"🌍 {self.T("selection")[1]}", sorted(implants_df["site_name"].unique())
        )
        filtered = implants_df[implants_df["site_name"] == selected_site]
        selected_implant = col2.selectbox(
            f"⚙️ {self.T("selection")[2]}", filtered["implant_name"]
        )

        selected_row = filtered[filtered["implant_name"] == selected_implant].iloc[0]
        return selected_row["subfolder"]

    def render(self):
        st.title("🖥️ " + self.T("title"))
        ll, rr = st.columns([7, 5])
        # Select Plant
        with ll:
            with st.container(border=True):
                st.markdown(f"🔎 {self.T("selection")[0]}")
                if "subfolder" not in st.session_state:
                    st.session_state["subfolder"] = -1
                subfolder = self.select_plant()
                if (
                    "plant_manager" not in st.session_state
                    or subfolder != st.session_state["subfolder"]
                ):
                    st.session_state["plant_manager"] = {
                        "grid": GridManager(subfolder),
                        "module": ModuleManager(subfolder),
                        "site": SiteManager(subfolder),
                    }
                    st.session_state["subfolder"] = subfolder
                self.grid_manager = st.session_state["plant_manager"]["grid"]
                self.module_manager = st.session_state["plant_manager"]["module"]
                self.site_manager = st.session_state["plant_manager"]["site"]
                st.session_state["subfolder"] = subfolder

        sac.divider(
            "Display",
            align="center",
            variant="dashed",
            icon=sac.BsIcon("clipboard-fill", size=16),
        )
        labels_display = self.T("display_setup")
        a, b = st.columns([6, 1])
        with a:
            tab = sac.tabs(
                items=[
                    sac.TabsItem(labels_display[0], icon=sac.BsIcon("sun")),
                    sac.TabsItem(labels_display[1], icon=sac.BsIcon("diagram-3")),
                    sac.TabsItem(labels_display[2], icon=sac.BsIcon("compass")),
                ],
                variant="outline",
                return_index=True,
                key="display_tab",
            )
        with b:
            sumup = st.segmented_control(
                "sumup",
                options=labels_display[3:5],
                label_visibility="collapsed",
                selection_mode="multi",
            )

        scheme = True if labels_display[3] in sumup else False
        description = True if labels_display[4] in sumup else False
        self.show_sumup(tab, scheme, description)
        tab_display = 0
        if tab < 2:  # Not the site
            _, tab_col, _ = st.columns([1, 12, 1])
            with tab_col:
                tab_display = sac.tabs(
                    items=[
                        sac.TabsItem(
                            labels_display[5], icon=sac.BsIcon("gear-wide-connected")
                        ),
                        sac.TabsItem(labels_display[6], icon=sac.BsIcon("graph-up")),
                    ],
                    size="xs",
                    align="center",
                    return_index=True,
                )

        self.show_display(tab, tab_display)
        with rr.container(border=True):
            self.top_buttons()

    @st.fragment
    def top_buttons(self):
        rerun = False

        buttons_labels = self.T("buttons")
        save = {
            0: [
                self.site_manager,
                self.grid_manager,
                self.module_manager,
            ],
            1: [self.module_manager],
            2: [self.module_manager],
            3: [self.site_manager],
        }

        l, r = st.columns([1, 5])
        with l:
            sac.divider(f"{buttons_labels[1]}", icon=sac.BsIcon("floppy"))
        with r:
            icons = [
                sac.BsIcon("download"),
                sac.BsIcon("sun"),
                sac.BsIcon("diagram-3"),
                sac.BsIcon("compass"),
            ]
            st.session_state["enable_change"] = [
                True if True in st.session_state["change"] else False
            ] + st.session_state["change"]
            colors = [
                "red" if i else "green" for i in st.session_state["enable_change"]
            ]
            to_save = sac.buttons(
                items=[
                    sac.ButtonsItem(label=label, icon=icon, color=color)
                    for label, icon, color in zip(buttons_labels[2:], icons, colors)
                ],
                index=None,
                color="green",
                description=f"💾{buttons_labels[1]}",
                variant="dashed",
                gap="md",
                return_index=True,
                radius="lg",
                use_container_width=True,
            )

        d, a, b = st.columns([2, 2, 3])
        with d:
            sac.divider(f"{buttons_labels[6]}", icon=sac.BsIcon("fire"))

        if not (to_save == None):
            if st.session_state["enable_change"][to_save]:
                with b:
                    import time

                    with st.spinner("Saving", show_time=True):
                        for i, element in enumerate(save[to_save]):
                            element.save()
                            time.sleep(1)
                    if to_save > 0:
                        st.session_state["change"][to_save - 1] = False
                    else:
                        st.session_state["change"] = [False, False, False]
                    st.session_state["enable_sim"] = True
                    rerun = True
        with a:
            sim_file: Path = st.session_state["subfolder"] / "simulation.csv"
            if "enable_sim" not in st.session_state:
                st.session_state["enable_sim"] = not sim_file.exists()

            if st.session_state["enable_sim"]:
                color = "blue"
                variant = "outline"
            else:
                color = "blue"
                variant = "dashed"
            execute_sim = sac.buttons(
                items=[
                    sac.ButtonsItem(
                        f" {buttons_labels[0]}", icon=sac.BsIcon("collection-play")
                    )
                ],
                index=None,
                color=color,
                variant=variant,
                return_index=True,
                radius="lg",
                use_container_width=True,
            )

            if execute_sim == 0 and st.session_state["enable_sim"]:
                with b:
                    with st.spinner("Simulating", show_time=True):
                        from simulation.simulator import Simulator

                        Simulator(st.session_state["subfolder"]).run()
                st.session_state["enable_sim"] = False
                rerun = True
        if rerun:
            st.rerun()

    def show_sumup(self, tab: int, scheme: bool, description: bool) -> None:
        if tab == 1 and description:
            self.grid_manager.get_description()

    def show_display(self, tab: int = 0, display: int = 0) -> None:
        manager_map = {
            0: self.module_manager,
            1: self.grid_manager,
            2: self.site_manager,
        }

        manager: Union[SiteManager, ModuleManager, GridManager] = manager_map.get(tab)
        if manager is None:
            raise ValueError(f"Invalid tab index: {tab}")

        if display == 0:
            enable_change = manager.render_setup()

            if enable_change:
                st.session_state["change"][tab] = True
                # st.info(f"{tab} changed")
        elif display == 1:
            manager.render_analysis()
        else:
            raise ValueError(f"Invalid display index: {display}")
