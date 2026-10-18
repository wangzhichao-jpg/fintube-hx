"""SI continuous-fin (plain, louver, herringbone wavy) / staggered smooth-tube geometry; no invented circuit route.
Minimum-area expression adapted from python-hvac, Copyright (c) 2023 Tom
Christiaens (MIT); full notice: third_party_licenses/python-hvac/LICENSE.md.
"""
from __future__ import annotations
from copy import deepcopy
import math


def validate_geometry(value: dict, equal_circuits: bool = True) -> dict:
    if not isinstance(value,dict):
        raise ValueError('geometry must be an object for geometry-derived UA')
    g=deepcopy(value)
    allowed={'fin_type','tube_type','arrangement','rows','tubes_per_row','circuits_count','tube_length_m',
             'tube_outer_diameter_m','tube_inner_diameter_m','transverse_pitch_m','longitudinal_pitch_m',
             'fin_pitch_m','fin_thickness_m','fin_conductivity_w_m_k','tube_conductivity_w_m_k','tube_roughness_m',
             'fin_count','notes','drawing_reference',
             'louver_pitch_m','louver_height_m','wave_height_m','wave_projected_length_m','fin_efficiency_method',
             'correlation_range_tolerance'}
    unknown=set(g)-allowed
    if unknown:
        raise ValueError('Unsupported active geometry fields: '+', '.join(sorted(unknown)))
    from .airside import FIN_TYPES, FIN_EFFICIENCY_METHODS
    if g.get('fin_type') not in FIN_TYPES or g.get('tube_type')!='smooth' or g.get('arrangement')!='staggered':
        raise NotImplementedError('Geometry baseline supports plain, louver or wavy_herringbone continuous fins '
                                  'on staggered smooth tubes only')
    shape={'plain':(),'louver':('louver_pitch_m','louver_height_m'),
           'wavy_herringbone':('wave_height_m','wave_projected_length_m')}
    for kind,keys in shape.items():
        for key in keys:
            if kind==g['fin_type']:
                v=g.get(key)
                if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0:
                    raise ValueError(f'geometry.{key} is required for fin_type={kind} as a finite positive SI number')
                g[key]=float(v)
            elif key in g:
                raise ValueError(f'geometry.{key} applies only to fin_type={kind}; no silently ignored field')
    if 'correlation_range_tolerance' in g:
        from .airside import MAX_RANGE_TOLERANCE
        v=g['correlation_range_tolerance']
        if g['fin_type']=='plain':
            raise ValueError('geometry.correlation_range_tolerance applies only to louver/wavy_herringbone fins')
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not 0<v<=MAX_RANGE_TOLERANCE:
            raise ValueError('geometry.correlation_range_tolerance must be in (0, 0.01]: declared geometric boundary extrapolation only')
        g['correlation_range_tolerance']=float(v)
    if 'fin_efficiency_method' in g and g['fin_efficiency_method'] not in FIN_EFFICIENCY_METHODS:
        raise ValueError('geometry.fin_efficiency_method must be equal_area_annular or schmidt')
    for key in ['rows','tubes_per_row','circuits_count']:
        v=g.get(key)
        if isinstance(v,bool) or not isinstance(v,int) or v<1:
            raise ValueError(f'geometry.{key} must be a positive integer')
    if g['rows']>6:
        raise ValueError('Wang plain-fin baseline restricted to 1..6 rows')
    if g['tubes_per_row']>500 or g['circuits_count']>500:
        raise ValueError('Geometry exceeds baseline size limit')
    for key in ['tube_length_m','tube_outer_diameter_m','tube_inner_diameter_m','transverse_pitch_m',
                'longitudinal_pitch_m','fin_pitch_m','fin_thickness_m','fin_conductivity_w_m_k','tube_conductivity_w_m_k']:
        v=g.get(key)
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0:
            raise ValueError(f'geometry.{key} must be a finite positive SI number')
        g[key]=float(v)
    g.setdefault('tube_roughness_m',0.)
    rough=g['tube_roughness_m']
    if isinstance(rough,bool) or not isinstance(rough,(int,float)) or not math.isfinite(rough) or rough<0:
        raise ValueError('geometry.tube_roughness_m must be finite and nonnegative')
    if rough/g['tube_inner_diameter_m']>.05:
        raise ValueError('Tube relative roughness outside this baseline')
    if g['tube_inner_diameter_m']>=g['tube_outer_diameter_m']:
        raise ValueError('Tube inner diameter must be smaller than outer diameter')
    if g['fin_thickness_m']>=g['fin_pitch_m']:
        raise ValueError('Fin thickness must be less than fin pitch')
    if g['fin_pitch_m']>g['tube_length_m']:
        raise ValueError('At least one equivalent fin pitch must fit the tube length')
    if 'fin_count' in g:
        # Actual counted fins on one tube length. A finite stack of n fins has
        # n-1 pitches, so the count may differ from L/pitch by about one fin.
        n=g['fin_count']
        if isinstance(n,bool) or not isinstance(n,int) or n<1:
            raise ValueError('geometry.fin_count must be a positive integer (actual fins per tube length)')
        if abs(n-g['tube_length_m']/g['fin_pitch_m'])>1.5:
            raise ValueError('geometry.fin_count must agree with tube_length_m/fin_pitch_m within 1.5 fins; '
                             'correct the finned length or pitch instead of overriding the area')
        if n*g['fin_thickness_m']>=g['tube_length_m']:
            raise ValueError('geometry.fin_count leaves no open length between fins')
    collar=g['tube_outer_diameter_m']+2*g['fin_thickness_m']
    diagonal=math.hypot(g['transverse_pitch_m']/2,g['longitudinal_pitch_m'])
    if min(g['transverse_pitch_m'],diagonal)<=collar:
        raise ValueError('Collar/tube collision in transverse or staggered spacing')
    total=g['rows']*g['tubes_per_row']
    if g['circuits_count']>total or (equal_circuits and total%g['circuits_count']):
        raise ValueError('Equal-circuit baseline requires total tubes divisible by circuits_count')
    return g


def geometry_metrics(value: dict, equal_circuits: bool = True) -> dict:
    g=validate_geometry(value,equal_circuits=equal_circuits)
    nr,nt,nc=g['rows'],g['tubes_per_row'],g['circuits_count']
    L,pt,pl=g['tube_length_m'],g['transverse_pitch_m'],g['longitudinal_pitch_m']
    do,di,tf,pf=g['tube_outer_diameter_m'],g['tube_inner_diameter_m'],g['fin_thickness_m'],g['fin_pitch_m']
    dc=do+2*tf;H=nt*pt;depth=nr*pl;total=nr*nt
    counted='fin_count' in g
    nf=float(g['fin_count']) if counted else L/pf
    a_face=L*H
    # Staggered minimum-area expression adapted from MIT python-hvac geometry.py.
    # Includes the outermost transverse gap rather than treating every gap as periodic.
    gap_transverse=.5*(pt-dc)*(1-tf/pf)
    # Fin blockage follows the same diagonal clear gap, not the transverse one.
    # Both candidate flow cuts have the axial open fraction (1 - tf/pf).
    gap_diagonal=(math.hypot(pt/2,pl)-dc)*(1-tf/pf)
    gap=2*min(gap_transverse,gap_diagonal)
    a_min=((nt-1)*gap+(pt-dc)*(1-tf/pf))*L
    # Herringbone wavy fins: developed face area along the corrugation, sec(theta) =
    # sqrt(Xf^2+Pd^2)/Xf (geometric; collar holes are taken as projected).
    sec=(math.hypot(g['wave_projected_length_m'],g['wave_height_m'])/g['wave_projected_length_m']
         if g['fin_type']=='wavy_herringbone' else 1.)
    a_fin_faces=2*(H*depth*sec-total*math.pi*dc**2/4)*nf if sec!=1. else 2*(H*depth-total*math.pi*dc**2/4)*nf
    a_fin_edges=2*(H+depth)*tf*nf
    a_fin=a_fin_faces+a_fin_edges
    # Legacy expression kept byte-for-byte when no count is supplied.
    a_bare=math.pi*dc*(L-nf*tf)*total if counted else math.pi*dc*L*(1-tf/pf)*total
    a_out=a_fin+a_bare
    if a_min<=0 or a_min>=a_face or a_fin<=0:
        raise ValueError('Geometry produces nonphysical minimum flow or fin area')
    if counted:
        # The correlation hydraulic diameter is a periodic channel property (one
        # pitch per fin). Counting an end fin adds area but must not change j/f.
        periodic_out=(2*(H*depth*sec-total*math.pi*dc**2/4)+2*(H+depth)*tf)*L/pf+math.pi*dc*L*(1-tf/pf)*total
        dh=4*a_min*depth/periodic_out
    else:
        dh=4*a_min*depth/a_out
    return {'tube_count':total,'tubes_per_circuit':total//nc if equal_circuits else total/nc,'equivalent_fin_count':nf,
            'fin_count_basis':'input_actual_count' if counted else 'tube_length_over_pitch',
            'width_m':L,'height_m':H,'air_depth_m':depth,'frontal_area_m2':a_face,
            'minimum_air_area_m2':a_min,'free_area_ratio':a_min/a_face,
            'collar_diameter_m':dc,'air_hydraulic_diameter_m':dh,
            'fin_area_m2':a_fin,'bare_outer_area_m2':a_bare,'total_outer_area_m2':a_out,
            'inner_area_m2':math.pi*di*L*total,'tube_path_length_m':L*total/nc,
            'equivalent_annular_fin_outer_diameter_m':2*math.sqrt(pt*pl/math.pi),
            **({'fin_area_enhancement_sec_theta':sec,
                'corrugation_angle_deg':math.degrees(math.atan(g['wave_height_m']/g['wave_projected_length_m']))}
               if g['fin_type']=='wavy_herringbone' else {})}
