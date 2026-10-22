"""Public Community API; supports only models stated in the edition contract."""
from copy import deepcopy
from datetime import datetime,timezone
import math
import platform
import CoolProp
from . import __version__
from .schema import validate_case


def _assert_finite(value,path='result'):
    if isinstance(value,float) and not math.isfinite(value):raise ValueError('Nonfinite value at '+path)
    if isinstance(value,dict):
        for key,v in value.items():_assert_finite(v,path+'.'+str(key))
    elif isinstance(value,(list,tuple)):
        for i,v in enumerate(value):_assert_finite(v,path+f'[{i}]')


def capabilities():
    from . import CORE_API_VERSION
    return {'edition':'community','core_version':__version__,'core_api':CORE_API_VERSION,'input_schema':'0.1',
            'water':['input_ua_lumped','geometry_lumped_counterflow','counted_fins','exposed_bare_tubes_dry',
                     'wet_surface_contact_factor (default)','wet_surface_threlkeld_braun (optional)',
                     'contact_conductance / inner_fouling (optional, no default)'],
            'evaporator':['input_ua_lumped','subzero_evaporation reject | dry_only | initial_frost'],'condenser':['input_ua_lumped'],
            'targets':['water_outlet_temperature','evaporator_superheat','condenser_subcooling'],
            'geometry':{'arrangement':['staggered'],'tube_type':['smooth','microfin (Professional evaporator networks only)'],
                        'fin_type':{'plain':'Wang, Chi & Chang 2000','louver':'Wang, Lee, Chang & Lin 1999',
                                    'wavy_herringbone':'Wang, Hwang & Lin 2002'},
                        'fin_efficiency':['equal_area_annular','schmidt'],'rows':'1..6 (correlation sample range)'},
            'pressure_scope':{'legacy_v0':'default when model.pressure_scope is absent: dry core air friction + straight water-tube friction',
                              'v1':'air: core friction + acceleration + wet increment (entrance/exit included in f per the originals); '
                                   'geometry.fin_surface required'},
            'wet_air_friction':{'plain + bare_aluminum':'Wang, Lin & Lee 2000 (IJHMT 43:1869)',
                                'hydrophilic / louver / wavy_herringbone':'not computed; reported as not_computed (spec A4)'},
            'declared_extrapolations':{'correlation_range_tolerance':'louver/wavy_herringbone geometric bounds, <= 1 %',
                                       'fin_pitch_extrapolation':'plain fins, 8.7..12 mm',
                                       'row_extrapolation':'saturate_at_row_6, 7..12 rows, per-row API for tube networks only; '
                                                           'lumped models reject N > 6'},
            'structured_errors':'fintube_hx.errors.ModelRangeError (ValueError; Chinese message, field, allowed range, fallbacks)',
            'model_coverage':'every result lists included / excluded / extrapolated / degraded items',
            'not_supported_planned':['slit/bridge fins (original correlation not yet obtained)','small tubes Dc < 6.9 mm',
                                     'inline arrangement','microchannel / flat tubes',
                                     'mixtures not built into CoolProp (e.g. R454B, R513A)','frost growth / defrost',
                                     'water headers / return bends in the lumped coil','fan-curve coupling','tube networks (Professional)'],
            'requires_professional_package':False,'measured_precision_verified':False,
            'measured_comparisons':'validation/measured-v6 (CETIAT, Tan 2015, KH 1994; extrapolation references separate; '
                                    'not a precision certification)'}


def model_coverage(c, result):
    from .coverage import item, coverage
    scope=c['model'].get('pressure_scope','legacy_v0')
    if c['model']['ua_mode']!='geometry':
        return coverage(excluded=[item('pressure_not_modelled_input_ua')])
    g=c['geometry'];detail=result.get('geometry_model',{});factors=detail.get('air_correlation',{})
    inc=[item('air_core_friction',factors.get('source')),item('water_straight_friction','Churchill 1977 Darcy friction')]
    exc=[item('water_header'),item('return_bend')]
    if 'contact_conductance_w_m2_k' not in g:exc.append(item('contact_resistance_not_given'))
    ext=[];deg=[]
    if g['fin_type']!='plain' and 'correlation_range_tolerance' in g:ext.append(item('correlation_range_tolerance',detail=g['correlation_range_tolerance']))
    if g.get('fin_pitch_extrapolation'):ext.append(item('plain_fin_pitch_gt_8_7mm',detail=g['fin_pitch_m']))
    if scope=='legacy_v0':
        exc.insert(0,item('legacy_scope_pressure_terms'))
        return coverage(inc,exc,ext,deg)
    from .airside_pressure import ENTRANCE_EXIT_IN_F
    inc.insert(1,item('air_entrance_exit',ENTRANCE_EXIT_IN_F[g['fin_type']]))
    inc.insert(2,item('air_acceleration','Kays & London; Wang et al. data-reduction equations'))
    wet=result.get('air_pressure_drop_breakdown_pa',{}).get('wet_increment')
    if isinstance(wet,dict):
        deg.append(item('wet_increment_not_computed',detail=wet.get('not_computed')))
    elif result.get('air_pressure_drop_basis',{}).get('wet_fraction',0)>0:
        inc.insert(3,item('air_wet_increment',result.get('air_wet_friction',{}).get('source')))
    return coverage(inc,exc,ext,deg)


def run_case(case):
    c=validate_case(case);_assert_finite(c,'inputs')
    if c['kind']=='water':
        from .water import simulate_water,solve_water_target
        result=solve_water_target(c) if 'target' in c else simulate_water(c)
    else:
        from .refrigerant import simulate_refrigerant,solve_refrigerant_target
        result=solve_refrigerant_target(c) if 'target' in c else simulate_refrigerant(c)
    required={'case_name','kind','model_version','heat_transfer_w','air_out','fluid_out','condensate_kg_s','sensible_heat_w','energy_balance_relative_error','iterations','converged','warnings','segments'}
    if required-set(result):raise ValueError('Model returned incomplete result')
    if result['heat_transfer_w']<0 or result['condensate_kg_s']<0:raise ValueError('Negative capacity/condensate')
    result['inputs']=deepcopy(c);result['edition']='community';result['verification_level']='numerical_prototype_not_measured_validation'
    result['capability_level']='plain_fin_geometry_lumped_water' if c['model']['ua_mode']=='geometry' else 'UA_baseline_not_geometry_derived'
    result['warnings']=list(dict.fromkeys(result['warnings']+['Community数值基线；理论/软件对照不等于实际产品精度，未实现完整工程能力。']))
    result['model_coverage']=model_coverage(c,result)
    result['provenance']={'software':'fintube-hx','version':__version__,'python':platform.python_version(),'coolprop':CoolProp.__version__,
        'calculated_at_utc':datetime.now(timezone.utc).isoformat(),'source_kind':c.get('metadata',{}).get('source_kind','unspecified'),
        'source':c.get('metadata',{}).get('source','not provided')}
    _assert_finite(result);return result
