"""Declared plain-fin pitch extrapolation 8.7..12 mm (contract 2.1, spec C2/P5)."""
import json
from pathlib import Path
import pytest
from fintube_hx.airside import air_side_factors
from fintube_hx.geometry import geometry_metrics, validate_geometry
from fintube_hx.wang_plain_fin import wang_plain_fin
from fintube_hx.engine import run_case
from fintube_hx.errors import ModelRangeError

EX = Path(__file__).resolve().parents[1] / 'examples'


def geom(pitch, **kw):
    g = json.loads((EX / 'water_geometry.json').read_text(encoding='utf8'))['geometry']
    # Pt 25.4 / Pl 12.7 mm keeps Dh inside Wang's range at the published 8.7 mm pitch (the example's
    # Pt 25 / Pl 22 mm already exceeds Dh 9.37 mm there, which correctly blocks the declaration).
    g.update(transverse_pitch_m=0.0254, longitudinal_pitch_m=0.0127, fin_pitch_m=pitch, **kw)
    return g


def test_undeclared_large_pitch_offers_the_declaration():
    g = geom(0.010); m = geometry_metrics(g)
    with pytest.raises(ModelRangeError) as e:
        air_side_factors(g, m, 2000.)
    assert e.value.field == 'geometry.fin_pitch_m'
    assert {'geometry.fin_pitch_extrapolation': True} in [f['patch'] for f in e.value.fallbacks]


def test_declared_pitch_uses_unchanged_equations_and_discloses():
    g = geom(0.010, fin_pitch_extrapolation=True); m = geometry_metrics(g)
    r = air_side_factors(g, m, 2000.)
    a = (2000., m['collar_diameter_m'], m['air_hydraulic_diameter_m'], g['transverse_pitch_m'], g['longitudinal_pitch_m'], .010, g['rows'])
    same = wang_plain_fin(*a, extended_upper={'fin pitch': .012, 'hydraulic diameter': 1.0})
    assert r['colburn_j'] == same['colburn_j'] and r['fanning_friction_factor'] == same['fanning_friction_factor']
    assert r['range_extrapolation']['fin pitch']['published_range'] == [0.001, 0.0087]
    assert r['range_extrapolation_basis'] == 'fin_pitch_extrapolation'


def test_continuity_across_the_published_bound():
    inside = geom(0.0087); m0 = geometry_metrics(inside)
    outside = geom(0.0087 * (1 + 1e-6), fin_pitch_extrapolation=True); m1 = geometry_metrics(outside)
    a, b = air_side_factors(inside, m0, 2000.), air_side_factors(outside, m1, 2000.)
    assert b['colburn_j'] == pytest.approx(a['colburn_j'], rel=1e-5)
    assert b['fanning_friction_factor'] == pytest.approx(a['fanning_friction_factor'], rel=1e-5)


@pytest.mark.parametrize('pitch,kw', [(0.008, {'fin_pitch_extrapolation': True}), (0.013, {'fin_pitch_extrapolation': True}),
                                      (0.010, {'fin_pitch_extrapolation': 'yes'})])
def test_declaration_bounds(pitch, kw):
    with pytest.raises(ModelRangeError):
        validate_geometry(geom(pitch, **kw))


def test_louver_cannot_use_pitch_extrapolation():
    g = geom(0.002, fin_type='louver', louver_pitch_m=.0024, louver_height_m=.0014, fin_pitch_extrapolation=True)
    with pytest.raises(ModelRangeError, match='平片'):
        validate_geometry(g)


def test_lumped_coil_result_is_flagged():
    c = json.loads((EX / 'water_geometry.json').read_text(encoding='utf8'))
    c['geometry'].update(transverse_pitch_m=0.0254, longitudinal_pitch_m=0.0127, fin_pitch_m=0.010, fin_pitch_extrapolation=True)
    r = run_case(c)
    assert any(w.startswith('边界外推：按声明的fin_pitch_extrapolation') for w in r['warnings'])
    assert [i['id'] for i in r['model_coverage']['extrapolated']] == ['plain_fin_pitch_gt_8_7mm']


def test_dh_excess_not_caused_by_pitch_blocks_the_declaration():
    g = geom(0.010, fin_pitch_extrapolation=True)
    g.update(transverse_pitch_m=0.025, longitudinal_pitch_m=0.022)     # Dh at 8.7 mm = 9.51 mm > 9.37 mm
    with pytest.raises(ModelRangeError, match='8.7 mm'):
        air_side_factors(g, geometry_metrics(g), 2000.)
