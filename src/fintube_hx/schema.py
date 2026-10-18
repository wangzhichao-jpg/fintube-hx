"""Shared boundary/solver contracts and the Community-only capability validator.
Extensions may declare additional fields, but no private solver is imported here.
"""
from copy import deepcopy
import math


class EditionCapabilityError(ValueError):
    """A requested engineering model is not part of this edition."""


def number(value,label,minimum=None,maximum=None):
    if isinstance(value,bool) or not isinstance(value,(int,float)):
        raise ValueError(f'{label} must be a JSON number')
    value=float(value)
    if not math.isfinite(value):raise ValueError(f'{label} must be finite')
    if minimum is not None and value<minimum:raise ValueError(f'{label} must be >= {minimum}')
    if maximum is not None and value>maximum:raise ValueError(f'{label} must be <= {maximum}')
    return value


def check_keys(value,allowed,label):
    if not isinstance(value,dict):raise ValueError(f'{label} must be an object')
    unknown=set(value)-set(allowed)
    if unknown:raise ValueError(f'Unsupported {label} fields: {", ".join(sorted(unknown))}')


def normalize_boundaries(case,*,extra_case_fields=(),extra_air_fields=()):
    """Validate shared inputs on a deep copy; extension fields must be explicit."""
    if not isinstance(case,dict):raise ValueError('Case must be a JSON object')
    c=deepcopy(case)
    check_keys(c,{'schema_version','name','kind','air','fluid','model','solver','geometry','target','metadata'}|set(extra_case_fields),'case')
    if c.get('schema_version','0.1')!='0.1':raise ValueError('Unsupported case schema_version')
    c.setdefault('schema_version','0.1');c.setdefault('name','untitled')
    if not isinstance(c['name'],str):raise ValueError('name must be a string')
    if c.get('kind') not in ('water','evaporator','condenser'):raise ValueError('kind must be water, evaporator or condenser')
    if 'metadata' in c and not isinstance(c['metadata'],dict):raise ValueError('metadata must be an object')
    for key in ('air','fluid','model'):
        if not isinstance(c.get(key),dict):raise ValueError(f'Missing {key} object')
    a,f=c['air'],c['fluid']
    check_keys(a,{'t_db_c','relative_humidity','pressure_pa','volume_flow_m3_h'}|set(extra_air_fields),'air')
    a['t_db_c']=number(a.get('t_db_c'),'air.t_db_c',-40,100)
    a['relative_humidity']=number(a.get('relative_humidity'),'air.relative_humidity',0,1)
    a['pressure_pa']=number(a.get('pressure_pa',101325),'air.pressure_pa',10000,200000)
    a['volume_flow_m3_h']=number(a.get('volume_flow_m3_h'),'air.volume_flow_m3_h',1e-6)
    check_keys(f,{'name','pressure_pa','mass_flow_kg_s','inlet_t_c','inlet_h_j_kg'},'fluid')
    if not isinstance(f.get('name'),str) or not f['name']:raise ValueError('fluid.name is required')
    f['pressure_pa']=number(f.get('pressure_pa'),'fluid.pressure_pa',1)
    f['mass_flow_kg_s']=number(f.get('mass_flow_kg_s'),'fluid.mass_flow_kg_s',1e-9)
    if ('inlet_t_c' in f)==('inlet_h_j_kg' in f):raise ValueError('Provide exactly one of inlet_h_j_kg or inlet_t_c')
    if 'inlet_t_c' in f:f['inlet_t_c']=number(f['inlet_t_c'],'fluid.inlet_t_c',-100,200)
    else:f['inlet_h_j_kg']=number(f['inlet_h_j_kg'],'fluid.inlet_h_j_kg')
    return c


def recommended_iteration_budget(c):
    """Budget for axial counterflow information propagation, not a guarantee.

    Only the lumped refrigerant model uses model.segments. Actual tube
    networks keep their independent convergence policy.
    """
    model=c['model']
    if c['kind']!='water' and model.get('refrigerant_model','lumped')=='lumped':
        return max(200,2*model.get('segments',80)+20)
    return 200


def normalize_solver(c):
    solver=c.setdefault('solver',{});check_keys(solver,{'max_iterations','tolerance_k'},'solver')
    n=solver.setdefault('max_iterations',recommended_iteration_budget(c))
    if isinstance(n,bool) or not isinstance(n,int) or not 1<=n<=5000:raise ValueError('solver.max_iterations must be an integer in 1..5000')
    solver['tolerance_k']=number(solver.get('tolerance_k',1e-5),'solver.tolerance_k',1e-9,1)


def normalize_mass_flow_target(c):
    t=c['target'];key={'water':'outlet_temperature_c','evaporator':'superheat_k','condenser':'subcooling_k'}[c['kind']]
    if not isinstance(t,dict) or key not in t or set(t)-{key,'mass_flow_bounds_kg_s','tolerance_k'}:
        raise ValueError(f'Target for {c["kind"]} must contain {key}, flow bounds, and optional tolerance_k only')
    t[key]=number(t[key],'target.'+key,-100 if c['kind']=='water' else 1e-8)
    bounds=t.get('mass_flow_bounds_kg_s')
    if not isinstance(bounds,list) or len(bounds)!=2:raise ValueError('target.mass_flow_bounds_kg_s must be [lower, upper]')
    lo=number(bounds[0],'target.lower',1e-9);hi=number(bounds[1],'target.upper',1e-9)
    if lo>=hi:raise ValueError('Target flow bounds must be increasing')
    t['mass_flow_bounds_kg_s']=[lo,hi];t['tolerance_k']=number(t.get('tolerance_k',.001),'target.tolerance_k',1e-8,1)


WET_SURFACE_MODELS=('contact_factor','threlkeld_braun')


def normalize_wet_surface_model(model):
    """Optional; never defaulted into the case so legacy snapshots/hashes are unchanged."""
    if 'wet_surface_model' in model and model['wet_surface_model'] not in WET_SURFACE_MODELS:
        raise ValueError('model.wet_surface_model must be contact_factor or threlkeld_braun')
    return model


def validate_case(case):
    if isinstance(case,dict) and 'network' in case:raise EditionCapabilityError('Actual tube networks are not in Community; no silent fallback to lumped models')
    if isinstance(case,dict) and isinstance(case.get('air'),dict) and 'velocity_field' in case['air']:
        raise EditionCapabilityError('Prescribed air-column fields are not in Community')
    c=normalize_boundaries(case);m=c['model']
    if 'tube_network' in (m.get('water_model'),m.get('refrigerant_model')):
        raise EditionCapabilityError('Actual tube-network models are not in Community')
    if m.get('air_arrangement','counterflow')!='counterflow':
        raise EditionCapabilityError('Community supports only the lumped counterflow contract')
    check_keys(m,{'water_model','refrigerant_model','ua_mode','ua_w_k','segments','air_arrangement','exposed_tubes','wet_surface_model'},'model')
    if c['kind']=='water':
        if 'refrigerant_model' in m:raise ValueError('refrigerant_model is only applicable to evaporators/condensers')
        m.setdefault('water_model','lumped')
        if m['water_model']!='lumped':raise ValueError('Community water_model must be lumped')
    else:
        if 'water_model' in m:raise ValueError('water_model is only applicable to water coils')
        m.setdefault('refrigerant_model','lumped')
        if m['refrigerant_model']!='lumped':raise ValueError('Community refrigerant_model must be lumped')
    mode=m.setdefault('ua_mode','input')
    if mode not in ('input','geometry'):raise ValueError('model.ua_mode must be input or geometry')
    if mode=='geometry':
        if c['kind']!='water':raise EditionCapabilityError('Refrigerant geometry models are not in Community')
        if 'ua_w_k' in m:raise ValueError('Do not supply UA when ua_mode=geometry; no hidden manual override')
        from .geometry import validate_geometry
        c['geometry']=validate_geometry(c.get('geometry'))
        if 'exposed_tubes' in m:
            from .exposed_tubes import normalize_exposed_tubes
            m['exposed_tubes']=normalize_exposed_tubes(m['exposed_tubes'])
        normalize_wet_surface_model(m)
    else:
        if 'exposed_tubes' in m:raise ValueError('model.exposed_tubes requires a geometry-derived water coil')
        if 'wet_surface_model' in m:raise ValueError('model.wet_surface_model requires a geometry-derived water coil')
        m['ua_w_k']=number(m.get('ua_w_k'),'model.ua_w_k',0)
        if 'geometry' in c:raise ValueError('Input-UA Community models do not accept inactive geometry; move archival notes to metadata')
    n=m.setdefault('segments',80)
    if isinstance(n,bool) or not isinstance(n,int) or not 1<=n<=400:raise ValueError('model.segments must be an integer from 1 to 400')
    m.setdefault('air_arrangement','counterflow');normalize_solver(c)
    if 'target' in c:
        if isinstance(c['target'],dict) and 'heat_transfer_w' in c['target']:raise EditionCapabilityError('Capacity/condensing-temperature design is not in Community')
        normalize_mass_flow_target(c)
    return c
