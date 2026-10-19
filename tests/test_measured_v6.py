"""Measured validation set v6: integrity and reproducibility of the open-core (lumped) results."""
import hashlib, json, subprocess, sys
from pathlib import Path
import pytest

V6 = Path(__file__).resolve().parents[1] / 'validation/measured-v6'


def test_checksums_and_no_private_inputs():
    for line in (V6 / 'SHA256SUMS.txt').read_text(encoding='utf8').splitlines():
        digest, name = line.split('  ')
        assert hashlib.sha256((V6 / name).read_bytes()).hexdigest() == digest
    text = ''.join(p.read_text(encoding='utf8') for p in V6.glob('*.json'))
    assert '"paths"' not in text and '/home/' not in text


def test_tan2015_lumped_results_reproduce():
    sys.path.insert(0, str(V6.parents[1] / 'tools'))
    import run_measured_v6_tan as T
    from fintube_hx.engine import run_case
    meas = json.loads((V6 / 'tan2015_fcu_measured.json').read_text(encoding='utf8'))
    rec_rows = {(r['design'], r['unit'], r['sample']): r for r in
                json.loads((V6 / 'tan2015_fcu_results.json').read_text(encoding='utf8'))['lumped_core']['rows']}
    picked = [r for r in meas['records'] if (r['design'], r['unit'], r['sample']) in
              {('pre', '03#', 1), ('pre', '14#', 3), ('post', '05#', 7)}]
    assert len(picked) == 3
    for rec in picked:
        r = run_case(T.build(rec, meas['geometry_tables']))
        dq = r['heat_transfer_w'] / (rec['q_water_kw'] * 1000) - 1
        assert dq == pytest.approx(rec_rows[(rec['design'], rec['unit'], rec['sample'])]['dev_ref']['qw_rel'], abs=1e-12)


def test_cetiat_declared_counts():
    d = json.loads((V6 / 'cetiat_iea_annex54.json').read_text(encoding='utf8'))
    v = [r['verdict'] for r in d['results']]
    assert len(v) == 20 and sum(x['Q'] == 'robust_pass' for x in v) == 20
