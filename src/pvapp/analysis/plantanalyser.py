import pandas as pd
import json
from pathlib import Path
import streamlit as st
from typing import Optional


class PlantAnalyser:
    def __init__(self, subfolder: Path):
        """
        Load plant simulation results from CSV exported by SimulationResults.

        Args:
            subfolder (Path): Folder containing the `simulation.csv` file.
        """
        self.data = None
        self.site = None
        self.plant = None

        simulations_file = subfolder / "simulation.csv"
        if simulations_file.exists():
            try:
                self.data = pd.read_csv(simulations_file)
                self.data["timestamp"] = pd.to_datetime(
                    self.data["timestamp"], utc=True, errors="coerce"
                )
                self.data.set_index("timestamp", inplace=True)
            except Exception as e:
                st.error(f" Failed to read {simulations_file}: {e}")
                self.data = None
        else:
            st.error(f" Missing expected simulation.csv in {subfolder}")

    def periodic_report(
        self,
        array: Optional[int] = None,
        etype: Optional[str] = None,
        idx: Optional[int] = None,
    ):
        if array is not None:
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
        results = {"sum": {}, "mean": {}}

        for season_name, season_df in seasons.items():
            numeric_cols = season_df.select_dtypes(include="number").columns
            sums = season_df[numeric_cols].sum()
            means = season_df[numeric_cols].mean()

            # stats = pd.concat([sums.add_suffix('_sum'), means.add_suffix('_mean')])

            results["sum"][season_name] = sums
            results["mean"][season_name] = means

        df_sums = pd.DataFrame(results["sum"]).T
        df_means = pd.DataFrame(results["mean"]).T
        # Aggiungiamo una colonna per indicare il tipo
        df_sums_long = df_sums.reset_index().melt(
            id_vars="index", var_name="variable", value_name="value"
        )
        df_sums_long["stat"] = "sum"

        df_means_long = df_means.reset_index().melt(
            id_vars="index", var_name="variable", value_name="value"
        )
        df_means_long["stat"] = "mean"

        # Unione
        df_plot = pd.concat([df_sums_long, df_means_long])
        df_plot.rename(columns={"index": "season"}, inplace=True)

        return df_plot

    def numeric_dataframe(
        self,
        array: Optional[int] = None,
        etype: Optional[str] = None,
        idx: Optional[int] = None,
    ):
        if array is not None:
            data = self.arrays[array]
        else:
            if etype and idx is not None:
                data = self.filter_grid(elements=[etype], indices=[idx])
            else:
                data = self.grid
        return data

    @property
    def grid(self) -> pd.DataFrame:
        """
        Extract grid-related results (columns prefixed with 'grid_').
        Column names are returned without the 'grid_' prefix.
        """
        if self.data is None:
            return pd.DataFrame()
        grid_cols = [c for c in self.data.columns if c.startswith("(")]
        df = self.data[grid_cols].copy()
        # df.columns = [c.removeprefix("grid_") for c in df.columns]
        return df

    @property
    def arrays(self) -> dict[int, pd.DataFrame]:
        """
        Extract PV array results, grouped by sgen_id prefix.
        Column names are returned without the '<id>_' prefix.
        Returns a dict {sgen_id: DataFrame}.
        """
        if self.data is None:
            return {}
        out = {}
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
        List of available PV array IDs in the dataset.
        """
        return sorted(self.arrays.keys())

    @property
    def all_components(self) -> dict[str, pd.DataFrame | dict[int, pd.DataFrame]]:
        """
        Return a dict with both grid and array results:
        {
            "grid": <DataFrame>,
            "arrays": {id: DataFrame, ...}
        }
        """
        return {"grid": self.grid, "arrays": self.arrays}

    def get_array(self, array_id: int) -> pd.DataFrame:
        """
        Get the DataFrame of a specific array.
        Returns an empty DataFrame if the array is not present.
        """
        return self.arrays.get(array_id, pd.DataFrame())

    def filter_grid(
        self, elements: list[str] | None = None, indices: list[int] | None = None
    ) -> pd.DataFrame:
        import ast

        if self.grid.empty:
            return self.grid

        # normalize element names -> res_element
        if elements:
            res_tables = [
                f"res_{el}" if not el.startswith("res_") else el for el in elements
            ]
        else:
            res_tables = None

        new_cols = {}
        keep_cols = []
        for col in self.grid.columns:
            try:

                # parse "('res_bus','vm_pu',0)" into tuple
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
            new_cols[col] = var  # only variable name

        out = self.grid[keep_cols].rename(columns=new_cols)
        return out
