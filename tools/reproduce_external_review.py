"""Reproduce external review claims using installed Community.
Usage: python tools/reproduce_external_review.py output/external-review
No other edition imports, fitted inputs or reference-capacity targets.
"""
from pathlib import Path
from copy import deepcopy
import json,math,sys
from fintube_hx.engine import run_case
from fintube_hx.geometry import geometry_metrics
from fintube_hx.geometry_performance import wet_geometry_conductance
from fintube_hx.refrigerant import _cell
from fintube_hx.properties import fluid_pt,air_state
from fintube_hx.inverse import solve_mass_flow
PUB=Path(__file__).resolve().parents[1]
OUT=Path(sys.argv[1]);OUT.mkdir(parents=True,exist_ok=False)
def load(p):return json.loads(p.read_text(encoding='utf8'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
case=load(PUB/'references/python-hvac/water-community-input.json');r=run_case(case);save(OUT/'mapped-water-input.json',case);save(OUT/'mapped-water-result.json',r)
g=r['geometry_model'];stats={'q_w':r['heat_transfer_w'],'air_out_c':r['air_out']['t_db_c'],'water_out_c':r['fluid_out']['temperature_c'],'air_core_dp_pa':g['air_core_friction_pressure_drop_pa'],'water_straight_dp_pa':g['water_straight_tube_pressure_drop_pa'],'wet_fin_efficiency':g['wet_model']['wet_fin_efficiency_proxy'],'dry_fin_efficiency':g['fin_efficiency'],'normalized_segments':r['inputs']['model']['segments']}
test=deepcopy(case);test['air']['relative_humidity']=.5;dew=air_state(27,.5,101325)['dew_point_c'];series=[]
for t in [12.5,16.5,dew-.01,dew+.01,dew-.0001,dew+.0001]:
 test['fluid']['inlet_t_c']=t;res=run_case(test);series.append({'inlet_water_c':t,'q_w':res['heat_transfer_w'],'condensate_kg_s':res['condensate_kg_s'],'surface_policy':res['air_surface_condition']})
seg=[]
for n in [1,20]:
 cc=deepcopy(case);cc['model']['segments']=n;rr=run_case(cc);seg.append({'segments':n,'q_w':rr['heat_transfer_w']})
# Finite refrigerant heat-capacity coupling is solved in _cell, not Cr=0:
# change only liquid mass flow; air, inlet fluid T, total UA remain fixed.
air=air_state(25,.05,101325);fin=fluid_pt('R134a',1600000,50);cells=[]
for m in [.002,.02]:
 fout,aout,q,cond,ts,limited=_cell('R134a',1600000,fin['enthalpy_j_kg'],air,m,.2,20,-1)
 cells.append({'mass_flow_kg_s':m,'q_w':q,'fluid_out_c':fout['temperature_c'],'capacity_limited':limited})
# Narrow diagonal-controlled bank: independent repeated-gap construction.
ge=load(PUB/'examples/water_geometry.json')['geometry'];ge.update(transverse_pitch_m=.030,longitudinal_pitch_m=.0127)
met=geometry_metrics(ge);pt=ge['transverse_pitch_m'];pl=ge['longitudinal_pitch_m'];tf=ge['fin_thickness_m'];pf=ge['fin_pitch_m'];dc=ge['tube_outer_diameter_m']+2*tf
trans=(pt-dc)*(1-tf/pf);diag=2*(math.hypot(pt/2,pl)-dc)*(1-tf/pf);expected=((ge['tubes_per_row']-1)*min(trans,diag)+trans)*ge['tube_length_m']
# Same-sign endpoints do not establish that an internal target root is absent.
toy={'fluid':{'mass_flow_kg_s':1.},'target':{'goal':0.,'mass_flow_bounds_kg_s':[.1,2.],'tolerance_k':1e-5}}
def sim(c):return {'value':(c['fluid']['mass_flow_kg_s']-.5)*(c['fluid']['mass_flow_kg_s']-1.5),'converged':True,'iterations':1}
try:solve_mass_flow(toy,'goal',lambda r:r['value'],sim);msg='accepted'
except ValueError as e:msg=str(e)
report={'mapped_water':stats,'wet_transition_test':{'dew_c':dew,'conditions_note':'Mapped reference input with RH changed from .47 to .50; water inlet swept, remaining fields fixed','series':series},'water_segments':seg,'single_phase_cells':cells,'diagonal_minimum_area':{'geometry':ge,'program_m2':met['minimum_air_area_m2'],'independent_m2':expected,'relative_error_percent':100*(met['minimum_air_area_m2']-expected)/expected,'transverse_gap_m':trans,'two_diagonal_gaps_m':diag},'nonmonotonic_bounds_message':msg}
save(OUT/'summary.json',report)
print(json.dumps(report,ensure_ascii=False,indent=2))
