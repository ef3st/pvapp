# * =============================
# *   TYPEDDICT ELEMENT PARAMS
# * =============================
"""
=============================
  HOW TO USE THIS MODULE
=============================
This module centralizes strongly-typed parameter schemas (TypedDict) for
pandapower elements used across the project. Import the specific TypedDict
to build `create_*` calls with IDE/type-checker support and safer refactors.

Typical usage:
  from pvapp.backend.pandapower_network.TypedDict_elements_params import (
      SGenParams, LineParams, PARAM_CLASSES
  )

  sgen: SGenParams = {
      "bus": 3,
      "p_mw": 0.45,
      "q_mvar": 0.0,
      "name": "Array_0",
      "in_service": True,
      "scaling": 1.0,
  }
  line: LineParams = {
      "from_bus": 1,
      "to_bus": 2,
      "length_km": 0.12,
      "std_type": "NAYY 4x50 SE",
      "name": "L1",
      "in_service": True,
  }

  # Optional: dynamic lookup if you have the element name as string
  # schema = PARAM_CLASSES["sgen"]   # -> SGenParams type

Conventions:
- Field names mirror pandapower tables (e.g., net["sgen"], net["line"]).
- All dicts are `total=False`: specific projects can pass only needed keys.
- Prefer these TypedDicts over loose `dict` for clarity and auto-complete.
"""


from typing import TypedDict, Optional, Union, Tuple, Literal, Type, Dict


class SGenParams(TypedDict, total=False):
    """
    Parameters for a static generator (PQ) stored in `net["sgen"]`.

    Attributes:
        bus (int): Bus index where the sgen is connected.
        p_mw (float): Active power injection in MW. Positive means generation.
        q_mvar (Optional[float]): Reactive power injection in MVAr.
        name (Optional[str]): Human-readable element name.
        scaling (float): Multiplier applied to p_mw and q_mvar.
        in_service (bool): Whether the element is active in the power flow.
        type (Optional[str]): Connection type ("wye", "delta") for 3-phase calcs.
        sn_mva (Optional[float]): Rated apparent power in MVA.
        max_p_mw (Optional[float]): Upper bound for active power (OPF).
        min_p_mw (Optional[float]): Lower bound for active power (OPF).
        max_q_mvar (Optional[float]): Upper bound for reactive power (OPF).
        min_q_mvar (Optional[float]): Lower bound for reactive power (OPF).
        controllable (Optional[bool]): If True, treated as flexible in OPF.

    ---
    Notes:
    - See pandapower "sgen" for more details.
    """

    bus: int
    p_mw: float
    q_mvar: Optional[float]
    name: Optional[str]
    scaling: float
    in_service: bool
    type: Optional[str]
    sn_mva: Optional[float]
    max_p_mw: Optional[float]
    min_p_mw: Optional[float]
    max_q_mvar: Optional[float]
    min_q_mvar: Optional[float]
    controllable: Optional[bool]


class GenParams(TypedDict, total=False):
    """
    Parameters for a voltage-controlled generator (PV node) in `net["gen"]`.

    Attributes:
        bus (int): Index of the connected bus.
        p_mw (Optional[float]): Active power setpoint in MW.
        vm_pu (float): Voltage magnitude setpoint in p.u.
        name (Optional[str]): Human-readable name.
        q_mvar (Optional[float]): Reactive power injection.
        min_q_mvar (Optional[float]): Minimum reactive power (OPF).
        max_q_mvar (Optional[float]): Maximum reactive power (OPF).
        sn_mva (Optional[float]): Rated apparent power in MVA.
        slack (Optional[bool]): If True, this generator acts as slack.
        scaling (Optional[float]): Scaling factor for p_mw and q_mvar.
        in_service (bool): Whether the generator is active.
        controllable (Optional[bool]): If True, flexible for OPF.

    ---
    Notes:
    - See pandapower "gen" for more details.
    """

    bus: int
    p_mw: Optional[float]
    vm_pu: float
    name: Optional[str]
    q_mvar: Optional[float]
    min_q_mvar: Optional[float]
    max_q_mvar: Optional[float]
    sn_mva: Optional[float]
    slack: Optional[bool]
    scaling: Optional[float]
    in_service: bool
    controllable: Optional[bool]


class ExtGridParams(TypedDict, total=False):
    """
    Parameters for an external grid (slack) in `net["ext_grid"]`.

    Attributes:
        bus (int): Reference bus index.
        vm_pu (float): Voltage magnitude in p.u.
        va_degree (float): Voltage angle in degrees.
        name (Optional[str]): Human-readable name.
        in_service (bool): Whether the slack is active.

    ---
    Notes:
    - See pandapower "ext_grid" for more details.
    """

    bus: int
    vm_pu: float
    va_degree: float
    name: Optional[str]
    in_service: bool


class BusParams(TypedDict, total=False):
    """
    Parameters for a bus in `net["bus"]`.

    Attributes:
        vn_kv (Union[str, float, None]): Nominal voltage level in kV.
        name (Optional[str]): Human-readable bus name.
        geodata (Optional[tuple[float, float]]): Coordinates for plotting.
        type (Optional[str]): Bus type ("b", "n", "m").
        zone (Union[None, int, str]): Zone/area label.
        in_service (bool): Whether the bus is active.
        min_vm_pu (Optional[float]): Minimum allowed voltage [p.u.].
        max_vm_pu (Optional[float]): Maximum allowed voltage [p.u.].

    ---
    Notes:
    - See pandapower "bus" for more details.
    """

    vn_kv: Union[str, float, None]
    name: Optional[str]
    geodata: Optional[Tuple[float, float]]
    type: Optional[str]
    zone: Union[None, int, str]
    in_service: bool
    min_vm_pu: Optional[float]
    max_vm_pu: Optional[float]


class LineParams(TypedDict, total=False):
    """
    Parameters for a line in `net["line"]`.

    Attributes:
        from_bus (int): Sending-end bus index.
        to_bus (int): Receiving-end bus index.
        length_km (float): Line length in km.
        name (str): Human-readable line name.
        std_type (str): Standard type name (defines impedances).
        in_service (bool): Whether the line is active.

    ---
    Notes:
    - See pandapower "line" for more details.
    """

    from_bus: int
    to_bus: int
    length_km: float
    name: str
    std_type: str
    in_service: bool


class SwitchParams(TypedDict, total=False):
    """
    Parameters for a switch in `net["switch"]`.

    Attributes:
        bus (int): Bus side of the switch.
        element (int): Index of the connected element.
        et (str): Element type ("b", "l", "t", "t3").
        closed (bool): Switch status (True = closed).
        type (Optional[str]): Switch type ("CB", "LS", etc.).
        name (Optional[str]): Human-readable name.
        in_service (Optional[bool]): Whether the switch is active.
        z_ohm (Optional[float]): Resistance for bus-bus switches.

    ---
    Notes:
    - See pandapower "switch" for more details.
    """

    bus: int
    element: int
    et: str
    closed: bool
    type: Optional[str]
    name: Optional[str]
    in_service: Optional[bool]
    z_ohm: Optional[float]


class TrafoParams(TypedDict, total=False):
    """
    Parameters for a two-winding transformer in `net["trafo"]`.

    Attributes:
        hv_bus (int): High-voltage bus index.
        lv_bus (int): Low-voltage bus index.
        std_type (Optional[str]): Transformer standard type.
        name (Optional[str]): Name.
        tap_pos (Optional[int]): Tap position.
        in_service (bool): Whether the transformer is active.
        parallel (Optional[int]): Number of parallel units.
        df (Optional[float]): Derating factor.
        max_loading_percent (Optional[float]): Loading limit.
        sn_mva (Optional[float]): Rated apparent power.
        vn_hv_kv (Optional[float]): HV voltage rating.
        vn_lv_kv (Optional[float]): LV voltage rating.
        vkr_percent (Optional[float]): Real short-circuit voltage.
        vk_percent (Optional[float]): Short-circuit voltage.
        pfe_kw (Optional[float]): Iron losses.
        i0_percent (Optional[float]): No-load current.
        shift_degree (Optional[float]): Phase shift.
        tap_side (Optional[str]): Tap side ("hv" or "lv").
        tap_neutral (Optional[int]): Neutral tap position.
        tap_max (Optional[int]): Maximum tap.
        tap_min (Optional[int]): Minimum tap.
        tap_step_percent (Optional[float]): Tap step [%].
        tap_step_degree (Optional[float]): Tap step [deg].
        tap_phase_shifter (Optional[bool]): Phase-shifting flag.

    ---
    Notes:
    - See pandapower "trafo" for more details.
    """

    hv_bus: int
    lv_bus: int
    std_type: Optional[str]
    name: Optional[str]
    tap_pos: Optional[int]
    in_service: bool
    parallel: Optional[int]
    df: Optional[float]
    max_loading_percent: Optional[float]
    sn_mva: Optional[float]
    vn_hv_kv: Optional[float]
    vn_lv_kv: Optional[float]
    vkr_percent: Optional[float]
    vk_percent: Optional[float]
    pfe_kw: Optional[float]
    i0_percent: Optional[float]
    shift_degree: Optional[float]
    tap_side: Optional[str]
    tap_neutral: Optional[int]
    tap_max: Optional[int]
    tap_min: Optional[int]
    tap_step_percent: Optional[float]
    tap_step_degree: Optional[float]
    tap_phase_shifter: Optional[bool]


class Trafo3WParams(TypedDict, total=False):
    """
    Parameters for a three-winding transformer in `net["trafo3w"]`.

    Attributes:
        hv_bus (int): High-voltage bus index.
        mv_bus (int): Medium-voltage bus index.
        lv_bus (int): Low-voltage bus index.
        std_type (Optional[str]): Transformer type.
        name (Optional[str]): Name.
        tap_pos (Optional[int]): Tap position.
        tap_at_star_point (Optional[bool]): Tap at star point flag.
        in_service (bool): Active status.
        max_loading_percent (Optional[float]): Loading limit.

    ---
    Notes:
    - See pandapower "trafo3w" for more details.
    """

    hv_bus: int
    mv_bus: int
    lv_bus: int
    std_type: Optional[str]
    name: Optional[str]
    tap_pos: Optional[int]
    tap_at_star_point: Optional[bool]
    in_service: bool
    max_loading_percent: Optional[float]


class LoadParams(TypedDict, total=False):
    """
    Parameters for a load in `net["load"]`.

    Attributes:
        bus (int): Bus index.
        p_mw (float): Active power demand in MW.
        q_mvar (float): Reactive power demand in MVAr.
        name (Optional[str]): Name.
        scaling (float): Scaling factor for P/Q.
        in_service (bool): Active status.
        const_z_p_percent (Optional[float]): Constant-Z share of P.
        const_i_p_percent (Optional[float]): Constant-I share of P.
        const_z_q_percent (Optional[float]): Constant-Z share of Q.
        const_i_q_percent (Optional[float]): Constant-I share of Q.
        sn_mva (Optional[float]): Apparent power rating.
        type (Optional[str]): Connection type ("wye" or "delta").
        controllable (Optional[bool]): Flexible in OPF.

    ---
    Notes:
    - See pandapower "load" for more details.
    """

    bus: int
    p_mw: float
    q_mvar: float
    name: Optional[str]
    scaling: float
    in_service: bool
    const_z_p_percent: Optional[float]
    const_i_p_percent: Optional[float]
    const_z_q_percent: Optional[float]
    const_i_q_percent: Optional[float]
    sn_mva: Optional[float]
    type: Optional[str]
    controllable: Optional[bool]


class StorageParams(TypedDict, total=False):
    """
    Parameters for a storage unit in `net["storage"]`.

    Attributes:
        bus (int): Bus index.
        p_mw (float): Active power. Positive = discharging.
        max_e_mwh (float): Maximum energy capacity in MWh.
        soc_percent (float): State of charge [%].
        min_e_mwh (float): Minimum allowed energy.
        q_mvar (float): Reactive power in MVAr.
        sn_mva (float): Apparent power rating.
        controllable (bool): Flexible in OPF.
        name (Optional[str]): Name.
        in_service (bool): Active status.
        type (Optional[str]): Connection type label.
        scaling (Optional[float]): Scaling factor.

    ---
    Notes:
    - See pandapower "storage" for more details.
    """

    bus: int
    p_mw: float
    max_e_mwh: float
    soc_percent: float
    min_e_mwh: float
    q_mvar: float
    sn_mva: float
    controllable: bool
    name: Optional[str]
    in_service: bool
    type: Optional[str]
    scaling: Optional[float]


# * =========================================================
# *                 REGISTRY / MAPPINGS
# * =========================================================

PARAM_CLASSES: Dict[str, type] = {
    "sgen": SGenParams,
    "gen": GenParams,
    "ext_grid": ExtGridParams,
    "bus": BusParams,
    "line": LineParams,
    "switch": SwitchParams,
    "trafo": TrafoParams,
    "trafo3w": Trafo3WParams,
    "load": LoadParams,
    "storage": StorageParams,
}

__all__ = [
    # TypedDicts
    "SGenParams",
    "GenParams",
    "ExtGridParams",
    "BusParams",
    "LineParams",
    "SwitchParams",
    "TrafoParams",
    "Trafo3WParams",
    "LoadParams",
    "StorageParams",
    # Registry
    "PARAM_CLASSES",
]
