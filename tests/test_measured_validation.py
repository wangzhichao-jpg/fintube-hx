"""The public measured-validation data set is internally consistent and reproducible."""
import json
from pathlib import Path
import pytest
from fintube_hx.engine import run_case

DATA = Path(__file__).resolve().parents[1] / 'validation/measured'
CASES = json.loads((DATA / 'cases.json').read_text(encoding='utf8'))


def test_six_points_two_specimens_with_sources():
    cases = CASES['cases']
    assert sorted(cases) == ['C1', 'C2', 'E1', 'E2', 'W1', 'W2']
    assert {c['specimen'] for c in cases.values()} == {'Altwieb plain-fin coil (2 rows x 5 tubes)',
                                                       'CETIAT reversible coil (3 rows x 32 tubes, 8 circuits)'}
    for c in cases.values():
        src = CASES['sources'][c['source']]
        assert src['url'].startswith('https://') and len(src['sha256_of_retrieved_pdf']) == 64
        assert c['assumptions']


@pytest.mark.parametrize('cid', ['W1', 'W2'])
def test_community_water_points_reproduce_recorded_values(cid):
    for rec in CASES['cases'][cid]['community_lumped'].values():
        case = json.loads((DATA / rec['input']).read_text(encoding='utf8'))
        assert case['model'].get('ua_mode') == 'geometry' and 'heat_transfer_multiplier' not in case['model']
        assert run_case(case)['heat_transfer_w'] == pytest.approx(rec['q_w'], rel=1e-6)


def test_recorded_errors_match_measured_values():
    for cid, c in CASES['cases'].items():
        measured = c['measured'].get('q_avg_w') or c['measured']['q_kw'] * 1000
        for scenario in ('v4_reproduce', 'v5_documented'):
            r = c['professional_tube_network'][scenario]
            assert r['measured_q_w'] == pytest.approx(measured)
            assert r['q_error_percent'] == pytest.approx((r['q_w'] - measured) / measured * 100)
