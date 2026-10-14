# External review v3 follow-up

## Accepted corrections

- The original mapped water comparison remains 4363.49 W; straight-tube pressure drop remains 2435.37 Pa. The source audit showing a Darcy/Fanning factor-of-four mismatch in python-hvac is accepted. Its 3099.25 Pa correction removes that factor only, not all other reference modelling differences.
- The wet-branch approximation is an important source of the capacity peak in this mapped case, not merely a generic possible contributor. A fixed-case branch ablation is recorded below. It is **not** a new partial-wet model.
- Wang correlations require the **fin-collar diameter**, not bare-tube OD. For the adopted equal-thickness collar convention, Dc = Do + 2tf. Formed collar dimensions and wall thinning are separate physical inputs not resolved here. The upstream pinned correlation API explicitly specifies collar diameter; full primary-paper database reconstruction was not performed in this follow-up.
- Version-status statements written before the Professional installer rebuild were outdated: Professional 0.6.5.dev2 already contained core dev5 and the diagonal-clearance/worker fixes.

## Controlled wet-branch diagnostic

All geometry, flow, boundaries and correlations are fixed to the public mapped water case. The diagnostic disables both the wet equivalent-capacity/efficiency branch and wet contact. No production source file is modified, and no measured capacity is fitted.

| Inlet water / °C | Reference / W | Normal calculation / W | Forced-dry diagnostic / W | Normal difference | Diagnostic difference |
|---|---:|---:|---:|---:|---:|
| 10 | 3160.24 | 3551.49 | 2748.78 | +12.38% | −13.02% |
| 12.5 | 2397.30 | 2785.60 | 2360.35 | +16.20% | −1.54% |
| 14 | 2156.21 | 2274.78 | 2123.93 | +5.50% | −1.50% |

This supports prioritizing the wet branch for the peak near 12.5–14°C. It does not isolate the Boolean criterion from its equivalent cp, efficiency and contact closure, and does not establish an exact fraction of error attributable to each. At 10°C, forcing the coil dry is seriously wrong in the opposite direction; it must not become the production fix.

## Immediate budget fix: 0.1.0.dev6

For **lumped refrigerant axial models only**, a missing max-iteration setting now defaults to `max(200, 2*segments+20)`: 320 cells select 660 iterations and 400 select 820. Pure-water and actual tube-network policies retain 200. Explicit user limits remain unchanged, and a low limit is reported in warnings and the result budget record. Nonconvergence still produces a failed status/CLI exit 2.

The default scaling allocates enough room for observed counterflow propagation; it is not a convergence guarantee and does not alter cell heat-transfer equations. The original explicit-150 examples and prior numerical records are retained.

Tests: `tests/test_iteration_budget.py`. Existing dev5 diagonal-clearance and inverse-bracket corrections remain in place.
