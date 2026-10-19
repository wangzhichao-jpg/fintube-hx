"""0.1.0.dev11: micro-fin tube geometry and NIST correlations (TN 2224, NISTIR 6333)."""
import copy, json, math
from pathlib import Path
import pytest
from fintube_hx.microfin import (microfin_geometry, kedzierski_lin_nu, nist_two_phase_drop, relative_glide,
                                 microfin_boiling_h)
from fintube_hx.geometry import geometry_metrics
from fintube_hx.engine import run_case

ROOT = Path(__file__).resolve().parents[1]
MF = dict(tube_type='microfin', microfin_count=60, microfin_height_m=0.18e-3, microfin_apex_angle_deg=40.,
          microfin_helix_angle_deg=18., microfin_tip_thickness_m=0.05e-3)


def test_geometry_trapezoid_identities():
    g = microfin_geometry(8.92e-3, 60, 0.2e-3, 50.0, 18.0, 0.04e-3)
    tb = 0.04e-3 + 2 * 0.2e-3 * math.tan(math.radians(25))
    assert g['base_thickness_m'] == pytest.approx(tb)
    # Eq.(1) right-hand form (independent of thicknesses)
    ai = 2 * 60 * 0.2e-3 * math.sqrt(1 + math.tan(math.radians(25)) ** 2) + math.pi * 8.92e-3 - 2 * 60 * 0.2e-3 * math.tan(math.radians(25))
    assert g['area_per_length_m'] == pytest.approx(ai, rel=1e-12)
    assert g['flow_area_m2'] == pytest.approx(math.pi * 8.92e-3 ** 2 / 4 - 60 * 0.2e-3 * (0.04e-3 + tb) / 2)
    assert g['hydraulic_diameter_m'] == pytest.approx(4 * g['flow_area_m2'] / g['area_per_length_m'])
    # Turbo-A (NISTIR 6333 Table 1): Ai/L 44.6 mm published; idealised trapezoid gives 43.3 mm.
    assert g['area_per_length_m'] * 1e3 == pytest.approx(44.6, rel=0.035)


def test_geometry_range_and_overlap_rejected():
    with pytest.raises(ValueError, match='fin height'):
        microfin_geometry(8.92e-3, 60, 0.30e-3, 40.0, 18.0, 0.05e-3)
    with pytest.raises(ValueError, match='overlap'):
        microfin_geometry(8.92e-3, 82, 0.25e-3, 60.0, 18.0, 0.10e-3)


def test_tn2224_figure10_ratios():
    # Fictitious fluid of TN 2224 Fig. 10 (electric heating, Bo = 1e-4); the ratios are independent of k_l.
    def nu(x):
        co = ((1 - x) / x) ** 0.8 * (1 / 30) ** 0.5
        return kedzierski_lin_nu(5000., 4., 0.2, 1e-4, 0.015, co, 30., x)
    # Read from the published curve (300 dpi): 1.50, 2.26, 3.08 kW/m2K at x = 0.1, 0.5, 0.9.
    assert nu(0.1) / nu(0.5) == pytest.approx(1.50 / 2.26, rel=0.02)
    assert nu(0.9) / nu(0.5) == pytest.approx(3.08 / 2.26, rel=0.02)


def test_glide_factor_and_r410a_glide():
    assert relative_glide('R32', 9e5) == 0.0
    assert relative_glide('R410A', 920.5e3) * 277.6 == pytest.approx(0.110, abs=0.01)   # TN 2224 Table 3
    base = kedzierski_lin_nu(5000., 4., 0.2, 1e-4, 0.015, 1.0, 30., 0.5)
    assert kedzierski_lin_nu(5000., 4., 0.2, 1e-4, 0.015, 1.0, 30., 0.5, 4e-4) < base


def test_nistir6333_drop_hand_value():
    sat = {'h_g_j_kg': 420e3, 'h_l_j_kg': 220e3, 'mu_l': 1.6e-4}
    geom = {'flow_area_m2': 60.8e-6, 'hydraulic_diameter_m': 5.45e-3}
    f, a, info = nist_two_phase_drop(0.0182, geom, sat, 0.3, 0.4, 0.010, 0.013, 1.0)
    G = 0.0182 / 60.8e-6
    fn = 0.00506 * (G * 5.45e-3 / 1.6e-4) ** -0.0951 * (0.1 * 200e3 / 9.80665) ** 0.1554
    assert info['f_N'] == pytest.approx(fn) and f == pytest.approx(fn * 0.023 / 5.45e-3 * G ** 2)
    assert a == pytest.approx(0.003 * G ** 2)
    with pytest.raises(ValueError, match='K_f'):
        nist_two_phase_drop(0.0182, geom, sat, 0.3, 0.3, 0.010, 0.010, 1.0)


def test_metrics_and_field_rules():
    c = json.loads((ROOT / 'examples/water_geometry.json').read_text(encoding='utf8'))
    g = dict(c['geometry'], tube_inner_diameter_m=0.0089, tube_outer_diameter_m=0.00952, **MF)
    m = geometry_metrics(g)
    assert m['inner_area_m2'] == pytest.approx(m['microfin']['area_per_length_m'] * g['tube_length_m'] * m['tube_count'])
    assert m['inner_area_m2'] > math.pi * 0.0089 * g['tube_length_m'] * m['tube_count']
    with pytest.raises(ValueError, match='applies only to tube_type=microfin'):
        geometry_metrics(dict(c['geometry'], microfin_count=60))
    with pytest.raises(ValueError, match='required'):
        geometry_metrics(dict(g, microfin_count=None))
    with pytest.raises(NotImplementedError, match='refrigerant evaporator networks only'):
        run_case(dict(c, geometry=g))
