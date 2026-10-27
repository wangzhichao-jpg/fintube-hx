"""Air-side pressure-drop breakdown for the v1 pressure scope (spec A1-A4, contract section 3).

Data-reduction basis, checked against the originals (D0):
* Wang, Chi & Chang 2000 Part I Eq. (17), Wang et al. 1999 Eq. (13) and Wang et al. 2002 Table 2 note 2
  reduce the Fanning f with the Kays-London equation without Kc/Ke: entrance and exit losses are
  **included in f**.  They are reported as ``'included_in_f'`` and never added again.
* The same equations subtract the flow-acceleration term (1 + sigma^2)(rho1/rho2 - 1); it is therefore
  added here:  dp_acc = G^2/(2 rho1) * (1 + sigma^2) * (rho1/rho2 - 1).
  (Wang, Lin & Lee 2000 print Eq. (6) as "+(1 - sigma^2)(rho1/rho2 - 1)"; this contradicts the
  Kays-London derivation and the authors' own Part I Eq. (17) and is treated as a misprint.)
* Core friction keeps the legacy isothermal form f * (4 L/Dh) * G^2/(2 rho1) (rho1/rho_m ~ 1 is not
  applied), so the v0 'air_pressure_drop_pa' meaning is unchanged.
* Wet increment = phi_wet * (f_wet - f_dry) * (4 L/Dh) * G^2/(2 rho1), phi_wet = wetted fraction of the
  outer area (1 or 0 for the lumped coil, per-row in tube networks).
"""
from __future__ import annotations

ENTRANCE_EXIT_IN_F = {
    'plain': 'Wang, Chi & Chang 2000 Part I, IJHMT 43:2681, Eq. (17)',
    'louver': 'Wang, Lee, Chang & Lin 1999, IJHMT 42:1945, Eq. (13)',
    'wavy_herringbone': 'Wang, Hwang & Lin 2002, IJR 25:673, Table 2 note 2',
}
WET_TOTAL_LABEL = '空气压降（不含湿附加）'
TOTAL_LABEL = '空气压降（芯体摩擦 + 加速 + 湿附加；进出口已含于 f）'


def acceleration_pa(G: float, rho_in: float, rho_out: float, sigma: float) -> float:
    return G ** 2 / (2 * rho_in) * (1 + sigma ** 2) * (rho_in / rho_out - 1)


def friction_pa(f: float, depth: float, dh: float, G: float, rho_in: float) -> float:
    """Same expression and evaluation order as the legacy core friction."""
    return f * 4 * depth / dh * G ** 2 / (2 * rho_in)


NEGATIVE_EXTRAPOLATED_INCREMENT = '湿工况片距外推得到的湿附加为负（湿表面摩擦系数小于干表面），视为外推失效，湿附加未计算'


def checked_wet_increment(wet: dict, increment_pa: float):
    """(increment, reason): a declared fin-pitch extrapolation that gives a negative wet increment is a failed
    extrapolation (validity guard, not a physical correction); everything else is returned unchanged."""
    if 'fin_pitch_extrapolated' in wet and increment_pa < 0:
        wet['not_computed'] = NEGATIVE_EXTRAPOLATED_INCREMENT
        return None, NEGATIVE_EXTRAPOLATED_INCREMENT
    return increment_pa, None


def breakdown(*, fin_type: str, core_friction_pa: float, acceleration: float, wet_fraction: float,
              wet_increment_pa: float | None, wet_reason: str | None) -> dict:
    """Assemble the contract fields.  wet_increment_pa None with wet_fraction > 0 means 'not computed'."""
    parts = {'core_friction': core_friction_pa, 'entrance': 'included_in_f', 'exit': 'included_in_f',
             'acceleration': acceleration}
    total = core_friction_pa + acceleration
    if wet_fraction <= 0:
        parts['wet_increment'] = 0.0
        label = TOTAL_LABEL
    elif wet_increment_pa is None:
        parts['wet_increment'] = {'not_computed': wet_reason}
        label = WET_TOTAL_LABEL
    else:
        parts['wet_increment'] = wet_increment_pa
        total += wet_increment_pa
        label = TOTAL_LABEL
    return {'air_pressure_drop_breakdown_pa': parts, 'air_pressure_drop_total_pa': total,
            'air_pressure_drop_total_label': label,
            'air_pressure_drop_basis': {'entrance_exit_included_in_f': ENTRANCE_EXIT_IN_F[fin_type],
                                        'wet_fraction': wet_fraction}}
