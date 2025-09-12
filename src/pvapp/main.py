# * =============================
# *              MAIN
# * =============================

"""
PVApp — Main entry point.

Description
-----------
Command-line interface to start the PV Plants Analyser in different modes.

Supported modes:
- **gui**: Launch the Streamlit-based GUI application.
- **dev**: Developer sandbox (logger configured only; reserved for extensions).

Logging
-------
Configured via `tools.logger.setup_logger`. By default:
- `gui` uses DEBUG (interactive session).
- `dev` uses INFO.

CLI
---
Usage examples:
    $ python -m main gui
    $ python -m main gui --log-level INFO
    $ python -m main dev  --log-level DEBUG --no-queue

Args:
    mode (str): One of {"gui", "dev"}.
    --log-level (str): {"DEBUG","INFO","WARNING","ERROR","CRITICAL"} (optional).
    --no-queue (flag): Disable QueueHandler/QueueListener (single-process logs).

Returns:
    None

Raises:
    ValueError: If an unknown mode is provided.

---
Notes:
- The GUI entrypoint is `gui.gui.streamlit`.
- Queue-based logging is helpful when subprocesses may emit logs.

Example:
    >>> # Programmatic call
    >>> from main import run
    >>> run(mode="gui", log_level="INFO", use_queue=True)

---
TODO:
- Add a `test` mode for headless pipelines (e.g., batch simulations).
- Load defaults from a config file or env vars.
- Add `--version` tied to project metadata.
"""

from __future__ import annotations

# * =========================================================
# *                      IMPORTS (ORDERED)
# * =========================================================
from typing import Literal, Optional

import argparse

from tools.logger import setup_logger, get_logger


# * =========================================================
# *                      LOGGER HELPERS
# * =========================================================
def _configure_logger(log_level: str, *, use_queue: bool = True) -> None:
    """
    Configure the project logger.

    Args:
        log_level (str): One of {"DEBUG","INFO","WARNING","ERROR","CRITICAL"}.
        use_queue (bool): Enable multiprocessing-safe QueueHandler.

    Returns:
        None
    """
    setup_logger("pvapp", log_level=log_level, use_queue=use_queue)


# * =========================================================
# *                          RUN API
# * =========================================================
def run(
    *,
    mode: Literal["gui", "dev"],
    log_level: Optional[str] = None,
    use_queue: bool = True,
) -> None:
    """
    Programmatic runner (also used by the CLI).

    Args:
        mode (Literal["gui","dev"]): Execution mode.
        log_level (Optional[str]): Logger level; defaults depend on mode.
        use_queue (bool): Enable QueueHandler/QueueListener if True.

    Returns:
        None

    Raises:
        ValueError: If `mode` is unknown.
    """
    # ------ Defaults per mode ------
    effective_level = (log_level or ("DEBUG" if mode == "gui" else "INFO")).upper()

    _configure_logger(effective_level, use_queue=use_queue)
    logger = get_logger("pvapp")

    if mode == "gui":
        # Delayed import: keep CLI responsive even if Streamlit is heavy to import.
        from gui.gui import streamlit

        logger.info("Starting GUI (Streamlit)…")
        streamlit()
        return

    if mode == "dev":
        logger.info("Developer mode started. No further actions implemented yet.")
        return

    raise ValueError(f"Unknown mode: {mode}")


# * =========================================================
# *                       CLI ENTRYPOINT
# * =========================================================
def _build_parser() -> argparse.ArgumentParser:
    """
    Build and return the argument parser.

    Returns:
        argparse.ArgumentParser: Configured CLI parser.
    """
    parser = argparse.ArgumentParser(
        prog="pvapp",
        description="PV Plants Analyser — main entry point",
    )

    parser.add_argument(
        "mode",
        type=str,
        choices=["gui", "dev"],
        help="Execution mode: 'gui' for Streamlit UI, 'dev' for developer sandbox.",
    )

    parser.add_argument(
        "--log-level",
        dest="log_level",
        type=str,
        choices=[
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL",
            "debug",
            "info",
            "warning",
            "error",
            "critical",
        ],
        help="Logger level (default: DEBUG for 'gui', INFO for 'dev').",
    )

    parser.add_argument(
        "--no-queue",
        dest="no_queue",
        action="store_true",
        help="Disable QueueHandler/QueueListener (use single-process handlers).",
    )

    # Future flags could go here (e.g., --config path/to/config.toml)
    return parser


def main() -> None:
    """
    Parse CLI args and dispatch to `run()`.
    """
    parser = _build_parser()
    args = parser.parse_args()

    mode: Literal["gui", "dev"] = args.mode  # type: ignore[assignment]
    use_queue = not bool(args.no_queue)

    # Normalize log level
    log_level = args.log_level.upper() if isinstance(args.log_level, str) else None

    run(mode=mode, log_level=log_level, use_queue=use_queue)


# * =========================================================
# *                          SCRIPT MODE
# * =========================================================
if __name__ == "__main__":
    main()
