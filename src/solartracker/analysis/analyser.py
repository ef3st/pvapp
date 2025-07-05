from .database import Database
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd


class Analyser:
    def __init__(self, db: Database):
        self.db: pd.DataFrame = db.database
        sns.set_theme(style="dark")  # other: "whitegrid", "white", "darkgrid", "ticks"

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
