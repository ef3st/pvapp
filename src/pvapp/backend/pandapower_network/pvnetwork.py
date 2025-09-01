import json
from typing import Union, Optional, Tuple, Literal, TypedDict, List, Dict

import pandas as pd
import numpy as np
import pandapower as pp
from pandapower import toolbox as tb  # noqa: F401  # kept if you used it elsewhere
from pandapower.timeseries import run_timeseries, DFData
from pandapower.control import ConstControl
from tools.logger import get_logger, log_performance
from .TypedDict_elements_params import *


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

    # ======================== Lifecycle ========================
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

    # ======================== CRUD: Buses & Links ========================

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

    # =======================- CRUD: Generators & Others ========================

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

    # =========================Lookups & Accessors ========================

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

    # ======================== Counts / Small summaries ========================

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

    # ======================== Simulation / Plot ========================
    def runnet(
        self,
        timeseries: Union[pd.DataFrame, None] = None,
        selectors: Optional[List[str]] = None,
        return_df: bool = False,
    ) -> Union[List[str], Tuple[List[str], Optional[pd.DataFrame]]]:
        """
        Run a steady-state (pp.runpp) or time-series (pp.run_timeseries) power flow and
        optionally return results as a pandas DataFrame.

        Execution modes
        --------------
        1) Steady-state:
           If `timeseries` is None, a single power flow is executed (pp.runpp).
        2) Time-series:
           If `timeseries` is a DataFrame with tupled columns of the form
           ("sgen", "p_mw" | "q_mvar", <element_index>), ConstControls are created
           on-the-fly and a time-series simulation is executed (pp.run_timeseries).

        When `return_df=True`
        ---------------------
        • Steady-state: returns a single-row DataFrame with tupled columns
          (res_table, column, element_index).
        • Time-series: results are captured via an OutputWriter configured from
          `selectors`, and consolidated into one wide DataFrame with tupled columns
          (res_table, column, element_index) indexed by the original `timeseries.index`.

        Parameters
        ----------
        timeseries : pandas.DataFrame or None, default None
            Input profiles for time-series simulation. Expected to be the output of a
            function like `build_pp_dfdata_from_pvlib`, i.e. a wide DataFrame with
            tupled columns ("sgen", "p_mw" | "q_mvar", idx). If None, run a single
            steady-state power flow instead.
        selectors : list[str] or None, default None
            Result variables to collect, each in the form "res_table.column".
            Examples: ["res_bus.vm_pu", "res_line.loading_percent", "res_sgen.p_mw"].
            If None, a reasonable default set is used.
        return_df : bool, default False
            If True, also return a DataFrame of results as described above.

        Returns
        -------
        errors : list[str]
            A list of error messages emitted during checks or execution. Empty if no errors.
        results_df : pandas.DataFrame or None
            Only returned if `return_df=True`. In time-series mode, indexed by
            `timeseries.index`; in steady-state mode, a single row indexed by [0].

        Notes
        -----
        • `pandapower.timeseries.run_timeseries` does not return DataFrames directly.
          Results are logged during the simulation via `OutputWriter`. This method
          uses a dedicated utility to configure the OutputWriter from `selectors` and
          consolidate logs into a single wide DataFrame.
        • The method assumes that `self.net` is a valid pandapower network and
          `self.check_prerequisites()` verifies the minimal conditions to run a power flow.
        """
        import time
        from pandapower import runpp
        from pandapower.timeseries import run_timeseries
        from pandapower.timeseries.data_sources.frame_data import DFData
        from pandapower.control import ConstControl

        t0 = time.perf_counter()
        self.logger.debug(
            "[runnet] Enter | return_df=%s | timeseries_is_df=%s",
            return_df,
            isinstance(timeseries, pd.DataFrame),
        )

        # ---------- helpers ----------
        def _default_selectors() -> List[str]:
            """Return a reasonable default set of result variables."""
            return [
                "res_bus.vm_pu",
                "res_bus.va_degree",
                "res_line.loading_percent",
                "res_line.pl_mw",
                "res_trafo.loading_percent",
                "res_sgen.p_mw",
                "res_sgen.q_mvar",
                "res_load.p_mw",
                "res_load.q_mvar",
                "res_ext_grid.p_mw",
                "res_ext_grid.q_mvar",
            ]

        @log_performance("[PlantPowerGrid.runnet]_collect_with_outputwriter()")
        def _collect_with_outputwriter(
            selects: List[str], index: pd.Index
        ) -> pd.DataFrame:
            """
            Configure an OutputWriter from the provided selectors, run the time-series
            using label-based time_steps (the given `index`), and consolidate all logs
            into a single wide DataFrame.

            This function is robust to non-data keys in `ow.output` (e.g., "Parameters").
            Only variables explicitly requested via `selectors` are processed.

            Parameters
            ----------
            selects : list[str]
                Variables to log, each "res_table.column".
            index : pandas.Index
                Exact time_steps to simulate; must match DFData index labels (e.g., DateTimeIndex).

            Returns
            -------
            pandas.DataFrame
                Wide DataFrame with tupled columns (res_table, column, element_index)
                and `index` as the row index.
            """
            from pandapower.timeseries.output_writer import OutputWriter
            from pandapower.timeseries import run_timeseries

            # Ensure unique labels for label-based selection
            if not index.is_unique:
                raise ValueError(
                    "Timeseries index must be unique for run_timeseries / DFData."
                )

            # Parse selectors -> normalized tuples (table, column)
            parsed: List[Tuple[str, str]] = []
            for sel in selects:
                try:
                    tbl, col = sel.split(".", 1)
                    parsed.append((tbl.strip(), col.strip()))
                except ValueError:
                    self.logger.warning(
                        "[runnet] Malformed selector '%s' (expected 'res_table.column') -> skip",
                        sel,
                    )

            # Build accepted key sets to filter OutputWriter output deterministically
            accepted_str_keys = {f"{t}.{c}" for t, c in parsed}
            accepted_tup_keys = set(parsed)

            # In-memory OutputWriter (no files on disk)
            ow = OutputWriter(self.net, output_path=None, output_file_type=".json")

            # Register only the requested variables
            for t, c in parsed:
                ow.log_variable(t, c)

            # Use *label-based* time steps so DFData.loc[...] resolves correctly
            run_timeseries(self.net, time_steps=list(index))

            # Consolidate OutputWriter logs into a single wide DataFrame
            frames: List[pd.Series] = []
            for key, df in ow.output.items():
                # Key can be ('res_table','column') or "res_table.column" or metadata (e.g., "Parameters")
                if isinstance(key, tuple) and key in accepted_tup_keys:
                    tbl, col = key
                elif isinstance(key, str) and key in accepted_str_keys:
                    tbl, col = key.split(".", 1)
                else:
                    # Skip non-data / metadata keys quietly (debug-level to avoid noise)
                    self.logger.debug(
                        "[runnet] Skipping non-data OutputWriter key: %r", key
                    )
                    continue

                # Each df column is an element index in the result table
                for el_idx in df.columns:
                    series = df[el_idx].rename((str(tbl), str(col), el_idx))
                    frames.append(series)

            out = pd.concat(frames, axis=1) if frames else pd.DataFrame(index=index)
            try:
                out = out.reindex(
                    sorted(out.columns, key=lambda t: (t[0], t[1], t[2])), axis=1
                )
            except Exception:
                # Keep current order if tuple sorting fails
                pass
            return out

        # ---------- pre-checks ----------
        errors: List[str] = self.check_prerequisites()
        if errors:
            self.logger.error("[runnet] Prerequisite errors: %s", errors)
            return (errors, None) if return_df else errors

        selectors = selectors or _default_selectors()
        self.logger.debug("[runnet] Selectors: %s", selectors)

        results_df: Optional[pd.DataFrame] = None

        try:
            if isinstance(timeseries, pd.DataFrame):
                # ---- Time-series mode ----
                self.logger.debug(
                    "[runnet] Timeseries mode | steps=%d | columns=%d",
                    len(timeseries),
                    timeseries.shape[1],
                )

                # Build DFData and bind ConstControls for sgens (p and q, if present)
                data_source = DFData(timeseries)

                p_cols = [
                    c
                    for c in timeseries.columns
                    if isinstance(c, tuple)
                    and len(c) == 3
                    and c[0] == "sgen"
                    and c[1] == "p_mw"
                ]
                q_cols = [
                    c
                    for c in timeseries.columns
                    if isinstance(c, tuple)
                    and len(c) == 3
                    and c[0] == "sgen"
                    and c[1] == "q_mvar"
                ]

                if not p_cols:
                    msg = (
                        "No ('sgen','p_mw', idx) columns found in timeseries DataFrame."
                    )
                    self.logger.error("[runnet] %s", msg)
                    raise ValueError(msg)

                # Align element indices with the network's existing sgens
                sgen_idxs_p = [c[2] for c in p_cols if c[2] in self.net.sgen.index]
                if sgen_idxs_p:
                    ConstControl(
                        self.net,
                        element="sgen",
                        element_index=sgen_idxs_p,
                        variable="p_mw",
                        data_source=data_source,
                        profile_name=p_cols,
                    )

                if q_cols:
                    sgen_idxs_q = [c[2] for c in q_cols if c[2] in self.net.sgen.index]
                    if sgen_idxs_q:
                        ConstControl(
                            self.net,
                            element="sgen",
                            element_index=sgen_idxs_q,
                            variable="q_mvar",
                            data_source=data_source,
                            profile_name=q_cols,
                        )

                if return_df:
                    # Capture results via OutputWriter using label-based time steps
                    results_df = _collect_with_outputwriter(selectors, timeseries.index)
                    self.logger.debug(
                        "[runnet] Collected time-series results_df | shape=%s",
                        getattr(results_df, "shape", None),
                    )
                else:
                    # Fast path: run TS without building a DataFrame (still label-based)
                    self.logger.debug(
                        "[runnet] Running pandapower.run_timeseries(...) (no DF capture)"
                    )
                    run_timeseries(self.net, time_steps=list(timeseries.index))

            else:
                # ---- Steady-state mode ----
                self.logger.debug("[runnet] Steady-state mode (single runpp)")
                runpp(self.net)

                if return_df:
                    # Flatten selected res_* tables into a single row
                    row: Dict[Tuple[str, str, Union[int, str]], float] = {}
                    for sel in selectors:
                        try:
                            tbl, col = sel.split(".", 1)
                        except ValueError:
                            self.logger.warning(
                                "[runnet] Malformed selector '%s' -> skip", sel
                            )
                            continue
                        df_res = getattr(self.net, tbl, None)
                        if df_res is None or df_res.empty or col not in df_res.columns:
                            continue
                        for idx, val in df_res[col].items():
                            # Normalize index to int if possible, otherwise keep label
                            try:
                                key_idx: Union[int, str] = int(idx)
                            except Exception:
                                key_idx = idx
                            row[(tbl, col, key_idx)] = (
                                float(val) if pd.notna(val) else float("nan")
                            )
                    results_df = pd.DataFrame([row], index=[0])
                    try:
                        results_df = results_df.reindex(
                            sorted(
                                results_df.columns, key=lambda t: (t[0], t[1], t[2])
                            ),
                            axis=1,
                        )
                    except Exception:
                        pass
                    self.logger.debug(
                        "[runnet] Collected steady-state results | shape=%s",
                        results_df.shape,
                    )

        except Exception as e:
            # Provide a clean API: aggregate errors and keep returning (errors, df)
            self.logger.exception("[runnet] Error during power flow: %s", e)
            errors.append(str(e))
        finally:
            t1 = time.perf_counter()
            self.logger.debug(
                "[runnet] Exit | elapsed=%.3fs | return_df=%s | errors=%d",
                (t1 - t0),
                return_df,
                len(errors),
            )

        return (errors, results_df) if return_df else errors

    def show_grid(self):
        """
        (Placeholder) Build a plotly figure and return (fig, errors).

        Note:
            Current implementation returns (None, errors) unless you enable the plotting code.
        """
        from pandapower.plotting.plotly import simple_plotly
        from pandapower.plotting.generic_geodata import create_generic_coordinates

        errors = self.runnet()
        fig = None
        if not errors:
            create_generic_coordinates(self.net, overwrite=True)
            fig = simple_plotly(self.net, respect_switches=True, auto_open=False)
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

    # ======================== Controllers / Profiles =========================

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

    # ======================== Validation / Readiness ========================

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

    # ======================== Summaries / Projections ========================

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
