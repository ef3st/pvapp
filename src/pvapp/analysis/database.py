import pandas as pd
from pvlib.modelchain import ModelChainResult
from IPython.display import display
from tools.logger import get_logger
from typing import Dict, Iterable, Tuple, Optional
import pandas as pd
import numpy as np


PANDA_POWER_COLS = [
    # Buses
    "res_bus.vm_pu",  # voltage magnitude in p.u.
    "res_bus.va_degree",  # voltage angle in degree
    "res_bus.p_mw",  # active power at bus in MW
    "res_bus.q_mvar",  # reactive power at bus in MVAr
    # Lines
    "res_line.p_from_mw",  # active power from bus side in MW
    "res_line.q_from_mvar",  # reactive power from bus side in MVAr
    "res_line.p_to_mw",  # active power to bus side in MW
    "res_line.q_to_mvar",  # reactive power to bus side in MVAr
    "res_line.pl_mw",  # line losses in MW
    "res_line.ql_mvar",  # line reactive losses in MVAr
    "res_line.i_from_ka",  # current magnitude from bus in kA
    "res_line.i_to_ka",  # current magnitude to bus in kA
    "res_line.loading_percent",  # line loading in %
    # Transformers (2-winding)
    "res_trafo.p_hv_mw",  # active power at HV side
    "res_trafo.q_hv_mvar",  # reactive power at HV side
    "res_trafo.p_lv_mw",  # active power at LV side
    "res_trafo.q_lv_mvar",  # reactive power at LV side
    "res_trafo.pl_mw",  # transformer losses (active)
    "res_trafo.ql_mvar",  # transformer losses (reactive)
    "res_trafo.loading_percent",  # transformer loading
    # Transformers (3-winding, se presenti)
    "res_trafo3w.p_hv_mw",
    "res_trafo3w.q_hv_mvar",
    "res_trafo3w.p_mv_mw",
    "res_trafo3w.q_mv_mvar",
    "res_trafo3w.p_lv_mw",
    "res_trafo3w.q_lv_mvar",
    "res_trafo3w.pl_mw",
    "res_trafo3w.ql_mvar",
    "res_trafo3w.loading_percent",
    # Loads
    "res_load.p_mw",  # active power per load
    "res_load.q_mvar",  # reactive power per load
    # Static Generators
    "res_sgen.p_mw",  # active power of sgen
    "res_sgen.q_mvar",  # reactive power of sgen
    # Generators
    "res_gen.p_mw",  # active power of generator
    "res_gen.q_mvar",  # reactive power of generator
    "res_gen.vm_pu",  # voltage magnitude setpoint
    "res_gen.va_degree",  # voltage angle at bus
    # External Grid
    "res_ext_grid.p_mw",  # active power from/to external grid
    "res_ext_grid.q_mvar",  # reactive power from/to external grid
    "res_ext_grid.vm_pu",  # voltage magnitude at slack
    "res_ext_grid.va_degree",  # voltage angle at slack
    # Switches (risultati correnti/flussi se richiesti)
    "res_switch.current_ka",
    # Impedances
    "res_impedance.p_from_mw",
    "res_impedance.q_from_mvar",
    "res_impedance.p_to_mw",
    "res_impedance.q_to_mvar",
    # Shunt Elements
    "res_shunt.p_mw",
    "res_shunt.q_mvar",
]


class SimulationResults:
    def __init__(self):
        # self.database: pd.DataFrame = pd.DataFrame()
        self.logger = get_logger("pvapp")
        self.pvarrays: Dict[int, pd.DataFrame] = {}
        self.grid: Optional[pd.DataFrame] = None

    def add_modelchainresult(
        self,
        pvSystemId: int = None,
        # plant_name: str,
        results: Optional[ModelChainResult] = None,
        period: Optional[str] = None,
        # mount: str,
    ) -> None:
        ...
        if results is None:
            self.logger.warning("[SimulationResults] No modelchain to add")
            return
        if pvSystemId is None:
            self.logger.error("[SimulationResults] No pvSystemId provided")
            raise ValueError
        new_results = self.gather_modelchain_results(results)
        new_results["sgen_id"] = pvSystemId
        # new_results["Plant_name"] = plant_name
        new_results["period"] = period
        # new_results["mount"] = mount
        new_results.index.name = "timestamp"
        new_results = new_results.reset_index()
        self.pvarrays[pvSystemId] = new_results

    def gather_modelchain_results(self, results: ModelChainResult):
        """
        Collect key ModelChain results into a single DataFrame.
        """
        dfs = []
        for attr_name, value in vars(results).items():
            if isinstance(value, pd.DataFrame):
                # self.logger.debug(f"{attr_name} added")
                # self.logger.debug(f"A Dataframe {type(value)}: {attr_name}")
                df = value.copy()
                if attr_name == "ac":
                    df = df.add_prefix("ac_")
                if attr_name == "dc":
                    df = df.add_prefix("dc_")

                dfs.append(df)
            elif isinstance(value, pd.Series):
                # self.logger.debug(f"  B  SERIES {type(value)}: {attr_name}")
                dfs.append(value.to_frame(name=attr_name))
            # else:
            #     self.logger.debug(f"      C SINGLE {type(value)}: {attr_name} =  {value}")
        return pd.concat(dfs, axis=1)

    def show(self):
        display(self.database)

    def save(self, path):
        self.database.to_csv(f"{path}/simulation.csv")

    @property
    def max_ac_power(self) -> pd.Series:
        return self.database["ac_p_mp"]

    @property
    def is_empty(self) -> bool:
        return self.database.empty

    def get_acPowers_perTime_perArray(self) -> pd.DataFrame:
        """
        Returns a DataFrame with the AC power values.
        """
        if self.is_empty:
            self.logger.warning("[SimulationResults] No results to get powers from.")
            return pd.DataFrame()
        return self.database.pivot(
            index="timestamp", columns="sgen_id", values="ac_p_mp"
        )

    @property
    def database(self) -> pd.DataFrame:
        """
        Combine `self.grid` and all per-array DataFrames in `self.pvarrays`
        into a single wide DataFrame indexed by time.

        - Grid columns are prefixed with "grid_".
        - Each array's columns are prefixed with its key (e.g., "5_").
        - Outer-join on the time index to keep all timestamps.
        """

        def _to_time_index(df: pd.DataFrame) -> pd.DataFrame:
            if df is None or df.empty:
                return pd.DataFrame()
            # Prefer explicit 'timestamp' column, else keep existing index if it's datetime-like
            if "timestamp" in df.columns:
                out = df.copy()
                out = out.set_index(pd.to_datetime(out["timestamp"], utc=False)).drop(
                    columns=["timestamp"]
                )
                out.index.name = "timestamp"
                return out
            # If index is already a DatetimeIndex, standardize its name
            if isinstance(df.index, pd.DatetimeIndex):
                out = df.copy()
                out.index.name = "timestamp"
                return out
            # Last resort: try to coerce the index to datetime (if possible)
            try:
                idx = pd.to_datetime(df.index)
                out = df.copy()
                out.index = idx
                out.index.name = "timestamp"
                return out
            except Exception:
                # No usable time information
                return pd.DataFrame()

        pieces = []

        # 1) Grid (prefix 'grid_')
        grid_df = _to_time_index(self.grid)
        if not grid_df.empty:
            # grid_df = grid_df.add_prefix("grid_")
            pieces.append(grid_df)

        # 2) PV arrays (prefix with the dict key, e.g., '3_')
        for key, df in self.pvarrays.items():
            arr = _to_time_index(df)
            if arr.empty:
                continue
            # Drop any 'sgen_id' column (it's implied by the key) before prefixing
            if "sgen_id" in arr.columns:
                arr = arr.drop(columns=["sgen_id"])
            # Prefix with the key and underscore
            arr = arr.add_prefix(f"{key}_")
            pieces.append(arr)

        if not pieces:
            return pd.DataFrame()

        # Outer-join on timestamp, stable column order
        out = pd.concat(pieces, axis=1, join="outer").sort_index()
        # Optional: ensure columns are unique strings
        out.columns = [str(c) for c in out.columns]
        return out

    def get_df_for_pandapower(
        self,
        net,
        *,
        p_col_candidates: Tuple[str, ...] = (
            "p_mw",
            "ac_p_mw",
            "ac_p_kw",
            "ac_p_mp",
            "p_ac",
            "ac",
        ),
        q_col_candidates: Tuple[str, ...] = ("q_mvar", "q_ac"),
        pf_col_candidates: Tuple[str, ...] = ("pf", "power_factor"),
        default_q_mvar: float = 0.0,
        assume_ac_from_dc: Optional[float] = None,
        fill_value: float = 0.0,
    ) -> pd.DataFrame:
        """
        Build a time-indexed DataFrame suitable for pandapower time series (DFData).

        This function converts PVlib per-inverter results (stored in `self.pvarrays`)
        into a wide-format DataFrame with multi-key columns that match pandapower's
        expected format: `(element_type, variable, element_index)`.

        Workflow
        --------
        1. Ensure that all DataFrames have a proper `DatetimeIndex`:
           - If a "timestamp" column exists, it is used as index.
           - Otherwise, the index is converted to datetime.
           - All DataFrames are aligned to a common reference index.
        2. Extract active power (`p_mw`):
           - Priority order is given by `p_col_candidates`.
           - If only DC columns are available (`dc_p_mp`, `p_dc`), AC is computed
             using `assume_ac_from_dc` (conversion efficiency).
           - Watt values (e.g., `ac_p_mp`) are automatically converted to MW.
        3. Extract reactive power (`q_mvar`):
           - Taken from `q_col_candidates` if available.
           - If missing, computed from `pf_col_candidates` (power factor).
           - If still missing, tries `net.sgen["cos_phi"]`.
           - If none available, falls back to `default_q_mvar`.
        4. Any NaN values are filled with `fill_value`.

        Parameters
        ----------
        net : pandapowerNet
            The pandapower network (used to read cos_phi from `net.sgen`).
        p_col_candidates : tuple of str, optional
            Ordered list of candidate column names for active power.
        q_col_candidates : tuple of str, optional
            Ordered list of candidate column names for reactive power.
        pf_col_candidates : tuple of str, optional
            Ordered list of candidate column names for power factor.
        default_q_mvar : float, optional
            Default value for reactive power if not computable.
        assume_ac_from_dc : float or None, optional
            Conversion efficiency if only DC power is available.
        fill_value : float, optional
            Value used to replace NaN or missing data.

        Returns
        -------
        pandas.DataFrame
            A wide-format DataFrame indexed by time with tupled columns:
            - ("sgen", "p_mw", <sgen_idx>)
            - ("sgen", "q_mvar", <sgen_idx>)

        Raises
        ------
        ValueError
            If no valid power columns are found and conversion is not possible.

        Notes
        -----
        - All power values are converted to MW before being inserted.
        - Sign convention of reactive power is not enforced. Ensure consistency
          in input data and power factors before calling this method.

        Examples
        --------
        >>> df_pp = sim_results.get_df_for_pandapower(net, assume_ac_from_dc=0.97)
        >>> from pandapower.timeseries import DFData
        >>> data_source = DFData(df_pp)
        >>> profile = ("sgen", "p_mw", 0)
        >>> data_source.df[profile].head()
        """

        if not self.pvarrays:
            return pd.DataFrame()

        # --- Helper: ensure DataFrame has a proper DatetimeIndex ---
        def _ensure_time_index(df: pd.DataFrame) -> pd.DataFrame:
            if df is None or df.empty:
                return pd.DataFrame()
            out = df.copy()
            if "timestamp" in out.columns:
                # Use 'timestamp' column if present
                out["timestamp"] = pd.to_datetime(out["timestamp"], utc=False)
                out = out.set_index("timestamp")
            elif not isinstance(out.index, pd.DatetimeIndex):
                # Try to convert existing index to datetime
                try:
                    out.index = pd.to_datetime(out.index, utc=False)
                except Exception:
                    return pd.DataFrame()
            out.index.name = "timestamp"
            return out

        # --- Get reference time index from the first non-empty DataFrame ---
        first_key = next(iter(self.pvarrays))
        ref_df = _ensure_time_index(self.pvarrays[first_key])
        if ref_df.empty:
            for _, df in self.pvarrays.items():
                ref_df = _ensure_time_index(df)
                if not ref_df.empty:
                    break
        if ref_df.empty:
            return pd.DataFrame()
        ref_index = ref_df.index

        out_cols: Dict[Tuple[str, str, int], pd.Series] = {}

        # --- Process each sgen DataFrame ---
        for sgen_idx, df in self.pvarrays.items():
            dfi = _ensure_time_index(df)
            if dfi.empty:
                # Fill with default if DataFrame is empty
                self.logger.warning(
                    f"sgen {sgen_idx}: empty DataFrame; filling with fill_value={fill_value}.",
                    UserWarning,
                )
                p_series = pd.Series(fill_value, index=ref_index, dtype=float)
                q_series = pd.Series(fill_value, index=ref_index, dtype=float)
                out_cols[("sgen", "p_mw", int(sgen_idx))] = p_series
                out_cols[("sgen", "q_mvar", int(sgen_idx))] = q_series
                continue

            # Align to reference index if needed
            if not dfi.index.equals(ref_index):
                self.logger.warning(
                    f"sgen {sgen_idx}: timestamps differ from reference; reindexing.",
                    UserWarning,
                )
                dfi = dfi.reindex(ref_index)

            # --------------------
            # Active power (p_mw)
            # --------------------
            p_series = None
            used_col = None

            # Try candidate active power columns
            for c in p_col_candidates:
                if c in dfi.columns:
                    used_col = c
                    if c in ("p_mw", "ac_p_mw"):
                        p_series = dfi[c].astype(float)
                    elif c == "ac_p_kw":
                        p_series = dfi[c].astype(float) / 1e3
                    else:  # Assume values are in W
                        self.logger.warning(
                            f"sgen {sgen_idx}: using '{c}' (assumed W) -> converted to MW.",
                            UserWarning,
                        )
                        p_series = dfi[c].astype(float) / 1e6
                    break

            # Fallback: derive AC power from DC with efficiency
            if p_series is None:
                if "dc_p_mp" in dfi.columns:
                    if assume_ac_from_dc is None:
                        raise ValueError(
                            f"sgen {sgen_idx}: only 'dc_p_mp' present but no efficiency provided."
                        )
                    self.logger.warning(
                        f"sgen {sgen_idx}: converting 'dc_p_mp' to AC with efficiency {assume_ac_from_dc}.",
                        UserWarning,
                    )
                    p_series = (
                        dfi["dc_p_mp"].astype(float) * float(assume_ac_from_dc)
                    ) / 1e6
                    used_col = "dc_p_mp"
                elif "p_dc" in dfi.columns:
                    if assume_ac_from_dc is None:
                        raise ValueError(
                            f"sgen {sgen_idx}: only 'p_dc' present but no efficiency provided."
                        )
                    self.logger.warning(
                        f"sgen {sgen_idx}: converting 'p_dc' to AC with efficiency {assume_ac_from_dc}.",
                        UserWarning,
                    )
                    p_series = (
                        dfi["p_dc"].astype(float) * float(assume_ac_from_dc)
                    ) / 1e6
                    used_col = "p_dc"
                else:
                    raise ValueError(
                        f"sgen {sgen_idx}: no valid active power column found."
                    )

            # Replace NaNs if present
            if p_series.isna().any():
                n = int(p_series.isna().sum())
                self.logger.warning(
                    f"sgen {sgen_idx}: {n} NaNs in '{used_col}' -> filling with fill_value={fill_value}.",
                    UserWarning,
                )
                p_series = p_series.fillna(fill_value)

            # ----------------------
            # Reactive power (q_mvar)
            # ----------------------
            q_series = None
            used_q_source = None

            # Prefer explicit reactive power columns
            for c in q_col_candidates:
                if c in dfi.columns:
                    q_series = dfi[c].astype(float)
                    used_q_source = c
                    break

            # Else compute from power factor
            if q_series is None:
                pf_col = next((c for c in pf_col_candidates if c in dfi.columns), None)
                if pf_col is not None:
                    self.logger.warning(
                        f"sgen {sgen_idx}: computing q from power factor '{pf_col}'.",
                        UserWarning,
                    )
                    pf = dfi[pf_col].clip(lower=1e-6, upper=1.0).astype(float)
                    q_series = p_series * np.tan(np.arccos(pf))
                    used_q_source = pf_col
                else:
                    # Try cos_phi from net.sgen
                    cos_phi = None
                    if (
                        hasattr(net, "sgen")
                        and "cos_phi" in getattr(net, "sgen").columns
                    ):
                        try:
                            cos_phi = float(net.sgen.at[sgen_idx, "cos_phi"])
                        except Exception:
                            cos_phi = None
                    if (
                        cos_phi is not None
                        and np.isfinite(cos_phi)
                        and 0.0 < cos_phi <= 1.0
                    ):
                        self.logger.warning(
                            f"sgen {sgen_idx}: computing q from cos_phi={cos_phi}.",
                            UserWarning,
                        )
                        q_series = p_series * np.tan(np.arccos(cos_phi))
                        used_q_source = "cos_phi(net.sgen)"
                    else:
                        # Fallback to default value
                        self.logger.warning(
                            f"sgen {sgen_idx}: no q found -> using default_q_mvar={default_q_mvar}.",
                            UserWarning,
                        )
                        q_series = pd.Series(
                            default_q_mvar, index=ref_index, dtype=float
                        )
                        used_q_source = "default"

            # Replace NaNs in q-series
            if q_series.isna().any():
                n = int(q_series.isna().sum())
                self.logger.warning(
                    f"sgen {sgen_idx}: {n} NaNs in '{used_q_source}' -> filling with fill_value={fill_value}.",
                    UserWarning,
                )
                q_series = q_series.fillna(fill_value)

            # Assign to output dictionary
            out_cols[("sgen", "p_mw", int(sgen_idx))] = p_series.astype(float)
            out_cols[("sgen", "q_mvar", int(sgen_idx))] = q_series.astype(float)

        # --- Assemble final wide DataFrame ---
        out = pd.DataFrame(out_cols, index=ref_index)
        out = out.reindex(sorted(out.columns, key=lambda t: (t[0], t[1], t[2])), axis=1)
        return out

    def add_gridresult(self, df: pd.DataFrame):
        if df is None or df.empty:
            self.logger.warning("[SimulationResults] No grid results to add")
            return
        else:
            self.grid = df
