from implant_model.site import Site
import pandas as pd
from implant_model.nature import Nature
from implant_model.implant import Implant
from implant_model.modelchain import BuildModelChain
from pvlib.pvsystem import retrieve_sam
from utils.logger import setup_logger, get_logger
from analysis.database import Database
from gui.maingui import streamlit


def set_logger():
    setup_logger("solartracker", log_level="DEBUG", use_queue=True)
    return get_logger("solartracker")


def main():
    # logger = set_logger()
    streamlit()


if __name__ == "__main__":
    main()
