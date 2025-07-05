from .database import Database
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import json
from pathlib import Path
import streamlit as st
class ImplantAnalyser:
    def __init__(self, subfolder: Path):
        self.data = None  # inizializza sempre

        if subfolder.is_dir():
            site_file = subfolder / "site.json"
            implant_file = subfolder / "implant.json"
            simulations_file = subfolder / "simulation.csv"

            if site_file.exists() and implant_file.exists() and simulations_file.exists():
                try:
                    self.site = json.load(site_file.open())
                    self.implant = json.load(implant_file.open())
                    st.info(f"Loading: {simulations_file}")  # DEBUG

                    self.data = pd.read_csv(
                        simulations_file
                        )
                    self.data['timestamp'] = pd.to_datetime(self.data['timestamp'], utc=True)
                    self.data.set_index('timestamp', inplace=True)
                    st.info(str(self.data.index.dtype))
                    
                except Exception as e:
                    st.error(f" Failed to read data in {subfolder.name}: {e}")
                    self.data = None
            else:
                st.error(f" Missing expected files in {subfolder}")
    
    def periodic_report(self):
        seasons = {
                    'winter': self.data[(self.data.index.month == 12) | (self.data.index.month <= 2)],
                    'spring': self.data[(self.data.index.month >= 3) & (self.data.index.month <= 5)],
                    'summer': self.data[(self.data.index.month >= 6) & (self.data.index.month <= 8)],
                    'autumn': self.data[(self.data.index.month >= 9) & (self.data.index.month <= 11)],
                    'annual': self.data
                }
        results = {
                    "sum": {},
                    "mean": {}
                }

        for season_name, season_df in seasons.items():
            numeric_cols = season_df.select_dtypes(include='number').columns
            sums = season_df[numeric_cols].sum()
            means = season_df[numeric_cols].mean()

            # stats = pd.concat([sums.add_suffix('_sum'), means.add_suffix('_mean')])

            results["sum"][season_name] = sums
            results["mean"][season_name] = means
        
        df_sums = pd.DataFrame(results["sum"]).T
        df_means = pd.DataFrame(results["mean"]).T
        # Aggiungiamo una colonna per indicare il tipo
        df_sums_long = df_sums.reset_index().melt(id_vars='index', var_name='variable', value_name='value')
        df_sums_long['stat'] = 'sum'

        df_means_long = df_means.reset_index().melt(id_vars='index', var_name='variable', value_name='value')
        df_means_long['stat'] = 'mean'

        # Unione
        df_plot = pd.concat([df_sums_long, df_means_long])
        df_plot.rename(columns={'index': 'season'}, inplace=True)
        
        
        
        return df_plot
    
    def numeric_dataframe(self):
        return self.data


    def periodproduction(self):
        dc: pd.DataFrame = self.db[["timestamp", "dc_p_mp", "period"]]
        dc = dc.rename(columns={"dc_p_mp": "p_mp"})
        dc["current"] = "dc"
        ac: pd.DataFrame = self.db[["timestamp", "ac_p_mp", "period"]]
        ac = ac.rename(columns={"ac_p_mp": "p_mp"})
        ac["current"] = "ac"
        df = pd.concat([dc, ac])
        df = df[(df["p_mp"].notna()) & (df["p_mp"] != 0)]
        sns.boxplot(x="period", y="p_mp", hue="current", data=df)
        sns.despine(offset=10, trim=True)
        plt.show()

    def mountcomparison(self):
        df: pd.DataFrame = self.db[["timestamp", "dc_p_mp", "period", "Implant_name"]]
        df = df.rename(columns={"dc_p_mp": "p_mp"})
        df = df[(df["p_mp"].notna()) & (df["p_mp"] != 0)]
        sns.boxplot(x="period", y="p_mp", hue="Implant_name", data=df)
        sns.despine(offset=10, trim=True)
        plt.show()
