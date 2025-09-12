from typing import Optional

import json
from pathlib import Path

import pandas as pd
import streamlit as st


# * =============================
# *        PLANT ANALYSER
# * =============================
class PlantAnalyser:
    """
    Utility class to load and analyze simulation results from `SimulationResults` encoded CSV format.

    Attributes:
        data (Optional[pd.DataFrame]): Loaded simulation results (indexed by timestamp).
        site (Optional[str]): Placeholder for site metadata (not yet implemented).
        plant (Optional[str]): Placeholder for plant metadata (not yet implemented).

    Methods:
        periodic_report: Aggregate results by season (sum and mean).
        numeric_dataframe: Extract numeric data for arrays or grid.
        grid: Property returning grid-related results.
        arrays: Property returning dict of PV array results.
        array_ids: Property returning available array IDs.
        all_components: Property returning both grid and arrays together.
        get_array: Get results for a specific array.
        filter_grid: Filter grid results by element and index.
    """

    # * =========================================================
    # *                      LIFECYCLE
    # * =========================================================
    def __init__(self, subfolder: Path) -> None:
        """
        Load plant simulation results from `simulation.csv` exported by `SimulationResults`.

        Args:
            subfolder (Path): Folder containing the `simulation.csv` file.
        """
        self.data: Optional[pd.DataFrame] = None
        self.site: Optional[str] = None
        self.plant: Optional[str] = None

        simulations_file = subfolder / "simulation.csv"
        if simulations_file.exists():
            try:
                self.data = pd.read_csv(simulations_file)
                self.data["timestamp"] = pd.to_datetime(
                    self.data["timestamp"], utc=True, errors="coerce"
                )
                self.data.set_index("timestamp", inplace=True)
            except Exception as e:
                st.error(f"Failed to read {simulations_file}: {e}")
                self.data = None
        else:
            st.error(f"Missing expected simulation.csv in {subfolder}")

    # * =========================================================
    # *                      ANALYSIS
    # * =========================================================
    def periodic_report(
        self,
        array: Optional[int] = None,
        etype: Optional[str] = None,
        idx: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Compute seasonal sums and means for selected data.

        Args:
            array (Optional[int]): PV array ID to analyze.
            etype (Optional[str]): Grid element type (e.g. "bus", "sgen").
            idx (Optional[int]): Element index.

        Returns:
            pd.DataFrame: Long-format DataFrame with columns
                ['season','variable','value','stat'].
        """
        if array is not None:
            if array not in self.array_ids:
                return self.arrays
            data = self.arrays[array]
        else:
            if etype and idx is not None:
                data = self.filter_grid(elements=[etype], indices=[idx])
            else:
                data = self.grid

        seasons = {
            "winter": data[(data.index.month == 12) | (data.index.month <= 2)],
            "spring": data[(data.index.month >= 3) & (data.index.month <= 5)],
            "summer": data[(data.index.month >= 6) & (data.index.month <= 8)],
            "autumn": data[(data.index.month >= 9) & (data.index.month <= 11)],
            "annual": data,
        }
        results: dict[str, dict[str, pd.Series]] = {"sum": {}, "mean": {}}

        for season_name, season_df in seasons.items():
            numeric_cols = season_df.select_dtypes(include="number").columns
            sums = season_df[numeric_cols].sum()
            means = season_df[numeric_cols].mean()

            results["sum"][season_name] = sums
            results["mean"][season_name] = means

        df_sums = pd.DataFrame(results["sum"]).T
        df_means = pd.DataFrame(results["mean"]).T

        # Long-format conversion
        df_sums_long = df_sums.reset_index().melt(
            id_vars="index", var_name="variable", value_name="value"
        )
        df_sums_long["stat"] = "sum"

        df_means_long = df_means.reset_index().melt(
            id_vars="index", var_name="variable", value_name="value"
        )
        df_means_long["stat"] = "mean"

        df_plot = pd.concat([df_sums_long, df_means_long])
        df_plot.rename(columns={"index": "season"}, inplace=True)

        return df_plot

    def numeric_dataframe(
        self,
        array: Optional[int] = None,
        etype: Optional[str] = None,
        idx: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Return raw numeric results for an array or grid element.

        Args:
            array (Optional[int]): PV array ID to select.
            etype (Optional[str]): Grid element type.
            idx (Optional[int]): Element index.

        Returns:
            pd.DataFrame: Numeric subset of results.
        """
        if array is not None:
            if array not in self.array_ids:
                return pd.DataFrame()
            data = self.arrays[array]
        else:
            if etype and idx is not None:
                data = self.filter_grid(elements=[etype], indices=[idx])
            else:
                data = self.grid
        return data

    # * =========================================================
    # *                     PROPERTIES
    # * =========================================================
    @property
    def grid(self) -> pd.DataFrame:
        """
        Extract grid-related results (columns prefixed with '(').

        Returns:
            pd.DataFrame: Grid-related results with original tuple-style column names.
        """
        if self.data is None:
            return pd.DataFrame()
        grid_cols = [c for c in self.data.columns if c.startswith("(")]
        df = self.data[grid_cols].copy()
        return df

    @property
    def arrays(self) -> dict[int, pd.DataFrame]:
        """
        Extract PV array results grouped by array ID.

        Returns:
            dict[int, pd.DataFrame]: {array_id: DataFrame} with renamed columns.
        """
        if self.data is None:
            return {}
        out: dict[int, list[tuple[str, str]]] = {}
        for col in self.data.columns:
            if "_" in col and not col.startswith("("):
                prefix, rest = col.split("_", 1)
                try:
                    key = int(prefix)
                except ValueError:
                    continue
                if key not in out:
                    out[key] = []
                out[key].append((col, rest))

        return {
            key: self.data[[orig for orig, _ in cols]].rename(
                columns={orig: clean for orig, clean in cols}
            )
            for key, cols in out.items()
        }

    @property
    def array_ids(self) -> list[int]:
        """
        List available PV array IDs.

        Returns:
            list[int]: Sorted array IDs.
        """
        return sorted(self.arrays.keys())

    @property
    def all_components(self) -> dict[str, pd.DataFrame | dict[int, pd.DataFrame]]:
        """
        Return both grid and array results in a dictionary.

        Returns:
            dict[str, pd.DataFrame | dict[int, pd.DataFrame]]:
                {"grid": DataFrame, "arrays": {id: DataFrame, ...}}
        """
        return {"grid": self.grid, "arrays": self.arrays}

    # * =========================================================
    # *                     ACCESSORS
    # * =========================================================
    def get_array(self, array_id: int) -> pd.DataFrame:
        """
        Get the DataFrame of a specific array.

        Args:
            array_id (int): Array ID.

        Returns:
            pd.DataFrame: DataFrame of the array, or empty DataFrame if missing.
        """
        return self.arrays.get(array_id, pd.DataFrame())

    def filter_grid(
        self, elements: list[str] | None = None, indices: list[int] | None = None
    ) -> pd.DataFrame:
        """
        Filter grid results by element type and/or index.

        Args:
            elements (Optional[list[str]]): Elements to keep (e.g., ["bus", "sgen"]).
            indices (Optional[list[int]]): Element indices to keep.

        Returns:
            pd.DataFrame: Filtered grid results with simplified column names.
        """
        import ast

        if self.grid.empty:
            return self.grid

        if elements:
            res_tables = [
                f"res_{el}" if not el.startswith("res_") else el for el in elements
            ]
        else:
            res_tables = None

        new_cols: dict[str, str] = {}
        keep_cols: list[str] = []
        for col in self.grid.columns:
            try:
                parsed = ast.literal_eval(col)
            except Exception:
                continue

            if not isinstance(parsed, tuple) or len(parsed) != 3:
                continue

            table, var, idx = parsed

            if res_tables and table not in res_tables:
                continue
            if indices and idx not in indices:
                continue

            keep_cols.append(col)
            new_cols[col] = var

        out = self.grid[keep_cols].rename(columns=new_cols)
        return out
