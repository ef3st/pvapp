from implant_model.site import Site
import pandas as pd
from implant_model.nature import Nature
from implant_model.implant import Implant
from implant_model.modelchain import BuildModelChain
from pvlib.pvsystem import retrieve_sam
from utils.logger import setup_logger, get_logger
from analysis.database import Database
from analysis.analyser import Analyser
import json
from pathlib import Path

def Simulate(subfolder:Path):
    site_path = subfolder / "site.json"
    with site_path.open() as f:
        data_site = json.load(f)
    
    site = Site(name=data_site["name"], coordinates=(data_site["coordinates"]["lat"],data_site["coordinates"]["lon"]), altitude=data_site["altitude"],tz=data_site["tz"])
    
    implant_path = subfolder / "implant.json"
    with implant_path.open() as f:
        data_implant = json.load(f)
    implant = Implant(name=data_implant["name"], location=site,id=subfolder.name)
    module = None
    if data_implant["module"]["origin"] == "Custom":
        module = data_implant["module"]["model"]
    else:
        module = retrieve_sam(data_implant["module"]["origin"])[data_implant["module"]["name"]]
    
    inverter = None
    if data_implant["inverter"]["origin"] == "Custom":
        inverter = data_implant["inverter"]["model"]
    else:
        inverter = retrieve_sam(data_implant["inverter"]["origin"])[data_implant["inverter"]["name"]]
        
    mount_type = data_implant["mount"]["type"]
    
    implant.setimplant(module=module,inverter=inverter,mount_type=mount_type)
    
    modelchain = BuildModelChain(system=implant.system, site=site.site)
    database: Database = Database()
    times = pd.date_range(
            start="2024-03-01",
            end="2025-02-28",
            freq="1h",
            tz=site.site.tz,
        )
    nature = Nature(site.site, times)
    modelchain.run_model(nature.weather_simulation(temp_air=25, wind_speed=1))
    database.add_modelchainresult(
            implant.id, implant.name, modelchain.results, "annual", mount=mount_type
        )
    database.save(subfolder)