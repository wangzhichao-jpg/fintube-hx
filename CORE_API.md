# Core Architecture & API Specification

`fintube_hx` provides a modular, lightweight computational engine for fin-tube heat exchanger rating and inverse design. This document outlines the architecture, internal modules, and API contracts.

---

## 1. Module Hierarchy

The package is organized into decoupled layers:

- **`fintube_hx.properties`**  
  Interface to CoolProp and humid air thermophysical properties. Handles single-phase transport properties, saturation curves, and phase equilibrium queries.
- **`fintube_hx.thermal`**  
  Fundamental heat and mass transfer building blocks, including sensible/latent heat exchange, wet coil contact factors, and condensate drain energy accounting.
- **`fintube_hx.geometry` & `fintube_hx.wang_plain_fin`**  
  Continuous plain-fin and staggered-tube geometry metrics (fin area, primary area, minimum free flow area, hydraulic diameter) and the Wang & Chi (2000) air-side Colburn $j$ and Fanning $f$ correlations. Optional `fin_count` gives the actual number of fins (area only; the correlation hydraulic diameter stays periodic).
- **`fintube_hx.exposed_tubes`** (0.1.0.dev7)  
  Dry Churchill–Bernstein convection of unfinned straight tube ends and return bends standing in the air stream (`model.exposed_tubes`), with exact constant-air-temperature element heat. Used by the lumped water model and available to extensions.
- **`fintube_hx.airside`** (0.1.0.dev9)  
  Air-side j/f dispatch by `geometry.fin_type` (plain: Wang & Chi 2000; louver: Wang et al. 1999; wavy_herringbone: Wang et al. 2002) with published sample-range checks (optionally extended for geometric bounds only by a declared `geometry.correlation_range_tolerance` ≤ 1 %, disclosed in results, 0.1.0.dev10), and fin efficiency by `geometry.fin_efficiency_method` (equal-area annular, legacy default for plain fins; Schmidt, default for the enhanced fins).
- **`fintube_hx.errors`** (0.1.0.dev16, API 2)  
  `ModelRangeError` (a `ValueError`) and `UnsupportedFeatureError` (also a `NotImplementedError`): Chinese `message_zh` (= `str(exc)`, with the former English text kept in parentheses), `field`, `value`, `allowed`, `source`, `fallbacks` (user-confirmed patches) and `to_dict()`.
- **`fintube_hx.airside`** additions (0.1.0.dev16)  
  `air_side_factors_by_row` (7–12 rows only with `geometry.row_extrapolation: "saturate_at_row_6"`), declared plain-fin pitch extrapolation (`geometry.fin_pitch_extrapolation`), `wang_lin_lee_2000_wet_plain` and `wet_friction_factor` (wet Fanning f or a `not_computed` reason).
- **`fintube_hx.airside_pressure`** and **`fintube_hx.coverage`** (0.1.0.dev16)  
  v1 air-pressure breakdown (acceleration, entrance/exit included in f, wet increment) and the `model_coverage` vocabulary; `schema.normalize_pressure_scope` validates `model.pressure_scope`.
- **Exact fast paths** (0.1.0.dev17)  
  `properties.air_wh`, `properties.air_from_h_w_wh`, `thermal.air_with_h_w_wh` and `contact_air(..., wh_only=True)` return only the humidity ratio and enthalpy, bit-identical to the full routines (same CoolProp calls and refusals) without the unused volume/cp/dew-point evaluations; `contact_air(..., outlet_state=False)` is now bit-identical in the wet branch too. Optional `solver.time_limit_s` (wall-time fuse, enforced by tube networks). Row extrapolation additionally requires the local row-6 j ≥ 0.5·j(6).
- **Declared wet-friction fin-pitch extrapolation** (0.1.0.dev19)  
  Optional `geometry.wet_friction_fin_pitch_extrapolation: true` (plain, bare-aluminium fins, 3.2 mm < Fp ≤ 4.0 mm): only the fin-pitch upper bound of Wang, Lin & Lee 2000 is raised; the wet friction record carries `fin_pitch_extrapolated`, the coverage an `extrapolated` item `wet_friction_fin_pitch_extrapolated`; a negative extrapolated wet increment is reported as not computed (`airside_pressure.checked_wet_increment`). Invalid declarations raise `ModelRangeError`. Absent key: results unchanged.
- **`fintube_hx.thermal.check_subzero_surface`** (0.1.0.dev12)  
  Optional dry sub-zero evaporating surfaces (`model.subzero_evaporation: dry_only`): accepted only at or above the local air frost point; frost deposition is rejected.
- **`fintube_hx.microfin`** (0.1.0.dev11)  
  Micro-fin tube geometry (NIST TN 2224 Eqs. 1, 4, 5, left-hand forms), Kedzierski & Lin (2023) convective-boiling Nusselt number with the mixture glide factor and the HEOS-based glide of R410A/R407C/R404A, and the NISTIR 6333 two-phase pressure drop. Geometry outside TN 2224 Table 4 raises; operating parameters outside it are flagged.
- **`fintube_hx.wet_surface`** (0.1.0.dev8)  
  Optional wet-surface element: Braun–Klein–Mitchell (1989) enthalpy-potential ε-NTU, Threlkeld wet-fin efficiency, effective-surface outlet humidity and the larger-of-dry-and-wet rule (`model.wet_surface_model: threlkeld_braun`). Used by the lumped geometry water model and available to extensions.
- **`fintube_hx.water` & `fintube_hx.refrigerant`**  
  Coil rating implementations for liquid water coils, direct expansion evaporators, and air-cooled condensers.
- **`fintube_hx.inverse`**  
  Bounded 1D Brent root-finding for water outlet temperature, refrigerant superheat or subcooling. Outlet-air-temperature targets are not implemented. A user bracket selects one root; monotonicity and global uniqueness are not certified.
- **`fintube_hx.schema` & `fintube_hx.units`**  
  Schema normalization, strict contract validation, and explicit engineering unit conversions.
- **`fintube_hx.engine`**  
  Top-level facade coordinating case validation, model dispatching, forward evaluation, and inverse solving.
- **`fintube_hx.spreadsheet` & `fintube_hx.reporting`**  
  Native Excel (.xlsx) and CSV export utilities for case snapshots, multi-run batches, and parametric scans.

---

## 2. API Design Principles

### Deterministic & Conservation-Enforcing
Every rating calculation checks energy balance closure:
$$\Delta \dot{Q} = |\dot{Q}_{\text{air}} - \dot{Q}_{\text{fluid}}|$$
Energy residuals are explicitly recorded in results. Out-of-bounds states or non-converged iterations are reported as distinct non-converged states rather than fabricated approximations.

### Snapshot-Based Immutability
All calculations operate on self-contained JSON-serializable dictionaries. Solvers do not mutate their input cases. Output dictionaries contain complete metadata, execution timestamps, convergence metrics, and full copies of the requested inputs.

### Strict Validation
The schema validator (`validate_case`) strictly checks input fields against supported models before dispatching to numerical solvers. Unknown fields or mutually contradictory options (such as supplying both two-phase inlet temperature and enthalpy) are rejected with clear diagnostics.

---

## 3. Python Integration

### Direct Case Evaluation
```python
from fintube_hx.engine import run_case
from fintube_hx.storage import load_case

case = load_case("examples/water_geometry.json")
result = run_case(case)

assert result["converged"]
print(f"Capacity: {result['heat_transfer_w']:.2f} W")
```

### Inverse Mass Flow Solving
When `case["target"]` is specified (e.g., target outlet temperature), `run_case` automatically engages the inverse solver:
```json
{
  "target": {
    "outlet_temperature_c": 12.0,
    "mass_flow_bounds_kg_s": [0.01, 0.5],
    "tolerance_k": 0.001
  }
}
```
The solver returns both the solved operating inputs and the final verified state.
