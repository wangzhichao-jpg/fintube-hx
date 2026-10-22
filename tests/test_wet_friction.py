"""Wang, Lin & Lee 2000 wet plain-fin friction (IJHMT 43:1869), spec A2/A4.

The expected value is an independent re-transcription of Eqs. (11)-(15) from the 300 dpi page images
(page 1872), written here without importing the production expression.
"""
import math
import pytest
from fintube_hx.airside import wang_lin_lee_2000_wet_plain, wet_friction_factor, WET_PLAIN_RANGE
from fintube_hx.geometry import geometry_metrics
from fintube_hx.errors import ModelRangeError

GEOM = {'fin_type': 'plain', 'tube_type': 'smooth', 'arrangement': 'staggered', 'rows': 2, 'tubes_per_row': 20,
        'circuits_count': 4, 'tube_length_m': 0.5, 'tube_outer_diameter_m': 0.0095, 'tube_inner_diameter_m': 0.0087,
        'transverse_pitch_m': 0.025, 'longitudinal_pitch_m': 0.022, 'fin_pitch_m': 0.002, 'fin_thickness_m': 0.0001,
        'fin_conductivity_w_m_k': 205.0, 'tube_conductivity_w_m_k': 385.0, 'fin_surface': 'bare_aluminum'}


def paper_f(Re, Dc, Dh, Pt, Pl, Fp, AoApo, Ref):
    f1 = -0.7339 + 7.187 * (Fp / Pl) ** 2.5 * math.log(9 * Ref)
    f2 = -0.5417 * math.log(AoApo) * (Fp / Dc) ** 0.9
    f3 = 0.02722 * math.log(6 * Ref) * (Pl / Pt) ** 3.2 * math.log(Re)
    f4 = 0.2973 * math.log(AoApo) * math.log(Dh / Dc)
    return (16.55 * Re ** f1 * (10 * Ref) ** f2 * AoApo ** f3 * (Pl / Pt) ** f4 * (Fp / Dh) ** (-0.5827)
            * (math.e ** (Dh / Dc)) ** (-1.117))


@pytest.mark.parametrize('Re,Ref', [(400., 0.3), (1500., 1.0), (4800., 3.0)])
def test_equations_match_independent_transcription(Re, Ref):
    m = geometry_metrics(GEOM)
    ao = m['total_outer_area_m2'] / m['bare_outer_area_m2']
    r = wang_lin_lee_2000_wet_plain(Re, m['collar_diameter_m'], m['air_hydraulic_diameter_m'], .025, .022, .002, 2, ao, Ref)
    assert r['fanning_friction_factor'] == pytest.approx(
        paper_f(Re, m['collar_diameter_m'], m['air_hydraulic_diameter_m'], .025, .022, .002, ao, Ref), rel=1e-13)
    assert 'entrance/exit losses included' in r['friction_definition']


def test_published_sample_range_from_table_1():
    assert WET_PLAIN_RANGE['collar diameter'] == (.00753, .01034)      # samples 10-13 / 1-9
    assert WET_PLAIN_RANGE['fin pitch'] == (.00119, .0032)             # samples 30 / 3
    assert WET_PLAIN_RANGE['longitudinal pitch'] == (.0124, .022)
    assert WET_PLAIN_RANGE['transverse pitch'] == (.021, .0254)
    assert WET_PLAIN_RANGE['Re'] == (300., 5000.) and WET_PLAIN_RANGE['rows'] == (1, 6)
    m = geometry_metrics(GEOM)
    with pytest.raises(ModelRangeError, match='Re_Dc'):
        wang_lin_lee_2000_wet_plain(5200., m['collar_diameter_m'], m['air_hydraulic_diameter_m'], .025, .022, .002, 2, 10., 1.)


def test_condensate_film_reynolds_definition():
    m = geometry_metrics(GEOM)
    mc, mu = 8e-4, 1.3e-3
    r = wet_friction_factor(GEOM, m, 1500., mc, mu)
    assert r['re_film'] == pytest.approx(2 * (mc / (2 * 0.5)) / mu, rel=1e-15)   # Gamma = mc/(N*W), W = tube length


def test_wet_increment_refused_not_the_calculation():
    m = geometry_metrics(GEOM)
    assert 'not_computed' in wet_friction_factor({**GEOM, 'fin_surface': 'hydrophilic'}, m, 1500., 8e-4, 1.3e-3)
    louver = {**GEOM, 'fin_type': 'louver', 'louver_pitch_m': .0024, 'louver_height_m': .0014}
    assert '原文尚未取得' in wet_friction_factor(louver, m, 1500., 8e-4, 1.3e-3)['not_computed']
    big = {**GEOM, 'fin_pitch_m': .0034}
    out = wet_friction_factor(big, geometry_metrics(big), 1500., 8e-4, 1.3e-3)
    assert '超出适用范围' in out['not_computed'] and '片距' in out['not_computed']
    zero = wet_friction_factor(GEOM, m, 1500., 0.0, 1.3e-3)
    assert 'not_computed' in zero
