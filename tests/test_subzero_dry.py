"""0.1.0.dev11: optional dry sub-zero evaporation (model.subzero_evaporation=dry_only)."""
import copy, json
from pathlib import Path
import pytest
from CoolProp.CoolProp import PropsSI
from fintube_hx.engine import run_case
from fintube_hx.properties import air_state
from fintube_hx.thermal import check_subzero_surface

ROOT = Path(__file__).resolve().parents[1]


def sub_zero_case(rh, mode=None, t_evap=-3.0):
    c = json.loads((ROOT / 'examples/evaporator.json').read_text(encoding='utf8'))
    p = PropsSI('P', 'T', t_evap + 273.15, 'Q', 0, c['fluid']['name'])
    h0, h1 = PropsSI('H', 'P', p, 'Q', 0, c['fluid']['name']), PropsSI('H', 'P', p, 'Q', 1, c['fluid']['name'])
    c['fluid'] = {'name': c['fluid']['name'], 'pressure_pa': p, 'inlet_h_j_kg': h0 + 0.2 * (h1 - h0),
                  'mass_flow_kg_s': c['fluid']['mass_flow_kg_s']}
    c['air']['relative_humidity'] = rh; c['air']['t_db_c'] = 20.0
    c.pop('target', None)
    if mode:
        c['model']['subzero_evaporation'] = mode
    return c


def test_frost_point_rule():
    dry = air_state(20.0, 0.10, 101325.0)       # frost point about -12 C
    assert check_subzero_surface(-3.0, dry, 'dry_only') is True
    assert check_subzero_surface(1.0, dry, 'reject') is False
    with pytest.raises(ValueError, match='frost model'):
        check_subzero_surface(-3.0, dry, 'reject')
    humid = air_state(20.0, 0.50, 101325.0)     # dew point about 9 C
    with pytest.raises(ValueError, match='frost point'):
        check_subzero_surface(-3.0, humid, 'dry_only')


def test_default_still_rejects_and_dry_only_runs_without_condensate():
    with pytest.raises(ValueError, match='frost'):
        run_case(sub_zero_case(0.10))
    r = run_case(sub_zero_case(0.10, 'dry_only'))
    assert r['converged'] and r['condensate_kg_s'] == 0.0
    assert any('霜点' in w for w in r['warnings'])
    with pytest.raises(ValueError, match='frost point'):
        run_case(sub_zero_case(0.50, 'dry_only'))


def test_field_rules():
    c = json.loads((ROOT / 'examples/condenser.json').read_text(encoding='utf8'))
    c['model']['subzero_evaporation'] = 'dry_only'
    with pytest.raises(ValueError, match='only to evaporators'):
        run_case(c)
    with pytest.raises(ValueError, match='reject or dry_only'):
        run_case(sub_zero_case(0.10, 'always'))
