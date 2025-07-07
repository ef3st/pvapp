from utils.logger import setup_logger, get_logger
from gui.maingui import streamlit


def set_logger():
    setup_logger("solartracker", log_level="DEBUG", use_queue=True)
    return get_logger("solartracker")


def main():
    # logger = set_logger()
    streamlit()


if __name__ == "__main__":
    main()
