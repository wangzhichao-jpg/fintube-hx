"""Strict same-platform proof comparator: no numerical tolerance or broad exclusions."""
import importlib.util
from pathlib import Path


def tool():
    p = Path(__file__).resolve().parents[1] / 'tools/absent_key_dual_run.py'
    s = importlib.util.spec_from_file_location('dual', p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


def test_one_ulp_and_signed_zero_are_not_equal():
    import math
    compare = tool().exact_differences
    assert compare(1.0, math.nextafter(1.0, 2.0))
    assert compare(0.0, -0.0)
    assert not compare(1.0, 1.0)


def test_keys_types_strings_warnings_coverage_and_provenance_are_compared():
    compare = tool().exact_differences
    for a, b in [(1, 1.0), (True, 1), ({'a': 1}, {}), (['x'], ['y']),
                 ({'warnings': []}, {'warnings': ['changed']}),
                 ({'model_coverage': {'included': []}}, {'model_coverage': {'included': ['changed']}}),
                 ({'provenance': {'source': 'x'}}, {'provenance': {'source': 'y'}})]:
        assert compare(a, b), (a, b)


def test_only_precisely_registered_runtime_values_are_accepted():
    m = tool()
    base = {'provenance': {'version': '0.1.0.dev17', 'calculated_at_utc': '2026-10-01T00:00:00+00:00'}}
    new = {'provenance': {'version': '0.1.0.dev19', 'calculated_at_utc': '2026-10-02T00:00:00+00:00'}}
    assert len(m.exact_differences(base, new)) == 2
    assert not m.result_differences(base, new)[0]
    new['provenance']['version'] = 'wrong'
    assert m.result_differences(base, new)[0]
