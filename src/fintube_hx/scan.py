"""Bounded scalar parameter scans; failed points are retained, not silently dropped."""
from __future__ import annotations
from copy import deepcopy
import json
import math
from .schema import validate_case
from .engine import run_case


def set_scalar_path(case: dict,path: str,value):
    if not isinstance(path,str) or not path or any(not part for part in path.split('.')):
        raise ValueError('Parameter path must be a nonempty dot-separated JSON field')
    parts=path.split('.');node=case
    for part in parts[:-1]:
        if not isinstance(node,dict) or part not in node:
            raise ValueError(f'Unknown parameter path: {path}')
        node=node[part]
    if not isinstance(node,dict) or parts[-1] not in node:
        raise ValueError(f'Unknown parameter path: {path}')
    if isinstance(node[parts[-1]],(dict,list)):
        raise ValueError('Scan must address an existing scalar, not an object/array')
    node[parts[-1]]=value


def scan_case(base_case: dict,parameter: str,values: list,progress=None) -> dict:
    if not isinstance(values,list) or not 1<=len(values)<=128:
        raise ValueError('Scan requires 1..128 scalar values')
    for value in values:
        if not isinstance(value,(int,float,str,bool,type(None))):
            raise ValueError('Scan values must be JSON scalars')
        if isinstance(value,float) and not math.isfinite(value):
            raise ValueError('Scan values must be finite')
    base=validate_case(base_case)
    json.dumps(base,allow_nan=False)  # Reject non-JSON or nonfinite archival inputs.
    probe=deepcopy(base);set_scalar_path(probe,parameter,values[0])
    results=[]
    for index,value in enumerate(values,1):
        case=deepcopy(base);set_scalar_path(case,parameter,value)
        if parameter!='name':case['name']=f"{base['name']}-scan-{index:03d}"
        try:
            result=run_case(case)
        except Exception as exc:
            result={'case_name':str(case.get('name','failed')),'kind':case.get('kind','unknown'),
                    'converged':False,'error':str(exc),'inputs':case,
                    'verification_level':'failed_not_validated'}
        result['scan']={'parameter':parameter,'value':value,'index':index,'count':len(values)}
        results.append(result)
        if progress:progress(index,len(values),result)
    return {'schema_version':'0.1','parameter':parameter,'values':deepcopy(values),
            'base_inputs':base,'results':results,'status':'complete',
            'all_converged':all(r['converged'] for r in results),
            'passed_points':sum(r['converged'] for r in results),
            'failed_points':sum(not r['converged'] for r in results),
            'verification_level':'numerical_scan_not_measured_validation'}
