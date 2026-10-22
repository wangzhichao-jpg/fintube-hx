"""0.1.0.dev17 exact shortcuts: every value must be bit-identical to the full routines (T3 M3a)."""
import itertools
import json
from pathlib import Path
import pytest
from fintube_hx.properties import air_state, air_wh, air_from_h_w, air_from_h_w_wh
from fintube_hx.thermal import contact_air, air_with_h_w, air_with_h_w_wh
from fintube_hx.airside import air_side_factors_by_row, ROW6_LOCAL_J_FLOOR
from fintube_hx.geometry import geometry_metrics
from fintube_hx.errors import ModelRangeError
from fintube_hx.schema import normalize_solver

EX = Path(__file__).resolve().parents[1] / 'examples'
P = (101325.0, 95000.0)


def bits(x):
    return float(x).hex()


@pytest.mark.parametrize('t,rh,p', list(itertools.product((-5.0, 4.3, 12.7, 27.0, 41.9), (0.0, 0.31, 0.97, 1.0), P)))
def test_air_wh_equals_air_state(t, rh, p):
    s = air_state(t, rh, p)
    w, h = air_wh(t, rh, p)
    assert (bits(w), bits(h)) == (bits(s['humidity_ratio_kg_kg_da']), bits(s['enthalpy_j_kg_da']))


@pytest.mark.parametrize('t,rh,p', list(itertools.product((3.0, 18.5, 30.0), (0.2, 0.8, 1.0), P)))
def test_air_from_h_w_wh_equals_full(t, rh, p):
    s = air_state(t, rh, p)
    h, w = s['enthalpy_j_kg_da'] * (1 + 1e-7), s['humidity_ratio_kg_kg_da']
    full = air_from_h_w(h, w, p)
    assert tuple(map(bits, air_from_h_w_wh(h, w, p))) == (bits(full['humidity_ratio_kg_kg_da']), bits(full['enthalpy_j_kg_da']))
    fog = air_with_h_w(h, w * 1.05, p) if rh == 1.0 else air_with_h_w(h, w, p)
    fog_wh = air_with_h_w_wh(h, w * 1.05, p) if rh == 1.0 else air_with_h_w_wh(h, w, p)
    assert tuple(map(bits, fog_wh)) == (bits(fog['humidity_ratio_kg_kg_da']), bits(fog['enthalpy_j_kg_da']))


@pytest.mark.parametrize('ts,fraction', list(itertools.product((2.0, 8.0, 14.0, 22.0, 35.0), (0.0, 0.17, 0.63, 1.0))))
def test_contact_air_wh_only_heat_is_bit_identical(ts, fraction):
    air = air_state(27.0, 0.55, 101325.0)
    out, q, c = contact_air(air, ts, fraction, 0.3)
    out2, q2, c2 = contact_air(air, ts, fraction, 0.3, wh_only=True)
    assert (bits(q2), bits(c2)) == (bits(q), bits(c))
    assert set(out2) == {'humidity_ratio_kg_kg_da', 'enthalpy_j_kg_da'}
    assert all(bits(out2[k]) == bits(out[k]) for k in out2)
    _, q3, c3 = contact_air(air, ts, fraction, 0.3, outlet_state=False)
    if ts < air['dew_point_c']:                                  # wet branch: exact
        assert (bits(q3), bits(c3)) == (bits(q), bits(c))
    assert outcome(contact_air, air, ts, fraction, 0.3, wet=False) == outcome(contact_air, air, ts, fraction, 0.3, wet=False, wh_only=True)


def outcome(fn, *a, **k):
    """Heat (bits) or the raised exception, so that refusals must coincide as well."""
    try:
        return ('ok', bits(fn(*a, **k)[1]))
    except ValueError as exc:
        return ('raise', type(exc).__name__, str(exc))


def test_row6_local_j_floor():
    assert ROW6_LOCAL_J_FLOOR == 0.5
    g = json.loads((EX / 'water_geometry.json').read_text(encoding='utf8'))['geometry']
    g.update(fin_type='louver', louver_pitch_m=.0024, louver_height_m=.0014, transverse_pitch_m=.0254,
             longitudinal_pitch_m=.019, fin_pitch_m=.0018, rows=10, circuits_count=10, row_extrapolation='saturate_at_row_6')
    m = geometry_metrics(g)
    with pytest.raises(ModelRangeError, match='病态') as e:          # Re 800: j6/j(6) ~ 0.02 (T2 record)
        air_side_factors_by_row(g, m, 800.)
    assert e.value.allowed['j6_min'] > 0
    ok = air_side_factors_by_row(g, m, 3000.)['row_extrapolation']    # j6/j(6) ~ 0.77
    assert ok['j_local_6'] >= 0.5 * ok['j_bank_6']


def test_time_limit_field_is_optional_and_bounded():
    c = {'kind': 'water', 'model': {}, 'solver': {}}
    normalize_solver(c)
    assert 'time_limit_s' not in c['solver']
    c = {'kind': 'water', 'model': {}, 'solver': {'time_limit_s': 30}}
    normalize_solver(c)
    assert c['solver']['time_limit_s'] == 30.0
    with pytest.raises(ValueError):
        normalize_solver({'kind': 'water', 'model': {}, 'solver': {'time_limit_s': 0}})
