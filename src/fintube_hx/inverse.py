"""Shared bounded inverse engine; optional continuation is an injected opaque strategy.
The public package provides no engineering initial-state or tube-network implementation.
Every accepted answer is recomputed without continuation and checked against tolerance.
"""
from copy import deepcopy
import math
import time
from scipy.optimize import brentq


def solve_mass_flow(case,target_key,output,simulate,xtol=1e-9,*,continuation=None):
    """Solve one root bracketed by the user bounds; monotonicity is not assumed.

    Same-sign endpoints do not prove that interior roots are absent. The caller
    must supply a bracket for the desired root of a nonmonotonic response.
    continuation.capture(case,result)->seed, seed.usable(case), evaluate(case,seed).
    """
    target=case['target'];goal=target[target_key];bounds=target['mass_flow_bounds_kg_s'];tolerance=target.get('tolerance_k',.001)
    forward=deepcopy(case);forward.pop('target',None)
    cache={};trace=[];cache_hits=0;warm_enabled=continuation is not None
    def evaluate(flow,*,cold=False,phase='search'):
        nonlocal cache_hits
        flow=float(flow)
        if not cold and flow in cache:
            cache_hits+=1;return output(cache[flow][0])-goal
        forward['fluid']['mass_flow_kg_s']=flow;seed=None
        if not cold and warm_enabled and cache:
            nearest=min(cache,key=lambda m:abs(math.log(flow/m)))
            candidate=cache[nearest][1]
            if candidate is not None and candidate.usable(forward):seed=candidate
        attempts=[]
        for initial in ([seed,None] if seed is not None else [None]):
            start=time.perf_counter()
            try:
                result=continuation.evaluate(forward,initial) if initial is not None else simulate(forward)
                residual=float(output(result))-goal
                if not result['converged']:raise ValueError('Forward solve did not converge during inverse solve')
                if not math.isfinite(residual):raise ValueError('Nonfinite forward residual during inverse solve')
            except ValueError as exc:
                attempts.append({'warm_start':initial is not None,'error':str(exc),'elapsed_s':time.perf_counter()-start})
                if initial is None:
                    trace.append({'mass_flow_kg_s':flow,'phase':phase,'attempts':attempts});raise
                continue
            attempts.append({'warm_start':initial is not None,'iterations':result['iterations'],'elapsed_s':time.perf_counter()-start,'converged':True});break
        trace.append({'mass_flow_kg_s':flow,'phase':phase,'residual_k':residual,'attempts':attempts})
        cache[flow]=(result,continuation.capture(forward,result) if continuation is not None else None)
        return residual
    left,right=evaluate(bounds[0]),evaluate(bounds[1])
    if abs(left)<=tolerance and abs(right)<=tolerance:raise ValueError('Target does not determine a unique mass flow within these bounds')
    if left*right>0:
        raise ValueError('Target is not bracketed by the supplied mass-flow endpoints; '
                         'interior roots of a nonmonotonic response are not excluded')
    class TargetReached(Exception):
        def __init__(self,flow):self.flow=flow
    def root(phase='search'):
        def residual(flow):
            value=evaluate(flow,phase=phase)
            if abs(value)<=tolerance*.05:raise TargetReached(flow)
            return value
        try:return brentq(residual,*bounds,xtol=xtol,maxiter=100)
        except TargetReached as reached:return float(reached.flow)
    flow=root();error=evaluate(flow,cold=True,phase='cold_verification')
    if abs(error)>tolerance and warm_enabled:
        warm_enabled=False;cache.clear();flow=root('cold_recovery');error=evaluate(flow,cold=True,phase='cold_verification')
    if abs(error)>tolerance:raise ValueError('Target outlet-state residual exceeds tolerance after cold verification')
    result=cache[flow][0];result['operating_inputs']=deepcopy(forward)
    result['target_solution']={'mass_flow_kg_s':flow,target_key:goal,'residual_k':error,
        'evaluations':sum(len(t['attempts']) for t in trace),'cache_hits':cache_hits,'cold_verified':True,
        'root_selection':'one_root_in_supplied_bracket','uniqueness_verified':False,
        'total_forward_iterations':sum(a.get('iterations',0) for t in trace for a in t['attempts']),
        'forward_elapsed_s':sum(a['elapsed_s'] for t in trace for a in t['attempts']),'evaluation_trace':trace}
    return result
