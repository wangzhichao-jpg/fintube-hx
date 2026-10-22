"""Air-side contact approximation, with condensate enthalpy relative to 0 C."""
from __future__ import annotations
from scipy.optimize import brentq
from .properties import air_state, air_from_h_w, air_wh, air_from_h_w_wh

LIQUID_WATER_CP = 4180.0  # J/kg/K; disclosed prototype condensate approximation


def air_with_h_w(h: float, w: float, p: float) -> dict:
    """Resolve a supersaturated mixture onto saturation at constant enthalpy.

    This is a disclosed equilibrium-fog approximation, not a wet-fin correlation.
    """
    try:
        return air_from_h_w(h, w, p)
    except ValueError:
        from CoolProp.CoolProp import PropsSI
        # Stay below the boiling point and humid-air mole-fraction validity limit.
        upper_t = min(80.0, PropsSI("T", "P", p * 0.5, "Q", 0, "Water") - 273.15)
        t = brentq(lambda tc: air_state(tc, 1.0, p)["enthalpy_j_kg_da"] - h, -40, upper_t)
        saturated = air_state(t, 1.0, p)
        if saturated["humidity_ratio_kg_kg_da"] > w + 1e-8:
            raise ValueError("Unable to create physically admissible air outlet")
        return saturated


def air_with_h_w_wh(h: float, w: float, p: float) -> tuple[float, float]:
    """(humidity ratio, enthalpy) of air_with_h_w(h, w, p), bit-identical (0.1.0.dev17)."""
    try:
        return air_from_h_w_wh(h, w, p)
    except ValueError:
        s = air_with_h_w(h, w, p)          # rare fog path: the full routine, same result by construction
        return s["humidity_ratio_kg_kg_da"], s["enthalpy_j_kg_da"]


def contact_air(air_in: dict, surface_t_c: float, fraction: float, m_da: float,
                wet: bool | None = None, outlet_state: bool = True, wh_only: bool = False) -> tuple[dict, float, float]:
    """Interpolate towards a cold saturated surface or dry sensible surface.

    Return outlet, positive heat from air to fluid, condensate mass rate.
    Condensate is assumed to drain at surface temperature and carry cp*T.

    ``wh_only`` (0.1.0.dev17): the outlet is returned as {humidity ratio, enthalpy} only; heat and
    condensate are bit-identical to the full call.  ``outlet_state=False`` returns no outlet: the wet
    branch is then bit-identical as well (it skips only unused state properties), the dry branch keeps
    its historical shortcut q = m_da*(h_in - h_out) without the outlet flash.
    """
    if wh_only or not outlet_state:
        return _contact_air_wh(air_in, surface_t_c, fraction, m_da, wet, outlet_state)
    fraction = min(1.0, max(0.0, fraction))
    p = air_in["pressure_pa"]
    w_in, h_in = air_in["humidity_ratio_kg_kg_da"], air_in["enthalpy_j_kg_da"]
    if wet is None:
        wet = surface_t_c < air_in["dew_point_c"]
    if wet and surface_t_c >= air_in["dew_point_c"]:
        raise ValueError("Wet contact requested above the air dew point")
    if wet:
        surface = air_state(surface_t_c, 1.0, p)
        w = w_in + fraction * (surface["humidity_ratio_kg_kg_da"] - w_in)
        h = h_in + fraction * (surface["enthalpy_j_kg_da"] - h_in)
        out = dict(surface) if fraction == 1.0 else air_with_h_w(h, w, p)
        condensate = max(0.0, m_da * (w_in - out["humidity_ratio_kg_kg_da"]))
        q = m_da * (h_in - out["enthalpy_j_kg_da"]) - condensate * LIQUID_WATER_CP * surface_t_c
    else:
        # Sensible exchange uses humid-air enthalpy at fixed humidity ratio.
        from CoolProp.HumidAirProp import HAPropsSI
        h_surface = HAPropsSI("H", "T", surface_t_c + 273.15, "W", w_in, "P", p)
        h_out = h_in + fraction * (h_surface - h_in)
        if not outlet_state:
            # Identical heat; skips the outlet-state flash for root-finding residuals.
            return None, m_da * (h_in - h_out), 0.0
        out = air_from_h_w(h_out, w_in, p)
        q, condensate = m_da * (h_in - out["enthalpy_j_kg_da"]), 0.0
    return out, q, condensate


def _contact_air_wh(air_in, surface_t_c, fraction, m_da, wet, outlet_state):
    """Same arithmetic as contact_air, with only the humidity ratio and enthalpy of each state evaluated."""
    fraction = min(1.0, max(0.0, fraction))
    p = air_in["pressure_pa"]
    w_in, h_in = air_in["humidity_ratio_kg_kg_da"], air_in["enthalpy_j_kg_da"]
    if wet is None:
        wet = surface_t_c < air_in["dew_point_c"]
    if wet and surface_t_c >= air_in["dew_point_c"]:
        raise ValueError("Wet contact requested above the air dew point")
    if wet:
        ws, hs = air_wh(surface_t_c, 1.0, p)
        w = w_in + fraction * (ws - w_in)
        h = h_in + fraction * (hs - h_in)
        w_out, h_out = (ws, hs) if fraction == 1.0 else air_with_h_w_wh(h, w, p)
        condensate = max(0.0, m_da * (w_in - w_out))
        q = m_da * (h_in - h_out) - condensate * LIQUID_WATER_CP * surface_t_c
    else:
        from CoolProp.HumidAirProp import HAPropsSI
        h_surface = HAPropsSI("H", "T", surface_t_c + 273.15, "W", w_in, "P", p)
        h_out = h_in + fraction * (h_surface - h_in)
        if not outlet_state:
            return None, m_da * (h_in - h_out), 0.0
        w_out, h_out = air_from_h_w_wh(h_out, w_in, p)
        q, condensate = m_da * (h_in - h_out), 0.0
    if not outlet_state:
        return None, q, condensate
    return {"humidity_ratio_kg_kg_da": w_out, "enthalpy_j_kg_da": h_out}, q, condensate


SUBZERO_MODES = ('reject', 'dry_only', 'initial_frost')


def check_subzero_surface(surface_t_c: float, air_in: dict, mode: str = 'reject') -> bool:
    """Evaporating surfaces at/below 0 C (model.subzero_evaporation).

    'reject' (default, legacy): any surface at/below 0 C raises.
    'dry_only': allowed only while the surface stays at/above the local air frost point
    (CoolProp humid-air saturation is over ice below 0 C), i.e. no deposition; otherwise
    a frost model would be required and the case is rejected.  Returns True for a dry
    sub-zero surface.  The refrigerant-side temperature is used as the surface temperature,
    which is conservative for this check (the actual fin surface is warmer).
    """
    if surface_t_c > 0:
        return False
    if mode == 'initial_frost':
        return True          # deposition handled by the caller's strict wet-surface model (clean-surface limit)
    if mode != 'dry_only':
        raise ValueError('Evaporating surface at/below 0 C requires a frost model, absent here '
                         '(model.subzero_evaporation="dry_only" allows dry sub-zero surfaces only)')
    if surface_t_c < air_in['dew_point_c']:
        raise ValueError(f'Surface {surface_t_c:.2f} C is below the air frost point {air_in["dew_point_c"]:.2f} C: '
                         'frost deposition requires a frost model, absent here')
    return True


ICE_FUSION_J_KG = 333.4e3       # latent heat of fusion at 0 C
ICE_CP_J_KG_K = 2050.0


def condensate_enthalpy_rate(mass_kg_s: float, surface_t_c: float) -> float:
    """Enthalpy flow of removed water, 0 C liquid reference.  Liquid above 0 C uses the legacy
    expression m*4180*T unchanged; at or below 0 C the deposit is ice (-333.4 kJ/kg + 2050*T)."""
    if surface_t_c > 0:
        return mass_kg_s * LIQUID_WATER_CP * surface_t_c
    return mass_kg_s * (-ICE_FUSION_J_KG + ICE_CP_J_KG_K * surface_t_c)
