from pathlib import Path
import json,ast
import pytest
from fintube_hx.engine import run_case
ROOT=Path(__file__).resolve().parents[1]/'references/python-hvac'


@pytest.mark.parametrize('kind',['water','evaporator','condenser'])
def test_whole_coil_reference_is_reproduced_not_measured(kind):
    r=json.loads((ROOT/(kind+'.json')).read_text(encoding='utf8'))
    assert r['status']=='completed' and not r['notebook_inputs_modified']
    assert r['evidence_kind']=='software_reference_not_measured'
    assert r['source_commit']=='94247560a667905bfbf67e45a58965a58254fce8'
    assert r['computed']['heat_transfer_w']>0 and abs(r['differences_from_saved_rounding']['heat_transfer_w'])<1
    if kind!='water':assert r['computed']['fluid_pressure_drop_pa'] is None


def test_water_explicit_mapping_reproduces_candidate_not_exact_geometry():
    c=json.loads((ROOT/'water-community-input.json').read_text(encoding='utf8'))
    comparison=json.loads((ROOT/'water-community-comparison.json').read_text(encoding='utf8'))
    assert c['model']['ua_mode']=='geometry' and 'ua_w_k' not in c['model'] and not comparison['ua_fitted']
    assert not comparison['exact_geometry_parity'] and not comparison['measured_validation']
    assert comparison['mapping']['tube_inventory'][0]!=comparison['mapping']['tube_inventory'][1]
    r=run_case(c);assert r['converged'] and r['heat_transfer_w']==pytest.approx(comparison['community_summary']['heat_transfer_w'],rel=1e-10)


def test_public_reproducer_and_data_have_no_private_imports_or_host_paths():
    for p in ROOT.rglob('*'):
        if not p.is_file() or p.suffix not in ('.py','.json','.txt','.md'):continue
        s=p.read_text(encoding='utf8');assert not any(x in s for x in ('D:/Users','D:\\Users')+tuple(__import__('base64').b64decode(b).decode() for b in ('amllZmVuZw==','5o235Liw')))
        if p.suffix=='.py':
            for n in ast.walk(ast.parse(s)):
                if isinstance(n,ast.ImportFrom):assert not (n.module or '').startswith('fintube_hx_pro')
    ledger=json.loads((ROOT/'source-tree.json').read_text(encoding='utf8'));assert len(ledger['files'])==419
