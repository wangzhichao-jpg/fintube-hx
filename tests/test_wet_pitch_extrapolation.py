"""Declared wet-friction fin-pitch extrapolation (core 0.1.0.dev18; Pro 0.7.0.dev3 rework R6d, demand-side decision Q6).

Wang, Lin & Lee 2000 (wet, plain, non-hydrophilic) was fitted on 31 coils with fin pitch 1.19..3.2 mm.  With
geometry.wet_friction_fin_pitch_extrapolation = true the fin-pitch upper bound - and only that bound - is raised to
4.0 mm; the result carries an 'extrapolated' coverage item.  Without the declaration nothing changes (only the wet
increment is refused).  A negative extrapolated increment (f_wet < f_dry) is treated as a failed extrapolation."""
import json
from copy import deepcopy
from pathlib import Path

import pytest

from fintube_hx.engine import run_case
from fintube_hx.errors import ModelRangeError

EX = Path(__file__).resolve().parents[1] / 'examples'


def wet_case(pitch, **geometry):
    c = json.loads((EX / 'water_geometry.json').read_text(encoding='utf8'))
    c['air'].update(relative_humidity=0.6)                         # 27 C / 60 % over 7 C water: wet coil
    c['model']['pressure_scope'] = 'v1'
    c['geometry'].update({'fin_pitch_m': pitch, 'fin_surface': 'bare_aluminum', **geometry})
    return c


def coverage_ids(r, cat):
    return [i['id'] for i in r['model_coverage'][cat]]


def test_limit_constant():
    from fintube_hx.errors import WET_FRICTION_FIN_PITCH_EXTRAPOLATION_MAX_M
    assert WET_FRICTION_FIN_PITCH_EXTRAPOLATION_MAX_M == 0.004


def test_without_declaration_only_the_wet_increment_is_refused():
    r = run_case(wet_case(0.00324))
    assert isinstance(r['air_pressure_drop_breakdown_pa']['wet_increment'], dict)
    assert 'wet_increment_not_computed' in coverage_ids(r, 'degraded') and coverage_ids(r, 'extrapolated') == []


def test_declared_extrapolation_computes_the_increment_and_marks_it():
    r = run_case(wet_case(0.00324, wet_friction_fin_pitch_extrapolation=True))
    inc = r['air_pressure_drop_breakdown_pa']['wet_increment']
    assert isinstance(inc, float) and inc > 0
    assert 'wet_friction_fin_pitch_extrapolated' in coverage_ids(r, 'extrapolated')
    assert 'wet_increment_not_computed' not in coverage_ids(r, 'degraded')
    ext = r['air_wet_friction']['fin_pitch_extrapolated']
    assert ext['published_range_m'] == [0.00119, 0.0032] and ext['declared_limit_m'] == 0.004 and ext['value_m'] == 0.00324


def test_declared_extrapolation_up_to_the_limit():
    r = run_case(wet_case(0.004, wet_friction_fin_pitch_extrapolation=True))
    assert 'wet_friction_fin_pitch_extrapolated' in coverage_ids(r, 'extrapolated')


@pytest.mark.parametrize('pitch, extra, words', [
    (0.0030, {}, '不应声明'),                                       # inside the published range
    (0.0041, {}, '4 mm'),                                          # beyond the declared limit
    (0.00324, {'fin_surface': 'hydrophilic'}, '裸铝'),
    (0.00324, {'fin_type': 'louver', 'louver_pitch_m': 0.0017, 'louver_height_m': 0.0011}, '平片'),
])
def test_invalid_declarations_are_refused_in_chinese(pitch, extra, words):
    with pytest.raises(ModelRangeError) as e:
        run_case(wet_case(pitch, wet_friction_fin_pitch_extrapolation=True, **extra))
    assert words in str(e.value) and e.value.field.startswith('geometry.')


def test_declaration_must_be_true():
    with pytest.raises(ModelRangeError):
        run_case(wet_case(0.00324, wet_friction_fin_pitch_extrapolation=False))


def test_other_wet_bounds_are_not_extended(monkeypatch):
    """Only the fin pitch is extended: a transverse pitch outside 21..25.4 mm still refuses the wet increment."""
    r = run_case(wet_case(0.00324, wet_friction_fin_pitch_extrapolation=True, transverse_pitch_m=0.0270))
    assert isinstance(r['air_pressure_drop_breakdown_pa']['wet_increment'], dict)
    assert 'wet_friction_fin_pitch_extrapolated' not in coverage_ids(r, 'extrapolated')


def test_a_negative_extrapolated_increment_is_not_reported(monkeypatch):
    import fintube_hx.airside as A
    real = A.wet_friction_factor

    def tiny(*a, **k):
        out = real(*a, **k); out = deepcopy(out); out['fanning_friction_factor'] = 1e-6; return out
    monkeypatch.setattr(A, 'wet_friction_factor', tiny)
    r = run_case(wet_case(0.00324, wet_friction_fin_pitch_extrapolation=True))
    inc = r['air_pressure_drop_breakdown_pa']['wet_increment']
    assert isinstance(inc, dict) and '外推失效' in inc['not_computed']
    assert 'wet_friction_fin_pitch_extrapolated' not in coverage_ids(r, 'extrapolated')


def test_absent_key_leaves_results_unchanged_against_dev17():
    """Review A/M3: compared with results computed by core 0.1.0.dev17 itself (frozen digests), not with dev18."""
    import hashlib
    ref = json.loads((Path(__file__).parent / 'data/wet_absent_key_dev17_reference.json').read_text(encoding='utf8'))['cases']
    for key, digest in ref.items():
        pitch, rh = (float(x) for x in key.split('-'))
        c = wet_case(pitch); c['air']['relative_humidity'] = rh
        r = {k: v for k, v in run_case(c).items() if k != 'provenance'}
        assert hashlib.sha256(json.dumps(r, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest() == digest, key
        assert 'fin_pitch_extrapolated' not in r.get('air_wet_friction', {})


def test_a_dry_coil_with_the_declaration_has_no_extrapolated_item():
    c = wet_case(0.00324, wet_friction_fin_pitch_extrapolation=True); c['air']['relative_humidity'] = 0.2   # dry over 7 C water
    r = run_case(c)
    assert r['air_pressure_drop_basis']['wet_fraction'] == 0
    assert 'wet_friction_fin_pitch_extrapolated' not in coverage_ids(r, 'extrapolated')
