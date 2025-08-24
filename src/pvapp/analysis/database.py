import pandas as pd
from pvlib.modelchain import ModelChainResult
from IPython.display import display
from utils.logger import get_logger
from typing import Optional


class SimulationResults:
    def __init__(self):
        self.database: pd.DataFrame = pd.DataFrame()
        self.logger = get_logger("pvapp")

    def add_modelchainresult(
        self,
        pvSystemId: int = 0,
        # plant_name: str,
        results: Optional[ModelChainResult] = None,
        period: Optional[str] = None,
        # mount: str,
    ) -> None:
        if results is None:
            self.logger.warning("[SimulationResults] No modelchain to add")
            return
        new_results = self.gather_modelchain_results(results)
        new_results["sgen_id"] = pvSystemId
        # new_results["Plant_name"] = plant_name
        new_results["period"] = period
        # new_results["mount"] = mount
        new_results.index.name = "timestamp"
        new_results = new_results.reset_index()
        self.database: pd.DataFrame = pd.concat([self.database, new_results])

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
