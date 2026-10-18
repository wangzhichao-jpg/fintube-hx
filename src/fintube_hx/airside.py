"""Air-side j/f correlations by fin type, and fin-efficiency methods.

Original implementations transcribed from the published papers (equation numbers
cited); coefficients were read from 200 dpi and 400 dpi page renderings.

* plain             Wang & Chi (2000) via ``wang_plain_fin`` (unchanged legacy path).
* louver            Wang, Lee, Chang & Lin (1999), Int. J. Heat Mass Transfer 42:1945-1956,
                    Eqs. (18)-(27) for j and (29)-(39) for f.  Eq. (28) is printed as
                    Dh = 4Ac/L; the paper's nomenclature defines Dh = 4AcL/Ao, which is used.
* wavy_herringbone  Wang, Hwang & Lin (2002), Int. J. Refrig. 25:673-680, Eqs. (31)-(47);
                    tan(theta) = Pd/Xf, Fs = Fp - delta_f, Dh = 4AcL/Ao (paper nomenclature).

All three papers reduce j with the Schmidt plate-fin efficiency (Wang, Webb & Chi
2000, Exp. Therm. Fluid Sci. 21:218, Eqs. (7)-(11)), and their Fanning f includes the
core entrance/exit losses, so dp = f*(Ao/Ac)*G^2/(2 rho) (isothermal form).

Validated ranges are the sample ranges reported in the papers (louver: Table 1 and
Fig. 5; herringbone: Table 2 "this study" and Section 5, fin pitch upper bound 6.45 mm
from Table 1 sample 34 where Table 2 prints 6.43); values outside raise.
"""
from __future__ import annotations
import math
from .wang_plain_fin import wang_plain_fin

FIN_TYPES = ('plain', 'louver', 'wavy_herringbone')
FIN_EFFICIENCY_METHODS = ('equal_area_annular', 'schmidt')

LOUVER_RANGE = {'Re': (300., 8000.), 'collar diameter': (.00693, .01042), 'transverse pitch': (.0177, .0254),
                'longitudinal pitch': (.0127, .022), 'fin pitch': (.0012, .00249), 'rows': (1, 6),
                'louver height': (.00079, .0014), 'louver pitch': (.0017, .00375),
                'louver height/pitch': (.24, .824)}
HERRINGBONE_RANGE = {'Re': (300., 10000.), 'collar diameter': (.00766, .01685), 'transverse pitch': (.021, .0381),
                     'longitudinal pitch': (.0127, .033), 'fin pitch': (.00121, .00645), 'rows': (1, 6),
                     'corrugation angle deg': (5.3, 18.5), 'projected wave length': (.003175, .00825),
                     'wave height': (.0003, .0018)}


MAX_RANGE_TOLERANCE = 0.01
NOT_EXTENDABLE = ('Re', 'rows')


def _check(name, values, limits, tolerance=0.0):
    """Raise outside the published sample range.  An explicit ``tolerance`` (relative,
    at most 1 %) extends only geometric bounds, never Re or rows; every extended
    parameter is returned so that results can disclose the boundary extrapolation."""
    if not 0.0 <= tolerance <= MAX_RANGE_TOLERANCE:
        raise ValueError('correlation_range_tolerance must be within 0..0.01')
    extended = {}
    for key, value in values.items():
        lo, hi = limits[key]
        # 1e-9 relative: floating-point unit conversion only, not a range extension.
        if math.isfinite(value) and lo * (1 - 1e-9) <= value <= hi * (1 + 1e-9):
            continue
        tol = 0.0 if key in NOT_EXTENDABLE else tolerance
        if math.isfinite(value) and lo * (1 - tol) <= value <= hi * (1 + tol):
            extended[key] = {'value': value, 'published_range': [lo, hi],
                             'relative_excess': (value - hi) / hi if value > hi else (value - lo) / lo}
            continue
        raise ValueError(f'{name} {key}={value:g} outside published sample range [{lo:g},{hi:g}]'
                         + (f' (+{tol:.1%} declared tolerance)' if tol else ''))
    return extended


def wang_louver_1999(Re, dc, dh, pt, pl, pf, rows, lp, lh, ao_at, range_tolerance=0.0):
    extended = _check('Wang 1999 louver', {'Re': Re, 'collar diameter': dc, 'transverse pitch': pt, 'longitudinal pitch': pl,
                                'fin pitch': pf, 'rows': rows, 'louver height': lh, 'louver pitch': lp,
                                'louver height/pitch': lh / lp}, LOUVER_RANGE, range_tolerance)
    N = rows; ln = math.log; lnRe = ln(Re)
    if Re < 1000:
        J1 = -0.991 - 0.1055 * (pl / pt) ** 3.1 * ln(lh / lp)                       # (19)
        J2 = -0.7344 + 2.1059 * (N ** 0.55 / (lnRe - 3.2))                          # (20)
        J3 = 0.08485 * (pl / pt) ** -4.4 * N ** -0.68                               # (21)
        J4 = -0.1741 * ln(N)                                                        # (22)
        j = 14.3117 * Re ** J1 * (pf / dc) ** J2 * (lh / lp) ** J3 * (pf / pl) ** J4 * (pl / pt) ** -1.724   # (18)
        branch_j = 'Eq18_Re_lt_1000'
    else:
        J5 = -0.6027 + 0.02593 * (pl / dh) ** 0.52 * N ** -0.5 * ln(lh / lp)        # (24)
        J6 = -0.4776 + 0.40774 * (N ** 0.7 / (lnRe - 4.4))                          # (25)
        J7 = -0.58655 * (pf / dh) ** 2.3 * (pl / pt) ** -1.6 * N ** -0.65           # (26)
        J8 = 0.0814 * (lnRe - 3)                                                    # (27)
        j = 1.1373 * Re ** J5 * (pf / pl) ** J6 * (lh / lp) ** J7 * (pl / pt) ** J8 * N ** 0.3545       # (23)
        branch_j = 'Eq23_Re_ge_1000'
    if N == 1:
        F1 = 0.1691 + 4.4118 * (pf / pl) ** -0.3 * (lh / lp) ** -2 * ln(pl / pt) * (pf / pt) ** 3   # (30)
        F2 = -2.6642 - 14.3809 / lnRe                                               # (31)
        F3 = -0.6816 * ln(pf / pl)                                                  # (32)
        F4 = 6.4668 * (pf / pt) ** 1.7 * ln(ao_at)                                  # (33)
        f = 0.00317 * Re ** F1 * (pf / pl) ** F2 * (dh / dc) ** F3 * (lh / lp) ** F4 * ln(ao_at) ** -6.0483  # (29)
        branch_f = 'Eq29_N_eq_1'
    else:
        F5 = 0.1395 - 0.0101 * (pf / pl) ** 0.58 * (lh / lp) ** -2 * ln(ao_at) * (pl / pt) ** 1.9  # (35)
        F6 = -6.4367 / lnRe                                                         # (36)
        F7 = 0.07191 * lnRe                                                         # (37)
        F8 = -2.0585 * (pf / pt) ** 1.67 * lnRe                                     # (38)
        F9 = 0.1036 * ln(pl / pt)                                                   # (39)
        f = 0.06393 * Re ** F5 * (pf / dc) ** F6 * (dh / dc) ** F7 * (lh / lp) ** F8 * N ** F9 * (lnRe - 4.0) ** -1.093  # (34)
        branch_f = 'Eq34_N_gt_1'
    return {'colburn_j': j, 'fanning_friction_factor': f, 'branches': [branch_j, branch_f],
            'source': 'Wang, Lee, Chang & Lin 1999, IJHMT 42:1945-1956, Eqs. (18)-(39)',
            'friction_definition': 'Fanning, entrance/exit losses included (paper Eq. 14)',
            **({'range_extrapolation': extended} if extended else {}),
            'correlation_range_checked': True}


def wang_herringbone_2002(Re, dc, dh, pt, pl, pf, tf, rows, pd, xf, range_tolerance=0.0):
    tan = pd / xf; theta = math.degrees(math.atan(tan))
    extended = _check('Wang 2002 herringbone', {'Re': Re, 'collar diameter': dc, 'transverse pitch': pt, 'longitudinal pitch': pl,
                                     'fin pitch': pf, 'rows': rows, 'corrugation angle deg': theta,
                                     'projected wave length': xf, 'wave height': pd}, HERRINGBONE_RANGE)
    N = rows; fs = pf - tf; ln = math.log; lnRe = ln(Re)
    if Re < 1000:
        J1 = (0.0045 - 0.491 * Re ** (-0.0316 - 0.0171 * ln(N * tan)) * (pl / pt) ** (-0.109 * ln(N * tan))
              * (dc / dh) ** (0.542 + 0.0471 * N) * (fs / dc) ** 0.984 * (fs / pt) ** -0.349)           # (32)
        J2 = -2.72 + 6.84 * tan                                                                         # (33)
        J3 = 2.66 * tan                                                                                 # (34)
        j = 0.882 * Re ** J1 * (dc / dh) ** J2 * (fs / pt) ** J3 * (fs / dc) ** -1.58 * tan ** -0.2       # (31)
        F1 = (-0.574 - 0.137 * (lnRe - 5.26) ** 0.245 * (pt / dc) ** -0.765 * (dc / dh) ** -0.243
              * (fs / dh) ** -0.474 * tan ** -0.217 * N ** 0.035)                                       # (39)
        F2 = -3.05 * tan; F3 = -0.192 * N; F4 = -0.646 * tan                                            # (40)-(42)
        f = 4.37 * Re ** F1 * (fs / dh) ** F2 * (pl / pt) ** F3 * (dc / dh) ** 0.2054 * N ** F4           # (38)
        branches = ['Eq31_Re_lt_1000', 'Eq38_Re_lt_1000']
    else:
        j1 = (-0.0545 - 0.0538 * tan - 0.302 * N ** -0.24 * (fs / pl) ** -1.3 * (pl / pt) ** 0.379
              * (pl / dh) ** -1.35 * tan ** -0.256)                                                      # (36)
        j2 = (-1.29 * (pl / pt) ** (1.77 - 9.43 * tan) * (dc / dh) ** (0.229 - 1.43 * tan)
              * N ** (-0.166 - 1.08 * tan) * (fs / pt) ** (-0.174 * ln(0.5 * N)))                       # (37)
        j = 0.0646 * Re ** j1 * (dc / dh) ** j2 * (fs / pt) ** -1.03 * (pl / dc) ** 0.432 * tan ** -0.692 * N ** -0.737  # (35)
        f1 = (-0.141 * (fs / pl) ** 0.0512 * tan ** -0.472 * (pl / pt) ** 0.35 * (pt / dh) ** (0.449 * tan)
              * N ** (-0.049 + 0.237 * tan))                                                             # (44)
        f2 = -0.562 * lnRe ** -0.0923 * N ** 0.013                                                      # (45)
        f3 = 0.302 * Re ** 0.03 * (pt / dc) ** 0.026                                                    # (46)
        f4 = -0.306 + 3.63 * tan                                                                        # (47)
        f = 0.228 * Re ** f1 * tan ** f2 * (fs / pl) ** f3 * (pl / dc) ** f4 * (dc / dh) ** 0.383 * (pl / pt) ** -0.247  # (43)
        branches = ['Eq35_Re_ge_1000', 'Eq43_Re_ge_1000']
    return {'colburn_j': j, 'fanning_friction_factor': f, 'branches': branches, 'corrugation_angle_deg': theta,
            'source': 'Wang, Hwang & Lin 2002, Int. J. Refrig. 25:673-680, Eqs. (31)-(47)',
            'friction_definition': 'Fanning, entrance/exit losses included (paper Table 2 note 2)',
            **({'range_extrapolation': extended} if extended else {}),
            'correlation_range_checked': True}


def air_side_factors(g: dict, metrics: dict, Re: float) -> dict:
    """j and f for the declared fin type; Re is based on the collar diameter and Gc."""
    t = g['fin_type']; dc, dh = metrics['collar_diameter_m'], metrics['air_hydraulic_diameter_m']
    pt, pl, pf, n = g['transverse_pitch_m'], g['longitudinal_pitch_m'], g['fin_pitch_m'], g['rows']
    if t == 'plain':
        return wang_plain_fin(Re, dc, dh, pt, pl, pf, n)
    if t == 'louver':
        return wang_louver_1999(Re, dc, dh, pt, pl, pf, n, g['louver_pitch_m'], g['louver_height_m'],
                                metrics['total_outer_area_m2'] / metrics['bare_outer_area_m2'],
                                g.get('correlation_range_tolerance', 0.0))
    if t == 'wavy_herringbone':
        return wang_herringbone_2002(Re, dc, dh, pt, pl, pf, g['fin_thickness_m'], n,
                                     g['wave_height_m'], g['wave_projected_length_m'],
                                     g.get('correlation_range_tolerance', 0.0))
    raise NotImplementedError(f'Unsupported fin_type {t}')


def schmidt_fin_efficiency(dc, pt, pl, rows, fin_thickness, fin_conductivity, h):
    """Schmidt plate-fin efficiency (Wang, Webb & Chi 2000 Eqs. 7-11; staggered,
    or the inline/1-row form for a single row with X_L = Pl/2)."""
    r = dc / 2; xm = pt / 2
    if rows > 1:
        xl = math.hypot(pt / 2, pl) / 2
        ratio = 1.27 * xm / r * math.sqrt(xl / xm - 0.3)
    else:
        xl = pl / 2
        ratio = 1.28 * xm / r * math.sqrt(xl / xm - 0.2)
    if not ratio > 1:
        raise ValueError('Schmidt equivalent radius is not larger than the collar radius')
    m = math.sqrt(2 * h / (fin_conductivity * fin_thickness))
    phi = (ratio - 1) * (1 + 0.35 * math.log(ratio))
    x = m * r * phi
    return math.tanh(x) / x if x > 0 else 1.0


def fin_efficiency_method(g: dict) -> str:
    return g.get('fin_efficiency_method', 'equal_area_annular' if g['fin_type'] == 'plain' else 'schmidt')


def fin_efficiency(g: dict, metrics: dict, h: float) -> float:
    if fin_efficiency_method(g) == 'schmidt':
        return schmidt_fin_efficiency(metrics['collar_diameter_m'], g['transverse_pitch_m'], g['longitudinal_pitch_m'],
                                      g['rows'], g['fin_thickness_m'], g['fin_conductivity_w_m_k'], h)
    from ht import fin_efficiency_Kern_Kraus
    return fin_efficiency_Kern_Kraus(metrics['collar_diameter_m'], metrics['equivalent_annular_fin_outer_diameter_m'],
                                     g['fin_thickness_m'], g['fin_conductivity_w_m_k'], h)


def extrapolation_warning(factors: dict) -> str | None:
    """Disclosure text for a declared boundary extrapolation (None when within range)."""
    ext = factors.get('range_extrapolation')
    if not ext:
        return None
    items = '、'.join(f"{k} {v['value']:.6g}（文献样本{v['published_range'][0]:g}–{v['published_range'][1]:g}，"
                     f"超出{abs(v['relative_excess']):.2%}）" for k, v in ext.items())
    return '边界外推：按声明的correlation_range_tolerance在文献样本范围外使用关联式——' + items + '。结果不属于关联式已验证范围。'


def geometry_extrapolation_warning(g: dict, metrics: dict) -> str | None:
    """Same disclosure from the geometry alone (only geometric bounds can be extended;
    Re = 1000 lies inside both published Re ranges and does not affect this check)."""
    if g['fin_type'] == 'plain' or 'correlation_range_tolerance' not in g:
        return None
    return extrapolation_warning(air_side_factors(g, metrics, 1000.0))
