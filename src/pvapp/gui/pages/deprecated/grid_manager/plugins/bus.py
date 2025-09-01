# app/plugins/bus.py
from __future__ import annotations
from typing import Any, Dict, Tuple, Callable, Optional
from ..core.registry import ElementPlugin, ElementPayload, BuildResult, registry


class BusPlugin(ElementPlugin):
    """
    Bus element plugin: UI builder + model actions.

    Args:
        T (Callable[[str], Any]): Translator/labels resolver (e.g., self.T).
        sac (Any): UI helper component set (streamlit-antd-components or similar).
        bus_form_ui (Callable[..., Tuple[int, Dict[str, Any]]]):
            Callable that renders the Bus form and returns (quantity, params).
            Signature example: bus_form_ui(id: str, defaults: dict|None, quantity: bool, borders: bool) -> (int, dict)

    Returns:
        BusPlugin: A fully wired plugin ready for registration.

    ------
    Note:
        Dependency Injection: you pass all dependencies from GridManager
        when constructing this plugin — no globals, no circular imports.
    """

    kind = "bus"
    label = "Bus"

    def __init__(
        self,
        *,
        T: Callable[[str], Any],
        sac: Any,
        bus_form_ui: Callable[..., Tuple[int, Dict[str, Any]]],
    ) -> None:
        self.T = T
        self.sac = sac
        self._bus_form_ui = bus_form_ui

    # ---------- UI ----------
    def build_params_ui(
        self, *, id: str, defaults: Optional[Dict[str, Any]] = None
    ) -> BuildResult:
        """
        Render the Bus form and normalize the payload.

        Args:
            id (str): Unique UI key suffix.
            defaults (dict|None): Pre-filled params for editing.

        Returns:
            BuildResult: (ok, payload) where payload is:
                {
                    "quantity": int,         # how many buses (creation flows)
                    "params":   dict,        # BusParams-like structure
                }
        ------
        Note:
            - Always returns ok=True here; add validations if needed.
            - When used in edit dialogs, you may ignore "quantity".
        """
        qty, params = self._bus_form_ui(
            id=id,
            bus=defaults,
            quantity=True,
            borders=True,
        )
        payload: ElementPayload = {"quantity": int(qty or 1), "params": params}
        return True, payload

    # ---------- Model actions ----------
    def create_in_grid(self, grid: Any, payload: ElementPayload) -> None:
        """
        Create one or more buses using the grid model API.

        Args:
            grid (Any): The grid model (e.g., PlantPowerGrid).
            payload (ElementPayload): {"quantity": int, "params": dict}

        Returns:
            None
        """
        qty = int(payload.get("quantity", 1))
        params = payload["params"]
        for _ in range(qty):
            grid.create_bus(params)

    def update_in_grid(self, grid: Any, payload: ElementPayload) -> None:
        """
        Update a bus by id using the grid model API.

        Args:
            grid (Any): The grid model.
            payload (ElementPayload): {"id": int, "params": dict}

        Returns:
            None

        Raises:
            ValueError: If 'id' is missing.
        """
        bus_id = payload.get("id")
        if bus_id is None:
            raise ValueError("Missing 'id' in payload for bus update.")
        grid.update_bus(int(bus_id), payload["params"])
