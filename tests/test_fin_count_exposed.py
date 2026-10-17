"""0.1.0.dev7: counted fins and exposed bare tube / return-bend convection."""
import copy
import json
import math
from pathlib import Path
import pytest
from CoolProp.HumidAirProp import HAPropsSI
from ht.conv_external import Nu_cylinder_Churchill_Bernstein
from fintube_hx.engine import run_case
from fintube_hx.geometry import geometry_metrics
from fintube_hx.exposed_tubes import normalize_exposed_tubes, element_conductance, element_heat_to_fluid
from fintube_hx.wang_plain_fin import wang_plain_fin

ROOT = Path(__file__).resolve().parents[1]


def case(name):
    return json.loads((ROOT / 'examples' / name).read_text(encoding='utf8'))


def test_absent_fin_count_is_byte_identical_legacy_geometry():
    g = case('water_geometry.json')['geometry']
    m = geometry_metrics(g)
    L, pf, tf = g['tube_length_m'], g['fin_pitch_m'], g['fin_thickness_m']
    dc = g['tube_outer_diameter_m'] + 2 * tf
    total = g['rows'] * g['tubes_per_row']
    assert m['fin_count_basis'] == 'tube_length_over_pitch'
    assert m['equivalent_fin_count'] == L / pf
    assert m['bare_outer_area_m2'] == math.pi * dc * L * (1 - tf / pf) * total


def test_counted_fins_scale_area_but_not_periodic_hydraulic_diameter():
    g = case('water_geometry.json')['geometry']
    base = geometry_metrics(g)
    n = round(g['tube_length_m'] / g['fin_pitch_m']) + 1
    counted = geometry_metrics({**g, 'fin_count': n})
    assert counted['fin_count_basis'] == 'input_actual_count'
    assert counted['fin_area_m2'] == pytest.approx(base['fin_area_m2'] * n / base['equivalent_fin_count'], rel=1e-12)
    # Wang j/f depends on Dh; an end fin must not change the periodic channel diameter.
    assert counted['air_hydraulic_diameter_m'] == pytest.approx(base['air_hydraulic_diameter_m'], rel=1e-12)
    assert counted['minimum_air_area_m2'] == base['minimum_air_area_m2']


@pytest.mark.parametrize('bad', [0, -1, 2.5, True, 10**6])
def test_fin_count_rejects_non_counts_and_area_overrides(bad):
    g = case('water_geometry.json')['geometry']
    with pytest.raises(ValueError, match='fin_count'):
        geometry_metrics({**g, 'fin_count': bad})


def test_exposed_tube_conductance_matches_hand_calculation():
    do, di, k, L = 0.00952, 0.009, 387.6, 0.5
    h_in = 4000.0
    t_air, t_s, v, p = 24.0, 58.0, 2.183, 101325.0
    w = HAPropsSI('W', 'T', t_air + 273.15, 'P', p, 'R', 0.5)
    film = (t_air + t_s) / 2 + 273.15
    mu = HAPropsSI('M', 'T', film, 'P', p, 'W', w); kk = HAPropsSI('K', 'T', film, 'P', p, 'W', w)
    cp = HAPropsSI('C', 'T', film, 'P', p, 'W', w) / (1 + w); rho = (1 + w) / HAPropsSI('V', 'T', film, 'P', p, 'W', w)
    h_out = Nu_cylinder_Churchill_Bernstein(rho * v * do / mu, cp * mu / kk) * kk / do
    expected = 1 / (1 / (h_out * math.pi * do * L) + math.log(do / di) / (2 * math.pi * k * L) + 1 / (h_in * math.pi * di * L))
    assert element_conductance(L, do, di, k, h_out, h_in) == pytest.approx(expected, rel=1e-12)
    q = element_heat_to_fluid(expected, 0.03, 4180.0, t_s, t_air)
    assert q == pytest.approx(0.03 * 4180 * (t_air - t_s) * (1 - math.exp(-expected / (0.03 * 4180))), rel=1e-12)
    assert -q < expected * (t_s - t_air)  # exact element is below the linear bound


def hot_case():
    c = case('water_geometry.json')
    c['air'].update(t_db_c=24.0, relative_humidity=0.5)
    c['fluid']['inlet_t_c'] = 60.0
    return c


def test_lumped_exposed_tubes_add_heat_and_close_balance():
    c = hot_case()
    base = run_case(c)
    c['model']['exposed_tubes'] = {'straight_length_per_tube_m': 0.02, 'return_bend_count': 15,
                                   'return_bend_centerline_radius_m': 0.0125, 'approach_velocity_m_s': 2.0}
    r = run_case(c)
    e = r['exposed_tubes']
    assert e['heat_to_water_w'] < 0
    assert r['heat_transfer_w'] > base['heat_transfer_w']
    assert r['finned_core_heat_w'] == pytest.approx(r['heat_transfer_w'] + e['heat_to_water_w'], rel=1e-9)
    assert r['energy_balance_relative_error'] < 1e-9 and r['converged']
    tubes = c['geometry']['rows'] * c['geometry']['tubes_per_row']
    assert e['straight_length_m'] == pytest.approx(0.02 * tubes)
    assert e['return_bend_length_m'] == pytest.approx(15 * math.pi * 0.0125)


def test_exposed_tubes_contract_is_explicit():
    with pytest.raises(ValueError, match='return_bend_count is required'):
        normalize_exposed_tubes({'straight_length_per_tube_m': 0.01, 'approach_velocity_m_s': 2})
    with pytest.raises(ValueError, match='disagrees'):
        normalize_exposed_tubes({'return_bend_count': 3, 'return_bend_centerline_radius_m': .01,
                                 'approach_velocity_m_s': 2}, derived_bend_count=9)
    with pytest.raises(ValueError, match='no exposed surface'):
        normalize_exposed_tubes({'return_bend_count': 0, 'approach_velocity_m_s': 2})
    with pytest.raises(ValueError, match='Unsupported'):
        normalize_exposed_tubes({'return_bend_count': 0, 'straight_length_per_tube_m': .01,
                                 'approach_velocity_m_s': 2, 'heat_multiplier': 2})
    c = case('water_wet.json')
    c['model']['exposed_tubes'] = {'straight_length_per_tube_m': 0.02, 'return_bend_count': 0, 'approach_velocity_m_s': 2.0}
    with pytest.raises(ValueError):
        run_case(c)  # input-UA case: exposed tubes need geometry
    g = case('water_geometry.json')
    g['air'].update(t_db_c=27.0, relative_humidity=0.6)
    g['fluid']['inlet_t_c'] = 7.0
    g['model']['exposed_tubes'] = {'straight_length_per_tube_m': 0.02, 'return_bend_count': 0, 'approach_velocity_m_s': 2.0}
    with pytest.raises(ValueError, match='dry-only'):
        run_case(g)


def test_wang_input_unchanged_by_count_for_measured_w1_geometry():
    """W1 (Altwieb 2022): 21 counted fins on 84.3 mm at 4.23 mm pitch."""
    g = {'fin_type': 'plain', 'tube_type': 'smooth', 'arrangement': 'staggered', 'rows': 2, 'tubes_per_row': 5,
         'circuits_count': 1, 'tube_length_m': 0.0843, 'tube_outer_diameter_m': 0.00952, 'tube_inner_diameter_m': 0.009,
         'transverse_pitch_m': 0.025, 'longitudinal_pitch_m': 0.0217, 'fin_pitch_m': 0.00423, 'fin_thickness_m': 0.00012,
         'fin_conductivity_w_m_k': 202.4, 'tube_conductivity_w_m_k': 387.6}
    a, b = geometry_metrics(g), geometry_metrics({**g, 'fin_count': 21})
    ja = wang_plain_fin(2300, a['collar_diameter_m'], a['air_hydraulic_diameter_m'], .025, .0217, .00423, 2)
    jb = wang_plain_fin(2300, b['collar_diameter_m'], b['air_hydraulic_diameter_m'], .025, .0217, .00423, 2)
    assert ja['colburn_j'] == pytest.approx(jb['colburn_j'], rel=1e-12)
    assert b['fin_area_m2'] / a['fin_area_m2'] == pytest.approx(21 / (0.0843 / 0.00423), rel=1e-12)
