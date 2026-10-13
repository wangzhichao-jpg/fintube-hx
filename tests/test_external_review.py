"""Focused analytical regressions from the external Community review."""
from copy import deepcopy
from pathlib import Path
import json
import math
import pytest
from fintube_hx.geometry import geometry_metrics
from fintube_hx.engine import run_case
from fintube_hx.inverse import solve_mass_flow
from fintube_hx.properties import air_state,fluid_pt
from fintube_hx.refrigerant import _cell
ROOT=Path(__file__).resolve().parents[1]
def example(name='water_geometry.json'):
    return json.loads((ROOT/'examples'/name).read_text(encoding='utf8'))

@pytest.mark.parametrize('fin_fraction',[.02,.05,.1])
def test_diagonal_control_fin_blockage_uses_diagonal_clear_gap(fin_fraction):
    g=example()['geometry']
    g.update(transverse_pitch_m=.030,longitudinal_pitch_m=.0127)
    g['fin_thickness_m']=g['fin_pitch_m']*fin_fraction
    dc=g['tube_outer_diameter_m']+2*g['fin_thickness_m']
    transverse=(g['transverse_pitch_m']-dc)*(1-fin_fraction)
    diagonal=2*(math.hypot(g['transverse_pitch_m']/2,g['longitudinal_pitch_m'])-dc)*(1-fin_fraction)
    assert diagonal<transverse
    # Clear cut through a periodic interior plus the transverse outer opening.
    expected=((g['tubes_per_row']-1)*diagonal+transverse)*g['tube_length_m']
    assert geometry_metrics(g)['minimum_air_area_m2']==pytest.approx(expected,rel=1e-14)


def test_transverse_control_is_unchanged():
    g=example()['geometry'];m=geometry_metrics(g)
    dc=g['tube_outer_diameter_m']+2*g['fin_thickness_m']
    expected=g['tubes_per_row']*(g['transverse_pitch_m']-dc)*(1-g['fin_thickness_m']/g['fin_pitch_m'])*g['tube_length_m']
    assert m['minimum_air_area_m2']==pytest.approx(expected,rel=1e-14)


def test_water_wet_proxy_recomputes_fin_efficiency():
    c=json.loads((ROOT/'references/python-hvac/water-community-input.json').read_text(encoding='utf8'))
    g=run_case(c)['geometry_model']
    wet=g['wet_model']
    assert wet['wet_fin_efficiency_proxy']<g['fin_efficiency']
    assert wet['wet_air_resistance_k_w']<g['resistance_air_k_w']
    assert wet['model']=='air_resistance_only_heat_mass_analogy_not_rigorous_partial_wet'


def test_water_legacy_segments_are_not_reported_as_discretization():
    c=example('water_dry.json');c['model'].pop('segments',None)
    # Omitted segments are accepted, and legacy supplied segments are explicit.
    a=run_case(c);c['model']['segments']=1;b=run_case(c);c['model']['segments']=20;d=run_case(c)
    assert a['heat_transfer_w']==b['heat_transfer_w']==d['heat_transfer_w']
    assert not d['numerical_controls']['segments_applied']
    assert d['numerical_controls']['segments_requested']==20
    assert d['segments']==[]


def test_dry_single_phase_cell_has_finite_fluid_capacity():
    air=air_state(25,.05,101325);fin=fluid_pt('R134a',1600000,50)
    low=_cell('R134a',1600000,fin['enthalpy_j_kg'],air,.002,.2,20,-1)
    high=_cell('R134a',1600000,fin['enthalpy_j_kg'],air,.02,.2,20,-1)
    # At identical UA and inlet states, Q depends strongly on m_ref.
    assert high[2]>4*low[2]
    assert low[0]['temperature_c']>=air['t_db_c']
    for m,result in [(.002,low),(.02,high)]:
        assert result[2]==pytest.approx(m*(fin['enthalpy_j_kg']-result[0]['enthalpy_j_kg']),abs=1e-8)


def test_same_sign_endpoints_do_not_prove_no_internal_roots():
    c={'fluid':{'mass_flow_kg_s':1.},'target':{'goal':0.,'mass_flow_bounds_kg_s':[.1,2.],'tolerance_k':1e-5}}
    def simulate(c):
        m=c['fluid']['mass_flow_kg_s']
        return {'value':(m-.5)*(m-1.5),'iterations':1,'converged':True}
    with pytest.raises(ValueError,match='not bracketed.*interior roots'):
        solve_mass_flow(c,'goal',lambda r:r['value'],simulate)
    c['target']['mass_flow_bounds_kg_s']=[.1,1.]
    r=solve_mass_flow(c,'goal',lambda r:r['value'],simulate)
    assert r['target_solution']['mass_flow_kg_s']==pytest.approx(.5,abs=1e-5)
    assert r['target_solution']['uniqueness_verified'] is False
    assert r['target_solution']['cold_verified']
