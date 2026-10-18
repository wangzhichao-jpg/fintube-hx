"""0.1.0.dev9: louver / herringbone-wavy j-f correlations and Schmidt fin efficiency."""
import copy, json, math
from pathlib import Path
import pytest
from ht import fin_efficiency_Kern_Kraus
from fintube_hx.engine import run_case
from fintube_hx.geometry import geometry_metrics
from fintube_hx.airside import (wang_louver_1999, wang_herringbone_2002, air_side_factors,
                                schmidt_fin_efficiency, fin_efficiency)
from fintube_hx.wang_plain_fin import wang_plain_fin

ROOT = Path(__file__).resolve().parents[1]
BASE = json.loads((ROOT / 'examples/water_geometry.json').read_text(encoding='utf8'))
COIL = dict(tube_outer_diameter_m=0.00952, tube_inner_diameter_m=0.0089, transverse_pitch_m=0.0254,
            longitudinal_pitch_m=0.022, fin_pitch_m=0.0018)
LOUVER = dict(fin_type='louver', louver_pitch_m=0.0024, louver_height_m=0.0012)
WAVY = dict(fin_type='wavy_herringbone', wave_height_m=0.00118, wave_projected_length_m=0.00476)


def case(**upd):
    c = copy.deepcopy(BASE); c['geometry'].update(COIL); c['geometry'].update(upd); return c


def test_plain_dispatch_is_the_legacy_function():
    g = case()['geometry']; m = geometry_metrics(g)
    a = air_side_factors(g, m, 1500.)
    b = wang_plain_fin(1500., m['collar_diameter_m'], m['air_hydraulic_diameter_m'], g['transverse_pitch_m'],
                       g['longitudinal_pitch_m'], g['fin_pitch_m'], g['rows'])
    assert a == b
    h = 60.
    assert fin_efficiency(g, m, h) == fin_efficiency_Kern_Kraus(m['collar_diameter_m'], m['equivalent_annular_fin_outer_diameter_m'],
                                                                g['fin_thickness_m'], g['fin_conductivity_w_m_k'], h)


def test_regression_values_transcribed_equations():
    # Pinned values of the transcribed equations (cross-checked for herringbone against an
    # independent implementation in the private validation record; see U2 record).
    lv = wang_louver_1999(1500., .00974, .00229, .0254, .022, .0018, 3, .0024, .0012, 18.)
    assert lv['colburn_j'] == pytest.approx(0.0272546858, rel=1e-8)   # Eq. (23)-(27) evaluated by hand
    assert lv['branches'] == ['Eq23_Re_ge_1000', 'Eq34_N_gt_1']
    hb = wang_herringbone_2002(800., .00862, .00216, .0254, .01905, .0017, .00012, 2, .00118, .00476)
    assert hb['branches'] == ['Eq31_Re_lt_1000', 'Eq38_Re_lt_1000']
    assert hb['corrugation_angle_deg'] == pytest.approx(math.degrees(math.atan(1.18 / 4.76)))


def test_ranges_are_enforced():
    with pytest.raises(ValueError, match='louver height/pitch'):
        wang_louver_1999(1500., .00974, .00229, .0254, .022, .0018, 3, .0037, .0008, 18.)
    with pytest.raises(ValueError, match='Re'):
        wang_louver_1999(9000., .00974, .00229, .0254, .022, .0018, 3, .0024, .0012, 18.)
    with pytest.raises(ValueError, match='corrugation angle'):
        wang_herringbone_2002(1500., .00862, .00216, .0254, .01905, .0017, .00012, 2, .0018, .0040)


def test_schmidt_close_to_exact_annular_fin_at_equivalent_radius():
    dc, pt, pl, t, k = .00974, .0254, .022, .0001, 200.
    r = dc / 2; xm = pt / 2; xl = math.hypot(pt / 2, pl) / 2
    req = r * 1.27 * xm / r * math.sqrt(xl / xm - .3)
    for h in (20., 60., 150.):
        exact = fin_efficiency_Kern_Kraus(dc, 2 * req, t, k, h)
        assert schmidt_fin_efficiency(dc, pt, pl, 3, t, k, h) == pytest.approx(exact, rel=0.03)
    assert schmidt_fin_efficiency(dc, pt, pl, 3, t, k, 1e-9) == pytest.approx(1., abs=1e-6)


def test_geometry_rules_and_wavy_area():
    p = geometry_metrics(case()['geometry']); w = geometry_metrics(case(**WAVY)['geometry'])
    sec = math.hypot(4.76, 1.18) / 4.76
    assert w['fin_area_enhancement_sec_theta'] == pytest.approx(sec)
    assert w['minimum_air_area_m2'] == p['minimum_air_area_m2']
    assert w['fin_area_m2'] > p['fin_area_m2'] and w['air_hydraulic_diameter_m'] < p['air_hydraulic_diameter_m']
    assert geometry_metrics(case(**LOUVER)['geometry'])['fin_area_m2'] == p['fin_area_m2']
    for bad in (dict(fin_type='louver', louver_pitch_m=.0024), dict(louver_pitch_m=.0024, louver_height_m=.0012),
                dict(WAVY, louver_height_m=.001), dict(fin_efficiency_method='exact')):
        with pytest.raises(ValueError):
            geometry_metrics(case(**bad)['geometry'])


@pytest.mark.parametrize('upd', [LOUVER, WAVY, dict(fin_efficiency_method='schmidt')])
def test_lumped_coil_runs_dry_and_wet(upd):
    for rh, model in ((0.2, None), (0.6, 'threlkeld_braun')):
        c = case(**upd); c['air']['relative_humidity'] = rh
        if model:
            c['model']['wet_surface_model'] = model
        r = run_case(c)
        assert r['converged'] and r['energy_balance_relative_error'] < 1e-9
        gm = r['geometry_model']
        assert gm['geometry']['fin_type'] == upd.get('fin_type', 'plain')
        if 'fin_type' in upd:
            assert any('Wang' in w for w in r['warnings'])
    plain = run_case(case()); louver = run_case(case(**LOUVER))
    assert louver['geometry_model']['air_h_w_m2_k'] > plain['geometry_model']['air_h_w_m2_k']
    assert louver['geometry_model']['air_core_friction_pressure_drop_pa'] > plain['geometry_model']['air_core_friction_pressure_drop_pa']


def test_declared_boundary_extrapolation_is_limited_and_disclosed():
    # CETIAT-like: Pt 25.5 mm and Fp 2.5 mm exceed the louver sample maxima 25.4 / 2.49 mm by 0.4 %.
    upd = dict(LOUVER, transverse_pitch_m=0.0255, fin_pitch_m=0.0025)
    with pytest.raises(ValueError, match='outside published sample range'):
        run_case(case(**upd))
    r = run_case(case(**upd, correlation_range_tolerance=0.005))
    ext = r['geometry_model']['air_correlation']['range_extrapolation']
    assert set(ext) == {'transverse pitch', 'fin pitch'}
    assert ext['fin pitch']['relative_excess'] == pytest.approx(0.0025 / 0.00249 - 1)
    assert any(w.startswith('边界外推') for w in r['warnings'])
    for bad in (0.02, 0.0, -0.001):
        with pytest.raises(ValueError, match='correlation_range_tolerance'):
            geometry_metrics(case(**upd, correlation_range_tolerance=bad)['geometry'])
    with pytest.raises(ValueError, match='only to louver'):
        geometry_metrics(case(correlation_range_tolerance=0.005)['geometry'])
    with pytest.raises(ValueError, match='Re'):        # Re is never extended
        wang_louver_1999(8010., .00974, .00229, .0254, .022, .0018, 3, .0024, .0012, 18., range_tolerance=0.01)
