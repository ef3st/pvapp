from utils.logger import setup_logger, get_logger
import argparse

def set_logger(log_level):
    setup_logger("solartracker", log_level=log_level, use_queue=True)
    return get_logger("solartracker")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", type=str)
    parser.add_argument("--debug", dest= "log_level", action="store_const", const="DEBUG")
    parser.add_argument("--info", dest= "log_level", action="store_const", const="INFO")
    parser.add_argument("--warning", dest= "log_level", action="store_const", const="WARNING")
    parser.add_argument("--critical", dest= "log_level", action="store_const", const="CRITICAL")
    args = parser.parse_args()
    mode = args.mode
    
    if mode == "gui":
        from gui.maingui import streamlit
        streamlit()
    elif mode == "dev":
        log_level = args.log_level  if args.log_level else "INFO"
        set_logger(log_level)
        


if __name__ == "__main__":
    main()
