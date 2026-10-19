"""Micro-fin (inner-grooved) tube geometry, convective boiling and two-phase pressure drop.

Original implementations of published NIST equations (US-government works):

* Geometry: Kedzierski & Lin (2023), NIST TN 2224, Eqs. (1), (4), (5), left-hand forms
  (trapezoidal fin with tip thickness t_t; base thickness t_b = t_t + 2 e tan(beta/2)).
  The right-hand forms of Eqs. (4)-(5) as printed are dimensionally inconsistent and are
  not used.  Fin parameters are taken in the cross section perpendicular to the tube axis.
* Boiling: Kedzierski & Lin (2023) Eq. (7) for pure/azeotropic fluids, Eq. (8) glide factor;
  Nu = h Dh / k_l with h based on the actual inner area A_i; Re, G based on A_ca and Dh.
* Two-phase pressure drop: Choi, Kedzierski & Domanski (1999), NISTIR 6333, Eqs. (15)-(16):
  dP = [f_N L (v_out + v_in)/Dh + (v_out - v_in)] G^2,  f_N = 0.00506 Re_fo^-0.0951 K_f^0.1554,
  K_f = |dx| i_fg / (L g).

Geometric parameters outside TN 2224 Table 4 raise; operating parameters outside it are
flagged (``out_of_range``) for disclosure, never extrapolated silently.
"""
from __future__ import annotations
import math

G_ACCEL = 9.80665
TN2224_GEOMETRY_RANGE = {'root diameter': (2.11e-3, 11.98e-3), 'hydraulic diameter': (0.95e-3, 6.67e-3),
                         'helix angle deg': (6.3, 30.0), 'apex angle deg': (11.0, 66.0),
                         'fin height': (0.10e-3, 0.26e-3), 'fin count': (40, 82)}
TN2224_OPERATING_RANGE = {'G': (48., 859.), 'T_sat_K': (268.1, 333.1), 'q_flux': (700., 50500.),
                          'Bd': (3.5e-3, 3.8e-2), 'Bo': (1.2e-5, 1.9e-3), 'Co': (5.7e-3, 20.), 'Re': (628., 23512.),
                          'rho_ratio': (5., 147.), 'Pr': (1.77, 5.75), 'p_reduced': (0.04, 0.69), 'x': (0.002, 0.986),
                          'glide_rel': (0., 8.4e-2)}
X_MIN, X_MAX = 0.002, 0.986


def microfin_geometry(root_diameter, fin_count, fin_height, apex_angle_deg, helix_angle_deg, tip_thickness):
    dr, n, e, tt = float(root_diameter), int(fin_count), float(fin_height), float(tip_thickness)
    half = math.radians(apex_angle_deg) / 2
    tb = tt + 2 * e * math.tan(half)
    if not (tt >= 0 and e > 0 and 0 < half < math.pi / 2):
        raise ValueError('Micro-fin height, tip thickness and apex angle must be physical')
    if n * tb >= math.pi * dr:
        raise ValueError('Micro-fin bases overlap: fin_count * base thickness exceeds the root circumference')
    if 2 * e >= dr:
        raise ValueError('Micro-fin height too large for the root diameter')
    ai_l = 2 * n * math.sqrt(e ** 2 + ((tb - tt) / 2) ** 2) + math.pi * dr - n * (tb - tt)       # Eq. (1)
    aca = math.pi * dr ** 2 / 4 - n * e * (tt + tb) / 2                                          # Eq. (4)
    dh = 4 * aca / ai_l                                                                           # Eq. (5)
    values = {'root diameter': dr, 'hydraulic diameter': dh, 'helix angle deg': float(helix_angle_deg),
              'apex angle deg': float(apex_angle_deg), 'fin height': e, 'fin count': n}
    for key, v in values.items():
        lo, hi = TN2224_GEOMETRY_RANGE[key]
        if not lo * (1 - 1e-9) <= v <= hi * (1 + 1e-9):
            raise ValueError(f'Micro-fin {key}={v:g} outside NIST TN 2224 Table 4 range [{lo:g},{hi:g}]')
    return {'area_per_length_m': ai_l, 'flow_area_m2': aca, 'hydraulic_diameter_m': dh,
            'base_thickness_m': tb, 'tip_thickness_m': tt, 'area_ratio_to_root_smooth': ai_l / (math.pi * dr),
            'source': 'Kedzierski & Lin 2023, NIST TN 2224, Eqs. (1),(4),(5)'}


def kedzierski_lin_nu(Re, Pr, p_reduced, Bo, Bd, Co, rho_ratio, x, glide_rel=0.0):
    """Local convective-boiling Nusselt number, TN 2224 Eqs. (7)-(8)."""
    C1 = 0.53 - 0.64 * x ** 2
    C2 = -0.23 * x ** 2
    C3 = -5.80 * x + 7.46 * x ** 2
    C4 = 0.44 - 0.77 * x + 0.40 * x ** 2
    C5 = 0.56 - 0.11 * x
    C6 = -0.068
    C7 = -4.70 * x + 6.22 * x ** 2
    nu = 713.50 * Re ** C1 * Pr ** C2 * p_reduced ** C3 * Bo ** C4 * Bd ** C5 * Co ** C6 * rho_ratio ** C7
    if glide_rel > 0:
        nu *= 1 - 0.166 * glide_rel ** (0.12 * x * (1 - x))
    return nu


def boiling_dimensionless(flow, x, sat, geom, heat_flux, fin_count, fin_height, glide_rel=0.0):
    G = flow / geom['flow_area_m2']; dh = geom['hydraulic_diameter_m']
    ifg = sat['h_g_j_kg'] - sat['h_l_j_kg']
    out = {'G': G, 'Re': G * dh / sat['mu_l'], 'Pr': sat['cp_l'] * sat['mu_l'] / sat['k_l'],
           'p_reduced': sat['pressure_pa'] / sat['p_crit_pa'], 'Bo': abs(heat_flux) / (G * ifg),
           'Bd': G_ACCEL * dh * (sat['rho_l'] - sat['rho_g']) * fin_height / (sat['sigma'] * fin_count),
           'Co': ((1 - x) / x) ** 0.8 * (sat['rho_g'] / sat['rho_l']) ** 0.5, 'rho_ratio': sat['rho_l'] / sat['rho_g'],
           'x': x, 'q_flux': abs(heat_flux), 'T_sat_K': sat['t_sat_c'] + 273.15, 'glide_rel': glide_rel}
    out['out_of_range'] = sorted(k for k, (lo, hi) in TN2224_OPERATING_RANGE.items()
                                 if not lo * (1 - 1e-9) <= out[k] <= hi * (1 + 1e-9))
    return out


def microfin_boiling_h(flow, x, sat, geom, heat_flux, fin_count, fin_height, glide_rel=0.0):
    """h [W/m2K] based on the actual inner area; quality limited to the TN 2224 range by caller."""
    d = boiling_dimensionless(flow, x, sat, geom, heat_flux, fin_count, fin_height, glide_rel)
    if d['Bo'] <= 0:
        raise ValueError('Kedzierski-Lin micro-fin boiling needs a positive heat flux (Bo>0); no flux floor')
    nu = kedzierski_lin_nu(d['Re'], d['Pr'], d['p_reduced'], d['Bo'], d['Bd'], d['Co'], d['rho_ratio'], x, glide_rel)
    return nu * sat['k_l'] / geom['hydraulic_diameter_m'], {**d, 'Nu': nu}


def nist_two_phase_drop(flow, geom, sat_mean, x_in, x_out, v_in, v_out, length):
    """NISTIR 6333 Eq. (15)-(16): returns (friction_pa, acceleration_pa, info)."""
    G = flow / geom['flow_area_m2']; dh = geom['hydraulic_diameter_m']
    ifg = sat_mean['h_g_j_kg'] - sat_mean['h_l_j_kg']
    re_fo = G * dh / sat_mean['mu_l']
    kf = abs(x_out - x_in) * ifg / (length * G_ACCEL)
    if kf <= 0:
        raise ValueError('NISTIR 6333 friction factor needs a nonzero quality change (K_f>0)')
    f_n = 0.00506 * re_fo ** -0.0951 * kf ** 0.1554
    return f_n * length * (v_out + v_in) / dh * G ** 2, (v_out - v_in) * G ** 2, {'f_N': f_n, 'Re_fo': re_fo, 'K_f': kf}


# Temperature glide for the TN 2224 mixture factor (Eq. 8).  CoolProp's predefined blends
# such as "R410A" are pseudo-pure (no glide); the glide is therefore evaluated with the
# HEOS mixture of the declared components at the local pressure (bubble-point basis).
BLENDS = {'R410A': (('R32', 'R125'), (0.50, 0.50)),
          'R407C': (('R32', 'R125', 'R134a'), (0.23, 0.25, 0.52)),
          'R404A': (('R125', 'R143a', 'R134a'), (0.44, 0.52, 0.04))}
_GLIDE_CACHE = {}


def relative_glide(name: str, pressure_pa: float) -> float:
    """(T_dew - T_bubble)/T_bubble at the local pressure; 0 for pure fluids."""
    import CoolProp.CoolProp as CP
    if name in BLENDS:
        key = (name, round(pressure_pa, -1))
        if key not in _GLIDE_CACHE:
            comps, mass = BLENDS[name]
            n = [m / CP.PropsSI('M', c) for m, c in zip(mass, comps)]; s = sum(n)
            st = CP.AbstractState('HEOS', '&'.join(comps)); st.set_mole_fractions([v / s for v in n])
            st.update(CP.PQ_INPUTS, pressure_pa, 0.0); tb = st.T()
            st.update(CP.PQ_INPUTS, pressure_pa, 1.0); td = st.T()
            _GLIDE_CACHE[key] = (td - tb) / tb
        return _GLIDE_CACHE[key]
    if CP.get_fluid_param_string(name, 'pure') == 'true':
        return 0.0
    raise NotImplementedError(f'Temperature glide of {name} is not defined for the micro-fin mixture factor; '
                              'add its composition to fintube_hx.microfin.BLENDS')
