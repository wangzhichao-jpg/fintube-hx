"""Re-run the Community-runnable measured points and print the comparison table.

    python tools/run_measured_validation.py

Only the two water-coil points (W1/W2, Altwieb et al. 2022) can be run with the Community lumped model.
The refrigerant points (E1/E2/C1/C2, CETIAT / IEA HPT Annex 54) require an actual tube-circuit model;
their recorded Professional results are listed from validation/measured/cases.json for transparency.
Exit code 1 if a Community result no longer reproduces the recorded value.
"""
from __future__ import annotations
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from fintube_hx.engine import run_case  # noqa: E402

DATA = ROOT / 'validation/measured'


def main():
    cases = json.loads((DATA / 'cases.json').read_text(encoding='utf8'))['cases']
    failed = False
    print(f'{"case":4} {"mapping":15} {"measured":>10} {"community":>10} {"error":>8}')
    for cid in ('W1', 'W2'):
        measured = cases[cid]['measured']['q_avg_w']
        for scenario, rec in cases[cid]['community_lumped'].items():
            case = json.loads((DATA / rec['input']).read_text(encoding='utf8'))
            q = run_case(case)['heat_transfer_w']
            ok = abs(q - rec['q_w']) <= 1e-6 * rec['q_w']
            failed |= not ok
            print(f'{cid:4} {scenario:15} {measured:10.1f} {q:10.1f} {(q - measured) / measured * 100:+7.2f}%{"" if ok else "  (differs from recorded)"}')
    print('\nRecorded Professional tube-network results (not runnable here):')
    for cid, rec in cases.items():
        r = rec['professional_tube_network']['v5_documented']
        extra = ''
        if 'sh_k' in r:
            extra = f'  SH {r["sh_k"]:.1f} K (measured {r["measured_sh_k"]})'
        if 'sc_k' in r:
            extra = f'  SC {r["sc_k"]:.1f} K (measured {r["measured_sc_k"]})'
        print(f'{cid:4} Q {r["q_w"]:9.1f} W vs {r["measured_q_w"]:9.1f} W  {r["q_error_percent"]:+6.2f}%{extra}')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
