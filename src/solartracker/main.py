from implant_model.site import Site
import pandas as pd
from implant_model.nature import Nature
from implant_model.implant import Implant
from implant_model.modelchain import BuildModelChain
from pvlib.pvsystem import retrieve_sam
from utils.logger import setup_logger, get_logger
from analysis.database import Database
from analysis.analyser import Analyser
from gui.maingui import streamlit


def set_logger():
    setup_logger("solartracker", log_level="DEBUG", use_queue=True)
    return get_logger("solartracker")


def main():
    logger = set_logger()
    streamlit()
    return
    logger = set_logger()
    site = Site("NE", coordinates=(45.4642, 45.4642), altitude=0, tz="Europe/Rome")
    implant = Implant(name="PV_Implant_Single_Axis", location=site)
    module = retrieve_sam("CECMod")["Canadian_Solar_Inc__CS5P_220M"]
    inverter = {"pdc0": 240}
    implant.setimplant(
        module=module, inverter=inverter, mount_type="SingleAxisTrackerMount"
    )
    logger.info(
        f"Implant {implant.name} built with: \n - module: {module} \n - inverter: {inverter}"
    )
    modelchain = BuildModelChain(system=implant.system, site=site.site)

    metheorological_periods = {
        "spring": ("2024-03-01", "2024-05-31"),
        "summer": ("2024-06-01", "2024-08-31"),
        "autumn": ("2024-09-01", "2024-11-30"),
        "winter": ("2024-12-01", "2025-02-28"),
        "annual": ("2024-03-01", "2025-02-28"),
        "daily": ("2024-06-21", "2024-06-22"),
    }

    database: Database = Database()
    for period in metheorological_periods:
        times = pd.date_range(
            start=metheorological_periods[period][0],
            end=metheorological_periods[period][1],
            freq="1h",
            tz=site.site.tz,
        )
        nature = Nature(site.site, times)
        modelchain.run_model(nature.weather_simulation(temp_air=25, wind_speed=1))
        database.add_modelchainresult(
            implant.id, implant.name, modelchain.results, period, mount="Custom"
        )

    site = Site("NE", coordinates=(45.4642, 45.4642), altitude=0, tz="Europe/Rome")
    implant = Implant(name="PV_Implant_Fixed", location=site)
    module = retrieve_sam("CECMod")["Canadian_Solar_Inc__CS5P_220M"]
    inverter = {"pdc0": 240}
    implant.setimplant(module=module, inverter=inverter, mount_type="FixedMount")
    logger.info(
        f"Implant {implant.name} built with: \n - module: {module} \n - inverter: {inverter}"
    )
    modelchain = BuildModelChain(system=implant.system, site=site.site)

    for period in metheorological_periods:
        times = pd.date_range(
            start=metheorological_periods[period][0],
            end=metheorological_periods[period][1],
            freq="1h",
            tz=site.site.tz,
        )
        nature = Nature(site.site, times)
        modelchain.run_model(nature.weather_simulation(temp_air=25, wind_speed=1))
        database.add_modelchainresult(
            implant.id, implant.name, modelchain.results, period, mount="FixedMount"
        )

    # database.show()

    # gui(database.database)
    # Analyser(database).mountcomparison()


if __name__ == "__main__":
    main()
