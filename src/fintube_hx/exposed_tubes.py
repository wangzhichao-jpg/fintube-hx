"""Dry convection from bare tube lengths and return bends outside the finned core.

Small test coils and many installed coils have unfinned straight tube ends and
U-bends standing in the air stream. Their surface is not part of the Wang
plain-fin area. This module adds that surface explicitly, as a separate
cylinder-in-crossflow element with its own declared approach velocity.

Scope (disclosed in every result):
- Churchill-Bernstein average Nusselt number for a single circular cylinder in
  crossflow; bends are treated as curved cylinders with the same correlation.
- The exposed elements exchange heat with a separate stream at the coil inlet
  air state; that stream is not mixed into the finned-core outlet air.
- Dry surfaces only; a wet exposed surface is rejected instead of guessed.
"""
from __future__ import annotations
import math
from CoolProp.HumidAirProp import HAPropsSI
from ht.conv_external import Nu_cylinder_Churchill_Bernstein

ALLOWED = {'straight_length_per_tube_m', 'return_bend_count', 'return_bend_centerline_radius_m',
           'approach_velocity_m_s', 'notes', 'source'}


def _positive_number(value, label, minimum=0.0, maximum=None, strict=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{label} must be a finite number')
    value = float(value)
    if value < minimum or (strict and value == minimum):
        raise ValueError(f'{label} must be {">" if strict else ">="} {minimum}')
    if maximum is not None and value > maximum:
        raise ValueError(f'{label} must be <= {maximum}')
    return value


def normalize_exposed_tubes(spec, *, derived_bend_count=None):
    """Validate the exposed-surface declaration on a copy.

    ``derived_bend_count`` is supplied by network models that know the actual
    tube-to-tube connections; lumped models require an explicit count.
    """
    if not isinstance(spec, dict):
        raise ValueError('model.exposed_tubes must be an object')
    unknown = set(spec) - ALLOWED
    if unknown:
        raise ValueError('Unsupported model.exposed_tubes fields: ' + ', '.join(sorted(unknown)))
    s = dict(spec)
    s['straight_length_per_tube_m'] = _positive_number(s.get('straight_length_per_tube_m', 0.0),
                                                       'model.exposed_tubes.straight_length_per_tube_m', 0.0, 5.0)
    if 'return_bend_count' in s:
        n = s['return_bend_count']
        if isinstance(n, bool) or not isinstance(n, int) or not 0 <= n <= 10000:
            raise ValueError('model.exposed_tubes.return_bend_count must be an integer 0..10000')
        if derived_bend_count is not None and n != derived_bend_count:
            raise ValueError('model.exposed_tubes.return_bend_count disagrees with the network connections '
                             f'({derived_bend_count}); omit it to use the network value')
    elif derived_bend_count is not None:
        s['return_bend_count'] = int(derived_bend_count)
    else:
        raise ValueError('model.exposed_tubes.return_bend_count is required for lumped coils')
    if s['return_bend_count'] > 0:
        s['return_bend_centerline_radius_m'] = _positive_number(
            s.get('return_bend_centerline_radius_m'), 'model.exposed_tubes.return_bend_centerline_radius_m',
            0.0, 0.5, strict=True)
    elif 'return_bend_centerline_radius_m' in s:
        s['return_bend_centerline_radius_m'] = _positive_number(
            s['return_bend_centerline_radius_m'], 'model.exposed_tubes.return_bend_centerline_radius_m', 0.0, 0.5, strict=True)
    s['approach_velocity_m_s'] = _positive_number(s.get('approach_velocity_m_s'),
                                                  'model.exposed_tubes.approach_velocity_m_s', 0.0, 30.0, strict=True)
    for key in ('notes', 'source'):
        if key in s and not isinstance(s[key], str):
            raise ValueError(f'model.exposed_tubes.{key} must be a string')
    if s['straight_length_per_tube_m'] == 0 and s['return_bend_count'] == 0:
        raise ValueError('model.exposed_tubes declares no exposed surface; omit the object instead')
    return s


def exposed_lengths(spec, tube_count):
    straight = spec['straight_length_per_tube_m'] * tube_count
    bends = spec['return_bend_count'] * math.pi * spec.get('return_bend_centerline_radius_m', 0.0)
    return straight, bends


def outside_coefficient(spec, outer_diameter_m, air_in, surface_t_c):
    """Average dry outside coefficient at film temperature, inlet humidity ratio."""
    if surface_t_c < air_in['dew_point_c']:
        raise ValueError('Exposed tube surface below inlet dew point; wet exposed-tube transfer is not modelled')
    film = (air_in['t_db_c'] + surface_t_c) / 2 + 273.15
    p, w = air_in['pressure_pa'], air_in['humidity_ratio_kg_kg_da']
    args = ('T', film, 'P', p, 'W', w)
    mu = HAPropsSI('M', *args); k = HAPropsSI('K', *args)
    cp = HAPropsSI('C', *args) / (1 + w); rho = (1 + w) / HAPropsSI('V', *args)
    pr = cp * mu / k
    re = rho * spec['approach_velocity_m_s'] * outer_diameter_m / mu
    if re * pr <= 0.2:
        raise ValueError('Exposed tube Re*Pr <= 0.2 is outside the Churchill-Bernstein correlation')
    nu = Nu_cylinder_Churchill_Bernstein(re, pr)
    return {'h_w_m2_k': nu * k / outer_diameter_m, 'reynolds': re, 'prandtl': pr, 'nusselt': nu,
            'film_temperature_c': film - 273.15}


def element_conductance(length_m, outer_diameter_m, inner_diameter_m, tube_conductivity, h_out, h_in):
    """Series outside/wall/inside conductance of a bare tube element of length L."""
    if length_m <= 0:
        return 0.0
    r_out = 1 / (h_out * math.pi * outer_diameter_m * length_m)
    r_in = 1 / (h_in * math.pi * inner_diameter_m * length_m)
    r_wall = math.log(outer_diameter_m / inner_diameter_m) / (2 * math.pi * tube_conductivity * length_m)
    return 1 / (r_out + r_wall + r_in)


def element_heat_to_fluid(ua, flow_kg_s, cp_j_kg_k, fluid_t_c, air_t_c):
    """Exact constant-air-temperature element: fluid approaches the air temperature."""
    if ua <= 0:
        return 0.0
    capacity = flow_kg_s * cp_j_kg_k
    return capacity * (air_t_c - fluid_t_c) * (1 - math.exp(-ua / capacity))


MODEL_NOTE = ('Exposed bare tube/return-bend surface: Churchill-Bernstein single-cylinder crossflow at the '
              'declared approach velocity and inlet air state, dry only; heat goes to a separate air stream, '
              'not to the finned-core outlet air.')
