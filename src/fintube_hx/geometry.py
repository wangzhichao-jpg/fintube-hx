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
             'correlation_range_tolerance','microfin_count','microfin_height_m','microfin_apex_angle_deg',
             'microfin_helix_angle_deg','microfin_tip_thickness_m','contact_conductance_w_m2_k',
             'inner_fouling_resistance_m2_k_w','fin_surface','row_extrapolation','fin_pitch_extrapolation',
             'wet_friction_fin_pitch_extrapolation'}
    unknown=set(g)-allowed
    if unknown:
        raise ValueError('Unsupported active geometry fields: '+', '.join(sorted(unknown)))
    from .airside import FIN_TYPES, FIN_EFFICIENCY_METHODS
    from .errors import UnsupportedFeatureError, ModelRangeError, range_error, fallback, PLANNED_NOTE, \
        ROW_EXTRAPOLATION_MAX_ROWS, PLAIN_FIN_PITCH_EXTRAPOLATION_MAX_M
    legacy_en='Geometry baseline supports plain, louver or wavy_herringbone continuous fins on staggered smooth or micro-fin tubes only'
    if g.get('fin_type') not in FIN_TYPES:
        what=('条缝片（桥片）：关联式须按原文实现，原文尚未取得' if g.get('fin_type') in ('slit','bridge')
              else f'片型 {g.get("fin_type")!r}')
        raise UnsupportedFeatureError(f'{what}；{PLANNED_NOTE}。本版支持平片 plain、百叶片 louver、人字波纹片 wavy_herringbone',
                                      field='geometry.fin_type',value=g.get('fin_type'),allowed={'enum':list(FIN_TYPES)},message_en=legacy_en)
    if g.get('tube_type') not in ('smooth','microfin'):
        raise UnsupportedFeatureError(f'管型 {g.get("tube_type")!r}（扁管、微通道等）{PLANNED_NOTE}。本版支持光管 smooth 与内螺纹管 microfin',
                                      field='geometry.tube_type',value=g.get('tube_type'),allowed={'enum':['smooth','microfin']},message_en=legacy_en)
    if g.get('arrangement')!='staggered':
        raise UnsupportedFeatureError(f'排列方式 {g.get("arrangement")!r}（顺排等）{PLANNED_NOTE}。本版只支持叉排 staggered',
                                      field='geometry.arrangement',value=g.get('arrangement'),allowed={'enum':['staggered']},message_en=legacy_en)
    if 'fin_surface' in g and g['fin_surface'] not in ('hydrophilic','bare_aluminum'):
        raise ModelRangeError('geometry.fin_surface 只能为 hydrophilic（亲水涂层）或 bare_aluminum（裸铝）',
                              field='geometry.fin_surface',value=g['fin_surface'],allowed={'enum':['hydrophilic','bare_aluminum']})
    mf_keys=('microfin_count','microfin_height_m','microfin_apex_angle_deg','microfin_helix_angle_deg','microfin_tip_thickness_m')
    if g['tube_type']=='microfin':
        for key in mf_keys:
            v=g.get(key)
            ok=(isinstance(v,int) and not isinstance(v,bool) and v>0) if key=='microfin_count' else \
               (not isinstance(v,bool) and isinstance(v,(int,float)) and math.isfinite(v) and (v>=0 if key=='microfin_tip_thickness_m' else v>0))
            if not ok:
                raise ValueError(f'geometry.{key} is required for tube_type=microfin (fin parameters perpendicular to the tube axis; '
                                 'tube_inner_diameter_m is the fin-root diameter)')
            if key!='microfin_count':g[key]=float(v)
    else:
        for key in mf_keys:
            if key in g:raise ValueError(f'geometry.{key} applies only to tube_type=microfin; no silently ignored field')
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
    for key in ('contact_conductance_w_m2_k','inner_fouling_resistance_m2_k_w'):
        if key in g:
            v=g[key]
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0:
                raise ValueError(f'geometry.{key} must be a finite positive SI number')
            g[key]=float(v)
    if 'fin_efficiency_method' in g and g['fin_efficiency_method'] not in FIN_EFFICIENCY_METHODS:
        raise ValueError('geometry.fin_efficiency_method must be equal_area_annular or schmidt')
    for key in ['rows','tubes_per_row','circuits_count']:
        v=g.get(key)
        if isinstance(v,bool) or not isinstance(v,int) or v<1:
            raise ValueError(f'geometry.{key} must be a positive integer')
    if 'row_extrapolation' in g:
        if g['row_extrapolation']!='saturate_at_row_6':
            raise ModelRangeError('geometry.row_extrapolation 只能为 saturate_at_row_6',field='geometry.row_extrapolation',
                                  value=g['row_extrapolation'],allowed={'enum':['saturate_at_row_6']})
        if g['rows']<=6:
            raise ModelRangeError(f'排数 {g["rows"]} 在关联式样本范围 1～6 排以内，不应声明 row_extrapolation',
                                  field='geometry.row_extrapolation',value=g['row_extrapolation'],
                                  fallbacks=[fallback('remove_row_extrapolation','删除该声明',{'geometry.row_extrapolation':None})])
    if g['rows']>ROW_EXTRAPOLATION_MAX_ROWS:
        raise ModelRangeError(f'排数 {g["rows"]} 超过外推上限 {ROW_EXTRAPOLATION_MAX_ROWS} 排，一律拒绝',field='geometry.rows',value=g['rows'],
                              allowed={'min':1,'max':ROW_EXTRAPOLATION_MAX_ROWS},message_en='Wang plain-fin baseline restricted to 1..6 rows')
    if g['rows']>6 and g.get('row_extrapolation')!='saturate_at_row_6':
        raise range_error('空气侧关联式','rows',g['rows'],1,6,message_en='Wang plain-fin baseline restricted to 1..6 rows')
    if 'fin_pitch_extrapolation' in g:
        pf=g.get('fin_pitch_m')
        if g['fin_pitch_extrapolation'] is not True:
            raise ModelRangeError('geometry.fin_pitch_extrapolation 只能为 true（不声明时请删除该字段）',
                                  field='geometry.fin_pitch_extrapolation',value=g['fin_pitch_extrapolation'])
        if g['fin_type']!='plain':
            raise ModelRangeError('大片距外推只用于平片；百叶片与波纹片只允许 correlation_range_tolerance（≤ 1%）',
                                  field='geometry.fin_pitch_extrapolation',value=True)
        if isinstance(pf,bool) or not isinstance(pf,(int,float)) or not 0.0087<pf<=PLAIN_FIN_PITCH_EXTRAPOLATION_MAX_M:
            raise ModelRangeError(f'大片距外推只适用于片距 8.7～{PLAIN_FIN_PITCH_EXTRAPOLATION_MAX_M*1000:g} mm（当前 {pf}）；'
                                  '片距 ≤ 8.7 mm 时不应声明，超过 12 mm 一律拒绝',field='geometry.fin_pitch_m',value=pf,
                                  allowed={'min':0.0087,'max':PLAIN_FIN_PITCH_EXTRAPOLATION_MAX_M})
    if 'wet_friction_fin_pitch_extrapolation' in g:
        from .errors import WET_FRICTION_FIN_PITCH_PUBLISHED_MAX_M as WLO,WET_FRICTION_FIN_PITCH_EXTRAPOLATION_MAX_M as WHI
        pf=g.get('fin_pitch_m');fld='geometry.wet_friction_fin_pitch_extrapolation'
        if g['wet_friction_fin_pitch_extrapolation'] is not True:
            raise ModelRangeError('geometry.wet_friction_fin_pitch_extrapolation 只能为 true（不声明时请删除该字段）',
                                  field=fld,value=g['wet_friction_fin_pitch_extrapolation'])
        if g['fin_type']!='plain':
            raise ModelRangeError('湿工况摩擦关联式片距外推只用于平片（Wang, Lin & Lee 2000 的样本均为平片）',field=fld,value=True)
        if g.get('fin_surface')!='bare_aluminum':
            raise ModelRangeError('湿工况摩擦关联式片距外推只用于裸铝翅片（原文样本均无亲水涂层）',field=fld,value=True)
        if isinstance(pf,bool) or not isinstance(pf,(int,float)) or not WLO<pf<=WHI:
            raise ModelRangeError(f'湿工况摩擦关联式片距外推只适用于片距 {WLO*1000:g}～{WHI*1000:g} mm（当前 {pf}）；'
                                  f'片距 ≤ {WLO*1000:g} mm 时不应声明，超过 {WHI*1000:g} mm 一律拒绝',field='geometry.fin_pitch_m',value=pf,
                                  allowed={'min':WLO,'max':WHI})
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
    inner={'inner_area_m2':math.pi*di*L*total}
    if g['tube_type']=='microfin':
        from .microfin import microfin_geometry
        mf=microfin_geometry(di,g['microfin_count'],g['microfin_height_m'],g['microfin_apex_angle_deg'],
                             g['microfin_helix_angle_deg'],g['microfin_tip_thickness_m'])
        inner={'inner_area_m2':mf['area_per_length_m']*L*total,'inner_flow_area_m2':mf['flow_area_m2'],
               'inner_hydraulic_diameter_m':mf['hydraulic_diameter_m'],'microfin':mf}
    extra_r={}
    if 'contact_conductance_w_m2_k' in g:
        # Fin-collar/tube contact, based on the tube outer area pi*Do*L of all tubes.
        extra_r['contact_resistance_k_w']=1/(g['contact_conductance_w_m2_k']*math.pi*do*L*total)
    if 'inner_fouling_resistance_m2_k_w' in g:
        extra_r['inner_fouling_resistance_k_w']=g['inner_fouling_resistance_m2_k_w']/inner['inner_area_m2']
    return {'tube_count':total,**extra_r,'tubes_per_circuit':total//nc if equal_circuits else total/nc,'equivalent_fin_count':nf,
            'fin_count_basis':'input_actual_count' if counted else 'tube_length_over_pitch',
            'width_m':L,'height_m':H,'air_depth_m':depth,'frontal_area_m2':a_face,
            'minimum_air_area_m2':a_min,'free_area_ratio':a_min/a_face,
            'collar_diameter_m':dc,'air_hydraulic_diameter_m':dh,
            'fin_area_m2':a_fin,'bare_outer_area_m2':a_bare,'total_outer_area_m2':a_out,
            **inner,'tube_path_length_m':L*total/nc,
            'equivalent_annular_fin_outer_diameter_m':2*math.sqrt(pt*pl/math.pi),
            **({'fin_area_enhancement_sec_theta':sec,
                'corrugation_angle_deg':math.degrees(math.atan(g['wave_height_m']/g['wave_projected_length_m']))}
               if g['fin_type']=='wavy_herringbone' else {})}
