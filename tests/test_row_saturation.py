"""7..12-row declared saturation (contract 2.1, spec C1/P4), checked against direct correlation calls."""
import json
from pathlib import Path
import pytest
from fintube_hx import airside
from fintube_hx.airside import air_side_factors, air_side_factors_by_row
from fintube_hx.geometry import geometry_metrics, validate_geometry
from fintube_hx.wang_plain_fin import wang_plain_fin
from fintube_hx.engine import run_case
from fintube_hx.errors import ModelRangeError

EX = Path(__file__).resolve().parents[1] / 'examples'


def geom(rows, **kw):
    g = json.loads((EX / 'water_geometry.json').read_text(encoding='utf8'))['geometry']
    g.update(rows=rows, circuits_count=rows, **kw)
    return g


@pytest.mark.parametrize('rows', [1, 3, 6])
def test_up_to_six_rows_every_row_is_the_bank_value(rows):
    g = geom(rows); m = geometry_metrics(g)
    out = air_side_factors_by_row(g, m, 2000.)
    bank = air_side_factors(g, m, 2000.)
    assert out['row_extrapolation'] is None and len(out['rows']) == rows
    assert all(r['colburn_j'] == bank['colburn_j'] and r['fanning_friction_factor'] == bank['fanning_friction_factor'] for r in out['rows'])


@pytest.mark.parametrize('rows', [7, 9, 12])
def test_declared_saturation_matches_hand_difference(rows):
    g = geom(rows, row_extrapolation='saturate_at_row_6'); m = geometry_metrics(g)
    Re = 2000.
    a = [m['collar_diameter_m'], m['air_hydraulic_diameter_m'], g['transverse_pitch_m'], g['longitudinal_pitch_m'], g['fin_pitch_m']]
    w6, w5 = wang_plain_fin(Re, *a, 6), wang_plain_fin(Re, *a, 5)
    j6 = 6 * w6['colburn_j'] - 5 * w5['colburn_j']
    f6 = 6 * w6['fanning_friction_factor'] - 5 * w5['fanning_friction_factor']
    out = air_side_factors_by_row(g, m, Re)
    assert [r['basis'] for r in out['rows']] == ['bank_average_N6'] * 6 + ['local_row6_saturated'] * (rows - 6)
    assert all(r['colburn_j'] == w6['colburn_j'] for r in out['rows'][:6])
    assert all(r['colburn_j'] == pytest.approx(j6, rel=1e-15) and r['fanning_friction_factor'] == pytest.approx(f6, rel=1e-15)
               for r in out['rows'][6:])
    assert out['bank_average']['colburn_j'] == pytest.approx((6 * w6['colburn_j'] + (rows - 6) * j6) / rows, rel=1e-14)
    assert 0 < j6 <= wang_plain_fin(Re, *a, 1)['colburn_j']
    # Wang plain f grows weakly with N (c1 has -0.00758/N): the local f6 exceeds the 1-row value, which is
    # why contract v1.1 bounds only f6 > 0.
    assert f6 > wang_plain_fin(Re, *a, 1)['fanning_friction_factor'] > 0


def test_declaration_rules():
    with pytest.raises(ModelRangeError) as e:
        validate_geometry(geom(8))
    assert e.value.fallbacks[0]['patch'] == {'geometry.row_extrapolation': 'saturate_at_row_6'}
    assert 'restricted to 1..6 rows' in str(e.value)                 # legacy English kept in parentheses
    with pytest.raises(ModelRangeError, match='13'):
        validate_geometry(geom(13, row_extrapolation='saturate_at_row_6'))
    with pytest.raises(ModelRangeError, match='不应声明'):
        validate_geometry(geom(4, row_extrapolation='saturate_at_row_6'))
    with pytest.raises(ModelRangeError, match='saturate_at_row_6'):
        validate_geometry(geom(8, row_extrapolation='linear'))
    g = geom(8, row_extrapolation='saturate_at_row_6')
    with pytest.raises(ModelRangeError, match='6 排'):
        air_side_factors(g, geometry_metrics(g), 2000.)


def test_lumped_model_rejects_extrapolated_rows():
    c = json.loads((EX / 'water_geometry.json').read_text(encoding='utf8'))
    c['geometry'].update(rows=8, circuits_count=4, row_extrapolation='saturate_at_row_6')
    with pytest.raises(ModelRangeError, match='集总'):
        run_case(c)


def test_nonphysical_local_value_raises_instead_of_switching(monkeypatch):
    real = airside.air_side_factors

    def fake(g, m, Re):
        r = dict(real(g, m, Re))
        if g['rows'] == 5:
            r['colburn_j'] = r['colburn_j'] * 1.5        # makes j6 = 6 j(6) - 5 j(5) negative
        return r
    monkeypatch.setattr(airside, 'air_side_factors', fake)
    g = geom(8, row_extrapolation='saturate_at_row_6')
    with pytest.raises(ModelRangeError, match='不适用'):
        air_side_factors_by_row(g, geometry_metrics(g), 2000.)
