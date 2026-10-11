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
  Continuous plain-fin and staggered-tube geometry metrics (fin area, primary area, minimum free flow area, hydraulic diameter) and the Wang & Chi (2000) air-side Colburn $j$ and Fanning $f$ correlations.
- **`fintube_hx.water` & `fintube_hx.refrigerant`**  
  Coil rating implementations for liquid water coils, direct expansion evaporators, and air-cooled condensers.
- **`fintube_hx.inverse`**  
  Robust inverse solvers. Employs bounded 1D root-finding (Brent / bisection) to determine required mass flow rate for a target outlet air/fluid temperature, superheat, or subcooling.
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
