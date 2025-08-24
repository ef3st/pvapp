from __future__ import annotations

from typing import Any, Dict, Protocol, Tuple, Optional, runtime_checkable, Iterable

# ---------- Types ----------
ElementPayload = Dict[str, Any]  # normalized payload for UI <-> model
BuildResult = Tuple[bool, ElementPayload]  # (is_valid, payload)


@runtime_checkable
class ElementPlugin(Protocol):
    """
    Contract for grid element plugins (bus, line, trafo, ...).

    Args:
        None

    Methods:
        build_params_ui(*, id: str, defaults=None) -> BuildResult:
            Render the parameter editor and return (ok, payload).
            The payload should at least contain "params"; it can also include
            "quantity", "id", or other fields as needed by create/update.
        create_in_grid(grid, payload: ElementPayload) -> None:
            Apply creation using the grid model API.
        update_in_grid(grid, payload: ElementPayload) -> None:
            Apply update using the grid model API.

    Returns:
        ElementPlugin: Implementations are registered into the Registry.

    ------
    Note:
        - This is a Protocol (structural typing): any object with the same
          attributes/methods is acceptable — perfect for plugin architectures.
        - Use Dependency Injection when instantiating plugins to provide their
          dependencies (translations, UI helpers, accessors, etc.).
    """

    kind: str
    label: str

    def build_params_ui(
        self, *, id: str, defaults: Any | None = None
    ) -> BuildResult: ...
    def create_in_grid(self, grid: Any, payload: ElementPayload) -> None: ...
    def update_in_grid(self, grid: Any, payload: ElementPayload) -> None: ...


class Registry:
    """
    In-memory registry that maps element `kind` -> plugin instance.

    Args:
        None

    Methods:
        register(plugin): Add a plugin instance (constructor DI already applied).
        get(kind): Retrieve a plugin by kind (raises KeyError if missing).
        has(kind): Check existence.
        kinds(): Iterable of registered kinds.
        clear(): Empty the registry (useful in tests).

    Returns:
        Registry: A simple manager for element plugins.

    ------
    Note:
        - Register **instances**, not classes. This enables Dependency Injection:
          you build the plugin with all its dependencies and then register it.
        - Idempotent on same instance: re-registering the same kind overwrites it.
    """

    def __init__(self) -> None:
        self._items: Dict[str, ElementPlugin] = {}

    def register(self, plugin: ElementPlugin) -> ElementPlugin:
        """
        Register a plugin instance.

        Args:
            plugin (ElementPlugin): The plugin to register. Must expose
                `.kind`, `.label`, and implement the Protocol methods.

        Returns:
            ElementPlugin: The same plugin for fluent usage.

        ------
        Note:
            Raises a TypeError if the plugin does not conform to the Protocol.
        """
        if not isinstance(plugin, ElementPlugin):
            # Structural check at runtime (thanks to @runtime_checkable)
            raise TypeError(
                f"Plugin does not conform to ElementPlugin Protocol: {plugin!r}"
            )
        if not getattr(plugin, "kind", None):
            raise ValueError("Plugin.kind must be a non-empty string.")
        self._items[plugin.kind] = plugin
        return plugin

    def get(self, kind: str) -> ElementPlugin:
        """
        Retrieve a plugin by its kind.

        Args:
            kind (str): Element kind id (e.g., 'bus', 'line').

        Returns:
            ElementPlugin: The registered plugin.

        Raises:
            KeyError: If no plugin is registered for `kind`.
        """
        try:
            return self._items[kind]
        except KeyError:
            raise KeyError(
                f"No plugin registered for kind='{kind}'. Available: {list(self._items)}"
            ) from None

    def has(self, kind: str) -> bool:
        """
        Check if a plugin kind is registered.

        Args:
            kind (str): Kind to check.

        Returns:
            bool: True if registered, False otherwise.
        """
        return kind in self._items

    def kinds(self) -> Iterable[str]:
        """
        List registered kinds.

        Returns:
            Iterable[str]: The plugin kinds.
        """
        return self._items.keys()

    def clear(self) -> None:
        """
        Clear all registered plugins.

        Returns:
            None
        """
        self._items.clear()


# Provide a singleton-like default registry for convenience.
registry = Registry()
