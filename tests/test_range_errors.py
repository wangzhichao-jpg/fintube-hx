"""Structured Chinese range errors (contract section 4, spec C4/C5)."""
import json
from pathlib import Path
import pytest
from fintube_hx.errors import ModelRangeError, UnsupportedFeatureError
from fintube_hx.geometry import validate_geometry
from fintube_hx.engine import run_case

EX = Path(__file__).resolve().parents[1] / 'examples'


def geom(**kw):
    g = json.loads((EX / 'water_geometry.json').read_text(encoding='utf8'))['geometry']
    g.update(kw)
    return g


def test_error_types_stay_compatible():
    e = UnsupportedFeatureError('中文', message_en='english')
    assert isinstance(e, ModelRangeError) and isinstance(e, ValueError) and isinstance(e, NotImplementedError)
    assert str(e) == '中文（english）' and e.to_dict()['message_en'] == 'english'


@pytest.mark.parametrize('kw,field,word', [
    ({'fin_type': 'slit'}, 'geometry.fin_type', '条缝片'),
    ({'fin_type': 'bridge'}, 'geometry.fin_type', '原文尚未取得'),
    ({'tube_type': 'flat'}, 'geometry.tube_type', '扁管'),
    ({'arrangement': 'inline'}, 'geometry.arrangement', '顺排'),
])
def test_planned_features_are_refused_in_chinese(kw, field, word):
    with pytest.raises(UnsupportedFeatureError) as e:
        validate_geometry(geom(**kw))
    assert e.value.field == field and word in str(e.value) and '本版本不支持，规划中' in str(e.value)
    assert 'Geometry baseline supports plain' in str(e.value)        # legacy English retained


def test_small_tube_is_planned_not_a_plain_range_error():
    c = json.loads((EX / 'water_geometry.json').read_text(encoding='utf8'))
    c['geometry'].update(tube_outer_diameter_m=0.005, tube_inner_diameter_m=0.0045, transverse_pitch_m=0.021)
    with pytest.raises(UnsupportedFeatureError) as e:
        run_case(c)
    assert e.value.field == 'geometry.tube_outer_diameter_m' and '小管径' in str(e.value)
    assert e.value.allowed['min'] == 0.0069 and 'outside validated correlation range' in str(e.value)


def test_correlation_range_error_carries_field_and_range():
    c = json.loads((EX / 'water_geometry.json').read_text(encoding='utf8'))
    c['air']['volume_flow_m3_h'] = 20.0
    with pytest.raises(ModelRangeError) as e:
        run_case(c)
    d = e.value.to_dict()
    assert d['field'] == 'air.volume_flow_m3_h' and d['allowed'] == {'min': 300.0, 'max': 20000.0}
    assert '雷诺数' in d['message_zh'] and 'Wang' in d['source']


def test_unknown_mixture_refrigerant():
    c = json.loads((EX / 'evaporator.json').read_text(encoding='utf8'))
    c['fluid']['name'] = 'R454B'
    with pytest.raises(UnsupportedFeatureError, match='R454B') as e:
        run_case(c)
    assert e.value.field == 'fluid.name' and '规划中' in str(e.value)


def test_fallback_patch_makes_the_case_run():
    c = json.loads((EX / 'water_geometry.json').read_text(encoding='utf8'))
    c['geometry'].update(transverse_pitch_m=0.0254, longitudinal_pitch_m=0.0127, fin_pitch_m=0.010)
    with pytest.raises(ModelRangeError) as e:
        run_case(c)
    for path, value in e.value.fallbacks[0]['patch'].items():
        section, key = path.split('.')
        c[section][key] = value
    assert run_case(c)['converged']
