"""Wang-Chi plain-fin j/f adaptation from python-hvac (MIT).

Copyright (c) 2023 Tom Christiaens. Adapted from correlations.py, commit
94247560a667905bfbf67e45a58965a58254fce8. Full MIT notice is preserved in
third_party_licenses/python-hvac/LICENSE.md. This module is NOT a measured
Jiefeng validation or permission to extrapolate beyond the stated range.
"""
import math


def wang_plain_fin(Re,dc,dh,pt,pl,pf,rows):
    limits={'Re':(Re,300.,20000.),'collar diameter':(dc,.0069,.0136),
            'hydraulic diameter':(dh,.00130,.00937),'transverse pitch':(pt,.0204,.0318),
            'longitudinal pitch':(pl,.0127,.032),'fin pitch':(pf,.001,.0087),
            'rows':(rows,1,6)}
    for name,(value,lo,hi) in limits.items():
        if not math.isfinite(value) or not lo<=value<=hi:
            raise ValueError(f'Wang plain-fin {name}={value:g} outside validated correlation range [{lo:g},{hi:g}]')
    ln=math.log(Re)
    if rows<2:
        c1=1.9-.23*ln;c2=-.236+.126*ln
        j=.108*Re**(-.29)*(pt/pl)**c1*(pf/dc)**(-1.084)*(pf/dh)**(-.786)*(pf/pt)**c2
    else:
        c3=-.361-.042*rows/ln+.158*math.log(rows*(pf/dc)**.41)
        c4=-1.224-.076*(pl/dh)**1.42/ln
        c5=-.083+.058*rows/ln;c6=-5.735+1.21*math.log(Re/rows)
        j=.086*Re**c3*rows**c4*(pf/dc)**c5*(pf/dh)**c6*(pf/pt)**(-.93)
    c1=-.764+.739*(pt/pl)+.177*(pf/dc)-.00758/rows
    c2=-15.689+64.021/ln;c3=1.696-15.695/ln
    f=.0267*Re**c1*(pt/pl)**c2*(pf/dc)**c3
    return {'colburn_j':j,'fanning_friction_factor':f,
            'source':'python-hvac Wang-Chi 2000 implementation, pinned MIT source',
            'source_commit':'94247560a667905bfbf67e45a58965a58254fce8',
            'source_url':'https://github.com/TomLXXVI/python-hvac/blob/94247560a667905bfbf67e45a58965a58254fce8/hvac/heat_exchanger/recuperator/fintube/continuous_fin/correlations.py',
            'correlation_range_checked':True}
