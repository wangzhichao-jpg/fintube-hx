"""v1 pressure scope (spec A1-A4, contract sections 1 and 3) on the lumped geometry water coil."""
import json
from copy import deepcopy
from pathlib import Path
import pytest
from fintube_hx.engine import run_case
from fintube_hx.errors import ModelRangeError
from fintube_hx.airside_pressure import acceleration_pa, ENTRANCE_EXIT_IN_F

EX = Path(__file__).resolve().parents[1] / 'examples'


def case(**model):
    c = json.loads((EX / 'water_geometry.json').read_text(encoding='utf8'))
    c['model'].update(model)
    return c


def wet(c):
    c['fluid']['inlet_t_c'] = 7.0
    c['air'].update(t_db_c=27.0, relative_humidity=0.5)
    return c


def v1(c, surface='bare_aluminum'):
    c['model']['pressure_scope'] = 'v1'
    c['geometry']['fin_surface'] = surface
    return c


def test_legacy_scope_is_default_and_adds_only_coverage():
    legacy = run_case(case())
    explicit = run_case(case(pressure_scope='legacy_v0'))
    assert explicit['heat_transfer_w'] == legacy['heat_transfer_w']
    assert 'air_pressure_drop_breakdown_pa' not in legacy
    assert legacy['model_coverage']['excluded'][0]['id'] == 'legacy_scope_pressure_terms'
    assert 'pressure_scope' not in legacy['inputs']['model']          # never defaulted into the case


def test_acceleration_hand_calculation():
    G, r1, r2, s = 3.0, 1.18, 1.21, 0.55
    assert acceleration_pa(G, r1, r2, s) == pytest.approx(9 / 2.36 * (1 + .3025) * (1.18 / 1.21 - 1), rel=1e-14)


def test_dry_v1_breakdown_and_unchanged_core_friction():
    legacy = run_case(case())
    r = run_case(v1(case()))
    b = r['air_pressure_drop_breakdown_pa']
    assert r['heat_transfer_w'] == legacy['heat_transfer_w']           # pressure terms do not feed back
    assert b['core_friction'] == legacy['geometry_model']['air_core_friction_pressure_drop_pa'] == r['air_pressure_drop_pa']
    assert b['entrance'] == b['exit'] == 'included_in_f' and b['wet_increment'] == 0.0
    assert r['air_pressure_drop_total_pa'] == pytest.approx(b['core_friction'] + b['acceleration'], rel=1e-15)
    assert b['acceleration'] < 0                                        # air cooled -> denser outlet -> recovery
    basis = r['air_pressure_drop_basis']
    assert b['acceleration'] == pytest.approx(acceleration_pa(basis['mass_flux_kg_m2_s'], basis['inlet_density_kg_m3'],
                                                              basis['outlet_density_kg_m3'], basis['contraction_ratio_sigma']), rel=1e-15)
    assert basis['entrance_exit_included_in_f'] == ENTRANCE_EXIT_IN_F['plain']
    ids = [i['id'] for i in r['model_coverage']['included']]
    assert ids[:3] == ['air_core_friction', 'air_entrance_exit', 'air_acceleration']


@pytest.mark.parametrize('wet_model', ['contact_factor', 'threlkeld_braun'])
def test_wet_increment_bare_aluminum(wet_model):
    r = run_case(v1(wet(case(wet_surface_model=wet_model))))
    b = r['air_pressure_drop_breakdown_pa']
    assert r['condensate_kg_s'] > 0 and b['wet_increment'] > 0
    f_dry = r['geometry_model']['air_correlation']['fanning_friction_factor']
    f_wet = r['air_wet_friction']['fanning_friction_factor']
    assert b['wet_increment'] == pytest.approx(b['core_friction'] * (f_wet / f_dry - 1), rel=1e-12)
    assert r['air_pressure_drop_total_pa'] == pytest.approx(sum(b[k] for k in ('core_friction', 'acceleration', 'wet_increment')), rel=1e-15)
    assert 'air_wet_increment' in [i['id'] for i in r['model_coverage']['included']]
    assert not any('空气压降仍为干表面' in w or '压降仍为干表面摩擦基线' in w for w in r['warnings'])


def test_hydrophilic_refuses_only_the_wet_increment():
    bare = run_case(v1(wet(case())))
    r = run_case(v1(wet(case()), 'hydrophilic'))
    assert r['heat_transfer_w'] == bare['heat_transfer_w']
    assert 'not_computed' in r['air_pressure_drop_breakdown_pa']['wet_increment']
    assert r['air_pressure_drop_total_label'] == '空气压降（不含湿附加）'
    assert r['model_coverage']['degraded'][0]['id'] == 'wet_increment_not_computed'


def test_scope_field_rules():
    with pytest.raises(ModelRangeError, match='fin_surface') as e:
        run_case(case(pressure_scope='v1'))
    assert e.value.allowed == {'enum': ['hydrophilic', 'bare_aluminum']}
    c = case(); c['geometry']['fin_surface'] = 'bare_aluminum'
    with pytest.raises(ModelRangeError, match='legacy_v0') as e:
        run_case(c)
    assert e.value.fallbacks[0]['patch'] == {'model.pressure_scope': 'v1'}
    with pytest.raises(ModelRangeError, match='pressure_scope'):
        run_case(case(pressure_scope='v2'))
    with pytest.raises(ModelRangeError):
        bad = v1(case()); bad['geometry']['fin_surface'] = 'unknown'; run_case(bad)


def test_input_ua_v1_needs_no_surface():
    c = json.loads((EX / 'water_dry.json').read_text(encoding='utf8'))
    c['model']['pressure_scope'] = 'v1'
    r = run_case(c)
    assert r['model_coverage']['excluded'][0]['id'] == 'pressure_not_modelled_input_ua'
