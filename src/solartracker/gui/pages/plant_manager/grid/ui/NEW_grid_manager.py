from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Union

import json
import re

import pandas as pd
import streamlit as st
from streamlit.errors import StreamlitAPIException

from functools import singledispatchmethod
from contextlib import contextmanager

from ..core.registry import ElementSpec
from ....page import Page
from pandapower_network.pvnetwork import (
    PlantPowerGrid,
)


# ===================================================================
#                         Grid Manager UI
# ===================================================================


class GridManager(Page):
    """
    Interactive grid builder and editor for PlantPowerGrid.

    The UI is organized in four tabs:
      1) Links (buses, lines, transformers and switches)
      2) Generators (sgen, gen, storage)
      3) Passive elements
      4) Sensors & controllers

    Design for maintainability & extensibility
    -----------------------------------------
    This class provides reusable primitives and patterns:
      - ElementSpec registry via Dependency Injection.
      - `_build_items(...)`: generic grid of parameter editors with +/- controls.
      - `add_any(...)`: single creation flow for all element kinds.
      - `@singledispatchmethod` for editing (bus/line/...).
      - Context manager `grid_change(...)` to toggle the "modified" state.

    ------
    Note:
        Comments in code are in English per project preference.
    """

    # ========== LIFECYCLE ==========
    def __init__(self, subfolder: Path) -> None:
        """
        Initialize the page, load or create a grid model, and wire element specs.

        Args:
            subfolder (Path): Folder that holds `grid.json` and related assets.

        Returns:
            None
        ------
        Note:
            - Uses DI to register UI builders and model actions for "bus" and "line".
            - Extend `self.element_specs` to add new element types (e.g., transformer).
        """
        super().__init__("grid_manager")

        self.grid_file: Path = subfolder / "grid.json"
        if self.grid_file.exists():
            st.session_state["plant_grid"] = PlantPowerGrid(self.grid_file)
        else:
            st.session_state["plant_grid"] = PlantPowerGrid()

        st.session_state.setdefault(
            "arrays_to_add", {}
        )  # PV arrays pending persistence
        st.session_state.setdefault("modified", False)  # grid change flag

        # ---- Dependency Injection: register element specs here ----
        self.element_specs: Dict[str, ElementSpec] = {
            # BUS
            "bus": ElementSpec(
                kind="bus",
                label="Bus",
                build_params_ui=lambda *, id="bus", defaults=None: self._wrap_bus_params(
                    id=id, defaults=defaults
                ),
                create_in_grid=lambda grid, payload: self._create_bus(grid, payload),
                update_in_grid=lambda grid, payload: self._update_bus(grid, payload),
            ),
            # LINE
            "line": ElementSpec(
                kind="line",
                label="Line",
                build_params_ui=lambda *, id="line", defaults=None: self._wrap_line_params(
                    id=id, defaults=defaults
                ),
                create_in_grid=lambda grid, payload: self._create_line(grid, payload),
                update_in_grid=lambda grid, payload: self._update_line(grid, payload),
            ),
            # You can add here: "transformer", "switch", ...
        }

    # ========== PROPERTIES ==========
    @property
    def grid(self) -> PlantPowerGrid:
        """
        Get the current grid model from session state.

        Returns:
            PlantPowerGrid: The active grid model instance.
        ------
        Note:
            Falls back to a new PlantPowerGrid if not present in session state.
        """
        return st.session_state.get("plant_grid", PlantPowerGrid())

    @property
    def pv_arrays(self) -> Dict[int, PVParams]:
        """
        PV arrays staged for persistence (keyed by SGen index).

        Returns:
            Dict[int, PVParams]: Mapping SGen index -> PVParams object.
        ------
        Note:
            Updated on save() into `arrays.json`.
        """
        return st.session_state.get("arrays_to_add", {})

    # =============== RENDERS ============
    def render_setup(self) -> bool:
        """
        Render setup/management UI and return True if the grid changed.

        Args:
            None

        Returns:
            bool: True if any operation marked the grid as modified.
        ------
        Note:
            Builds the main tabbed UI and delegates to tab-specific renderers.
        """
        if self.grid.net.bus.empty:
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

        changed = False
        if tab == 0:
            changed |= self.render_bus_links_tab()
        elif tab == 1:
            changed |= self.active_elements_manager()
        elif tab == 2:
            changed |= self.passive_manager()
        elif tab == 3:
            changed |= self.sensors_manager()

        # Bubble up any pending "modified" flag set by operations
        changed |= bool(st.session_state.get("modified"))
        if st.session_state.get("modified"):
            st.session_state["modified"] = False
        return changed

    def render_analysis(self) -> None:
        """
        Placeholder for future analysis UI.

        Returns:
            None
        """
        ...

    # =========== SUMMARIES ==========
    def get_scheme(self):
        """
        Placeholder hook for future schematic export.

        Returns:
            None
        """
        ...

    def get_description(self) -> None:
        """
        Show a compact textual resume of the grid.

        Args:
            None

        Returns:
            None
        ------
        Note:
            Dumps `self.grid.net` string representation into a disabled text area.
        """
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
        """
        Persist the grid and any staged PV arrays to disk.

        Args:
            None

        Returns:
            None
        ------
        Note:
            - Saves the pandapower net to `grid.json`.
            - Merges `arrays_to_add` into `arrays.json` and clears the staging dict.
        """
        self.grid.save(self.grid_file)

        if self.pv_arrays:
            arrays: Dict[str, Any] = {}
            path = self.grid_file.parent / "arrays.json"
            if path.exists():
                with path.open("r", encoding="utf-8") as f:
                    arrays = json.load(f)
            arrays.update({str(k): v for k, v in self.pv_arrays.items()})
            with path.open("w", encoding="utf-8") as f:
                json.dump(arrays, f, indent=4, ensure_ascii=False)
            st.session_state["arrays_to_add"] = {}

    # =========================================================
    #                         TABS
    # =========================================================

    # ============= LINKS (BUSES / LINES / TX) TAB ===============
    def render_bus_links_tab(self) -> bool:
        """
        Render the 'Links' tab, including adders and managers for buses/lines.

        Returns:
            bool: True if the grid was modified by actions in this tab.
        ------
        Note:
            Uses generic creation via `add_any("bus"|"line")` and the managers.
        """
        labels_root = "tabs.links"
        changed = False

        # --- Adder ---
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
                changed |= self.add_bus()
            elif item == 1:
                changed |= self.add_line()
            elif item == 2:
                changed |= self.add_transformer()

        with st.container():
            self.bus_links_manager()

        return changed

    # -------------> Parameter editors <-------------
    def bus_params(
        self,
        borders: bool = True,
        id: Union[int, str] = 1,
        quantity: bool = True,
        bus: Optional["BusParams"] = None,
    ) -> Tuple[int, "BusParams"]:
        """
        Render the editor for a Bus and return (quantity, params).

        Args:
            borders (bool): Draw a border around the editor container.
            id (Union[int, str]): Unique UI id suffix for the widget keys.
            quantity (bool): If True, show a quantity selector.
            bus (Optional[BusParams]): Pre-filled bus parameters to edit.

        Returns:
            Tuple[int, BusParams]: (quantity, updated_bus_params)
        ------
        Note:
            - Uses segmented controls for bus level (b/n/m) and voltage ranges.
            - Writes fields in-place into `bus` dict-like (TypedDict compatible).
        """
        labels_root = "tabs.links.item.bus"

        if bus is None:
            bus = BusParams(name="New_Bus", vn_kv=0.230, type="b", in_service=True)

        n_new_bus: Optional[int] = None

        with st.container(border=borders):
            titles = self.T(f"{labels_root}.titles")
            left, right = st.columns([1, 2])

            with left:
                sac.divider(label=titles[0], align="center", key=f"{id}_bus_prop_div")
                bus["name"] = st.text_input(
                    "Name",
                    label_visibility="collapsed",
                    value=bus["name"],
                    key=f"{id}_bus_name",
                )

                type_idx = {"b": 0, "n": 1, "m": 2}
                idx = sac.segmented(
                    items=[
                        sac.SegmentedItem(label)
                        for label in self.T(f"{labels_root}.bus_level")
                    ],
                    direction="vertical",
                    color="grey",
                    index=type_idx.get(bus["type"], 0),
                    return_index=True,
                    align="center",
                    key=f"{id}_bus_type",
                )
                bus["type"] = {v: k for k, v in type_idx.items()}[idx]

                bus["in_service"] = sac.switch(
                    self.T(f"{labels_root}.in_service"),
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

            with right:
                sac.divider(label=titles[1], align="center", key=f"{id}_bus_volt_div")
                left2, right2 = st.columns(2)

                values_constraints = {
                    "LV": (0.0, 1.0),
                    "MV": (1.0, 35.0),
                    "HV": (36.0, 220.0),
                    "EHV": (220.0, 800.0),
                }
                voltage_type = {"LV": 0, "MV": 1, "HV": 2, "EHV": 3}
                voltages = {"LV": 0.250, "MV": 15.0, "HV": 150.0, "EHV": 380.0}
                with left2:
                    # pick category by current vn_kv
                    idx = 0
                    for k, (lo, hi) in values_constraints.items():
                        if lo <= bus["vn_kv"] <= hi:
                            idx = voltage_type[k]
                            break
                    voltage_idx = sac.segmented(
                        items=[
                            sac.SegmentedItem(label)
                            for label in self.T(f"{labels_root}.voltage")
                        ],
                        direction="vertical",
                        color="grey",
                        index=idx,
                        align="center",
                        return_index=True,
                        key=f"{id}_bus_voltage_str",
                    )
                    labels = self.T(f"{labels_root}.constraints")
                    enable_limits = st.checkbox(labels[0], key=f"{id}_bus_set_limits")

                with right2:
                    constraints = list(values_constraints.values())[voltage_idx]
                    bus["vn_kv"] = st.number_input(
                        labels[1],
                        disabled=True,
                        value=voltages[list(voltage_type.keys())[voltage_idx]],
                        key=f"{id}_bus_volt_int",
                    )

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

    def line_params(
        self,
        borders: bool = True,
        id: Union[int, str] = 1,
        line: Optional["LineParams"] = None,
        horizontal: bool = True,
    ) -> Tuple[bool, "LineParams"]:
        """
        Render the editor for a Line and return (is_valid, params).

        Args:
            borders (bool): Draw a border around the editor container.
            id (Union[int, str]): Unique UI id suffix for the widget keys.
            line (Optional[LineParams]): Pre-filled line parameters to edit.
            horizontal (bool): Layout orientation for bus selectors.

        Returns:
            Tuple[bool, LineParams]: (is_valid, updated_line_params)
        ------
        Note:
            - Validates whether a link between the selected buses is allowed.
            - Shows read-only bus level segments (b/n/m) for context.
        """
        labels_root = "tabs.links.item.link"
        line_types = self.grid.get_aviable_lines()

        if line is None:
            line = LineParams(
                from_bus=0,
                to_bus=0,
                length_km=0.1,
                name="New_(NAVY 4x50 SE)_0.1km",
                std_type=line_types[0] if line_types else "",
            )

        def select_bus(align: str = "start", bus_id: Optional[int] = None) -> int:
            """
            Render a bus selector and return the chosen index.

            Args:
                align (str): "start" or "end" – only affects UI alignment.
                bus_id (Optional[int]): Default selected bus index.

            Returns:
                int: Selected bus index (pandapower bus table index).
            """
            a = b = c = d = st.container()
            if horizontal:
                if align == "start":
                    a, b = st.columns([1, 10])  # noqa: F841
                    c, d = st.columns(2)
                else:
                    b, a = st.columns([10, 1])  # noqa: F841
                    d, c = st.columns(2)

            with c:
                sac.divider(
                    self.T(f"{labels_root}.bus_identity")[0],
                    align=align,
                    key=f"{id}_line_{align}_bus_name_div",
                )
                opts = list(self.grid.net.get("bus")["name"])
                bus_id = 0 if bus_id is None else int(bus_id)
                name = st.selectbox(
                    label="Bus name",
                    label_visibility="collapsed",
                    options=opts,
                    index=min(bus_id, max(0, len(opts) - 1)),
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
                level_map = {"b": 0, "n": 1, "m": 2}
                level_val = self.grid.get_element("bus", index=index, column="type")
                level_idx = level_map.get(level_val, None)
                sac.segmented(
                    items=[
                        sac.SegmentedItem(lbl)
                        for lbl in self.T(f"{labels_root}.bus_level")
                    ],
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
            first, link_box, second = st.columns([1, 2, 1])

            with first:
                sac.divider(
                    self.T(f"{labels_root}.buses")[0],
                    align="center",
                    variant="dashed",
                    key=f"{id}_line_startbus_div",
                )
                start_bus = select_bus("start", line["from_bus"])

            with second:
                sac.divider(
                    self.T(f"{labels_root}.buses")[1],
                    align="center",
                    variant="dashed",
                    key=f"{id}_line_endbus_div",
                )
                end_bus = select_bus("end", line["to_bus"])

            with link_box:
                labels = self.T(f"{labels_root}.line_params")
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

                error_map = self.T(f"{labels_root}.errors")
                color = "green"
                buses_df = self.grid.net.bus
                link_available = True
                error_code = self.grid.aviable_link(
                    buses_df.iloc[start_bus], buses_df.iloc[end_bus]
                )
                if error_code:
                    color = "red"
                    link_available = False

                sac.divider(
                    error_map[error_code],
                    align="center",
                    size=5,
                    color=color,
                    variant="dotted",
                    key=f"{id}_line_status_div",
                )

                with st.expander(f"ℹ️ {self.T(f'{labels_root}.infos')[0]}"):
                    line_tab, start_tab, end_tab = st.tabs(
                        tabs=self.T(f"{labels_root}.infos")[1:]
                    )
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

        return link_available, new_line

    # -------------> Manager <--------
    @st.fragment
    def bus_links_manager(self):
        """
        Render the combined manager for buses (tree) and connections (list).

        Args:
            None

        Returns:
            None
        ------
        Note:
            - Left side: bus tree with connected elements (and edit on selection).
            - Right side: connection rows (line/trafo/etc.) with color-coded voltage.
        """
        df = self.grid.summarize_buses()
        st.dataframe(df.drop(columns=["elements"]))

        with st.expander("Rete elettrica (bus → elementi)"):
            icon_cols = st.columns(8)
            col = 0
            for i, icon in enumerate(ICON_MAP):
                if col == 8:
                    col = 0
                with icon_cols[col]:
                    sac.segmented(
                        items=[
                            sac.SegmentedItem(icon=ICON_MAP[icon]),
                            sac.SegmentedItem(icon),
                        ],
                        index=None,
                        color="grey",
                        readonly=True,
                        size="sm",
                        bg_color="#043b41",
                    )
                col += 1

        tree_bus, connection = st.columns([2, 5])
        with connection:
            self.manager_connections()
        with tree_bus:
            self.manager_buses()

    def manager_buses(self):
        """
        Render the bus tree and open edit dialog when a bus is selected.

        Returns:
            None
        ------
        Note:
            - Uses `build_sac_tree_from_bus_df(...)` (assumed available) to build the tree kwargs.
            - On selection of a bus node like "[42] BusName", extracts `bus_id` and opens editor.
        """
        df = self.grid.summarize_buses().copy()
        show_connectors = st.toggle("Show connectors", key="bus_tree_show_connectors")

        with st.empty():
            if "original_tree" not in st.session_state:
                st.session_state.original_tree = None

            kwargs = build_sac_tree_from_bus_df(
                self.grid.summarize_buses(),
                bus_name_col="name",
                elements_col="elements",
                net=self.grid.net,
                show_connectors=show_connectors,
            )

            def update_tree():
                st.session_state.original_tree = None

            selected = sac.tree(on_change=update_tree, key="original_tree", **kwargs)

            if "tree_selected_bus" not in st.session_state:
                st.session_state["tree_selected_bus"] = selected

            if selected and st.session_state["tree_selected_bus"] != selected:
                st.session_state["tree_selected_bus"] = selected
                match = re.match(r"\[(\d+)\]", selected)
                if match:
                    bus_id = int(match.group(1))
                    bus = self.grid.net.bus.loc[bus_id].to_dict()
                    try:
                        self.change_element(
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
                        self.logger.error(
                            f"[GridManagerPage] Error in changing bus: {e}"
                        )
                        st.toast(f"❌ Error in changing bus: \n {e}", icon="❌")

    def manager_connections(self):
        """
        Render all bus-to-bus connections with voltage legends and open edit on click.

        Returns:
            None
        ------
        Note:
            - Uses colors per VN_kV class (LV/MV/HV/EHV).
            - Clicking a connection button opens the edit dialog for that line.
        """
        open_dialog = None
        values_constraints = {
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
        sac.divider(variant="dotted")

        def get_color(bus_idx):
            """
            Map a bus index to the LV/MV/HV/EHV color based on vn_kv.
            """
            try:
                v = self.grid.net.bus["vn_kv"].iloc[bus_idx]
            except Exception as e:
                st.error(f"❌ Error in uploading connections: {e}")
                return "#6E6E6E"
            for k, (lo, hi) in values_constraints.items():
                if lo < v < hi:
                    return colors[k]
            return "#6E6E6E"

        for row in self.grid.bus_connections().itertuples(index=False):
            cols = st.columns([2, 1.3, 2])
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

            if cols[1].button(
                row.name,
                type="tertiary",
                key=f"connection_{row.type}_{row.name}_{row.id}",
                use_container_width=True,
            ):
                connector = self.grid.net[row.type].loc[row.id].to_dict()
                open_dialog = connector

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

        if open_dialog:
            try:
                self.change_element(
                    params=LineParams(**open_dialog), line_id=None, type="line"
                )
            except StreamlitAPIException as e:
                self.logger.error(
                    f"[GridManagerPage] Streamlit error in connection change dialog: {e}"
                )
                st.toast(f" ❌ Error in streamlit for connection dialog: {e}")

    # ---------- Unified edit dialog via singledispatch ----------
    @singledispatchmethod
    def _edit_core(self, params, **ctx):
        """
        Dispatch editing UI based on parameter type.

        Args:
            params (Any): Element params (typed dict/dataclass) to be edited.
            **ctx: Contextual info (e.g., bus_id, line_id, connected_elements).

        Returns:
            None
        ------
        Note:
            Concrete implementations are registered for BusParams and LineParams.
        """
        raise NotImplementedError("Unsupported element type for editing")

    @_edit_core.register
    def _(self, params: "BusParams", **ctx):
        """
        Bus editor implementation for `_edit_core`.
        """
        _, new_bus = self.bus_params(
            id=f"manager_{ctx.get('bus_id', 'unknown')}",
            quantity=False,
            bus=params,
            borders=False,
        )

        # Connected elements table (if provided)
        connected = ctx.get("connected_elements") or []
        rows = []
        for el in connected:
            etype, eid, name_hint = self._normalize_element_spec(el)
            rows.append({"type": etype, "element ID": eid, "name": name_hint})
        if rows and any("element ID" in r for r in rows):
            df_elements = pd.DataFrame(rows).set_index("element ID")
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
            if ctx.get("bus_id") is None:
                raise ValueError("Missing 'bus_id' for bus update.")
            with self.grid_change():
                self.grid.update_bus(ctx["bus_id"], new_bus)
            st.toast(f"Bus {ctx['bus_id']} updated successfully.", icon="✅")
            st.rerun(scope="fragment")

    @_edit_core.register
    def _(self, params: "LineParams", **ctx):
        """
        Line editor implementation for `_edit_core`.
        """
        ok, new_line = self.line_params(line=params, horizontal=False)
        if st.button("Save changes", key="save_line") and ok:
            with self.grid_change():
                # Adapt to your model API; here we call by params only
                self.grid.update_line(new_line)
            st.toast("Line updated successfully.", icon="✅")
            st.rerun(scope="fragment")

    @st.dialog("Edit grid element", width="large")
    def change_element(
        self,
        params: Union["BusParams", "LineParams"],
        *,
        bus_id: Optional[int] = None,
        line_id: Optional[int] = None,
        connected_elements=None,
        type: Optional[Literal["bus", "line"]] = None,
    ) -> bool:
        """
        Open the edit dialog for a grid element and dispatch to the proper editor.

        Args:
            params (Union[BusParams, LineParams]): Parameters to edit.
            bus_id (Optional[int]): Bus index when editing buses.
            line_id (Optional[int]): Line index when editing lines (if needed).
            connected_elements: Optional list of elements connected to the bus.
            type (Optional[Literal['bus','line']]): Unused; kept for backward compatibility.

        Returns:
            bool: Always True; the dialog handles saving and reruns the fragment.
        """
        self._edit_core(
            params,
            bus_id=bus_id,
            line_id=line_id,
            connected_elements=connected_elements,
        )
        return True

    # -------------> Adders (generic) <-------------
    def add_bus(self) -> bool:
        """
        Create one or more buses using the generic creation flow.

        Returns:
            bool: True if at least one bus was created.
        """
        return self.add_any("bus")

    def add_line(self) -> bool:
        """
        Create one or more lines using the generic creation flow.

        Returns:
            bool: True if at least one line was created.
        """
        return self.add_any("line")

    def add_transformer(self) -> bool:
        """
        Placeholder for transformer creation UI.

        Returns:
            bool: Always False (not implemented).
        """
        sac.result("Transformer creation coming soon.", status="warning")
        return False

    # ------------- Builders (generic) --------
    def build_items_for(
        self, kind: str, *, state_key: str, n_cols: int = 1
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Build a grid of parameter editors for a given element kind.

        Args:
            kind (str): Element kind registered in `self.element_specs` (e.g., "bus").
            state_key (str): Key for session state to persist the editors list.
            n_cols (int): Number of columns per row in the editor grid.

        Returns:
            Tuple[bool, List[Dict[str, Any]]]: (all_valid, payloads)
        ------
        Note:
            - Internally calls `_build_items(...)` with the spec's `build_params_ui`.
            - Returns only the `payload` objects for which `is_valid` is True.
        """
        spec = self.element_specs[kind]
        all_valid, items = self._build_items(
            state_key=state_key,
            n_cols=n_cols,
            render_param_fn=lambda i: spec.build_params_ui(id=f"{kind}_{i}"),
            add_label=self.T("tabs.links.item.bus.buttons")[0],
            remove_label=self.T("tabs.links.item.bus.buttons")[1],
            borders=True,
        )
        payloads = [pl for ok, pl in items if ok]
        return all_valid, payloads

    def add_any(self, kind: str) -> bool:
        """
        Generic creation handler for any registered element kind.

        Args:
            kind (str): Element kind id (e.g., "bus", "line").

        Returns:
            bool: True if at least one element was created.
        ------
        Note:
            - Binds the "Create" button to the spec's `create_in_grid` action.
        """
        spec = self.element_specs[kind]
        ok, payloads = self.build_items_for(kind, state_key=f"gm_new_{kind}")
        if st.button(self.T("tabs.links.item.link.buttons")[2]) and ok:
            for p in payloads:
                with self.grid_change():
                    spec.create_in_grid(self.grid, p)
            st.toast(f"{spec.label} created successfully.", icon="✅")
            return True
        return False

    def build_buses(self, borders: bool = True) -> List[Tuple[int, "BusParams"]]:
        """
        Backward-compatible wrapper that returns a list of (quantity, BusParams).

        Args:
            borders (bool): Ignored; preserved for compatibility with previous code.

        Returns:
            List[Tuple[int, BusParams]]: Items built via the generic mechanism.
        ------
        Note:
            - Internally uses `build_items_for("bus")` and unwraps quantity+params.
        """
        _, items = self._build_items(
            state_key="gm_new_bus",
            n_cols=3,
            render_param_fn=lambda i: self._wrap_bus_params(id=i),
            add_label=self.T("tabs.links.item.bus.buttons")[0],
            remove_label=self.T("tabs.links.item.bus.buttons")[1],
            borders=borders,
        )
        # Convert generic payload {"quantity": q, "params": bus} -> (q, bus)
        return [(pl["quantity"], pl["params"]) for ok, pl in items if ok]

    def build_line(self, borders: bool = True) -> Tuple[bool, List["LineParams"]]:
        """
        Backward-compatible wrapper that returns (all_valid, [LineParams,...]).

        Args:
            borders (bool): Whether to render borders around editors.

        Returns:
            Tuple[bool, List[LineParams]]: (all_valid, list_of_params)
        ------
        Note:
            - Internally uses the line spec and unwraps only `params`.
        """
        all_valid, items = self._build_items(
            state_key="gm_new_line",
            n_cols=1,  # line editors are wide; keep one per row
            render_param_fn=lambda i: self._wrap_line_params(id=i),
            add_label=self.T("tabs.links.item.link.buttons")[0],
            remove_label=self.T("tabs.links.item.link.buttons")[1],
            borders=borders,
        )
        lines_to_add: List["LineParams"] = [pl["params"] for ok, pl in items if ok]
        return all_valid, lines_to_add

    # ============ INTERNAL UTILITIES ===========

    @staticmethod
    @contextmanager
    def grid_change(flag_key: str = "modified"):
        """
        Context manager to mark the grid as modified after a block succeeds.

        Args:
            flag_key (str): Session state key to toggle. Defaults to "modified".

        Yields:
            None
        ------
        Note:
            Use `with grid_change(): <mutations>` to ensure the UI updates.
        """
        try:
            yield
        finally:
            st.session_state[flag_key] = True

    def _build_items(
        self,
        *,
        state_key: str,
        n_cols: int,
        render_param_fn: Callable[[int], Tuple[bool, Dict[str, Any]]],
        add_label: str,
        remove_label: str,
        borders: bool = True,
    ) -> Tuple[bool, List[Tuple[bool, Dict[str, Any]]]]:
        """
        Build a responsive grid of parameter editors with add/remove controls.

        Args:
            state_key (str): Session key to store the list of editor "slots".
            n_cols (int): Number of columns per row.
            render_param_fn (Callable[[int], Tuple[bool, Dict[str, Any]]]):
                Function that renders one editor and returns (is_valid, payload).
            add_label (str): Label for the "add" button.
            remove_label (str): Label for the "remove" button.
            borders (bool): Wrap each editor in a bordered container.

        Returns:
            Tuple[bool, List[Tuple[bool, Dict[str, Any]]]]:
                (all_valid, list_of_(is_valid, payload))
        ------
        Note:
            - Maintains a list of integer indices in `st.session_state[state_key]`.
            - On add/remove, re-renders consistently and preserves widget state.
        """
        st.session_state.setdefault(state_key, [0])
        slots: List[int] = st.session_state[state_key]

        ctrl_cols = st.columns(2)
        with ctrl_cols[0]:
            if st.button(add_label, key=f"{state_key}_add"):
                next_id = (max(slots) + 1) if slots else 0
                slots.append(next_id)
        with ctrl_cols[1]:
            if st.button(remove_label, key=f"{state_key}_remove") and slots:
                slots.pop()

        # Render in rows of n_cols
        results: List[Tuple[bool, Dict[str, Any]]] = []
        row: List[int] = []
        for i, slot_id in enumerate(slots):
            row.append(slot_id)
            if len(row) == n_cols or i == len(slots) - 1:
                cols = st.columns(len(row))
                for c, sid in zip(cols, row):
                    with c:
                        ok, payload = render_param_fn(sid)
                        results.append((ok, payload))
                row = []

        all_valid = all(ok for ok, _ in results) if results else False
        return all_valid, results

    @staticmethod
    def _normalize_element_spec(el: Any) -> Tuple[str, Optional[int], Optional[str]]:
        """
        Normalize heterogeneous element specs into (type, id, name).

        Args:
            el (Any): Element spec in one of the allowed formats:
                - tuple: ('line', 5)
                - dict:  {'type': 'line', 'index': 5, 'name': 'L5'}
                - dict:  {'table': 'line', 'idx': 5}
                - str:   'line:5' or 'line'

        Returns:
            Tuple[str, Optional[int], Optional[str]]:
                (etype, eid, name_hint)
        ------
        Note:
            Unknown formats fall back to ('unknown', None, str(el)).
        """
        if isinstance(el, tuple) and len(el) >= 2:
            return str(el[0]), int(el[1]), None
        if isinstance(el, dict):
            et = el.get("type") or el.get("table") or "unknown"
            ei = el.get("index") or el.get("idx")
            nm = el.get("name")
            return str(et), (int(ei) if ei is not None else None), nm
        if isinstance(el, str):
            if ":" in el:
                et, sid = el.split(":", 1)
                try:
                    return et, int(sid), None
                except ValueError:
                    return et, None, el
            return el, None, None
        return "unknown", None, str(el)

    # ---------- DI adapters (wrap existing editors) ----------
    def _wrap_bus_params(
        self, *, id: Union[int, str], defaults=None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Adapter that wraps `bus_params(...)` into the generic (ok, payload) shape.

        Args:
            id (Union[int, str]): Unique UI id suffix for widget keys.
            defaults (Any): Default bus parameters (BusParams).

        Returns:
            Tuple[bool, Dict[str, Any]]: (True, {"quantity": q, "params": bus})
        """
        qty, params = self.bus_params(id=id, bus=defaults, quantity=True, borders=True)
        return True, {"quantity": int(qty), "params": params}

    def _wrap_line_params(
        self, *, id: Union[int, str], defaults=None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Adapter that wraps `line_params(...)` into the generic (ok, payload) shape.

        Args:
            id (Union[int, str]): Unique UI id suffix for widget keys.
            defaults (Any): Default line parameters (LineParams).

        Returns:
            Tuple[bool, Dict[str, Any]]: (ok, {"params": line_params})
        """
        ok, params = self.line_params(
            id=id, line=defaults, horizontal=True, borders=True
        )
        return ok, {"params": params}

    # ---------- Model actions used by DI specs ----------
    def _create_bus(self, grid, payload: Dict[str, Any]) -> None:
        """
        Create N buses in the grid model.

        Args:
            grid (PlantPowerGrid): Grid model.
            payload (Dict[str, Any]): {"quantity": int, "params": BusParams}

        Returns:
            None
        """
        for _ in range(payload["quantity"]):
            grid.create_bus(payload["params"])

    def _update_bus(self, grid, payload: Dict[str, Any]) -> None:
        """
        Update a bus in the grid model.

        Args:
            grid (PlantPowerGrid): Grid model.
            payload (Dict[str, Any]): {"id": int, "params": BusParams}

        Returns:
            None
        """
        bus_id = payload.get("id")
        if bus_id is None:
            raise ValueError("Missing 'id' in payload for bus update.")
        grid.update_bus(bus_id, payload["params"])

    def _create_line(self, grid, payload: Dict[str, Any]) -> None:
        """
        Create a line in the grid model.

        Args:
            grid (PlantPowerGrid): Grid model.
            payload (Dict[str, Any]): {"params": LineParams}

        Returns:
            None
        """
        grid.link_buses(payload["params"])

    def _update_line(self, grid, payload: Dict[str, Any]) -> None:
        """
        Update a line in the grid model.

        Args:
            grid (PlantPowerGrid): Grid model.
            payload (Dict[str, Any]): {"params": LineParams} (+ optional "id")

        Returns:
            None
        ------
        Note:
            Adapt to your specific API if an explicit line id is required.
        """
        grid.update_line(payload["params"])
