from typing import TypedDict, Optional, Union, Tuple, Literal


class SGenParams(TypedDict, total=False):
    """
    Parameters for a static generator (PQ) stored in net['sgen'].

    Params:
        bus (int): Bus index where the sgen is connected.
        p_mw (float): Active power injection in MW. Positive means generation.
        q_mvar (float, optional): Reactive power injection in MVAr.
        name (str, optional): Human-readable element name.
        scaling (float): Multiplier applied to p_mw and q_mvar.
        in_service (bool): Whether the element is active in the power flow.
        type (str, optional): Connection type ("wye", "delta") for 3-phase calcs.
        sn_mva (float, optional): Rated apparent power in MVA.
        max_p_mw (float, optional): Upper bound for active power (OPF).
        min_p_mw (float, optional): Lower bound for active power (OPF).
        max_q_mvar (float, optional): Upper bound for reactive power (OPF).
        min_q_mvar (float, optional): Lower bound for reactive power (OPF).
        controllable (bool, optional): If True, treated as flexible in OPF.

    ---
    Note:
        See pandapower 'sgen' for more details.
    """

    bus: int  # Bus index where the sgen is connected
    p_mw: float  # Active power [MW], positive = generation
    q_mvar: Optional[float]  # Reactive power [MVAr], +inj / -cons
    name: Optional[str]  # Readable name
    scaling: float  # Multiplier applied to p_mw and q_mvar
    in_service: bool  # True if the element is active
    type: Optional[str]  # Connection type (3-phase only)
    sn_mva: Optional[float]  # Nominal apparent power [MVA]
    max_p_mw: Optional[float]  # Max active power (OPF)
    min_p_mw: Optional[float]  # Min active power (OPF)
    max_q_mvar: Optional[float]  # Max reactive power (OPF)
    min_q_mvar: Optional[float]  # Min reactive power (OPF)
    controllable: Optional[bool]  # Flexible in OPF if True


class GenParams(TypedDict, total=False):
    """
    Parameters for a voltage-controlled generator (PV node) in net['gen'].

    Params:
        bus (int): Index of the connected bus.
        p_mw (float, optional): Active power setpoint in MW.
        vm_pu (float): Voltage magnitude setpoint in p.u.
        name (str, optional): Human-readable name.
        q_mvar (float, optional): Reactive power injection.
        min_q_mvar (float, optional): Minimum reactive power (OPF).
        max_q_mvar (float, optional): Maximum reactive power (OPF).
        sn_mva (float, optional): Rated apparent power in MVA.
        slack (bool, optional): If True, this generator acts as slack.
        scaling (float, optional): Scaling factor for p_mw and q_mvar.
        in_service (bool): Whether the generator is active.
        controllable (bool, optional): If True, flexible for OPF.

    ---
    Note:
        See pandapower 'gen' for more details.
    """

    bus: int  # Bus index
    p_mw: Optional[float]  # Active power [MW]
    vm_pu: float  # Voltage setpoint [pu]
    name: Optional[str]  # Name
    q_mvar: Optional[float]  # Reactive power [MVAr]
    min_q_mvar: Optional[float]  # Min Q (OPF)
    max_q_mvar: Optional[float]  # Max Q (OPF)
    sn_mva: Optional[float]  # Apparent power rating [MVA]
    slack: Optional[bool]  # Slack flag
    scaling: Optional[float]  # Scaling factor
    in_service: bool  # Active status
    controllable: Optional[bool]  # OPF flexibility


class ExtGridParams(TypedDict, total=False):
    """
    Parameters for an external grid (slack) in net['ext_grid'].

    Params:
        bus (int): Reference bus index.
        vm_pu (float): Voltage magnitude in p.u.
        va_degree (float): Voltage angle in degrees.
        name (str, optional): Human-readable name.
        in_service (bool): Whether the slack is active.

    ---
    Note:
        See pandapower 'ext_grid' for more details.
    """

    bus: int  # Reference bus
    vm_pu: float  # Voltage magnitude [pu]
    va_degree: float  # Voltage angle [deg]
    name: Optional[str]  # Name
    in_service: bool  # Active status


class BusParams(TypedDict, total=False):
    """
    Parameters for a bus in net['bus'].

    Params:
        vn_kv (str | float | None): Nominal voltage level in kV.
        name (str, optional): Human-readable bus name.
        geodata (tuple, optional): Coordinates for plotting.
        type (str, optional): Bus type ("b", "n", "m").
        zone (int | str | None): Zone/area label.
        in_service (bool): Whether the bus is active.
        min_vm_pu (float, optional): Minimum allowed voltage [p.u.].
        max_vm_pu (float, optional): Maximum allowed voltage [p.u.].

    ---
    Note:
        See pandapower 'bus' for more details.
    """

    vn_kv: Union[str, float, None]  # Nominal voltage [kV]
    name: Optional[str]  # Name
    geodata: Optional[Tuple]  # (x,y) coordinates
    type: Optional[str]  # Bus type
    zone: Union[None, int, str]  # Zone label
    in_service: bool  # Active status
    min_vm_pu: Optional[float]  # Lower voltage limit [pu]
    max_vm_pu: Optional[float]  # Upper voltage limit [pu]


class LineParams(TypedDict, total=False):
    """
    Parameters for a line in net['line'].

    Params:
        from_bus (int): Sending-end bus index.
        to_bus (int): Receiving-end bus index.
        length_km (float): Line length in km.
        name (str): Human-readable line name.
        std_type (str): Standard type name (defines impedances).
        in_service (bool): Whether the line is active.

    ---
    Note:
        See pandapower 'line' for more details.
    """

    from_bus: int  # From bus
    to_bus: int  # To bus
    length_km: float  # Length [km]
    name: str  # Line name
    std_type: str  # Standard type
    in_service: bool  # Active status


class SwitchParams(TypedDict, total=False):
    """
    Parameters for a switch in net['switch'].

    Params:
        bus (int): Bus side of the switch.
        element (int): Index of the connected element.
        et (str): Element type ("b", "l", "t", "t3").
        closed (bool): Switch status (True = closed).
        type (str, optional): Switch type ("CB", "LS", etc.).
        name (str, optional): Human-readable name.
        in_service (bool, optional): Whether the switch is active.
        z_ohm (float, optional): Resistance for bus-bus switches.

    ---
    Note:
        See pandapower 'switch' for more details.
    """

    bus: int  # Bus side
    element: int  # Connected element index
    et: str  # Element type
    closed: bool  # Switch status
    type: Optional[str]  # Switch type
    name: Optional[str]  # Name
    in_service: Optional[bool]  # Active status
    z_ohm: Optional[float]  # Resistance (bus-bus)


class TrafoParams(TypedDict, total=False):
    """
    Parameters for a two-winding transformer in net['trafo'].

    Params:
        hv_bus (int): High-voltage bus index.
        lv_bus (int): Low-voltage bus index.
        std_type (str, optional): Transformer standard type.
        name (str, optional): Name.
        tap_pos (int, optional): Tap position.
        in_service (bool): Whether the transformer is active.
        parallel (int, optional): Number of parallel units.
        df (float, optional): Derating factor.
        max_loading_percent (float, optional): Loading limit.
        sn_mva (float, optional): Rated apparent power.
        vn_hv_kv (float, optional): HV voltage rating.
        vn_lv_kv (float, optional): LV voltage rating.
        vkr_percent (float, optional): Real short-circuit voltage.
        vk_percent (float, optional): Short-circuit voltage.
        pfe_kw (float, optional): Iron losses.
        i0_percent (float, optional): No-load current.
        shift_degree (float, optional): Phase shift.
        tap_side (str, optional): Tap side ("hv" or "lv").
        tap_neutral (int, optional): Neutral tap pos.
        tap_max (int, optional): Maximum tap.
        tap_min (int, optional): Minimum tap.
        tap_step_percent (float, optional): Tap step [%].
        tap_step_degree (float, optional): Tap step [deg].
        tap_phase_shifter (bool, optional): Phase-shifting flag.

    ---
    Note:
        See pandapower 'trafo' for more details.
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
    Parameters for a three-winding transformer in net['trafo3w'].

    Params:
        hv_bus (int): High-voltage bus index.
        mv_bus (int): Medium-voltage bus index.
        lv_bus (int): Low-voltage bus index.
        std_type (str, optional): Transformer type.
        name (str, optional): Name.
        tap_pos (int, optional): Tap position.
        tap_at_star_point (bool, optional): Tap at star point flag.
        in_service (bool): Active status.
        max_loading_percent (float, optional): Loading limit.

    ---
    Note:
        See pandapower 'trafo3w' for more details.
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
    Parameters for a load in net['load'].

    Params:
        bus (int): Bus index.
        p_mw (float): Active power demand in MW.
        q_mvar (float): Reactive power demand in MVAr.
        name (str, optional): Name.
        scaling (float): Scaling factor for P/Q.
        in_service (bool): Active status.
        const_z_p_percent (float, optional): Const-Z share of P.
        const_i_p_percent (float, optional): Const-I share of P.
        const_z_q_percent (float, optional): Const-Z share of Q.
        const_i_q_percent (float, optional): Const-I share of Q.
        sn_mva (float, optional): Apparent power rating.
        type (str, optional): Connection type ("wye" or "delta").
        controllable (bool, optional): Flexible in OPF.

    ---
    Note:
        See pandapower 'load' for more details.
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
    Parameters for a storage unit in net['storage'].

    Params:
        bus (int): Bus index.
        p_mw (float): Active power. Positive = discharging.
        max_e_mwh (float): Maximum energy capacity in MWh.
        soc_percent (float): State of charge [%].
        min_e_mwh (float): Minimum allowed energy.
        q_mvar (float): Reactive power in MVAr.
        sn_mva (float): Apparent power rating.
        controllable (bool): Flexible in OPF.
        name (str, optional): Name.
        in_service (bool): Active status.
        type (str, optional): Connection type label.
        scaling (float, optional): Scaling factor.

    ---
    Note:
        See pandapower 'storage' for more details.
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
