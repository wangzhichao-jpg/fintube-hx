# Model Scope & Integration Guide

This document describes the scope of the `fintube_hx` baseline models and guidelines for extending or integrating them into external workflows.

---

## 1. Supported Model Scope

The baseline package provides clean, reproducible reference models for fin-tube heat exchanger thermal rating:

1. **Air-to-Water Heat Exchanger**
   - **Input-UA Mode**: Fast thermal rating with user-supplied overall UA ($W/K$).
   - **Geometric Mode**: Predicts overall conductance from tube and plain-fin dimensions using:
     - Air side: Wang & Chi (2000) plain fin correlation.
     - Water side: Hausen (laminar entry) and Gnielinski (turbulent) internal flow correlations, with Churchill friction factors.
     - Sensible heating and wet cooling (condensation) regimes.

2. **Refrigerant Evaporator & Condenser**
   - **Input-UA Mode**: Fast rating based on refrigerant saturation properties and input overall conductance.
   - Handles subcooled liquid, two-phase saturation, and superheated vapor regions.

3. **Parametric & Inverse Solvers**
   - Single-variable parameter scans over arbitrary inputs (air flow, fluid flow, inlet temperature, etc.).
   - Inverse mass-flow rate targeting for specified outlet temperatures or superheat/subcooling.

---

## 2. Model Assumptions & Boundaries

- **Fin Type**: Continuous plain flat fins with round tubes in a staggered layout. Enhanced surfaces (wavy, louvered, slit) and microchannel geometries are not covered by this baseline core.
- **Airflow**: 1D uniform face velocity and row-by-row air mixing. Two-dimensional maldistribution and CFD velocity profile mappings are external to this core.
- **Tube Circuiting**: The baseline models use lumped cross-counterflow formulations. Individual tube-by-tube network marching and header pressure balancing can be built on top of the provided resistance and property utilities.

---

## 3. Integrating with Other Software

`fintube_hx` is designed as a standalone Python library that can easily integrate into larger engineering pipelines or optimization loops:

```python
from fintube_hx.engine import run_case
from fintube_hx.schema import validate_case

def evaluate_hx_design(params: dict) -> float:
    case = build_case_from_params(params)
    validate_case(case)
    result = run_case(case)
    if not result["converged"]:
        raise ValueError("Calculation did not converge")
    return result["heat_transfer_w"]
```

Inputs and outputs are standard JSON-serializable dictionaries, making it straightforward to wrap the core into REST APIs, GUI front-ends, or optimization frameworks.
