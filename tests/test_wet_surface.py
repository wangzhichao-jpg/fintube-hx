import copy, json, math
from pathlib import Path
import pytest
from fintube_hx.engine import run_case
from fintube_hx.properties import air_state
from fintube_hx.wet_surface import wet_element, saturated_enthalpy, _SaturationCurve

ROOT = Path(__file__).resolve().parents[1]
BASE = json.loads((ROOT / 'examples/water_geometry.json').read_text(encoding='utf8'))


def humid(rh, model=None):
    c = copy.deepcopy(BASE); c['air']['relative_humidity'] = rh
    if model:
        c['model']['wet_surface_model'] = model
    return c


def test_saturation_interpolant_matches_coolprop():
    s = _SaturationCurve(101325.0, 2.0, 35.0)
    for t in (2.0, 7.3, 15.0, 22.2, 35.0):
        assert s.i(t) == pytest.approx(saturated_enthalpy(t, 101325.0), rel=1e-6)
        assert s.t_of(s.i(t)) == pytest.approx(t, abs=1e-8)


def test_analytic_limit_constant_surface_unit_fin_efficiency():
    # No inner resistance, fin efficiency 1, constant-temperature coolant:
    # Q = m (i_in - i_s(Tf)) (1 - exp(-hA/(cp m))) exactly (Braun et al. 1989, Le=1).
    air = air_state(27.0, 0.6, 101325.0); m, h, a, tf = 0.2, 60.0, 8.0, 8.0
    r = wet_element(air, m, h, a, 6.0, lambda hh: 1.0, tf, None, 0.0)
    expected = m * (air['enthalpy_j_kg_da'] - saturated_enthalpy(tf, 101325.0)) * -math.expm1(-h * a / (air['cp_j_kg_da_k'] * m))
    assert r['air_enthalpy_drop_w'] == pytest.approx(expected, rel=2e-6)
    assert r['tube_base_t_c'] == pytest.approx(tf, abs=1e-6)


def test_balances_and_bounds():
    air = air_state(27.0, 0.6, 101325.0); m = 0.2
    from ht import fin_efficiency_Kern_Kraus
    fe = lambda hh: fin_efficiency_Kern_Kraus(0.0097, 0.026, 0.0001, 205.0, hh)
    r = wet_element(air, m, 55.0, 8.0, 7.2, fe, 7.0, 0.2 * 4190, 1e-3, 'counterflow')
    out = r['air_out']
    assert r['condensate_kg_s'] == pytest.approx(m * (air['humidity_ratio_kg_kg_da'] - out['humidity_ratio_kg_kg_da']), rel=1e-12)
    assert r['heat_to_fluid_w'] == pytest.approx(r['air_enthalpy_drop_w'] - r['condensate_enthalpy_rate_w'], rel=1e-12)
    assert out['relative_humidity'] <= 1.0 and out['humidity_ratio_kg_kg_da'] < air['humidity_ratio_kg_kg_da']
    assert 7.0 < r['effective_surface_t_c'] < air['dew_point_c']
    assert r['wet_fin_efficiency'] < fe(55.0)          # Threlkeld: wet fin less efficient


def test_not_admissible_when_air_is_dry():
    air = air_state(27.0, 0.15, 101325.0)
    assert wet_element(air, 0.2, 60.0, 8.0, 7.0, lambda h: 1.0, 7.0, None, 1e-3) is None


def test_legacy_unchanged_without_field_and_with_contact_factor():
    for rh in (0.2, 0.6):
        a, b = run_case(humid(rh)), run_case(humid(rh, 'contact_factor'))
        assert a['heat_transfer_w'] == b['heat_transfer_w']
        assert a['air_out'] == b['air_out'] and 'wet_surface_model' not in a


def test_strict_lumped_coil_physics():
    for rh in (0.45, 0.6, 0.9):
        r = run_case(humid(rh, 'threlkeld_braun'))
        assert r['converged'] and r['air_surface_condition'] == 'wet'
        assert r['energy_balance_relative_error'] < 1e-9
        assert r['air_out']['relative_humidity'] <= 1.0
        assert r['air_out']['t_db_c'] > r['fluid_in']['temperature_c']
        assert r['condensate_kg_s'] > 0 and r['wet_surface_model'] == 'threlkeld_braun'
    dry = run_case(humid(0.2, 'threlkeld_braun'))
    assert dry['air_surface_condition'] == 'dry' and dry['heat_transfer_w'] == run_case(humid(0.2))['heat_transfer_w']


def test_dry_wet_transition_is_continuous():
    # Braun's larger-of rule switches near RH 0.41 here; with RH steps of 0.002 no step
    # may exceed 0.5 % (the smooth wet-branch slope is about 0.2-0.4 % per step).
    runs = [run_case(humid(0.400 + 0.002 * k, 'threlkeld_braun')) for k in range(16)]
    q = [r['heat_transfer_w'] for r in runs]
    assert {r['air_surface_condition'] for r in runs} == {'dry', 'wet'}
    assert max(abs(b - a) / a for a, b in zip(q, q[1:])) < 0.005
    assert all(b >= a - 1e-6 for a, b in zip(q, q[1:]))


def test_schema_rejects_bad_or_inactive_field():
    with pytest.raises(ValueError):
        run_case(humid(0.6, 'exact'))
    c = json.loads((ROOT / 'examples/water_wet.json').read_text(encoding='utf8'))
    c['model']['wet_surface_model'] = 'threlkeld_braun'
    with pytest.raises(ValueError):
        run_case(c)
