"""Counterflow epsilon-NTU water baseline, with disclosed wet-contact approximation."""
from __future__ import annotations
from ht.hx import effectiveness_from_NTU
from .schema import validate_case
from .properties import air_state, air_mass_flow, fluid_pt, fluid_ph
from .thermal import contact_air, LIQUID_WATER_CP


def simulate_water(case: dict) -> dict:
    c = validate_case(case)
    if c["kind"] != "water":
        raise ValueError("Water model requires kind=water")
    if c["fluid"]["name"].lower() != "water":
        raise NotImplementedError("This first baseline supports pure Water only, not solutions")
    if c["model"]["air_arrangement"] != "counterflow":
        raise ValueError("Water baseline supports counterflow only")
    a, f = c["air"], c["fluid"]
    ain = air_state(a["t_db_c"], a["relative_humidity"], a["pressure_pa"])
    fin = fluid_ph(f["name"], f["pressure_pa"], f["inlet_h_j_kg"]) if "inlet_h_j_kg" in f else fluid_pt(f["name"], f["pressure_pa"], f["inlet_t_c"])
    if fin["cp_j_kg_k"] is None or fin["temperature_c"] <= 0:
        raise ValueError("Water baseline requires liquid inlet above 0 C; freezing is not modelled")
    from CoolProp.CoolProp import PhaseSI
    if PhaseSI("P", f["pressure_pa"], "H", fin["enthalpy_j_kg"], f["name"]) != "liquid":
        raise ValueError("Water baseline requires a liquid state")
    m_da, mf, ua = air_mass_flow(a), f["mass_flow_kg_s"], c["model"].get("ua_w_k", 0.)
    geometry_mode = c["model"]["ua_mode"] == "geometry"
    geometry_detail = None
    tin = fin["temperature_c"]
    wet = tin < ain["dew_point_c"] and tin < ain["t_db_c"]
    exposed_spec = c["model"].get("exposed_tubes") if geometry_mode else None
    if exposed_spec is not None and tin < ain["dew_point_c"]:
        raise ValueError("model.exposed_tubes is dry-only; water inlet is below the air dew point")
    exposed_detail = None; q_exposed = 0.0
    wet_model = c["model"].get("wet_surface_model", "contact_factor")
    wet_detail_strict = None; surface_condition = "wet_approximation" if wet else "dry"; drain_t = tin
    cp_water = fin["cp_j_kg_k"]
    old_t = tin; converged = False; mean_water_temperature = tin
    max_iter, tol = c["solver"]["max_iterations"], c["solver"]["tolerance_k"]
    for iteration in range(1, max_iter + 1):
        if geometry_mode:
            from .geometry_performance import water_geometry_performance
            geometry_detail = water_geometry_performance(c, mean_water_temperature)
            ua = geometry_detail["ua_w_k"]
        ca = m_da * ain["cp_j_kg_da_k"]
        ua_effective = ua
        if wet and wet_model == "contact_factor":
            sat = air_state(tin, 1.0, a["pressure_pa"])
            cp_air_effective = (ain["enthalpy_j_kg_da"] - sat["enthalpy_j_kg_da"]) / (ain["t_db_c"] - tin)
            ca = m_da * cp_air_effective
            # In geometry mode the known water/wall resistances must not be
            # spuriously multiplied by the air-side latent enhancement.
            ratio = cp_air_effective / ain["cp_j_kg_da_k"]
            if geometry_mode:
                from .geometry_performance import wet_geometry_conductance
                wet_detail = wet_geometry_conductance(geometry_detail, ratio)
                geometry_detail["wet_model"] = wet_detail
                ua_effective = wet_detail["effective_ua_w_k"]
            else:
                ua_effective = ua * ratio
        cw = mf * cp_water
        cmin, cmax = min(ca, cw), max(ca, cw)
        epsilon = effectiveness_from_NTU(ua_effective / cmin, cmin / cmax, "counterflow") if ua else 0.0
        fraction = epsilon * cmin / ca
        if wet and wet_model == "threlkeld_braun":
            aout, q_to_water, condensate, wet_detail_strict, surface_condition, drain_t = _strict_wet_coil(
                ain, m_da, tin, mf * cp_water, ua, geometry_detail)
            ua_effective = wet_detail_strict["overall_mass_conductance_kg_s"] * wet_detail_strict["saturation_slope_inner_j_kg_k"] \
                if wet_detail_strict and surface_condition == "wet" else ua
        elif fraction == 0:
            aout, q_to_water, condensate = dict(ain), 0.0, 0.0
        else:
            aout, q_to_water, condensate = contact_air(ain, tin, fraction, m_da)
        if exposed_spec is not None:
            exposed_detail = _lumped_exposed(exposed_spec, geometry_detail, ain, mean_water_temperature)
            q_exposed = exposed_detail["heat_to_water_w"]
        fout = fluid_ph(f["name"], f["pressure_pa"], fin["enthalpy_j_kg"] + (q_to_water + q_exposed) / mf)
        if fout["cp_j_kg_k"] is None:
            raise ValueError("Computed water outlet is not single phase")
        mean = fluid_pt(f["name"], f["pressure_pa"], (tin + fout["temperature_c"]) / 2)
        cp_water = mean["cp_j_kg_k"]
        mean_water_temperature = mean["temperature_c"]
        if abs(fout["temperature_c"] - old_t) <= tol:
            converged = True; break
        old_t = fout["temperature_c"]
    fout["mass_flow_kg_s"] = mf
    air_net = m_da * (ain["enthalpy_j_kg_da"] - aout["enthalpy_j_kg_da"]) - condensate * LIQUID_WATER_CP * drain_t
    fluid_heat = mf * (fout["enthalpy_j_kg"] - fin["enthalpy_j_kg"])
    warnings = [
        "水盘管采用整体逆流ε-NTU基线，恒定水压；segments参数不生成虚假的逐管结果。",
        ("当前压降仅作芯体/直管摩擦预测；流量分配、溶液物性和真实压力状态耦合未实现。" if geometry_mode else
         "当前未实现水侧/空气侧压降、实际几何UA、流量分配和溶液物性。"),
        "凝水焓采用0℃参考的4180*T近似，凝水排出温度取进水温度。",
    ]
    if wet and wet_model == "threlkeld_braun":
        from .wet_surface import MODEL_NOTE as _WET_NOTE
        warnings[2] = "凝水焓采用0℃参考的4180*T近似，凝水按有效表面温度排出。"
        warnings.append(_WET_NOTE + ("本工况判定为湿表面。" if surface_condition == "wet" else
                                     "本工况干工况换热量不低于全湿计算，按干表面计算。"))
        warnings.append("整盘按逆流集总：饱和焓曲线以割线斜率线性化，未逐管分段；空气压降仍为干表面摩擦。")
    elif wet:
        warnings.append("湿工况采用入口水温作为有效露点及热质传递类比的接触因子近似，不是严格部分湿翅片模型。")
        if geometry_mode:
            warnings.append("几何湿段只修改空气侧热阻/等效翅片效率；压降仍为干表面摩擦基线，未考虑水膜阻力。")
    if not converged:
        warnings.append("平均物性迭代未在给定次数内收敛。")
    if geometry_detail:
        warnings.extend(geometry_detail["warnings"])
    result = {
        "case_name": c["name"], "kind": "water", "model_version": "water-geometry-lumped-0.2" if geometry_mode else "water-eps-ntu-contact-0.1",
        "ua_w_k": ua, "effective_ua_w_k": ua_effective,
        "heat_transfer_w": abs(fluid_heat), "signed_air_to_fluid_w": fluid_heat,
        "air_in": ain, "air_out": aout, "fluid_in": fin, "fluid_out": fout,
        "dry_air_mass_flow_kg_s": m_da, "condensate_kg_s": condensate,
        "sensible_heat_w": abs(m_da * ain["cp_j_kg_da_k"] * (ain["t_db_c"] - aout["t_db_c"])),
        "energy_balance_relative_error": abs(fluid_heat - air_net - q_exposed) / max(abs(fluid_heat), 1.0),
        "iterations": iteration, "converged": converged, "warnings": warnings,
        "segments": [], "air_surface_condition": surface_condition,
        "numerical_controls": {"segments_requested": c["model"]["segments"],
                               "segments_applied": False, "water_model": "lumped"},
    }
    if geometry_detail:
        result["geometry_model"] = geometry_detail
    if wet_detail_strict is not None:
        result["wet_surface"] = {k: v for k, v in wet_detail_strict.items() if k != "air_out"}
    if wet_model != "contact_factor":
        result["wet_surface_model"] = wet_model
    if exposed_detail is not None:
        result["exposed_tubes"] = exposed_detail
        result["finned_core_heat_w"] = abs(fluid_heat - q_exposed)
        result["warnings"].append("外露光管/U弯按Churchill-Bernstein单管横掠、给定迎面风速和进风状态计算，"
                                  "整体模型按平均水温线性计入；其换热进入旁通气流，不并入芯体出风状态。")
    return result


def _strict_wet_coil(ain, m_da, tin, c_water, ua_dry, detail):
    """Whole-coil counterflow: larger of dry and fully wet (Braun et al. 1989)."""
    from ht import fin_efficiency_Kern_Kraus
    from .wet_surface import wet_element, dry_or_wet
    g, m = detail["geometry"], detail["metrics"]
    fe = lambda h: fin_efficiency_Kern_Kraus(m["collar_diameter_m"], m["equivalent_annular_fin_outer_diameter_m"],
                                             g["fin_thickness_m"], g["fin_conductivity_w_m_k"], h)
    wet = wet_element(ain, m_da, detail["air_h_w_m2_k"], m["total_outer_area_m2"], m["fin_area_m2"], fe, tin,
                      c_water, detail["resistance_water_k_w"] + detail["resistance_wall_k_w"], "counterflow")
    ca = m_da * ain["cp_j_kg_da_k"]; cmin, cmax = min(ca, c_water), max(ca, c_water)
    eps = effectiveness_from_NTU(ua_dry / cmin, cmin / cmax, "counterflow")
    try:
        dry = contact_air(ain, tin, eps * cmin / ca, m_da, wet=False)
    except ValueError:
        dry = None   # dry analysis would supersaturate the outlet: not admissible
    choice = dry_or_wet(dry[1] if dry else None, wet)
    if choice == "wet":
        return wet["air_out"], wet["heat_to_fluid_w"], wet["condensate_kg_s"], wet, "wet", wet["effective_surface_t_c"]
    if dry is None:
        raise ValueError("Neither dry nor fully wet analysis is admissible for this coil state")
    return dry[0], dry[1], 0.0, wet, "dry", tin


def _lumped_exposed(spec, detail, air_in, water_t_c):
    from .exposed_tubes import exposed_lengths, outside_coefficient, element_conductance, MODEL_NOTE
    g, m = detail["geometry"], detail["metrics"]
    straight, bends = exposed_lengths(spec, m["tube_count"])
    length = straight + bends
    outside = outside_coefficient(spec, g["tube_outer_diameter_m"], air_in, water_t_c)
    # Every circuit carries its own bare elements; tube_count already includes all of them.
    ua = element_conductance(length, g["tube_outer_diameter_m"], g["tube_inner_diameter_m"],
                             g["tube_conductivity_w_m_k"], outside["h_w_m2_k"], detail["water_h_w_m2_k"])
    return {"specification": dict(spec), "straight_length_m": straight, "return_bend_length_m": bends,
            "outer_area_m2": 3.141592653589793 * g["tube_outer_diameter_m"] * length,
            "outside": outside, "ua_w_k": ua,
            "heat_to_water_w": ua * (air_in["t_db_c"] - water_t_c),
            "lumped_policy": "linear_at_mean_water_temperature", "model": MODEL_NOTE}


def solve_water_target(case: dict) -> dict:
    c = validate_case(case)
    if not c.get('target') or 'outlet_temperature_c' not in c['target']:
        raise ValueError('Water target requires outlet_temperature_c')
    from .inverse import solve_mass_flow
    return solve_mass_flow(c, 'outlet_temperature_c', lambda r: r['fluid_out']['temperature_c'],
                           simulate_water, xtol=1e-10)
