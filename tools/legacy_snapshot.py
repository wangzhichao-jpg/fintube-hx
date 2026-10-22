"""Legacy-scope result snapshots: freeze inputs + full results, then prove bit-for-bit reproduction.

    python tools/legacy_snapshot.py --write  SNAPSHOT.json.gz      # freeze the current corpus and results
    python tools/legacy_snapshot.py --compare SNAPSHOT.json.gz     # rerun the frozen inputs, compare every value
    python tools/legacy_snapshot.py --list                          # show the corpus without running it

Contract (docs: Pro 接口契约_v1.md, section 5):
* Inputs are frozen inside the snapshot.  ``--compare`` reruns exactly those inputs; it never regenerates them.
* Every case runs in a fresh worker process (no cache or call-order coupling between cases).
* Results are compared as complete JSON trees.  Floats compare by exact value (JSON stores repr, so the
  round trip is exact), and int/float type changes count as differences.  Text differences fail unless they
  are explicitly allowed with ``--allow-text-change`` (each allowance is listed in the report).
* Only volatile run metadata is removed before comparison (``VOLATILE_KEYS``).  Version strings are removed
  because a new core/Pro version must still reproduce the legacy numbers.
* Under the legacy scope the only keys that may be added are ``model.pressure_scope`` and ``model_coverage``
  (``ALLOWED_NEW_KEYS``).  Removed keys always fail.

This module also serves as the shared snapshot engine of the Professional workspace
(``软件研发/scripts/legacy_snapshot.py`` imports it), so both editions use one comparison rule.
"""
from __future__ import annotations

import argparse
import fnmatch
import gzip
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

FORMAT = 'fintube-legacy-snapshot/1'
PUB = Path(__file__).resolve().parents[1]

# Run metadata that legitimately differs between two runs of identical numerics.
VOLATILE_KEYS = frozenset({
    'calculated_at_utc', 'created_at_utc', 'updated_at_utc', 'started_at_utc', 'finished_at_utc', 'checked_at_utc',
    'version', 'shared_core_version', 'shared_core_api', 'shared_core_package', 'python', 'coolprop',
    'pro_version', 'core_version', 'software_version',
    'seconds', 'elapsed_s', 'elapsed_seconds', 'wall_time_s', 'forward_elapsed_s',
    # SHA-256 digests of records that themselves contain timestamps/uuid4 (the hashed numbers are compared directly)
    'result_sha256', 'workset_sha256', 'snapshot_sha256',
})
# Version identity stored under a parent key (contract change C-2): (parent, key).
VOLATILE_CHILD_KEYS = frozenset({('shared_core', 'api')})
# Random uuid4 identifiers (design/workset plans) are not deleted: they are mapped, in deterministic traversal order,
# to '<uuid#n>' so that references between them (ranked ids, best candidate) are still compared.
_UUID = r'(?:[0-9a-f]{32}|[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})'
UUID_RE = re.compile(rf'^{_UUID}(?::{_UUID})*$')   # also composite ids such as design:scenario
# Keys that a legacy-scope result may gain (interface contract v1).  (parent key or None, key)
ALLOWED_NEW_KEYS = (('model', 'pressure_scope'), (None, 'model_coverage'))
MAX_DIFFS_PER_CASE = 25


# ---------------------------------------------------------------- normalisation / hashing

def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf8')).hexdigest()


def normalize(value, volatile=VOLATILE_KEYS):
    """JSON round trip (tuples -> lists, exact float repr), removal of volatile metadata keys, uuid4 -> ordinal."""
    ids = {}

    def strip(v, parent=None):
        if isinstance(v, dict):
            return {k: strip(x, k) for k, x in v.items() if k not in volatile and (parent, k) not in VOLATILE_CHILD_KEYS}
        if isinstance(v, list):
            return [strip(x, parent) for x in v]
        if isinstance(v, str) and UUID_RE.match(v):
            return ':'.join(ids.setdefault(part, f'<uuid#{len(ids) + 1}>') for part in v.split(':'))
        return v
    return strip(json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False, default=_json_default)))


def _json_default(obj):
    if isinstance(obj, (set, frozenset)):
        return sorted(obj)
    if isinstance(obj, Path):
        return str(obj)
    raise TypeError(f'Not JSON serializable: {type(obj).__name__}')


# ---------------------------------------------------------------- comparison

def _allowed_addition(path, key):
    parent = path[-1] if path else None
    return any(key == k and (p is None or p == parent) for p, k in ALLOWED_NEW_KEYS)


def diff_trees(old, new, allow_text=(), path=()):
    """Yield (kind, path, old, new).  kind: value | type | text | missing | added | added_allowed | length."""
    if isinstance(old, dict) and isinstance(new, dict):
        for k in old:
            if k not in new:
                yield ('missing', path + (k,), old[k], None)
            else:
                yield from diff_trees(old[k], new[k], allow_text, path + (k,))
        for k in new:
            if k not in old:
                yield ('added_allowed' if _allowed_addition(path, k) else 'added', path + (k,), None, new[k])
        return
    if isinstance(old, list) and isinstance(new, list):
        if len(old) != len(new):
            yield ('length', path, len(old), len(new))
        for i, (a, b) in enumerate(zip(old, new)):
            yield from diff_trees(a, b, allow_text, path + (i,))
        return
    if type(old) is not type(new):
        yield ('type', path, old, new)
        return
    if old == new and (not isinstance(old, float) or old.hex() == new.hex()):
        return
    if isinstance(old, str):
        dotted = '.'.join(map(str, path))
        kind = 'text_allowed' if any(fnmatch.fnmatch(dotted, g) for g in allow_text) else 'text'
        yield (kind, path, old, new)
        return
    yield ('value', path, old, new)


FAILING = {'value', 'type', 'text', 'missing', 'added', 'length'}


# ---------------------------------------------------------------- execution

WORKER_FLAG = '--_worker'


def worker_main(runner):
    """Child-process side: read one corpus entry (JSON) from stdin, run it, write the normalized result to stdout."""
    entry = json.loads(sys.stdin.buffer.read().decode('utf8'))
    t0 = time.perf_counter()
    try:
        result = {'output': normalize(runner(entry))}
    except Exception as exc:  # recorded and compared like any other result
        result = {'output': {'error': {'type': type(exc).__name__, 'message': str(exc)}},
                  'traceback_tail': traceback.format_exc().splitlines()[-3:]}
    result['elapsed_s'] = time.perf_counter() - t0
    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False, allow_nan=False).encode('utf8'))
    return 0


def _run_one(entry, script):
    """Parent side: one fresh interpreter per case (no cache or call-order coupling between cases)."""
    proc = subprocess.run([sys.executable, script, WORKER_FLAG], input=json.dumps(entry, ensure_ascii=False).encode('utf8'),
                          capture_output=True, env=os.environ.copy())
    if proc.returncode != 0:
        raise RuntimeError(f'worker crashed for {entry["id"]} (exit {proc.returncode}): '
                           + proc.stderr.decode('utf8', 'replace')[-2000:])
    return json.loads(proc.stdout.decode('utf8'))


def run_corpus(entries, script, workers):
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(_run_one, e, script) for e in entries]
        results = []
        for i, f in enumerate(futures, 1):
            results.append(f.result())
            if i % 10 == 0 or i == len(futures):
                print(f'  {i}/{len(futures)} done', flush=True)
    return results


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree_digest(root: Path, pattern='**/*.py'):
    files = sorted(p for p in Path(root).glob(pattern) if '__pycache__' not in p.parts)
    h = hashlib.sha256()
    for p in files:
        h.update(str(p.relative_to(root)).encode('utf8') + b'\0' + p.read_bytes() + b'\0')
    return {'root': str(root), 'files': len(files), 'sha256': h.hexdigest()}


def write_snapshot(path, snapshot):
    data = (json.dumps(snapshot, ensure_ascii=False, indent=None, separators=(',', ':'), allow_nan=False) + '\n').encode('utf8')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise SystemExit(f'Refusing to overwrite an existing snapshot: {path}')
    with open(path, 'wb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', mtime=0, filename='') as gz:
        gz.write(data)


def read_snapshot(path):
    with gzip.open(path, 'rb') as gz:
        snap = json.loads(gz.read().decode('utf8'))
    if snap.get('format') != FORMAT:
        raise SystemExit(f'Unsupported snapshot format: {snap.get("format")}')
    return snap


def main_cli(*, edition, build_corpus, runner, script, environment, default_workers=None, argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == [WORKER_FLAG]:
        return worker_main(runner)
    p = argparse.ArgumentParser(description=f'{edition} legacy-scope snapshot (write / compare)')
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--write', metavar='SNAPSHOT.json.gz')
    g.add_argument('--compare', metavar='SNAPSHOT.json.gz')
    g.add_argument('--list', action='store_true')
    p.add_argument('--groups', help='comma-separated subset of groups (default: all)')
    p.add_argument('--workers', type=int, default=default_workers or max(1, (os.cpu_count() or 2) - 2))
    p.add_argument('--report', help='compare: write the JSON comparison report here')
    p.add_argument('--allow-text-change', action='append', default=[], metavar='GLOB',
                   help='compare: dotted-path glob whose text change is accepted (listed in the report)')
    a = p.parse_args(argv)
    wanted = set(a.groups.split(',')) if a.groups else None

    if a.list or a.write:
        corpus = build_corpus()
        entries = [e for e in corpus['entries'] if wanted is None or e['group'] in wanted]
        if a.list:
            for name, info in corpus['groups'].items():
                n = sum(e['group'] == name for e in entries)
                print(f'{name:28s} {n:4d}  {info}')
            for ex in corpus.get('excluded', []):
                print(f'EXCLUDED {ex["name"]}: {ex["reason"]}')
            print(f'total {len(entries)}')
            return 0
        print(f'{edition}: running {len(entries)} frozen inputs with {a.workers} workers', flush=True)
        t0 = time.time()
        results = run_corpus(entries, script, a.workers)
        cases = []
        for e, r in zip(entries, results):
            cases.append({'id': e['id'], 'group': e['group'], 'input_kind': e['input_kind'], 'input': e['input'],
                          'input_sha256': sha256_text(canonical(e['input'])),
                          'output': r['output'], 'output_sha256': sha256_text(canonical(r['output'])),
                          'elapsed_s': r['elapsed_s']})
        snap = {'format': FORMAT, 'edition': edition, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
                'tool': {'engine': str(Path(__file__).resolve()), 'engine_sha256': file_sha256(__file__),
                         'runner': str(script), 'runner_sha256': file_sha256(script)},
                'environment': environment(),
                'normalization': {'volatile_keys': sorted(VOLATILE_KEYS),
                                  'volatile_child_keys': sorted('.'.join(p) for p in VOLATILE_CHILD_KEYS),
                                  'allowed_new_keys': [f'{p or "*"}.{k}' for p, k in ALLOWED_NEW_KEYS]},
                'groups': {k: v for k, v in corpus['groups'].items() if wanted is None or k in wanted},
                'excluded': corpus.get('excluded', []),
                'run_seconds': time.time() - t0, 'cases': cases}
        write_snapshot(a.write, snap)
        errors = sum('error' in c['output'] for c in cases)
        print(f'wrote {a.write}: {len(cases)} cases ({errors} recorded errors), {time.time()-t0:.0f}s')
        return 0

    snap = read_snapshot(a.compare)
    cases = [c for c in snap['cases'] if wanted is None or c['group'] in wanted]
    for c in cases:
        if sha256_text(canonical(c['input'])) != c['input_sha256']:
            raise SystemExit(f'Frozen input checksum mismatch: {c["id"]}')
    entries = [{'id': c['id'], 'group': c['group'], 'input_kind': c['input_kind'], 'input': c['input']} for c in cases]
    print(f'{edition}: rerunning {len(entries)} frozen inputs from {a.compare} with {a.workers} workers', flush=True)
    t0 = time.time()
    results = run_corpus(entries, script, a.workers)
    report = {'snapshot': str(a.compare), 'snapshot_created_at_utc': snap['created_at_utc'],
              'compared_at_utc': datetime.now(timezone.utc).isoformat(), 'environment': environment(),
              'allow_text_change': a.allow_text_change, 'cases': len(cases), 'identical': 0,
              'identical_with_allowed_additions': 0, 'failed': [], 'allowed_text_changes': [], 'seconds': 0.0}
    for c, r in zip(cases, results):
        # Re-normalize the stored output with the current rules (idempotent; makes a rule change effective).
        diffs = list(diff_trees(normalize(c['output']), r['output'], tuple(a.allow_text_change)))
        failing = [d for d in diffs if d[0] in FAILING]
        if failing:
            report['failed'].append({'id': c['id'], 'group': c['group'], 'difference_count': len(failing),
                                     'differences': [{'kind': k, 'path': '.'.join(map(str, pth)),
                                                      'old': _short(o), 'new': _short(n)}
                                                     for k, pth, o, n in failing[:MAX_DIFFS_PER_CASE]]})
        elif diffs:
            report['identical_with_allowed_additions'] += 1
        else:
            report['identical'] += 1
        report['allowed_text_changes'] += [{'id': c['id'], 'path': '.'.join(map(str, pth)), 'old': _short(o), 'new': _short(n)}
                                           for k, pth, o, n in diffs if k == 'text_allowed']
    report['seconds'] = time.time() - t0
    report['all_identical'] = not report['failed']
    if a.report:
        Path(a.report).parent.mkdir(parents=True, exist_ok=True)
        Path(a.report).write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n', encoding='utf8')
    print(f'identical {report["identical"]}, identical+allowed additions {report["identical_with_allowed_additions"]}, '
          f'FAILED {len(report["failed"])} of {len(cases)}  ({report["seconds"]:.0f}s)')
    for f in report['failed'][:20]:
        d = f['differences'][0]
        print(f'  FAIL {f["id"]}: {f["difference_count"]} diffs; first {d["kind"]} at {d["path"]}: {d["old"]!r} -> {d["new"]!r}')
    return 0 if report['all_identical'] else 1


def _short(v):
    if isinstance(v, (dict, list)):
        text = canonical(v)
        return text if len(text) <= 200 else text[:200] + '…'
    return v


# ================================================================ Community corpus

def _load(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def community_corpus():
    entries, groups = [], {}

    def add(group, ident, input_kind, value):
        entries.append({'id': f'{group}/{ident}', 'group': group, 'input_kind': input_kind, 'input': value})

    groups['examples'] = 'examples/*.json (all shipped Community examples)'
    for f in sorted((PUB / 'examples').glob('*.json')):
        add('examples', f.name, 'case', _load(f))

    groups['references'] = 'references/python-hvac/water-community-input.json (mapped software reference)'
    add('references', 'water-community-input.json', 'case', _load(PUB / 'references/python-hvac/water-community-input.json'))

    groups['measured-v5-inputs'] = 'validation/measured/inputs/*.json (published W1/W2 inputs)'
    for f in sorted((PUB / 'validation/measured/inputs').glob('*.json')):
        add('measured-v5-inputs', f.name, 'case', _load(f))

    groups['measured-v6-tan-lumped'] = 'Tan 2015 lumped inputs rebuilt by tools/run_measured_v6_tan.build (recorded units only)'
    sys.path.insert(0, str(PUB / 'tools'))
    import run_measured_v6_tan as T
    v6 = PUB / 'validation/measured-v6'
    meas = _load(v6 / 'tan2015_fcu_measured.json')
    recorded = {(r['design'], r['unit'], r['sample']) for r in _load(v6 / 'tan2015_fcu_results.json')['lumped_core']['rows']}
    for rec in meas['records']:
        key = (rec['design'], rec['unit'], rec['sample'])
        if key in recorded:
            add('measured-v6-tan-lumped', '-'.join(map(str, key)), 'case', T.build(rec, meas['geometry_tables']))

    groups['workflows'] = 'scan and dew-point/segment series from tools/reproduce_external_review.py'
    mapped = _load(PUB / 'references/python-hvac/water-community-input.json')
    add('workflows', 'scan-water-geometry-airflow', 'workflow',
        {'workflow': 'scan', 'case': _load(PUB / 'examples/water_geometry.json'),
         'parameter': 'air.volume_flow_m3_h', 'values': [800.0, 1000.0, 1200.0]})
    add('workflows', 'external-review-dew-series', 'workflow', {'workflow': 'dew_series', 'case': mapped})
    add('workflows', 'external-review-segments', 'workflow', {'workflow': 'segments', 'case': mapped, 'segments': [1, 20]})
    return {'entries': entries, 'groups': groups, 'excluded': [
        {'name': 'validation/measured-v6 Batista/Joppolo', 'reason': 'extrapolation references computed with range checks removed by research scripts; not a product path'},
        {'name': 'capabilities()', 'reason': 'declared capability list, intentionally updated by T2; not a numerical result'}]}


def community_run(entry):
    """Executed inside the worker process."""
    from fintube_hx.engine import run_case
    inp = deepcopy(entry['input'])
    if entry['input_kind'] == 'case':
        return run_case(inp)
    wf = inp['workflow']
    if wf == 'scan':
        from fintube_hx.scan import scan_case
        return scan_case(inp['case'], inp['parameter'], inp['values'])
    if wf == 'dew_series':
        from fintube_hx.properties import air_state
        test = deepcopy(inp['case'])
        test['air']['relative_humidity'] = .5
        dew = air_state(27, .5, 101325)['dew_point_c']
        out = []
        for t in [12.5, 16.5, dew - .01, dew + .01, dew - .0001, dew + .0001]:
            test['fluid']['inlet_t_c'] = t
            out.append({'inlet_water_c': t, 'result': run_case(test)})
        return out
    if wf == 'segments':
        out = []
        for n in inp['segments']:
            c = deepcopy(inp['case'])
            c['model']['segments'] = n
            out.append({'segments': n, 'result': run_case(c)})
        return out
    raise ValueError(f'unknown workflow {wf}')


def package_versions(names):
    from importlib import metadata
    out = {}
    for n in names:
        try:
            out[n] = metadata.version(n)
        except metadata.PackageNotFoundError:
            out[n] = None
    return out


def community_environment():
    import fintube_hx
    return {'python': platform.python_version(), 'platform': platform.platform(), 'machine': platform.processor() or platform.machine(),
            'fintube_hx_version': fintube_hx.__version__, 'fintube_hx_file': fintube_hx.__file__,
            'source_tree': tree_digest(Path(fintube_hx.__file__).parent),
            'packages': package_versions(['CoolProp', 'scipy', 'numpy', 'ht', 'fluids', 'openpyxl'])}


if __name__ == '__main__':
    sys.exit(main_cli(edition='community', build_corpus=community_corpus, runner=community_run,
                      script=str(Path(__file__).resolve()), environment=community_environment))
