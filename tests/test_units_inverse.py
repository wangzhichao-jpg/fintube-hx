from copy import deepcopy
import math
import pytest
from fintube_hx.units import to_si,from_si,absolute_pressure
from fintube_hx.inverse import solve_mass_flow


@pytest.mark.parametrize('value,quantity,unit,si',[(9.5,'length','mm',.0095),(300,'pressure','kPa',300000),(2.7,'pressure','MPa',2700000),
 (72,'mass_flow','kg/h',.02),(250,'enthalpy','kJ/kg',250000),(50,'rh','%',.5)])
def test_engineering_units(value,quantity,unit,si):
    assert to_si(value,quantity,unit)==pytest.approx(si)
    assert from_si(si,quantity,unit)==pytest.approx(value)


@pytest.mark.parametrize('value',[True,math.nan,math.inf,'1'])
def test_invalid_unit_values(value):
    with pytest.raises(ValueError):to_si(value,'pressure','Pa')


def test_no_unknown_units_or_hidden_atmosphere():
    with pytest.raises(ValueError):to_si(1,'pressure','bar')
    with pytest.raises(ValueError):absolute_pressure(200,'kPa',reference='gauge')
    assert absolute_pressure(210,'kPa',reference='gauge',atmosphere_pa=90000)==300000


def toy_case():return {'fluid':{'mass_flow_kg_s':1.},'target':{'goal':.8,'mass_flow_bounds_kg_s':[.5,1.5],'tolerance_k':1e-5}}
def sim(c):return {'value':c['fluid']['mass_flow_kg_s'],'iterations':1,'converged':True}
class Seed:
    def usable(self,c):return True
class Continuation:
    def __init__(self,fail=False):self.fail=fail
    def capture(self,c,r):return Seed()
    def evaluate(self,c,seed):
        if self.fail:raise ValueError('Deliberate generic initial-state failure')
        r=sim(c);r['value']+=.05;return r


@pytest.mark.parametrize('fail',[False,True])
def test_opaque_strategy_is_rechecked_cold_and_cannot_bias_answer(fail):
    c=toy_case();before=deepcopy(c);r=solve_mass_flow(c,'goal',lambda r:r['value'],sim,continuation=Continuation(fail))
    assert c==before and r['value']==pytest.approx(.8,abs=1e-5) and r['target_solution']['cold_verified']
    assert any(a['warm_start'] for t in r['target_solution']['evaluation_trace'] for a in t['attempts'])
    assert not r['target_solution']['evaluation_trace'][-1]['attempts'][0]['warm_start']
    if not fail:assert any(t['phase']=='cold_recovery' for t in r['target_solution']['evaluation_trace'])
