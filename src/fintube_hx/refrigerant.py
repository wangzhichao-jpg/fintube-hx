"""Constant-pressure P/h finite-volume baseline with controlled air/fluid coupling."""
from __future__ import annotations
from copy import deepcopy
import math
from scipy.optimize import brentq
from .schema import validate_case
from .properties import air_state, air_mass_flow, fluid_pt, fluid_ph, saturation
from .thermal import contact_air, LIQUID_WATER_CP


def _cell(name, p, h_in, air_in, m_ref, m_da, ua, direction):
    fin = fluid_ph(name, p, h_in)
    t_ref = fin["temperature_c"]
    if direction * (air_in["t_db_c"] - t_ref) <= 1e-9 or ua == 0:
        return fin, dict(air_in), 0.0, 0.0, t_ref, False
    if direction == 1 and t_ref <= 0:
        raise ValueError("Evaporating below/equal 0 C requires frost treatment, absent in this baseline")
    fraction = -math.expm1(-ua / (m_da * air_in["cp_j_kg_da_k"]))
    # Finite endpoint bounds prevent crossing the local inlet temperatures.
    eq_t = air_in["t_db_c"] - direction * 1e-5
    eq = fluid_pt(name, p, eq_t)
    fluid_limit = direction * m_ref * (eq["enthalpy_j_kg"] - h_in)
    _, air_heat_limit, _ = contact_air(air_in, t_ref, 1.0, m_da)
    upper = min(fluid_limit, direction * air_heat_limit)
    if upper <= 1e-8:
        return fin, dict(air_in), 0.0, 0.0, t_ref, False
    def evaluate(q):
        out = fluid_ph(name, p, h_in + direction * q / m_ref)
        surface_t = (t_ref + out["temperature_c"]) / 2
        air_out, air_heat, cond = contact_air(air_in, surface_t, fraction, m_da)
        return out, air_out, direction * air_heat, cond, surface_t
    residual = lambda q: evaluate(q)[2] - q
    limited = residual(upper) > 0
    q = upper if limited else brentq(residual, 0.0, upper, xtol=1e-7, maxiter=60)
    fout, aout, _, cond, surface_t = evaluate(q)
    if limited:
        # Capacity bound means the requested contact factor is too strong.
        frac = brentq(lambda f: direction * contact_air(air_in, surface_t, f, m_da)[1] - q,
                      0.0, fraction, xtol=1e-12)
        aout, _, cond = contact_air(air_in, surface_t, frac, m_da)
    return fout, aout, q, cond, surface_t, limited


def simulate_refrigerant(case: dict) -> dict:
    c = validate_case(case)
    if c["kind"] not in ("evaporator", "condenser"):
        raise ValueError("Refrigerant model requires evaporator or condenser")
    a, f, model = c["air"], c["fluid"], c["model"]
    ain = air_state(a["t_db_c"], a["relative_humidity"], a["pressure_pa"])
    fin = fluid_ph(f["name"], f["pressure_pa"], f["inlet_h_j_kg"]) if "inlet_h_j_kg" in f else fluid_pt(f["name"], f["pressure_pa"], f["inlet_t_c"])
    direction = 1 if c["kind"] == "evaporator" else -1
    if direction * (ain["t_db_c"] - fin["temperature_c"]) <= 0 and model["ua_w_k"] > 0:
        raise ValueError("Inlet temperatures do not support the selected evaporator/condenser role")
    n = model["segments"]
    m_da, m_ref = air_mass_flow(a), f["mass_flow_kg_s"]
    # Counterflow: fluid index 0..n; air enters at n and leaves at 0.
    air_grid = [dict(ain) for _ in range(n + 1)]
    tol, max_iter = c["solver"]["tolerance_k"], c["solver"]["max_iterations"]
    converged = False
    for iteration in range(1, max_iter + 1):
        old_grid = deepcopy(air_grid)
        h = fin["enthalpy_j_kg"]
        cells = []; condensate = 0.0; drain_heat = 0.0; bound_count = 0
        for i in range(n):
            local_air = air_grid[i + 1]
            f_out, a_out, q, cond, ts, limited = _cell(
                f["name"], f["pressure_pa"], h, local_air, m_ref, m_da,
                model["ua_w_k"] / n, direction)
            cells.append({
                "index": i, "fluid_in_h_j_kg": h,
                "fluid_out_h_j_kg": f_out["enthalpy_j_kg"],
                "fluid_in_t_c": fluid_ph(f["name"], f["pressure_pa"], h)["temperature_c"],
                "fluid_out_t_c": f_out["temperature_c"], "fluid_out_quality": f_out["quality"],
                "air_in_t_c": local_air["t_db_c"], "air_out_t_c": a_out["t_db_c"],
                "air_out_humidity_ratio_kg_kg_da": a_out["humidity_ratio_kg_kg_da"],
                "heat_transfer_w": q, "condensate_kg_s": cond,
                "approximate_surface_t_c": ts,
            })
            h = f_out["enthalpy_j_kg"]
            air_grid[i] = a_out
            condensate += cond; drain_heat += cond * LIQUID_WATER_CP * ts
            bound_count += int(limited)
        delta = max(max(abs(new["t_db_c"] - old["t_db_c"]),
                        1000 * abs(new["humidity_ratio_kg_kg_da"] - old["humidity_ratio_kg_kg_da"]))
                    for new, old in zip(air_grid, old_grid))
        if delta <= tol:
            converged = True; break
    aout = air_grid[0]
    fout = fluid_ph(f["name"], f["pressure_pa"], h)
    fout["mass_flow_kg_s"] = m_ref
    fluid_heat = m_ref * (fout["enthalpy_j_kg"] - fin["enthalpy_j_kg"])
    air_net = m_da * (ain["enthalpy_j_kg_da"] - aout["enthalpy_j_kg_da"]) - drain_heat
    balance = abs(fluid_heat - air_net) / max(abs(fluid_heat), 1.0)
    mass_cond = m_da * (ain["humidity_ratio_kg_kg_da"] - aout["humidity_ratio_kg_kg_da"])
    warnings = [
        "制冷剂采用恒压压力-焓轴向分段基线及逆流空气迭代；分段不等于实际逐管流路。",
        "每段总UA由输入平均分配，不包含空气/管内关联式或强化管几何。",
        "有效表面温度取段内制冷剂温度均值，湿段使用接触因子近似；未实现严格部分湿翅片。",
        "凝水焓按4180*T、凝水温度取有效表面温度；低温结霜、局部压降与支路分配未实现。",
    ]
    if bound_count:
        warnings.append(f"{bound_count}个分段触及温差容量界限，接触因子受到物理容量截断。")
    if not converged:
        warnings.append("空气-制冷剂逆流迭代未在给定次数内收敛。")
    if balance > 0.005:
        converged = False; warnings.append("整体能量残差超过0.5%，结果不得作为通过验算。")
    result = {
        "case_name": c["name"], "kind": c["kind"], "model_version": "constant-p-ph-segments-0.1",
        "heat_transfer_w": abs(fluid_heat), "signed_air_to_fluid_w": fluid_heat,
        "air_in": ain, "air_out": aout, "fluid_in": fin, "fluid_out": fout,
        "dry_air_mass_flow_kg_s": m_da, "condensate_kg_s": condensate,
        "condensate_mass_balance_error_kg_s": abs(condensate - mass_cond),
        "condensate_enthalpy_rate_w": drain_heat,
        "sensible_heat_w": abs(m_da * ain["cp_j_kg_da_k"] * (ain["t_db_c"] - aout["t_db_c"])),
        "energy_balance_relative_error": balance, "iterations": iteration,
        "converged": converged, "warnings": warnings, "segments": cells,
    }
    vapor_sat = saturation(f["name"], f["pressure_pa"], 1.0)
    liquid_sat = saturation(f["name"], f["pressure_pa"], 0.0)
    # Signed thermal margins; negative values indicate the target single-phase state is not reached.
    result["outlet_superheat_k"] = fout["temperature_c"] - vapor_sat["temperature_c"]
    result["outlet_subcooling_k"] = liquid_sat["temperature_c"] - fout["temperature_c"]
    return result


def solve_refrigerant_target(case: dict) -> dict:
    c = validate_case(case)
    key = 'superheat_k' if c['kind'] == 'evaporator' else 'subcooling_k'
    if not c.get('target') or key not in c['target']:
        raise ValueError(f'Target requires {key}')
    from .inverse import solve_mass_flow
    return solve_mass_flow(c, key, lambda r: r['outlet_' + key], simulate_refrigerant)
