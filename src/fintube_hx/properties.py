"""CoolProp-backed SI state functions; psychrometric enthalpy is per kg dry air."""
from __future__ import annotations
import math
from functools import lru_cache
from threading import local
from CoolProp.CoolProp import PropsSI, PhaseSI
from CoolProp.HumidAirProp import HAPropsSI


def _finite(value: float, label: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{label} is not finite")
    return value


@lru_cache(maxsize=16000)
def _cached_air_state(t_db_c: float, rh: float, p_pa: float = 101325.0) -> dict:
    t_db_c, rh, p_pa = map(float, (t_db_c, rh, p_pa))
    if not (0.0 <= rh <= 1.0) or p_pa <= 0:
        raise ValueError("Air RH must be 0..1 and absolute pressure positive")
    t = t_db_c + 273.15
    args = ("T", t, "P", p_pa, "R", rh)
    data = {
        "t_db_c": t_db_c,
        "relative_humidity": rh,
        "pressure_pa": p_pa,
        "humidity_ratio_kg_kg_da": HAPropsSI("W", *args),
        "enthalpy_j_kg_da": HAPropsSI("H", *args),
        "specific_volume_m3_kg_da": HAPropsSI("V", *args),
        "cp_j_kg_da_k": HAPropsSI("C", *args),
        "dew_point_c": HAPropsSI("D", *args) - 273.15,
    }
    return {key: _finite(value, key) for key, value in data.items()}


def air_state(t_db_c: float, rh: float, p_pa: float = 101325.0) -> dict:
    # Never expose mutable cache entries to callers.
    return dict(_cached_air_state(float(t_db_c), float(rh), float(p_pa)))


def air_from_h_w(h_j_kg_da: float, w: float, p_pa: float = 101325.0) -> dict:
    if w < 0 or p_pa <= 0:
        raise ValueError("Humidity ratio must be nonnegative and pressure positive")
    t = HAPropsSI("T", "H", float(h_j_kg_da), "W", float(w), "P", float(p_pa))
    try:
        rh = HAPropsSI("R", "T", t, "W", float(w), "P", float(p_pa))
    except ValueError as exc:
        # CoolProp can reject RH=1+roundoff before returning the value.
        # Only accept a numerical saturation-boundary match, not real supersaturation.
        sat_w = HAPropsSI("W", "T", t, "R", 1.0, "P", float(p_pa))
        if not math.isclose(float(w), sat_w, rel_tol=5e-7, abs_tol=1e-10):
            raise ValueError("Supersaturated or invalid air state; condensation model must resolve it") from exc
        rh = 1.0
    if rh > 1.0 + 1e-6:
        raise ValueError("Supersaturated air state; condensation model must resolve it")
    return dict(air_state(t - 273.15, min(1.0, max(0.0, rh)), p_pa))


def air_mass_flow(air: dict) -> float:
    state = air_state(air["t_db_c"], air["relative_humidity"], air.get("pressure_pa", 101325.0))
    return float(air["volume_flow_m3_h"]) / 3600.0 / state["specific_volume_m3_kg_da"]


@lru_cache(maxsize=256)
def fluid_available(name: str) -> bool:
    """True when CoolProp's HEOS backend can build the fluid (pure, predefined pseudo-pure blend or '&' mixture)."""
    import CoolProp.CoolProp as CP
    try:
        CP.AbstractState("HEOS", name)
    except ValueError:
        return False
    return True


_STATE_LOCAL = local()


def _abstract_state(name: str):
    # Mutable CoolProp states must not be shared between Python threads.
    # One HEOS flash yields T/Q/rho/cp together, instead of four PropsSI flashes.
    import CoolProp.CoolProp as CP
    if not hasattr(_STATE_LOCAL, 'states'):
        _STATE_LOCAL.states = {}
    state = _STATE_LOCAL.states.get(name)
    if state is None:
        state = _STATE_LOCAL.states[name] = CP.AbstractState("HEOS", name)
    return state


@lru_cache(maxsize=32000)
def _fluid_state(name: str, pressure_pa: float, enthalpy_j_kg: float) -> dict:
    import CoolProp.CoolProp as CP
    p, h = float(pressure_pa), float(enthalpy_j_kg)
    state = _abstract_state(name)
    state.update(CP.HmassP_INPUTS, h, p)
    t, q, rho = state.T(), state.Q(), state.rhomass()
    # Two-phase cp is not a meaningful finite heat-capacity input.
    cp = None if 0 <= q <= 1 else _finite(state.cpmass(), "fluid cp")
    return {
        "name": name,
        "temperature_c": _finite(t - 273.15, "fluid temperature"),
        "pressure_pa": _finite(p, "fluid pressure"),
        "enthalpy_j_kg": _finite(h, "fluid enthalpy"),
        "density_kg_m3": _finite(rho, "fluid density"),
        "cp_j_kg_k": cp,
        "quality": _finite(q, "fluid quality"),
    }


def fluid_pt(name: str, pressure_pa: float, temperature_c: float) -> dict:
    p, t = float(pressure_pa), float(temperature_c) + 273.15
    if p <= 0:
        raise ValueError("Fluid absolute pressure must be positive")
    try:
        phase = PhaseSI("P", p, "T", t, name)
        if phase in ("twophase", "unknown"):
            raise ValueError("A two-phase P/T pair does not uniquely specify enthalpy")
        h = PropsSI("H", "P", p, "T", t, name)
        return dict(_fluid_state(name, p, h))
    except ValueError as exc:
        raise ValueError(f"Cannot define {name} from P/T; provide a reliable inlet enthalpy: {exc}") from exc


def fluid_ph(name: str, pressure_pa: float, enthalpy_j_kg: float) -> dict:
    if pressure_pa <= 0:
        raise ValueError("Fluid absolute pressure must be positive")
    return dict(_fluid_state(name, float(pressure_pa), float(enthalpy_j_kg)))


def saturation(name: str, pressure_pa: float, quality: float) -> dict:
    if not 0 <= quality <= 1:
        raise ValueError("Saturation quality must be 0..1")
    h = PropsSI("H", "P", float(pressure_pa), "Q", float(quality), name)
    return dict(_fluid_state(name, float(pressure_pa), h))
