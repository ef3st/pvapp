import streamlit as st

from ..utils.translation.traslator import translate
from tools.logger import get_logger


# * =============================
# *             PAGE
# * =============================
class Page:
    """
    Base class for Streamlit application pages.

    Attributes:
        lang (str): Current session language (from `st.session_state["language"]`).
        page_name (str): Page identifier used for translation namespaces.
        logger: Application logger instance (`get_logger("pvapp")`).

    Methods:
        T: Translate a key scoped under this page's namespace.
    """

    # * =========================================================
    # *                      LIFECYCLE
    # * =========================================================
    def __init__(self, pagename: str) -> None:
        """
        Initialize a new Page instance.

        Args:
            pagename (str): Name of the page, used as a translation namespace.
        """
        self.lang: str = st.session_state.get("language", "it")
        self.page_name: str = pagename
        self.logger = get_logger("pvapp")

    # * =========================================================
    # *                      TRANSLATION
    # * =========================================================
    def T(self, key: str) -> str | list:
        """
        Translate a key under this page's namespace.

        Args:
            key (str): Translation key relative to the page namespace.

        Returns:
            str | list: Translated string or list, depending on translation content.
        """
        return translate(f"{self.page_name}.{key}")
