"""Rebuild the Tan 2015 lumped inputs from validation/measured-v6 and rerun them with the open core.

Derivations (see tan2015_fcu_measured.json -> declaration.inputs_derivation):
  * dry-air flow during the wet test = air-side capacity / (h_in - h_out) from measured dry/wet bulbs (D2)
  * Pt = coil height / tubes per row (D1); Pl from the scaled circuit drawings: 22 mm (9.52 mm tubes), 12.7 mm (7 mm) (D2)
  * louver Lh/Lp = 0.583 reference (D4), Schmidt fin efficiency, Threlkeld/Braun wet surface
Usage: python tools/run_measured_v6_tan.py [--check]   (--check compares with the recorded results)
"""
import json, sys
from pathlib import Path
from CoolProp.HumidAirProp import HAPropsSI
from CoolProp.CoolProp import PropsSI
from fintube_hx.engine import run_case

V6 = Path(__file__).resolve().parents[1] / 'validation/measured-v6'
P = 101325.0
PL = {'pre': 0.022, 'post': 0.0127}
LP, LH = 0.0024, 0.0014


def build(rec, geom_tables):
    g0 = geom_tables[rec['design']]
    t, wb = rec['air_in_db_c'], rec['air_in_wb_c']
    hin = HAPropsSI('H', 'T', t + 273.15, 'B', wb + 273.15, 'P', P)
    hout = HAPropsSI('H', 'T', rec['air_out_db_c'] + 273.15, 'B', rec['air_out_wb_c'] + 273.15, 'P', P)
    rh = HAPropsSI('R', 'T', t + 273.15, 'B', wb + 273.15, 'P', P)
    v_da = HAPropsSI('V', 'T', t + 273.15, 'R', rh, 'P', P)
    m_da = rec['q_air_kw'] * 1000 / (hin - hout)
    do = g0['tube_od_mm'] / 1000
    geometry = {'fin_type': 'louver', 'tube_type': 'smooth', 'arrangement': 'staggered', 'rows': g0['rows'],
                'tubes_per_row': g0['tubes_per_row'], 'circuits_count': rec['circuits'], 'tube_length_m': rec['tube_length_mm'] / 1000,
                'tube_outer_diameter_m': do, 'tube_inner_diameter_m': do - 2 * g0['wall_mm'] / 1000,
                'transverse_pitch_m': g0['height_mm'] / 1000 / g0['tubes_per_row'], 'longitudinal_pitch_m': PL[rec['design']],
                'fin_pitch_m': 0.0254 / g0['fpi'], 'fin_thickness_m': g0['fin_t_mm'] / 1000, 'fin_conductivity_w_m_k': 204.0,
                'tube_conductivity_w_m_k': 390.0, 'tube_roughness_m': 0.0, 'louver_pitch_m': LP, 'louver_height_m': LH,
                'fin_efficiency_method': 'schmidt'}
    rho_w = PropsSI('D', 'T', rec['water_in_c'] + 273.15, 'P', 3e5, 'Water')
    return {'schema_version': '0.1', 'name': f"tan2015-{rec['design']}-{rec['unit']}-{rec['sample']}", 'kind': 'water',
            'air': {'t_db_c': t, 'relative_humidity': rh, 'pressure_pa': P, 'volume_flow_m3_h': m_da * v_da * 3600},
            'fluid': {'name': 'Water', 'pressure_pa': 3e5, 'inlet_t_c': rec['water_in_c'], 'mass_flow_kg_s': rec['water_m3_h'] * rho_w / 3600},
            'model': {'ua_mode': 'geometry', 'segments': 20, 'air_arrangement': 'counterflow', 'wet_surface_model': 'threlkeld_braun'},
            'solver': {'max_iterations': 300, 'tolerance_k': 1e-6}, 'geometry': geometry}


def main():
    meas = json.loads((V6 / 'tan2015_fcu_measured.json').read_text(encoding='utf8'))
    recorded = {(r['design'], r['unit'], r['sample']): r for r in
                json.loads((V6 / 'tan2015_fcu_results.json').read_text(encoding='utf8'))['lumped_core']['rows']}
    worst = 0.0; n = 0
    for rec in meas['records']:
        key = (rec['design'], rec['unit'], rec['sample'])
        if key not in recorded:
            continue
        r = run_case(build(rec, meas['geometry_tables']))
        dq = r['heat_transfer_w'] / (rec['q_water_kw'] * 1000) - 1
        worst = max(worst, abs(dq - recorded[key]['dev_ref']['qw_rel'])); n += 1
        if '--check' not in sys.argv:
            print(f"{key}  ΔQw {dq*100:+.2f}%")
    print(f'{n} units rerun; max |ΔQw - recorded| = {worst:.2e}')
    return 0 if worst < 1e-9 else 1


if __name__ == '__main__':
    sys.exit(main())
