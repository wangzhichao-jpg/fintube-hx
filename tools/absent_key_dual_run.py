"""Reproduce dev17/dev19 absent-key equivalence in separate processes, without pytest import paths.

Run this file from any directory. Extract the original wheels into separate directories first.
`fixtures`, two `run` invocations (one interpreter/dependency environment), then `compare`.
No network access, model tuning or numeric tolerance. Raw outputs include native type/float-bit records.
"""
import argparse
from datetime import datetime
import hashlib
import importlib
import json
import math
from pathlib import Path
import platform
import sys


def save(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def exact_differences(a, b, path=''):
    if type(a) is not type(b):
        return [dict(path=path, kind='type', old=type(a).__name__, new=type(b).__name__)]
    if isinstance(a, dict):
        out = []
        if set(a) != set(b):
            out.append(dict(path=path, kind='keys', only_old=sorted(set(a)-set(b)), only_new=sorted(set(b)-set(a))))
        for k in sorted(set(a) & set(b)):
            out.extend(exact_differences(a[k], b[k], path + '/' + str(k).replace('~','~0').replace('/','~1')))
        return out
    if isinstance(a, (list, tuple)):
        out = []
        if len(a) != len(b):
            out.append(dict(path=path, kind='length', old=len(a), new=len(b)))
        for i, (x,y) in enumerate(zip(a,b)):
            out.extend(exact_differences(x,y,path+'/'+str(i)))
        return out
    if isinstance(a, float):
        if not (math.isfinite(a) and math.isfinite(b)) or a.hex() != b.hex():
            return [dict(path=path, kind='float_bits', old=a, new=b, old_hex=a.hex(), new_hex=b.hex())]
    elif a != b:
        return [dict(path=path, kind='value', old=a, new=b)]
    return []


def result_differences(a, b):
    failed, allowed = [], []
    for d in exact_differences(a,b):
        p = d['path']
        ok = p == '/provenance/version' and d.get('old') == '0.1.0.dev17' and d.get('new') == '0.1.0.dev19'
        if p == '/provenance/calculated_at_utc' and d.get('kind') == 'value':
            try:
                ok = all(datetime.fromisoformat(d[k]).tzinfo is not None for k in ('old','new'))
            except (TypeError, ValueError):
                ok = False
        (allowed if ok else failed).append(d)
    return failed, allowed


def native_types(value, path=''):
    out = {path: type(value).__name__}
    if isinstance(value, dict):
        for k, v in value.items():
            out.update(native_types(v,path+'/'+str(k).replace('~','~0').replace('/','~1')))
    elif isinstance(value, (list, tuple)):
        for i,v in enumerate(value): out.update(native_types(v,path+'/'+str(i)))
    return out


def worker(args):
    root = Path(args.core_dir).resolve()
    sys.path.insert(0,str(root))
    import fintube_hx
    from fintube_hx.engine import run_case
    module = Path(fintube_hx.__file__).resolve()
    if not module.is_relative_to(root) or fintube_hx.__version__ != args.version:
        raise RuntimeError('Wrong core import: ' + str(module) + ' ' + fintube_hx.__version__)
    deps = {}
    for name in ('CoolProp','numpy','scipy','ht','fluids'):
        m=importlib.import_module(name); f=Path(m.__file__).resolve()
        deps[name] = dict(version=m.__version__, path=str(f), sha256=hashlib.sha256(f.read_bytes()).hexdigest())
    inputs=json.loads(Path(args.inputs).read_text(encoding='utf-8'))
    if len(inputs) != 8 or any('wet_friction_fin_pitch_extrapolation' in c['geometry'] for c in inputs.values()):
        raise ValueError('Expected exactly eight absent-key cases')
    results = {k:run_case(c) for k,c in inputs.items()}
    save(args.out, dict(core=dict(version=fintube_hx.__version__, module=str(module),
         source_sha256={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root/'fintube_hx').rglob('*.py'))}),
         environment=dict(python=sys.version, executable=sys.executable, platform=platform.platform(), dependencies=deps),
         inputs=inputs, native_types={k:native_types(r) for k,r in results.items()}, results=results))


def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    f=sub.add_parser('fixtures'); f.add_argument('--example',required=True); f.add_argument('--out',required=True)
    w=sub.add_parser('run')
    for flag in ('core-dir','version','inputs','out'): w.add_argument('--'+flag,required=True)
    c=sub.add_parser('compare')
    for flag in ('old','new','out'): c.add_argument('--'+flag,required=True)
    a=p.parse_args()
    if a.command=='fixtures':
        base=json.loads(Path(a.example).read_text(encoding='utf-8')); cases={}
        for pitch in (0.0018,0.003,0.00324,0.0045):
            for rh in (0.2,0.6):
                d=json.loads(json.dumps(base)); d['air']['relative_humidity']=rh; d['model']['pressure_scope']='v1'
                d['geometry'].update(fin_pitch_m=pitch,fin_surface='bare_aluminum'); cases[f'{pitch}-{rh}']=d
        save(a.out,cases)
    elif a.command=='run': worker(a)
    else:
        old,new=(json.loads(Path(x).read_text(encoding='utf-8')) for x in (a.old,a.new))
        diff=exact_differences(old['environment'],new['environment'],'/environment')
        diff+=exact_differences(old['inputs'],new['inputs'],'/inputs')
        diff+=exact_differences(old['native_types'],new['native_types'],'/native_types')
        if old['core']['version']!='0.1.0.dev17' or new['core']['version']!='0.1.0.dev19':
            diff.append(dict(path='/core/version',kind='unexpected_versions'))
        allowed=[]
        for key in sorted(set(old['results'])|set(new['results'])):
            if key not in old['results'] or key not in new['results']:
                diff.append(dict(path='/results/'+key,kind='missing_case')); continue
            bad,ok=result_differences(old['results'][key],new['results'][key])
            for d in bad: d['path']='/results/'+key+d['path']
            for d in ok: d['path']='/results/'+key+d['path']
            diff+=bad; allowed+=ok
        if len(old['results'])!=8 or len(new['results'])!=8:
            diff.append(dict(path='/results',kind='expected_eight_cases'))
        out=dict(passed=not diff,cases=len(old['results']),precision='float.hex exact, including signed zero; no tolerance',
                 excluded_paths=['/provenance/version (dev17 -> dev19 only)','/provenance/calculated_at_utc (timezone-aware ISO timestamp only)'],
                 differences=diff,allowed_differences=allowed)
        save(a.out,out); print(json.dumps(dict(passed=out['passed'],cases=out['cases'],differences=len(diff),allowed=len(allowed))))
        return 1 if diff else 0
    return 0


if __name__=='__main__': sys.exit(main())
