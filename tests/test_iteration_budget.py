"""Counterflow axial iteration budget: scale defaults, preserve explicit limits."""
from copy import deepcopy
from pathlib import Path
import json
import pytest
from fintube_hx.schema import validate_case,recommended_iteration_budget
from fintube_hx.engine import run_case
ROOT=Path(__file__).resolve().parents[1]
def example(name):return json.loads((ROOT/'examples'/name).read_text(encoding='utf8'))

@pytest.mark.parametrize('segments,expected',[(20,200),(80,200),(160,340),(320,660),(400,820)])
def test_default_budget_scales_with_refrigerant_segments(segments,expected):
    c=example('condenser.json');c['model']['segments']=segments;c['solver'].pop('max_iterations')
    original=deepcopy(c);n=validate_case(c)
    assert c==original and n['solver']['max_iterations']==expected
    assert recommended_iteration_budget(n)==expected


def test_explicit_budget_is_preserved_and_disclosed():
    c=example('condenser.json');c['model']['segments']=20;c['solver']['max_iterations']=1
    n=validate_case(c);assert n['solver']['max_iterations']==1
    r=run_case(c)
    assert not r['converged']
    assert r['iteration_budget']['configured_max_iterations']==1
    assert r['iteration_budget']['recommended_max_iterations']==200
    assert any('保留显式上限' in w for w in r['warnings'])


def test_water_and_real_tube_network_do_not_inherit_axial_budget():
    c=example('water_dry.json');c['model']['segments']=320;c['solver'].pop('max_iterations')
    assert validate_case(c)['solver']['max_iterations']==200
    # Shared policy is also invoked by an extending edition for network cases.
    c={'kind':'evaporator','model':{'refrigerant_model':'tube_network','axial_segments_per_tube':32}}
    assert recommended_iteration_budget(c)==200
