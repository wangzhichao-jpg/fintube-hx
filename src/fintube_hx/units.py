"""Explicit engineering display-unit conversion; core calculation inputs remain SI."""
import math

SCALES={'length':{'mm':.001,'m':1.},'pressure':{'Pa':1.,'kPa':1000.,'MPa':1e6},
        'mass_flow':{'kg/s':1.,'kg/h':1/3600.},'enthalpy':{'J/kg':1.,'kJ/kg':1000.},'rh':{'fraction':1.,'%':.01}}


def to_si(value,quantity,unit):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):raise ValueError('Display-unit value must be a finite number')
    try:scale=SCALES[quantity][unit]
    except KeyError:raise ValueError('Unsupported quantity/unit; no implicit conversion') from None
    converted=float(value)*scale
    if not math.isfinite(converted):raise ValueError('Unit conversion overflow')
    return converted


def from_si(value,quantity,unit):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):raise ValueError('SI value must be a finite number')
    try:scale=SCALES[quantity][unit]
    except KeyError:raise ValueError('Unsupported quantity/unit; no implicit conversion') from None
    converted=float(value)/scale
    if not math.isfinite(converted):raise ValueError('Unit conversion overflow')
    return converted


def absolute_pressure(display_value,unit,*,reference='absolute',atmosphere_pa=None):
    p=to_si(display_value,'pressure',unit)
    if reference=='gauge':
        if isinstance(atmosphere_pa,bool) or not isinstance(atmosphere_pa,(int,float)) or not math.isfinite(atmosphere_pa) or atmosphere_pa<=0:
            raise ValueError('Gauge pressure requires visible positive absolute atmospheric pressure')
        p+=atmosphere_pa
    elif reference!='absolute':raise ValueError('Unknown pressure reference')
    if p<=0 or not math.isfinite(p):raise ValueError('Absolute pressure must be finite and positive')
    return p
