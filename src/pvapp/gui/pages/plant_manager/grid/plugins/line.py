from typing import Any, Tuple, Dict
import streamlit as st
from ..core.registry import ElementSpec, element

# from your_module import LineParams
# Reuse your existing function:
# def line_params(id: str, line: Optional[LineParams] = None, horizontal: bool = True, borders: bool = True) -> Tuple[bool, LineParams]


@element(kind="line", label="Line")
class LinePlugin:
    def build_params_ui(
        self, *, id: str = "line", defaults=None
    ) -> Tuple[bool, Dict[str, Any]]:
        gm = st.session_state.get("_gm_instance")
        if gm is None:
            st.error("GridManager instance not found in session.")
            return False, {}
        ok, params = gm.line_params(id=id, line=defaults, horizontal=True, borders=True)
        payload = {"params": params}
        return ok, payload

    def create_in_grid(self, grid, payload: Dict[str, Any]) -> None:
        grid.link_buses(payload["params"])  # your model API

    def update_in_grid(self, grid, payload: Dict[str, Any]) -> None:
        # If your API needs an id, put it in payload["id"] and call grid.update_line(id, params)
        grid.update_line(payload["params"])  # adapt as needed

    @property
    def spec(self) -> ElementSpec:
        return ElementSpec(
            kind="line",
            label="Line",
            build_params_ui=self.build_params_ui,
            create_in_grid=self.create_in_grid,
            update_in_grid=self.update_in_grid,
        )
