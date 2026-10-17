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
    return {'edition':'community','input_schema':'0.1','water':['input_ua_lumped','plain_smooth_geometry_lumped','counted_fins','exposed_bare_tubes_dry'],
            'evaporator':['input_ua_lumped'],'condenser':['input_ua_lumped'],
            'targets':['water_outlet_temperature','evaporator_superheat','condenser_subcooling'],
            'requires_professional_package':False,'measured_precision_verified':False,
            'measured_comparisons':'validation/measured (6 published points, 2 specimens; not a precision certification)'}


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
    result['provenance']={'software':'fintube-hx','version':__version__,'python':platform.python_version(),'coolprop':CoolProp.__version__,
        'calculated_at_utc':datetime.now(timezone.utc).isoformat(),'source_kind':c.get('metadata',{}).get('source_kind','unspecified'),
        'source':c.get('metadata',{}).get('source','not provided')}
    _assert_finite(result);return result
