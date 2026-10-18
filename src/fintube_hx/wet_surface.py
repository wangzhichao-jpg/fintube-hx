"""Wet-surface heat and mass transfer for one finned element (optional model).

Method (original implementation of published equations):

* Enthalpy-potential effectiveness of Braun, Klein & Mitchell (1989), "Effectiveness
  models for cooling towers and cooling coils", ASHRAE Trans. 95(2):164-174. The air
  stream is treated as an enthalpy stream (capacity m_da) and the coolant as an
  equivalent stream of capacity C_f/b_r, where b_r is the secant slope of the
  saturated-air enthalpy curve between coolant and tube-base temperatures.
* Overall wet conductance in the form used by Wang, Hsieh & Lin (1997) after
  Threlkeld (1970), with the condensate-film resistance neglected:
      1/UA* = b_r*R_inner + cp_a / (h_c*(A_p*b_wm/b_wp + eta_f,wet*A_f))
* Wet fin efficiency (Threlkeld): the dry fin-efficiency function evaluated with
  h_ow = h_c*b_wm/cp_a, b_wm being the saturation-curve slope at the mean
  fin-surface (water-film) temperature.
* Outlet humidity from the effective-surface construction of Braun et al. (1989):
      i_s,eff = i_in - (i_in-i_out)/(1-exp(-NTU_o)),  w_out = w_s,eff + (w_in-w_s,eff)exp(-NTU_o)

Disclosed assumptions: Lewis number 1 (h_m = h_c/cp_a); the dry convective
coefficient is applied to the wet surface (no wet-surface j correlation); uniform
wetting within the element; partially wet elements take the larger of the dry and
the fully wet heat rate (Braun et al. 1989 rule); condensate drains at the effective
surface temperature carrying 4180*T J/kg; no frost (surface must stay above 0 C).
"""
from __future__ import annotations
import math
from scipy.optimize import brentq
from ht.hx import effectiveness_from_NTU
from .properties import air_state
from .thermal import air_with_h_w, LIQUID_WATER_CP

MODEL_ID = "threlkeld_braun"
MODEL_NOTE = ("湿表面：Braun-Klein-Mitchell(1989)焓势ε-NTU + Threlkeld湿翅片效率；Le=1，湿表面沿用干表面换热系数，"
              "忽略水膜热阻；单元内按全湿计算，与干工况取换热量较大者；不含结霜。")


def saturated_enthalpy(t_c: float, p_pa: float) -> float:
    return air_state(t_c, 1.0, p_pa)["enthalpy_j_kg_da"]


def saturation_slope(t1_c: float, t2_c: float, p_pa: float) -> float:
    """Secant slope di_s/dT [J/(kg_da K)] of saturated air between two temperatures."""
    if abs(t1_c - t2_c) < 0.02:
        tm = 0.5 * (t1_c + t2_c)
        return (saturated_enthalpy(tm + 0.05, p_pa) - saturated_enthalpy(tm - 0.05, p_pa)) / 0.1
    return (saturated_enthalpy(t1_c, p_pa) - saturated_enthalpy(t2_c, p_pa)) / (t1_c - t2_c)


def saturation_temperature(i_j_kg_da: float, p_pa: float) -> float:
    return brentq(lambda t: saturated_enthalpy(t, p_pa) - i_j_kg_da, -40.0, 90.0, xtol=1e-10)


class _SaturationCurve:
    """Chebyshev interpolant of CoolProp saturated-air enthalpy on one element's temperature
    span (degree 8 up to a 40 K span, else 16); relative error < 2e-7 for spans up to 60 K."""

    def __init__(self, p_pa: float, t_lo: float, t_hi: float):
        from CoolProp.HumidAirProp import HAPropsSI
        import numpy as np
        self.lo, self.hi = t_lo, t_hi
        n = 9 if t_hi - t_lo <= 40 else (17 if t_hi - t_lo <= 60 else 33)
        k = np.arange(n)
        x = np.cos((2 * k + 1) * np.pi / (2 * n))
        t = 0.5 * (t_lo + t_hi) + 0.5 * (t_hi - t_lo) * x
        i = [HAPropsSI("H", "T", tc + 273.15, "P", p_pa, "R", 1.0) for tc in t]
        self.c = np.polynomial.chebyshev.chebfit(x, i, n - 1)
        self.d = np.polynomial.chebyshev.chebder(self.c)
        self._val = np.polynomial.chebyshev.chebval

    def _x(self, t):
        return (2 * t - self.lo - self.hi) / (self.hi - self.lo)

    def i(self, t):
        return float(self._val(self._x(t), self.c))

    def slope(self, t):
        return float(self._val(self._x(t), self.d)) * 2 / (self.hi - self.lo)

    def secant(self, t1, t2):
        return self.slope(0.5 * (t1 + t2)) if abs(t1 - t2) < 0.02 else (self.i(t1) - self.i(t2)) / (t1 - t2)

    def t_of(self, i_target):
        t = 0.5 * (self.lo + self.hi)
        for _ in range(50):
            step = (self.i(t) - i_target) / self.slope(t)
            t -= step
            if abs(step) < 1e-10:
                return t
        raise ValueError("Saturation-curve inversion did not converge")


def wet_element(air_in: dict, m_da: float, h_c: float, area_outer_m2: float, area_fin_m2: float,
                fin_efficiency, fluid_in_t_c: float, fluid_capacity_w_k: float | None,
                inner_resistance_k_w: float, arrangement: str = "counterflow",
                conductance_multiplier: float = 1.0, max_iterations: int = 200) -> dict | None:
    """Fully wet element.  Returns None when the fully wet analysis is not admissible
    (effective surface at/above the inlet dew point, or no enthalpy potential)."""
    p = air_in["pressure_pa"]; cp_a = air_in["cp_j_kg_da_k"]
    i_in, w_in = air_in["enthalpy_j_kg_da"], air_in["humidity_ratio_kg_kg_da"]
    if not (m_da > 0 and h_c > 0 and area_outer_m2 > 0 and 0 <= area_fin_m2 < area_outer_m2):
        raise ValueError("Wet element requires positive air flow, coefficient and areas")
    if fluid_in_t_c <= 0:
        raise ValueError("Wet surface at/below 0 C requires a frost model, absent here")
    if air_in["dew_point_c"] <= fluid_in_t_c:
        return None
    sat = _SaturationCurve(p, fluid_in_t_c - 0.5, air_in["t_db_c"] + 0.5)
    i_r = sat.i(fluid_in_t_c)
    if i_in - i_r <= 1e-9:
        return None
    a_p = area_outer_m2 - area_fin_m2
    t_b = fluid_in_t_c + 0.3 * (air_in["dew_point_c"] - fluid_in_t_c)
    t_wm = t_b; q_air = 0.0; converged = False
    for iteration in range(1, max_iterations + 1):
        b_wm = sat.slope(t_wm)
        b_wp = sat.slope(t_b)
        h_ow = h_c * b_wm / cp_a
        eta_f = fin_efficiency(h_ow)
        k_air = h_c * (a_p * b_wm / b_wp + eta_f * area_fin_m2) / cp_a          # kg/s
        t_fm = fluid_in_t_c if fluid_capacity_w_k is None else fluid_in_t_c + 0.5 * q_air / fluid_capacity_w_k
        b_r = sat.secant(t_b, t_fm)
        ua_star = conductance_multiplier / (1.0 / k_air + b_r * inner_resistance_k_w)
        c_air = m_da
        c_fluid = math.inf if fluid_capacity_w_k is None else fluid_capacity_w_k / b_r
        c_min, c_max = min(c_air, c_fluid), max(c_air, c_fluid)
        cr = 0.0 if math.isinf(c_max) else c_min / c_max
        ntu = ua_star / c_min
        eps = -math.expm1(-ntu) if cr == 0.0 else effectiveness_from_NTU(ntu, cr, arrangement)
        q_new = eps * c_min * (i_in - i_r)
        i_out = i_in - q_new / m_da
        # Tube-base temperature from the inner-side resistance.
        t_fm = fluid_in_t_c if fluid_capacity_w_k is None else fluid_in_t_c + 0.5 * q_new / fluid_capacity_w_k
        t_b_new = t_fm + q_new * inner_resistance_k_w / conductance_multiplier
        i_am = 0.5 * (i_in + i_out)
        i_wm = i_am - eta_f * (i_am - sat.i(t_b_new))
        t_wm_new = sat.t_of(i_wm)
        change = max(abs(t_b_new - t_b), abs(t_wm_new - t_wm), abs(q_new - q_air) / max(q_new, 1.0))
        t_b, t_wm, q_air = t_b_new, t_wm_new, q_new
        if change < 1e-9:
            converged = True; break
    if not converged:
        raise ValueError("Wet-element iteration did not converge")
    ntu_o = k_air * conductance_multiplier / m_da
    decay = math.exp(-ntu_o)
    i_s_eff = i_in - (i_in - i_out) / (1.0 - decay)
    t_s_eff = sat.t_of(i_s_eff)
    if t_s_eff >= air_in["dew_point_c"]:
        return None
    if t_s_eff <= 0 or t_b <= 0:
        raise ValueError("Wet surface at/below 0 C requires a frost model, absent here")
    w_s_eff = air_state(t_s_eff, 1.0, p)["humidity_ratio_kg_kg_da"]
    w_out = w_s_eff + (w_in - w_s_eff) * decay
    air_out = air_with_h_w(i_out, w_out, p)
    condensate = max(0.0, m_da * (w_in - air_out["humidity_ratio_kg_kg_da"]))
    drain_w = condensate * LIQUID_WATER_CP * t_s_eff
    return {"model": MODEL_ID, "air_out": air_out, "air_enthalpy_drop_w": m_da * (i_in - air_out["enthalpy_j_kg_da"]),
            "heat_to_fluid_w": m_da * (i_in - air_out["enthalpy_j_kg_da"]) - drain_w,
            "condensate_kg_s": condensate, "condensate_enthalpy_rate_w": drain_w,
            "effective_surface_t_c": t_s_eff, "tube_base_t_c": t_b, "fin_mean_surface_t_c": t_wm,
            "wet_fin_efficiency": eta_f, "wet_equivalent_h_w_m2_k": h_ow,
            "saturation_slope_fin_j_kg_k": b_wm, "saturation_slope_base_j_kg_k": b_wp,
            "saturation_slope_inner_j_kg_k": b_r, "air_side_mass_conductance_kg_s": k_air * conductance_multiplier,
            "overall_mass_conductance_kg_s": ua_star, "ntu_enthalpy": ntu, "effectiveness": eps,
            "air_side_ntu": ntu_o, "iterations": iteration}


def dry_or_wet(dry_heat_to_fluid_w: float | None, wet: dict | None) -> str:
    """Braun et al. (1989) rule: the larger of the dry and fully wet heat rates."""
    if wet is None:
        return "dry"
    if dry_heat_to_fluid_w is None:
        return "wet"
    return "wet" if wet["heat_to_fluid_w"] > dry_heat_to_fluid_w else "dry"
