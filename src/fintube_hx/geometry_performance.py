"""Geometry-derived dry conductance and separately reported core friction losses.

No actual tube routing, branch-pressure distribution or pressure-state coupling.
Continuous fins use an explicitly disclosed equal-area annular efficiency proxy.
"""
from __future__ import annotations
import math
from CoolProp.CoolProp import PropsSI,PhaseSI
from CoolProp.HumidAirProp import HAPropsSI
from ht.conv_internal import laminar_entry_thermal_Hausen,turbulent_Gnielinski
from fluids.friction import friction_factor
from .geometry import validate_geometry,geometry_metrics
from .properties import air_state,air_mass_flow
from .airside import air_side_factors, fin_efficiency, fin_efficiency_method


def inner_series_extra(detail: dict) -> float:
    """Optional contact + inner fouling resistance (0.0 when not supplied)."""
    return detail.get('resistance_contact_k_w',0.)+detail.get('resistance_inner_fouling_k_w',0.)


def wet_geometry_conductance(detail: dict, heat_capacity_ratio: float) -> dict:
    """Wet heat/mass analogy modifies only the air resistance, not the water film."""
    if not math.isfinite(heat_capacity_ratio) or heat_capacity_ratio<=0:
        raise ValueError('Invalid wet equivalent-air heat-capacity ratio')
    g,m=detail['geometry'],detail['metrics']
    h=detail['air_h_w_m2_k']*heat_capacity_ratio
    eta=fin_efficiency(g,m,h)
    eta_surface=1-m['fin_area_m2']/m['total_outer_area_m2']*(1-eta)
    ra=1/(h*eta_surface*m['total_outer_area_m2'])
    ua=1/(ra+detail['resistance_water_k_w']+detail['resistance_wall_k_w']+inner_series_extra(detail))
    return {'effective_ua_w_k':ua,'effective_air_h_w_m2_k':h,'wet_fin_efficiency_proxy':eta,
            'wet_surface_efficiency_proxy':eta_surface,'wet_air_resistance_k_w':ra,
            'model':'air_resistance_only_heat_mass_analogy_not_rigorous_partial_wet'}


def air_pressure_v1(detail: dict, case: dict, air_in: dict, air_out: dict, wet_fraction: float,
                    condensate_kg_s: float, drain_t_c: float) -> dict:
    """v1 air-side breakdown for the lumped geometry coil (spec A1-A4); see fintube_hx.airside_pressure."""
    from .airside import wet_friction_factor
    from .airside_pressure import acceleration_pa, friction_pa, breakdown
    g,m=detail['geometry'],detail['metrics']
    m_da=air_mass_flow(case['air']);w_in=air_in['humidity_ratio_kg_kg_da']
    G=m_da*(1+w_in)/m['minimum_air_area_m2']
    rho_in=(1+w_in)/air_in['specific_volume_m3_kg_da']
    rho_out=(1+air_out['humidity_ratio_kg_kg_da'])/air_out['specific_volume_m3_kg_da']
    core=detail['air_core_friction_pressure_drop_pa']
    acc=acceleration_pa(G,rho_in,rho_out,m['free_area_ratio'])
    wet=None;inc=None;reason=None
    if wet_fraction>0:
        mu=PropsSI('VISCOSITY','T',drain_t_c+273.15,'P',101325.,'Water')
        wet=wet_friction_factor(g,m,detail['air_reynolds_collar'],condensate_kg_s,mu)
        if 'not_computed' in wet:
            reason=wet['not_computed']
        else:
            inc=wet_fraction*(friction_pa(wet['fanning_friction_factor'],m['air_depth_m'],m['air_hydraulic_diameter_m'],G,rho_in)-core)
    out=breakdown(fin_type=g['fin_type'],core_friction_pa=core,acceleration=acc,wet_fraction=wet_fraction,
                  wet_increment_pa=inc,wet_reason=reason)
    out['air_pressure_drop_pa']=core
    out['air_pressure_drop_basis'].update(mass_flux_kg_m2_s=G,inlet_density_kg_m3=rho_in,outlet_density_kg_m3=rho_out,
                                          contraction_ratio_sigma=m['free_area_ratio'])
    if wet is not None:
        out['air_wet_friction']=wet
    return out


def water_geometry_performance(case: dict, water_temperature_c: float) -> dict:
    g=validate_geometry(case['geometry']);metrics=geometry_metrics(g)
    if g['rows']>6:
        from .errors import ModelRangeError
        raise ModelRangeError(f'集总（整体）模型不支持排数外推（当前 {g["rows"]} 排）；7～12 排只在逐管网络中按声明外推',
                              field='geometry.rows',value=g['rows'],allowed={'min':1,'max':6})
    if g['tube_type']!='smooth':
        raise NotImplementedError('Micro-fin tubes are implemented for refrigerant evaporator networks only, not water coils')
    a,f=case['air'],case['fluid']
    if f['name'].lower()!='water':
        raise NotImplementedError('Geometry-derived conductance currently supports liquid water only')
    t,p=water_temperature_c+273.15,f['pressure_pa']
    rho=PropsSI('D','T',t,'P',p,'Water');mu=PropsSI('VISCOSITY','T',t,'P',p,'Water')
    k=PropsSI('CONDUCTIVITY','T',t,'P',p,'Water');cp=PropsSI('C','T',t,'P',p,'Water')
    quality=PropsSI('Q','T',t,'P',p,'Water')
    if 0<=quality<=1 or water_temperature_c<=0 or PhaseSI('T',t,'P',p,'Water')!='liquid':
        raise ValueError('Geometry water model requires a liquid state above freezing')
    di=g['tube_inner_diameter_m'];path=metrics['tube_path_length_m']
    flow=f['mass_flow_kg_s']/g['circuits_count']
    velocity=flow/(rho*math.pi*di**2/4);Re_water=rho*velocity*di/mu;Pr_water=cp*mu/k
    fd=friction_factor(Re_water,g['tube_roughness_m']/di,Method='Churchill_1977')
    warnings=[]
    if Re_water<=2300:
        Nu=laminar_entry_thermal_Hausen(Re_water,Pr_water,path,di);regime='laminar_Hausen'
    elif Re_water<3000:
        lam=laminar_entry_thermal_Hausen(Re_water,Pr_water,path,di)
        turb=turbulent_Gnielinski(3000.,Pr_water,friction_factor(3000.,g['tube_roughness_m']/di,Method='Churchill_1977'))
        Nu=lam+(turb-lam)*(Re_water-2300)/700;regime='transition_interpolation'
        warnings.append('水侧2300<Re<3000采用连续插值，仅作数值过渡，非已验证过渡区关联式。')
    else:
        if Re_water>5e6 or not .5<=Pr_water<=2000:
            raise ValueError('Water Gnielinski correlation outside Re/Pr range')
        Nu=turbulent_Gnielinski(Re_water,Pr_water,fd);regime='turbulent_Gnielinski'
    h_water=Nu*k/di
    water_dp=fd*path/di*rho*velocity**2/2
    if water_dp>=p:
        raise ValueError('Predicted straight-tube pressure loss exceeds inlet absolute pressure; supplied flow/geometry is infeasible')
    state=air_state(a['t_db_c'],a['relative_humidity'],a['pressure_pa'])
    m_da=air_mass_flow(a);w=state['humidity_ratio_kg_kg_da'];m_air=m_da*(1+w)
    rho_air=(1+w)/state['specific_volume_m3_kg_da'];cp_air=state['cp_j_kg_da_k']/(1+w)
    args=('T',a['t_db_c']+273.15,'P',a['pressure_pa'],'R',a['relative_humidity'])
    mu_air=HAPropsSI('M',*args);k_air=HAPropsSI('K',*args);Pr_air=cp_air*mu_air/k_air
    G=m_air/metrics['minimum_air_area_m2'];Re_air=G*metrics['collar_diameter_m']/mu_air
    factors=air_side_factors(g,metrics,Re_air)
    h_air=factors['colburn_j']*G*cp_air/Pr_air**(2/3)
    eta_fin=fin_efficiency(g,metrics,h_air)
    eta_surface=1-metrics['fin_area_m2']/metrics['total_outer_area_m2']*(1-eta_fin)
    R_air=1/(h_air*eta_surface*metrics['total_outer_area_m2'])
    R_water=1/(h_water*metrics['inner_area_m2'])
    R_wall=math.log(g['tube_outer_diameter_m']/di)/(2*math.pi*g['tube_conductivity_w_m_k']*g['tube_length_m']*metrics['tube_count'])
    R_extra=metrics.get('contact_resistance_k_w',0.)+metrics.get('inner_fouling_resistance_k_w',0.)
    ua=1/(R_air+R_water+R_wall) if not R_extra else 1/(R_air+R_water+R_wall+R_extra)
    air_dp=factors['fanning_friction_factor']*4*metrics['air_depth_m']/metrics['air_hydraulic_diameter_m']*G**2/(2*rho_air)
    warnings.extend(['几何水盘管仍采用整体等效逆流；不是逐管/排间交叉流网络。',
                     '理想芯体边界：总高=每排管数×横向管距、空气深度=排数×纵向管距；实际边界尚未自由定义。',
                     ('套管直径采用等厚套管口径Dc=Do+2tf；翅片面积按输入实际片数fin_count计算；实际成形套管尺寸未独立输入。'
                      if 'fin_count' in g else
                      '套管直径采用等厚套管口径Dc=Do+2tf；等效片数=管长/片距（可用fin_count输入实际片数）；实际成形套管尺寸未独立输入。'),
                     (('连续平翅片效率采用等面积环形翅片近似；无接触热阻、污垢和严格部分湿翅片。'
                       if fin_efficiency_method(g)=='equal_area_annular' else
                       '翅片效率采用Schmidt当量圆翅片法（Wang, Webb & Chi 2000）；无接触热阻、污垢。')
                      if not R_extra else
                      ('翅片效率：'+('等面积环形近似' if fin_efficiency_method(g)=='equal_area_annular' else 'Schmidt当量圆翅片法')+
                       '；计入输入的'+'、'.join(n for k,n in (('contact_conductance_w_m2_k','接触热导（按πDoL）'),
                       ('inner_fouling_resistance_m2_k_w','管内污垢热阻')) if k in g)+'，按常数串联，未随湿润/温度变化。')),
                     '空气物性取入口，水物性取迭代平均温度；不含壁温修正。',
                     '压降仅预测空气芯体摩擦和水侧直管摩擦，不含U弯/集管/局部损失；未耦合沿程压力状态。',
                     'circuits_count只定义等长等流量并联假设，未输入或求解真实连管与分配。'])
    if g['fin_type']!='plain':
        warnings.append(f"空气侧{factors['source']}，仅在文献样本范围内使用；湿表面沿用干表面j/f。")
        from .airside import extrapolation_warning
        note=extrapolation_warning(factors)
        if note:warnings.append(note)
    elif g.get('fin_pitch_extrapolation'):
        from .airside import extrapolation_warning
        warnings.append(extrapolation_warning(factors))
    return {'model_version':'plain-smooth-water-geometry-0.2' if g['fin_type']=='plain' else f"{g['fin_type']}-smooth-water-geometry-0.1",'geometry':g,'metrics':metrics,
            'ua_w_k':ua,'air_h_w_m2_k':h_air,'water_h_w_m2_k':h_water,
            'fin_efficiency':eta_fin,'surface_efficiency':eta_surface,
            'resistance_air_k_w':R_air,'resistance_water_k_w':R_water,'resistance_wall_k_w':R_wall,
            **({'resistance_contact_k_w':metrics['contact_resistance_k_w']} if 'contact_resistance_k_w' in metrics else {}),
            **({'resistance_inner_fouling_k_w':metrics['inner_fouling_resistance_k_w']} if 'inner_fouling_resistance_k_w' in metrics else {}),
            'air_reynolds_collar':Re_air,'air_prandtl':Pr_air,'water_reynolds':Re_water,'water_prandtl':Pr_water,
            'water_nusselt':Nu,'water_flow_regime':regime,'water_darcy_friction_factor':fd,
            'water_velocity_m_s':velocity,'air_frontal_velocity_m_s':a['volume_flow_m3_h']/3600/metrics['frontal_area_m2'],
            'air_minimum_velocity_m_s':G/rho_air,'air_core_friction_pressure_drop_pa':air_dp,
            'water_straight_tube_pressure_drop_pa':water_dp,'pressure_drop_coupled':False,
            'air_pressure_drop_model':'dry_isothermal_Wang_friction_only',
            'air_correlation':factors,'warnings':warnings}
