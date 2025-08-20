from __future__ import annotations

from pathlib import Path
from typing import Optional, Union, List, Dict, Any
import json
import time

import streamlit as st
import pandas as pd
import streamlit_antd_components as sac

from ..page import Page
from .module.module import ModuleManager
from .grid.grid import GridManager
from .site.site import SiteManager


class PlantManager(Page):
    """Streamlit page that orchestrates site, module, and grid managers.

    This class provides a unified UI to:
    - Scan a data directory for available plants (site + implant folders)
    - Let the user select a plant
    - Display and edit configuration ("Setup") or analytics ("Analysis")
    - Save changes selectively (all / module / grid / site)
    - Run a simulation on demand

    Notes
    -----
    - Session state keys used:
        - "change": List[bool] of length 3, flags for [module, grid, site]
        - "subfolder": Path to the active plant directory
        - "plant_manager": cache of instantiated managers
        - "enable_sim": bool, whether simulation can be (re)run
        - "auto_save": bool, optional toggle to auto-save after edits (default False)
        - "auto_sim": bool, optional toggle to auto-run simulation after saving (default False)
    - The class assumes each plant folder contains both `site.json` and `implant.json`.
    """

    def __init__(self) -> None:
        super().__init__("plant_manager")

        # Initialize session-state defaults to avoid KeyError later.
        st.session_state.setdefault(
            "change", [False, False, False]
        )  # [module, grid, site]
        st.session_state.setdefault("subfolder", None)
        st.session_state.setdefault("plant_manager", None)
        st.session_state.setdefault("enable_sim", True)
        st.session_state.setdefault("auto_save", False)
        st.session_state.setdefault("auto_sim", False)

        # Placeholders for managers (assigned in render())
        self.grid_manager: Optional[GridManager] = None
        self.module_manager: Optional[ModuleManager] = None
        self.site_manager: Optional[SiteManager] = None

    # ---------------------------------------------------------------------
    # Data discovery & selection
    # ---------------------------------------------------------------------
    def load_all_implants(self, folder: Path = Path("data/")) -> pd.DataFrame:
        """Return a dataframe of available plants discovered under *folder*.

        Each valid plant is a subfolder that contains both `site.json` and
        `implant.json`. Basic metadata is aggregated for UI selection.

        Parameters
        ----------
        folder : Path
            Base directory to scan. Defaults to `data/`.

        Returns
        -------
        pd.DataFrame
            Columns: [site_name, implant_name, subfolder]
        """
        data: List[Dict[str, Any]] = []
        if not folder.exists():
            st.warning(f"Base folder not found: {folder}")
            return pd.DataFrame(columns=["site_name", "implant_name", "subfolder"])

        for subfolder in sorted(folder.iterdir()):
            if not subfolder.is_dir():
                continue

            site_file = subfolder / "site.json"
            implant_file = subfolder / "implant.json"

            if site_file.exists() and implant_file.exists():
                try:
                    with site_file.open("r", encoding="utf-8") as f_site:
                        site = json.load(f_site)
                    with implant_file.open("r", encoding="utf-8") as f_implant:
                        implant = json.load(f_implant)

                    data.append(
                        {
                            "site_name": site.get("name", "Unknown"),
                            "implant_name": implant.get("name", "Unnamed"),
                            "subfolder": subfolder,
                        }
                    )
                except (
                    Exception
                ) as e:  # Broad by design: surface any file/JSON issues to the UI.
                    st.error(f"Error reading '{subfolder.name}': {e}")

        return pd.DataFrame(data)

    def select_plant(self) -> Optional[Path]:
        """Render the site/implant selectors and return the chosen subfolder.

        Returns
        -------
        Optional[Path]
            The plant directory chosen by the user, or ``None`` if none are available.
        """
        implants_df = self.load_all_implants()
        if implants_df.empty:
            messages = self.T("messages.no_plant_found")
            sac.result(messages[0], description=messages[1], status="empty")
            return None

        col1, col2 = st.columns(2)
        selected_site: str = col1.selectbox(
            f"🌍 {self.T('selection')[1]}", sorted(implants_df["site_name"].unique())
        )

        filtered = implants_df[implants_df["site_name"] == selected_site]
        selected_implant: str = col2.selectbox(
            f"⚙️ {self.T('selection')[2]}", filtered["implant_name"].tolist()
        )

        selected_row = filtered[filtered["implant_name"] == selected_implant].iloc[0]
        return Path(selected_row["subfolder"])  # type: ignore[return-value]

    # ---------------------------------------------------------------------
    # Top-level page rendering
    # ---------------------------------------------------------------------
    def render(self, tab_index: int = 0) -> None:
        """Render the full Plant Manager page."""
        # st.title("🖥️ " + self.T("title"))
        sac.alert(
            self.T("title"),
            variant="quote-light",
            color="orange",
            size=35,
            icon=sac.BsIcon("building-fill-gear", color="white"),
        )

        left_col, right_col = st.columns([7, 5])

        # --- Selection & manager instantiation
        with left_col:
            with st.container(border=True):
                st.markdown(f"🔎 {self.T('selection')[0]}")

                subfolder = self.select_plant()
                if subfolder is None:
                    return  # Nothing more to render

                # (Re)build managers if first run or the plant changed
                if st.session_state.get(
                    "plant_manager"
                ) is None or subfolder != st.session_state.get("subfolder"):
                    st.session_state["plant_manager"] = {
                        "grid": GridManager(subfolder),
                        "module": ModuleManager(subfolder),
                        "site": SiteManager(subfolder),
                    }
                    st.session_state["subfolder"] = subfolder

                # Local references for convenience
                self.grid_manager = st.session_state["plant_manager"]["grid"]
                self.module_manager = st.session_state["plant_manager"]["module"]
                self.site_manager = st.session_state["plant_manager"]["site"]

        # --- Display options header
        sac.divider(
            "Display",
            align="center",
            variant="dashed",
            icon=sac.BsIcon("clipboard-fill", size=16),
        )

        labels_display = self.T("display_setup")
        a, b = st.columns([6, 1])

        # Primary tabs: Module / Grid / Site
        with a:
            tab_index = sac.tabs(
                items=[
                    sac.TabsItem(labels_display[0], icon=sac.BsIcon("sun")),
                    sac.TabsItem(labels_display[1], icon=sac.BsIcon("diagram-3")),
                    sac.TabsItem(labels_display[2], icon=sac.BsIcon("compass")),
                ],
                variant="outline",
                return_index=True,
                key="display_tab",
                index=tab_index,
            )

        # Sum-up switches: show scheme / show description
        with b:
            sumup = st.segmented_control(
                "sumup",
                options=labels_display[3:5],
                label_visibility="collapsed",
                selection_mode="multi",
            )

        scheme = labels_display[3] in sumup
        description = labels_display[4] in sumup
        placeholeder = st.empty()
        with placeholeder.container():
            self.show_sumup(tab_index, scheme, description)

        # Secondary tabs (except for the Site): Setup / Analysis
        tab_display = 0
        if tab_index < 2:
            _, tab_col, _ = st.columns([1, 12, 1])
            with tab_col:
                tab_display = sac.tabs(
                    items=[
                        sac.TabsItem(
                            labels_display[5], icon=sac.BsIcon("gear-wide-connected")
                        ),
                        sac.TabsItem(labels_display[6], icon=sac.BsIcon("graph-up")),
                    ],
                    size="sm",
                    align="center",
                    return_index=True,
                    color="orange",
                )

        # Main content region
        try:
            self.show_display(tab_index, tab_display)
        except ValueError as e:
            self.logger.error("[PlantManagerPage] Errors in show_display(): {e}")

        # Right side: top action buttons (save / simulate)
        with right_col.empty():
            with st.container(border=True):
                self.top_buttons()

    # ---------------------------------------------------------------------
    # Actions (save / simulate)
    # ---------------------------------------------------------------------
    @st.fragment
    def top_buttons(self) -> None:
        """Render the top action buttons (save & simulate) and handle actions."""
        buttons_labels = self.T("buttons")

        # Mapping for which managers to save per button index
        save_targets = {
            0: [self.module_manager, self.grid_manager, self.site_manager],  # Save all
            1: [self.module_manager],  # Save module only
            2: [self.grid_manager],  # Save grid only
            3: [self.site_manager],  # Save site only
        }

        # --- Header
        l, r = st.columns([1, 5])
        with l:
            sac.divider(f"{buttons_labels[1]}", icon=sac.BsIcon("floppy"))

        # --- Save buttons group
        with r:
            icons = [
                sac.BsIcon("download"),
                sac.BsIcon("sun"),
                sac.BsIcon("diagram-3"),
                sac.BsIcon("compass"),
            ]

            # Build enable flags: index 0 refers to "any changed?" then per-manager
            st.session_state["enable_change"] = [
                any(st.session_state["change"])
            ] + st.session_state["change"]
            colors = [
                "red" if flag else "green" for flag in st.session_state["enable_change"]
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

        # --- Simulate header
        d, a, b = st.columns([2, 2, 3])
        with d:
            sac.divider(f"{buttons_labels[6]}", icon=sac.BsIcon("fire"))

        rerun_needed = False

        # --- Handle save
        if to_save is not None:
            if st.session_state["enable_change"][to_save]:
                with b:
                    with st.spinner("Saving", show_time=True):
                        for manager in save_targets[to_save]:
                            if manager is not None:
                                manager.save()
                                time.sleep(1)

                    # Reset change flags accordingly
                    if to_save > 0:
                        st.session_state["change"][to_save - 1] = False
                    else:
                        st.session_state["change"] = [False, False, False]

                    st.session_state["enable_sim"] = True
                    rerun_needed = True

        # --- Simulate button
        with a:
            subfolder: Optional[Path] = st.session_state.get("subfolder")
            sim_file = (
                (subfolder / "simulation.csv") if isinstance(subfolder, Path) else None
            )

            # Enable if no existing results or after a save
            if sim_file is not None:
                st.session_state["enable_sim"] = (
                    not sim_file.exists() or st.session_state.get("enable_sim", True)
                )

            color = "blue"
            variant = (
                "outline" if st.session_state.get("enable_sim", True) else "dashed"
            )

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

            # Auto or user-triggered simulation
            should_run_sim = (
                (execute_sim == 0) or bool(st.session_state.get("auto_sim", False))
            ) and bool(st.session_state.get("enable_sim", True))

            if should_run_sim and isinstance(subfolder, Path):
                with b:
                    with st.spinner("Simulating", show_time=True):
                        from simulation.simulator import Simulator

                        Simulator(subfolder).run()
                st.session_state["enable_sim"] = False
                rerun_needed = True

        if rerun_needed:
            st.rerun()

    # ---------------------------------------------------------------------
    # Programmatic save/simulate helpers (used by auto-save/auto-sim)
    # ---------------------------------------------------------------------
    def save_all(self) -> None:
        """Save all managers that have pending changes.

        Resets change flags, optionally triggers simulation if `auto_sim` is ON,
        and requests a rerun to refresh the UI.
        """
        elements_to_save = [self.module_manager, self.grid_manager, self.site_manager]

        st.toast("Saving", icon="💾")
        for idx, manager in enumerate(elements_to_save):
            if manager is not None and st.session_state["change"][idx]:
                manager.save()
                time.sleep(1)

        st.session_state["change"] = [False, False, False]
        st.session_state["enable_sim"] = True

        if st.session_state.get("auto_sim", False):
            self.sim_all()

        st.rerun()

    def sim_all(self) -> None:
        """Run a simulation for the current plant if enabled."""
        st.toast("Simulating", icon="🔥")

        if not st.session_state.get("enable_sim", True):
            return

        subfolder = st.session_state.get("subfolder")
        if isinstance(subfolder, Path):
            from simulation.simulator import Simulator

            Simulator(subfolder).run()
            st.session_state["enable_sim"] = False

    # ---------------------------------------------------------------------
    # Content rendering helpers
    # ---------------------------------------------------------------------
    def show_sumup(self, tab: int, scheme: bool, description: bool) -> None:
        """Render optional summaries per active tab.

        Parameters
        ----------
        tab : int
            Active top-level tab index (0=Module, 1=Grid, 2=Site)
        scheme : bool
            Whether to show the scheme (not used here; reserved for future use)
        description : bool
            Whether to show descriptions/metadata where available
        """
        # Only Grid currently exposes a textual description
        if tab == 1 and self.grid_manager is not None:
            if scheme:
                self.grid_manager.get_scheme()
            if description:
                self.grid_manager.get_description()

    def show_display(self, tab: int = 0, display: int = 0) -> None:
        """Dispatch rendering to the selected manager and view.

        Parameters
        ----------
        tab : int
            Which primary tab is active (0=Module, 1=Grid, 2=Site)
        display : int
            Which secondary tab is active (0=Setup, 1=Analysis)
        """
        if (
            self.module_manager is None
            or self.grid_manager is None
            or self.site_manager is None
        ):
            return

        manager_map: Dict[int, Union[SiteManager, ModuleManager, GridManager]] = {
            0: self.module_manager,
            1: self.grid_manager,
            2: self.site_manager,
        }

        manager = manager_map.get(tab)
        if manager is None:
            raise ValueError(f"Invalid tab index: {tab}")

        if display == 0:  # Setup view
            # If the manager reports a change and auto-save is enabled, persist it
            enable_change = manager.render_setup()
            if enable_change:
                st.session_state["change"][tab] = True
                if st.session_state.get("auto_save", False):
                    self.save_all()
        elif display == 1:  # Analysis view
            manager.render_analysis()
        else:
            raise ValueError(f"Invalid display index: {display}")


# from ..page import Page
# import json
# from pathlib import Path
# import streamlit as st
# import pandas as pd
# import streamlit_antd_components as sac
# from .module.module import ModuleManager
# from .grid.grid import GridManager
# from .site.site import SiteManager
# from typing import Union, Optional

# import time

# class PlantManager(Page):
#     def __init__(self) -> None:
#         super().__init__("plant_manager")
#         if "change" not in st.session_state:
#             st.session_state["change"] = [False, False, False]

#     def load_all_implants(self, folder: Path = Path("data/")) -> pd.DataFrame:
#         data = []
#         for subfolder in sorted(folder.iterdir()):
#             if subfolder.is_dir():
#                 site_file = subfolder / "site.json"
#                 implant_file = subfolder / "implant.json"
#                 if site_file.exists() and implant_file.exists():
#                     try:
#                         site = json.load(site_file.open())
#                         implant = json.load(implant_file.open())
#                         data.append(
#                             {
#                                 "site_name": site.get("name", "Unknown"),
#                                 "implant_name": implant.get("name", "Unnamed"),
#                                 "subfolder": subfolder,
#                             }
#                         )
#                     except Exception as e:
#                         st.error(f"Error reading {subfolder.name}: {e}")
#         return pd.DataFrame(data)

#     def select_plant(self):
#         implants_df = self.load_all_implants()
#         if implants_df.empty:
#             st.warning("No valid implant folders found.")
#             return

#         col1, col2 = st.columns(2)
#         selected_site = col1.selectbox(
#             f"🌍 {self.T("selection")[1]}", sorted(implants_df["site_name"].unique())
#         )
#         filtered = implants_df[implants_df["site_name"] == selected_site]
#         selected_implant = col2.selectbox(
#             f"⚙️ {self.T("selection")[2]}", filtered["implant_name"]
#         )

#         selected_row = filtered[filtered["implant_name"] == selected_implant].iloc[0]
#         return selected_row["subfolder"]

#     def render(self):
#         st.title("🖥️ " + self.T("title"))
#         ll, rr = st.columns([7, 5])
#         # Select Plant
#         with ll:
#             with st.container(border=True):
#                 st.markdown(f"🔎 {self.T("selection")[0]}")
#                 if "subfolder" not in st.session_state:
#                     st.session_state["subfolder"] = -1
#                 subfolder = self.select_plant()
#                 if (
#                     "plant_manager" not in st.session_state
#                     or subfolder != st.session_state["subfolder"]
#                 ):
#                     st.session_state["plant_manager"] = {
#                         "grid": GridManager(subfolder),
#                         "module": ModuleManager(subfolder),
#                         "site": SiteManager(subfolder),
#                     }
#                     st.session_state["subfolder"] = subfolder
#                 self.grid_manager = st.session_state["plant_manager"]["grid"]
#                 self.module_manager = st.session_state["plant_manager"]["module"]
#                 self.site_manager = st.session_state["plant_manager"]["site"]
#                 st.session_state["subfolder"] = subfolder

#         sac.divider(
#             "Display",
#             align="center",
#             variant="dashed",
#             icon=sac.BsIcon("clipboard-fill", size=16),
#         )
#         labels_display = self.T("display_setup")
#         a, b = st.columns([6, 1])
#         with a:
#             tab = sac.tabs(
#                 items=[
#                     sac.TabsItem(labels_display[0], icon=sac.BsIcon("sun")),
#                     sac.TabsItem(labels_display[1], icon=sac.BsIcon("diagram-3")),
#                     sac.TabsItem(labels_display[2], icon=sac.BsIcon("compass")),
#                 ],
#                 variant="outline",
#                 return_index=True,
#                 key="display_tab",
#             )
#         with b:
#             sumup = st.segmented_control(
#                 "sumup",
#                 options=labels_display[3:5],
#                 label_visibility="collapsed",
#                 selection_mode="multi",
#             )

#         scheme = True if labels_display[3] in sumup else False
#         description = True if labels_display[4] in sumup else False
#         self.show_sumup(tab, scheme, description)
#         tab_display = 0
#         if tab < 2:  # Not the site
#             _, tab_col, _ = st.columns([1, 12, 1])
#             with tab_col:
#                 tab_display = sac.tabs(
#                     items=[
#                         sac.TabsItem(
#                             labels_display[5], icon=sac.BsIcon("gear-wide-connected")
#                         ),
#                         sac.TabsItem(labels_display[6], icon=sac.BsIcon("graph-up")),
#                     ],
#                     size="xs",
#                     align="center",
#                     return_index=True,
#                 )

#         self.show_display(tab, tab_display)
#         with rr.container(border=True):
#             self.top_buttons()

#     @st.fragment
#     def top_buttons(self):
#         rerun = False

#         buttons_labels = self.T("buttons")
#         save = {
#             0: [
#                 self.module_manager,
#                 self.grid_manager,
#                 self.site_manager,
#             ],
#             1: [self.module_manager],
#             2: [self.grid_manager],
#             3: [self.site_manager],
#         }

#         l, r = st.columns([1, 5])
#         with l:
#             sac.divider(f"{buttons_labels[1]}", icon=sac.BsIcon("floppy"))
#         with r:
#             icons = [
#                 sac.BsIcon("download"),
#                 sac.BsIcon("sun"),
#                 sac.BsIcon("diagram-3"),
#                 sac.BsIcon("compass"),
#             ]
#             st.session_state["enable_change"] = [
#                 True if True in st.session_state["change"] else False
#             ] + st.session_state["change"]
#             colors = [
#                 "red" if i else "green" for i in st.session_state["enable_change"]
#             ]
#             to_save = sac.buttons(
#                 items=[
#                     sac.ButtonsItem(label=label, icon=icon, color=color)
#                     for label, icon, color in zip(buttons_labels[2:], icons, colors)
#                 ],
#                 index=None,
#                 color="green",
#                 description=f"💾{buttons_labels[1]}",
#                 variant="dashed",
#                 gap="md",
#                 return_index=True,
#                 radius="lg",
#                 use_container_width=True,
#             )

#         d, a, b = st.columns([2, 2, 3])
#         with d:
#             sac.divider(f"{buttons_labels[6]}", icon=sac.BsIcon("fire"))

#         if not (to_save == None):
#             if st.session_state["enable_change"][to_save]:
#                 with b:

#                     with st.spinner("Saving", show_time=True):
#                         for i, element in enumerate(save[to_save]):
#                             element.save()
#                             time.sleep(1)
#                     if to_save > 0:
#                         st.session_state["change"][to_save - 1] = False
#                     else:
#                         st.session_state["change"] = [False, False, False]
#                     st.session_state["enable_sim"] = True
#                     rerun = True
#         with a:
#             sim_file: Path = st.session_state["subfolder"] / "simulation.csv"
#             if "enable_sim" not in st.session_state:
#                 st.session_state["enable_sim"] = not sim_file.exists()

#             if st.session_state["enable_sim"]:
#                 color = "blue"
#                 variant = "outline"
#             else:
#                 color = "blue"
#                 variant = "dashed"
#             execute_sim = sac.buttons(
#                 items=[
#                     sac.ButtonsItem(
#                         f" {buttons_labels[0]}", icon=sac.BsIcon("collection-play")
#                     )
#                 ],
#                 index=None,
#                 color=color,
#                 variant=variant,
#                 return_index=True,
#                 radius="lg",
#                 use_container_width=True,
#             )

#             if (execute_sim == 0 or st.session_state["auto_sim"]) and st.session_state["enable_sim"]:
#                 with b:
#                     with st.spinner("Simulating", show_time=True):
#                         from simulation.simulator import Simulator

#                         Simulator(st.session_state["subfolder"]).run()
#                 st.session_state["enable_sim"] = False
#                 rerun = True
#         if rerun:
#             st.rerun()

#     def save_all(self):
#         elements_to_save = [
#                 self.module_manager,
#                 self.grid_manager,
#                 self.site_manager,
#             ]
#         st.toast("Saving",icon="💾")
#         for i, element in enumerate(elements_to_save):
#             if st.session_state["change"][i]:
#                 element.save()
#                 time.sleep(1)
#         st.session_state["change"] = [False, False, False]
#         st.session_state["enable_sim"] = True
#         if st.session_state["auto_sim"]:
#                 self.sim_all()
#         st.rerun()
#     def sim_all(self):
#         st.toast("Simulating",icon="🔥")
#         if st.session_state["enable_sim"]:
#             from simulation.simulator import Simulator
#             Simulator(st.session_state["subfolder"]).run()
#             st.session_state["enable_sim"] = False


#     def show_sumup(self, tab: int, scheme: bool, description: bool) -> None:
#         if tab == 1 and description:
#             self.grid_manager.get_description()

#     def show_display(self, tab: int = 0, display: int = 0) -> None:
#         manager_map = {
#             0: self.module_manager,
#             1: self.grid_manager,
#             2: self.site_manager,
#         }

#         manager: Union[SiteManager, ModuleManager, GridManager] = manager_map.get(tab)
#         if manager is None:
#             raise ValueError(f"Invalid tab index: {tab}")

#         if display == 0:
#             enable_change = manager.render_setup()

#             if enable_change:
#                 st.session_state["change"][tab] = True
#                 if st.session_state["auto_save"]:
#                     self.save_all()


#                 # st.info(f"{tab} changed")
#         elif display == 1:
#             manager.render_analysis()
#         else:
#             raise ValueError(f"Invalid display index: {display}")
